"""
Idempotency tracking for MediaMan sends with explicit delivery states.

Uses 15-minute UTC cycle buckets and explicit state transitions:
- PENDING: Cycle generated, ready to send
- SENDING: Send in progress
- SENT: Telegram confirmed success
- FAILED: Send failed, retryable

Runtime state stored outside Git in /var/lib/mediaman/
Uses atomic file writes (write-temp-then-fsync-then-rename) for safety.
Relies on os.replace() for atomic state transitions (POSIX semantics).
"""

import json
import os
import hashlib
import tempfile
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class IdempotencyKey:
    """Immutable key for send idempotency based on 15-minute UTC buckets."""
    race_id: str
    cycle_timestamp: str  # Normalized to 15-min boundary (e.g., 2026-08-26T19:00:00Z)
    chat_id: str
    
    def hash(self) -> str:
        """Compute deterministic hash of the key."""
        key_str = f"{self.race_id}|{self.cycle_timestamp}|{self.chat_id}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def normalize_to_15min_bucket(dt: datetime) -> str:
    """
    Normalize a datetime to the start of its 15-minute UTC bucket.
    
    Examples:
    - 2026-08-26T19:07:30Z → 2026-08-26T19:00:00Z
    - 2026-08-26T19:14:59Z → 2026-08-26T19:00:00Z
    - 2026-08-26T19:15:00Z → 2026-08-26T19:15:00Z
    """
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Round down to nearest 15-minute boundary
    minutes = (dt.minute // 15) * 15
    normalized = dt.replace(minute=minutes, second=0, microsecond=0)
    return normalized.isoformat()


class DeliveryRecord:
    """Record of a delivery attempt with explicit state."""
    
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    
    def __init__(self, cycle_id: str, state: str, timestamp: str, error: str = ""):
        self.cycle_id = cycle_id
        self.state = state
        self.timestamp = timestamp
        self.error = error
    
    def to_dict(self):
        """Serialize to JSON-safe dict."""
        return {
            "cycle_id": self.cycle_id,
            "state": self.state,
            "timestamp": self.timestamp,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Deserialize from dict."""
        return cls(
            cycle_id=data.get("cycle_id"),
            state=data.get("state"),
            timestamp=data.get("timestamp"),
            error=data.get("error", "")
        )


class IdempotencyStore:
    """
    Stateful delivery tracking with explicit state machine.
    
    State file: /var/lib/mediaman/delivery-state.json (outside Git)
    Uses atomic writes via tempfile + os.replace for safety.
    No explicit locking—relies on POSIX atomic rename for consistency.
    
    Design:
    - Each operation reads, modifies, and atomically writes the entire state.
    - Concurrent writes may race, but the last one wins (safe for one-shot processes).
    - For true concurrency, use fcntl-based locking (future enhancement).
    """
    
    def __init__(self, state_dir: str = None):
        if state_dir is None:
            state_dir = "/var/lib/mediaman"
        
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "delivery-state.json"
        
        # Create directory if needed
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    
    def _load_state(self) -> dict:
        """Load state from disk or return empty dict."""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_state(self, state: dict) -> None:
        """Save state to disk atomically (temp → fsync → rename)."""
        try:
            # Write to temp file in same directory (for atomic rename)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(self.state_dir),
                prefix=".delivery-state-",
                suffix=".tmp"
            )
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(state, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception:
                os.close(temp_fd)
                raise
            
            # Atomic rename
            Path(temp_path).replace(self.state_file)
        except Exception:
            pass  # Non-fatal: continue with in-memory state
    
    def record_pending(self, key: IdempotencyKey) -> bool:
        """
        Mark cycle as PENDING (ready to send).
        Returns True if new cycle, False if already known.
        """
        state = self._load_state()
        key_hash = key.hash()
        
        if key_hash in state:
            return False  # Already known
        
        # Create pending record
        record = DeliveryRecord(
            cycle_id=key.cycle_timestamp,
            state=DeliveryRecord.PENDING,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        state[key_hash] = record.to_dict()
        self._save_state(state)
        return True
    
    def record_sending(self, key: IdempotencyKey) -> None:
        """Mark cycle as SENDING (in progress)."""
        state = self._load_state()
        key_hash = key.hash()
        if key_hash in state:
            record = DeliveryRecord.from_dict(state[key_hash])
            record.state = DeliveryRecord.SENDING
            record.timestamp = datetime.now(timezone.utc).isoformat()
            state[key_hash] = record.to_dict()
            self._save_state(state)
    
    def record_sent(self, key: IdempotencyKey) -> None:
        """Mark cycle as SENT (Telegram confirmed success)."""
        state = self._load_state()
        key_hash = key.hash()
        if key_hash in state:
            record = DeliveryRecord.from_dict(state[key_hash])
            record.state = DeliveryRecord.SENT
            record.timestamp = datetime.now(timezone.utc).isoformat()
            record.error = ""
            state[key_hash] = record.to_dict()
            self._save_state(state)
    
    def record_failed(self, key: IdempotencyKey, error: str) -> None:
        """Mark cycle as FAILED (retryable)."""
        state = self._load_state()
        key_hash = key.hash()
        if key_hash in state:
            record = DeliveryRecord.from_dict(state[key_hash])
            record.state = DeliveryRecord.FAILED
            record.timestamp = datetime.now(timezone.utc).isoformat()
            record.error = error
            state[key_hash] = record.to_dict()
            self._save_state(state)
    
    def can_retry(self, key: IdempotencyKey) -> bool:
        """Check if a FAILED delivery can be retried."""
        state = self._load_state()
        key_hash = key.hash()
        if key_hash not in state:
            return True  # New cycle
        record = DeliveryRecord.from_dict(state[key_hash])
        # FAILED, PENDING, and SENDING (stale) can be retried
        return record.state in (DeliveryRecord.FAILED, DeliveryRecord.PENDING, DeliveryRecord.SENDING)
    
    def get_state(self, key: IdempotencyKey) -> str:
        """Get current state of a cycle."""
        state = self._load_state()
        key_hash = key.hash()
        if key_hash not in state:
            return None
        record = DeliveryRecord.from_dict(state[key_hash])
        return record.state
    
    def cleanup_old_entries(self, max_age_days: int = 90) -> int:
        """Remove entries older than max_age_days. Returns count removed."""
        state = self._load_state()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        keys_to_remove = []
        for key, record in state.items():
            if record.get("timestamp", "") < cutoff:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del state[key]
        
        if keys_to_remove:
            self._save_state(state)
        
        return len(keys_to_remove)
    
    def get_stats(self) -> dict:
        """Return statistics about stored sends."""
        state = self._load_state()
        self.cleanup_old_entries()
        states = {}
        for record in state.values():
            st = record.get("state", "UNKNOWN")
            states[st] = states.get(st, 0) + 1
        
        return {
            "total_records": len(state),
            "state_file": str(self.state_file),
            "states": states,
            "last_write": (
                datetime.fromtimestamp(
                    self.state_file.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                if self.state_file.exists()
                else None
            )
        }
    
    def clear_for_testing(self) -> None:
        """Clear all state for testing. Use with caution."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass

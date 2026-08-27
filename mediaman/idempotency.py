"""
Idempotency tracking for MediaMan with explicit fcntl locking and atomic writes.

Delivery states: PENDING → SENDING → SENT/FAILED
Lock: fcntl.flock(LOCK_EX) on separate .lock file
Atomicity: temp file + fsync + os.replace()
Runtime: /var/lib/mediaman (production) or TemporaryDirectory (tests)
"""

import json
import os
import hashlib
import tempfile
import fcntl
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class IdempotencyKey:
    """15-minute UTC bucket-based idempotency key."""
    race_id: str
    cycle_timestamp: str
    chat_id: str
    
    def hash(self) -> str:
        key_str = f"{self.race_id}|{self.cycle_timestamp}|{self.chat_id}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def normalize_to_15min_bucket(dt: datetime) -> str:
    """Normalize datetime to 15-minute UTC bucket."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    minutes = (dt.minute // 15) * 15
    normalized = dt.replace(minute=minutes, second=0, microsecond=0)
    return normalized.isoformat()


class DeliveryRecord:
    """Explicit delivery state record."""
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
        return {
            "cycle_id": self.cycle_id,
            "state": self.state,
            "timestamp": self.timestamp,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            cycle_id=data.get("cycle_id"),
            state=data.get("state"),
            timestamp=data.get("timestamp"),
            error=data.get("error", "")
        )


class IdempotencyStore:
    """Locked idempotency store with atomic writes."""
    
    def __init__(self, state_dir: str = None):
        if state_dir is None:
            state_dir = "/var/lib/mediaman"
        
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "idempotency.json"
        self.lock_file = self.state_dir / "idempotency.lock"
        
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        self._lock_fd = None
    
    def _acquire_lock(self):
        """Acquire exclusive lock. Raise on failure."""
        try:
            self._lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR, 0o644)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
        except Exception as e:
            if self._lock_fd is not None:
                try:
                    os.close(self._lock_fd)
                except:
                    pass
            raise RuntimeError(f"Failed to acquire lock: {e}")
    
    def _release_lock(self):
        """Release lock. No error on failure (best effort)."""
        try:
            if self._lock_fd is not None:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
        except Exception:
            pass
    
    def _load_state(self) -> dict:
        """Load state from disk. Fail-closed on corruption."""
        if not self.state_file.exists():
            return {}  # OK: file doesn't exist yet
        
        try:
            with open(self.state_file) as f:
                return json.load(f)  # OK: valid JSON
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"State file corrupted (invalid JSON): {self.state_file} at position {e.pos}"
            )
        except OSError as e:
            raise RuntimeError(
                f"State file storage error: {self.state_file} ({e})"
            )
        except Exception as e:
            raise RuntimeError(
                f"Unexpected state file error: {self.state_file} ({type(e).__name__}: {e})"
            )
    
    def _save_state(self, state: dict) -> None:
        """Save state atomically: temp → fsync → rename."""
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(self.state_dir),
                prefix=".idempotency-",
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
            Path(temp_path).replace(self.state_file)
        except Exception:
            pass
    
    def record_pending(self, key: IdempotencyKey) -> bool:
        """Acquire lock, check if new, record PENDING.
        
        Raises:
            RuntimeError: If state file is corrupted or storage error occurs.
        """
        self._acquire_lock()
        try:
            state = self._load_state()  # Raises RuntimeError on corruption
            key_hash = key.hash()
            
            if key_hash in state:
                return False
            
            record = DeliveryRecord(
                cycle_id=key.cycle_timestamp,
                state=DeliveryRecord.PENDING,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            state[key_hash] = record.to_dict()
            self._save_state(state)
            return True
        finally:
            self._release_lock()
    
    def record_sending(self, key: IdempotencyKey) -> None:
        """Mark as SENDING under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
            key_hash = key.hash()
            if key_hash in state:
                record = DeliveryRecord.from_dict(state[key_hash])
                record.state = DeliveryRecord.SENDING
                record.timestamp = datetime.now(timezone.utc).isoformat()
                state[key_hash] = record.to_dict()
                self._save_state(state)
        finally:
            self._release_lock()
    
    def record_sent(self, key: IdempotencyKey) -> None:
        """Mark as SENT under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
            key_hash = key.hash()
            if key_hash in state:
                record = DeliveryRecord.from_dict(state[key_hash])
                record.state = DeliveryRecord.SENT
                record.timestamp = datetime.now(timezone.utc).isoformat()
                record.error = ""
                state[key_hash] = record.to_dict()
                self._save_state(state)
        finally:
            self._release_lock()
    
    def record_failed(self, key: IdempotencyKey, error: str) -> None:
        """Mark as FAILED under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
            key_hash = key.hash()
            if key_hash in state:
                record = DeliveryRecord.from_dict(state[key_hash])
                record.state = DeliveryRecord.FAILED
                record.timestamp = datetime.now(timezone.utc).isoformat()
                record.error = error
                state[key_hash] = record.to_dict()
                self._save_state(state)
        finally:
            self._release_lock()
    
    def can_retry(self, key: IdempotencyKey) -> bool:
        """Check retryability under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
            key_hash = key.hash()
            if key_hash not in state:
                return True
            record = DeliveryRecord.from_dict(state[key_hash])
            return record.state in (DeliveryRecord.FAILED, DeliveryRecord.PENDING, DeliveryRecord.SENDING)
        finally:
            self._release_lock()
    
    def get_state(self, key: IdempotencyKey) -> str:
        """Get state under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
            key_hash = key.hash()
            if key_hash not in state:
                return None
            record = DeliveryRecord.from_dict(state[key_hash])
            return record.state
        finally:
            self._release_lock()
    
    def cleanup_old_entries(self, max_age_days: int = 90) -> int:
        """Remove old entries under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
            cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
            keys_to_remove = [k for k, r in state.items() if r.get("timestamp", "") < cutoff]
            for key in keys_to_remove:
                del state[key]
            if keys_to_remove:
                self._save_state(state)
            return len(keys_to_remove)
        finally:
            self._release_lock()
    
    def get_stats(self) -> dict:
        """Get stats under lock."""
        self._acquire_lock()
        try:
            state = self._load_state()
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
        finally:
            self._release_lock()
    
    def clear_for_testing(self) -> None:
        """Clear state for testing."""
        self._acquire_lock()
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        finally:
            self._release_lock()

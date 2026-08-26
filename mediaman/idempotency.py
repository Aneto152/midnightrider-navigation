"""
Idempotency tracking for MediaMan sends.

Ensures the same cycle is never sent twice to the same Telegram target.
Uses local state file outside Git.
"""

import json
import os
import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class IdempotencyKey:
    """Immutable key for send idempotency."""
    race_id: str
    cycle_timestamp: str
    chat_id: str
    
    def hash(self) -> str:
        """Compute deterministic hash of the key."""
        key_str = f"{self.race_id}|{self.cycle_timestamp}|{self.chat_id}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]


class IdempotencyStore:
    """
    Local state store for idempotency tracking.
    
    Located outside Git in ~/.openclaw/mediaman/idempotency.json
    """
    
    def __init__(self, state_dir: str = None):
        if state_dir is None:
            state_dir = os.path.expanduser("~/.openclaw/mediaman")
        
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "idempotency.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load state from disk or return empty dict."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_state(self) -> None:
        """Save state to disk."""
        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2)
    
    def _cleanup_old_entries(self, max_age_days: int = 90) -> None:
        """Remove entries older than max_age_days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        
        keys_to_remove = []
        for key, record in self._state.items():
            if record.get("timestamp", "") < cutoff:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._state[key]
    
    def check_and_record(self, key: IdempotencyKey) -> bool:
        """
        Check if key was already sent. If not, record it and return True.
        
        Returns:
            True if this is a new cycle (should send)
            False if already sent (skip)
        """
        key_hash = key.hash()
        
        if key_hash in self._state:
            return False  # Already sent
        
        # Record new send
        self._state[key_hash] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "race_id": key.race_id,
            "chat_id": key.chat_id,  # Not PII; stored in config
            "cycle": key.cycle_timestamp
        }
        
        # Cleanup old entries periodically
        if len(self._state) % 10 == 0:
            self._cleanup_old_entries()
        
        self._save_state()
        return True  # New cycle, should send
    
    def get_stats(self) -> dict:
        """Return statistics about stored sends."""
        self._cleanup_old_entries()
        return {
            "total_records": len(self._state),
            "state_file": str(self.state_file),
            "last_write": (
                datetime.fromtimestamp(
                    self.state_file.stat().st_mtime
                ).isoformat()
                if self.state_file.exists()
                else None
            )
        }
    
    def clear_for_testing(self) -> None:
        """Clear all state for testing. Use with caution."""
        self._state.clear()
        self._save_state()

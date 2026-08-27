"""
SQLite-backed idempotency store for MediaMan delivery state.

Uses transactional semantics for reliable state tracking:
- PENDING: ready to send
- SENDING: in progress
- SENT: confirmed by provider (final)
- FAILED: failed, retryable

Unique constraint: (race_id, cycle_id, target_id)
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager


class SQLiteStateStore:
    """Transactional SQLite-backed delivery state."""
    
    STALE_SENDING_TIMEOUT_SECONDS = 3600  # 1 hour
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = "/var/lib/mediaman/state.sqlite3"
        
        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Cannot create state directory {self.db_path.parent}: {e}")
        
        self._init_schema()
    
    def _get_conn(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    @contextmanager
    def _transaction(self):
        """Context manager for transactions."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Create schema if missing."""
        try:
            with self._transaction() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS deliveries (
                        delivery_key TEXT PRIMARY KEY,
                        race_id TEXT NOT NULL,
                        cycle_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        state TEXT NOT NULL CHECK (
                            state IN ('PENDING', 'SENDING', 'SENT', 'FAILED')
                        ),
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL,
                        sent_at INTEGER,
                        provider_message_id TEXT,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_delivery_identity
                    ON deliveries(race_id, cycle_id, target_id)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_deliveries_retry
                    ON deliveries(state, updated_at)
                    """
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Schema initialization failed: {e}")
    
    def _make_key(self, race_id: str, cycle_id: str, target_id: str) -> str:
        """Create a unique delivery key."""
        return f"{race_id}|{cycle_id}|{target_id}"
    
    def record_pending(self, race_id: str, cycle_id: str, target_id: str) -> bool:
        """Try to reserve a delivery as PENDING. Returns True if reserved, False if already exists."""
        key = self._make_key(race_id, cycle_id, target_id)
        now = int(datetime.now(timezone.utc).timestamp())
        
        try:
            with self._transaction() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO deliveries 
                    (delivery_key, race_id, cycle_id, target_id, state, created_at, updated_at, retry_count)
                    VALUES (?, ?, ?, ?, 'PENDING', ?, ?, 0)
                    """,
                    (key, race_id, cycle_id, target_id, now, now)
                )
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False  # Already exists
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to record pending: {e}")
    
    def record_sending(self, race_id: str, cycle_id: str, target_id: str) -> None:
        """Transition from PENDING to SENDING."""
        key = self._make_key(race_id, cycle_id, target_id)
        now = int(datetime.now(timezone.utc).timestamp())
        
        try:
            with self._transaction() as conn:
                conn.execute(
                    """
                    UPDATE deliveries SET state='SENDING', updated_at=?
                    WHERE delivery_key=? AND state='PENDING'
                    """,
                    (now, key)
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to record sending: {e}")
    
    def record_sent(self, race_id: str, cycle_id: str, target_id: str, 
                   provider_message_id: str = None) -> None:
        """Transition from SENDING to SENT."""
        key = self._make_key(race_id, cycle_id, target_id)
        now = int(datetime.now(timezone.utc).timestamp())
        
        try:
            with self._transaction() as conn:
                conn.execute(
                    """
                    UPDATE deliveries 
                    SET state='SENT', updated_at=?, sent_at=?, provider_message_id=?, last_error=NULL
                    WHERE delivery_key=? AND state='SENDING'
                    """,
                    (now, now, provider_message_id, key)
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to record sent: {e}")
    
    def record_failed(self, race_id: str, cycle_id: str, target_id: str, 
                     error: str) -> None:
        """Transition from SENDING to FAILED."""
        key = self._make_key(race_id, cycle_id, target_id)
        now = int(datetime.now(timezone.utc).timestamp())
        
        try:
            with self._transaction() as conn:
                conn.execute(
                    """
                    UPDATE deliveries 
                    SET state='FAILED', updated_at=?, retry_count=retry_count+1, last_error=?
                    WHERE delivery_key=? AND state='SENDING'
                    """,
                    (now, error[:500], key)  # Truncate error to 500 chars
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to record failure: {e}")
    
    def claim_for_send(self, race_id: str, cycle_id: str, target_id: str) -> bool:
        """Claim a delivery for sending. Returns True if allowed to send.
        
        Allowed:
        - absent → PENDING → SENDING
        - FAILED → SENDING (retry)
        - stale SENDING → SENDING (recovery)
        
        Blocked:
        - SENT (never retry)
        - recent SENDING (already in progress)
        """
        key = self._make_key(race_id, cycle_id, target_id)
        now = int(datetime.now(timezone.utc).timestamp())
        
        try:
            with self._transaction() as conn:
                # Check existing state
                cursor = conn.execute(
                    "SELECT state, updated_at FROM deliveries WHERE delivery_key=?",
                    (key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    # New delivery: reserve as PENDING, transition to SENDING
                    conn.execute(
                        """
                        INSERT INTO deliveries 
                        (delivery_key, race_id, cycle_id, target_id, state, created_at, updated_at, retry_count)
                        VALUES (?, ?, ?, ?, 'SENDING', ?, ?, 0)
                        """,
                        (key, race_id, cycle_id, target_id, now, now)
                    )
                    return True
                
                state, updated_at = row
                
                if state == 'SENT':
                    return False  # Never retry SENT
                
                if state == 'FAILED':
                    # Retry: transition to SENDING
                    conn.execute(
                        "UPDATE deliveries SET state='SENDING', updated_at=? WHERE delivery_key=?",
                        (now, key)
                    )
                    return True
                
                if state == 'SENDING':
                    age = now - updated_at
                    if age > self.STALE_SENDING_TIMEOUT_SECONDS:
                        # Stale: retry transition to SENDING
                        conn.execute(
                            "UPDATE deliveries SET state='SENDING', updated_at=? WHERE delivery_key=?",
                            (now, key)
                        )
                        return True
                    else:
                        # Recent: do not retry
                        return False
                
                # PENDING: transition to SENDING
                if state == 'PENDING':
                    conn.execute(
                        "UPDATE deliveries SET state='SENDING', updated_at=? WHERE delivery_key=?",
                        (now, key)
                    )
                    return True
                
                return False
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to claim for send: {e}")


    def can_retry(self, race_id: str, cycle_id: str, target_id: str) -> bool:
        """Check if a delivery is retryable."""
        key = self._make_key(race_id, cycle_id, target_id)
        now = int(datetime.now(timezone.utc).timestamp())
        
        try:
            with self._transaction() as conn:
                cursor = conn.execute(
                    """
                    SELECT state, updated_at FROM deliveries WHERE delivery_key=?
                    """,
                    (key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return True  # Not yet reserved
                
                state, updated_at = row
                
                if state == 'SENT':
                    return False  # Never retry SENT
                
                if state == 'FAILED':
                    return True  # Always retry FAILED
                
                if state == 'PENDING':
                    return True  # Retry PENDING
                
                if state == 'SENDING':
                    age = now - updated_at
                    return age > self.STALE_SENDING_TIMEOUT_SECONDS  # Retry if stale
                
                return False
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to check retry: {e}")
    
    def get_state(self, race_id: str, cycle_id: str, target_id: str) -> str:
        """Get the current state."""
        key = self._make_key(race_id, cycle_id, target_id)
        
        try:
            with self._transaction() as conn:
                cursor = conn.execute(
                    "SELECT state FROM deliveries WHERE delivery_key=?",
                    (key,)
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get state: {e}")
    
    def get_stats(self) -> dict:
        """Get delivery statistics."""
        try:
            with self._transaction() as conn:
                cursor = conn.execute(
                    "SELECT state, COUNT(*) FROM deliveries GROUP BY state"
                )
                rows = cursor.fetchall()
                states = {row[0]: row[1] for row in rows}
                
                cursor = conn.execute("SELECT COUNT(*) FROM deliveries")
                total = cursor.fetchone()[0]
                
                return {
                    "total_records": total,
                    "states": states,
                    "db_path": str(self.db_path),
                    "db_exists": self.db_path.exists()
                }
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get stats: {e}")
    
    def clear_for_testing(self) -> None:
        """Clear all data for testing."""
        try:
            with self._transaction() as conn:
                conn.execute("DELETE FROM deliveries")
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to clear: {e}")

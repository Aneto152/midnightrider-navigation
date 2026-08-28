"""
EventQueue — Durable local SQLite queue for DetectedEvent objects.

Idempotent enqueue by event_id. Transactional claim with exponential backoff.
No external publishers, no network access, no daemon.
"""

import sqlite3
import json
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum

from mediaman.event_detector import DetectedEvent


class EventStatus(Enum):
    """Queue event status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class QueuedEvent:
    """Representation of a queued event."""
    event_id: str
    event_type: str
    status: str
    attempts: int
    observed_at: str
    source_timestamp: Optional[str]
    race_id: Optional[str]
    severity: str
    affected_field: Optional[str]
    payload_json: str
    next_attempt_at: str
    locked_until: Optional[str]
    last_error: Optional[str]
    created_at: str
    updated_at: str


class EventQueue:
    """Durable SQLite event queue."""

    def __init__(self, db_path: str = ":memory:", clock=None):
        """Initialize queue."""
        self.db_path = db_path
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', '') + 'Z')
        self.conn = None
        self.initialize()

    def _row_to_queued_event(self, row: sqlite3.Row) -> QueuedEvent:
        """Convert a sqlite3.Row to QueuedEvent using named column access."""
        return QueuedEvent(
            event_id=row['event_id'],
            event_type=row['event_type'],
            status=row['status'],
            attempts=row['attempts'],
            observed_at=row['observed_at'],
            source_timestamp=row['source_timestamp'],
            race_id=row['race_id'],
            severity=row['severity'],
            affected_field=row['affected_field'],
            payload_json=row['payload_json'],
            next_attempt_at=row['next_attempt_at'],
            locked_until=row['locked_until'],
            last_error=row['last_error'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def initialize(self):
        """Create schema and open connection."""
        self.conn = sqlite3.connect(self.db_path, timeout=10.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                source_timestamp TEXT,
                race_id TEXT,
                severity TEXT NOT NULL,
                affected_field TEXT,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT NOT NULL,
                locked_until TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def enqueue(self, event: DetectedEvent) -> bool:
        """
        Enqueue a DetectedEvent idempotently.

        Returns True if inserted, False if already exists.
        """
        # Validate no sensitive data in payload
        event_dict = event.to_dict()
        payload_json = json.dumps(event_dict, ensure_ascii=False, sort_keys=True)

        # Check for sensitive patterns
        if any(x in payload_json for x in ['latitude', 'longitude', 'token', 'password', 'secret']):
            if any(pattern in event_dict.get('affected_field', '') or
                   str(event_dict.get('event_type', '')).count('position') > 0
                   for pattern in ['41.', '73.', '-73.']):
                raise ValueError("Exact coordinates not allowed in queue payload")

        now = self.clock()
        try:
            self.conn.execute("""
                INSERT INTO events (
                    event_id, event_type, observed_at, source_timestamp, race_id,
                    severity, affected_field, payload_json, status, attempts,
                    next_attempt_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.event_type, event.observed_at,
                event.source_timestamp, event.race_id, event.severity,
                event.affected_field, payload_json, EventStatus.PENDING.value, 0,
                now, now, now
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Event already exists
            return False

    def claim(self, count: int = 10, lock_duration_seconds: int = 300) -> List[QueuedEvent]:
        """
        Claim PENDING events due for retry.

        Returns a list of claimed events; marks them PROCESSING.
        """
        now = self.clock()
        locked_until = (
            datetime.fromisoformat(now.replace('Z', '+00:00')) +
            timedelta(seconds=lock_duration_seconds)
        ).isoformat().replace('+00:00', 'Z')

        cursor = self.conn.execute("""
            SELECT event_id, event_type, observed_at, source_timestamp, race_id,
                   severity, affected_field, payload_json, status, attempts,
                   next_attempt_at, locked_until, last_error, created_at, updated_at
            FROM events
            WHERE status = ? AND next_attempt_at <= ?
            LIMIT ?
        """, (EventStatus.PENDING.value, now, count))

        events = []
        event_ids = []
        for row in cursor:
            events.append(self._row_to_queued_event(row))
            event_ids.append(row['event_id'])

        if event_ids:
            placeholders = ','.join(['?' for _ in event_ids])
            self.conn.execute(f"""
                UPDATE events SET status = ?, locked_until = ?, updated_at = ?
                WHERE event_id IN ({placeholders})
            """, [EventStatus.PROCESSING.value, locked_until, now] + event_ids)
            self.conn.commit()

        return events

    def mark_sent(self, event_id: str) -> bool:
        """Mark event as SENT (idempotent)."""
        now = self.clock()
        cursor = self.conn.execute("""
            UPDATE events SET status = ?, updated_at = ?
            WHERE event_id = ? AND status != ?
        """, (EventStatus.SENT.value, now, event_id, EventStatus.SENT.value))
        self.conn.commit()
        return cursor.rowcount > 0

    def mark_failed(self, event_id: str, error: str, max_attempts: int = 5) -> bool:
        """Mark event failed; increment attempts; schedule retry or move to DEAD_LETTER."""
        now = self.clock()
        sanitized_error = error[:200] if error else ""

        cursor = self.conn.execute("SELECT attempts FROM events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            return False

        attempts = row[0] + 1
        new_status = EventStatus.DEAD_LETTER.value if attempts >= max_attempts else EventStatus.PENDING.value

        # Exponential backoff: 2^attempts seconds, capped at 3600 (1 hour)
        backoff_secs = min(2 ** attempts, 3600)
        next_attempt_at = (
            datetime.fromisoformat(now.replace('Z', '+00:00')) +
            timedelta(seconds=backoff_secs)
        ).isoformat().replace('+00:00', 'Z')

        self.conn.execute("""
            UPDATE events SET status = ?, attempts = ?, next_attempt_at = ?,
                             last_error = ?, updated_at = ?
            WHERE event_id = ?
        """, (new_status, attempts, next_attempt_at, sanitized_error, now, event_id))
        self.conn.commit()
        return True

    def release_expired_leases(self) -> int:
        """Release PROCESSING events whose lock has expired."""
        now = self.clock()
        cursor = self.conn.execute("""
            UPDATE events SET status = ?, locked_until = NULL, updated_at = ?
            WHERE status = ? AND locked_until IS NOT NULL AND locked_until <= ?
        """, (EventStatus.PENDING.value, now, EventStatus.PROCESSING.value, now))
        self.conn.commit()
        return cursor.rowcount

    def get_event(self, event_id: str) -> Optional[QueuedEvent]:
        """Retrieve a single event by ID."""
        cursor = self.conn.execute("""
            SELECT event_id, event_type, observed_at, source_timestamp, race_id,
                   severity, affected_field, payload_json, status, attempts,
                   next_attempt_at, locked_until, last_error, created_at, updated_at
            FROM events WHERE event_id = ?
        """, (event_id,))
        row = cursor.fetchone()
        return self._row_to_queued_event(row) if row else None

    def count_by_status(self, status: str) -> int:
        """Count events by status."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM events WHERE status = ?", (status,))
        return cursor.fetchone()[0]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

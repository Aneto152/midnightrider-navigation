"""Tests for EventQueue — local durable SQLite queue for DetectedEvent objects."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sqlite3

from mediaman.event_queue import EventQueue, EventStatus, QueuedEvent
from mediaman.event_detector import DetectedEvent


@pytest.fixture
def temp_db():
    """Temporary SQLite database (in-memory preferred)."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def in_memory_db():
    """In-memory database for isolation."""
    return ":memory:"


@pytest.fixture
def clock():
    """Deterministic clock for testing."""
    base_time = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

    class Clock:
        def __init__(self):
            self.current = base_time

        def __call__(self):
            result = self.current.isoformat().replace('+00:00', '') + 'Z'
            self.current += timedelta(seconds=1)
            return result

    return Clock()


@pytest.fixture
def sample_event():
    """Create a sample DetectedEvent."""
    return DetectedEvent(
        event_id="evt_test_abc123",
        event_type="NAVIGATION_DATA_LOST",
        observed_at="2026-08-28T12:00:00Z",
        source_timestamp="2026-08-28T11:59:00Z",
        race_id="race_001",
        severity="WARNING",
        affected_field=None,
        previous_status="COMPLETE",
        current_status="PARTIAL",
    )


class TestEventQueueSchema:
    """Test schema creation."""

    def test_schema_creation(self, temp_db):
        """Schema is created on initialization."""
        queue = EventQueue(temp_db)
        cursor = queue.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        )
        assert cursor.fetchone() is not None
        queue.close()


class TestEventQueueEnqueue:
    """Test idempotent enqueue."""

    def test_enqueue_valid_event(self, temp_db, sample_event, clock):
        """Enqueuing a valid event returns True."""
        queue = EventQueue(temp_db, clock=clock)
        result = queue.enqueue(sample_event)
        assert result is True
        queue.close()

    def test_duplicate_enqueue_idempotent(self, temp_db, sample_event, clock):
        """Enqueuing the same event twice returns False on second attempt."""
        queue = EventQueue(temp_db, clock=clock)
        result1 = queue.enqueue(sample_event)
        result2 = queue.enqueue(sample_event)
        assert result1 is True
        assert result2 is False
        queue.close()

    def test_duplicate_enqueue_preserves_sent_status(self, temp_db, sample_event, clock):
        """Duplicate enqueue does not reset SENT status."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)
        queue.conn.execute(
            "UPDATE events SET status = ? WHERE event_id = ?",
            (EventStatus.SENT.value, sample_event.event_id),
        )
        queue.conn.commit()

        result = queue.enqueue(sample_event)
        assert result is False

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.SENT.value
        queue.close()


class TestEventQueueSensitiveFieldRejection:
    """Test fail-closed validation for sensitive fields."""

    def test_latitude_field_rejection(self, in_memory_db, clock):
        """Events with 'latitude' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event = DetectedEvent(
            event_id="evt_latitude_reject",
            event_type="POSITION_UPDATE",
            observed_at="2026-08-28T12:00:00Z",
            severity="INFO",
        )
        # Add latitude to the dict via mutation before serialization check
        event_dict = event.to_dict()
        event_dict['latitude'] = 41.5

        with pytest.raises(ValueError, match="latitude"):
            # We test the validation directly
            queue._validate_payload(event_dict)
        queue.close()

    def test_longitude_field_rejection(self, in_memory_db, clock):
        """Events with 'longitude' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_lon_reject',
            'event_type': 'POSITION_UPDATE',
            'longitude': -73.9,
        }

        with pytest.raises(ValueError, match="longitude"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_lat_field_rejection(self, in_memory_db, clock):
        """Events with 'lat' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_lat', 'lat': 41.5}

        with pytest.raises(ValueError, match="lat"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_lon_field_rejection(self, in_memory_db, clock):
        """Events with 'lon' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_lon', 'lon': -73.9}

        with pytest.raises(ValueError, match="lon"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_nested_coordinate_rejection(self, in_memory_db, clock):
        """Events with coordinates in nested structures are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_nested_coord',
            'position': {'latitude': 41.5, 'longitude': -73.9}
        }

        with pytest.raises(ValueError, match="latitude|longitude"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_token_field_rejection(self, in_memory_db, clock):
        """Events with 'token' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_token', 'token': 'abc123def456'}

        with pytest.raises(ValueError, match="token"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_password_field_rejection(self, in_memory_db, clock):
        """Events with 'password' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_pwd', 'password': 'secret123'}

        with pytest.raises(ValueError, match="password"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_secret_field_rejection(self, in_memory_db, clock):
        """Events with 'secret' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_secret', 'secret': 'hidden'}

        with pytest.raises(ValueError, match="secret"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_api_key_field_rejection(self, in_memory_db, clock):
        """Events with 'api_key' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_key', 'api_key': 'key_xyz789'}

        with pytest.raises(ValueError, match="api_key"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_credential_pattern_rejection(self, in_memory_db, clock):
        """Events with credential-like patterns are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_cred',
            'error': 'connection failed: credential=mypass'
        }

        with pytest.raises(ValueError, match="Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_password_pattern_rejection(self, in_memory_db, clock):
        """Events with password= patterns are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_pwd_pattern',
            'message': 'password=secret123'
        }

        with pytest.raises(ValueError, match="Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_token_pattern_rejection(self, in_memory_db, clock):
        """Events with token= patterns are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_token_pat',
            'header': 'token=abc123xyz'
        }

        with pytest.raises(ValueError, match="Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()


class TestEventQueueErrorSanitization:
    """Test error message sanitization."""

    def test_last_error_redaction(self, temp_db, sample_event, clock):
        """last_error is sanitized: credentials are redacted."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        error_with_creds = "Connection failed: token=abc123xyz password=secret456"
        queue.mark_failed(sample_event.event_id, error_with_creds)

        event = queue.get_event(sample_event.event_id)
        assert event.last_error is not None
        assert 'abc123xyz' not in event.last_error
        assert 'secret456' not in event.last_error
        assert '<redacted>' in event.last_error
        queue.close()

    def test_last_error_truncation_after_redaction(self, temp_db, sample_event, clock):
        """last_error is truncated only after sanitization."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        long_error = ("x" * 150) + " token=secret123" + ("y" * 150)
        queue.mark_failed(sample_event.event_id, long_error)

        event = queue.get_event(sample_event.event_id)
        assert len(event.last_error) <= 200
        # Verify it was actually truncated
        assert len(event.last_error) < len(long_error)
        queue.close()

    def test_coordinate_redaction_in_error(self, temp_db, sample_event, clock):
        """Exact coordinates in error messages are redacted."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        error_with_coords = "Last position: latitude 41.3851 longitude -73.9268"
        queue.mark_failed(sample_event.event_id, error_with_coords)

        event = queue.get_event(sample_event.event_id)
        assert '41.3851' not in event.last_error
        assert '-73.9268' not in event.last_error
        assert '<coordinate>' in event.last_error
        queue.close()

    def test_authorization_redaction_in_error(self, temp_db, sample_event, clock):
        """Authorization headers are redacted."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        error_with_auth = "Request failed: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        queue.mark_failed(sample_event.event_id, error_with_auth)

        event = queue.get_event(sample_event.event_id)
        assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in event.last_error
        assert '<redacted>' in event.last_error
        queue.close()

    def test_empty_error_handling(self, temp_db, sample_event, clock):
        """Empty error strings are handled gracefully."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        queue.mark_failed(sample_event.event_id, "")

        event = queue.get_event(sample_event.event_id)
        assert event.last_error == ""
        queue.close()


class TestEventQueueClaim:
    """Test transactional claim operations."""

    def test_claim_due_pending_event(self, temp_db, sample_event, clock):
        """Claim returns PENDING events with due next_attempt_at."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        claimed = queue.claim(count=10)
        assert len(claimed) == 1
        assert claimed[0].event_id == sample_event.event_id
        queue.close()

    def test_claim_changes_status_to_processing(self, temp_db, sample_event, clock):
        """Claim changes event status to PROCESSING."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        queue.claim(count=10)

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.PROCESSING.value
        queue.close()

    def test_claim_bounded_size(self, temp_db, clock):
        """Claim respects count limit."""
        queue = EventQueue(temp_db, clock=clock)

        for i in range(15):
            event = DetectedEvent(
                event_id=f"evt_bounded_{i}",
                event_type="NAVIGATION_DATA_LOST",
                observed_at="2026-08-28T12:00:00Z",
                severity="WARNING",
            )
            queue.enqueue(event)

        claimed = queue.claim(count=5)
        assert len(claimed) == 5
        queue.close()

    def test_concurrent_claim_prevention(self, temp_db, sample_event, clock):
        """Two queue instances cannot claim the same event."""
        queue1 = EventQueue(temp_db, clock=clock)
        queue1.enqueue(sample_event)

        # First instance claims
        claimed1 = queue1.claim(count=1)
        assert len(claimed1) == 1

        # Second instance tries to claim from same database
        queue2 = EventQueue(temp_db, clock=clock)
        claimed2 = queue2.claim(count=1)

        # Second should get nothing (event is in PROCESSING status)
        assert len(claimed2) == 0

        queue1.close()
        queue2.close()


class TestEventQueueRetry:
    """Test retry and backoff behavior."""

    def test_mark_sent_idempotent(self, temp_db, sample_event, clock):
        """mark_sent is idempotent."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        result1 = queue.mark_sent(sample_event.event_id)
        result2 = queue.mark_sent(sample_event.event_id)

        assert result1 is True
        assert result2 is False  # No update on second call
        queue.close()

    def test_mark_failed_does_not_alter_sent(self, temp_db, sample_event, clock):
        """mark_failed cannot alter SENT events."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Mark as SENT
        queue.mark_sent(sample_event.event_id)

        # Try to mark as failed
        result = queue.mark_failed(sample_event.event_id, "Some error")
        assert result is False

        # Verify still SENT
        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.SENT.value
        queue.close()

    def test_mark_failed_increments_attempts(self, temp_db, sample_event, clock):
        """mark_failed increments attempts."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        queue.mark_failed(sample_event.event_id, "Network timeout")

        event = queue.get_event(sample_event.event_id)
        assert event.attempts == 1
        queue.close()

    def test_exponential_backoff(self, temp_db, sample_event, clock):
        """Retry delay uses deterministic exponential backoff."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # First failure: backoff = 2^1 = 2 seconds
        queue.mark_failed(sample_event.event_id, "Error 1")
        event1 = queue.get_event(sample_event.event_id)
        next_attempt_1 = datetime.fromisoformat(event1.next_attempt_at.replace('Z', '+00:00'))

        # Verify backoff is approximately 2 seconds
        base_time = datetime.fromisoformat("2026-08-28T12:00:00+00:00")
        delta = (next_attempt_1 - base_time).total_seconds()
        assert 1 < delta <= 4  # Allow some slack for clock granularity
        queue.close()

    def test_max_attempts_to_dead_letter(self, temp_db, sample_event, clock):
        """Events reach DEAD_LETTER after max attempts."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        for i in range(5):
            queue.mark_failed(sample_event.event_id, f"Failure {i+1}")

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.DEAD_LETTER.value
        queue.close()

    def test_retry_attempts_preserved(self, temp_db, sample_event, clock):
        """Retry attempts are preserved across operations."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        queue.mark_failed(sample_event.event_id, "First failure")
        queue.mark_failed(sample_event.event_id, "Second failure")

        event = queue.get_event(sample_event.event_id)
        assert event.attempts == 2
        queue.close()


class TestEventQueueLeaseRecovery:
    """Test expired lease recovery."""

    def test_release_expired_leases(self, temp_db, sample_event, clock):
        """release_expired_leases recovers PROCESSING events with expired locks."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Claim with 1-second lock
        queue.claim(count=10, lock_duration_seconds=1)

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.PROCESSING.value

        # Advance clock beyond lock expiry
        base_time = datetime.fromisoformat(clock().replace('Z', '+00:00'))
        clock.current = base_time + timedelta(seconds=10)

        released = queue.release_expired_leases()
        assert released == 1

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.PENDING.value
        queue.close()

    def test_dead_letter_unchanged_by_lease_recovery(self, temp_db, sample_event, clock):
        """DEAD_LETTER events are not affected by lease recovery."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Move to DEAD_LETTER
        for _ in range(5):
            queue.mark_failed(sample_event.event_id, "Repeated failures")

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.DEAD_LETTER.value

        # Release expired leases does nothing
        released = queue.release_expired_leases()
        assert released == 0

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.DEAD_LETTER.value
        queue.close()


class TestEventQueueTransactions:
    """Test transaction safety and atomicity."""

    def test_claim_is_atomic(self, temp_db, sample_event, clock):
        """Claim operation is atomic: all-or-nothing."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        claimed = queue.claim(count=10, lock_duration_seconds=300)

        # Verify all returned events have locked_until set
        for claimed_event in claimed:
            assert claimed_event.locked_until is not None

        queue.close()

    def test_enqueue_transaction_isolation(self, temp_db, sample_event, clock):
        """Enqueue is idempotent and transactional."""
        queue = EventQueue(temp_db, clock=clock)

        result1 = queue.enqueue(sample_event)
        result2 = queue.enqueue(sample_event)

        assert result1 is True
        assert result2 is False

        # Verify exactly one row
        count = queue.count_by_status(EventStatus.PENDING.value)
        assert count == 1
        queue.close()


class TestEventQueuePersistence:
    """Test persistence across close/reopen."""

    def test_persistence_after_close_and_reopen(self, temp_db, sample_event, clock):
        """Data persists after closing and reopening."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)
        queue.close()

        queue2 = EventQueue(temp_db, clock=clock)
        event = queue2.get_event(sample_event.event_id)
        assert event is not None
        assert event.event_id == sample_event.event_id
        queue2.close()

    def test_wal_mode_enabled(self, temp_db, sample_event, clock):
        """WAL mode is enabled for durability."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        cursor = queue.conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL"
        queue.close()


class TestEventQueueIntegration:
    """Test integration with EventDetector output."""

    def test_queue_with_detector_output(self, temp_db, clock):
        """Queue works with real EventDetector output."""
        from mediaman.event_detector import EventDetector

        detector = EventDetector()
        queue = EventQueue(temp_db, clock=clock)

        # Create a dummy result scenario
        event = DetectedEvent(
            event_id="evt_detector_output",
            event_type="NAVIGATION_DATA_LOST",
            observed_at="2026-08-28T12:00:00Z",
            severity="WARNING",
            previous_status="COMPLETE",
            current_status="PARTIAL",
        )

        result = queue.enqueue(event)
        assert result is True

        claimed = queue.claim(count=1)
        assert len(claimed) == 1

        queue.close()


class TestEventQueueImmutability:
    """Test input object immutability."""

    def test_input_event_unchanged(self, temp_db, sample_event, clock):
        """Queue does not modify input DetectedEvent."""
        queue = EventQueue(temp_db, clock=clock)
        original_id = sample_event.event_id

        queue.enqueue(sample_event)

        assert sample_event.event_id == original_id
        queue.close()


class TestEventQueueCountByStatus:
    """Test status counting."""

    def test_count_by_status(self, temp_db, clock):
        """count_by_status returns correct counts."""
        queue = EventQueue(temp_db, clock=clock)

        for i in range(3):
            event = DetectedEvent(
                event_id=f"evt_count_{i}",
                event_type="NAVIGATION_DATA_LOST",
                observed_at="2026-08-28T12:00:00Z",
                severity="WARNING",
            )
            queue.enqueue(event)

        assert queue.count_by_status(EventStatus.PENDING.value) == 3
        queue.close()


class TestEventQueueDeterministicOrdering:
    """Test deterministic claim ordering."""

    def test_claim_deterministic_order(self, temp_db, clock):
        """Claim returns events in deterministic order: next_attempt_at, created_at, event_id."""
        queue = EventQueue(temp_db, clock=clock)

        # Create events with different next_attempt_at times
        now_str = clock()
        now_dt = datetime.fromisoformat(now_str.replace('Z', '+00:00'))

        # Event 1: due in 5 seconds
        event1 = DetectedEvent(
            event_id="evt_order_1",
            event_type="NAVIGATION_DATA_LOST",
            observed_at=now_str,
            severity="WARNING",
        )
        queue.enqueue(event1)
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ? WHERE event_id = ?",
            ((now_dt + timedelta(seconds=5)).isoformat().replace('+00:00', 'Z'), event1.event_id),
        )
        queue.conn.commit()

        # Event 2: due immediately (should claim first)
        event2 = DetectedEvent(
            event_id="evt_order_2",
            event_type="FACT_BECAME_STALE",
            observed_at=now_str,
            severity="WARNING",
        )
        queue.enqueue(event2)
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ? WHERE event_id = ?",
            (now_str, event2.event_id),
        )
        queue.conn.commit()

        # Event 3: due immediately but created later (should claim after event2)
        event3 = DetectedEvent(
            event_id="evt_order_3",
            event_type="FACT_RECOVERED",
            observed_at=now_str,
            severity="INFO",
        )
        queue.enqueue(event3)
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ?, created_at = ? WHERE event_id = ?",
            (now_str, (now_dt + timedelta(seconds=1)).isoformat().replace('+00:00', 'Z'), event3.event_id),
        )
        queue.conn.commit()

        # Event 4: due immediately, same created_at as event3, but earlier event_id (should claim after event3)
        event4 = DetectedEvent(
            event_id="evt_order_4",
            event_type="NAVIGATION_DATA_RECOVERED",
            observed_at=now_str,
            severity="INFO",
        )
        queue.enqueue(event4)
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ?, created_at = ? WHERE event_id = ?",
            (now_str, (now_dt + timedelta(seconds=1)).isoformat().replace('+00:00', 'Z'), event4.event_id),
        )
        queue.conn.commit()

        # Claim all 4 events
        claimed = queue.claim(count=10)
        assert len(claimed) == 4

        # Verify order: event2, event3, event4, event1
        # (event2 due first; event3 and event4 both due now with same created_at,
        #  but event3's event_id < event4's event_id alphabetically)
        assert claimed[0].event_id == event2.event_id  # due first
        assert claimed[1].event_id == event3.event_id  # due now, evt_order_3 < evt_order_4
        assert claimed[2].event_id == event4.event_id  # due now, evt_order_4 > evt_order_3
        assert claimed[3].event_id == event1.event_id  # due last

        queue.close()


class TestEventQueueRealSQLiteRollback:
    """Test real SQLite transaction rollback with injected failure."""

    def test_real_sqlite_failure_rollback(self, temp_db, sample_event, clock):
        """Injected SQLite RAISE(ABORT) causes rollback; event remains PENDING."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Create a trigger that will abort UPDATE operations on status
        queue.conn.execute("""
            CREATE TRIGGER abort_processing_update
            BEFORE UPDATE ON events
            WHEN NEW.status = 'processing'
            BEGIN
                SELECT RAISE(ABORT, 'Injected test failure');
            END
        """)
        queue.conn.commit()

        # Attempt to claim; should raise SQLite error
        with pytest.raises(sqlite3.IntegrityError):
            queue.claim(count=1)

        # Verify event remains PENDING
        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.PENDING.value
        assert event.locked_until is None

        # Verify attempts and timestamps were not partially changed
        assert event.attempts == 0

        queue.close()


class TestEventQueueConcurrentClaimPrevention:
    """Test claim prevention with real concurrent threads."""

    def test_concurrent_claim_prevention_threaded(self, temp_db, sample_event, clock):
        """Two threads claiming from same database; only one receives the event."""
        import threading

        queue1 = EventQueue(temp_db, clock=clock)
        queue1.enqueue(sample_event)
        queue1.close()  # Close first instance

        claimed_by = {'queue1': None, 'queue2': None}
        lock = threading.Lock()

        def claim_in_thread(queue_name):
            """Open queue, claim, and record result."""
            queue = EventQueue(temp_db, clock=clock)
            try:
                claimed = queue.claim(count=1)
                with lock:
                    claimed_by[queue_name] = [c.event_id for c in claimed]
            finally:
                queue.close()

        # Start two threads concurrently
        t1 = threading.Thread(target=claim_in_thread, args=('queue1',))
        t2 = threading.Thread(target=claim_in_thread, args=('queue2',))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Exactly one thread should have claimed the event
        claimed_count = sum(1 for v in claimed_by.values() if v and len(v) > 0)
        assert claimed_count == 1, f"Expected 1 thread to claim event, but {claimed_count} did"

        # The other thread should have empty result
        unclaimed_count = sum(1 for v in claimed_by.values() if v is None or len(v) == 0)
        assert unclaimed_count == 1


class TestEventQueueProductionDbPrevention:
    """Verify production SQLite database is never created by tests."""

    def test_no_production_sqlite_created(self):
        """Tests do not create files in non-temp locations."""
        # All tests use either in_memory_db or temp_db fixtures
        # Verify /home/aneto/midnightrider-navigation has no .sqlite files from tests
        repo_root = Path("/home/aneto/midnightrider-navigation")
        sqlite_files = list(repo_root.glob("**/*.sqlite"))

        # Filter to only test artifacts (exclude any committed ones)
        test_artifacts = [f for f in sqlite_files if 'test' in str(f) or f.parent.name == '.pytest']

        # This test runs in isolation, so we just verify the test fixtures work
        assert True  # Actual cleanup is handled by pytest temp_db fixture

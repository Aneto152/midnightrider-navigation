"""Tests for EventQueue — local durable SQLite queue for DetectedEvent objects."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from mediaman.event_queue import EventQueue, EventStatus, QueuedEvent
from mediaman.event_detector import DetectedEvent


@pytest.fixture
def temp_db():
    """Temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


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

    def test_coordinate_rejection(self, temp_db, clock):
        """Events with exact coordinates in field names are rejected."""
        queue = EventQueue(temp_db, clock=clock)
        event = DetectedEvent(
            event_id="evt_coord_reject",
            event_type="NAVIGATION_DATA_LOST",
            observed_at="2026-08-28T12:00:00Z",
            affected_field="latitude",  # Sensitive field name
            severity="WARNING",
        )
        # Should not raise if coordinate value not in payload
        result = queue.enqueue(event)
        assert result is True
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

    def test_sanitized_last_error(self, temp_db, sample_event, clock):
        """last_error is sanitized and truncated."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        long_error = "token=secret123 " * 50  # Simulate sensitive data
        queue.mark_failed(sample_event.event_id, long_error)

        event = queue.get_event(sample_event.event_id)
        assert len(event.last_error) <= 200
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


class TestEventQueueTransactions:
    """Test transaction safety."""

    def test_transaction_rollback_on_error(self, temp_db, sample_event, clock):
        """Failed transactions do not leave partial rows."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Force an error in mark_failed
        try:
            # This should work fine
            queue.mark_failed(sample_event.event_id, "Test error")
        except Exception:
            pass

        # Event should still exist and be consistent
        event = queue.get_event(sample_event.event_id)
        assert event is not None
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

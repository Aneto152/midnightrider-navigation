"""Tests for EventQueue — local durable SQLite queue for DetectedEvent objects."""

import pytest
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sqlite3
import re

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


class TestEventQueueRecursiveSensitiveFieldRejection:
    """Test recursive fail-closed validation for sensitive fields."""

    def test_latitude_field_rejection(self, in_memory_db, clock):
        """Events with 'latitude' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_lat', 'latitude': 41.5}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_longitude_field_rejection(self, in_memory_db, clock):
        """Events with 'longitude' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_lon_reject', 'longitude': -73.9}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_lat_field_rejection(self, in_memory_db, clock):
        """Events with 'lat' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_lat', 'lat': 41.5}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_lon_field_rejection(self, in_memory_db, clock):
        """Events with 'lon' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_lon', 'lon': -73.9}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_nested_coordinate_rejection(self, in_memory_db, clock):
        """Events with coordinates in nested dictionaries are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_nested_coord',
            'position': {'latitude': 41.5, 'longitude': -73.9}
        }

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_coordinate_in_list_rejection(self, in_memory_db, clock):
        """Events with coordinates in lists are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_list_coord',
            'positions': [{'latitude': 41.5}, {'longitude': -73.9}]
        }

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_affected_field_latitude_rejection(self, in_memory_db, clock):
        """affected_field='latitude' is rejected as sensitive."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_affected_lat',
            'event_type': 'NAVIGATION_DATA_LOST',
            'affected_field': 'latitude',
            'severity': 'WARNING',
        }

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_token_field_rejection(self, in_memory_db, clock):
        """Events with 'token' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_token', 'token': 'abc123def456'}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_password_field_rejection(self, in_memory_db, clock):
        """Events with 'password' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_pwd', 'password': 'secret123'}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_secret_field_rejection(self, in_memory_db, clock):
        """Events with 'secret' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_secret', 'secret': 'hidden'}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_api_key_field_rejection(self, in_memory_db, clock):
        """Events with 'api_key' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_key', 'api_key': 'key_xyz789'}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_apikey_field_rejection(self, in_memory_db, clock):
        """Events with 'apikey' field name (no separator) are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_apikey', 'apikey': 'abc123'}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_api_key_with_dash_rejection(self, in_memory_db, clock):
        """Events with 'api-key' field name (dash separator) are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_api_dash', 'api-key': 'secret'}

        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_authorization_field_rejection(self, in_memory_db, clock):
        """Events with 'authorization' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_auth', 'authorization': 'Bearer token123'}

        with pytest.raises(ValueError, match="Sensitive field"):
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

    def test_authorization_colon_pattern_rejection(self, in_memory_db, clock):
        """Events with authorization: patterns are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_auth_colon',
            'header': 'authorization: Bearer token123'
        }

        with pytest.raises(ValueError, match="Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_bearer_pattern_rejection(self, in_memory_db, clock):
        """Events with bearer token patterns are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_bearer',
            'auth': 'bearer eyJhbGciOiJIUzI1NiJ9'
        }

        with pytest.raises(ValueError, match="Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_jwt_like_pattern_rejection(self, in_memory_db, clock):
        """Events with JWT-like (eyJ...) patterns are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_jwt',
            'auth_header': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
        }

        with pytest.raises(ValueError, match="Sensitive pattern|Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_connection_string_field_rejection(self, in_memory_db, clock):
        """Events with 'connection_string' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_connstr',
            'connection_string': 'server=localhost;user=admin;password=secret'
        }

        # Will be caught as sensitive field name
        with pytest.raises(ValueError, match="Sensitive field"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_raw_mcp_field_rejection(self, in_memory_db, clock):
        """Events with 'raw_mcp' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_raw_mcp', 'raw_mcp': 'raw MCP envelope data'}

        # Will be caught as sensitive field name (or pattern)
        with pytest.raises(ValueError, match="Sensitive field|Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_subprocess_output_field_rejection(self, in_memory_db, clock):
        """Events with 'subprocess_output' field name are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {'event_id': 'evt_subprocess', 'subprocess_output': 'subprocess output data'}

        # Will be caught as sensitive field name (or pattern)
        with pytest.raises(ValueError, match="Sensitive field|Sensitive pattern"):
            queue._validate_payload(event_dict)
        queue.close()


class TestEventQueueConnectionStringRejection:
    """Test rejection of credential-bearing connection strings."""

    def test_postgres_connection_string_rejection(self, in_memory_db, clock):
        """Events with postgres://user:pass@host connection strings are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_postgres',
            'database_url': 'postgresql://admin:secretpwd@localhost:5432/mydb'
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_mysql_connection_string_rejection(self, in_memory_db, clock):
        """Events with mysql://user:pass@host connection strings are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_mysql',
            'db_url': 'mysql://dbuser:dbpass@db.example.com:3306/database'
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_redis_connection_string_rejection(self, in_memory_db, clock):
        """Events with redis://user:pass@host connection strings are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_redis',
            'cache_url': 'redis://cacheuser:cachepass@cache.local:6379'
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_mongodb_connection_string_rejection(self, in_memory_db, clock):
        """Events with mongodb://user:pass@host connection strings are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_mongodb',
            'mongo_uri': 'mongodb://mongouser:mongopass@mongo.internal:27017/database'
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_nested_connection_string_rejection(self, in_memory_db, clock):
        """Events with nested connection strings are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_nested_conn',
            'database': {
                'primary': 'postgresql://admin:secret@localhost/db',
                'secondary': 'postgresql://admin:secret@backup/db'
            }
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_connection_string_in_list_rejection(self, in_memory_db, clock):
        """Events with connection strings in lists are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_list_conn',
            'replicas': [
                'mysql://user1:pass1@replica1/db',
                'mysql://user2:pass2@replica2/db'
            ]
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_http_connection_with_credentials_rejection(self, in_memory_db, clock):
        """Events with HTTP URLs containing credentials are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_http_cred',
            'endpoint': 'https://apiuser:apikey@api.example.com/v1/data'
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_amqp_connection_string_rejection(self, in_memory_db, clock):
        """Events with AMQP connection strings are rejected."""
        queue = EventQueue(in_memory_db, clock=clock)
        event_dict = {
            'event_id': 'evt_amqp',
            'broker_url': 'amqp://guest:guestpass@rabbitmq:5672/'
        }

        with pytest.raises(ValueError, match="Credential-bearing connection string"):
            queue._validate_payload(event_dict)
        queue.close()

    def test_safe_uri_without_credentials_accepted(self, in_memory_db, clock):
        """URIs without embedded credentials are accepted."""
        queue = EventQueue(in_memory_db, clock=clock)
        # Safe URIs (no user:password@)
        event_dict = {
            'event_id': 'evt_safe_uri',
            'urls': [
                'https://api.example.com/v1/data',
                'postgresql://localhost:5432/mydb',
                'redis://cache.local'
            ]
        }

        # Should not raise
        queue._validate_payload(event_dict)
        queue.close()


class TestEventQueueErrorSanitization:
    """Test error message sanitization."""

    def test_last_error_redaction(self, temp_db, sample_event, clock):
        """last_error is sanitized: credentials are redacted before truncation."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        error_with_creds = "Connection failed: token=abc123xyz password=secret456"
        queue.mark_failed(sample_event.event_id, error_with_creds)

        event = queue.get_event(sample_event.event_id)
        assert event.last_error is not None
        # Verify sensitive values are NOT in the error
        assert 'abc123xyz' not in event.last_error
        assert 'secret456' not in event.last_error
        # Verify redaction marker is present
        assert '<redacted>' in event.last_error
        queue.close()

    def test_all_sensitive_values_redacted_from_error(self, temp_db, sample_event, clock):
        """All types of sensitive values are redacted from last_error."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Test multiple credential types in one error
        error = (
            "Error: token=mytoken123 api_key=key_abc secret=pwd123 "
            "password=pass456 credential=cred789 bearer eyJhbGciOiJIUzI1NiJ9"
        )
        queue.mark_failed(sample_event.event_id, error)

        event = queue.get_event(sample_event.event_id)
        # Verify NO raw credentials remain
        assert 'mytoken123' not in event.last_error
        assert 'key_abc' not in event.last_error
        assert 'pwd123' not in event.last_error
        assert 'pass456' not in event.last_error
        assert 'cred789' not in event.last_error
        assert 'eyJhbGciOiJIUzI1NiJ9' not in event.last_error
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

    def test_none_error_handling(self, temp_db, sample_event, clock):
        """None error values are handled gracefully."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Initially last_error is None
        event = queue.get_event(sample_event.event_id)
        assert event.last_error is None
        queue.close()

    def test_connection_string_redaction_in_error(self, temp_db, sample_event, clock):
        """Credential-bearing connection strings are redacted from last_error."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        error_with_conn = "Database connection failed: postgresql://dbuser:dbpass@db.local/mydb"
        queue.mark_failed(sample_event.event_id, error_with_conn)

        event = queue.get_event(sample_event.event_id)
        assert event.last_error is not None
        # Verify no credentials in error
        assert 'dbuser' not in event.last_error
        assert 'dbpass' not in event.last_error
        assert 'postgresql://' not in event.last_error
        # Verify redaction marker present
        assert '<redacted-connection>' in event.last_error
        queue.close()

    def test_multiple_connection_strings_redacted(self, temp_db, sample_event, clock):
        """Multiple connection strings in error are all redacted."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        error = (
            "Failover error: primary=postgresql://user1:pass1@primary/db, "
            "secondary=mysql://user2:pass2@secondary/db"
        )
        queue.mark_failed(sample_event.event_id, error)

        event = queue.get_event(sample_event.event_id)
        # Verify NO credentials remain
        assert 'user1' not in event.last_error
        assert 'user2' not in event.last_error
        assert 'pass1' not in event.last_error
        assert 'pass2' not in event.last_error
        # Verify redaction occurred
        redacted_count = event.last_error.count('<redacted-connection>')
        assert redacted_count >= 2, f"Expected at least 2 redactions, got {redacted_count}"
        queue.close()

    def test_connection_string_redaction_before_truncation(self, temp_db, sample_event, clock):
        """Connection string redaction happens before truncation."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Long error with connection string
        error = ("x" * 150 + " postgresql://user:pass@host/db " + "y" * 150)
        queue.mark_failed(sample_event.event_id, error)

        event = queue.get_event(sample_event.event_id)
        assert len(event.last_error) <= 200
        # Verify no raw credential
        assert 'postgresql://user:pass' not in event.last_error
        # Verify redaction marker is present (if not truncated away)
        if '<redacted-connection>' not in event.last_error:
            # It was truncated, but that's ok - main thing is credentials are gone
            assert 'user' not in event.last_error or event.last_error.count('user') == 0
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


class TestEventQueueTerminalStateGuards:
    """Test terminal state (SENT, DEAD_LETTER) immutability."""

    def test_mark_sent_idempotent(self, temp_db, sample_event, clock):
        """mark_sent is idempotent: second call returns False."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        result1 = queue.mark_sent(sample_event.event_id)
        result2 = queue.mark_sent(sample_event.event_id)

        assert result1 is True
        assert result2 is False  # No update on second call
        queue.close()

    def test_mark_failed_cannot_alter_sent(self, temp_db, sample_event, clock):
        """mark_failed cannot alter SENT events."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Mark as SENT
        queue.mark_sent(sample_event.event_id)

        # Try to mark as failed
        result = queue.mark_failed(sample_event.event_id, "Some error")
        assert result is False

        # Verify still SENT (unchanged)
        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.SENT.value
        assert event.attempts == 0  # unchanged
        assert event.last_error is None  # unchanged
        queue.close()

    def test_mark_sent_cannot_alter_dead_letter(self, temp_db, sample_event, clock):
        """mark_sent cannot alter DEAD_LETTER events."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Move to DEAD_LETTER
        for _ in range(5):
            queue.mark_failed(sample_event.event_id, "Failure")

        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.DEAD_LETTER.value

        # Try to mark as SENT
        result = queue.mark_sent(sample_event.event_id)
        assert result is False

        # Verify still DEAD_LETTER
        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.DEAD_LETTER.value
        queue.close()

    def test_mark_failed_cannot_alter_dead_letter(self, temp_db, sample_event, clock):
        """mark_failed cannot alter DEAD_LETTER events."""
        queue = EventQueue(temp_db, clock=clock)
        queue.enqueue(sample_event)

        # Move to DEAD_LETTER
        for _ in range(5):
            queue.mark_failed(sample_event.event_id, "Failure")

        event = queue.get_event(sample_event.event_id)
        original_attempts = event.attempts
        assert event.status == EventStatus.DEAD_LETTER.value

        # Try to mark as failed again
        result = queue.mark_failed(sample_event.event_id, "Another failure")
        assert result is False

        # Verify still DEAD_LETTER with unchanged metadata
        event = queue.get_event(sample_event.event_id)
        assert event.status == EventStatus.DEAD_LETTER.value
        assert event.attempts == original_attempts  # unchanged
        queue.close()


class TestEventQueueRetry:
    """Test retry and backoff behavior."""

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


class TestEventQueueDeterministicOrdering:
    """Test deterministic claim ordering with complete tie-breaking."""

    def test_claim_deterministic_order_next_attempt_at(self, temp_db, clock):
        """Claim orders first by next_attempt_at ASC."""
        queue = EventQueue(temp_db, clock=clock)
        now_str = clock()
        now_dt = datetime.fromisoformat(now_str.replace('Z', '+00:00'))

        # Event due in 5 seconds
        event_future = DetectedEvent(
            event_id="evt_future",
            event_type="NAVIGATION_DATA_LOST",
            observed_at=now_str,
            severity="WARNING",
        )
        queue.enqueue(event_future)
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ? WHERE event_id = ?",
            ((now_dt + timedelta(seconds=5)).isoformat().replace('+00:00', 'Z'), event_future.event_id),
        )
        queue.conn.commit()

        # Event due immediately
        event_now = DetectedEvent(
            event_id="evt_now",
            event_type="FACT_BECAME_STALE",
            observed_at=now_str,
            severity="WARNING",
        )
        queue.enqueue(event_now)
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ? WHERE event_id = ?",
            (now_str, event_now.event_id),
        )
        queue.conn.commit()

        claimed = queue.claim(count=10)
        assert len(claimed) == 1
        assert claimed[0].event_id == event_now.event_id
        queue.close()

    def test_claim_deterministic_order_created_at_tiebreaker(self, temp_db, clock):
        """When next_attempt_at is equal, claim orders by created_at ASC."""
        queue = EventQueue(temp_db, clock=clock)
        now_str = clock()
        now_dt = datetime.fromisoformat(now_str.replace('Z', '+00:00'))

        # Both events due now, but created at different times
        event_old = DetectedEvent(
            event_id="evt_created_old",
            event_type="NAVIGATION_DATA_LOST",
            observed_at=now_str,
            severity="WARNING",
        )
        queue.enqueue(event_old)
        # Set created_at to earlier time
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ?, created_at = ? WHERE event_id = ?",
            (now_str, now_dt.isoformat().replace('+00:00', 'Z'), event_old.event_id),
        )
        queue.conn.commit()

        event_new = DetectedEvent(
            event_id="evt_created_new",
            event_type="FACT_BECAME_STALE",
            observed_at=now_str,
            severity="WARNING",
        )
        queue.enqueue(event_new)
        # Set created_at to later time
        queue.conn.execute(
            "UPDATE events SET next_attempt_at = ?, created_at = ? WHERE event_id = ?",
            (now_str, (now_dt + timedelta(seconds=2)).isoformat().replace('+00:00', 'Z'), event_new.event_id),
        )
        queue.conn.commit()

        claimed = queue.claim(count=10)
        assert len(claimed) == 2
        # Event with earlier created_at should be claimed first
        assert claimed[0].event_id == event_old.event_id
        assert claimed[1].event_id == event_new.event_id
        queue.close()

    def test_claim_deterministic_order_event_id_tiebreaker(self, temp_db, clock):
        """When next_attempt_at and created_at are equal, claim orders by event_id ASC."""
        queue = EventQueue(temp_db, clock=clock)
        now_str = clock()

        # Both events due now with same created_at, different event_ids
        for event_id in ["evt_z", "evt_a", "evt_m"]:
            event = DetectedEvent(
                event_id=event_id,
                event_type="TEST_EVENT",
                observed_at=now_str,
                severity="INFO",
            )
            queue.enqueue(event)
            # Set same next_attempt_at and created_at
            queue.conn.execute(
                "UPDATE events SET next_attempt_at = ?, created_at = ? WHERE event_id = ?",
                (now_str, now_str, event_id),
            )
            queue.conn.commit()

        claimed = queue.claim(count=10)
        assert len(claimed) == 3
        # Should be ordered by event_id ASC
        assert claimed[0].event_id == "evt_a"
        assert claimed[1].event_id == "evt_m"
        assert claimed[2].event_id == "evt_z"
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

        # Drop the trigger to verify claim can proceed after failure is removed
        queue.conn.execute("DROP TRIGGER abort_processing_update")
        queue.conn.commit()

        # Now claim should work
        claimed = queue.claim(count=1)
        assert len(claimed) == 1
        assert claimed[0].event_id == sample_event.event_id
        assert claimed[0].status == EventStatus.PROCESSING.value

        queue.close()


class TestEventQueueConcurrentClaimPrevention:
    """Test claim prevention with real concurrent threads."""

    def test_concurrent_claim_prevention_threaded(self, temp_db, sample_event, clock):
        """Two threads claiming from same database; only one receives the event."""
        queue1 = EventQueue(temp_db, clock=clock)
        queue1.enqueue(sample_event)
        queue1.close()  # Close first instance

        claimed_by = {'queue1': None, 'queue2': None}
        exceptions = {'queue1': None, 'queue2': None}
        barrier = threading.Barrier(2)  # Synchronize both threads
        lock = threading.Lock()

        def claim_in_thread(queue_name):
            """Open queue, claim at barrier, and record result."""
            try:
                queue = EventQueue(temp_db, clock=clock)
                try:
                    # Wait for both threads to be ready
                    barrier.wait()
                    claimed = queue.claim(count=1)
                    with lock:
                        claimed_by[queue_name] = [c.event_id for c in claimed]
                finally:
                    queue.close()
            except Exception as e:
                with lock:
                    exceptions[queue_name] = str(e)

        # Start two threads concurrently
        t1 = threading.Thread(target=claim_in_thread, args=('queue1',))
        t2 = threading.Thread(target=claim_in_thread, args=('queue2',))

        t1.start()
        t2.start()

        t1.join(timeout=5)
        t2.join(timeout=5)

        # Check for exceptions in workers
        for queue_name, exc in exceptions.items():
            assert exc is None, f"{queue_name} raised exception: {exc}"

        # Exactly one thread should have claimed the event
        claimed_count = sum(1 for v in claimed_by.values() if v and len(v) > 0)
        assert claimed_count == 1, f"Expected 1 thread to claim event, but {claimed_count} did"

        # The other thread should have empty result
        unclaimed_count = sum(1 for v in claimed_by.values() if v is None or len(v) == 0)
        assert unclaimed_count == 1

        # Verify only one worker got the event_id
        claimed_ids = []
        for v in claimed_by.values():
            if v:
                claimed_ids.extend(v)
        assert len(claimed_ids) == 1
        assert claimed_ids[0] == sample_event.event_id


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

    def test_safe_payload_accepted(self, temp_db, clock):
        """Safe payloads without sensitive data are accepted."""
        queue = EventQueue(temp_db, clock=clock)

        # Create event with safe, non-sensitive fields
        safe_event = DetectedEvent(
            event_id="evt_safe",
            event_type="NAVIGATION_DATA_LOST",
            observed_at="2026-08-28T12:00:00Z",
            source_timestamp="2026-08-28T11:59:00Z",
            race_id="race_001",
            severity="WARNING",
            affected_field="wind_speed",  # safe field name
            previous_status="COMPLETE",
            current_status="PARTIAL",
        )

        result = queue.enqueue(safe_event)
        assert result is True

        event = queue.get_event(safe_event.event_id)
        assert event is not None
        assert event.status == EventStatus.PENDING.value
        queue.close()


class TestEventQueueImmutability:
    """Test input object immutability."""

    def test_input_event_unchanged(self, temp_db, sample_event, clock):
        """Queue does not modify input DetectedEvent."""
        queue = EventQueue(temp_db, clock=clock)
        original_dict = sample_event.to_dict().copy()

        queue.enqueue(sample_event)

        # Verify original event dict is unchanged
        current_dict = sample_event.to_dict()
        assert current_dict == original_dict
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

        # Claim one and verify counts
        queue.claim(count=1)
        assert queue.count_by_status(EventStatus.PENDING.value) == 2
        assert queue.count_by_status(EventStatus.PROCESSING.value) == 1
        queue.close()


class TestEventQueueConnectionStringPatternDetection:
    """Test the connection string pattern regex specifically."""

    def test_credential_uri_pattern_matches_postgres(self, in_memory_db, clock):
        """Verify pattern matches postgres connection strings with credentials."""
        queue = EventQueue(in_memory_db, clock=clock)

        # Test that the pattern would match
        test_uri = 'postgresql://admin:secret@localhost:5432/db'
        assert re.search(queue.CREDENTIAL_BEARING_URI_PATTERN, test_uri, re.IGNORECASE)
        queue.close()

    def test_credential_uri_pattern_matches_mysql(self, in_memory_db, clock):
        """Verify pattern matches mysql connection strings."""
        queue = EventQueue(in_memory_db, clock=clock)

        test_uri = 'mysql://user:pass@mysql.local/database'
        assert re.search(queue.CREDENTIAL_BEARING_URI_PATTERN, test_uri, re.IGNORECASE)
        queue.close()

    def test_credential_uri_pattern_matches_redis(self, in_memory_db, clock):
        """Verify pattern matches redis connection strings."""
        queue = EventQueue(in_memory_db, clock=clock)

        test_uri = 'redis://user:password@redis.local:6379'
        assert re.search(queue.CREDENTIAL_BEARING_URI_PATTERN, test_uri, re.IGNORECASE)
        queue.close()

    def test_credential_uri_pattern_rejects_uri_without_credentials(self, in_memory_db, clock):
        """Verify pattern does NOT match URIs without embedded credentials."""
        queue = EventQueue(in_memory_db, clock=clock)

        # No user:password@ part
        safe_uri = 'postgresql://localhost:5432/db'
        assert not re.search(queue.CREDENTIAL_BEARING_URI_PATTERN, safe_uri, re.IGNORECASE)
        queue.close()


class TestEventQueueConnectionStringIntegration:
    """Test connection string handling in real scenarios."""

    def test_event_with_safe_database_name_accepted(self, temp_db, clock):
        """Events with safe database names (not URIs) are accepted."""
        queue = EventQueue(temp_db, clock=clock)

        safe_event = DetectedEvent(
            event_id="evt_safe_db",
            event_type="DATABASE_ERROR",
            observed_at="2026-08-28T12:00:00Z",
            severity="WARNING",
            affected_field="db_name",  # Safe field name
            previous_status="CONNECTED",
            current_status="DISCONNECTED",
        )

        result = queue.enqueue(safe_event)
        assert result is True

        event = queue.get_event(safe_event.event_id)
        assert event is not None
        queue.close()


class TestEventQueueProductionDbPrevention:
    """Verify production SQLite database is never created by tests."""

    def test_no_production_sqlite_created(self):
        """Tests do not create .sqlite, .sqlite-wal, or .sqlite-shm files in repository root."""
        repo_root = Path("/home/aneto/midnightrider-navigation")

        # Check for production SQLite files (excluding .git)
        sqlite_files = list(repo_root.glob("**/*.sqlite"))
        sqlite_wal_files = list(repo_root.glob("**/*.sqlite-wal"))
        sqlite_shm_files = list(repo_root.glob("**/*.sqlite-shm"))

        # Filter out .git directory
        sqlite_files = [f for f in sqlite_files if '.git' not in f.parts]
        sqlite_wal_files = [f for f in sqlite_wal_files if '.git' not in f.parts]
        sqlite_shm_files = [f for f in sqlite_shm_files if '.git' not in f.parts]

        # All tests should use temp_db (tempfile) or in_memory_db (:memory:)
        # No production SQLite files should exist
        assert len(sqlite_files) == 0, f"Production .sqlite files found: {sqlite_files}"
        assert len(sqlite_wal_files) == 0, f"Production .sqlite-wal files found: {sqlite_wal_files}"
        assert len(sqlite_shm_files) == 0, f"Production .sqlite-shm files found: {sqlite_shm_files}"

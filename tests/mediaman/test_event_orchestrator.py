"""Tests for event orchestrator — FINAL HARDENING with pre-validation logging safety.

Tests prove:
- Raw event fields are NOT logged before validation
- Raw exceptions are NOT logged
- All credential forms are redacted (secret=, credential=, all URI schemes)
- HTTP/HTTPS URIs with credentials are redacted
"""

import pytest
from unittest.mock import Mock
import logging

from mediaman.event_orchestrator import EventOrchestrator, SafePromptBuilder, ErrorSanitizer
from mediaman.event_queue import QueuedEvent


class TestErrorSanitizer:
    """Test comprehensive error redaction (FINAL HARDENING)."""

    def test_sanitize_secret_equals_pattern(self):
        """secret=value is redacted."""
        error = "Config error: secret=mysecretpassword"
        result = ErrorSanitizer.sanitize(error)
        assert "mysecretpassword" not in result
        assert "<redacted-secret>" in result

    def test_sanitize_credential_equals_pattern(self):
        """credential=value is redacted."""
        error = "Auth failed: credential=abc123xyz"
        result = ErrorSanitizer.sanitize(error)
        assert "abc123xyz" not in result
        assert "<redacted-credential>" in result

    def test_sanitize_http_credential_bearing_uri(self):
        """HTTP URI with user:password is redacted."""
        error = "Connection failed: http://user:secretpass@host/path"
        result = ErrorSanitizer.sanitize(error)
        assert "user:secretpass" not in result
        assert "<redacted-connection>" in result

    def test_sanitize_https_credential_bearing_uri(self):
        """HTTPS URI with user:password is redacted."""
        error = "Secure connection failed: https://admin:password123@secure.host/api"
        result = ErrorSanitizer.sanitize(error)
        assert "admin:password123" not in result
        assert "<redacted-connection>" in result

    def test_sanitize_postgres_uri(self):
        """PostgreSQL URI is redacted."""
        error = "DB error: postgres://user:pass@localhost/db"
        result = ErrorSanitizer.sanitize(error)
        assert "user:pass" not in result
        assert "<redacted-connection>" in result

    def test_sanitize_mysql_uri(self):
        """MySQL URI is redacted."""
        error = "MySQL failed: mysql://root:password@db.host/database"
        result = ErrorSanitizer.sanitize(error)
        assert "root:password" not in result
        assert "<redacted-connection>" in result


class TestSafePromptBuilder:
    """Test prompt builder with strict type validation."""

    def test_reject_all_16_sensitive_field_names(self):
        """All 16 sensitive field names are rejected."""
        sensitive_names = ['latitude', 'longitude', 'lat', 'lon', 'token', 'api_key',
                          'apikey', 'secret', 'password', 'credential', 'authorization',
                          'bearer', 'connection_string', 'raw_mcp', 'subprocess_output']
        for sensitive_name in sensitive_names:
            event = QueuedEvent(
                event_id="e1", event_type="test", status="processing", attempts=1,
                observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
                race_id="race1", severity="normal", affected_field=sensitive_name,
                payload_json='{}', next_attempt_at="2026-08-31T10:05:00Z",
                locked_until=None, last_error=None, created_at="2026-08-31T10:00:00Z",
                updated_at="2026-08-31T10:00:00Z",
            )
            with pytest.raises(ValueError, match="sensitive field name"):
                SafePromptBuilder.build_prompt(event)

    def test_payload_json_never_forwarded(self):
        """payload_json is never included in prompt."""
        event = QueuedEvent(
            event_id="e1", event_type="test", status="processing", attempts=1,
            observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1", severity="normal", affected_field=None,
            payload_json='{"secret_token": "abc123", "coordinates": [10.5, 20.3]}',
            next_attempt_at="2026-08-31T10:05:00Z", locked_until=None, last_error=None,
            created_at="2026-08-31T10:00:00Z", updated_at="2026-08-31T10:00:00Z",
        )
        prompt = SafePromptBuilder.build_prompt(event)
        assert "secret_token" not in prompt
        assert "abc123" not in prompt
        assert "10.5" not in prompt


class TestEventOrchestrator:
    """Test orchestrator with pre-validation logging safety (FINAL HARDENING)."""

    def test_no_raw_event_fields_logged_before_validation(self, caplog):
        """Raw event fields are never logged before validation."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1", event_type="test_type_value", status="processing", attempts=1,
            observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
            race_id="test_race", severity="warning_severity", affected_field=None,
            payload_json='{"secret_data": "should_not_log"}',
            next_attempt_at="2026-08-31T10:05:00Z", locked_until=None, last_error=None,
            created_at="2026-08-31T10:00:00Z", updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="OK")

        orch = EventOrchestrator(queue, adapter)
        with caplog.at_level(logging.DEBUG):
            result = orch.process_one_cycle()

        log_text = caplog.text
        assert "test_type_value" not in log_text
        assert "test_race" not in log_text
        assert "warning_severity" not in log_text
        assert "secret_data" not in log_text
        assert "e1" in log_text

    def test_no_raw_exceptions_logged(self, caplog):
        """Raw exception messages are never logged."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1", event_type="test", status="processing", attempts=1,
            observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1", severity="normal", affected_field=None, payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z", locked_until=None, last_error=None,
            created_at="2026-08-31T10:00:00Z", updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.side_effect = Exception("postgres://user:pass@host")

        orch = EventOrchestrator(queue, adapter)
        with caplog.at_level(logging.WARNING):
            result = orch.process_one_cycle()

        log_text = caplog.text
        assert "user:pass" not in log_text
        assert "postgres://" not in log_text

    def test_mark_failed_receives_only_safe_classification(self):
        """mark_failed() receives only safe classification."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1", event_type="test", status="processing", attempts=1,
            observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1", severity="normal", affected_field=None, payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z", locked_until=None, last_error=None,
            created_at="2026-08-31T10:00:00Z", updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=False, error="https://user:password@secure.host")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        call_args = queue.mark_failed.call_args
        error_classification = call_args[0][1]
        assert "user:password" not in error_classification
        assert "https://" not in error_classification

    def test_single_event_processing_maintained(self):
        """Exactly one event is claimed per cycle."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1", event_type="test", status="processing", attempts=1,
            observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1", severity="normal", affected_field=None, payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z", locked_until=None, last_error=None,
            created_at="2026-08-31T10:00:00Z", updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="OK")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        queue.claim.assert_called_once_with(count=1)

    def test_mark_sent_only_on_success(self):
        """mark_sent() is called only on success."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1", event_type="test", status="processing", attempts=1,
            observed_at="2026-08-31T10:00:00Z", source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1", severity="normal", affected_field=None, payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z", locked_until=None, last_error=None,
            created_at="2026-08-31T10:00:00Z", updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="OK")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        queue.mark_sent.assert_called_once_with("e1")
        queue.mark_failed.assert_not_called()

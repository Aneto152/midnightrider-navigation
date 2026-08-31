"""Tests for event orchestrator — single-event processing, safe prompts, state transitions."""

import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from mediaman.event_orchestrator import EventOrchestrator, SafePromptBuilder, OrchestratorResult
from mediaman.event_queue import QueuedEvent


class TestSafePromptBuilder:
    """Test safe prompt construction from allowlisted fields only."""

    def test_build_prompt_with_all_fields(self):
        """Prompt includes all allowlisted fields."""
        event = QueuedEvent(
            event_id="e1",
            event_type="gps_dropout",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="stamford_ct",
            severity="warning",
            affected_field="signal_strength",
            payload_json='{"ignored": "completely"}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        prompt = SafePromptBuilder.build_prompt(event)
        assert "gps_dropout" in prompt
        assert "stamford_ct" in prompt
        assert "warning" in prompt
        assert "signal_strength" in prompt
        # Verify payload_json is never forwarded
        assert "ignored" not in prompt

    def test_build_prompt_excludes_forbidden_affected_field(self):
        """affected_field with sensitive name is excluded."""
        event = QueuedEvent(
            event_id="e1",
            event_type="data_anomaly",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="critical",
            affected_field="latitude",  # FORBIDDEN
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        prompt = SafePromptBuilder.build_prompt(event)
        # latitude should not appear as affected_field
        assert "Champ affecté:" not in prompt or "latitude" not in prompt.split("Champ affecté:")[-1]

    def test_build_prompt_with_none_fields(self):
        """prompt builder handles None values gracefully."""
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id=None,
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        prompt = SafePromptBuilder.build_prompt(event)
        assert "unspecified" in prompt or "test" in prompt

    def test_validate_prompt_input_requires_safe_fields(self):
        """validate_prompt_input checks required safe fields."""
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        assert SafePromptBuilder.validate_prompt_input(event)

    def test_prompt_never_mutates_queued_event(self):
        """Prompt construction never modifies the QueuedEvent."""
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field="field1",
            payload_json='{"data": "value"}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        original_payload = event.payload_json
        SafePromptBuilder.build_prompt(event)
        assert event.payload_json == original_payload


class TestEventOrchestrator:
    """Test event orchestration: claim, prompt, adapt, state-transition."""

    def test_process_one_cycle_no_events_available(self):
        """No-work cycle when no events available."""
        queue = Mock()
        adapter = Mock()
        queue.claim.return_value = []

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        assert result.success is False
        assert result.error == "no_events_available"
        assert result.event_id is None
        adapter.generate_article.assert_not_called()

    def test_process_one_cycle_single_event_claimed(self):
        """Exactly one event is processed per cycle."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test_event",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="Test content")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        assert result.success is True
        assert result.event_id == "e1"
        queue.claim.assert_called_once_with(count=1)
        queue.mark_sent.assert_called_once_with("e1")
        adapter.generate_article.assert_called_once()

    def test_process_one_cycle_mark_sent_on_success(self):
        """mark_sent() is called only after successful adapter result."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="Content")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        assert result.state_transition == "mark_sent"
        queue.mark_sent.assert_called_once()

    def test_process_one_cycle_mark_failed_on_adapter_failure(self):
        """mark_failed() is called on adapter failure."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=False, error="timeout")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        assert result.success is False
        assert result.state_transition == "mark_failed"
        queue.mark_failed.assert_called_once_with("e1", "adapter: timeout")

    def test_process_one_cycle_adapter_unavailable(self):
        """Orchestrator handles adapter unavailability gracefully."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=False, error="unavailable", provider_status="unavailable")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        queue.mark_failed.assert_called_once()
        queue.mark_sent.assert_not_called()

    def test_process_one_cycle_payload_json_never_forwarded(self):
        """payload_json is never passed to adapter."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{"secret_token": "abc123"}',  # Should be excluded
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="OK")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        # Verify adapter was called with prompt, not payload_json
        call_args = adapter.generate_article.call_args
        prompt = call_args.kwargs.get("prompt") or call_args.args[0]
        assert "secret_token" not in prompt
        assert "abc123" not in prompt

    def test_retry_ownership_eventqueue_only(self):
        """EventQueue owns retry scheduling; Orchestrator does not retry."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=False, error="timeout")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        # Verify only one mark_failed call, no retry loop
        queue.mark_failed.assert_called_once()
        queue.claim.assert_called_once()

    def test_state_transition_ownership_orchestrator(self):
        """Orchestrator owns mark_sent and mark_failed, not adapter."""
        queue = Mock()
        adapter = Mock()
        event = QueuedEvent(
            event_id="e1",
            event_type="test",
            status="processing",
            attempts=1,
            observed_at="2026-08-31T10:00:00Z",
            source_timestamp="2026-08-31T10:00:00Z",
            race_id="race1",
            severity="normal",
            affected_field=None,
            payload_json='{}',
            next_attempt_at="2026-08-31T10:05:00Z",
            locked_until=None,
            last_error=None,
            created_at="2026-08-31T10:00:00Z",
            updated_at="2026-08-31T10:00:00Z",
        )
        queue.claim.return_value = [event]
        adapter.generate_article.return_value = Mock(success=True, content="Content")

        orch = EventOrchestrator(queue, adapter)
        result = orch.process_one_cycle()

        # Orchestrator calls mark_sent, not adapter
        queue.mark_sent.assert_called_once()

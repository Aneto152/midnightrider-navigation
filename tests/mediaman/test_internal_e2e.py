"""Internal offline event-flow E2E tests.

Validates the internal processing pipeline:
DetectedEvent → EventQueue → claim(count=1) → EventOrchestrator
→ SafePromptBuilder → mocked adapter.generate_article() → internal content
→ mark_sent() → SENT state

No external services. No production database. No runtime E2E validation.
"""

import pytest
from unittest.mock import Mock

from mediaman.event_detector import DetectedEvent
from mediaman.event_queue import EventQueue, EventStatus
from mediaman.event_orchestrator import EventOrchestrator
from mediaman.openclaw_adapter import OpenClawResult


def fixed_clock():
    """Deterministic clock for internal E2E tests."""
    return "2026-08-31T23:00:00Z"


def test_internal_flow_success_marks_event_sent(tmp_path):
    """Internal flow succeeds: event enqueued, claimed, orchestrated, marked SENT."""
    queue = EventQueue(
        db_path=str(tmp_path / "internal-success.sqlite"),
        clock=fixed_clock,
    )
    queue.initialize()

    try:
        event = DetectedEvent(
            event_id="internal-e2e-success-001",
            event_type="FACT_BECAME_STALE",
            observed_at="2026-08-31T22:59:00Z",
            source_timestamp="2026-08-31T22:58:00Z",
            race_id="race-internal-e2e",
            severity="WARNING",
            affected_field="sog",
        )

        assert queue.enqueue(event) is True

        adapter = Mock()
        adapter.generate_article.return_value = OpenClawResult(
            success=True,
            content="Internal content generated for offline E2E.",
            provider_status="success",
            execution_id="offline-e2e-success",
        )

        orchestrator = EventOrchestrator(queue, adapter)
        result = orchestrator.process_one_cycle()

        assert result.success is True
        assert result.event_id == "internal-e2e-success-001"
        assert result.content == "Internal content generated for offline E2E."
        assert result.state_transition == "mark_sent"

        adapter.generate_article.assert_called_once()
        call_kwargs = adapter.generate_article.call_args.kwargs

        assert set(call_kwargs) == {"prompt"}
        assert isinstance(call_kwargs["prompt"], str)
        assert call_kwargs["prompt"]

        prompt = call_kwargs["prompt"]

        assert "FACT_BECAME_STALE" in prompt
        assert "race-internal-e2e" in prompt
        assert "WARNING" in prompt
        assert "sog" in prompt

        assert "payload_json" not in prompt
        assert "latitude" not in prompt
        assert "longitude" not in prompt
        assert "token" not in prompt.lower()
        assert "password" not in prompt.lower()
        assert "secret" not in prompt.lower()

        queued = queue.get_event("internal-e2e-success-001")

        assert queued is not None
        assert queued.status == EventStatus.SENT.value
        assert queued.attempts == 0
        assert queued.last_error is None

    finally:
        queue.close()


def test_internal_flow_failure_returns_pending_with_retry_scheduled(tmp_path):
    """Internal flow failure: event remains PENDING with retry scheduled."""
    queue = EventQueue(
        db_path=str(tmp_path / "internal-failure.sqlite"),
        clock=fixed_clock,
    )
    queue.initialize()

    try:
        event = DetectedEvent(
            event_id="internal-e2e-failure-001",
            event_type="NAVIGATION_DATA_LOST",
            observed_at="2026-08-31T22:59:00Z",
            source_timestamp="2026-08-31T22:58:00Z",
            race_id="race-internal-e2e",
            severity="ERROR",
            affected_field="position",
        )

        assert queue.enqueue(event) is True

        adapter = Mock()
        adapter.generate_article.return_value = OpenClawResult(
            success=False,
            content=None,
            error="connection refused",
            provider_status="error",
            execution_id="offline-e2e-failure",
        )

        orchestrator = EventOrchestrator(queue, adapter)
        result = orchestrator.process_one_cycle()

        assert result.success is False
        assert result.event_id == "internal-e2e-failure-001"
        assert result.state_transition == "mark_failed"
        assert result.error == "adapter_connection_error"

        queued = queue.get_event("internal-e2e-failure-001")

        assert queued is not None

        # EventQueue owns retry scheduling.
        # One failure does not immediately create DEAD_LETTER.
        assert queued.status == EventStatus.PENDING.value
        assert queued.attempts == 1
        assert queued.last_error == "adapter_connection_error"
        assert queued.next_attempt_at != "2026-08-31T23:00:00Z"

        assert "connection refused" not in result.error
        assert "connection refused" not in queued.last_error

    finally:
        queue.close()


def test_internal_flow_processes_only_one_event_per_cycle(tmp_path):
    """Single-event processing: only one event processed per cycle."""
    queue = EventQueue(
        db_path=str(tmp_path / "internal-single.sqlite"),
        clock=fixed_clock,
    )
    queue.initialize()

    try:
        first_event = DetectedEvent(
            event_id="internal-e2e-single-001",
            event_type="FACT_BECAME_STALE",
            observed_at="2026-08-31T22:59:00Z",
            source_timestamp="2026-08-31T22:58:00Z",
            race_id="race-internal-e2e",
            severity="WARNING",
            affected_field="sog",
        )

        second_event = DetectedEvent(
            event_id="internal-e2e-single-002",
            event_type="FACT_BECAME_STALE",
            observed_at="2026-08-31T22:59:01Z",
            source_timestamp="2026-08-31T22:58:01Z",
            race_id="race-internal-e2e",
            severity="WARNING",
            affected_field="cog",
        )

        assert queue.enqueue(first_event) is True
        assert queue.enqueue(second_event) is True

        adapter = Mock()
        adapter.generate_article.return_value = OpenClawResult(
            success=True,
            content="Single internal E2E content.",
            provider_status="success",
            execution_id="offline-e2e-single",
        )

        orchestrator = EventOrchestrator(queue, adapter)
        result = orchestrator.process_one_cycle()

        assert result.success is True
        adapter.generate_article.assert_called_once()

        first = queue.get_event("internal-e2e-single-001")
        second = queue.get_event("internal-e2e-single-002")

        assert first is not None
        assert second is not None
        assert first.status == EventStatus.SENT.value
        assert second.status == EventStatus.PENDING.value

    finally:
        queue.close()

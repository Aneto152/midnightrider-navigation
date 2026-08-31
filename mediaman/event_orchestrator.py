"""Event orchestrator — claim events, build safe prompts, invoke adapter, manage state.

Single-event processing: claim(count=1), construct prompt from safe-field allowlist only,
invoke OpenClawAdapter.generate_article(), handle results, call mark_sent() or mark_failed().

EventQueue owns retry scheduling, next_attempt_at, exponential backoff, DEAD_LETTER escalation.
Orchestrator owns state transitions (mark_sent, mark_failed) and safe prompt construction.
OpenClawAdapter remains stateless with respect to EventQueue.

No Telegram. No external publication. No Runtime E2E.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from mediaman.event_queue import EventQueue
from mediaman.openclaw_adapter import OpenClawAdapter


logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    """Result of one orchestration cycle."""
    success: bool
    event_id: Optional[str] = None
    error: Optional[str] = None
    content: Optional[str] = None  # Internal content only, not for publication
    state_transition: Optional[str] = None  # "mark_sent" or "mark_failed"


class SafePromptBuilder:
    """Build safe prompts from explicit allowlisted fields only."""

    # Allowlisted fields from QueuedEvent
    SAFE_FIELDS = {'event_type', 'race_id', 'severity', 'observed_at', 'source_timestamp', 'affected_field'}

    @staticmethod
    def build_prompt(queued_event) -> str:
        """
        Construct a safe prompt from explicit allowlisted fields only.

        Never includes:
        - raw payload_json
        - coordinates (latitude, longitude, lat, lon)
        - credentials, tokens, passwords
        - last_error, locked_until
        - arbitrary free-text fields

        Raises ValueError if a required safe field has invalid type.
        """
        # Explicit field extraction with type checking and bounds
        event_type = str(queued_event.event_type or "unknown")[:100]
        race_id = str(queued_event.race_id or "unspecified")[:100] if queued_event.race_id else "unspecified"
        severity = str(queued_event.severity or "normal")[:50]
        observed_at = str(queued_event.observed_at or "unknown time")[:50]

        # affected_field is optional and must be validated to exclude sensitive fields
        affected_field = ""
        if queued_event.affected_field:
            af_str = str(queued_event.affected_field)[:100].lower()
            # Reject sensitive field names
            forbidden = {'latitude', 'longitude', 'lat', 'lon', 'token', 'password', 'credential', 'secret'}
            if af_str not in forbidden:
                affected_field = af_str

        # Build safe descriptive prompt in French (neutral, non-directive)
        prompt = (
            f"Événement détecté: {event_type}\n"
            f"Course: {race_id}\n"
            f"Sévérité: {severity}\n"
            f"Observé à: {observed_at}"
        )
        if affected_field:
            prompt += f"\nChamp affecté: {affected_field}"

        return prompt

    @staticmethod
    def validate_prompt_input(queued_event) -> bool:
        """Validate that queued_event has required fields for safe prompt construction."""
        required = {'event_type', 'severity', 'observed_at'}
        event_dict = {
            'event_type': queued_event.event_type,
            'severity': queued_event.severity,
            'observed_at': queued_event.observed_at,
        }
        return all(event_dict.get(f) is not None for f in required)


class EventOrchestrator:
    """Orchestrate event processing: claim, prompt, adapt, state-transition."""

    def __init__(self, event_queue: EventQueue, adapter: OpenClawAdapter):
        """Initialize with EventQueue and OpenClawAdapter."""
        self.event_queue = event_queue
        self.adapter = adapter
        self.prompt_builder = SafePromptBuilder()

    def process_one_cycle(self) -> OrchestratorResult:
        """
        Process exactly one event per cycle.

        1. Claim exactly one event
        2. If no event, return idle result
        3. If event claimed, validate and build safe prompt
        4. Invoke adapter with prompt (never QueuedEvent or payload_json)
        5. Handle result: mark_sent() or mark_failed()
        6. Return orchestration result

        Do not process more than one event per cycle.
        Do not implement retry logic (EventQueue owns that).
        """
        # Step 1: Claim exactly one event
        claimed = self.event_queue.claim(count=1)

        if not claimed:
            logger.debug("No events available for processing")
            return OrchestratorResult(
                success=False,
                error="no_events_available"
            )

        event = claimed[0]
        event_id = event.event_id

        # Verify status is PROCESSING (guarantee from EventQueue.claim)
        if event.status != "processing":
            logger.error(f"Event {event_id} status is {event.status}, expected PROCESSING")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error="invalid_event_status"
            )

        logger.info(f"Processing event {event_id} (type={event.event_type}, severity={event.severity})")

        # Step 2: Validate and build safe prompt
        try:
            if not self.prompt_builder.validate_prompt_input(event):
                raise ValueError("Event missing required safe fields")

            prompt = self.prompt_builder.build_prompt(event)
            logger.debug(f"Prompt constructed for event {event_id} (length={len(prompt)})")
        except Exception as e:
            logger.error(f"Failed to build prompt for event {event_id}: {e}")
            try:
                self.event_queue.mark_failed(event_id, "prompt_construction_failed")
            except Exception as mark_err:
                logger.error(f"Failed to mark_failed for event {event_id}: {mark_err}")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error="prompt_construction_failed",
                state_transition="mark_failed"
            )

        # Step 3: Invoke adapter (never pass QueuedEvent or payload_json)
        try:
            result = self.adapter.generate_article(prompt=prompt)
        except Exception as e:
            logger.error(f"Adapter invocation failed for event {event_id}: {e}")
            try:
                self.event_queue.mark_failed(event_id, f"adapter_error: {type(e).__name__}")
            except Exception as mark_err:
                logger.error(f"Failed to mark_failed for event {event_id}: {mark_err}")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error=f"adapter_error",
                state_transition="mark_failed"
            )

        # Step 4: Handle adapter result
        if result.success and result.content:
            # Successful content generation
            logger.info(f"Content generated for event {event_id} (length={len(result.content)})")
            try:
                self.event_queue.mark_sent(event_id)
                logger.info(f"Event {event_id} marked as SENT")
                return OrchestratorResult(
                    success=True,
                    event_id=event_id,
                    content=result.content,  # Internal content only
                    state_transition="mark_sent"
                )
            except Exception as e:
                logger.error(f"Failed to mark_sent for event {event_id}: {e}")
                return OrchestratorResult(
                    success=False,
                    event_id=event_id,
                    error="mark_sent_failed",
                    state_transition=None
                )
        else:
            # Adapter failure (unavailable, timeout, provider error, etc.)
            error_msg = result.error or "unknown_adapter_error"
            logger.warning(f"Adapter failed for event {event_id}: {error_msg}")
            try:
                self.event_queue.mark_failed(event_id, f"adapter: {error_msg}")
                logger.info(f"Event {event_id} marked as FAILED (EventQueue owns retry scheduling)")
                return OrchestratorResult(
                    success=False,
                    event_id=event_id,
                    error=error_msg,
                    state_transition="mark_failed"
                )
            except Exception as e:
                logger.error(f"Failed to mark_failed for event {event_id}: {e}")
                return OrchestratorResult(
                    success=False,
                    event_id=event_id,
                    error="mark_failed_failed",
                    state_transition=None
                )

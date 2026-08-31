"""Event orchestrator — claim events, build safe prompts, invoke adapter, manage state.

Single-event processing: claim(count=1), construct prompt from STRICT safe-field allowlist only,
invoke OpenClawAdapter.generate_article(), handle results, call mark_sent() or mark_failed().

HARDENED: strict type validation, prompt injection resistance, error redaction before logging.

EventQueue owns retry scheduling, next_attempt_at, exponential backoff, DEAD_LETTER escalation.
Orchestrator owns state transitions (mark_sent, mark_failed) and safe prompt construction.
OpenClawAdapter remains stateless with respect to EventQueue.

No Telegram. No external publication. No Runtime E2E.
"""

import logging
import re
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
    error: Optional[str] = None  # Safe classification or sanitized value only
    content: Optional[str] = None  # Internal content only, not for publication
    state_transition: Optional[str] = None  # "mark_sent" or "mark_failed"


class ErrorSanitizer:
    """Redact sensitive values from error messages before logging or returning."""

    # Patterns to redact
    SENSITIVE_PATTERNS = [
        (r'\btoken\s*[=:]\s*[^\s,;]+', '<redacted-token>'),
        (r'\bapi[_-]?key\s*[=:]\s*[^\s,;]+', '<redacted-apikey>'),
        (r'\bpassword\s*[=:]\s*[^\s,;]+', '<redacted-password>'),
        (r'\bauthorization\s*[=:]\s*[^\s,;]+', '<redacted-auth>'),
        (r'\bbearer\s+[^\s]+', '<redacted-bearer>'),
        (r'eyJ[a-zA-Z0-9_.-]+', '<redacted-jwt>'),
        (r'(postgres|mysql|mongodb|redis|amqp)://[^\s]+', '<redacted-uri>'),
        (r'\d+\.\d+\.\d+\.\d+', '<redacted-ip>'),
    ]

    # Patterns to detect (for classification)
    CREDENTIAL_PATTERNS = [
        r'\b(token|api_?key|password|secret|credential|authorization|bearer)\b',
        r'(postgres|mysql|mongodb|redis|amqp)://',
    ]

    @staticmethod
    def sanitize(text: str, max_length: int = 100) -> str:
        """
        Redact sensitive values from text.
        Returns sanitized, bounded text safe for logging.
        """
        if not isinstance(text, str):
            return '<invalid-error-type>'

        result = text
        # Apply redaction patterns
        for pattern, replacement in ErrorSanitizer.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Remove control characters
        result = ''.join(c if ord(c) >= 32 else '?' for c in result)

        # Truncate
        if len(result) > max_length:
            result = result[:max_length - 3] + '...'

        return result

    @staticmethod
    def classify_error(error_msg: str) -> str:
        """Classify error as safe category without exposing details."""
        if not isinstance(error_msg, str):
            return 'unknown_error'

        msg_lower = error_msg.lower()
        if 'timeout' in msg_lower or 'timed' in msg_lower:
            return 'adapter_timeout'
        elif 'unavailable' in msg_lower:
            return 'adapter_unavailable'
        elif 'connection' in msg_lower or 'refused' in msg_lower:
            return 'adapter_connection_error'
        elif 'authentication' in msg_lower or 'unauthorized' in msg_lower:
            return 'adapter_auth_error'
        else:
            return 'adapter_error'


class SafePromptBuilder:
    """Build safe prompts from STRICT explicit allowlisted fields only.

    HARDENED:
    - Strict type validation (fail-closed on invalid types)
    - Prompt injection resistance (reject control chars, instruction patterns)
    - Comprehensive sensitive field coverage
    """

    # Allowlisted fields from QueuedEvent (strict types)
    SAFE_FIELDS = {'event_type', 'race_id', 'severity', 'observed_at', 'source_timestamp', 'affected_field'}

    # Comprehensive sensitive field names (case + separator normalized)
    SENSITIVE_FIELD_NAMES = {
        'latitude', 'longitude', 'lat', 'lon',
        'token', 'api_key', 'apikey', 'secret', 'password',
        'credential', 'authorization', 'bearer',
        'connection_string', 'raw_mcp', 'subprocess_output',
    }

    # Prompt injection patterns (reject these)
    INJECTION_PATTERNS = [
        r'\bignore\s+previous\s+instructions\b',
        r'\bsystem\s+message\b',
        r'\bassistant\s*:\s*',
        r'\buser\s*:\s*',
        r'\btool\s+call\b',
        r'\bexecute\s+command\b',
    ]

    MAX_FIELD_LENGTHS = {
        'event_type': 100,
        'race_id': 100,
        'severity': 50,
        'observed_at': 50,
        'source_timestamp': 50,
        'affected_field': 50,
    }

    @staticmethod
    def normalize_field_name(name: str) -> str:
        """Normalize field name: lowercase, replace separators with underscore."""
        if not isinstance(name, str):
            return ''
        return name.lower().replace('-', '_').replace(' ', '_')

    @staticmethod
    def is_sensitive_field_name(value: str) -> bool:
        """Check if string value is a sensitive field name."""
        if not isinstance(value, str):
            return False
        normalized = SafePromptBuilder.normalize_field_name(value)
        return normalized in SafePromptBuilder.SENSITIVE_FIELD_NAMES

    @staticmethod
    def reject_injection_content(value: str) -> bool:
        """Check if value contains prompt injection patterns."""
        if not isinstance(value, str):
            return False
        for pattern in SafePromptBuilder.INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def validate_field_type_and_value(field_name: str, value) -> None:
        """
        Strict type and value validation.
        Raises ValueError if validation fails.
        """
        # Type check: must be string (except optional fields which can be None)
        if field_name in {'race_id', 'source_timestamp', 'affected_field'}:
            # Optional fields
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field_name}: expected string or None, got {type(value).__name__}")
        else:
            # Required fields
            if not isinstance(value, str):
                raise ValueError(f"{field_name}: expected string, got {type(value).__name__}")
            if not value:
                raise ValueError(f"{field_name}: required field is empty")

        # If string, validate content
        if isinstance(value, str) and value:
            # Check length
            max_len = SafePromptBuilder.MAX_FIELD_LENGTHS.get(field_name, 100)
            if len(value) > max_len:
                raise ValueError(f"{field_name}: length {len(value)} exceeds max {max_len}")

            # Check for control characters
            if any(ord(c) < 32 and c not in '\t\n' for c in value):
                raise ValueError(f"{field_name}: contains control characters")

            # Check for newlines (not allowed in field values)
            if '\n' in value or '\r' in value:
                raise ValueError(f"{field_name}: contains newlines")

            # Check for injection patterns
            if SafePromptBuilder.reject_injection_content(value):
                raise ValueError(f"{field_name}: contains prompt injection pattern")

            # Check for sensitive field names (in any field)
            if SafePromptBuilder.is_sensitive_field_name(value):
                raise ValueError(f"{field_name}: contains sensitive field name '{value}'")

    @staticmethod
    def build_prompt(queued_event) -> str:
        """
        Construct a SAFE prompt from explicit allowlisted fields only.

        Raises ValueError if:
        - Required field has invalid type
        - Field value exceeds length bounds
        - Field contains control characters
        - Field contains injection patterns
        - Field contains sensitive field name
        - Field is malformed

        Never includes:
        - raw payload_json
        - coordinates (latitude, longitude, lat, lon)
        - credentials, tokens, passwords
        - last_error, locked_until
        - arbitrary free-text fields

        Fail-closed on any validation failure.
        """
        # Strict type validation for each field
        SafePromptBuilder.validate_field_type_and_value('event_type', queued_event.event_type)
        SafePromptBuilder.validate_field_type_and_value('severity', queued_event.severity)
        SafePromptBuilder.validate_field_type_and_value('observed_at', queued_event.observed_at)
        SafePromptBuilder.validate_field_type_and_value('race_id', queued_event.race_id)
        SafePromptBuilder.validate_field_type_and_value('source_timestamp', queued_event.source_timestamp)
        SafePromptBuilder.validate_field_type_and_value('affected_field', queued_event.affected_field)

        # Explicit field extraction (already validated)
        event_type = queued_event.event_type
        race_id = queued_event.race_id or "unspecified"
        severity = queued_event.severity
        observed_at = queued_event.observed_at

        # Build safe descriptive prompt in French (neutral, non-directive)
        prompt = (
            f"Événement détecté: {event_type}\n"
            f"Course: {race_id}\n"
            f"Sévérité: {severity}\n"
            f"Observé à: {observed_at}"
        )
        if queued_event.source_timestamp:
            prompt += f"\nTimestamp source: {queued_event.source_timestamp}"
        if queued_event.affected_field:
            prompt += f"\nChamp affecté: {queued_event.affected_field}"

        return prompt

    @staticmethod
    def validate_prompt_input(queued_event) -> bool:
        """Validate that queued_event has required fields for safe prompt construction."""
        required = {'event_type', 'severity', 'observed_at'}
        try:
            for field in required:
                val = getattr(queued_event, field, None)
                if val is None or (isinstance(val, str) and not val):
                    return False
            return True
        except Exception:
            return False


class EventOrchestrator:
    """Orchestrate event processing: claim, prompt, adapt, state-transition.

    HARDENED:
    - Strict type validation in safe-field builder
    - Prompt injection resistance
    - Error sanitization before logging and mark_failed()
    - No raw exceptions in logs
    """

    def __init__(self, event_queue: EventQueue, adapter: OpenClawAdapter):
        """Initialize with EventQueue and OpenClawAdapter."""
        self.event_queue = event_queue
        self.adapter = adapter
        self.prompt_builder = SafePromptBuilder()
        self.sanitizer = ErrorSanitizer()

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

        HARDENED: strict validation, error sanitization, no raw exceptions in logs.
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
            logger.warning(f"Event {event_id} has invalid status: {event.status}")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error="invalid_event_status"
            )

        logger.info(f"Processing event {event_id} (type={event.event_type}, severity={event.severity})")

        # Step 2: Validate and build safe prompt (HARDENED: strict validation)
        try:
            if not self.prompt_builder.validate_prompt_input(event):
                raise ValueError("Event missing required safe fields")

            prompt = self.prompt_builder.build_prompt(event)
            logger.debug(f"Safe prompt constructed for event {event_id} (length={len(prompt)})")
        except ValueError as e:
            logger.warning(f"Prompt validation failed for event {event_id}: {ErrorSanitizer.sanitize(str(e))}")
            try:
                self.event_queue.mark_failed(event_id, "prompt_validation_failed")
            except Exception as mark_err:
                logger.error(f"Failed to mark_failed for event {event_id}: {ErrorSanitizer.classify_error(str(mark_err))}")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error="prompt_validation_failed",
                state_transition="mark_failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error building prompt for event {event_id}: {ErrorSanitizer.classify_error(str(e))}")
            try:
                self.event_queue.mark_failed(event_id, "prompt_construction_error")
            except Exception as mark_err:
                logger.error(f"Failed to mark_failed: {ErrorSanitizer.classify_error(str(mark_err))}")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error="prompt_construction_error",
                state_transition="mark_failed"
            )

        # Step 3: Invoke adapter (never pass QueuedEvent or payload_json)
        try:
            result = self.adapter.generate_article(prompt=prompt)
        except Exception as e:
            # Sanitize error before logging
            sanitized_error = ErrorSanitizer.sanitize(str(e))
            error_classification = ErrorSanitizer.classify_error(str(e))
            logger.warning(f"Adapter invocation failed for event {event_id}: {error_classification}")
            try:
                self.event_queue.mark_failed(event_id, error_classification)
            except Exception as mark_err:
                logger.error(f"Failed to mark_failed: {ErrorSanitizer.classify_error(str(mark_err))}")
            return OrchestratorResult(
                success=False,
                event_id=event_id,
                error=error_classification,
                state_transition="mark_failed"
            )

        # Step 4: Handle adapter result (HARDENED: no raw errors)
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
                logger.error(f"Failed to mark_sent for event {event_id}: {ErrorSanitizer.classify_error(str(e))}")
                return OrchestratorResult(
                    success=False,
                    event_id=event_id,
                    error="mark_sent_failed",
                    state_transition=None
                )
        else:
            # Adapter failure (unavailable, timeout, provider error, etc.)
            error_msg = result.error or "unknown_adapter_error"
            error_classification = ErrorSanitizer.classify_error(error_msg)
            logger.warning(f"Adapter failed for event {event_id}: {error_classification}")
            try:
                self.event_queue.mark_failed(event_id, error_classification)
                logger.info(f"Event {event_id} marked as FAILED (EventQueue owns retry scheduling)")
                return OrchestratorResult(
                    success=False,
                    event_id=event_id,
                    error=error_classification,
                    state_transition="mark_failed"
                )
            except Exception as e:
                logger.error(f"Failed to mark_failed for event {event_id}: {ErrorSanitizer.classify_error(str(e))}")
                return OrchestratorResult(
                    success=False,
                    event_id=event_id,
                    error="mark_failed_failed",
                    state_transition=None
                )

"""
Publication bridge: offline adapter for injected sender-compatible mocks in dry-run mode only.

Accepts injected PublicationStateStore and TelegramSender-compatible mock.
Validates DTOs, manages state transitions, enforces dry-run-only publication.
No network access, no environment variables, no TelegramSender instantiation.
"""

from mediaman.publication_contract import PublicationDTO, PublicationValidator
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateStore,
    PublicationStateMachine,
)
from datetime import datetime, timezone


class PublicationBridge:
    """Offline publication bridge with injected dependencies and dry-run enforcement."""

    def __init__(self, state_store, sender, clock=None):
        """
        Initialize bridge with injected dependencies.

        Args:
            state_store: PublicationStateStore instance
            sender: TelegramSender-compatible mock with dry_run attribute and send() method
            clock: Optional clock function returning ISO 8601 UTC timestamp
        """
        if not isinstance(state_store, PublicationStateStore):
            raise ValueError("invalid_state_store")

        self.state_store = state_store
        self.sender = sender
        self.clock = clock or (
            lambda: datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

    def publish(
        self,
        publication: PublicationDTO,
        *,
        as_of_utc: str | None = None,
        window_seconds: int | None = None,
    ) -> PublicationStateRecord:
        """
        Publish a publication via injected sender in dry-run mode only.

        Args:
            publication: PublicationDTO to publish
            as_of_utc: Historical timestamp for deterministic ID derivation (optional)
            window_seconds: Historical window in seconds for deterministic ID derivation (optional)

        Returns the final PublicationStateRecord after all transitions.

        Raises:
            ValueError("invalid_publication"): DTO validation failed
            ValueError("publication_already_exists"): Duplicate non-terminal state
            ValueError("live_publication_forbidden"): Sender is not in dry-run mode
            ValueError("invalid_sender_result"): Result has invalid attributes
        """
        # A. Validate DTO
        is_valid, error_code = PublicationValidator.validate(publication)
        if not is_valid:
            raise ValueError("invalid_publication")

        current_timestamp = self.clock()

        # B. Create initial state record
        initial_record = PublicationStateRecord(
            publication_id=publication.publication_id,
            race_id=publication.race_id,
            cycle_id=publication.cycle_id,
            state=PublicationState.READY,
            created_at=publication.created_at,
            updated_at=current_timestamp,
            provider_message_id=None,
            last_error=None,
        )

        # C. Duplicate handling
        created = self.state_store.create(initial_record)
        if not created:
            # Publication already exists
            existing_record = self.state_store.get(publication.publication_id)
            if existing_record is None:
                raise ValueError("publication_not_found")

            # Terminal states: return without sending
            if existing_record.state == PublicationState.SENT:
                return existing_record
            if existing_record.state == PublicationState.SENT_RECONCILED:
                return existing_record

            # Any other existing state is an error
            raise ValueError("publication_already_exists")

        # D. Normal state transitions: READY → VALIDATED → SENDING
        current_record = initial_record

        # READY → VALIDATED
        current_record = self.state_store.transition(
            publication.publication_id,
            PublicationState.VALIDATED,
        )

        # VALIDATED → SENDING
        current_record = self.state_store.transition(
            publication.publication_id,
            PublicationState.SENDING,
        )

        # E. Sender safety gate: require dry_run=True
        if not hasattr(self.sender, "dry_run"):
            raise ValueError("invalid_sender_result")

        if self.sender.dry_run is not True:
            raise ValueError("live_publication_forbidden")

        # F. Sender invocation: call exactly once
        # Pass canonical parameters for deterministic cross-process identity if sender supports it
        if not hasattr(self.sender, 'send'):
            raise ValueError("invalid_sender_result")

        import inspect
        sig = inspect.signature(self.sender.send)

        # Check if send() accepts race_id, as_of_utc, window_seconds parameters
        if 'race_id' in sig.parameters and 'as_of_utc' in sig.parameters and 'window_seconds' in sig.parameters:
            # New contract: pass canonical parameters explicitly
            send_result = self.sender.send(
                publication.content,
                race_id=publication.race_id,
                as_of_utc=as_of_utc,
                window_seconds=window_seconds
            )
        else:
            # Fallback: old sender signature without canonical params
            send_result = self.sender.send(publication.content)

        # G. Handle sender result
        # Success case: dry_run=True, success=True, provider_status="DRY_RUN"
        if (
            hasattr(send_result, "dry_run")
            and send_result.dry_run is True
            and hasattr(send_result, "success")
            and send_result.success is True
            and hasattr(send_result, "provider_status")
            and send_result.provider_status == "DRY_RUN"
            and hasattr(send_result, "execution_id")
            and send_result.execution_id
        ):
            # SENDING → SENT with provider ID (deterministic cross-process identity)
            synthetic_message_id = send_result.execution_id if send_result.execution_id.startswith('dry-run:') else f'dry-run:{send_result.execution_id}'
            current_record = self.state_store.transition(
                publication.publication_id,
                PublicationState.SENT,
                provider_message_id=synthetic_message_id,
            )
            return current_record

        # H. Deterministic failure: API_ERROR
        if (
            hasattr(send_result, "dry_run")
            and send_result.dry_run is True
            and hasattr(send_result, "success")
            and send_result.success is False
            and hasattr(send_result, "provider_status")
            and send_result.provider_status == "API_ERROR"
        ):
            # SENDING → FAILED with safe classification
            current_record = self.state_store.transition(
                publication.publication_id,
                PublicationState.FAILED,
                last_error="telegram_api_error",
            )
            return current_record

        # I. Ambiguous failure: NETWORK_ERROR, HTTP_ERROR, ERROR
        if (
            hasattr(send_result, "dry_run")
            and send_result.dry_run is True
            and hasattr(send_result, "success")
            and send_result.success is False
            and hasattr(send_result, "provider_status")
            and send_result.provider_status
            in ("NETWORK_ERROR", "HTTP_ERROR", "ERROR")
        ):
            # SENDING → UNKNOWN (requires operator reconciliation)
            current_record = self.state_store.transition(
                publication.publication_id,
                PublicationState.UNKNOWN,
            )
            return current_record

        # J. Invalid sender result
        raise ValueError("invalid_sender_result")

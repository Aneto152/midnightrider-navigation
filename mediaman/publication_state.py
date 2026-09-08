"""
Publication state machine: nine-state publication lifecycle with immutable records and SQLite persistence.

Defines PublicationState enum, PublicationStateRecord (immutable), PublicationStateMachine (validation),
and PublicationStateStore (SQLite persistence). No content, credentials, or external communication.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import sqlite3
from datetime import datetime, timezone


class PublicationState(Enum):
    """Nine-state publication lifecycle."""
    READY = "READY"
    VALIDATED = "VALIDATED"
    SENDING = "SENDING"
    UNKNOWN = "UNKNOWN"
    RETRY_AUTHORIZED = "RETRY_AUTHORIZED"
    SENT = "SENT"
    SENT_RECONCILED = "SENT_RECONCILED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True)
class PublicationStateRecord:
    """Immutable publication state record."""
    publication_id: str
    race_id: str
    cycle_id: str
    state: PublicationState
    created_at: str
    updated_at: str
    provider_message_id: Optional[str] = None
    last_error: Optional[str] = None


class PublicationStateMachine:
    """State machine with strict transition rules."""

    # Terminal states: no outgoing transitions allowed
    TERMINAL_STATES = {
        PublicationState.SENT,
        PublicationState.SENT_RECONCILED,
        PublicationState.DEAD_LETTER,
    }

    # Exact allowed transitions
    ALLOWED_TRANSITIONS = {
        PublicationState.READY: {PublicationState.VALIDATED},
        PublicationState.VALIDATED: {PublicationState.SENDING},
        PublicationState.SENDING: {
            PublicationState.SENT,
            PublicationState.UNKNOWN,
            PublicationState.FAILED,
        },
        PublicationState.UNKNOWN: {
            PublicationState.SENT_RECONCILED,
            PublicationState.RETRY_AUTHORIZED,
            PublicationState.DEAD_LETTER,
        },
        PublicationState.RETRY_AUTHORIZED: {PublicationState.READY},
        PublicationState.FAILED: set(),
    }

    @staticmethod
    def transition(
        record: PublicationStateRecord,
        target_state: PublicationState,
        *,
        updated_at: str,
        provider_message_id: Optional[str] = None,
        last_error: Optional[str] = None,
        operator_authorized: bool = False,
    ) -> PublicationStateRecord:
        """
        Transition a record to a target state with strict validation.

        Returns a new frozen PublicationStateRecord.
        Raises ValueError with safe classification on invalid transitions.
        """
        if not isinstance(record, PublicationStateRecord):
            raise ValueError("invalid_record")

        if not isinstance(target_state, PublicationState):
            raise ValueError("invalid_target_state")

        # Check if current state is terminal
        if record.state in PublicationStateMachine.TERMINAL_STATES:
            raise ValueError("invalid_transition")

        # Check if transition is allowed
        allowed = PublicationStateMachine.ALLOWED_TRANSITIONS.get(record.state, set())
        if target_state not in allowed:
            raise ValueError("invalid_transition")

        # UNKNOWN transitions require explicit operator authorization
        if record.state == PublicationState.UNKNOWN and not operator_authorized:
            raise ValueError("operator_authorization_required")

        # SENDING → SENT: provider_message_id required (non-empty string), last_error must be None
        if (
            record.state == PublicationState.SENDING
            and target_state == PublicationState.SENT
        ):
            if not provider_message_id or not isinstance(provider_message_id, str):
                raise ValueError("provider_message_id_required")
            if last_error is not None:
                raise ValueError("invalid_transition")

        # SENDING → FAILED: last_error required (safe classification), provider_message_id must be None
        if (
            record.state == PublicationState.SENDING
            and target_state == PublicationState.FAILED
        ):
            if not last_error:
                raise ValueError("invalid_error_classification")
            # Validate error classification format: ^[a-z0-9_]{1,64}$
            import re
            if not re.match(r'^[a-z0-9_]{1,64}$', last_error):
                raise ValueError("invalid_error_classification")
            if provider_message_id is not None:
                raise ValueError("invalid_transition")

        # SENDING → UNKNOWN: both provider_message_id and last_error must be None
        if (
            record.state == PublicationState.SENDING
            and target_state == PublicationState.UNKNOWN
        ):
            if provider_message_id is not None:
                raise ValueError("invalid_transition")
            if last_error is not None:
                raise ValueError("invalid_transition")

        # All other transitions: provider_message_id and last_error must be None
        if not (
            (record.state == PublicationState.SENDING and target_state == PublicationState.SENT) or
            (record.state == PublicationState.SENDING and target_state == PublicationState.FAILED) or
            (record.state == PublicationState.SENDING and target_state == PublicationState.UNKNOWN)
        ):
            if provider_message_id is not None:
                raise ValueError("invalid_transition")
            if last_error is not None:
                raise ValueError("invalid_transition")

        # Create new immutable record
        return PublicationStateRecord(
            publication_id=record.publication_id,
            race_id=record.race_id,
            cycle_id=record.cycle_id,
            state=target_state,
            created_at=record.created_at,
            updated_at=updated_at,
            provider_message_id=provider_message_id,
            last_error=last_error,
        )


class PublicationStateStore:
    """SQLite persistence for publication state records."""

    def __init__(self, db_path: str = ":memory:", clock=None):
        """
        Initialize the store with optional custom clock for testing.

        db_path defaults to :memory: (test); tests use tmp_path for isolation.
        """
        self.db_path = db_path
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
        self.connection = None

    def initialize(self) -> None:
        """Create the publication_states table."""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publication_states (
                publication_id TEXT PRIMARY KEY,
                race_id TEXT NOT NULL,
                cycle_id TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                provider_message_id TEXT,
                last_error TEXT
            )
        """)
        self.connection.commit()

    def create(self, record: PublicationStateRecord) -> bool:
        """
        Create a new publication state record.

        Only READY state is allowed as initial state.
        Returns True on success, False if publication_id already exists.
        """
        if not isinstance(record, PublicationStateRecord):
            raise ValueError("invalid_record")

        if not isinstance(record.state, PublicationState):
            raise ValueError("invalid_record")

        if record.state != PublicationState.READY:
            raise ValueError("initial_state_must_be_ready")

        if record.provider_message_id is not None:
            raise ValueError("invalid_transition")

        if record.last_error is not None:
            raise ValueError("invalid_transition")

        if self.connection is None:
            raise RuntimeError("Store not initialized; call initialize() first")

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO publication_states
                (publication_id, race_id, cycle_id, state, created_at, updated_at,
                 provider_message_id, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.publication_id,
                record.race_id,
                record.cycle_id,
                record.state.value,
                record.created_at,
                record.updated_at,
                record.provider_message_id,
                record.last_error,
            ))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get(self, publication_id: str) -> Optional[PublicationStateRecord]:
        """
        Retrieve a publication state record by ID.

        Returns None if not found.
        Converts state.value back to PublicationState enum.
        """
        if self.connection is None:
            raise RuntimeError("Store not initialized; call initialize() first")

        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT publication_id, race_id, cycle_id, state, created_at, updated_at,
                   provider_message_id, last_error
            FROM publication_states
            WHERE publication_id = ?
        """, (publication_id,))

        row = cursor.fetchone()
        if row is None:
            return None

        return PublicationStateRecord(
            publication_id=row[0],
            race_id=row[1],
            cycle_id=row[2],
            state=PublicationState(row[3]),  # Convert state.value back to enum
            created_at=row[4],
            updated_at=row[5],
            provider_message_id=row[6],
            last_error=row[7],
        )

    def transition(
        self,
        publication_id: str,
        target_state: PublicationState,
        *,
        provider_message_id: Optional[str] = None,
        last_error: Optional[str] = None,
        operator_authorized: bool = False,
    ) -> Optional[PublicationStateRecord]:
        """
        Transition a publication to a target state.

        Returns the new state record, or None if publication_id not found.
        Delegates validation to PublicationStateMachine.
        Failed transitions do not modify the database.
        Successful transitions are atomic.
        """
        if self.connection is None:
            raise RuntimeError("Store not initialized; call initialize() first")

        record = self.get(publication_id)
        if record is None:
            return None

        # Delegate validation to state machine
        new_record = PublicationStateMachine.transition(
            record,
            target_state,
            updated_at=self.clock(),
            provider_message_id=provider_message_id,
            last_error=last_error,
            operator_authorized=operator_authorized,
        )

        # Update atomically
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE publication_states
            SET state = ?, updated_at = ?, provider_message_id = ?, last_error = ?
            WHERE publication_id = ?
        """, (
            new_record.state.value,
            new_record.updated_at,
            new_record.provider_message_id,
            new_record.last_error,
            publication_id,
        ))
        self.connection.commit()

        return new_record

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

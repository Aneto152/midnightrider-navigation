"""
Tests for publication state machine: PublicationState enum, PublicationStateRecord, 
PublicationStateMachine, and PublicationStateStore.

Twelve offline unit tests validating the nine-state machine, immutability, 
state transitions, persistence, and separation from EventQueue.
No network access, no credentials, temporary SQLite only.
"""

import pytest
import sqlite3
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateMachine,
    PublicationStateStore,
)
from mediaman.event_queue import EventQueue


class TestPublicationState:
    """Test publication state machine and persistence."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up temporary test databases and fixed clock."""
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "publication-state.sqlite3"
        self.event_db_path = tmp_path / "event-queue.sqlite3"
        self.fixed_timestamp = "2026-08-31T23:00:00Z"
        self.clock = lambda: self.fixed_timestamp

    def test_publication_state_enum_matches_approved_nine_states(self):
        """PublicationState enum contains exactly nine approved states."""
        expected_states = {
            "READY",
            "VALIDATED",
            "SENDING",
            "UNKNOWN",
            "RETRY_AUTHORIZED",
            "SENT",
            "SENT_RECONCILED",
            "FAILED",
            "DEAD_LETTER",
        }
        actual_states = {state.name for state in PublicationState}
        assert actual_states == expected_states
        assert len(PublicationState) == 9

    def test_ready_record_is_created_and_persisted_without_content_column(self):
        """READY records can be created; publication_states table has no content column."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )

        result = store.create(record)
        assert result is True

        # Verify table structure: no content column
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(publication_states)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "content" not in columns
        assert "payload_json" not in columns
        assert "chat_id" not in columns
        assert "token" not in columns
        conn.close()

        store.close()

    def test_normal_publication_transitions_are_allowed(self):
        """Normal publication flow: READY → VALIDATED → SENDING → SENT."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.create(record)

        # READY → VALIDATED
        r1 = store.transition(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            PublicationState.VALIDATED,
        )
        assert r1.state == PublicationState.VALIDATED

        # VALIDATED → SENDING
        r2 = store.transition(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            PublicationState.SENDING,
        )
        assert r2.state == PublicationState.SENDING

        # SENDING → SENT with provider_message_id
        r3 = store.transition(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            PublicationState.SENT,
            provider_message_id="msg-123",
        )
        assert r3.state == PublicationState.SENT
        assert r3.provider_message_id == "msg-123"

        store.close()

    def test_sending_can_transition_to_unknown_without_automatic_retry(self):
        """SENDING → UNKNOWN is allowed, but no automatic retry occurs."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.SENDING,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.connection = store.connection or sqlite3.connect(str(self.db_path))
        cursor = store.connection.cursor()
        cursor.execute("""
            INSERT INTO publication_states
            (publication_id, race_id, cycle_id, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            record.publication_id,
            record.race_id,
            record.cycle_id,
            record.state.value,
            record.created_at,
            record.updated_at,
        ))
        store.connection.commit()

        # SENDING → UNKNOWN (no automatic retry)
        r = store.transition(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            PublicationState.UNKNOWN,
        )
        assert r.state == PublicationState.UNKNOWN

        # Verify metadata validation: provider_message_id not allowed for UNKNOWN
        with pytest.raises(ValueError) as exc_info:
            store.transition(
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                PublicationState.UNKNOWN,
                provider_message_id="msg-123",
            )
        assert str(exc_info.value) == "invalid_transition"

        # Verify metadata validation: last_error not allowed for UNKNOWN
        with pytest.raises(ValueError) as exc_info:
            store.transition(
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                PublicationState.UNKNOWN,
                last_error="some_error",
            )
        assert str(exc_info.value) == "invalid_transition"

        store.close()

    def test_unknown_transitions_require_explicit_operator_authorization(self):
        """UNKNOWN transitions require operator_authorized=True."""
        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.UNKNOWN,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )

        # Without operator_authorized, should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT_RECONCILED,
                updated_at=self.fixed_timestamp,
                operator_authorized=False,
            )
        assert str(exc_info.value) == "operator_authorization_required"

        # With operator_authorized=True, should succeed
        r = PublicationStateMachine.transition(
            record,
            PublicationState.SENT_RECONCILED,
            updated_at=self.fixed_timestamp,
            operator_authorized=True,
        )
        assert r.state == PublicationState.SENT_RECONCILED

    def test_retry_authorized_returns_to_ready_only(self):
        """RETRY_AUTHORIZED can only transition back to READY."""
        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.RETRY_AUTHORIZED,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )

        # RETRY_AUTHORIZED → READY should succeed
        r = PublicationStateMachine.transition(
            record,
            PublicationState.READY,
            updated_at=self.fixed_timestamp,
        )
        assert r.state == PublicationState.READY

        # Try invalid transitions from RETRY_AUTHORIZED
        with pytest.raises(ValueError):
            PublicationStateMachine.transition(
                record,
                PublicationState.SENDING,
                updated_at=self.fixed_timestamp,
            )

    def test_invalid_transitions_are_rejected(self):
        """Invalid state transitions raise ValueError with safe classifications."""
        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )

        # READY cannot go to SENT directly
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT,
                updated_at=self.fixed_timestamp,
            )
        assert str(exc_info.value) == "invalid_transition"

        # READY cannot go to UNKNOWN
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.UNKNOWN,
                updated_at=self.fixed_timestamp,
            )
        assert str(exc_info.value) == "invalid_transition"

        # dict passed to transition() raises invalid_record
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                {"state": "READY"},
                PublicationState.VALIDATED,
                updated_at=self.fixed_timestamp,
            )
        assert str(exc_info.value) == "invalid_record"

        # string passed to transition() raises invalid_record
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                "not_a_record",
                PublicationState.VALIDATED,
                updated_at=self.fixed_timestamp,
            )
        assert str(exc_info.value) == "invalid_record"

    def test_sent_requires_provider_message_id(self):
        """SENDING → SENT requires non-empty provider_message_id."""
        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.SENDING,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )

        # Without provider_message_id
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT,
                updated_at=self.fixed_timestamp,
            )
        assert str(exc_info.value) == "provider_message_id_required"

        # With last_error set (invalid for SENT)
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT,
                updated_at=self.fixed_timestamp,
                provider_message_id="msg-123",
                last_error="some_error",
            )
        assert str(exc_info.value) == "invalid_transition"

        # With provider_message_id only
        r = PublicationStateMachine.transition(
            record,
            PublicationState.SENT,
            updated_at=self.fixed_timestamp,
            provider_message_id="msg-abc-123",
        )
        assert r.state == PublicationState.SENT

    def test_failed_requires_safe_error_classification(self):
        """SENDING → FAILED requires safe error classification (^[a-z0-9_]{1,64}$)."""
        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.SENDING,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )

        # Without last_error
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.FAILED,
                updated_at=self.fixed_timestamp,
            )
        assert str(exc_info.value) == "invalid_error_classification"

        # With invalid format (uppercase)
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.FAILED,
                updated_at=self.fixed_timestamp,
                last_error="ADAPTER_TIMEOUT",
            )
        assert str(exc_info.value) == "invalid_error_classification"

        # With provider_message_id set (invalid for FAILED)
        with pytest.raises(ValueError) as exc_info:
            PublicationStateMachine.transition(
                record,
                PublicationState.FAILED,
                updated_at=self.fixed_timestamp,
                last_error="adapter_timeout",
                provider_message_id="msg-123",
            )
        assert str(exc_info.value) == "invalid_transition"

        # With valid format
        r = PublicationStateMachine.transition(
            record,
            PublicationState.FAILED,
            updated_at=self.fixed_timestamp,
            last_error="adapter_timeout",
        )
        assert r.state == PublicationState.FAILED
        assert r.last_error == "adapter_timeout"

    def test_terminal_states_cannot_transition(self):
        """Terminal states (SENT, SENT_RECONCILED, DEAD_LETTER) cannot transition."""
        for terminal_state in [
            PublicationState.SENT,
            PublicationState.SENT_RECONCILED,
            PublicationState.DEAD_LETTER,
        ]:
            record = PublicationStateRecord(
                publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                race_id="race-001",
                cycle_id="cycle-001",
                state=terminal_state,
                created_at=self.fixed_timestamp,
                updated_at=self.fixed_timestamp,
            )

            with pytest.raises(ValueError) as exc_info:
                PublicationStateMachine.transition(
                    record,
                    PublicationState.READY,
                    updated_at=self.fixed_timestamp,
                )
            assert str(exc_info.value) == "invalid_transition"

    def test_publication_store_is_separate_from_event_queue(self):
        """PublicationStateStore uses separate SQLite database, not EventQueue's."""
        # Create EventQueue
        event_queue = EventQueue(db_path=str(self.event_db_path), clock=self.clock)
        event_queue.initialize()

        # Create PublicationStateStore
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Read tables from EventQueue database
        event_conn = sqlite3.connect(str(self.event_db_path))
        event_cursor = event_conn.cursor()
        event_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        event_tables = {row[0] for row in event_cursor.fetchall()}
        event_conn.close()

        # Read tables from PublicationStateStore database
        pub_conn = sqlite3.connect(str(self.db_path))
        pub_cursor = pub_conn.cursor()
        pub_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        pub_tables = {row[0] for row in pub_cursor.fetchall()}
        pub_conn.close()

        # Verify EventQueue database structure
        assert "events" in event_tables
        assert "publication_states" not in event_tables

        # Verify PublicationStateStore database structure
        assert "publication_states" in pub_tables
        assert "events" not in pub_tables

        store.close()
        event_queue.close()

    def test_state_record_survives_store_reopen(self):
        """State records persist across store close and reopen."""
        # Create and store a record
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.create(record)
        store.close()

        # Reopen store and verify record persists
        store2 = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store2.initialize()

        retrieved = store2.get("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        assert retrieved is not None
        assert retrieved.publication_id == record.publication_id
        assert retrieved.race_id == record.race_id
        assert retrieved.cycle_id == record.cycle_id
        assert retrieved.state == PublicationState.READY
        assert retrieved.created_at == self.fixed_timestamp
        assert retrieved.updated_at == self.fixed_timestamp

        # Verify store.create() rejects non-PublicationStateRecord
        with pytest.raises(ValueError) as exc_info:
            store2.create({"state": "READY"})
        assert str(exc_info.value) == "invalid_record"

        # Verify store.create() rejects non-PublicationState state
        bad_record = PublicationStateRecord(
            publication_id="1" * 64,
            race_id="race-002",
            cycle_id="cycle-002",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        good_result = store2.create(bad_record)
        assert good_result is True

        # Verify store.create() rejects READY with provider_message_id
        bad_ready = PublicationStateRecord(
            publication_id="2" * 64,
            race_id="race-003",
            cycle_id="cycle-003",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
            provider_message_id="msg-123",
        )
        with pytest.raises(ValueError) as exc_info:
            store2.create(bad_ready)
        assert str(exc_info.value) == "invalid_transition"

        # Verify store.create() rejects READY with last_error
        bad_ready_error = PublicationStateRecord(
            publication_id="3" * 64,
            race_id="race-004",
            cycle_id="cycle-004",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
            last_error="some_error",
        )
        with pytest.raises(ValueError) as exc_info:
            store2.create(bad_ready_error)
        assert str(exc_info.value) == "invalid_transition"

        store2.close()

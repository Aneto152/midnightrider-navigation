"""
Tests for publication state machine: PublicationState enum, PublicationStateRecord, 
PublicationStateMachine, and PublicationStateStore.

Twelve offline unit tests validating the nine-state machine, immutability, 
state transitions, persistence, and separation from EventQueue.
No network access, no credentials, temporary SQLite only.
"""

import unittest
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateMachine,
    PublicationStateStore,
)


class TestPublicationState(unittest.TestCase):
    """Test publication state machine and persistence."""

    def setUp(self):
        """Set up temporary test database and fixed clock."""
        self.temp_dir = tempfile.mkdtemp(prefix="pub-state-test-")
        self.db_path = os.path.join(self.temp_dir, "test_pub_state.db")
        self.fixed_timestamp = "2026-08-31T23:00:00Z"
        self.clock = lambda: self.fixed_timestamp

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

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
        self.assertEqual(actual_states, expected_states)
        self.assertEqual(len(PublicationState), 9)

    def test_ready_record_is_created_and_persisted_without_content_column(self):
        """READY records can be created; publication_states table has no content column."""
        store = PublicationStateStore(db_path=self.db_path, clock=self.clock)
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
        self.assertTrue(result)

        # Verify table structure: no content column
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(publication_states)")
        columns = {row[1] for row in cursor.fetchall()}
        self.assertNotIn("content", columns)
        self.assertNotIn("payload_json", columns)
        self.assertNotIn("chat_id", columns)
        self.assertNotIn("token", columns)
        conn.close()

        store.close()

    def test_normal_publication_transitions_are_allowed(self):
        """Normal publication flow: READY → VALIDATED → SENDING → SENT."""
        store = PublicationStateStore(db_path=self.db_path, clock=self.clock)
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
        self.assertEqual(r1.state, PublicationState.VALIDATED)

        # VALIDATED → SENDING
        r2 = store.transition(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            PublicationState.SENDING,
        )
        self.assertEqual(r2.state, PublicationState.SENDING)

        # SENDING → SENT with provider_message_id
        r3 = store.transition(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            PublicationState.SENT,
            provider_message_id="msg-123",
        )
        self.assertEqual(r3.state, PublicationState.SENT)
        self.assertEqual(r3.provider_message_id, "msg-123")

        store.close()

    def test_sending_can_transition_to_unknown_without_automatic_retry(self):
        """SENDING → UNKNOWN is allowed, but no automatic retry occurs."""
        store = PublicationStateStore(db_path=self.db_path, clock=self.clock)
        store.initialize()

        record = PublicationStateRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.SENDING,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.connection = store.connection or __import__('sqlite3').connect(store.db_path)
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
        self.assertEqual(r.state, PublicationState.UNKNOWN)

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
        with self.assertRaises(ValueError) as ctx:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT_RECONCILED,
                updated_at=self.fixed_timestamp,
                operator_authorized=False,
            )
        self.assertEqual(str(ctx.exception), "operator_authorization_required")

        # With operator_authorized=True, should succeed
        r = PublicationStateMachine.transition(
            record,
            PublicationState.SENT_RECONCILED,
            updated_at=self.fixed_timestamp,
            operator_authorized=True,
        )
        self.assertEqual(r.state, PublicationState.SENT_RECONCILED)

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
        self.assertEqual(r.state, PublicationState.READY)

        # Try invalid transitions from RETRY_AUTHORIZED
        with self.assertRaises(ValueError):
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
        with self.assertRaises(ValueError) as ctx:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT,
                updated_at=self.fixed_timestamp,
            )
        self.assertEqual(str(ctx.exception), "invalid_transition")

        # READY cannot go to UNKNOWN
        with self.assertRaises(ValueError) as ctx:
            PublicationStateMachine.transition(
                record,
                PublicationState.UNKNOWN,
                updated_at=self.fixed_timestamp,
            )
        self.assertEqual(str(ctx.exception), "invalid_transition")

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
        with self.assertRaises(ValueError) as ctx:
            PublicationStateMachine.transition(
                record,
                PublicationState.SENT,
                updated_at=self.fixed_timestamp,
            )
        self.assertEqual(str(ctx.exception), "provider_message_id_required")

        # With provider_message_id
        r = PublicationStateMachine.transition(
            record,
            PublicationState.SENT,
            updated_at=self.fixed_timestamp,
            provider_message_id="msg-abc-123",
        )
        self.assertEqual(r.state, PublicationState.SENT)

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
        with self.assertRaises(ValueError) as ctx:
            PublicationStateMachine.transition(
                record,
                PublicationState.FAILED,
                updated_at=self.fixed_timestamp,
            )
        self.assertEqual(str(ctx.exception), "invalid_error_classification")

        # With invalid format (uppercase)
        with self.assertRaises(ValueError) as ctx:
            PublicationStateMachine.transition(
                record,
                PublicationState.FAILED,
                updated_at=self.fixed_timestamp,
                last_error="ADAPTER_TIMEOUT",
            )
        self.assertEqual(str(ctx.exception), "invalid_error_classification")

        # With valid format
        r = PublicationStateMachine.transition(
            record,
            PublicationState.FAILED,
            updated_at=self.fixed_timestamp,
            last_error="adapter_timeout",
        )
        self.assertEqual(r.state, PublicationState.FAILED)
        self.assertEqual(r.last_error, "adapter_timeout")

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

            with self.assertRaises(ValueError) as ctx:
                PublicationStateMachine.transition(
                    record,
                    PublicationState.READY,
                    updated_at=self.fixed_timestamp,
                )
            self.assertEqual(str(ctx.exception), "invalid_transition")

    def test_publication_store_is_separate_from_event_queue(self):
        """PublicationStateStore uses separate SQLite database, not EventQueue's."""
        store = PublicationStateStore(db_path=self.db_path, clock=self.clock)
        store.initialize()

        # Verify only publication_states table exists
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        self.assertIn("publication_states", tables)
        self.assertNotIn("events", tables)
        self.assertNotIn("event_queue", tables)
        conn.close()

        store.close()

    def test_state_record_survives_store_reopen(self):
        """State records persist across store close and reopen."""
        # Create and store a record
        store = PublicationStateStore(db_path=self.db_path, clock=self.clock)
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
        store2 = PublicationStateStore(db_path=self.db_path, clock=self.clock)
        store2.initialize()

        retrieved = store2.get("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.publication_id, record.publication_id)
        self.assertEqual(retrieved.race_id, record.race_id)
        self.assertEqual(retrieved.cycle_id, record.cycle_id)
        self.assertEqual(retrieved.state, PublicationState.READY)
        self.assertEqual(retrieved.created_at, self.fixed_timestamp)
        self.assertEqual(retrieved.updated_at, self.fixed_timestamp)

        store2.close()


if __name__ == '__main__':
    unittest.main()

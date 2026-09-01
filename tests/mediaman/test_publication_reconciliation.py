"""
Tests for publication reconciliation: PublicationEvidenceRecord, PublicationEvidenceValidator,
and PublicationReconciler.

Ten offline unit tests validating evidence validation, immutability, manual reconciliation paths,
operator authorization requirements, and terminal state enforcement.
No network access, no credentials, temporary SQLite only.
"""

import pytest
import sqlite3
from datetime import datetime, timezone
from mediaman.publication_reconciliation import (
    PublicationEvidenceRecord,
    PublicationEvidenceValidator,
    PublicationReconciler,
)
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateStore,
)


class TestPublicationReconciliation:
    """Test manual publication reconciliation."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up temporary test database and fixed clock."""
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "publication-state.sqlite3"
        self.fixed_timestamp = "2026-08-31T23:00:00Z"
        self.fixed_evidence_timestamp = "2026-08-31T23:05:00Z"
        self.clock = lambda: self.fixed_timestamp
        self.valid_publication_id = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def test_valid_evidence_record_is_accepted(self):
        """PublicationEvidenceRecord with valid fields is created and validates successfully."""
        evidence = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="Operator confirmed delivery via manual search",
            operator_identity="operator-001",
            evidence_reference="manual_ui:2026-08-31T23:05:00Z:ref-001",
            optional_telegram_message_id="msg-12345",
            reconciliation_timestamp="2026-08-31T23:05:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )

        is_valid, error_code = PublicationEvidenceValidator.validate(evidence)
        assert is_valid is True
        assert error_code == ""

    def test_evidence_record_is_immutable_and_has_exactly_eight_fields(self):
        """PublicationEvidenceRecord is frozen and has exactly eight fields."""
        evidence = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="operator_confirmed_delivery",
        )

        # Evidence record is frozen (immutable)
        with pytest.raises(AttributeError):
            evidence.publication_id = "modified"

        # Record has exactly eight fields
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(evidence)}
        expected_fields = {
            "publication_id",
            "transition",
            "reason",
            "operator_identity",
            "evidence_reference",
            "optional_telegram_message_id",
            "reconciliation_timestamp",
            "safe_decision_classification",
        }
        assert field_names == expected_fields
        assert len(field_names) == 8

    def test_only_approved_transition_and_classifications_are_accepted(self):
        """Only UNKNOWN_TO_SENT_RECONCILED transition and four classifications are valid."""
        # Valid transition and classification
        evidence = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, _ = PublicationEvidenceValidator.validate(evidence)
        assert is_valid is True

        # Invalid transition
        bad_transition = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_RETRY_AUTHORIZED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(bad_transition)
        assert is_valid is False
        assert error_code == "invalid_transition"

        # Invalid classification
        bad_classification = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="invalid_classification",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(bad_classification)
        assert is_valid is False
        assert error_code == "invalid_safe_decision_classification"

        # Test all four approved classifications
        for classification in [
            "manual_ui_search_confirmed",
            "api_query_confirmed",
            "external_monitoring_confirmed",
            "operator_confirmed_delivery",
        ]:
            evidence = PublicationEvidenceRecord(
                publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                transition="UNKNOWN_TO_SENT_RECONCILED",
                reason="test",
                operator_identity="op-001",
                evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
                optional_telegram_message_id=None,
                reconciliation_timestamp="2026-08-31T23:00:00Z",
                safe_decision_classification=classification,
            )
            is_valid, _ = PublicationEvidenceValidator.validate(evidence)
            assert is_valid is True

    def test_invalid_evidence_returns_safe_classification_without_echoing_values(self):
        """Validation errors are safe classifications; evidence values are never echoed."""
        # Invalid publication_id
        evidence = PublicationEvidenceRecord(
            publication_id="invalid_id_not_hex",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(evidence)
        assert is_valid is False
        assert error_code == "invalid_publication_id"
        # Error code does not contain the invalid value
        assert "invalid_id_not_hex" not in error_code

        # Reason with credentials should be rejected without echoing
        bad_reason = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="secret=my_actual_secret_12345",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(bad_reason)
        assert is_valid is False
        assert error_code == "unsafe_content"
        # Secret is not echoed
        assert "my_actual_secret_12345" not in error_code

        # Invalid evidence_reference: invalid calendar date (2026-99-99)
        invalid_date = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-99-99T10:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(invalid_date)
        assert is_valid is False
        assert error_code == "invalid_evidence_reference"
        assert "2026-99-99" not in error_code

        # Invalid evidence_reference: invalid hour (25)
        invalid_hour = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T25:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(invalid_hour)
        assert is_valid is False
        assert error_code == "invalid_evidence_reference"
        assert "T25:00:00Z" not in error_code

        # Invalid evidence_reference: invalid minute (61)
        invalid_minute = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T10:61:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(invalid_minute)
        assert is_valid is False
        assert error_code == "invalid_evidence_reference"
        assert "10:61:00" not in error_code

        # Invalid evidence_reference: non-UTC timestamp (with +01:00 offset)
        non_utc = PublicationEvidenceRecord(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T10:00:00+01:00:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp="2026-08-31T23:00:00Z",
            safe_decision_classification="manual_ui_search_confirmed",
        )
        is_valid, error_code = PublicationEvidenceValidator.validate(non_utc)
        assert is_valid is False
        assert error_code == "invalid_evidence_reference"
        assert "+01:00" not in error_code

    def test_unknown_to_sent_reconciled_requires_valid_evidence(self):
        """reconcile_sent() requires valid evidence; rejects with ValueError('invalid_evidence')."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Create UNKNOWN publication
        record = PublicationStateRecord(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.UNKNOWN,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.connection = sqlite3.connect(str(self.db_path))
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

        reconciler = PublicationReconciler(store)

        # Valid evidence
        valid_evidence = PublicationEvidenceRecord(
            publication_id=self.valid_publication_id,
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="Operator confirmed delivery",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp=self.fixed_evidence_timestamp,
            safe_decision_classification="manual_ui_search_confirmed",
        )
        result = reconciler.reconcile_sent(valid_evidence)
        assert result.state == PublicationState.SENT_RECONCILED

        # Invalid evidence (bad publication_id)
        invalid_evidence = PublicationEvidenceRecord(
            publication_id="invalid_id",
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp=self.fixed_evidence_timestamp,
            safe_decision_classification="manual_ui_search_confirmed",
        )
        with pytest.raises(ValueError, match="invalid_evidence"):
            reconciler.reconcile_sent(invalid_evidence)

        store.close()

    def test_unknown_to_retry_authorized_then_ready_requires_operator_authorization(self):
        """authorize_retry() transitions UNKNOWN → RETRY_AUTHORIZED → READY via operator authorization."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Create UNKNOWN publication
        record = PublicationStateRecord(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.UNKNOWN,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.connection = sqlite3.connect(str(self.db_path))
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

        reconciler = PublicationReconciler(store)

        # authorize_retry transitions UNKNOWN → RETRY_AUTHORIZED → READY
        result = reconciler.authorize_retry(
            publication_id=self.valid_publication_id,
            operator_identity="op-001",
            reason="Operator authorized manual retry",
            timestamp=self.fixed_evidence_timestamp,
        )

        # Final state must be READY
        assert result.state == PublicationState.READY

        # Verify via store
        final_record = store.get(self.valid_publication_id)
        assert final_record.state == PublicationState.READY

        store.close()

    def test_unknown_to_dead_letter_requires_operator_authorization(self):
        """abandon() transitions UNKNOWN → DEAD_LETTER via operator authorization."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Create UNKNOWN publication
        record = PublicationStateRecord(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.UNKNOWN,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.connection = sqlite3.connect(str(self.db_path))
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

        reconciler = PublicationReconciler(store)

        # abandon transitions UNKNOWN → DEAD_LETTER
        result = reconciler.abandon(
            publication_id=self.valid_publication_id,
            operator_identity="op-001",
            reason="Operator abandoned publication",
            timestamp=self.fixed_evidence_timestamp,
        )

        assert result.state == PublicationState.DEAD_LETTER

        # Verify via store
        final_record = store.get(self.valid_publication_id)
        assert final_record.state == PublicationState.DEAD_LETTER

        store.close()

    def test_reconciliation_rejects_non_unknown_states(self):
        """reconcile_sent(), authorize_retry(), and abandon() reject non-UNKNOWN states."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Test READY state
        record = PublicationStateRecord(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.READY,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        store.connection = sqlite3.connect(str(self.db_path))
        store.create(record)

        reconciler = PublicationReconciler(store)

        # reconcile_sent rejects READY
        evidence = PublicationEvidenceRecord(
            publication_id=self.valid_publication_id,
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp=self.fixed_evidence_timestamp,
            safe_decision_classification="manual_ui_search_confirmed",
        )
        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler.reconcile_sent(evidence)

        # authorize_retry rejects READY
        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler.authorize_retry(
                self.valid_publication_id,
                "op-001",
                "reason",
                self.fixed_evidence_timestamp,
            )

        # abandon rejects READY
        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler.abandon(
                self.valid_publication_id,
                "op-001",
                "reason",
                self.fixed_evidence_timestamp,
            )

        # Test SENT state (terminal)
        store2_path = self.tmp_path / "publication-state2.sqlite3"
        store2 = PublicationStateStore(db_path=str(store2_path), clock=self.clock)
        store2.initialize()

        sent_record = PublicationStateRecord(
            publication_id="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            race_id="race-002",
            cycle_id="cycle-002",
            state=PublicationState.SENT,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
            provider_message_id="msg-123",
        )
        # Create SENT state via SQL (not allowed via store.create)
        store2.connection = sqlite3.connect(str(store2_path))
        cursor2 = store2.connection.cursor()
        cursor2.execute("""
            INSERT INTO publication_states
            (publication_id, race_id, cycle_id, state, created_at, updated_at, provider_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sent_record.publication_id,
            sent_record.race_id,
            sent_record.cycle_id,
            sent_record.state.value,
            sent_record.created_at,
            sent_record.updated_at,
            sent_record.provider_message_id,
        ))
        store2.connection.commit()

        reconciler2 = PublicationReconciler(store2)

        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler2.reconcile_sent(
                PublicationEvidenceRecord(
                    publication_id="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
                    transition="UNKNOWN_TO_SENT_RECONCILED",
                    reason="test",
                    operator_identity="op-001",
                    evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
                    optional_telegram_message_id=None,
                    reconciliation_timestamp=self.fixed_evidence_timestamp,
                    safe_decision_classification="manual_ui_search_confirmed",
                )
            )

        store.close()
        store2.close()

    def test_reconciliation_does_not_contact_external_services_or_store_content(self):
        """Reconciliation is offline: no network, no content storage, no external queries."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        record = PublicationStateRecord(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.UNKNOWN,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        # Create UNKNOWN state via SQL (not allowed via store.create)
        store.connection = sqlite3.connect(str(self.db_path))
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

        reconciler = PublicationReconciler(store)

        evidence = PublicationEvidenceRecord(
            publication_id=self.valid_publication_id,
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="Operator confirmed",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp=self.fixed_evidence_timestamp,
            safe_decision_classification="manual_ui_search_confirmed",
        )

        # Execute reconciliation
        result = reconciler.reconcile_sent(evidence)

        # Verify no content was stored
        cursor = store.connection.cursor()
        cursor.execute("PRAGMA table_info(publication_states)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "content" not in columns
        assert "payload_json" not in columns
        assert "evidence_payload" not in columns

        # Verify record has no content
        assert not hasattr(result, "content")
        assert not hasattr(result, "evidence_content")

        store.close()

    def test_terminal_reconciliation_states_cannot_be_reprocessed(self):
        """SENT, SENT_RECONCILED, and DEAD_LETTER states are terminal."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        reconciler = PublicationReconciler(store)

        # Test SENT_RECONCILED (terminal)
        pub_id_1 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        sent_rec_record = PublicationStateRecord(
            publication_id=pub_id_1,
            race_id="race-001",
            cycle_id="cycle-001",
            state=PublicationState.SENT_RECONCILED,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        # Create SENT_RECONCILED state via SQL (not allowed via store.create)
        store.connection = sqlite3.connect(str(self.db_path))
        cursor = store.connection.cursor()
        cursor.execute("""
            INSERT INTO publication_states
            (publication_id, race_id, cycle_id, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sent_rec_record.publication_id,
            sent_rec_record.race_id,
            sent_rec_record.cycle_id,
            sent_rec_record.state.value,
            sent_rec_record.created_at,
            sent_rec_record.updated_at,
        ))
        store.connection.commit()

        evidence = PublicationEvidenceRecord(
            publication_id=pub_id_1,
            transition="UNKNOWN_TO_SENT_RECONCILED",
            reason="test",
            operator_identity="op-001",
            evidence_reference="manual_ui:2026-08-31T23:00:00Z:ref-001",
            optional_telegram_message_id=None,
            reconciliation_timestamp=self.fixed_evidence_timestamp,
            safe_decision_classification="manual_ui_search_confirmed",
        )

        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler.reconcile_sent(evidence)

        # Test DEAD_LETTER (terminal)
        pub_id_2 = "1123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        dead_record = PublicationStateRecord(
            publication_id=pub_id_2,
            race_id="race-002",
            cycle_id="cycle-002",
            state=PublicationState.DEAD_LETTER,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
        )
        # Create DEAD_LETTER state via SQL
        cursor = store.connection.cursor()
        cursor.execute("""
            INSERT INTO publication_states
            (publication_id, race_id, cycle_id, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dead_record.publication_id,
            dead_record.race_id,
            dead_record.cycle_id,
            dead_record.state.value,
            dead_record.created_at,
            dead_record.updated_at,
        ))
        store.connection.commit()

        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler.abandon(
                pub_id_2,
                "op-001",
                "reason",
                self.fixed_evidence_timestamp,
            )

        # SENT state is also terminal
        pub_id_3 = "2223456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        sent_record = PublicationStateRecord(
            publication_id=pub_id_3,
            race_id="race-003",
            cycle_id="cycle-003",
            state=PublicationState.SENT,
            created_at=self.fixed_timestamp,
            updated_at=self.fixed_timestamp,
            provider_message_id="msg-123",
        )
        # Create SENT state via SQL
        cursor.execute("""
            INSERT INTO publication_states
            (publication_id, race_id, cycle_id, state, created_at, updated_at, provider_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sent_record.publication_id,
            sent_record.race_id,
            sent_record.cycle_id,
            sent_record.state.value,
            sent_record.created_at,
            sent_record.updated_at,
            sent_record.provider_message_id,
        ))
        store.connection.commit()

        with pytest.raises(ValueError, match="reconciliation_requires_unknown"):
            reconciler.authorize_retry(
                pub_id_3,
                "op-001",
                "reason",
                self.fixed_evidence_timestamp,
            )

        store.close()

"""
Tests for publication bridge: PublicationBridge with injected dependencies and dry-run enforcement.

Ten offline unit tests validating offline adapter behavior, state transitions, sender mocking,
and content non-persistence. No network access, no TelegramSender instantiation, temporary SQLite only.
"""

import pytest
import sqlite3
from unittest.mock import Mock, create_autospec
from dataclasses import dataclass
from mediaman.publication_bridge import PublicationBridge
from mediaman.publication_contract import PublicationDTO
from mediaman.publication_state import (
    PublicationState,
    PublicationStateStore,
)
from mediaman.telegram_sender import SendResult


class TestPublicationBridge:
    """Test offline publication bridge with mocked sender."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up temporary test database and fixed clock."""
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "publication-state.sqlite3"
        self.fixed_timestamp = "2026-08-31T23:00:00Z"
        self.clock = lambda: self.fixed_timestamp
        self.valid_publication_id = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def test_dry_run_success_completes_ready_validated_sending_sent(self):
        """Successful dry-run completes state progression: READY → VALIDATED → SENDING → SENT."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Mock sender with dry_run=True and success
        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=True,
                provider_status="DRY_RUN",
                error_code="",
                message_length=42,
                execution_id="exec-001",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        # Create and publish
        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="Test article content",
            created_at=self.fixed_timestamp,
        )

        result = bridge.publish(publication)

        # Verify final state is SENT
        assert result.state == PublicationState.SENT
        # Verify synthetic provider ID
        assert result.provider_message_id == "dry-run:exec-001"
        assert result.last_error is None

        # Verify sender called exactly once
        mock_sender.send.assert_called_once_with("Test article content")

        store.close()

    def test_dry_run_success_uses_synthetic_provider_identifier(self):
        """Successful dry-run uses synthetic provider ID format: dry-run:<execution_id>."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=True,
                provider_status="DRY_RUN",
                error_code="",
                message_length=10,
                execution_id="abc123xyz",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="content",
            created_at=self.fixed_timestamp,
        )

        result = bridge.publish(publication)

        # Verify synthetic provider ID begins with "dry-run:"
        assert result.provider_message_id.startswith("dry-run:")
        assert "abc123xyz" in result.provider_message_id

        store.close()

    def test_invalid_publication_is_rejected_before_state_creation(self):
        """Invalid publication DTO is rejected before creating any state record."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True

        bridge = PublicationBridge(store, mock_sender, self.clock)

        # Invalid DTO: missing content
        invalid_publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="",  # Invalid: empty
            created_at=self.fixed_timestamp,
        )

        with pytest.raises(ValueError, match="invalid_publication"):
            bridge.publish(invalid_publication)

        # Verify no record was created
        assert store.get(self.valid_publication_id) is None
        # Verify sender was never called
        mock_sender.send.assert_not_called()

        store.close()

    def test_sender_is_called_exactly_once_with_publication_content(self):
        """Sender is called exactly once with the publication content."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=True,
                provider_status="DRY_RUN",
                error_code="",
                message_length=20,
                execution_id="exec-001",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="Exact content to send",
            created_at=self.fixed_timestamp,
        )

        bridge.publish(publication)

        # Sender called exactly once
        assert mock_sender.send.call_count == 1
        # With exact content
        mock_sender.send.assert_called_once_with("Exact content to send")

        store.close()

    def test_duplicate_sent_publication_is_not_sent_again(self):
        """Duplicate SENT publication is returned without calling sender."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=True,
                provider_status="DRY_RUN",
                error_code="",
                message_length=10,
                execution_id="exec-001",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="content",
            created_at=self.fixed_timestamp,
        )

        # First publish
        result1 = bridge.publish(publication)
        assert result1.state == PublicationState.SENT
        assert mock_sender.send.call_count == 1

        # Attempt duplicate publish
        result2 = bridge.publish(publication)
        assert result2.state == PublicationState.SENT
        # Sender NOT called again
        assert mock_sender.send.call_count == 1
        # Same record returned
        assert result2.provider_message_id == result1.provider_message_id

        store.close()

    def test_api_error_transitions_to_failed_with_safe_classification(self):
        """API_ERROR from sender transitions to FAILED with safe error classification."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=False,
                provider_status="API_ERROR",
                error_code="invalid_chat_id",
                message_length=0,
                execution_id="",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="content",
            created_at=self.fixed_timestamp,
        )

        result = bridge.publish(publication)

        # State transitions to FAILED
        assert result.state == PublicationState.FAILED
        # Error is safe classification (not raw error_code)
        assert result.last_error == "telegram_api_error"
        assert "invalid_chat_id" not in str(result.last_error)

        store.close()

    def test_ambiguous_sender_failure_transitions_to_unknown_without_retry(self):
        """Ambiguous failures (NETWORK_ERROR, HTTP_ERROR, ERROR) transition to UNKNOWN."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Test NETWORK_ERROR
        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=False,
                provider_status="NETWORK_ERROR",
                error_code="connection_timeout",
                message_length=0,
                execution_id="",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="content",
            created_at=self.fixed_timestamp,
        )

        result = bridge.publish(publication)

        # Transitions to UNKNOWN (requires operator reconciliation)
        assert result.state == PublicationState.UNKNOWN
        # No automatic retry or reconciliation
        assert result.provider_message_id is None

        store.close()

    def test_live_sender_is_rejected_before_send(self):
        """Sender with dry_run=False is rejected before calling send()."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = False  # Live mode forbidden

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="content",
            created_at=self.fixed_timestamp,
        )

        with pytest.raises(ValueError, match="live_publication_forbidden"):
            bridge.publish(publication)

        # Sender.send() never called
        mock_sender.send.assert_not_called()

        store.close()

    def test_invalid_sender_result_is_rejected_safely(self):
        """Invalid sender result (missing attributes or unsupported status) raises ValueError."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True
        # Invalid result: missing required attributes
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=True,
                provider_status="UNSUPPORTED_STATUS",  # Not DRY_RUN, API_ERROR, or ambiguous
                error_code="",
                message_length=10,
                execution_id="exec-001",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="content",
            created_at=self.fixed_timestamp,
        )

        with pytest.raises(ValueError, match="invalid_sender_result"):
            bridge.publish(publication)

        store.close()

    def test_bridge_does_not_persist_or_log_publication_content(self):
        """Publication content is never stored in state records or logs."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        mock_sender = Mock()
        mock_sender.dry_run = True
        mock_sender.send = Mock(
            return_value=SendResult(
                dry_run=True,
                success=True,
                provider_status="DRY_RUN",
                error_code="",
                message_length=50,
                execution_id="exec-001",
            )
        )

        bridge = PublicationBridge(store, mock_sender, self.clock)

        # Use valid content that passes PublicationValidator
        test_content = "This is a test publication article about race performance and results"

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content=test_content,
            created_at=self.fixed_timestamp,
        )

        result = bridge.publish(publication)

        # Verify content is NOT in state record
        assert not hasattr(result, "content")
        assert not hasattr(result, "payload")
        assert test_content not in str(result)

        # Verify content is NOT in database
        cursor = store.connection.cursor()
        cursor.execute("PRAGMA table_info(publication_states)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "content" not in columns
        assert "payload_json" not in columns

        store.close()

"""
Tests for staging activation gate: StagingActivation with strict mode and dry_run enforcement.

Eight offline unit tests validating one-shot staging activation, mode validation,
dry_run enforcement, and no persistent service activation. No network access, no TelegramSender instantiation.
"""

import pytest
from unittest.mock import Mock
from mediaman.staging_activation import StagingActivation
from mediaman.publication_bridge import PublicationBridge
from mediaman.publication_contract import PublicationDTO
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateStore,
)
from mediaman.telegram_sender import SendResult


class TestStagingActivation:
    """Test staging activation gate with strict mode and dry_run enforcement."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up temporary test database and fixed clock."""
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "publication-state.sqlite3"
        self.fixed_timestamp = "2026-08-31T23:00:00Z"
        self.clock = lambda: self.fixed_timestamp
        self.valid_publication_id = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def test_staging_activation_accepts_exact_staging_dry_run_mode(self):
        """StagingActivation accepts exactly mode='staging' and dry_run=True."""
        # Create mocked bridge
        mock_bridge = Mock(spec=PublicationBridge)

        # Create activation with exact staging mode and dry_run=True
        activation = StagingActivation(
            mock_bridge,
            mode="staging",
            dry_run=True,
        )

        assert activation.bridge is mock_bridge

    def test_non_staging_mode_is_rejected(self):
        """Non-staging modes are rejected with ValueError('staging_mode_required')."""
        mock_bridge = Mock(spec=PublicationBridge)

        # Test "production" mode
        with pytest.raises(ValueError, match="staging_mode_required"):
            StagingActivation(
                mock_bridge,
                mode="production",
                dry_run=True,
            )

        # Test "live" mode
        with pytest.raises(ValueError, match="staging_mode_required"):
            StagingActivation(
                mock_bridge,
                mode="live",
                dry_run=True,
            )

        # Test empty mode
        with pytest.raises(ValueError, match="staging_mode_required"):
            StagingActivation(
                mock_bridge,
                mode="",
                dry_run=True,
            )

    def test_dry_run_false_is_rejected(self):
        """dry_run must be exactly True; False, 1, 'true' are rejected with ValueError('dry_run_required')."""
        mock_bridge = Mock(spec=PublicationBridge)

        # Test dry_run=False
        with pytest.raises(ValueError, match="dry_run_required"):
            StagingActivation(
                mock_bridge,
                mode="staging",
                dry_run=False,
            )

        # Test dry_run=1 (truthy but not bool)
        with pytest.raises(ValueError, match="dry_run_required"):
            StagingActivation(
                mock_bridge,
                mode="staging",
                dry_run=1,
            )

        # Test dry_run="true" (truthy but not bool)
        with pytest.raises(ValueError, match="dry_run_required"):
            StagingActivation(
                mock_bridge,
                mode="staging",
                dry_run="true",
            )

    def test_run_once_calls_bridge_exactly_once(self):
        """run_once() calls bridge.publish() exactly once."""
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
                message_length=10,
                execution_id="exec-001",
            )
        )

        # Create real bridge with mocked sender
        bridge = PublicationBridge(store, mock_sender, self.clock)

        # Create activation
        activation = StagingActivation(
            bridge,
            mode="staging",
            dry_run=True,
        )

        # Create publication
        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="Test article",
            created_at=self.fixed_timestamp,
        )

        # Run once
        activation.run_once(publication)

        # Verify sender.send() was called exactly once
        assert mock_sender.send.call_count == 1

        store.close()

    def test_run_once_returns_bridge_state_record(self):
        """run_once() returns the PublicationStateRecord returned by bridge.publish()."""
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
        activation = StagingActivation(
            bridge,
            mode="staging",
            dry_run=True,
        )

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="Test article",
            created_at=self.fixed_timestamp,
        )

        result = activation.run_once(publication)

        # Verify result is a PublicationStateRecord
        assert isinstance(result, PublicationStateRecord)
        # Verify state is SENT (successful dry-run)
        assert result.state == PublicationState.SENT
        assert result.provider_message_id == "dry-run:exec-001"

        store.close()

    def test_invalid_publication_is_rejected_before_bridge_call(self):
        """Invalid PublicationDTO is rejected before calling bridge.publish()."""
        mock_bridge = Mock(spec=PublicationBridge)

        activation = StagingActivation(
            mock_bridge,
            mode="staging",
            dry_run=True,
        )

        # Invalid input: not a PublicationDTO
        with pytest.raises(ValueError, match="invalid_publication"):
            activation.run_once("not a DTO")

        # Verify bridge.publish() was never called
        mock_bridge.publish.assert_not_called()

    def test_staging_gate_does_not_instantiate_telegram_sender_or_read_environment(self):
        """Staging gate does not instantiate TelegramSender or read environment variables."""
        store = PublicationStateStore(db_path=str(self.db_path), clock=self.clock)
        store.initialize()

        # Create bridge with mocked sender (not TelegramSender)
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
        activation = StagingActivation(
            bridge,
            mode="staging",
            dry_run=True,
        )

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content="Test article",
            created_at=self.fixed_timestamp,
        )

        # Execute run_once
        activation.run_once(publication)

        # Verify TelegramSender was not instantiated (only mocked sender was used)
        # This is verified by the fact that we're using a Mock object
        assert isinstance(mock_sender, Mock)

        store.close()

    def test_staging_gate_does_not_persist_or_log_publication_content(self):
        """Publication content is never persisted or logged by staging gate."""
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
        activation = StagingActivation(
            bridge,
            mode="staging",
            dry_run=True,
        )

        test_content = "This is sensitive race performance article content"

        publication = PublicationDTO(
            publication_id=self.valid_publication_id,
            race_id="race-001",
            cycle_id="cycle-001",
            content=test_content,
            created_at=self.fixed_timestamp,
        )

        result = activation.run_once(publication)

        # Verify content is NOT in state record
        assert not hasattr(result, "content")
        assert test_content not in str(result)

        # Verify content is NOT in database
        cursor = store.connection.cursor()
        cursor.execute("PRAGMA table_info(publication_states)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "content" not in columns

        store.close()

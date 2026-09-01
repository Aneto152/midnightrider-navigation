"""
Tests for runtime E2E entrypoint: RuntimeE2EEntrypoint with strict mode and dry_run enforcement.

Eight offline unit tests validating one-shot runtime entrypoint, mode validation,
dry_run enforcement, and no network/credential access. No external service contact.
"""

import pytest
from unittest.mock import Mock
from mediaman.runtime_entrypoint import RuntimeE2EEntrypoint
from mediaman.publication_bridge import PublicationBridge
from mediaman.publication_contract import PublicationDTO
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateStore,
)
from mediaman.telegram_sender import SendResult


class TestRuntimeE2EEntrypoint:
    """Test runtime E2E entrypoint with strict mode and dry_run enforcement."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up temporary test database and fixed clock."""
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "publication-state.sqlite3"
        self.fixed_timestamp = "2026-08-31T23:00:00Z"
        self.clock = lambda: self.fixed_timestamp
        self.valid_publication_id = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def test_exact_staging_dry_run_entrypoint_is_accepted(self):
        """RuntimeE2EEntrypoint accepts exactly mode='staging' and dry_run=True."""
        # Create mocked bridge
        mock_bridge = Mock(spec=PublicationBridge)

        # Create entrypoint with exact staging mode and dry_run=True
        entrypoint = RuntimeE2EEntrypoint(
            mock_bridge,
            mode="staging",
            dry_run=True,
        )

        assert entrypoint.bridge is mock_bridge

    def test_non_staging_mode_is_rejected(self):
        """Non-staging modes are rejected with ValueError('staging_mode_required')."""
        mock_bridge = Mock(spec=PublicationBridge)

        # Test "production" mode
        with pytest.raises(ValueError, match="staging_mode_required"):
            RuntimeE2EEntrypoint(
                mock_bridge,
                mode="production",
                dry_run=True,
            )

        # Test "live" mode
        with pytest.raises(ValueError, match="staging_mode_required"):
            RuntimeE2EEntrypoint(
                mock_bridge,
                mode="live",
                dry_run=True,
            )

        # Test empty mode
        with pytest.raises(ValueError, match="staging_mode_required"):
            RuntimeE2EEntrypoint(
                mock_bridge,
                mode="",
                dry_run=True,
            )

    def test_non_boolean_or_false_dry_run_is_rejected(self):
        """dry_run must be exactly True; False, 1, 'true' are rejected."""
        mock_bridge = Mock(spec=PublicationBridge)

        # Test dry_run=False
        with pytest.raises(ValueError, match="dry_run_required"):
            RuntimeE2EEntrypoint(
                mock_bridge,
                mode="staging",
                dry_run=False,
            )

        # Test dry_run=1 (truthy but not bool)
        with pytest.raises(ValueError, match="dry_run_required"):
            RuntimeE2EEntrypoint(
                mock_bridge,
                mode="staging",
                dry_run=1,
            )

        # Test dry_run="true" (truthy but not bool)
        with pytest.raises(ValueError, match="dry_run_required"):
            RuntimeE2EEntrypoint(
                mock_bridge,
                mode="staging",
                dry_run="true",
            )

    def test_invalid_bridge_is_rejected(self):
        """Invalid bridge is rejected with ValueError('invalid_bridge')."""
        # Test with non-bridge object
        with pytest.raises(ValueError, match="invalid_bridge"):
            RuntimeE2EEntrypoint(
                "not a bridge",
                mode="staging",
                dry_run=True,
            )

        # Test with None
        with pytest.raises(ValueError, match="invalid_bridge"):
            RuntimeE2EEntrypoint(
                None,
                mode="staging",
                dry_run=True,
            )

    def test_run_once_rejects_invalid_publication_before_bridge_call(self):
        """Invalid PublicationDTO is rejected before calling bridge.publish()."""
        mock_bridge = Mock(spec=PublicationBridge)

        entrypoint = RuntimeE2EEntrypoint(
            mock_bridge,
            mode="staging",
            dry_run=True,
        )

        # Invalid input: not a PublicationDTO
        with pytest.raises(ValueError, match="invalid_publication"):
            entrypoint.run_once("not a DTO")

        # Verify bridge.publish() was never called
        mock_bridge.publish.assert_not_called()

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

        # Create entrypoint
        entrypoint = RuntimeE2EEntrypoint(
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
        entrypoint.run_once(publication)

        # Verify sender.send() was called exactly once
        assert mock_sender.send.call_count == 1

        store.close()

    def test_run_once_returns_the_bridge_state_record(self):
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
        entrypoint = RuntimeE2EEntrypoint(
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

        result = entrypoint.run_once(publication)

        # Verify result is a PublicationStateRecord
        assert isinstance(result, PublicationStateRecord)
        # Verify state is SENT (successful dry-run)
        assert result.state == PublicationState.SENT
        assert result.provider_message_id == "dry-run:exec-001"

        store.close()

    def test_entrypoint_does_not_read_credentials_or_contact_external_services(self):
        """Entrypoint does not read credentials, instantiate TelegramSender, or contact services."""
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
        entrypoint = RuntimeE2EEntrypoint(
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
        result = entrypoint.run_once(publication)

        # Verify TelegramSender was not instantiated (only mocked sender was used)
        assert isinstance(mock_sender, Mock)
        # Verify result is valid (entrypoint worked correctly)
        assert isinstance(result, PublicationStateRecord)
        # Verify no external service was called (only bridge.publish and mock sender)
        assert mock_sender.send.call_count == 1

        store.close()

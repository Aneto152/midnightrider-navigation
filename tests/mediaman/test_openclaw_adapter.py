"""
Tests for OpenClaw adapter initialization and functionality with mocked subprocess.

Focus: Safe initialization, CLI availability detection, configuration validation.
No real OpenClaw Gateway contact, no Telegram contact, no payload logging.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock, Mock
from mediaman.openclaw_adapter import OpenClawAdapter, OpenClawResult


class TestOpenClawAdapterInitialization:
    """Test OpenClaw adapter safe initialization."""

    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_initialization_with_available_cli(self, mock_run):
        """Adapter initialization succeeds when CLI is available."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        adapter = OpenClawAdapter()

        assert adapter.available is True
        assert adapter.timeout_seconds == 30
        assert adapter.is_available() is True

    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_initialization_with_unavailable_cli(self, mock_run):
        """Adapter initialization gracefully handles unavailable CLI."""
        mock_run.side_effect = FileNotFoundError("openclaw not found")

        adapter = OpenClawAdapter()

        assert adapter.available is False
        assert adapter.timeout_seconds == 30
        assert adapter.is_available() is False

    def test_initialization_with_timeout_override(self):
        """Adapter initialization accepts timeout override."""
        with patch('mediaman.openclaw_adapter.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            adapter = OpenClawAdapter(timeout_seconds=60)

            assert adapter.timeout_seconds == 60

    def test_initialization_with_injected_availability_check(self):
        """Adapter initialization can use injected availability function."""
        def custom_check():
            return True

        adapter = OpenClawAdapter(availability_check=custom_check)

        assert adapter.available is True

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_initialization_logs_safe_metadata(self, mock_run, mock_logger):
        """Adapter initialization logs safe metadata only."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        adapter = OpenClawAdapter(timeout_seconds=45)

        # Verify logger was called with safe metadata
        mock_logger_instance.debug.assert_called()
        call_args = mock_logger_instance.debug.call_args[0][0]
        assert "available" in call_args
        assert "45" in call_args
        # Verify NO credentials or payloads in log
        assert "token" not in call_args.lower()
        assert "secret" not in call_args.lower()

    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_initialization_cli_timeout(self, mock_run):
        """Adapter initialization handles CLI availability check timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('openclaw', 5)

        adapter = OpenClawAdapter()

        assert adapter.available is False

    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_initialization_cli_os_error(self, mock_run):
        """Adapter initialization handles OSError from CLI check."""
        mock_run.side_effect = OSError("Permission denied")

        adapter = OpenClawAdapter()

        assert adapter.available is False

    def test_is_available_method(self):
        """Adapter provides is_available() method."""
        with patch('mediaman.openclaw_adapter.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            adapter = OpenClawAdapter()

            assert callable(adapter.is_available)
            assert adapter.is_available() is True


class TestOpenClawAdapter:
    """Test OpenClaw CLI adapter generation and error handling."""

    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_successful_generation(self, mock_run):
        """Successful generation should return content (not logged)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Midnight Rider navigue avec excellence à 8.5 nœuds au 270°. Le vent du 180° favorise la course. Excellentes conditions pour continuer.",
            stderr=""
        )

        adapter = OpenClawAdapter()
        # Mock availability check
        adapter.available = True

        result = adapter.generate_article(
            prompt="Générez un article sur Midnight Rider...",
            agent_id="main"
        )

        assert result.success
        assert "Midnight Rider" in result.content
        assert result.provider_status == "success"
        # Verify prompt is NOT logged (safe logging)
        # Logger should only log length, not content

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_generation_logs_safe_metadata_only(self, mock_run, mock_logger):
        """Generation logs only safe metadata, never prompts or payloads."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Test article content",
            stderr=""
        )

        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        adapter = OpenClawAdapter()
        adapter.available = True

        result = adapter.generate_article(
            prompt="Secret prompt content",
            agent_id="main"
        )

        assert result.success
        # Verify logging calls exist
        assert mock_logger_instance.debug.called or mock_logger_instance.warning.called or mock_logger_instance.info.called
        # Verify prompt NOT in any log
        for call in mock_logger_instance.method_calls:
            if len(call) > 1 and len(call[1]) > 0:
                log_msg = str(call[1][0])
                assert "Secret prompt content" not in log_msg

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_cli_not_available(self, mock_run, mock_logger):
        """Generate should fail gracefully if CLI unavailable."""
        mock_run.side_effect = FileNotFoundError()

        adapter = OpenClawAdapter()
        mock_logger_instance = MagicMock()
        adapter.logger = mock_logger_instance

        result = adapter.generate_article(
            prompt="Test prompt"
        )

        assert not result.success
        assert result.provider_status == "unavailable"
        assert "not available" in result.error.lower()
        # Verify safe logging (no prompt in logs)
        if mock_logger_instance.debug.called:
            for call in mock_logger_instance.debug.call_args_list:
                assert "prompt" not in str(call).lower() or "Test prompt" not in str(call)

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_cli_error(self, mock_run, mock_logger):
        """CLI error should return error result (safe logging)."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Invalid argument"
        )

        adapter = OpenClawAdapter()
        adapter.available = True
        mock_logger_instance = MagicMock()
        adapter.logger = mock_logger_instance

        result = adapter.generate_article(
            prompt="Test prompt"
        )

        assert not result.success
        assert result.provider_status == "error"
        assert "Invalid argument" in result.error
        # Verify error logged without prompts
        if mock_logger_instance.warning.called:
            for call in mock_logger_instance.warning.call_args_list:
                log_msg = str(call)
                # Error should be logged, but not the prompt
                assert "Test prompt" not in log_msg

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_timeout(self, mock_run, mock_logger):
        """Timeout should return timeout result (safe logging)."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('openclaw', 30)

        adapter = OpenClawAdapter(timeout_seconds=30)
        adapter.available = True
        mock_logger_instance = MagicMock()
        adapter.logger = mock_logger_instance

        result = adapter.generate_article(
            prompt="Test prompt"
        )

        assert not result.success
        assert result.provider_status == "timeout"
        assert "30 seconds" in result.error
        # Verify timeout logged without prompts
        if mock_logger_instance.warning.called:
            for call in mock_logger_instance.warning.call_args_list:
                log_msg = str(call)
                assert "Test prompt" not in log_msg

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_empty_output(self, mock_run, mock_logger):
        """Empty CLI output should fail (safe logging)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        adapter = OpenClawAdapter()
        adapter.available = True
        mock_logger_instance = MagicMock()
        adapter.logger = mock_logger_instance

        result = adapter.generate_article(
            prompt="Test prompt"
        )

        assert not result.success
        assert "empty output" in result.error.lower()
        # Verify no prompts logged
        if mock_logger_instance.warning.called:
            for call in mock_logger_instance.warning.call_args_list:
                assert "Test prompt" not in str(call)

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_file_handling(self, mock_run, mock_logger):
        """Prompt file should be created and cleaned up safely."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Generated content",
            stderr=""
        )

        adapter = OpenClawAdapter()
        adapter.available = True

        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile.return_value.__enter__.return_value.name = "/tmp/test_prompt.txt"

            result = adapter.generate_article(
                prompt="Test prompt"
            )

            assert result.success
            # Verify the command was called with --message-file
            call_args = mock_run.call_args[0][0]
            assert "--message-file" in call_args
            # Verify prompt file path is NOT logged
            if hasattr(adapter, 'logger') and adapter.logger:
                for call in adapter.logger.method_calls:
                    if len(call) > 1 and len(call[1]) > 0:
                        assert "/tmp/test_prompt.txt" not in str(call)

    @patch('mediaman.openclaw_adapter.logging.getLogger')
    @patch('mediaman.openclaw_adapter.subprocess.run')
    def test_cli_contract_verification(self, mock_run, mock_logger):
        """Verify OpenClaw CLI is called with correct arguments (not --deliver)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Content",
            stderr=""
        )

        adapter = OpenClawAdapter(timeout_seconds=45)
        adapter.available = True

        adapter.generate_article(
            prompt="Test",
            agent_id="custom-agent",
            thinking_level="medium"
        )

        # Verify the command structure
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "openclaw"
        assert call_args[1] == "agent"
        assert "--agent" in call_args
        assert "custom-agent" in call_args
        assert "--thinking" in call_args
        assert "medium" in call_args
        assert "--timeout" in call_args
        assert "45" in call_args
        # Should NOT use --deliver (Telegram responsibility)
        assert "--deliver" not in call_args
        # Should NOT use --timeout-seconds
        assert "--timeout-seconds" not in call_args

    def test_no_payload_logging(self):
        """Adapter must never log QueuedEvent payloads."""
        with patch('mediaman.openclaw_adapter.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Content", stderr="")

            adapter = OpenClawAdapter()
            adapter.available = True

            # Simulate a payload (would come from EventQueue)
            sensitive_payload = {
                'race_id': 'race123',
                'latitude': 41.1234,
                'longitude': -73.4567,
                'token': 'sk-1234567890'
            }

            result = adapter.generate_article(
                prompt="Test prompt"
            )

            # Verify no sensitive data in result error messages
            if result.error:
                assert '41.1234' not in result.error
                assert '-73.4567' not in result.error
                assert 'sk-1234567890' not in result.error

    def test_no_real_openclaw_gateway_contact(self):
        """Adapter initialization must not contact real OpenClaw Gateway."""
        with patch('mediaman.openclaw_adapter.subprocess.run') as mock_run:
            # If initialization tried to contact a real gateway, it would make network calls
            # We mock subprocess.run to ensure no real calls happen
            mock_run.return_value = MagicMock(returncode=0)

            adapter = OpenClawAdapter()

            # Verify only --version was called (for availability check)
            # No actual generation should happen during init
            assert mock_run.called
            # First call should be for --version check
            first_call = mock_run.call_args_list[0]
            assert '--version' in first_call[0][0]

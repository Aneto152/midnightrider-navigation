"""
Tests for historical_entrypoint.py — one-shot local dry-run message generation.

Tests the complete historical flow from environment variables through dry-run publication.
No live InfluxDB, no real credentials, no Telegram network calls.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestHistoricalEntrypoint:
    """Test historical entrypoint module."""

    def test_historical_entrypoint_module_exists(self):
        """Verify historical_entrypoint.py exists and is importable."""
        from mediaman import historical_entrypoint
        assert hasattr(historical_entrypoint, 'main')
        assert callable(historical_entrypoint.main)

    def test_historical_entrypoint_requires_provider_env(self):
        """Entrypoint requires MEDIAMAN_CONTENT_PROVIDER=historical_mcp."""
        from mediaman.historical_entrypoint import main
        
        with patch.dict(os.environ, {}, clear=True):
            result = main()
            assert result != 0, "Should fail without MEDIAMAN_CONTENT_PROVIDER"

    def test_historical_entrypoint_requires_as_of_env(self):
        """Entrypoint requires MEDIAMAN_HISTORICAL_AS_OF."""
        from mediaman.historical_entrypoint import main
        
        with patch.dict(os.environ, {
            'MEDIAMAN_CONTENT_PROVIDER': 'historical_mcp',
            'DRY_RUN': 'true'
        }, clear=True):
            result = main()
            assert result != 0, "Should fail without MEDIAMAN_HISTORICAL_AS_OF"

    def test_historical_entrypoint_requires_window_seconds_env(self):
        """Entrypoint requires MEDIAMAN_HISTORICAL_WINDOW_SECONDS."""
        from mediaman.historical_entrypoint import main
        
        with patch.dict(os.environ, {
            'MEDIAMAN_CONTENT_PROVIDER': 'historical_mcp',
            'MEDIAMAN_HISTORICAL_AS_OF': '2026-09-01T12:00:00Z',
            'DRY_RUN': 'true'
        }, clear=True):
            result = main()
            assert result != 0, "Should fail without MEDIAMAN_HISTORICAL_WINDOW_SECONDS"

    def test_historical_entrypoint_requires_mcp_server_path_env(self):
        """Entrypoint requires MEDIAMAN_MCP_SERVER_PATH."""
        from mediaman.historical_entrypoint import main
        
        with patch.dict(os.environ, {
            'MEDIAMAN_CONTENT_PROVIDER': 'historical_mcp',
            'MEDIAMAN_HISTORICAL_AS_OF': '2026-09-01T12:00:00Z',
            'MEDIAMAN_HISTORICAL_WINDOW_SECONDS': '60',
            'DRY_RUN': 'true'
        }, clear=True):
            result = main()
            assert result != 0, "Should fail without MEDIAMAN_MCP_SERVER_PATH"

    def test_historical_entrypoint_requires_dry_run_true(self):
        """Entrypoint requires DRY_RUN=true (exact string match)."""
        from mediaman.historical_entrypoint import main
        from pathlib import Path
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with patch.dict(os.environ, {
                'MEDIAMAN_CONTENT_PROVIDER': 'historical_mcp',
                'MEDIAMAN_HISTORICAL_AS_OF': '2026-09-01T12:00:00Z',
                'MEDIAMAN_HISTORICAL_WINDOW_SECONDS': '60',
                'MEDIAMAN_MCP_SERVER_PATH': tmp_path,
                'DRY_RUN': 'false'  # Wrong value
            }, clear=True):
                result = main()
                assert result != 0, "Should fail with DRY_RUN != 'true'"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_dry_run_sender_is_offline_only(self):
        """DryRunSender must not instantiate TelegramSender."""
        from mediaman.historical_entrypoint import DryRunSender
        
        sender = DryRunSender()
        assert sender.dry_run is True
        
        result = sender.send("test message")
        assert result.dry_run is True
        assert result.success is True
        assert result.provider_status == "DRY_RUN"
        assert result.provider_message_id.startswith("dry-run:")
        assert result.error_code is None

    def test_dry_run_sender_never_reads_credentials(self):
        """DryRunSender must not read real Telegram credentials."""
        from mediaman.historical_entrypoint import DryRunSender
        
        with patch.dict(os.environ, {}, clear=True):
            # No TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID
            sender = DryRunSender()
            result = sender.send("test")
            # Should still work without credentials
            assert result.success is True
            assert result.dry_run is True

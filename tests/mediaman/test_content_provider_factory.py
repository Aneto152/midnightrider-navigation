"""
Tests for content provider factory with explicit dependency injection.

Verifies:
1. test provider is returned without collector
2. historical_mcp provider requires collector injection
3. missing collector raises clear ValueError
4. factory does not silently fall back
"""

import pytest
from unittest.mock import Mock
from mediaman.content_provider import (
    get_content_provider,
    TestContentProvider,
    HistoricalMCPProvider,
)


class TestContentProviderFactory:
    """Test factory with explicit dependency injection."""

    def test_factory_returns_test_provider_by_default(self):
        """get_content_provider() with no args returns TestContentProvider."""
        provider = get_content_provider(provider_name="test")
        assert isinstance(provider, TestContentProvider)

    def test_factory_test_provider_needs_no_collector(self):
        """TestContentProvider does not require collector."""
        provider = get_content_provider(
            provider_name="test",
            mcp_collector=None
        )
        assert isinstance(provider, TestContentProvider)

    def test_factory_requires_collector_for_historical_mcp(self):
        """get_content_provider(provider_name='historical_mcp') without collector raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_content_provider(
                provider_name="historical_mcp",
                mcp_collector=None
            )

        error_msg = str(exc_info.value).lower()
        assert "mcp_collector" in error_msg or "collector" in error_msg
        assert "required" in error_msg or "injection" in error_msg or "none" in error_msg

    def test_factory_injects_collector_for_historical_mcp(self):
        """get_content_provider(provider_name='historical_mcp', mcp_collector=<mock>) returns HistoricalMCPProvider."""
        mock_collector = Mock()
        provider = get_content_provider(
            provider_name="historical_mcp",
            mcp_collector=mock_collector
        )

        assert isinstance(provider, HistoricalMCPProvider)
        assert provider.mcp_collector is mock_collector

    def test_factory_rejects_unknown_provider(self):
        """get_content_provider with unknown provider_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_content_provider(provider_name="unknown_provider")

        assert "unknown" in str(exc_info.value).lower()

    def test_factory_with_no_arguments_reads_env_and_defaults_to_test(self):
        """get_content_provider() with no arguments defaults to test provider."""
        import os

        # Clear env var if present
        old_env = os.environ.pop("MEDIAMAN_CONTENT_PROVIDER", None)

        try:
            provider = get_content_provider()
            assert isinstance(provider, TestContentProvider)
        finally:
            # Restore env var
            if old_env is not None:
                os.environ["MEDIAMAN_CONTENT_PROVIDER"] = old_env

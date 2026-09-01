"""
Tests for HistoricalMCPProvider — historical content generation from MCP collector.

Tests the historical provider with mocked MCP collector and synthetic data only.
No live InfluxDB, no real credentials, no Telegram.
"""

import pytest
from unittest.mock import Mock, MagicMock
from mediaman.content_provider import HistoricalMCPProvider
from mediaman.mcp_collector import (
    CollectionResult,
    CollectionStatus,
    NavigationFact,
    Provenance,
    MCPCollector,
)


class TestHistoricalProviderIntegration:
    """Test HistoricalMCPProvider with mocked collector."""

    def test_provider_requires_injected_collector(self):
        """Provider requires MCP collector injection."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalMCPProvider(mcp_collector=None)
        
        assert "MCPCollector" in str(exc_info.value) or "collector" in str(exc_info.value).lower()

    def test_provider_rejects_direct_get_content(self):
        """Provider rejects direct get_content() call (historical context required)."""
        provider = HistoricalMCPProvider(mcp_collector=Mock())
        
        with pytest.raises(NotImplementedError) as exc_info:
            provider.get_content(
                race_id="race-id",
                cycle_timestamp="2026-09-01T12:00:00Z"
            )
        assert "historical request context" in str(exc_info.value)

    def test_provider_generates_french_article_with_valid_facts(self):
        """Provider generates French article with valid historical facts."""
        # Create mocked collector result
        mock_collector = Mock(spec=MCPCollector)
        
        provenance = Provenance(
            tool_public_id="racing.get_historical_snapshot",
            server_name="racing",
            wire_tool_name="get_historical_snapshot",
            source_id="mcp:racing:historical",
            source_timestamp="2026-09-01T12:00:00Z",
            observed_at="2026-09-01T12:00:01Z",
            freshness_limit_seconds=None,
            validation_status="valid"
        )
        
        result = CollectionResult(
            status=CollectionStatus.COMPLETE,
            race_id="historical",
            facts=[
                NavigationFact(
                    field_name="latitude",
                    value=41.2619,
                    unit="decimal_degrees",
                    provenance=provenance
                ),
                NavigationFact(
                    field_name="longitude",
                    value=-73.1337,
                    unit="decimal_degrees",
                    provenance=provenance
                ),
                NavigationFact(
                    field_name="speed_over_ground",
                    value=5.5,
                    unit="m/s",
                    provenance=provenance
                ),
                NavigationFact(
                    field_name="course_over_ground",
                    value=180.0,
                    unit="degrees_true",
                    provenance=provenance
                ),
            ],
            collection_start_at="2026-09-01T12:00:00Z",
            collection_end_at="2026-09-01T12:00:01Z",
        )
        
        mock_collector.collect_historical.return_value = result
        
        provider = HistoricalMCPProvider(mcp_collector=mock_collector)
        content = provider.get_content_for_historical(
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=60
        )
        
        # Verify French content generated
        assert "🏁" in content
        assert "Midnight Rider" in content
        assert "Historique" in content
        assert "é" in content or "è" in content or "ê" in content  # French accents
        assert "41.2619" in content
        assert "-73.1337" in content
        assert "5.5" in content
        assert "180.0" in content
        assert "aucun message" in content.lower()  # No real Telegram message
        assert "Telegram" in content

    def test_provider_fails_on_missing_mandatory_facts(self):
        """Provider fails closed when mandatory facts missing."""
        mock_collector = Mock(spec=MCPCollector)
        
        # Result with missing latitude
        result = CollectionResult(
            status=CollectionStatus.PARTIAL,
            race_id="historical",
            facts=[
                NavigationFact(
                    field_name="longitude",
                    value=-73.1337,
                    unit="decimal_degrees",
                    provenance=Provenance(
                        tool_public_id="racing.get_historical_snapshot",
                        server_name="racing",
                        wire_tool_name="get_historical_snapshot",
                        source_id="mcp:racing:historical"
                    )
                ),
            ],
            collection_start_at="2026-09-01T12:00:00Z",
            collection_end_at="2026-09-01T12:00:01Z",
        )
        
        mock_collector.collect_historical.return_value = result
        
        provider = HistoricalMCPProvider(mcp_collector=mock_collector)
        
        with pytest.raises(ValueError) as exc_info:
            provider.get_content_for_historical(
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=60
            )
        assert "mandatory" in str(exc_info.value).lower()

    def test_provider_fails_on_collection_failure(self):
        """Provider fails closed when collection fails."""
        mock_collector = Mock(spec=MCPCollector)
        
        result = CollectionResult(
            status=CollectionStatus.FAILED,
            race_id="historical",
            facts=[],
            errors=["Historical snapshot request failed"],
            collection_start_at="2026-09-01T12:00:00Z",
            collection_end_at="2026-09-01T12:00:01Z",
        )
        
        mock_collector.collect_historical.return_value = result
        
        provider = HistoricalMCPProvider(mcp_collector=mock_collector)
        
        with pytest.raises(ValueError) as exc_info:
            provider.get_content_for_historical(
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=60
            )
        assert "failed" in str(exc_info.value).lower()

    def test_provider_validates_output(self):
        """Provider validates generated content."""
        provider = HistoricalMCPProvider()
        
        # Valid French content
        valid_content = "Ceci est un article en français avec des caractères accentués: é è ê ç"
        is_valid, error = provider.validate(valid_content)
        assert is_valid is True
        assert error == ""

    def test_provider_validates_rejects_non_french(self):
        """Provider rejects non-French content."""
        provider = HistoricalMCPProvider()
        
        # English content (no French characters)
        english_content = "This is an English article without any French characters."
        is_valid, error = provider.validate(english_content)
        assert is_valid is False
        assert "French" in error

    def test_provider_validates_rejects_credentials(self):
        """Provider rejects content containing credentials."""
        provider = HistoricalMCPProvider(Mock())
        
        # Content with credentials (using neutral marker)
        bad_content = "Article en français avec token=[REDACTED] incorporé"
        is_valid, error = provider.validate(bad_content)
        assert is_valid is False
        assert "credential" in error.lower()

    def test_provider_call_counter_increments(self):
        """Provider increments call counter."""
        mock_collector = Mock(spec=MCPCollector)
        
        provenance = Provenance(
            tool_public_id="racing.get_historical_snapshot",
            server_name="racing",
            wire_tool_name="get_historical_snapshot",
            source_id="mcp:racing:historical"
        )
        
        result = CollectionResult(
            status=CollectionStatus.COMPLETE,
            race_id="historical",
            facts=[
                NavigationFact(
                    field_name="latitude",
                    value=41.0,
                    unit="decimal_degrees",
                    provenance=provenance
                ),
                NavigationFact(
                    field_name="longitude",
                    value=-73.0,
                    unit="decimal_degrees",
                    provenance=provenance
                ),
            ],
            collection_start_at="2026-09-01T12:00:00Z",
            collection_end_at="2026-09-01T12:00:01Z",
        )
        
        mock_collector.collect_historical.return_value = result
        
        provider = HistoricalMCPProvider(mcp_collector=mock_collector)
        
        assert provider.call_count == 0
        
        provider.get_content_for_historical(
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=60
        )
        
        assert provider.call_count == 1
        assert "Historique 1" in provider.get_content_for_historical(
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=60
        )

    def test_provider_invalid_historical_request_rejected(self):
        """Provider rejects invalid historical request parameters."""
        mock_collector = Mock(spec=MCPCollector)
        provider = HistoricalMCPProvider(mcp_collector=mock_collector)
        
        with pytest.raises(ValueError) as exc_info:
            provider.get_content_for_historical(
                as_of_utc="not-a-timestamp",
                window_seconds=60
            )
        assert "Invalid historical request" in str(exc_info.value)

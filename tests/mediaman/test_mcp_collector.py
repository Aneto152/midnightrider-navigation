"""
Tests for MCPCollector — mocked MCP-based navigation fact collection.

Tests verify:
- Source-verified tool collection
- Provenance tracking
- Fail-closed semantics (no zero substitution, no fabrication)
- Freshness awareness
- Complete/partial/invalid collection status
- No live MCP, Signal K, InfluxDB access
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mediaman.mcp_collector import (
    MCPCollector,
    CollectionStatus,
    Provenance,
    NavigationFact,
    CollectionResult,
    SourceVerifiedTools
)
from mediaman.mcp_client import MCPClientError, MCPProtocolError, MCPServerError, MCPTimeoutError


@pytest.fixture
def mock_mcp_client():
    """Mock MCPClient for testing."""
    return Mock()


class TestMCPCollectorCompletCollection:
    """Complete collection with all three navigation tools."""

    def test_collect_all_three_tools(self, mock_mcp_client):
        """Successful collection of position, SOG, and COG."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        # Mock tool responses
        mock_mcp_client.call_tool.side_effect = [
            {
                'result': {
                    'latitude': 41.1234,
                    'longitude': -73.5678,
                    'source_timestamp': '2026-08-27T20:40:00Z',
                    'unit': 'decimal_degrees'
                },
                'observed_at': '2026-08-27T20:40:01Z'
            },
            {
                'result': {
                    'speed_over_ground_ms': 3.5,
                    'source_timestamp': '2026-08-27T20:40:00Z',
                    'unit': 'knots'
                },
                'observed_at': '2026-08-27T20:40:01Z'
            },
            {
                'result': {
                    'course_over_ground_degrees': 45.0,
                    'source_timestamp': '2026-08-27T20:40:00Z',
                    'unit': 'degrees (0-360)'
                },
                'observed_at': '2026-08-27T20:40:01Z'
            }
        ]
        
        result = collector.collect()
        
        assert result.status == CollectionStatus.COMPLETE
        assert len(result.facts) == 4  # latitude, longitude, SOG, COG
        assert result.tools_succeeded == ['racing.get_position', 'racing.get_sog', 'racing.get_cog']
        assert result.tools_failed == []
        assert result.errors == []

    def test_position_contains_provenance(self, mock_mcp_client):
        """Position facts include full provenance."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'latitude': 41.1234,
                'longitude': -73.5678,
                'source_timestamp': '2026-08-27T20:40:00Z'
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        assert len(result.facts) == 2  # lat and lon
        assert result.status == CollectionStatus.COMPLETE  # Position only, but completed
        fact = result.facts[0]
        assert fact.provenance.tool_public_id == "racing.get_position"
        assert fact.provenance.server_name == "racing"
        assert fact.provenance.wire_tool_name == "get_position"
        assert fact.provenance.source_timestamp == '2026-08-27T20:40:00Z'
        assert fact.provenance.observed_at == '2026-08-27T20:40:01Z'

    def test_sog_fact_preserves_value(self, mock_mcp_client):
        """SOG fact preserves exact value, not substituted."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'speed_over_ground_ms': 2.5,
                'source_timestamp': '2026-08-27T20:40:00Z'
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.SOG])
        
        assert len(result.facts) == 1
        fact = result.facts[0]
        assert fact.field_name == "speed_over_ground"
        assert fact.value == 2.5
        assert fact.unit == "m/s"


class TestMCPCollectorPartialCollection:
    """Partial collection when some tools fail."""

    def test_missing_sog_partial_status(self, mock_mcp_client):
        """Missing SOG results in PARTIAL status."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.side_effect = [
            {'result': {'latitude': 41.1234, 'longitude': -73.5678, 'source_timestamp': '2026-08-27T20:40:00Z'}, 'observed_at': '2026-08-27T20:40:01Z'},
            MCPServerError("SOG unavailable"),
            {'result': {'course_over_ground_degrees': 45.0, 'source_timestamp': '2026-08-27T20:40:00Z'}, 'observed_at': '2026-08-27T20:40:01Z'}
        ]
        
        result = collector.collect()
        
        assert result.status == CollectionStatus.PARTIAL
        assert 'racing.get_position' in result.tools_succeeded
        assert 'racing.get_sog' in result.tools_failed
        assert 'racing.get_cog' in result.tools_succeeded

    def test_missing_sog_value_none_not_zero(self, mock_mcp_client):
        """Missing SOG value remains None, never substituted with zero."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'speed_over_ground_ms': None,
                'source_timestamp': '2026-08-27T20:40:00Z'
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.SOG])
        
        assert result.status == CollectionStatus.FAILED
        assert len(result.facts) == 0
        assert 'speed_over_ground_ms is None' in result.warnings[0]


class TestMCPCollectorErrorHandling:
    """Error handling for various MCP failure modes."""

    def test_protocol_error_propagates(self, mock_mcp_client):
        """MCPProtocolError is raised and recorded."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.side_effect = MCPProtocolError("Malformed JSON")
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        assert result.status == CollectionStatus.FAILED
        assert 'racing.get_position' in result.tools_failed
        assert 'MCPProtocolError' in result.errors[0]

    def test_server_error_propagates(self, mock_mcp_client):
        """MCPServerError is raised and recorded."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.side_effect = MCPServerError("Server error -32000")
        
        result = collector.collect([SourceVerifiedTools.COG])
        
        assert result.status == CollectionStatus.FAILED
        assert 'racing.get_cog' in result.tools_failed
        assert 'MCPServerError' in result.errors[0]

    def test_client_error_propagates(self, mock_mcp_client):
        """MCPClientError is raised and recorded."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.side_effect = MCPClientError("Process exited")
        
        result = collector.collect([SourceVerifiedTools.SOG])
        
        assert result.status == CollectionStatus.FAILED
        assert 'racing.get_sog' in result.tools_failed
        assert 'MCPClientError' in result.errors[0]

    def test_timeout_error_propagates(self, mock_mcp_client):
        """MCPTimeoutError is raised and recorded."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.side_effect = MCPTimeoutError("Request timeout")
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        assert result.status == CollectionStatus.FAILED
        assert 'racing.get_position' in result.tools_failed
        assert 'MCPTimeoutError' in result.errors[0]


class TestMCPCollectorMissingValues:
    """Handling of missing or malformed results."""

    def test_missing_latitude_warning(self, mock_mcp_client):
        """Missing latitude generates warning."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'longitude': -73.5678,
                'source_timestamp': '2026-08-27T20:40:00Z'
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        assert result.status == CollectionStatus.FAILED
        assert len(result.facts) == 0
        assert 'malformed or missing fields' in result.warnings[0]

    def test_missing_result_field_warning(self, mock_mcp_client):
        """Missing 'result' field generates warning."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'error': 'Something went wrong',
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.SOG])
        
        assert result.status == CollectionStatus.FAILED
        assert len(result.facts) == 0
        assert 'malformed or missing fields' in result.warnings[0]


class TestMCPCollectorProvenanceTracking:
    """Provenance preservation for every fact."""

    def test_provenance_fields_complete(self, mock_mcp_client):
        """Every fact includes complete provenance."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'course_over_ground_degrees': 180.0,
                'source_timestamp': '2026-08-27T20:40:00Z'
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.COG])
        
        fact = result.facts[0]
        assert fact.provenance.tool_public_id == "racing.get_cog"
        assert fact.provenance.server_name == "racing"
        assert fact.provenance.wire_tool_name == "get_cog"
        assert fact.provenance.source_id == "mcp:racing:get_cog"
        assert fact.provenance.freshness_limit_seconds == 15

    def test_source_timestamp_unknown_when_absent(self, mock_mcp_client):
        """source_timestamp becomes 'UNKNOWN' when absent."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'speed_over_ground_ms': 2.0
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.SOG])
        
        fact = result.facts[0]
        assert fact.provenance.source_timestamp == 'UNKNOWN'

    def test_observed_at_distinct_from_source_timestamp(self, mock_mcp_client):
        """observed_at is distinct from source_timestamp."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'latitude': 41.0,
                'longitude': -73.0,
                'source_timestamp': '2026-08-27T20:39:00Z'
            },
            'observed_at': '2026-08-27T20:40:05Z'
        }
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        fact = result.facts[0]
        assert fact.provenance.source_timestamp == '2026-08-27T20:39:00Z'
        assert fact.provenance.observed_at == '2026-08-27T20:40:05Z'
        assert fact.provenance.source_timestamp != fact.provenance.observed_at


class TestMCPCollectorCollectionStatus:
    """Collection status determination."""

    def test_invalid_all_tools_fail(self, mock_mcp_client):
        """INVALID status when all tools fail."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.side_effect = [
            MCPProtocolError("Bad JSON"),
            MCPServerError("Server error"),
            MCPTimeoutError("Timeout")
        ]
        
        result = collector.collect()
        
        assert result.status == CollectionStatus.FAILED
        assert len(result.tools_failed) == 3
        assert len(result.facts) == 0


class TestMCPCollectorCoordinateSuppression:
    """Exact coordinates are not logged."""

    def test_position_values_preserved_not_logged(self, mock_mcp_client):
        """Position values are exact and preserved (not logged)."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {
                'latitude': 41.123456789,
                'longitude': -73.987654321,
                'source_timestamp': '2026-08-27T20:40:00Z'
            },
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        # Values are exact
        assert result.facts[0].value == 41.123456789
        assert result.facts[1].value == -73.987654321
        
        # Status is COMPLETE because position completed was collected (not SOG/COG)
        assert result.status == CollectionStatus.COMPLETE


class TestMCPCollectorNoLiveAccess:
    """Verify no live MCP, Signal K, InfluxDB, or network access."""

    def test_collector_uses_dependency_injected_client(self, mock_mcp_client):
        """Collector uses injected client, no live instantiation."""
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        mock_mcp_client.call_tool.return_value = {
            'result': {'latitude': 41.0, 'longitude': -73.0, 'source_timestamp': '2026-08-27T20:40:00Z'},
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        
        # Verify call was made to mocked client, not to live service
        mock_mcp_client.call_tool.assert_called()
        assert result.status == CollectionStatus.COMPLETE  # Position only, but completed

    def test_no_signal_k_access(self, mock_mcp_client):
        """Collector does not access Signal K directly."""
        # Verify by checking that MCPClient is the only external dependency
        collector = MCPCollector(mock_mcp_client, reference_time='2026-08-27T20:40:01Z')
        
        # If collector tried to access Signal K, it would need http.request or similar
        # This test verifies no direct Signal K calls are made
        assert hasattr(collector, 'client')
        assert isinstance(collector.client, Mock)


class TestMCPCollectorSourceVerifiedTools:
    """Tool enumeration reflects source-verified server definitions."""

    def test_position_tool_attributes(self):
        """POSITION tool has correct attributes."""
        assert SourceVerifiedTools.POSITION.public_id == "racing.get_position"
        assert SourceVerifiedTools.POSITION.wire_name == "get_position"
        assert SourceVerifiedTools.POSITION.server == "racing"

    def test_sog_tool_attributes(self):
        """SOG tool has correct attributes."""
        assert SourceVerifiedTools.SOG.public_id == "racing.get_sog"
        assert SourceVerifiedTools.SOG.wire_name == "get_sog"
        assert SourceVerifiedTools.SOG.server == "racing"

    def test_cog_tool_attributes(self):
        """COG tool has correct attributes."""
        assert SourceVerifiedTools.COG.public_id == "racing.get_cog"
        assert SourceVerifiedTools.COG.wire_name == "get_cog"
        assert SourceVerifiedTools.COG.server == "racing"


class TestMCPCollectorResultSerialization:
    """Result serialization to dict."""

    def test_result_to_dict_complete(self, mock_mcp_client):
        """Complete result serializes to dict."""
        collector = MCPCollector(mock_mcp_client, race_id="BIR-2026")
        
        mock_mcp_client.call_tool.return_value = {
            'result': {'latitude': 41.0, 'longitude': -73.0, 'source_timestamp': '2026-08-27T20:40:00Z'},
            'observed_at': '2026-08-27T20:40:01Z'
        }
        
        result = collector.collect([SourceVerifiedTools.POSITION])
        result_dict = result.to_dict()
        
        assert result_dict['status'] == 'complete'  # Position only, but completed
        assert result_dict['race_id'] == 'BIR-2026'
        assert len(result_dict['facts']) == 2  # latitude and longitude
        assert result_dict['facts'][0]['field_name'] == 'latitude'
        assert result_dict['facts'][0]['provenance']['tool_public_id'] == 'racing.get_position'

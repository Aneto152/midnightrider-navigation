"""Regression tests for the fail-soft historical MCP fact expansion."""

from unittest.mock import Mock

from mediaman.content_provider import HistoricalMCPProvider
from mediaman.mcp_collector import (
    CollectionStatus,
    MCPCollector,
    CollectionResult,
    NavigationFact,
    Provenance,
)


REQUIRED = {
    "latitude": 41.1,
    "longitude": -72.2,
    "speed_over_ground_ms": 2.5,
    "course_over_ground_degrees": 81.2,
}
UNITS = {
    "latitude": "degrees",
    "longitude": "degrees",
    "speed_over_ground_ms": "m_per_s",
    "course_over_ground_degrees": "degrees_true",
}
OPTIONAL = {
    "depth_below_transducer": 4.2,
    "wind_true_speed": 8.4,
    "outside_temperature": 19.5,
}
OPTIONAL_UNITS = {
    "depth_below_transducer": "m",
    "wind_true_speed": "m_per_s",
    "outside_temperature": "celsius",
}
OPTIONAL_TIMES = {
    key: "2026-09-05T12:00:02Z" for key in OPTIONAL
}


class OptionalFactsClient:
    """MCP fixture returning required and optional historical facts."""

    def __init__(self, optional=None):
        self.calls = []
        self.optional = OPTIONAL if optional is None else optional

    def call_tool(self, name, arguments=None):
        self.calls.append((name, dict(arguments or {})))
        return {
            "result": {
                "success": True,
                "facts": dict(REQUIRED),
                "units": dict(UNITS),
                "source_timestamp": "2026-09-05T12:00:01Z",
                "optional_facts": dict(self.optional),
                "optional_units": dict(OPTIONAL_UNITS),
                "optional_fact_timestamps": dict(OPTIONAL_TIMES),
            },
            "observed_at": "2026-09-05T12:00:03Z",
        }


def test_historical_collection_opts_in_to_optional_facts():
    client = OptionalFactsClient()
    result = MCPCollector(client, race_id="test").collect_historical(
        "2026-09-05T12:00:00Z", 3600
    )
    assert result.status is CollectionStatus.COMPLETE
    assert client.calls[0][1]["include_optional_facts"] is True


def test_optional_facts_are_appended_with_contract_units():
    result = MCPCollector(OptionalFactsClient(), race_id="test").collect_historical(
        "2026-09-05T12:00:00Z", 3600
    )
    values = {fact.field_name: fact for fact in result.facts}
    assert values["depth_below_transducer"].value == 4.2
    assert values["depth_below_transducer"].unit == "m"
    assert values["wind_true_speed"].provenance.source_timestamp == "2026-09-05T12:00:02Z"



def test_historical_optional_flag_is_not_added_to_live_contract():
    client = OptionalFactsClient()
    result = MCPCollector(client, race_id="test").collect_historical(
        "2026-09-05T12:00:00Z", 60
    )
    assert result.status is CollectionStatus.COMPLETE
    assert client.calls[0][1]["include_optional_facts"] is True


def test_invalid_optional_unit_is_ignored_without_failing_collection():
    client = OptionalFactsClient()
    client.optional = {"depth_below_transducer": 4.2}
    response = client.call_tool
    def wrong_unit(name, arguments=None):
        payload = response(name, arguments)
        payload["result"]["optional_units"]["depth_below_transducer"] = "feet"
        return payload
    client.call_tool = wrong_unit
    result = MCPCollector(client, race_id="test").collect_historical(
        "2026-09-05T12:00:00Z", 60
    )
    assert result.status is CollectionStatus.COMPLETE
    assert not any(f.field_name == "depth_below_transducer" for f in result.facts)
    assert any("unit" in warning for warning in result.warnings)


def _provenance():
    return Provenance(
        tool_public_id="racing.get_historical_snapshot",
        server_name="racing",
        wire_tool_name="get_historical_snapshot",
        source_id="mcp:racing:historical",
        source_timestamp="2026-09-05T12:00:01Z",
        observed_at="2026-09-05T12:00:03Z",
        freshness_limit_seconds=None,
        validation_status="valid",
    )


def test_provider_renders_optional_facts_when_present():
    facts = [
        NavigationFact("latitude", 41.1, "decimal_degrees", _provenance()),
        NavigationFact("longitude", -72.2, "decimal_degrees", _provenance()),
        NavigationFact("speed_over_ground", 2.5, "m/s", _provenance()),
        NavigationFact("course_over_ground", 81.2, "degrees_true", _provenance()),
        NavigationFact("depth_below_transducer", 4.2, "m", _provenance()),
        NavigationFact("wind_true_speed", 8.4, "m_per_s", _provenance()),
    ]
    result = CollectionResult(
        status=CollectionStatus.COMPLETE,
        race_id="test",
        facts=facts,
        collection_start_at="2026-09-05T12:00:00Z",
        collection_end_at="2026-09-05T12:00:03Z",
    )
    collector = Mock()
    collector.collect_historical.return_value = result
    article = HistoricalMCPProvider(collector).get_content_for_historical(
        "2026-09-05T12:00:00Z", 3600
    )
    assert "Profondeur" in article and "4.2 m" in article
    assert "Vent vrai - vitesse" in article and "8.4 m/s" in article


def test_provider_omits_optional_facts_when_absent():
    facts = [
        NavigationFact("latitude", 41.1, "decimal_degrees", _provenance()),
        NavigationFact("longitude", -72.2, "decimal_degrees", _provenance()),
        NavigationFact("speed_over_ground", 2.5, "m/s", _provenance()),
        NavigationFact("course_over_ground", 81.2, "degrees_true", _provenance()),
    ]
    result = CollectionResult(
        status=CollectionStatus.COMPLETE,
        race_id="test",
        facts=facts,
        collection_start_at="2026-09-05T12:00:00Z",
        collection_end_at="2026-09-05T12:00:03Z",
    )
    collector = Mock()
    collector.collect_historical.return_value = result
    article = HistoricalMCPProvider(collector).get_content_for_historical(
        "2026-09-05T12:00:00Z", 60
    )
    assert "Profondeur" not in article
    assert "Vent vrai" not in article

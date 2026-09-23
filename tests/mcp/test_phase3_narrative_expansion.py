"""Static contract tests for the opt-in MCP narrative expansion."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER = (ROOT / "mcp/servers/racing.js").read_text(encoding="utf-8")


def test_optional_expansion_is_explicitly_opt_in():
    assert "include_optional_facts" in SERVER
    assert "args.include_optional_facts === true" in SERVER
    assert "return await collectSnapshot(startUtc, endUtc, false)" in SERVER


def test_optional_response_keeps_required_four_fact_shape():
    assert "optional_facts: optionalFacts" in SERVER
    assert "optional_units: optionalUnits" in SERVER
    assert "optional_fact_timestamps: optionalTimestamps" in SERVER
    assert "facts: {" in SERVER


def test_all_fifteen_contract_ids_have_selectors():
    for fact_id in (
        "speed_through_water", "depth_below_transducer", "water_temperature",
        "wind_apparent_angle", "wind_apparent_speed", "wind_true_angle",
        "wind_true_speed", "wind_true_direction", "current_set", "current_drift",
        "attitude_roll", "attitude_pitch", "outside_temperature",
        "outside_pressure", "calypso_battery_percent",
    ):
        assert "fact: '%s'" % fact_id in SERVER


def test_source_pinning_follows_the_data_model():
    assert 'r.source == "N2K.35"' in SERVER
    assert 'r.source == "N2K.116"' in SERVER
    assert 'r.source =~ /^Calypso\\./' in SERVER
    assert 'r.source =~ /^signalk-truewind-calculator\\./' in SERVER
    assert 'r.source =~ /^signalk-current-calculator\\./' in SERVER


def test_unit_transforms_are_explicit():
    for transform in (
        "kelvin_to_celsius", "pascal_to_hpa", "radians_to_degrees",
        "radians_to_degrees_compass",
    ):
        assert transform in SERVER

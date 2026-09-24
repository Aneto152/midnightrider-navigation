"""The temporal query must name one instrument per series and never guess."""
import re
from pathlib import Path

SOURCE = Path("mcp/servers/racing.js").read_text(encoding="utf-8")


def _selector_block() -> str:
    start = SOURCE.index("const TEMPORAL_SELECTORS = [")
    return SOURCE[start:SOURCE.index("];", start)]


def _clause_block() -> str:
    start = SOURCE.index("const TEMPORAL_SOURCE_CLAUSES = {")
    return SOURCE[start:SOURCE.index("};", start)]


def test_the_four_environmental_selectors_are_declared_with_a_pinned_source():
    block = _selector_block()

    assert "{ series: 'outside_pressure', measurement: 'environment.outside.pressure', field: 'value', source: 'N2K.116' }" in block
    assert "{ series: 'water_temperature', measurement: 'environment.water.temperature', field: 'value', source: 'N2K.35' }" in block
    assert "{ series: 'leeway_angle', measurement: 'performance.leewayAngle', field: 'value', source: 'leeway' }" in block
    assert "{ series: 'rate_of_turn', measurement: 'navigation.rateOfTurn', field: 'value', source: 'Calypso.XX' }" in block


def test_every_selector_source_has_an_explicit_clause():
    declared = set(re.findall(r"source: '([^']+)' \}", _selector_block()))
    supported = set(re.findall(r"^\s+'?([A-Za-z0-9_.]+)'?: measurement =>", _clause_block(), re.MULTILINE))

    assert declared, "no selector source was parsed, the test would pass vacuously"
    assert declared <= supported, f"selector sources without a clause: {sorted(declared - supported)}"


def test_an_unknown_source_kind_throws_instead_of_falling_back():
    assert "throw new Error(`unknown temporal source kind: ${selector.source}`)" in SOURCE
    assert "Object.prototype.hasOwnProperty.call(TEMPORAL_SOURCE_CLAUSES, selector.source)" in SOURCE
    assert SOURCE.count("return `(r._measurement == \"${selector.measurement}\" and r.source =~ /^signalk-truewind-calculator\\./)`;") == 0


def test_the_temporal_path_still_downsamples_once_server_side():
    assert SOURCE.count("|> aggregateWindow(every: ${resolutionSeconds}s, fn: last, createEmpty: false)") == 1
    assert SOURCE.count("function buildTemporalQuery(") == 1


def test_the_new_series_are_converted_to_their_documented_units():
    assert "if (series === 'outside_pressure') return numeric / 100.0;" in SOURCE
    assert "if (series === 'water_temperature') return numeric - 273.15;" in SOURCE
    assert "if (series === 'rate_of_turn') return numeric * (180 / Math.PI) * 60;" in SOURCE
    assert "series === 'leeway_angle'" in SOURCE

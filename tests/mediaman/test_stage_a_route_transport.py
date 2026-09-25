from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
RACING = (REPO / "mcp/servers/racing.js").read_text(encoding="utf-8")
COLLECTOR = (REPO / "mediaman/mcp_collector.py").read_text(encoding="utf-8")


def test_route_measurement_and_series_are_declared():
    assert "navigation.currentRoute.waypoints" in RACING
    assert "route_waypoints" in RACING
    assert "function parseCsvLine" in RACING
    assert "const cells = parseCsvLine(line);" in RACING
    assert "const cells = line.split(',');" not in RACING


def test_route_rows_have_a_non_numeric_path():
    assert "function normalizeRouteRow" in RACING
    assert "if (isRouteRow(row))" in RACING
    assert "...routeRows" in RACING


def test_collector_exposes_raw_rows():
    assert "raw_rows" in COLLECTOR
    assert "temporal_rows" in COLLECTOR
    assert "row.get('series') == 'route_waypoints'" in COLLECTOR


def test_flux_query_remains_single_path():
    assert RACING.count("from(bucket:") == 1

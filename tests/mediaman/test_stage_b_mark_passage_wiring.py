"""Stage B regression tests for the geometric mark-passage wiring."""

from pathlib import Path

from mediaman.mark_passage_geometry import detect_mark_passage
from mediaman.historical_mark_passage import (
    detect_mark_passage_by_source,
    position_tracks_by_source,
    route_snapshots_from_rows,
    usable_route_snapshots,
)

REPO = Path(__file__).resolve().parents[2]
COLLECTOR = (REPO / "mediaman/mcp_collector.py").read_text(encoding="utf-8")
MODULE = (REPO / "mediaman/historical_mark_passage.py").read_text(encoding="utf-8")

WAYPOINTS = [
    {"name": "START", "latitude": 41.5000, "longitude": -70.9000},
    {"name": "BUZZARD", "latitude": 41.5100, "longitude": -70.9000},
    {"name": "FINISH", "latitude": 41.5200, "longitude": -70.9000},
]


def _rows():
    rows = [
        {"series": "route_waypoints", "source_id": "N2K.5",
         "timestamp_utc": "2026-09-05T14:00:00Z", "value": WAYPOINTS},
        {"series": "route_waypoints", "source_id": "N2K.8",
         "timestamp_utc": "2026-09-05T14:00:00Z", "value": WAYPOINTS},
    ]
    for source, offset in (("N2K.1", 0.0), ("N2K.2", 0.00002)):
        for index in range(41):
            latitude = 41.5000 + index * 0.0005 + offset
            stamp = "2026-09-05T14:%02d:00Z" % index
            rows.append({"series": "latitude", "source_id": source,
                         "timestamp_utc": stamp, "value": latitude})
            rows.append({"series": "longitude", "source_id": source,
                         "timestamp_utc": stamp, "value": -70.9000})
    return rows


def test_route_snapshots_preserve_source_and_instant():
    snapshots = route_snapshots_from_rows(_rows())
    assert len(snapshots) == 2
    assert {snapshot["source"] for snapshot in snapshots} == {"N2K.5", "N2K.8"}
    assert all(snapshot["timestamp"] for snapshot in snapshots)


def test_invalid_plotter_snapshot_is_rejected_individually():
    rows = [
        {"series": "route_waypoints", "source_id": "N2K.5",
         "timestamp_utc": "2026-09-05T14:00:00Z", "value": WAYPOINTS},
        {"series": "route_waypoints", "source_id": "N2K.8",
         "timestamp_utc": "2026-09-05T14:01:00Z", "value": [
             {"name": "", "position": {"value": {}}},
             {"name": "BUZZARD BAY LIGHT", "position": {"value": {
                 "latitude": 41.3960584, "longitude": -71.033509}}},
         ]},
    ]
    usable, rejected = usable_route_snapshots(route_snapshots_from_rows(rows))
    assert len(usable) == 1
    assert len(rejected) == 1
    assert rejected[0]["source"] == "N2K.8"
    assert "at least two usable waypoints" in rejected[0]["error"]


def test_tracks_are_grouped_independently_per_source():
    tracks = position_tracks_by_source(_rows())
    assert set(tracks) == {"N2K.1", "N2K.2"}
    assert all(sample["source"] == source for source, track in tracks.items() for sample in track)
    latitudes_1 = {sample["latitude"] for sample in tracks["N2K.1"]}
    latitudes_2 = {sample["latitude"] for sample in tracks["N2K.2"]}
    assert latitudes_1.isdisjoint(latitudes_2)


def test_a_source_without_both_coordinates_produces_no_fix():
    rows = [
        {"series": "latitude", "source_id": "N2K.9",
         "timestamp_utc": "2026-09-05T14:00:00Z", "value": 41.5},
    ]
    assert position_tracks_by_source(rows) == {}


def test_geometry_uses_directional_neighbors_on_sparse_track():
    route = [
        {"name": "START", "latitude": 41.5000, "longitude": -70.9000},
        {"name": "BUZZARD", "latitude": 41.3960111, "longitude": -71.0345366},
    ]
    track = [
        {"timestamp": "2026-09-05T14:10:00Z", "latitude": 41.3969086, "longitude": -71.0392485},
        {"timestamp": "2026-09-05T14:12:00Z", "latitude": 41.3973373, "longitude": -71.0349831},
        {"timestamp": "2026-09-05T14:15:00Z", "latitude": 41.3975000, "longitude": -71.0320000},
    ]
    result = detect_mark_passage(
        [
            {"timestamp": "2026-09-05T14:01:00Z", "value": route, "source": "N2K.5"},
        ],
        track,
        acceptance_start="2026-09-05T14:00:00Z",
        acceptance_end="2026-09-05T15:00:00Z",
    )
    assert result["event_count"] == 1
    assert result["events"][0]["mark_name"] == "BUZZARD"


def test_historical_route_replay_uses_topology_at_passage_time():
    rows = [
        {"series": "route_waypoints", "source_id": "N2K.5",
         "timestamp_utc": "2026-09-05T14:00:00Z", "value": [
             {"name": "THE RACE", "latitude": 41.5000, "longitude": -70.9000},
             {"name": "BUZZARD", "latitude": 41.5100, "longitude": -70.9000},
         ]},
        {"series": "route_waypoints", "source_id": "N2K.5",
         "timestamp_utc": "2026-09-05T14:13:00Z", "value": [
             {"name": "BUZZARD", "latitude": 41.5100, "longitude": -70.9000},
             {"name": "FINISH", "latitude": 41.5200, "longitude": -70.9000},
         ]},
    ]
    for index in range(41):
        stamp = "2026-09-05T14:%02d:00Z" % index
        latitude = 41.5000 + min(index, 12) * (0.0100 / 12.0) + max(0, index - 12) * 0.0002
        rows.append({"series": "latitude", "source_id": "N2K.1",
                     "timestamp_utc": stamp, "value": latitude})
        rows.append({"series": "longitude", "source_id": "N2K.1",
                     "timestamp_utc": stamp, "value": -70.9000})
    result = detect_mark_passage_by_source(
        rows,
        acceptance_start="2026-09-05T14:00:00Z",
        acceptance_end="2026-09-05T15:00:00Z",
    )
    assert any(event["mark_name"] == "BUZZARD"
               for event in result["results_by_source"]["N2K.1"]["events"])


def test_detection_runs_per_source_and_reports_consensus_after():
    result = detect_mark_passage_by_source(
        _rows(),
        acceptance_start="2026-09-05T14:00:00Z",
        acceptance_end="2026-09-05T15:00:00Z",
    )
    assert result["position_source_count"] == 2
    assert set(result["results_by_source"]) == {"N2K.1", "N2K.2"}
    assert set(result["event_count_by_source"]) == set(result["results_by_source"])
    for event in result["consensus_events"]:
        assert event["source_count"] == len(event["sources"])
        assert set(event["sources"]).issubset(set(result["results_by_source"]))


def test_no_route_snapshot_reports_an_error_without_crashing():
    rows = [row for row in _rows() if row["series"] != "route_waypoints"]
    result = detect_mark_passage_by_source(rows)
    assert result["route_snapshot_count"] == 0
    assert result["results_by_source"] == {}
    assert set(result["errors_by_source"]) == {"N2K.1", "N2K.2"}


def test_acceptance_never_uses_forbidden_criteria():
    result = detect_mark_passage_by_source(_rows())
    assert result["vmg_used_for_acceptance"] is False
    assert result["next_point_used_for_acceptance"] is False
    assert result["temporal_patterns_used_for_acceptance"] is False
    assert result["course_geometry_used_for_acceptance"] is True
    assert "true_gybe" not in MODULE
    assert "sustained_turn" not in MODULE


def test_collector_calls_the_geometric_detector():
    assert "detect_mark_passage_by_source" in COLLECTOR
    assert "result['mark_passage']" in COLLECTOR

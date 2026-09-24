from datetime import datetime, timedelta, timezone
import math

import pytest

from mediaman.mark_passage_geometry import (
    detect_mark_passage,
    normalize_route_snapshot,
)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def offset(lat, lon, bearing_deg, distance_nm):
    radians = math.radians(bearing_deg)
    return (
        lat + distance_nm * math.cos(radians) / 60.0,
        lon + distance_nm * math.sin(radians) / (60.0 * math.cos(math.radians(lat))),
    )


def route():
    return [{
        "_time": "2026-09-05T14:00:00Z",
        "source": "N2K.5",
        "value": [
            {"name": "THE RACE", "position": {"value": {"latitude": 41.2301107, "longitude": -72.0669283}}},
            {"name": "BUZZARD", "position": {"value": {"latitude": 41.3960111, "longitude": -71.0345366}}},
        ],
    }, {
        "_time": "2026-09-05T14:13:00Z",
        "source": "N2K.5",
        "value": [
            {"name": "BUZZARD", "position": {"value": {"latitude": 41.3960111, "longitude": -71.0345366}}},
            {"name": "BLOCK ISLAND EAST", "position": {"value": {"latitude": 41.1356496, "longitude": -71.5705348}}},
        ],
    }]


def track():
    mark_lat, mark_lon = 41.3960111, -71.0345366
    start = datetime(2026, 9, 5, 14, 10, tzinfo=timezone.utc)
    points = []
    for seconds in range(-180, 181, 10):
        distance = 0.03 + 0.002 * abs(seconds) / 10.0
        bearing = 110.0 if seconds < 0 else 240.0
        lat, lon = offset(mark_lat, mark_lon, bearing, distance)
        points.append({"_time": iso(start + timedelta(seconds=seconds)), "lat": lat, "lon": lon, "source": "N2K.5"})
    return points


def test_detects_endpoint_without_vmg_or_nextpoint():
    result = detect_mark_passage(route(), track(), acceptance_start="2026-09-05T14:00:00Z", acceptance_end="2026-09-05T15:00:00Z")
    assert result["course_geometry_used_for_acceptance"] is True
    assert result["vmg_used_for_acceptance"] is False
    assert result["next_point_used_for_acceptance"] is False
    assert result["event_count"] == 1
    assert result["events"][0]["mark_name"] == "BUZZARD"
    assert result["events"][0]["event_kind"] == "ROUTE_START_ENDPOINT_CANDIDATE"
    assert result["route_topology_status"] == "TRANSITION_OBSERVED"


def test_clusters_repeated_candidates_into_one_event():
    repeated = track() + track()
    result = detect_mark_passage(route(), repeated, acceptance_start="2026-09-05T14:00:00Z", acceptance_end="2026-09-05T15:00:00Z")
    assert result["event_count"] == 1
    assert result["raw_candidate_count"] >= 1


def test_rejects_track_that_does_not_approach_mark():
    far = []
    for point in track():
        item = dict(point)
        item["lat"] += 1.0
        far.append(item)
    result = detect_mark_passage(route(), far, acceptance_start="2026-09-05T14:00:00Z", acceptance_end="2026-09-05T15:00:00Z")
    assert result["event_count"] == 0


def null_waypoint_route():
    """Route snapshot mixing usable waypoints with a null-coordinate waypoint."""
    return {
        "timestamp": "2026-09-05T14:00:00.000Z",
        "value": [
            {"name": "THE RACE", "position": {"latitude": 41.2301107, "longitude": -72.0669283}},
            {"name": "GHOST", "position": {"latitude": None, "longitude": None}},
            {"name": "BUZZARD", "position": {"latitude": 41.3960111, "longitude": -71.0345366}},
        ],
    }


def test_route_snapshot_skips_null_waypoints_and_counts_them():
    snapshot = normalize_route_snapshot(null_waypoint_route())
    assert [item.name for item in snapshot.waypoints] == ["THE RACE", "BUZZARD"]
    assert snapshot.skipped_waypoints == 1


def test_route_snapshot_rejected_when_fewer_than_two_usable_waypoints():
    payload = {
        "timestamp": "2026-09-05T14:00:00.000Z",
        "value": [
            {"name": "BUZZARD", "position": {"latitude": 41.3960111, "longitude": -71.0345366}},
            {"name": "GHOST", "position": {"latitude": None, "longitude": None}},
        ],
    }
    with pytest.raises(ValueError, match="at least two usable waypoints"):
        normalize_route_snapshot(payload)


def test_detector_reports_skipped_waypoints():
    outcome = detect_mark_passage([null_waypoint_route()], track())
    assert outcome["route_waypoints_skipped"] == 1


def teleporting_track():
    """Approach BUZZARD normally, then jump 15 nm within one sampling step.

    This reproduces the outlier measured on source N2K.0 on 2026-09-05,
    where the sample 90 s after the closest approach sat 15.6 nm away,
    implying 624 knots.
    """
    mark = (41.3960111, -71.0345366)
    base = datetime(2026, 9, 5, 14, 10, 0, tzinfo=timezone.utc)
    samples = []
    for step in range(-18, 4):
        moment = base + timedelta(seconds=10 * step)
        lat, lon = offset(mark[0], mark[1], 310.0, 0.04 + abs(step) * 0.01)
        samples.append({"timestamp": iso(moment), "latitude": lat, "longitude": lon})
    for step in range(4, 19):
        moment = base + timedelta(seconds=10 * step)
        lat, lon = offset(mark[0], mark[1], 130.0, 15.6)
        samples.append({"timestamp": iso(moment), "latitude": lat, "longitude": lon})
    return samples


def test_rejects_candidate_whose_samples_imply_an_impossible_speed():
    outcome = detect_mark_passage(route(), teleporting_track())
    assert outcome["event_count"] == 0
    assert outcome["implausible_candidate_count"] >= 1
    assert outcome["max_plausible_speed_kn"] == 15.0


def test_same_candidate_is_accepted_once_the_speed_gate_is_lifted():
    outcome = detect_mark_passage(route(), teleporting_track(), max_plausible_speed_kn=10000.0)
    assert outcome["event_count"] == 1
    assert outcome["implausible_candidate_count"] == 0
    assert outcome["events"][0]["speed_after_kn"] > 500.0


def test_plausible_passage_reports_realistic_implied_speeds():
    outcome = detect_mark_passage(route(), track())
    event = outcome["events"][0]
    assert 0.0 < event["speed_before_kn"] <= 15.0
    assert 0.0 < event["speed_after_kn"] <= 15.0
    assert outcome["implausible_candidate_count"] == 0


def test_speed_gate_must_be_positive():
    with pytest.raises(ValueError, match="max_plausible_speed_kn must be positive"):
        detect_mark_passage(route(), track(), max_plausible_speed_kn=0.0)

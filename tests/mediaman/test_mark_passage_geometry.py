from datetime import datetime, timedelta, timezone
import math

from mediaman.mark_passage_geometry import detect_mark_passage


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

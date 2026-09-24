"""Tests for deterministic v1 navigation-pattern analysis."""

import pytest

from mediaman.nautical_units import (
    circular_delta_degrees,
    circular_mean_degrees,
    meters_per_second_to_knots,
    wrap_degrees,
)
from mediaman.pattern_contract import (
    IMPLEMENTED_PATTERN_IDS,
    PATTERN_BY_ID,
    PatternEvent,
    SeriesPoint,
)
from mediaman.pattern_detector import (
    PatternProfile,
    classify_point_of_sail,
    detect_heavy_heel,
    detect_patterns,
    detect_tack_and_maneuver_patterns,
    detect_wind_patterns,
)


def point(second, **values):
    return SeriesPoint(f"2026-09-05T12:00:{second:02d}Z", values)


def test_speed_is_rendered_in_knots_from_canonical_mps():
    assert round(meters_per_second_to_knots(1.0), 8) == 1.94384449


def test_circular_delta_handles_north_wrap():
    assert circular_delta_degrees(359.0, 1.0) == pytest.approx(2.0)
    assert circular_delta_degrees(1.0, 359.0) == pytest.approx(-2.0)


def test_circular_mean_handles_north_wrap():
    assert circular_mean_degrees([359.0, 1.0]) == pytest.approx(0.0)


def test_wrap_degrees_is_signed():
    assert wrap_degrees(181.0) == pytest.approx(-179.0)


def test_wind_strengthening_is_detected():
    events = detect_wind_patterns([point(0, wind_true_speed=3.0), point(30, wind_true_speed=4.0)])
    assert any(event.pattern_id == "wind_strengthening" for event in events)


def test_wind_weakening_is_detected():
    events = detect_wind_patterns([point(0, wind_true_speed=4.0), point(30, wind_true_speed=3.0)])
    assert any(event.pattern_id == "wind_weakening" for event in events)


def test_gusty_wind_uses_deviation_from_mean():
    events = detect_wind_patterns([point(0, wind_true_speed=3.0), point(10, wind_true_speed=3.0), point(20, wind_true_speed=6.0)])
    event = next(event for event in events if event.pattern_id == "gusty_wind")
    assert event.metrics["gust_excess_knots"] > 2.0


def test_point_of_sail_bands_are_explicit():
    assert classify_point_of_sail(35) == "close_hauled"
    assert classify_point_of_sail(90) == "beam_reach"
    assert classify_point_of_sail(170) == "run"


def test_point_of_sail_event_is_emitted():
    events = detect_patterns([point(0, wind_true_angle=40), point(30, wind_true_angle=42)])
    event = next(event for event in events if event.pattern_id == "point_of_sail")
    assert event.metrics["classification"] == "close_hauled"


def test_heavy_heel_requires_sustained_samples():
    points = [point(0, attitude_roll=21), point(10, attitude_roll=23), point(20, attitude_roll=22)]
    events = detect_heavy_heel(points)
    assert len(events) == 1
    assert events[0].metrics["samples"] == 3


def test_single_heel_spike_is_not_heavy_heel():
    points = [point(0, attitude_roll=21), point(10, attitude_roll=5), point(20, attitude_roll=4)]
    assert detect_heavy_heel(points) == []


def test_signed_twa_crossing_detects_tack():
    events = detect_tack_and_maneuver_patterns([point(0, wind_true_angle=35), point(30, wind_true_angle=-38)])
    assert any(event.pattern_id == "tack_change" for event in events)


def test_same_tack_twa_decrease_detects_luffing():
    events = detect_tack_and_maneuver_patterns([point(0, wind_true_angle=55), point(30, wind_true_angle=30)])
    assert any(event.pattern_id == "luffing" for event in events)


def test_same_tack_twa_increase_detects_bearing_away():
    events = detect_tack_and_maneuver_patterns([point(0, wind_true_angle=35), point(30, wind_true_angle=60)])
    assert any(event.pattern_id == "bearing_away" for event in events)


def test_multiple_tacks_create_sequence_event():
    points = [point(0, wind_true_angle=35), point(10, wind_true_angle=-35), point(20, wind_true_angle=40), point(30, wind_true_angle=-45)]
    events = detect_tack_and_maneuver_patterns(points)
    sequence = next(event for event in events if event.pattern_id == "tack_sequence")
    assert sequence.metrics["tack_count"] == 3


def test_event_serialization_contains_evidence():
    event = detect_wind_patterns([point(0, wind_true_speed=3), point(30, wind_true_speed=4)])[0]
    payload = event.as_dict()
    assert payload["pattern_id"] == event.pattern_id
    assert payload["evidence"]


def test_pattern_registry_documents_future_extensions():
    assert PATTERN_BY_ID["motor_suspected"].status == "planned"
    assert PATTERN_BY_ID["ais_comparison"].status == "planned"
    assert PATTERN_BY_ID["helm_identity"].status == "planned"


def test_unknown_pattern_event_is_rejected():
    with pytest.raises(ValueError, match="unknown pattern_id"):
        PatternEvent("not-a-pattern", "2026-09-05T12:00:00Z", "2026-09-05T12:00:00Z", 1.0, (), {})


def test_mark_passage_is_implemented_but_not_wired():
    """mark_passage has a validated detector that no analysis path calls yet."""
    assert PATTERN_BY_ID["mark_passage"].status == "implemented_unwired"
    assert "mark_passage" not in IMPLEMENTED_PATTERN_IDS

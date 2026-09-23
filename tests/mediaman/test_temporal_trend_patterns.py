"""Deterministic coverage for wind-trend and data-gap detectors."""
from mediaman.temporal_analyzer import analyze

RESOLUTION_SECONDS = 60


def _row(series: str, minute: int, value: float) -> dict:
    return {
        "series": series,
        "timestamp_utc": f"2026-09-05T12:{minute:02d}:00Z",
        "value": value,
        "source_id": "test",
    }


def _baseline(minutes: range) -> list[dict]:
    rows: list[dict] = []
    for minute in minutes:
        rows.append(_row("wind_true_speed", minute, 6.0))
        rows.append(_row("wind_true_angle", minute, -100.0))
    return rows


def test_persistent_shift_is_detected_from_absolute_wind_direction():
    minutes = range(0, 11)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("wind_true_direction", minute, 100.0 + 3.0 * minute))

    result = analyze(rows, "2026-09-05T12:00:00Z", "2026-09-05T12:11:00Z", RESOLUTION_SECONDS)
    identifiers = {pattern["pattern_id"] for pattern in result["patterns"]}

    assert "persistent_shift" in identifiers
    assert "wind_oscillation" not in identifiers

    event = next(p for p in result["patterns"] if p["pattern_id"] == "persistent_shift")
    assert event["metrics"]["rotation"] == "right"
    assert event["metrics"]["r_squared"] >= 0.7


def test_oscillating_breeze_is_not_reported_as_a_persistent_shift():
    minutes = range(0, 13)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("wind_true_direction", minute, 190.0 if minute % 2 else 170.0))

    result = analyze(rows, "2026-09-05T12:00:00Z", "2026-09-05T12:13:00Z", RESOLUTION_SECONDS)
    identifiers = {pattern["pattern_id"] for pattern in result["patterns"]}

    assert "wind_oscillation" in identifiers
    assert "persistent_shift" not in identifiers

    event = next(p for p in result["patterns"] if p["pattern_id"] == "wind_oscillation")
    assert event["metrics"]["trend_crossings"] >= 3
    assert event["metrics"]["amplitude_degrees"] >= 8.0


def test_missing_buckets_are_reported_as_a_data_gap():
    minutes = range(0, 10)
    rows = _baseline(minutes)
    for minute in (0, 1, 8, 9):
        rows.append(_row("speed_through_water", minute, 3.0))

    result = analyze(rows, "2026-09-05T12:00:00Z", "2026-09-05T12:10:00Z", RESOLUTION_SECONDS)
    events = [p for p in result["patterns"] if p["pattern_id"] == "data_gap"]

    assert len(events) == 1
    assert events[0]["metrics"]["worst_series"] == "speed_through_water"
    assert events[0]["metrics"]["worst_coverage_ratio"] < 1.0
    assert events[0]["metrics"]["degraded_series_count"] == 1


def test_complete_and_steady_coverage_raises_no_trend_or_gap_pattern():
    minutes = range(0, 10)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("wind_true_direction", minute, 210.0))

    result = analyze(rows, "2026-09-05T12:00:00Z", "2026-09-05T12:10:00Z", RESOLUTION_SECONDS)
    identifiers = {pattern["pattern_id"] for pattern in result["patterns"]}

    assert "data_gap" not in identifiers
    assert "persistent_shift" not in identifiers
    assert "wind_oscillation" not in identifiers

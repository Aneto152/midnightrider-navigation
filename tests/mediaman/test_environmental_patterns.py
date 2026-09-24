"""Deterministic coverage for the pressure, thermal, leeway and turn detectors."""
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


def _identifiers(rows: list[dict], last_minute: int) -> set[str]:
    result = analyze(rows, "2026-09-05T12:00:00Z", f"2026-09-05T12:{last_minute:02d}:00Z", RESOLUTION_SECONDS)
    return {pattern["pattern_id"] for pattern in result["patterns"]}


def _event(rows: list[dict], last_minute: int, pattern_id: str) -> dict:
    result = analyze(rows, "2026-09-05T12:00:00Z", f"2026-09-05T12:{last_minute:02d}:00Z", RESOLUTION_SECONDS)
    return next(p for p in result["patterns"] if p["pattern_id"] == pattern_id)


def test_falling_barometer_is_reported_as_a_pressure_drop():
    minutes = range(0, 31)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("outside_pressure", minute, 1015.0 - 0.1 * minute))

    event = _event(rows, 31, "pressure_drop")

    assert event["metrics"]["slope_hpa_per_hour"] < -1.0
    assert event["metrics"]["r_squared"] >= 0.7
    assert event["metrics"]["delta_hpa"] < 0.0


def test_rising_barometer_is_reported_as_a_pressure_rise():
    minutes = range(0, 31)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("outside_pressure", minute, 1005.0 + 0.1 * minute))

    identifiers = _identifiers(rows, 31)

    assert "pressure_rise" in identifiers
    assert "pressure_drop" not in identifiers


def test_a_flat_barometer_raises_no_pressure_pattern():
    minutes = range(0, 31)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("outside_pressure", minute, 1013.2))

    identifiers = _identifiers(rows, 31)

    assert "pressure_drop" not in identifiers
    assert "pressure_rise" not in identifiers


def test_a_water_temperature_step_is_reported_as_a_thermal_front():
    minutes = range(0, 11)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("water_temperature", minute, 18.0 if minute < 5 else 19.6))

    event = _event(rows, 11, "thermal_front")

    assert event["metrics"]["direction"] == "warming"
    assert event["metrics"]["delta_celsius"] >= 1.0
    assert event["metrics"]["largest_step_celsius"] >= 1.0


def test_a_small_water_temperature_drift_is_not_a_thermal_front():
    minutes = range(0, 11)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("water_temperature", minute, 18.0 + 0.02 * minute))

    assert "thermal_front" not in _identifiers(rows, 11)


def test_sustained_leeway_above_the_threshold_is_reported():
    minutes = range(0, 11)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("leeway_angle", minute, -8.0 if 2 <= minute <= 6 else -1.0))

    event = _event(rows, 11, "excessive_leeway")

    assert event["metrics"]["sustained_samples"] == 5
    assert event["metrics"]["maximum_absolute_degrees"] >= 6.0
    assert event["start_utc"] == "2026-09-05T12:02:00Z"


def test_moderate_leeway_raises_no_pattern():
    minutes = range(0, 11)
    rows = _baseline(minutes)
    for minute in minutes:
        rows.append(_row("leeway_angle", minute, 3.0))

    assert "excessive_leeway" not in _identifiers(rows, 11)


def test_turn_rate_requires_a_heading_confirmed_maneuver():
    minutes = range(0, 11)
    without_maneuver = _baseline(minutes)
    steady = _baseline(minutes)
    alternating = _baseline(minutes)
    for minute in minutes:
        without_maneuver.append(_row("rate_of_turn", minute, 30.0 if 3 <= minute <= 5 else 2.0))
        steady.append(_row("rate_of_turn", minute, 30.0 if 3 <= minute <= 5 else 2.0))
        alternating.append(_row("rate_of_turn", minute, 30.0 if minute % 2 else -30.0))
        if minute < 4:
            heading, wind = 40.0, 0.0
        else:
            heading, wind = 320.0, 0.0
        for rows in (steady, alternating):
            rows.append(_row("heading_true", minute, heading))
            rows.append(_row("wind_true_direction", minute, wind))
            rows.append(_row("wind_true_angle", minute, ((heading - wind) + 180.0) % 360.0 - 180.0))

    assert "sustained_turn" not in _identifiers(without_maneuver, 11)

    event = _event(steady, 11, "sustained_turn")
    assert event["metrics"]["sustained_samples"] == 3
    assert event["metrics"]["sampling"] == "instantaneous_last_in_bucket"
    assert event["metrics"]["corroborated_by"] == ["true_tack"]
    assert event["confidence"] == 0.6
    assert "sustained_turn" not in _identifiers(alternating, 11)

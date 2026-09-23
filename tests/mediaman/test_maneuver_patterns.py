"""Deterministic coverage for true_tack and true_gybe attribution."""
from mediaman.temporal_analyzer import analyze

RESOLUTION_SECONDS = 60
WINDOW_START = "2026-09-05T12:00:00Z"
WINDOW_END = "2026-09-05T12:06:00Z"


def _rows(headings: list[float], wind_directions: list[float]) -> list[dict]:
    """Build a six-bucket window from explicit heading and wind sequences."""
    rows: list[dict] = []
    for minute, (heading, wind) in enumerate(zip(headings, wind_directions)):
        angle = ((heading - wind) + 180.0) % 360.0 - 180.0
        rows.append(_row("heading_true", minute, heading))
        rows.append(_row("wind_true_direction", minute, wind))
        rows.append(_row("wind_true_angle", minute, angle))
        rows.append(_row("wind_true_speed", minute, 6.0))
    return rows


def _row(series: str, minute: int, value: float) -> dict:
    return {
        "series": series,
        "timestamp_utc": f"2026-09-05T12:{minute:02d}:00Z",
        "value": value,
        "source_id": "test",
    }


def _identifiers(rows: list[dict]) -> set[str]:
    result = analyze(rows, WINDOW_START, WINDOW_END, RESOLUTION_SECONDS)
    return {pattern["pattern_id"] for pattern in result["patterns"]}


def test_bow_crossing_the_wind_is_a_true_tack():
    rows = _rows(
        headings=[40.0, 40.0, 40.0, 320.0, 320.0, 320.0],
        wind_directions=[0.0] * 6,
    )
    identifiers = _identifiers(rows)

    assert "true_tack" in identifiers
    assert "true_gybe" not in identifiers


def test_stern_crossing_the_wind_is_a_true_gybe():
    rows = _rows(
        headings=[150.0, 150.0, 150.0, 210.0, 210.0, 210.0],
        wind_directions=[0.0] * 6,
    )
    identifiers = _identifiers(rows)

    assert "true_gybe" in identifiers
    assert "true_tack" not in identifiers


def test_a_wind_rotation_alone_is_never_a_maneuver():
    rows = _rows(
        headings=[45.0] * 6,
        wind_directions=[0.0, 19.0, 38.0, 57.0, 76.0, 95.0],
    )
    identifiers = _identifiers(rows)

    assert "true_tack" not in identifiers
    assert "true_gybe" not in identifiers
    assert "wind_shift_right" in identifiers


def test_a_tack_is_not_reported_as_a_bearing_away():
    rows = _rows(
        headings=[40.0, 40.0, 40.0, 320.0, 320.0, 320.0],
        wind_directions=[0.0] * 6,
    )
    identifiers = _identifiers(rows)

    assert "bearing_away" not in identifiers
    assert "luffing" not in identifiers

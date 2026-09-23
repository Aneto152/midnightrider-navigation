"""Deterministic aggregation and pattern analysis for historical series."""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable, Mapping

from mediaman.nautical_units import meters_per_second_to_knots, circular_delta_degrees
from mediaman.pattern_contract import SeriesPoint
from mediaman.pattern_detector import (
    detect_wind_patterns, detect_point_of_sail, detect_heavy_heel,
    detect_tack_and_maneuver_patterns,
)
from mediaman.temporal_contract import HistoricalAnalysis, HistoricalInterval, TemporalSample

WIND_SPEED = "wind_true_speed"
WIND_ANGLE = "wind_true_angle"
SOG = "speed_over_ground"
COG = "course_over_ground"
STW = "speed_through_water"
HEEL = "attitude_roll"
WIND_DIRECTION = "wind_true_direction"
HEADING = "heading_true"

PERSISTENT_SHIFT_MIN_DEGREES = 10.0
PERSISTENT_SHIFT_MIN_R_SQUARED = 0.7
OSCILLATION_MIN_CROSSINGS = 3
OSCILLATION_MIN_AMPLITUDE_DEGREES = 8.0
OSCILLATION_MAX_R_SQUARED = 0.5
TREND_MIN_SAMPLES = 5
DATA_GAP_MIN_COVERAGE_RATIO = 0.9
DATA_GAP_MAX_MISSING_BUCKETS = 2
MANEUVER_MIN_HEADING_CHANGE_DEGREES = 45.0
MANEUVER_MAX_WIND_ROTATION_RATIO = 0.5
MANEUVER_TACK_GYBE_BOUNDARY_DEGREES = 90.0
MANEUVER_MIN_ANGLE_DEADBAND_DEGREES = 5.0

def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight

def _stats(samples: list[TemporalSample], *, knots: bool = False, circular: bool = False) -> dict[str, Any]:
    values = [float(s.value) for s in samples]
    if knots:
        values = [meters_per_second_to_knots(v) for v in values]
    if not values:
        return {"sample_count": 0, "first_utc": None, "last_utc": None}
    if circular:
        radians = [math.radians(v) for v in values]
        mean = math.degrees(math.atan2(sum(math.sin(v) for v in radians), sum(math.cos(v) for v in radians))) % 360
    else:
        mean = statistics.fmean(values)
    return {
        "sample_count": len(values), "first_utc": samples[0].timestamp_utc,
        "last_utc": samples[-1].timestamp_utc, "min": min(values), "max": max(values),
        "mean": mean, "median": statistics.median(values),
        "stddev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "p50": _percentile(values, 0.50), "p90": _percentile(values, 0.90),
        "p95": _percentile(values, 0.95), "start": values[0], "end": values[-1],
        "delta": circular_delta_degrees(values[0], values[-1]) if circular else values[-1] - values[0],
    }

def normalize_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[TemporalSample]]:
    """Convert MCP temporal rows into the canonical analysis series."""
    result: dict[str, list[TemporalSample]] = defaultdict(list)
    for row in rows:
        key = str(row.get("series") or row.get("name") or "")
        if not key or row.get("timestamp_utc") is None:
            continue
        result[key].append(TemporalSample(str(row["timestamp_utc"]), float(row["value"]), row.get("source_id")))
    for values in result.values():
        values.sort(key=lambda sample: sample.timestamp_utc)
    return dict(result)

def _points(series: list[TemporalSample], key: str, *, knots: bool = False) -> list[SeriesPoint]:
    """Convert one named temporal series into detector-compatible points."""
    return [SeriesPoint(s.timestamp_utc, {key: meters_per_second_to_knots(s.value) if knots else s.value}) for s in series]

def detect_wind_attribution_patterns(series: Mapping[str, list[TemporalSample]]) -> list[dict[str, Any]]:
    """Attribute TWA changes only when absolute wind and heading evidence exists."""
    twa = series.get(WIND_ANGLE, [])
    wind_direction = series.get(WIND_DIRECTION, [])
    heading = series.get(HEADING, [])
    if len(twa) < 2 or len(wind_direction) < 2 or len(heading) < 2:
        return []
    twa_start, twa_end = twa[0].value, twa[-1].value
    wind_delta = circular_delta_degrees(wind_direction[0].value, wind_direction[-1].value)
    heading_delta = circular_delta_degrees(heading[0].value, heading[-1].value)
    twa_abs_delta = abs(twa_end) - abs(twa_start)
    start = twa[0].timestamp_utc
    end = twa[-1].timestamp_utc
    events: list[dict[str, Any]] = []
    if abs(wind_delta) >= 10.0:
        events.append({
            "pattern_id": "wind_shift_right" if wind_delta > 0 else "wind_shift_left",
            "start_utc": start, "end_utc": end, "confidence": 0.9,
            "evidence": ["absolute true-wind direction changed beyond the configured threshold"],
            "metrics": {"wind_direction_delta_degrees": wind_delta},
        })
    if abs(heading_delta) <= 5.0 and abs(twa_abs_delta) >= 15.0:
        events.append({
            "pattern_id": "wind_refusal" if twa_abs_delta < 0 else "wind_adonnante",
            "start_utc": start, "end_utc": end, "confidence": 0.85,
            "evidence": ["true heading remained stable while TWA changed materially"],
            "metrics": {"twa_absolute_delta_degrees": twa_abs_delta, "heading_delta_degrees": heading_delta},
        })
    elif abs(wind_delta) <= 5.0 and abs(heading_delta) >= 15.0 and abs(twa_abs_delta) >= 15.0:
        events.append({
            "pattern_id": "luffing" if twa_abs_delta < 0 else "bearing_away",
            "start_utc": start, "end_utc": end, "confidence": 0.85,
            "evidence": ["absolute wind direction remained stable while true heading changed materially"],
            "metrics": {"twa_absolute_delta_degrees": twa_abs_delta, "heading_delta_degrees": heading_delta},
        })
    return events


def _parse_utc(timestamp: str) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp, returning None when it is unusable."""
    try:
        return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

def _unwrap_degrees(samples: list[TemporalSample]) -> list[float]:
    """Unfold a circular bearing series into a continuous signed sequence."""
    unwrapped = [float(samples[0].value)]
    previous = float(samples[0].value)
    for sample in samples[1:]:
        current = float(sample.value)
        unwrapped.append(unwrapped[-1] + circular_delta_degrees(previous, current))
        previous = current
    return unwrapped

def detect_wind_direction_trend_patterns(series: Mapping[str, list[TemporalSample]]) -> list[dict[str, Any]]:
    """Separate a persistent wind rotation from an oscillating breeze.

    A persistent shift is a monotonic rotation that a linear fit explains well.
    An oscillation is a repeated swing around the trend that the fit explains
    poorly. The two conditions are mutually exclusive by construction.
    """
    direction = series.get(WIND_DIRECTION, [])
    if len(direction) < TREND_MIN_SAMPLES:
        return []
    times = [_parse_utc(sample.timestamp_utc) for sample in direction]
    if any(moment is None for moment in times):
        return []
    origin = times[0]
    minutes = [(moment - origin).total_seconds() / 60.0 for moment in times]
    if len(set(minutes)) < TREND_MIN_SAMPLES:
        return []
    values = _unwrap_degrees(direction)
    try:
        slope, intercept = statistics.linear_regression(minutes, values)
        r_squared = statistics.correlation(minutes, values) ** 2
    except (statistics.StatisticsError, ValueError, ZeroDivisionError):
        return []
    residuals = [value - (slope * minute + intercept) for value, minute in zip(values, minutes)]
    crossings = sum(
        1
        for first, second in zip(residuals, residuals[1:])
        if (first > 0.0 > second) or (first < 0.0 < second)
    )
    amplitude = max(residuals) - min(residuals)
    total_delta = values[-1] - values[0]
    start = direction[0].timestamp_utc
    end = direction[-1].timestamp_utc
    events: list[dict[str, Any]] = []
    if abs(total_delta) >= PERSISTENT_SHIFT_MIN_DEGREES and r_squared >= PERSISTENT_SHIFT_MIN_R_SQUARED:
        events.append({
            "pattern_id": "persistent_shift",
            "start_utc": start, "end_utc": end, "confidence": 0.85,
            "evidence": ["absolute wind direction rotated monotonically and a linear fit explains it"],
            "metrics": {
                "total_delta_degrees": total_delta,
                "slope_degrees_per_minute": slope,
                "r_squared": r_squared,
                "rotation": "right" if total_delta > 0 else "left",
            },
        })
    if (
        crossings >= OSCILLATION_MIN_CROSSINGS
        and amplitude >= OSCILLATION_MIN_AMPLITUDE_DEGREES
        and r_squared <= OSCILLATION_MAX_R_SQUARED
    ):
        events.append({
            "pattern_id": "wind_oscillation",
            "start_utc": start, "end_utc": end, "confidence": 0.8,
            "evidence": ["absolute wind direction swung repeatedly around its trend"],
            "metrics": {
                "trend_crossings": crossings,
                "amplitude_degrees": amplitude,
                "r_squared": r_squared,
                "total_delta_degrees": total_delta,
            },
        })
    return events

def detect_data_gap_patterns(
    series: Mapping[str, list[TemporalSample]],
    start_utc: str,
    end_utc: str,
    resolution_seconds: int,
) -> list[dict[str, Any]]:
    """Flag series whose bucket coverage is below the requested resolution."""
    start = _parse_utc(start_utc)
    end = _parse_utc(end_utc)
    if start is None or end is None or resolution_seconds <= 0:
        return []
    expected = int((end - start).total_seconds() // resolution_seconds)
    if expected < TREND_MIN_SAMPLES:
        return []
    tolerated_gap = resolution_seconds * (DATA_GAP_MAX_MISSING_BUCKETS + 1)
    degraded: list[tuple[str, float, float]] = []
    for name in sorted(series):
        samples = series[name]
        ratio = len(samples) / expected
        moments = [_parse_utc(sample.timestamp_utc) for sample in samples]
        spacings = [
            (second - first).total_seconds()
            for first, second in zip(moments, moments[1:])
            if first is not None and second is not None
        ]
        widest = max(spacings) if spacings else 0.0
        if ratio < DATA_GAP_MIN_COVERAGE_RATIO or widest > tolerated_gap:
            degraded.append((name, ratio, widest))
    if not degraded:
        return []
    worst = min(degraded, key=lambda entry: entry[1])
    return [{
        "pattern_id": "data_gap",
        "start_utc": start_utc, "end_utc": end_utc, "confidence": 0.95,
        "evidence": [
            "series below the configured coverage threshold: "
            + ", ".join(name for name, _, _ in degraded)
        ],
        "metrics": {
            "expected_buckets": expected,
            "degraded_series_count": len(degraded),
            "worst_series": worst[0],
            "worst_coverage_ratio": worst[1],
            "maximum_gap_seconds": max(widest for _, _, widest in degraded),
        },
    }]

def _aligned_relative_angles(
    series: Mapping[str, list[TemporalSample]],
) -> list[tuple[str, float, float, float]]:
    """Pair true heading with absolute wind direction on shared timestamps.

    The returned angle is the signed difference between the true heading and
    the direction the true wind comes from. Its sign identifies the tack; its
    magnitude says whether the bow or the stern faces the wind.
    """
    heading = {sample.timestamp_utc: float(sample.value) for sample in series.get(HEADING, [])}
    wind = {sample.timestamp_utc: float(sample.value) for sample in series.get(WIND_DIRECTION, [])}
    shared = sorted(set(heading) & set(wind))
    return [
        (moment, circular_delta_degrees(wind[moment], heading[moment]), heading[moment], wind[moment])
        for moment in shared
    ]

def detect_maneuver_patterns(series: Mapping[str, list[TemporalSample]]) -> list[dict[str, Any]]:
    """Separate a true tack from a gybe using heading and absolute wind.

    A tack change is claimed only when the boat itself turns: the true heading
    must move materially while the absolute wind direction stays comparatively
    stable. The crossing angle then decides between a bow crossing, which is a
    tack, and a stern crossing, which is a gybe. A wind rotation alone never
    produces a maneuver.
    """
    aligned = _aligned_relative_angles(series)
    if len(aligned) < 2:
        return []
    events: list[dict[str, Any]] = []
    for (before_utc, before_angle, before_heading, before_wind), (after_utc, after_angle, after_heading, after_wind) in zip(aligned, aligned[1:]):
        if before_angle * after_angle >= 0.0:
            continue
        if min(abs(before_angle), abs(after_angle)) < MANEUVER_MIN_ANGLE_DEADBAND_DEGREES:
            continue
        heading_delta = circular_delta_degrees(before_heading, after_heading)
        wind_delta = circular_delta_degrees(before_wind, after_wind)
        if abs(heading_delta) < MANEUVER_MIN_HEADING_CHANGE_DEGREES:
            continue
        if abs(wind_delta) > abs(heading_delta) * MANEUVER_MAX_WIND_ROTATION_RATIO:
            continue
        mean_absolute = (abs(before_angle) + abs(after_angle)) / 2.0
        is_tack = mean_absolute < MANEUVER_TACK_GYBE_BOUNDARY_DEGREES
        crossing = "the bow crossed the wind" if is_tack else "the stern crossed the wind"
        events.append({
            "pattern_id": "true_tack" if is_tack else "true_gybe",
            "start_utc": before_utc, "end_utc": after_utc, "confidence": 0.9,
            "evidence": [
                f"the signed heading-to-wind angle changed sign and {crossing}",
                "true heading changed materially while absolute wind direction stayed comparatively stable",
            ],
            "metrics": {
                "heading_delta_degrees": heading_delta,
                "wind_direction_delta_degrees": wind_delta,
                "angle_before_degrees": before_angle,
                "angle_after_degrees": after_angle,
                "mean_absolute_angle_degrees": mean_absolute,
            },
        })
    return events

def analyze(rows: Iterable[Mapping[str, Any]], start_utc: str, end_utc: str, resolution_seconds: int) -> dict[str, Any]:
    """Build a deterministic evidence-backed analysis packet."""
    interval = HistoricalInterval(start_utc, end_utc, resolution_seconds)
    series = normalize_rows(rows)
    series_output = {name: [sample.as_dict() for sample in values] for name, values in series.items()}
    stats = {}
    for name, values in series.items():
        stats[name] = _stats(values, knots=name in {WIND_SPEED, SOG, STW}, circular=name in {WIND_ANGLE, COG})
    coverage = {
        name: {
            "sample_count": len(values),
            "first_utc": values[0].timestamp_utc if values else None,
            "last_utc": values[-1].timestamp_utc if values else None,
        }
        for name, values in series.items()
    }
    evidence = {
        "query_count": 1,
        "source_ids": sorted({s.source_id for values in series.values() for s in values if s.source_id}),
        "sample_counts": {k: len(v) for k, v in series.items()},
    }
    required = {WIND_SPEED, WIND_ANGLE}
    missing = sorted(name for name in required if len(series.get(name, [])) < 2)
    if missing:
        result = HistoricalAnalysis(interval, coverage, series_output, stats, patterns=[], evidence=evidence).as_dict()
        result["success"] = False
        result["status"] = "INCOMPLETE"
        result["evidence"]["incomplete_reason"] = "required_temporal_series_missing_or_insufficient"
        result["evidence"]["missing_series"] = missing
        return result
    patterns = []
    patterns.extend(event.as_dict() for event in detect_wind_patterns(_points(series[WIND_SPEED], WIND_SPEED, knots=True)))
    patterns.extend(event.as_dict() for event in detect_point_of_sail(_points(series[WIND_ANGLE], WIND_ANGLE)))
    patterns.extend(detect_wind_attribution_patterns(series))
    patterns.extend(detect_wind_direction_trend_patterns(series))
    patterns.extend(detect_data_gap_patterns(series, start_utc, end_utc, resolution_seconds))
    patterns.extend(detect_maneuver_patterns(series))
    if HEEL in series:
        patterns.extend(event.as_dict() for event in detect_heavy_heel(_points(series[HEEL], HEEL)))
    return HistoricalAnalysis(interval, coverage, series_output, stats, patterns=patterns, evidence=evidence).as_dict()

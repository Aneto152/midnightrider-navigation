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

def _points(series: list[TemporalSample], *, knots: bool = False) -> list[SeriesPoint]:
    return [SeriesPoint(s.timestamp_utc, {"value": meters_per_second_to_knots(s.value) if knots else s.value}) for s in series]

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
    patterns.extend(event.as_dict() for event in detect_wind_patterns(_points(series[WIND_SPEED], knots=True)))
    patterns.extend(event.as_dict() for event in detect_point_of_sail(_points(series[WIND_ANGLE])))
    patterns.extend(event.as_dict() for event in detect_tack_and_maneuver_patterns(_points(series[WIND_ANGLE])))
    if HEEL in series:
        patterns.extend(event.as_dict() for event in detect_heavy_heel(_points(series[HEEL])))
    return HistoricalAnalysis(interval, coverage, series_output, stats, patterns=patterns, evidence=evidence).as_dict()

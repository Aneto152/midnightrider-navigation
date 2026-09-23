"""Deterministic v1 navigation-pattern detectors over normalized series."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Iterable

from mediaman.nautical_units import circular_delta_degrees, meters_per_second_to_knots
from mediaman.pattern_contract import PatternEvent, SeriesPoint


@dataclass(frozen=True)
class PatternProfile:
    """Thresholds for one deterministic analysis profile."""

    wind_change_knots: float = 1.0
    gust_excess_knots: float = 2.0
    gust_stddev_knots: float = 1.5
    heavy_heel_degrees: float = 20.0
    heavy_heel_min_samples: int = 3
    tack_deadband_degrees: float = 10.0
    maneuver_change_degrees: float = 15.0
    point_of_sail_close_hauled_degrees: float = 50.0
    point_of_sail_close_reach_degrees: float = 80.0
    point_of_sail_beam_reach_degrees: float = 110.0
    point_of_sail_broad_reach_degrees: float = 150.0


def _event(pattern_id, points, confidence, evidence, metrics):
    return PatternEvent(pattern_id, points[0].timestamp_utc, points[-1].timestamp_utc, confidence, tuple(evidence), metrics)


def classify_point_of_sail(twa_degrees: float, profile: PatternProfile = PatternProfile()) -> str:
    """Classify absolute signed true-wind angle using configurable thresholds."""
    angle = abs(twa_degrees)
    if angle < profile.point_of_sail_close_hauled_degrees:
        return "close_hauled"
    if angle < profile.point_of_sail_close_reach_degrees:
        return "close_reach"
    if angle < profile.point_of_sail_beam_reach_degrees:
        return "beam_reach"
    if angle < profile.point_of_sail_broad_reach_degrees:
        return "broad_reach"
    return "run"


def detect_wind_patterns(points: Iterable[SeriesPoint], profile: PatternProfile = PatternProfile()) -> list[PatternEvent]:
    """Detect strengthening, weakening and gustiness from true-wind speed."""
    points = [point for point in points if "wind_true_speed" in point.values]
    if len(points) < 2:
        return []
    speeds = [meters_per_second_to_knots(point.values["wind_true_speed"]) for point in points]
    mean = statistics.fmean(speeds)
    stddev = statistics.pstdev(speeds) if len(speeds) > 1 else 0.0
    events = []
    delta = speeds[-1] - speeds[0]
    if delta >= profile.wind_change_knots:
        events.append(_event("wind_strengthening", points, 0.9, ["end speed exceeds start speed by configured threshold"], {"start_knots": speeds[0], "end_knots": speeds[-1], "delta_knots": delta, "mean_knots": mean}))
    elif delta <= -profile.wind_change_knots:
        events.append(_event("wind_weakening", points, 0.9, ["end speed is below start speed by configured threshold"], {"start_knots": speeds[0], "end_knots": speeds[-1], "delta_knots": delta, "mean_knots": mean}))
    if stddev >= profile.gust_stddev_knots or max(speeds) - mean >= profile.gust_excess_knots:
        events.append(_event("gusty_wind", points, 0.85, ["wind dispersion or peak exceeds configured threshold"], {"mean_knots": mean, "stddev_knots": stddev, "maximum_knots": max(speeds), "gust_excess_knots": max(speeds) - mean}))
    return events


def detect_point_of_sail(points: Iterable[SeriesPoint], profile: PatternProfile = PatternProfile()) -> list[PatternEvent]:
    """Emit one classified sailing-mode event for the available TWA series."""
    points = [point for point in points if "wind_true_angle" in point.values]
    if not points:
        return []
    classifications = [classify_point_of_sail(point.values["wind_true_angle"], profile) for point in points]
    if len(set(classifications)) == 1:
        return [_event("point_of_sail", points, 0.9, ["all samples share one configured TWA band"], {"classification": classifications[0], "angle_start_degrees": points[0].values["wind_true_angle"], "angle_end_degrees": points[-1].values["wind_true_angle"]})]
    return [_event("point_of_sail", points, 0.75, ["TWA crosses configured sailing-mode bands"], {"classification_start": classifications[0], "classification_end": classifications[-1], "angle_start_degrees": points[0].values["wind_true_angle"], "angle_end_degrees": points[-1].values["wind_true_angle"]})]


def detect_heavy_heel(points: Iterable[SeriesPoint], profile: PatternProfile = PatternProfile()) -> list[PatternEvent]:
    """Detect a sustained heel event above the 20-degree default threshold."""
    points = [point for point in points if "attitude_roll" in point.values]
    events=[]; run=[]
    for point in points + [None]:
        if point is not None and abs(point.values["attitude_roll"]) >= profile.heavy_heel_degrees:
            run.append(point)
        else:
            if len(run) >= profile.heavy_heel_min_samples:
                events.append(_event("heavy_heel", run, 0.95, ["heel exceeded threshold for the minimum consecutive sample count"], {"maximum_degrees": max(abs(p.values["attitude_roll"]) for p in run), "threshold_degrees": profile.heavy_heel_degrees, "samples": len(run)}))
            run=[]
    return events


def detect_tack_and_maneuver_patterns(points: Iterable[SeriesPoint], profile: PatternProfile = PatternProfile()) -> list[PatternEvent]:
    """Detect signed-TWA tack crossings and luff/bear-away changes."""
    points=[p for p in points if "wind_true_angle" in p.values]
    if len(points)<2: return []
    events=[]; previous=None; segment=[points[0]]
    for point in points[1:]:
        current=point.values["wind_true_angle"]
        prior=previous if previous is not None else points[0].values["wind_true_angle"]
        if abs(prior)>profile.tack_deadband_degrees and abs(current)>profile.tack_deadband_degrees and prior*current<0:
            events.append(_event("tack_change", [segment[-1],point], 0.9, ["signed TWA crossed zero outside the deadband"], {"from_twa_degrees": prior, "to_twa_degrees": current}))
            segment=[point]
        else:
            segment.append(point)
        previous=current
    first=points[0].values["wind_true_angle"]; last=points[-1].values["wind_true_angle"]
    if first*last>0 and abs(abs(last)-abs(first)) >= profile.maneuver_change_degrees:
        pattern="luffing" if abs(last)<abs(first) else "bearing_away"
        events.append(_event(pattern, points, 0.8, ["signed TWA stayed on one tack and its absolute value changed persistently"], {"start_twa_degrees": first, "end_twa_degrees": last, "delta_absolute_degrees": abs(last)-abs(first)}))
    tack_events=[event for event in events if event.pattern_id=="tack_change"]
    if len(tack_events)>=2:
        events.append(_event("tack_sequence", points, 0.9, ["multiple tack_change events occurred in one window"], {"tack_count": len(tack_events)}))
    return events


def detect_patterns(points: Iterable[SeriesPoint], profile: PatternProfile = PatternProfile()) -> list[PatternEvent]:
    """Run all implemented deterministic v1 detectors over one window."""
    points=tuple(points)
    return detect_wind_patterns(points,profile)+detect_point_of_sail(points,profile)+detect_heavy_heel(points,profile)+detect_tack_and_maneuver_patterns(points,profile)

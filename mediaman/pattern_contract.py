"""Contracts and SSOT registry for deterministic navigation patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SeriesPoint:
    """One timestamped normalized sample from a historical analysis window."""

    timestamp_utc: str
    values: Mapping[str, float]

    def __post_init__(self) -> None:
        if not self.timestamp_utc.endswith("Z"):
            raise ValueError("series timestamps must be UTC and end with Z")
        for key, value in self.values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"series value must be numeric: {key}")


@dataclass(frozen=True)
class PatternEvent:
    """Evidence-backed event emitted by the pattern detector."""

    pattern_id: str
    start_utc: str
    end_utc: str
    confidence: float
    evidence: tuple[str, ...]
    metrics: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.pattern_id not in PATTERN_BY_ID:
            raise ValueError(f"unknown pattern_id: {self.pattern_id}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.start_utc.endswith("Z") or not self.end_utc.endswith("Z"):
            raise ValueError("event timestamps must be UTC and end with Z")

    def as_dict(self) -> dict[str, Any]:
        """Serialize the event for the future LLM evidence packet."""
        return {
            "pattern_id": self.pattern_id,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True)
class PatternSpec:
    """SSOT description of one detectable or planned pattern.

    ``status`` is one of:

    - ``implemented``: produced by the analyzer and reported to callers.
    - ``implemented_unwired``: a validated detector exists in the codebase
      but no analysis path calls it yet, so the pattern is never emitted.
    - ``planned``: no detector exists.
    """

    pattern_id: str
    category: str
    status: str
    required_inputs: tuple[str, ...]
    description: str


PATTERN_REGISTRY: tuple[PatternSpec, ...] = (
    PatternSpec("wind_strengthening", "wind", "implemented", ("wind_true_speed",), "True wind speed rises persistently."),
    PatternSpec("wind_weakening", "wind", "implemented", ("wind_true_speed",), "True wind speed falls persistently."),
    PatternSpec("gusty_wind", "wind", "implemented", ("wind_true_speed",), "Wind dispersion or short peaks exceed the profile threshold."),
    PatternSpec("point_of_sail", "sailing", "implemented", ("wind_true_angle",), "Classify close-hauled, reach, beam reach or run."),
    PatternSpec("heavy_heel", "handling", "implemented", ("attitude_roll",), "Heel exceeds 20 degrees for a sustained run."),
    PatternSpec("tack_change", "maneuver", "implemented", ("wind_true_angle",), "Signed true-wind angle crosses the deadband."),
    PatternSpec("luffing", "maneuver", "implemented", ("wind_true_angle",), "Absolute signed true-wind angle decreases on one tack."),
    PatternSpec("bearing_away", "maneuver", "implemented", ("wind_true_angle",), "Absolute signed true-wind angle increases on one tack."),
    PatternSpec("tack_sequence", "maneuver", "implemented", ("tack_change",), "Multiple tack events occur in one analysis window."),
    PatternSpec("wind_shift_refusal", "wind", "planned", ("wind_true_direction", "heading_true"), "Wind moves forward relative to a stable boat heading."),
    PatternSpec("wind_shift_adonnante", "wind", "planned", ("wind_true_direction", "heading_true"), "Wind moves aft relative to a stable boat heading."),
    PatternSpec("motor_suspected", "propulsion", "planned", ("speed_over_ground", "speed_through_water", "attitude_roll", "wind_true_angle"), "Sailing dynamics suggest propulsion without direct engine telemetry."),
    PatternSpec("engine_confirmed", "propulsion", "planned", ("engine_rpm", "engine_state"), "Direct engine telemetry confirms propulsion."),
    PatternSpec("polar_performance", "performance", "planned", ("speed_through_water", "wind_true_speed", "wind_true_angle"), "Compare boat response with a validated polar model."),
    PatternSpec("ais_comparison", "fleet", "planned", ("ais_tracks",), "Compare performance with nearby AIS targets."),
    PatternSpec("sun_phase", "environment", "planned", ("position", "timestamp"), "Attach sunrise, sunset and light phase."),
    PatternSpec("tide_state", "environment", "planned", ("position", "timestamp"), "Attach tidal height and stream state."),
    PatternSpec("mark_passage", "race", "implemented_unwired", ("position", "course_geometry"), "Detect passage near a named route waypoint from course geometry; detector lives in mediaman/mark_passage_geometry.py and is not yet called by analyze()."),
    PatternSpec("point_of_interest", "context", "planned", ("position", "poi_catalog"), "Attach a nearby configured point of interest."),
    PatternSpec("helm_identity", "context", "planned", ("helm_log",), "Attach the person at the helm when explicitly recorded."),
)
PATTERN_BY_ID = {spec.pattern_id: spec for spec in PATTERN_REGISTRY}
IMPLEMENTED_PATTERN_IDS = tuple(spec.pattern_id for spec in PATTERN_REGISTRY if spec.status == "implemented")

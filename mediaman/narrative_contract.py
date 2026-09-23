"""Validated data contract for MediaMan narrative inputs.

This module defines the boundary between historical collection and future
trend/LLM narration. It contains no network access and no publication logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FactQuality(str, Enum):
    """Quality state attached to one normalized fact."""

    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class FactSpec:
    """Canonical identity and unit contract for one narrative fact."""

    fact_id: str
    unit: str
    source_paths: tuple[str, ...]
    required: bool
    circular: bool = False


# The four required semantic facts are latitude, longitude, speed over ground,
# and course over ground (the true course used as the current heading proxy).
FACT_SPECS: tuple[FactSpec, ...] = (
    FactSpec("latitude", "degrees", ("navigation.position.lat",), True),
    FactSpec("longitude", "degrees", ("navigation.position.lon",), True),
    FactSpec("speed_over_ground", "m_per_s", ("navigation.speedOverGround",), True),
    FactSpec("course_over_ground", "degrees_true", ("navigation.courseOverGroundTrue",), True, circular=True),
    FactSpec("speed_through_water", "m_per_s", ("navigation.speedThroughWater",), False),
    FactSpec("depth_below_transducer", "m", ("environment.depth.belowTransducer",), False),
    FactSpec("water_temperature", "celsius", ("environment.water.temperature",), False),
    FactSpec("wind_apparent_angle", "degrees_relative", ("environment.wind.angleApparent",), False, circular=True),
    FactSpec("wind_apparent_speed", "m_per_s", ("environment.wind.speedApparent",), False),
    FactSpec("wind_true_angle", "degrees_relative", ("environment.wind.angleTrueWater", "environment.wind.angleTrueGround"), False, circular=True),
    FactSpec("wind_true_speed", "m_per_s", ("environment.wind.speedTrue",), False),
    FactSpec("wind_true_direction", "degrees_true", ("environment.wind.directionTrue",), False, circular=True),
    FactSpec("current_set", "degrees_true", ("environment.current.setTrue",), False, circular=True),
    FactSpec("current_drift", "m_per_s", ("environment.current.drift",), False),
    FactSpec("attitude_roll", "degrees", ("navigation.attitude.roll",), False),
    FactSpec("attitude_pitch", "degrees", ("navigation.attitude.pitch",), False),
    FactSpec("outside_temperature", "celsius", ("environment.outside.temperature",), False),
    FactSpec("outside_pressure", "hpa", ("environment.outside.pressure",), False),
    FactSpec("calypso_battery_percent", "percent", ("batteries.calypso.percent",), False),
)

SPEC_BY_ID = {spec.fact_id: spec for spec in FACT_SPECS}
REQUIRED_FACT_IDS = tuple(spec.fact_id for spec in FACT_SPECS if spec.required)
OPTIONAL_FACT_IDS = tuple(spec.fact_id for spec in FACT_SPECS if not spec.required)


@dataclass(frozen=True)
class NarrativeFact:
    """One normalized fact with provenance and quality metadata."""

    fact_id: str
    value: float | int | None
    unit: str
    source: str | None
    source_timestamp: str | None
    observed_at: str | None
    quality: FactQuality
    availability: str

    def __post_init__(self) -> None:
        spec = SPEC_BY_ID.get(self.fact_id)
        if spec is None:
            raise ValueError(f"unknown fact_id: {self.fact_id}")
        if self.unit != spec.unit:
            raise ValueError(f"unit mismatch for {self.fact_id}: expected {spec.unit}, got {self.unit}")
        if self.quality is FactQuality.VALID:
            if self.value is None or isinstance(self.value, bool):
                raise ValueError(f"valid fact requires numeric value: {self.fact_id}")
            if not isinstance(self.value, (int, float)):
                raise ValueError(f"fact value must be numeric: {self.fact_id}")
            if self.availability != "present":
                raise ValueError(f"valid fact must be present: {self.fact_id}")
        elif self.availability != "missing":
            raise ValueError(f"non-valid fact must be marked missing: {self.fact_id}")

    def as_dict(self) -> dict[str, Any]:
        """Serialize the fact without losing provenance or quality."""
        return {
            "fact_id": self.fact_id,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "source_timestamp": self.source_timestamp,
            "observed_at": self.observed_at,
            "quality": self.quality.value,
            "availability": self.availability,
        }


@dataclass(frozen=True)
class NarrativeSnapshot:
    """Validated one-window input for future trend and narration stages."""

    as_of_utc: str
    window_seconds: int
    facts: tuple[NarrativeFact, ...]
    collection_status: str = "complete"

    def __post_init__(self) -> None:
        if not self.as_of_utc.endswith("Z"):
            raise ValueError("as_of_utc must end with Z")
        if not isinstance(self.window_seconds, int) or isinstance(self.window_seconds, bool):
            raise ValueError("window_seconds must be an integer")
        if not 1 <= self.window_seconds <= 3600:
            raise ValueError("window_seconds must be between 1 and 3600")
        ids = [fact.fact_id for fact in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate fact_id in snapshot")
        missing_required = [fact_id for fact_id in REQUIRED_FACT_IDS if fact_id not in ids]
        if missing_required:
            raise ValueError(f"missing required facts: {', '.join(missing_required)}")
        invalid_required = [fact.fact_id for fact in self.facts if fact.fact_id in REQUIRED_FACT_IDS and fact.quality is not FactQuality.VALID]
        if invalid_required:
            raise ValueError(f"invalid required facts: {', '.join(invalid_required)}")

    def fact(self, fact_id: str) -> NarrativeFact | None:
        """Return one fact by canonical identifier, if supplied."""
        return next((fact for fact in self.facts if fact.fact_id == fact_id), None)

    def as_dict(self) -> dict[str, Any]:
        """Serialize the complete snapshot for future series/LLM adapters."""
        return {
            "as_of_utc": self.as_of_utc,
            "window_seconds": self.window_seconds,
            "collection_status": self.collection_status,
            "facts": [fact.as_dict() for fact in self.facts],
        }


def fact_spec(fact_id: str) -> FactSpec:
    """Return a canonical fact specification or raise for an unknown ID."""
    try:
        return SPEC_BY_ID[fact_id]
    except KeyError as exc:
        raise ValueError(f"unknown fact_id: {fact_id}") from exc

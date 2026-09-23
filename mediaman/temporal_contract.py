"""Validated contracts for bounded historical navigation analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

def validate_utc(value: str) -> str:
    """Validate and normalize an ISO-8601 UTC timestamp ending in Z."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be an ISO-8601 UTC string ending in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    if parsed > datetime.now(timezone.utc):
        raise ValueError("future timestamps are not allowed")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

@dataclass(frozen=True)
class TemporalSample:
    """One normalized historical sample with source provenance."""
    timestamp_utc: str
    value: float
    source_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp_utc", validate_utc(self.timestamp_utc))
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValueError("temporal sample value must be numeric")

    def as_dict(self) -> dict[str, Any]:
        return {"timestamp_utc": self.timestamp_utc, "value": self.value, "source_id": self.source_id}

@dataclass(frozen=True)
class HistoricalInterval:
    """Bounded analysis interval and requested resolution."""
    start_utc: str
    end_utc: str
    resolution_seconds: int

    def __post_init__(self) -> None:
        start = validate_utc(self.start_utc)
        end = validate_utc(self.end_utc)
        if end <= start:
            raise ValueError("end_utc must be strictly after start_utc")
        duration = (datetime.fromisoformat(end[:-1] + "+00:00") - datetime.fromisoformat(start[:-1] + "+00:00")).total_seconds()
        if duration > 21600:
            raise ValueError("historical analysis interval must not exceed 21600 seconds")
        if not isinstance(self.resolution_seconds, int) or not 10 <= self.resolution_seconds <= 300:
            raise ValueError("resolution_seconds must be an integer between 10 and 300")
        object.__setattr__(self, "start_utc", start)
        object.__setattr__(self, "end_utc", end)

    @property
    def duration_seconds(self) -> int:
        start = datetime.fromisoformat(self.start_utc[:-1] + "+00:00")
        end = datetime.fromisoformat(self.end_utc[:-1] + "+00:00")
        return int((end - start).total_seconds())

    def as_dict(self) -> dict[str, Any]:
        return {"start_utc": self.start_utc, "end_utc": self.end_utc, "duration_seconds": self.duration_seconds}

@dataclass(frozen=True)
class HistoricalAnalysis:
    """Evidence-backed deterministic analysis result; no LLM output."""
    interval: HistoricalInterval
    coverage: Mapping[str, Any]
    series: Mapping[str, Any]
    statistics: Mapping[str, Any]
    patterns: list[Mapping[str, Any]] = field(default_factory=list)
    maneuvers: list[Mapping[str, Any]] = field(default_factory=list)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": True,
            "status": "COMPLETE",
            "analysis_version": "1",
            "interval": self.interval.as_dict(),
            "resolution_seconds": self.interval.resolution_seconds,
            "coverage": dict(self.coverage),
            "series": dict(self.series),
            "statistics": dict(self.statistics),
            "patterns": list(self.patterns),
            "maneuvers": list(self.maneuvers),
            "evidence": dict(self.evidence),
            "llm_status": "not_activated",
        }

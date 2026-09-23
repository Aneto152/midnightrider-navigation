# MediaMan Narrative Data Contract v1

**Status:** validated design boundary — no live collector expansion yet
**Date:** 2026-09-22
**Scope:** historical MediaMan snapshots before trend aggregation and LLM narration

## Purpose

InfluxDB contains many onboard measurements, while the current historical MCP
path consumes only position, speed over ground and course over ground. This
document defines the normalized boundary that future collectors must satisfy
before MediaMan can build richer articles.

The contract deliberately separates three responsibilities:

1. collection and unit normalization;
2. trend and evolution calculation;
3. deterministic or LLM narration.

The LLM must never be responsible for calculating facts from raw database
values.

## Required semantic facts

Every valid snapshot must contain these four semantic facts:

| Fact ID | Unit | Source path | Circular |
|---|---|---|---|
| `latitude` | degrees | `navigation.position.lat` | no |
| `longitude` | degrees | `navigation.position.lon` | no |
| `speed_over_ground` | m/s | `navigation.speedOverGround` | no |
| `course_over_ground` | degrees true | `navigation.courseOverGroundTrue` | yes |

Position is represented by the latitude/longitude pair. Course over ground is
the current true-course proxy; a distinct heading fact may be added later.

## Optional narrative facts

Optional facts may be absent without invalidating the snapshot:

| Fact ID | Unit | Source path | Circular |
|---|---|---|---|
| `speed_through_water` | m/s | `navigation.speedThroughWater` | no |
| `depth_below_transducer` | m | `environment.depth.belowTransducer` | no |
| `water_temperature` | Celsius | `environment.water.temperature` | no |
| `wind_apparent_angle` | degrees relative | `environment.wind.angleApparent` | yes |
| `wind_apparent_speed` | m/s | `environment.wind.speedApparent` | no |
| `wind_true_angle` | degrees relative | `environment.wind.angleTrueWater` or `angleTrueGround` | yes |
| `wind_true_speed` | m/s | `environment.wind.speedTrue` | no |
| `wind_true_direction` | degrees true | `environment.wind.directionTrue` | yes |
| `current_set` | degrees true | `environment.current.setTrue` | yes |
| `current_drift` | m/s | `environment.current.drift` | no |
| `attitude_roll` | degrees | `navigation.attitude.roll` | no |
| `attitude_pitch` | degrees | `navigation.attitude.pitch` | no |
| `outside_temperature` | Celsius | `environment.outside.temperature` | no |
| `outside_pressure` | hPa | `environment.outside.pressure` | no |
| `calypso_battery_percent` | percent | `batteries.calypso.percent` | no |

This table is a MediaMan data contract, not a PGN table. Instrument PGN
ownership remains in `docs/HARDWARE/` and system PGN flow remains in
`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`.

## Fact envelope

Every fact is normalized into this shape:

```json
{
  "fact_id": "wind_true_speed",
  "value": 8.4,
  "unit": "m_per_s",
  "source": "signalk",
  "source_timestamp": "2026-09-05T12:00:00Z",
  "observed_at": "2026-09-05T12:00:01Z",
  "quality": "valid",
  "availability": "present"
}
```

`quality` is one of `valid`, `missing`, `invalid` or `conflict`. A valid fact
must be numeric and present. Optional unavailable facts are explicit rather
than silently invented.

## Boundary rules

- Historical timestamps must be UTC and end in `Z`.
- A snapshot window is bounded to 1–3600 seconds in v1.
- Required facts are fail-closed; optional facts are fail-soft.
- Every fact keeps source and timestamp provenance.
- Circular values must never be averaged arithmetically.
- AIS data is not a substitute for the vessel's `self` data.
- N2K.35 attitude data is handled by its documented source-priority rule.
- No LLM call is part of this contract.
- No Telegram publication is part of this contract.

## Next boundaries

**Evolution phase:** add a bounded series contract with samples, intervals,
aggregates and trends. It must preserve circular-angle semantics.

**Narration phase:** provide the validated facts and trends to a deterministic
or local LLM narrator. The narrator may describe supplied facts but may not
invent, calculate hidden values or replace missing data with guesses.

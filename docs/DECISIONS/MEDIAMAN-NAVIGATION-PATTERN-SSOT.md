# MediaMan Navigation Pattern SSOT

**Status:** v1 deterministic foundation, 2026-09-22
**Owner:** MediaMan historical analysis
**Scope:** definitions, inputs, units, thresholds and evidence requirements

This document is the single source of truth for navigation patterns emitted by
MediaMan. New patterns must be added here before implementation. A pattern is
not considered available merely because an LLM can describe it.

## Common event contract

Every detected event must contain:

```json
{
  "pattern_id": "gusty_wind",
  "start_utc": "2026-09-05T11:20:00Z",
  "end_utc": "2026-09-05T11:55:00Z",
  "confidence": 0.91,
  "evidence": ["12 valid samples", "P95 exceeded the configured threshold"],
  "metrics": {"mean_knots": 9.7, "stddev_knots": 2.1}
}
```

The detector calculates facts; the LLM only narrates validated events.

## Units

Internal collection remains canonical SI where already defined by the data
contract. Analysis and article-facing metrics use nautical units:

- speed and wind: knots (`1 m/s = 1.9438444924406 kn`);
- distance/depth: metres;
- pressure: hPa;
- temperature: Celsius;
- angles: degrees;
- direction angles use circular arithmetic.

The values `359°` and `1°` are two degrees apart, not 358 degrees apart.

## Implemented v1 patterns

| ID | Category | Required inputs | Detection rule |
|---|---|---|---|
| `wind_strengthening` | wind | true-wind speed | End-to-start increase exceeds the profile threshold. |
| `wind_weakening` | wind | true-wind speed | End-to-start decrease exceeds the profile threshold. |
| `gusty_wind` | wind | true-wind speed | Dispersion or peak excess exceeds the profile threshold. |
| `point_of_sail` | sailing | signed true-wind angle | Classify close-hauled, close reach, beam reach, broad reach or run. |
| `heavy_heel` | handling | attitude roll | Absolute heel exceeds 20° for at least three consecutive samples by default. |
| `tack_change` | maneuver | signed true-wind angle | TWA crosses zero outside the deadband. |
| `luffing` | maneuver | signed true-wind angle | Absolute TWA decreases while remaining on one tack. |
| `bearing_away` | maneuver | signed true-wind angle | Absolute TWA increases while remaining on one tack. |
| `tack_sequence` | maneuver | tack events | At least two tack changes occur in the analysis window. |

Signed TWA convention must be calibrated against the vessel's Signal K data
before live interpretation of port and starboard. The current v1 detector emits
signed events; the port/starboard label remains a calibration responsibility.

## Planned patterns

| ID | Required additions | Status |
|---|---|---|
| `wind_shift_refusal` | true-wind direction + stable heading | planned |
| `wind_shift_adonnante` | true-wind direction + stable heading | planned |
| `motor_suspected` | SOG/STW, heel, wind and confidence rules | planned, inferential only |
| `engine_confirmed` | engine state or RPM telemetry | planned |
| `polar_performance` | validated J/30 polar model | planned |
| `ais_comparison` | time-aligned AIS tracks and identity | planned |
| `sun_phase` | position and astronomical calculation | planned |
| `tide_state` | position and tide source | planned |
| `mark_passage` | configured race geometry | planned |
| `point_of_interest` | configured POI catalogue | planned |
| `helm_identity` | explicit helm log or event input | planned |

An inferred motor event must never be presented as confirmed engine operation
without direct engine telemetry.

## Extension protocol

Each future pattern must add:

1. one row to this registry;
2. required input facts and units;
3. a deterministic rule or explicitly marked inferential rule;
4. evidence and confidence requirements;
5. synthetic tests for positive, negative and missing-data cases;
6. a documented output schema;
7. no secret, credential or raw prompt in logs.

Future AIS, polar, tide, sun, helm, mark and POI data must be added as separate
context providers. They must not be mixed into the onboard instrument SSOT or
copied into hardware datasheets.

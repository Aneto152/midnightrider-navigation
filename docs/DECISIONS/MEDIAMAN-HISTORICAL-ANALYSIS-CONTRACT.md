# MediaMan Historical Analysis Contract

**Status:** Phase I v1 design and implementation boundary
**Scope:** bounded, read-only historical analysis from InfluxDB
**LLM:** not activated

## Contract

`get_historical_analysis` accepts `start_utc`, `end_utc` and
`resolution_seconds`. The interval is strictly historical, ends with a
literal `Z`, is at most six hours, and the resolution is 10–300 seconds.

The MCP layer performs one grouped temporal query. The Python analysis layer
normalizes samples, computes deterministic statistics, handles circular
angles, detects coverage gaps, and invokes only implemented detectors from
`MEDIAMAN-NAVIGATION-PATTERN-SSOT.md`.

## Result boundary

The result contains the interval, coverage, normalized series, statistics,
deterministic patterns, evidence metadata and `llm_status: not_activated`.
Missing coverage produces no invented pattern. Future extensions such as
refusal/adonnante, motor state, AIS, polar, sun, tides, marks, POIs and helm
identity remain planned registry entries until their evidence providers and
tests exist.

## Units

InfluxDB keeps canonical SI values. The analysis-facing speed statistics are
expressed in knots using the shared nautical-unit conversion. Angles use
circular arithmetic; a transition from 359° to 1° is a +2° movement.

## Security and operations

The path is read-only. It does not change Signal K, Docker, live MediaMan,
Telegram publication or LLM activation. Credentials remain in the secured
runtime environment and never enter results or logs.

## MCP query timeout

The grouped historical query uses a 20-second MCP HTTP timeout. The value is based on a measured 10.534281-second direct Flux response for a 10-minute historical window. This timeout applies only to the historical analysis path; the live path is unchanged.

## Server-side temporal downsampling

The grouped Flux query applies `aggregateWindow` at the requested resolution,
grouped by measurement, field and source, before returning data to MCP. The
representative is the last sample in each bucket, which preserves signed and
circular angle semantics. Python then performs deterministic statistics over
the bounded representative series. A one-hour baseline measured 56.815135
seconds and 28,306,910 bytes before this optimization.

## Historical query timeout

The historical grouped query has a dedicated 90-second HTTP timeout because a
one-hour direct Flux query measured 56.815135 seconds. The live and snapshot
paths retain the 20-second timeout. This is a bounded read-only safeguard, not
a service restart or a change to Signal K.

## Python MCP client timeout

The default Python MCPClient request timeout remains 5 seconds for the live
and snapshot paths. `MCPCollector.collect_historical_analysis` explicitly uses
a 120-second per-call override, matching the 90-second Node historical timeout
and the validated one-hour read-only query.

## Detector series wiring

The temporal analyzer maps each canonical series to the detector key expected by
the pattern contract. `wind_true_speed`, `wind_true_angle` and `attitude_roll`
are never emitted under a generic `value` key before detector execution.

## Wind attribution

TWA variation alone is not sufficient to claim luffing or bearing away. The
analysis requests `environment.wind.directionTrue` and
`navigation.headingTrue`. `wind_shift_left` and `wind_shift_right` describe
absolute wind-direction rotation. `wind_refusal` and `wind_adonnante` require a
stable true heading. `luffing` and `bearing_away` require stable absolute wind
direction and a material true-heading change. Without those inputs, the TWA
change remains unattributed.

## Wind trend and data-gap detectors

Three deterministic detectors complement the wind-attribution rules. They read
only canonical series and never call an LLM.

| Pattern | Required series | Rule |
|---|---|---|
| `persistent_shift` | `wind_true_direction` | at least 5 samples, unwrapped rotation of at least 10 degrees, linear fit with R-squared of at least 0.7 |
| `wind_oscillation` | `wind_true_direction` | at least 3 crossings of the fitted trend, residual amplitude of at least 8 degrees, R-squared of at most 0.5 |
| `data_gap` | any series | bucket coverage below 90 percent of the requested resolution, or a spacing wider than three buckets |

`persistent_shift` and `wind_oscillation` are mutually exclusive because the
R-squared bands do not overlap. `data_gap` is reported once for the whole
interval and names the worst series, so a sparse window never silently
produces confident tactical patterns.

## Tack and gybe attribution

A maneuver is claimed only when the boat itself turns. The detector pairs
`navigation.headingTrue` with `environment.wind.directionTrue` on shared
timestamps and follows the signed heading-to-wind angle.

| Condition | Threshold |
|---|---|
| signed angle changes sign | required |
| smallest crossing angle | at least 5 degrees |
| true-heading change | at least 45 degrees |
| absolute wind rotation | at most half the heading change |

The crossing magnitude then classifies the maneuver: a mean absolute angle
below 90 degrees means the bow crossed the wind and yields `true_tack`, while
90 degrees or more means the stern crossed and yields `true_gybe`. No tack side
is asserted, because the sign convention of the absolute wind direction is not
formally pinned in this repository.

`detect_tack_and_maneuver_patterns` in `mediaman/pattern_detector.py` stays
deliberately unwired from `analyze`: it derives `luffing` from the true-wind
angle alone, which cannot separate a boat maneuver from a wind rotation. The
attribution branch for `luffing` and `bearing_away` now also requires a
material absolute TWA change, so a tack, which leaves the TWA magnitude
unchanged, is never reported as a bearing away.

## Environmental and turn-rate series

Four series were added to the single grouped Flux query. Each measurement,
source and field below was confirmed present in the analysis window by a
probe carrying positive controls, not inferred from documentation.

| Series | Measurement | Source pinned | Stored unit | Emitted unit |
|---|---|---|---|---|
| `outside_pressure` | `environment.outside.pressure` | `N2K.116` | pascal | hectopascal |
| `water_temperature` | `environment.water.temperature` | `N2K.35` | kelvin | celsius |
| `leeway_angle` | `performance.leewayAngle` | `signalk-j30-leeway.*` | radian, signed | degree, signed |
| `rate_of_turn` | `navigation.rateOfTurn` | `Calypso.XX` | radian per second | degree per minute |

### Why the source is pinned

Three candidate measurements carry two instruments at once. Pressure is
published by both the dedicated barometer and the Calypso unit; rate of turn
by both the Calypso unit and another bus node; depth by two transducers. A
selector that does not name one instrument interleaves two time lines into a
single series, and the resulting steps are indistinguishable from real
events. Pressure follows the barometer and depth follows the DST sensor, in
line with the optional-fact selectors already shipped.

### Exhaustive source resolver

The resolver previously ended in an unconditional fallback to the true-wind
calculator, so an unrecognised source kind produced a filter for the wrong
instrument rather than an error. It is now a lookup table and an unknown
kind throws. A wrong filter and an empty series are otherwise impossible to
tell apart, which is the failure mode that once hid a malformed regex.

### Detectors and thresholds

| Pattern | Condition | Confidence |
|---|---|---|
| `pressure_drop` / `pressure_rise` | slope at least 1.0 hPa per hour and R squared at least 0.7 | 0.85 |
| `thermal_front` | water temperature changes by at least 1.0 celsius across the window | 0.8 |
| `excessive_leeway` | absolute leeway at or above 6 degrees for at least 3 consecutive samples | 0.75 |
| `sustained_turn` | absolute rate of turn at or above 20 degrees per minute, constant sign, at least 2 samples, and overlapping a heading-confirmed `true_tack` or `true_gybe` | 0.6 |

### Rate-of-turn sampling caveat

The temporal query downsamples with the last raw sample of each bucket. At a
sixty second resolution a rate-of-turn value is therefore instantaneous, not
an average, and a turn shorter than one bucket can be missed entirely. Its
confidence is deliberately the lowest of the set and `sustained_turn` is
corroborating evidence for a maneuver established from heading, never an
independent claim. If no `true_tack` or `true_gybe` interval overlaps the
rate-of-turn run, the run is suppressed entirely. No port or starboard direction
is asserted, for the same reason as in tack and gybe attribution: the sign
convention of this installation has not been verified against a known maneuver.

### Known divergence, not addressed here

`mediaman/pattern_contract.py` presents `PATTERN_REGISTRY` as the registry of
patterns, and `PatternEvent` rejects an unregistered identifier. The temporal
detectors return plain dictionaries, so they bypass that validation. Every
identifier emitted since the wind-attribution work is absent from the
registry, and the registry still lists the wind refusal and adonnante
patterns as planned under different names. Reconciling the registry with the
code is deliberately kept out of this change.

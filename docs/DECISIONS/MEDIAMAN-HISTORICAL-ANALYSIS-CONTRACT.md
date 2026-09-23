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

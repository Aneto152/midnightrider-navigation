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

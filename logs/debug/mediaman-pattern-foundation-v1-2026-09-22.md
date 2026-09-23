# MediaMan navigation pattern foundation v1 — 2026-09-22

This phase adds canonical nautical units, circular-angle helpers, evidence-backed PatternEvent/SeriesPoint contracts and the SSOT registry. Implemented synthetic detectors cover wind strengthening/weakening/gustiness, point of sail, heavy heel, tack changes, luffing, bearing away and tack sequences.

The detector is not yet wired to live InfluxDB series. Planned patterns include wind refusal/adonnante, engine confirmation, polar performance, AIS comparison, sun, tide, marks, POI and helm identity.

Verification: MediaMan 545->563 passed (+18); H9b 48 passed, 0 failed; no live query, LLM call or publication occurred.

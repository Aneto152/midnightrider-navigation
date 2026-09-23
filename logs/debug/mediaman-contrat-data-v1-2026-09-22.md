# MediaMan narrative data contract v1 — 2026-09-22

This contract-only phase defines four required and fifteen optional normalized facts with unit, source, timestamp, quality and availability. It does not expand MCP, calculate trends, invoke an LLM or publish to Telegram.

Required: latitude, longitude, speed_over_ground and course_over_ground. Optional: speed through water, depth, water temperature, apparent/true wind, current set/drift, roll/pitch, outside temperature/pressure and Calypso battery percentage.

Verification: MediaMan tests before=524 passed, after=539 passed, exact delta=15; H9b=48 passed, 0 failed.

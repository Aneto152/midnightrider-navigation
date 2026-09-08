# MediaMan Historical DRY_RUN Decision

## Scope

This document defines the offline historical DRY_RUN publication design.
It does not authorize real InfluxDB execution, Telegram publication,
production activation, Signal K, N2K, P5, Docker, or systemd changes.

## Approved decisions

- COMPLETE requires exactly four distinct valid fields:
  latitude, longitude, speed_over_ground, course_over_ground.
- SOG and COG are mandatory.
- Missing or invalid required facts block content generation and publication.
- No '?' placeholders are allowed in the historical publication path.
- The generic legacy sender fallback remains available for compatibility.
- Historical mode must reject an incompatible sender before entering SENDING.
- Historical mode must never use the process-local identity fallback.
- as_of_utc must use canonical ISO 8601 UTC with a literal Z suffix.
- Four independent historical metric queries are temporarily accepted.
- Every selected result must contain a valid actual _time.
- The maximum difference between the four selected _time values is 1000 ms.
- The aggregate source_timestamp is the newest selected _time.
- Individual source timestamps must remain available for auditability.
- race_id is metadata-only for the current single-race/single-session bucket invariant.
- If the single-race/single-session invariant cannot be demonstrated,
  race_id must become an MCP query parameter before real historical use.

## Snapshot terminology

The design uses the term:

bounded-skew historical snapshot

It must not be described as an atomic snapshot.

## Test boundary

The existing offline test is an orchestration test with mocked MCP boundaries.
It is not a real MCP-to-InfluxDB runtime E2E test.

Real local fake-MCP and synthetic HTTP/InfluxDB tests are planned.
Real InfluxDB execution remains separately unauthorized.

## Logging boundary

- stdout is reserved for JSON-RPC messages.
- Diagnostic logs must not be written to MCP stdout.
- Persistent service logs belong under:
  /home/pi/midnightrider-navigation/logs/services/
- Runtime logging is not considered validated until code and runtime checks pass.
- No credential, token, password, secret, or connection string may be logged.

## Metadata boundary

The following metadata fields are authoritative:

- audit_commit_sha
- implementation_commit_sha
- offline_orchestration_validated
- real_mcp_influxdb_runtime_e2e_validated
- production_readiness_status

runtime_e2e_validated must not be set to true for a test
that mocks MCP and InfluxDB boundaries.

remote_sha must not be used for two different commit meanings.

## Current status

- offline_orchestration_validated: false
- real_mcp_influxdb_runtime_e2e_validated: false
- production_readiness_status: BLOCKED — MULTIPLE_CODE_ISSUES
- real historical data: not executed
- Telegram publication: not executed

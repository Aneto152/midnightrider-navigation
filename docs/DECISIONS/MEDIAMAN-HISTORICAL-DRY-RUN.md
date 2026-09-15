# MediaMan Historical DRY_RUN Decision

## Scope

This document defines the historical DRY_RUN publication design.

Authorization status, updated 2026-09-15 by Denis:

- real InfluxDB read execution: AUTHORIZED and performed, see Current status
- Telegram publication: still NOT authorized, no credential accessed to date
- production activation, Signal K, N2K, P5, Docker and systemd changes:
  still NOT authorized by this document

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

tests/mediaman/test_historical_e2e_offline.py remains an orchestration test
with mocked MCP boundaries. tests/mcp/test_phase2_historical_contract.py,
23 tests, exercises the MCP contract against a synthetic HTTP/InfluxDB
double in the production CSV dialect.

Since 2026-09-15 these are no longer the only evidence: the full chain has
been executed against the real MCP server and the real InfluxDB instance,
see Current status. The offline doubles remain the regression net, the real
run remains the proof. Neither replaces the other.

## Logging boundary

- stdout is reserved for JSON-RPC messages.
- Diagnostic logs must not be written to MCP stdout.
- Persistent service logs belong under the logs/services/ directory OF THIS
  REPOSITORY, resolved from the module location by mediaman/logging_utils.py.
  The absolute path previously documented here, under the pi home directory,
  was wrong: on Midnight Rider the repository lives under /home/aneto, so
  setup_service_logger raised PermissionError, errno 13, and no service could
  initialise its logger at all. The historical entrypoint died on its very
  first statement. Fixed on 2026-09-15 in commit 43faf76. Absolute per-user
  paths must not be reintroduced in this document or in the code.
- Runtime logging is not considered validated until code and runtime checks pass.
- No credential, token, password, secret, or connection string may be logged.

## MCP tools/call response contract

mcp/servers/racing.js must return the tool payload inside the MCP 2024-11-05
result content envelope:

    result = { content: [ { type: 'text', text: <JSON string> } ],
               isError: false }

mediaman/mcp_client.py, _decode_mcp_result, enforces that envelope strictly
and rejects a bare result object with the message
"MCP result missing 'content' field". Returning the payload directly under
result is therefore a breaking contract violation even when the payload
itself is perfectly correct, which is exactly what happened on 2026-09-15:
the snapshot was right, the envelope was missing, and the whole chain
failed. Fixed in commit 43faf76.

Known gap: the other MCP servers under mcp/servers/ still answer with a bare
result object. MediaMan does not use them, but any Python or
specification-compliant consumer will need the same envelope.

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

## Current status, updated 2026-09-15

- offline_orchestration_validated: true
- real_mcp_influxdb_runtime_e2e_validated: true
  Evidence: mediaman/historical_entrypoint.py executed on the Raspberry Pi
  against the real racing.js MCP server and the real InfluxDB instance,
  DRY_RUN=true, as_of_utc 2026-09-07T14:36:26Z, window 60 seconds, exit
  code 0, four facts COMPLETE, bounded_skew_ms 1, source_timestamp
  2026-09-07T14:36:24.298Z, content generated and validated, publication
  state SENT with a provider_id carrying the dry-run prefix. Fact values
  are deliberately not recorded in this repository.
- implementation_commit_sha: 43faf7685431c322911dc449cf296745926b7f1c
- audit_commit_sha: f79abaf5ba1553c0f063033c41ce9a79a634b729
- contract test suite: 23 passed, 0 failed
- production_readiness_status: DRY_RUN_VALIDATED, NOT PRODUCTION READY
- real historical data: read once, in a bounded 60 second window, on
  2026-09-15
- Telegram publication: still not executed, no Telegram credential accessed

## Remaining work before production

1. mediaman/mcp_collector.py ignores fact_timestamps and bounded_skew_ms and
   never calls math.isfinite. The skew guarantee of this document is
   therefore enforced only inside racing.js, on the producer side.
2. tests/mcp/test_phase2_historical_contract.py advertises 24 scenarios for
   23 test functions, and none of them covers a skew of exactly 1000 ms
   accepted, a skew above 1000 ms rejected, preservation of the real _time
   values, selection of the newest source_timestamp, individual
   fact_timestamps, rejection of a non-finite value, or the HTTP timeout
   bound.
3. SEC-2026-09-14-01 remains open: the previously exposed InfluxDB token has
   not been revoked, even though a narrowly scoped replacement token now
   exists.
4. etc/systemd/system/midnight-logsync.service is obsolete, runs as user pi
   and uses git add -f, which would force-add gitignored service logs.
5. InfluxDB holds no measurement after 2026-09-07T14:36:24Z, so a live run
   needs fresh data before it can prove anything about live operation.

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

## Units contract, added 2026-09-18 (defect 63)

- Signal K serves angles in SI units. navigation.courseOverGroundTrue is
  therefore in radians, and the server published that raw value under the
  key course_over_ground_degrees: the collector labelled it
  unit="degrees_true" and the article printed "Cap: {value}deg", so a vessel
  heading 198 degrees would have been announced at 3.45 degrees.
- Measured proof, not convention: over 365 days of our own rows the field
  stays in [0.000000, 6.281400] rad, with 0 row(s) above 2*PI out of 4078141
  and 3626071 row(s) above 0.1 rad. A course expressed in degrees cannot
  stay below 6.29 for a year of sailing.
- mcp/servers/racing.js converts the course over ground from radians to true
  degrees exactly once, at the boundary of the server, in
  cogRadiansToDegrees(). The validated domain of the incoming value is [0,
  2*PI] and no longer [0, 360]: a degree interval contains the whole radian
  interval, which is why three successive validations never reported
  anything. A value beyond 2*PI now fails the collection loudly instead of
  publishing a false course.
- Every snapshot carries a units block next to facts: latitude and longitude
  in degrees, speed_over_ground_ms in m_per_s, course_over_ground_degrees in
  degrees_true. The block is a sibling of facts and never a fifth fact,
  because the four-field set is validated exactly.
- mediaman/mcp_collector.py refuses a payload whose units block contradicts
  that contract. An absent block is accepted, so an older server keeps
  working; a block that disagrees is a validation error.
- tests/mcp/test_defaut_63_cog_degres.py locks the conversion, the two
  domain bounds, the loud failure beyond 2*PI, the units block and the
  defect 58 context filter. Four of its eight tests fail against the code as
  it stood before this change: status of this run SUCCESS.

## One collection path, added 2026-09-18 (defect 65)

Decided with Denis on 2026-09-18, after measuring that the collector
addressed three tools - `racing.get_position`, `racing.get_sog`,
`racing.get_cog` - that the racing MCP server has never declared.

**Both uses are kept. Neither gets its own architecture.**

- Live consultation is the intended use during a race.
- Historical replay is the test bench for it, because a race cannot be
  debugged while it is being sailed.

The two differ by the temporal horizon and by nothing else. There is one
engine, `collectSnapshot(startUtc, endUtc)`, and two thin doors:

| Door | Upper bound chosen by | Freshness limit |
|------|----------------------|-----------------|
| `get_historical_snapshot(as_of_utc, window_seconds)` | the caller | none |
| `get_snapshot(start_utc, end_utc)` | the caller, set to now for live use | the window |

Those two lines are the complete list of legitimate differences. Everything
else - the Flux query, the `self == "true"` context filter of defect 58, the
bounded-skew check across the four facts, the radian-to-degree conversion of
defect 63, the `units` block - is shared by construction rather than by
discipline, because there is no second copy to keep in step.

**The server never asks what time it is.** The upper bound always arrives as
a parameter. This removes any need for a test backdoor: replaying a past
instant through the live code path is done by passing a past bound, not by
deceiving a clock. On the collector side the same role is played by
`reference_time`, which already existed.

**Bounds are normalised.** The engine rewrites both bounds through
`toISOString()` before building the query. Without it the two doors would
emit textually different queries for the same interval - `.000Z` against
`Z` - and convergence could only be checked on results, never on queries.

**What enforces this, in tests rather than in prose:**

- `tests/mcp/test_h9_chemin_unique.py` counts the Flux query builders in
  `racing.js` and requires exactly one;
- the same file asserts that both doors emit byte-identical queries and
  return identical facts and units for the same interval;
- it asserts that defects 58 and 63 stay closed through the new door;
- it forbids the three dead tool names from reappearing in the collector.

**What was removed, and why it was removed rather than completed:**
`collect()` and its three helpers, about 235 lines. Three separate calls
mean three instants, which cannot be skew-checked, and that code carried
neither the context filter nor the unit conversion. Completing it would have
reopened defects 58 and 63 on the path meant for racing.

`tests/mediaman/test_mcp_collector.py` - 627 lines, 32 tests - tested that
path exclusively and was deleted. Eight of its properties were ported to
`tests/mediaman/test_h9_collect_current.py`: coordinate suppression in logs
and in the LLM context, absence of any direct Signal K access, and the
handling of future or malformed timestamps. The other twenty-four asserted
a per-tool partial-collection semantics that no longer exists once the call
is atomic.

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

## Current status, updated 2026-09-18

- offline_orchestration_validated: true
- real_mcp_influxdb_runtime_e2e_validated: true
  Evidence: mediaman/historical_entrypoint.py replayed on the Raspberry Pi on
  2026-09-18 against the real racing.js MCP server and the real InfluxDB
  instance, with the defect 58 context filter in place, DRY_RUN=true,
  as_of_utc 2026-09-07T14:36:26Z, window 60 seconds, same parameters as the
  2026-09-15 run. Outcome: replay SUCCESS, dry-run enforcement verified. Publication id b36f4233caab5c1d.... Content generated and
  validated, publication state SENT with a provider_id carrying the dry-run
  prefix. Fact values are deliberately not recorded in this repository.
- superseded_evidence_2026_09_15: the original run reported exit code 0, four
  facts COMPLETE, bounded_skew_ms 1 and source_timestamp
  2026-09-07T14:36:24.298Z. That run queried InfluxDB WITHOUT any context
  filter, so its four facts may have belonged to an AIS target rather than to
  Midnight Rider. Measured on the same 60 second window on 2026-09-18: 4 of
  the four facts were selected from an AIS context, 4 of the four values
  change once the context filter is applied, the published position being about 11.04 nautical miles away from the vessel's actual position.
  Remeasured on 2026-09-18 at the instant the unfiltered query actually
  selected: exactly one row existed there for each of the 4 facts, so that
  query was deterministic. Replayed against the same dataset, frozen since
  2026-09-07, it returned an AIS context for 4 of the 4 facts. The
  2026-09-15 output is therefore wrong, not merely unverifiable. For 2 of
  the 4 facts that instant is the source_timestamp recorded on 2026-09-15. The 2026-09-15 status line
  must therefore not be read as proof about this vessel own data. It is kept
  here because the history of a decision is part of the decision. Defect 58
  was fixed in commit 8919130fe36e82dd66e8eb07a073e26234f48a9e, with six
  regression tests in tests/mcp/test_defaut_58_context_filter.py.
- our_sources_in_that_window: measured with schema.tagValues on the source
  tag, restricted by the predicate r.self == "true": N2K.1, N2K.2. N2K.0
  also writes navigation paths, but only for AIS contexts: it is the AIS
  receiver and never writes this vessel own context.
- measurement_method_note: the figure published on 2026-09-18 by chantier
  H8b, "only one context had written at that timestamp", was measured at OUR
  filtered winning timestamp and not at the instant the unfiltered query
  selected, so it did not answer the question it was written to answer.
  Corrected the same day by chantier H8c: 0 of 4 facts tie-broken, at most 1
  row(s) at the winning instant, 2 of 4 winning instants equal to the
  recorded source_timestamp. The commit message of
  1fa2853f91f1925c96a0972e57553f656fd1cb43 states the opposite conclusion;
  commit messages are not rewritten, this line supersedes it.
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
4. CLOSED on 2026-09-17, chantier H7e: etc/systemd/system/midnight-logsync
   was retired. The timer is disabled and inactive, the repository copies
   were realigned on the units actually installed and carry a retirement
   banner, and logs/debug/timers-systemd-2026-09-17.md records the
   measurement. The service had never run: WorkingDirectory pointed at
   /home/pi, so it failed with status=200/CHDIR roughly 480 times a day.
   No function was lost; scripts/commit-logs.sh covers all four log paths.
5. InfluxDB holds no measurement after 2026-09-07T14:36:24Z, so a live run
   needs fresh data before it can prove anything about live operation.

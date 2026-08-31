# Telegram Reporter (MediaMan) Integration Guide

**Status:** FOUNDATION ONLY — DRY-RUN VALIDATED — PRODUCTION ACTIVATION BLOCKED

**Current Development Phase (2026-08-31):**
- ✅ Outbound sender foundation (DRY_RUN validated)
- ✅ SQLite state machine (approved 9-state model)
- ✅ Logging infrastructure (structured, sanitized)
- ✅ Systemd units (service + timer) present but disabled
- ❌ Real content provider (not implemented)
- ❌ OpenClaw LLM adapter (not implemented)
- ❌ External publication bridge (not implemented)
- ⏳ Telegram bot/group (not created — development phase only)

## System Overview

MediaMan is a planned outbound-only Telegram reporter for race performance articles. No live Telegram contact has occurred. The current sender is NOT the future PublicationBridge.

**Security properties (current):**
- Outbound-only (no inbound webhook, polling, getUpdates, or command processing)
- No personal Telegram accounts
- No credentials in version control
- No credentials stored in logs
- No Signal K modifications required
- No Docker changes required
- Fail-closed: invalid content → skip send (never fake article)

## Publication State Machine — Approved Design

MediaMan uses an approved **9-state publication state machine** with explicit operator action requirements for certain transitions:

### State Definitions

```
READY                → Cycle generated, approved for validation
VALIDATED            → Content passed validation checks
SENDING              → Send attempt in progress
UNKNOWN              → Outcome ambiguous (no confirmation received)
RETRY_AUTHORIZED     → Operator explicitly authorized retry from UNKNOWN
SENT                 → Provider message ID confirmed (TERMINAL)
SENT_RECONCILED      → UNKNOWN → confirmed sent via manual evidence (TERMINAL)
FAILED               → Send failed permanently
DEAD_LETTER          → Operator explicitly abandoned publication attempt
```

### State Transitions (Approved)

**Normal Flow:**
- `READY` → `VALIDATED` (content validation passes)
- `VALIDATED` → `SENDING` (send attempt begins)
- `SENDING` → `SENT` (only when provider message ID is confirmed)

**Ambiguity Resolution (No Automatic Retry):**
- `SENDING` → `UNKNOWN` (no confirmation received, timeout exceeded)
- `UNKNOWN` → `SENT_RECONCILED` (operator provides explicit evidence of prior send)
- `UNKNOWN` → `RETRY_AUTHORIZED` (operator authorizes retry attempt)
- `RETRY_AUTHORIZED` → `READY` (retry cycle begins)
- `UNKNOWN` → `DEAD_LETTER` (operator explicitly abandons)

**Error Terminal:**
- `SENDING` → `FAILED` (send rejected by provider)
- `FAILED` → (retryable; external retry count, backoff, jitter, alerting, and terminal escalation remain PENDING operational decisions)

**Terminal States (Never Retried):**
- `SENT` — Provider message ID confirmed
- `SENT_RECONCILED` — Manual evidence of prior send
- `DEAD_LETTER` — Operator abandonment

### Approved Invariants

- `UNKNOWN` never retries automatically
- `SENDING` without confirmation never becomes `FAILED` automatically
- `SENT` and `SENT_RECONCILED` are permanent terminal states
- Exactly-once and zero-duplicate guarantees are **NOT** provided
- At-least-once delivery semantics (manual reconciliation required)

## Manual Reconciliation — Operator Evidence Format

When publication reaches `UNKNOWN` state (ambiguous outcome), the operator must provide explicit evidence to transition to `SENT_RECONCILED` or authorize retry.

### Evidence Reference Format

```
source:timestamp:reference_id
```

**Example (neutral placeholders only):**
```
manual_ui:2026-08-31T15:00:00Z:<external_reference_id>
monitoring:2026-08-31T15:00:00Z:<external_reference_id>
api_query:2026-08-31T15:05:30Z:<external_reference_id>
backup_log:2026-08-31T13:59:15Z:<external_reference_id>
```

### Evidence Properties

- **source:** Bounded and approved (manual_ui, monitoring, api_query, backup_log, etc.)
- **timestamp:** ISO 8601 UTC format (never timezone abbreviations)
- **reference_id:** External system identifier or operator-provided reference
- **No message body stored:** Evidence does not contain publication content
- **No credentials stored:** Evidence contains no tokens, chat IDs, or secrets
- **Operator attestation, not proof:** Evidence is human confirmation, not cryptographic proof
- **No automatic Bot API search:** Telegram Bot API cannot reliably search by content_hash
- **Manual operator action required:** All UNKNOWN transitions require explicit decision

### UNKNOWN → SENT_RECONCILED (With Evidence)

When evidence proves the publication was sent despite ambiguous response:

```
Evidence: monitoring:2026-08-31T14:30:15Z:<external_reference_id>
State transition: UNKNOWN → SENT_RECONCILED
Result: Terminal state, never retried
```

### UNKNOWN → RETRY_AUTHORIZED (With Operator Authorization)

When operator explicitly authorizes retry:

```
Action: RETRY_AUTHORIZED
Operator: <operator_name_or_id>
Timestamp: 2026-08-31T14:31:00Z
State transition: UNKNOWN → RETRY_AUTHORIZED → READY
Result: Retry cycle begins
```

### UNKNOWN → DEAD_LETTER (With Operator Abandonment)

When operator explicitly abandons publication attempt:

```
Action: DEAD_LETTER
Operator: <operator_name_or_id>
Timestamp: 2026-08-31T14:32:00Z
Reason: [operator provided reason]
State transition: UNKNOWN → DEAD_LETTER
Result: Terminal state, never retried or reconciled
```

## Current Status

### Validated Components

**DRY_RUN Foundation:**
- MediaMan main orchestration
- SQLite state machine (approved 9-state model)
- Logging infrastructure (structured, sanitized, no credentials)
- Outbound sender (test mode only)
- Systemd timer/service files (disabled)

**Test Coverage:**
- Outbound sender tests (all mocked, no network I/O)
- Logging validation tests
- DRY_RUN mode verified
- No automatic UNKNOWN retry verified
- No Telegram history-search methods

### Not Yet Implemented

- Real content provider (awaits approval and implementation)
- OpenClaw LLM adapter (awaits approval and implementation)
- PublicationBridge (awaits Step 4E/5 design completion)
- Telegram bot and group (not created)
- Production activation (not authorized)

## Execution Modes

### DRY_RUN Mode (Currently Authorized)

```bash
export DRY_RUN=true
export MEDIAMAN_CONTENT_PROVIDER=test
python3 -m mediaman.mediaman
```

**Allowed:**
- ✅ Validates SQLite state transitions
- ✅ Tests logging infrastructure
- ✅ No Telegram contact
- ✅ No network I/O
- ✅ Exit code 0 indicates success

### Production Mode (NOT Authorized)

Production activation requires:

1. Real content provider implementation (not yet approved)
2. Explicit Denis approval for Telegram bot creation
3. Secured environment variable configuration
4. Separate systemd unit configuration
5. Explicit production verification

**NOT AUTHORIZED IN CURRENT PHASE:**
- ❌ Creating Telegram bot
- ❌ Creating or joining Telegram group
- ❌ Sending real Telegram messages
- ❌ Enabling or starting mediaman.timer
- ❌ Configuring production credentials in version control

## Logging

### Service Logs (When Enabled)

Location: `/home/pi/midnightrider-navigation/logs/services/telegram-sender.log`

**Required Probes:**
- `STARTUP` — Initialization summary (no credentials)
- `HEARTBEAT` — One-shot sender heartbeat
- `DATA_IN` — Content length only (no message body)
- `DATA_OUT` — Provider status classification and content length
- `ERROR` — Exception class only (never raw message)
- `SHUTDOWN` — Clean completion event

**Security Guarantees:**
- No token values or fragments
- No chat IDs (including masked forms)
- No message bodies
- No raw Telegram responses
- No raw exception messages
- No credential-bearing URLs
- No connection strings

### Log Rotation

- Max file size: 5 MB
- Backup count: 3
- Format: Structured JSON (machine-readable)

## Pending Operational Decisions

The following remain **PENDING explicit approval** and are NOT implemented:

- Message language selection
- Message formatting (markdown, HTML, plain text)
- Maximum message length and truncation behavior
- External retry count and backoff strategy
- Jitter and retry timing
- Alerting strategy for failures
- Credential injection mechanism (environment vars vs. config file)
- Publication database path and schema
- Backup and restore procedures
- Manual deletion procedures
- Network and firewall approval (Cloudflare Tunnel, etc.)

**No implementation will occur for these items until explicitly approved by Denis.**

## Troubleshooting (Development Phase Only)

### Running a Dry-Run Test

```bash
export DRY_RUN=true
export MEDIAMAN_CONTENT_PROVIDER=test
python3 -m mediaman.mediaman
```

Expected: Exit 0, no network I/O, SQLite state transitions logged.

### Checking SQLite State

```bash
sqlite3 /var/lib/mediaman/state.sqlite3 \
  "SELECT state, race_id, cycle_id FROM deliveries ORDER BY created_at DESC LIMIT 5;"
```

### Viewing Logs

```bash
tail -20 /home/pi/midnightrider-navigation/logs/services/telegram-sender.log
```

### Systemd Timer Status (Non-Destructive)

```bash
systemctl is-enabled mediaman.timer || echo "not-found"
systemctl is-active mediaman.timer || echo "inactive"
```

## References

- **Repository:** `/home/aneto/midnightrider-navigation`
- **Source:** `mediaman/`
- **Tests:** `tests/mediaman/`
- **Systemd:** `etc/systemd/system/mediaman.{service,timer}`
- **Architecture:** See SYSTEM-SUMMARY.md and docs/ARCHITECTURE-MASTER.md

---

**Last Updated:** 2026-08-31
**Status:** Foundation Phase (DRY-RUN Validated, Production Blocked)
**Publication Design:** Approved 9-state machine with manual reconciliation
**Next Step:** Implement real content provider (OpenClaw or Regatta-based) and PublicationBridge

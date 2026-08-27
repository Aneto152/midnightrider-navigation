# Telegram Reporter (MediaMan) Integration Guide

**Status:** FOUNDATION ONLY — DRY-RUN VALIDATED — PRODUCTION ACTIVATION BLOCKED

**Current Development Phase (2026-08-27):**
- ✅ SQLite delivery state machine (PENDING → SENDING → SENT / FAILED)
- ✅ Telegram sender (outbound-only, no inbound)
- ✅ Logging infrastructure (structured, sanitized)
- ✅ Systemd units (service + timer) present but disabled
- ❌ Real content provider (not implemented)
- ❌ OpenClaw LLM adapter (not implemented)
- ⏳ Telegram bot/group (not created — development phase only)

## System Overview

MediaMan is a planned outbound-only Telegram reporter for race performance articles. It publishes content every 15 minutes to a temporary regatta group via a one-shot systemd timer.

**Security properties (current):**
- No inbound Telegram webhook, polling, getUpdates, or command processing
- No personal Telegram accounts
- No credentials in version control
- No Signal K modifications required
- No Docker changes required
- Fail-closed: invalid content → skip send (never fake article)

## Architecture

### Data Flow (When Implemented)

```
RaceFacts (validated) → Content Provider → Telegram Sender → Group Chat
                             ↓
                        (no inbound)
```

### Delivery States

```
PENDING → SENDING → SENT  (final, non-retryable)
              ↓
            FAILED → (retryable)
```

- **PENDING:** Cycle generated, waiting to send
- **SENDING:** In progress (stale sends after timeout are retryable)
- **SENT:** Confirmed by Telegram (never retried)
- **FAILED:** Send failed (remains retryable indefinitely)

### Idempotency Model

15-minute UTC buckets prevent duplicate sends:

```
2026-08-27T15:00:00Z → same send, if retried
2026-08-27T15:14:59Z → same cycle
2026-08-27T15:15:00Z → new cycle
```

## Current Status

### Validated Components

**DRY_RUN Foundation:**
- MediaMan main orchestration
- SQLite state transitions
- Logging (structured, sanitized)
- Test content provider (for validation only)
- Systemd timer/service files

**Test Coverage:**
- 51 unit tests (all passing)
- Dry-run integration test
- SQLite state machine test
- Logging signature test

### Blocked Components

**Content Provider:**
- OpenClawGatewayProvider: placeholder (raises NotImplementedError, must not be used for production) (raises NotImplementedError)
- TestContentProvider: test-only (cannot be used in production)
- Real LLM adapter: not implemented

**Telegram Integration:**
- No real bot created
- No real group created
- No real send authorized
- Timer remains disabled
- MEDIAMAN_PRODUCTION_MODE=false by default

## Not Authorized Yet

The following actions are NOT authorized in this development phase:

- ❌ Creating a Telegram bot account
- ❌ Creating or joining a Telegram group
- ❌ Enabling or starting mediaman.timer
- ❌ Sending real Telegram messages
- ❌ Configuring production credentials
- ❌ Exposing any endpoint via Portal/Regatta for Telegram inbound

## Future Activation (When Explicitly Approved)

### Phase 1: Create Telegram Infrastructure

This requires manual external action (not part of code):

1. Contact @BotFather on Telegram
   - Create dedicated bot for race reporting
   - Store token securely (not in this repo)

2. Create a private Telegram group
   - Add bot as admin (required for posting)
   - Store group ID securely (not in this repo)

### Phase 2: Implement Content Provider

Choose one of the following:

**Option A: OpenClaw CLI (Recommended)**
- Use documented command: `openclaw agent --agent main --message "<prompt>"`
- Timeout flag: `--timeout <seconds>` (not `--timeout-seconds`)
- File input: `--message-file <path>` available
- Local Gateway routing: default behavior
- Implementation required: MediaMan adapter for subprocess orchestration
- Status: Design complete, not yet implemented

**Option B: Regatta API Provider (Minimal Facts)**
- Proven data sources:
  - Own position: `/api/position`
  - Own speed/course: `/api/navigation`
  - Wind direction: `/api/race_data` (via Signal K)
  - Start line geometry: `/api/race_data`
  - Competitors nearby: `/api/ais` (if AIS active)
  - External wind: `/api/ndbc/<station>` (5+ min old)
- Unproven (must omit from content):
  - Race ID, elapsed time, ranking, competitor delta, heel angle
- Implementation required: Facts collector + article template
- Status: Design complete, not yet implemented

### Phase 3: Configure Runtime Environment

Create `/etc/mediaman/mediaman.env` (not version-controlled):

```bash
# Telegram credentials (required for production)
TELEGRAM_BOT_TOKEN is read from secured environment
TELEGRAM_CHAT_ID is read from secured environment

# Enable production mode
MEDIAMAN_PRODUCTION_MODE=true

# Select content provider (must be real, not "test")
MEDIAMAN_CONTENT_PROVIDER=test  # (only test or gateway supported)

# Disable dry-run
DRY_RUN=false

# Race identifier
MEDIAMAN_RACE_ID=block-island-2026
```

Protect the file:
```bash
sudo chmod 600 /etc/mediaman/mediaman.env
```

### Phase 4: Enable Systemd Timer

Only after content provider and credentials are verified:

```bash
**Future Production Activation** (not yet authorized):

When MediaMan real content provider is implemented and explicitly approved by Denis:
1. Create Telegram bot via @BotFather → obtain TELEGRAM_BOT_TOKEN
2. Create private Telegram group → obtain TELEGRAM_CHAT_ID
3. Configure credentials in /etc/mediaman/mediaman.env
4. Test with DRY_RUN=true first
5. Enable timer: Timer activation is not authorized in the current development phase.
6. Start: Timer activation is not authorized in the current development phase.
7. Monitor: journalctl -u mediaman -f

**This procedure requires explicit approval and is not authorized in the current development phase.**
sudo journalctl -u mediaman -f  # Monitor
```

**WARNING:** These commands are NOT authorized in the current development phase.

## Testing (Current Development Phase)

### Dry-Run Validation (Currently Authorized)

Test the complete stack without network I/O:

```bash
export TELEGRAM_BOT_TOKEN is read from secured environment
export TELEGRAM_CHAT_ID is read from secured environment
export DRY_RUN=true
export MEDIAMAN_CONTENT_PROVIDER=test

python3 -m mediaman.mediaman
```

Expected results:
- Exit code: 0
- No network requests to Telegram
- SQLite state transitions: PENDING → SENDING → SENT
- Logs sanitized (no credentials)

### Unit Tests

```bash
python3 -m unittest discover -s tests/mediaman -p 'test_*.py'
```

Expected: 51/51 tests pass

### Real Test (NOT Authorized Yet)

Once production activation is explicitly approved, use:

```bash
export TELEGRAM_BOT_TOKEN is read from secured environment
export TELEGRAM_CHAT_ID is read from secured environment
export MEDIAMAN_PRODUCTION_MODE=true
export DRY_RUN=false
export MEDIAMAN_CONTENT_PROVIDER=test  # (only test or gateway supported)

python3 -m mediaman.mediaman
```

This is NOT authorized in the current development phase.

## Data Availability (Verified)

### Proven Sources

| Data | Source | Unit | Freshness |
|------|--------|------|-----------|
| Own position | `/api/position` | degrees | ≤ 30s |
| Own SOG | `/api/navigation` | knots | Real-time |
| Own COG | `/api/navigation` | degrees | Real-time |
| Wind direction | `/api/race_data` → Signal K | degrees | ≤ 10s |
| Start line distance | `/api/race_data` | meters | Real-time |
| Start line side | `/api/race_data` | enum (OCS/CLEAR/BEHIND) | Real-time |
| Competitors nearby | `/api/ais` | count | Event-driven |
| External wind speed | `/api/ndbc/<station>` | knots | 5-30 min |

### Not Available

- ❌ Race ID (not returned by any endpoint)
- ❌ Race elapsed time (no timer state exposed)
- ❌ Own ranking or competitor delta (requires external algorithm)
- ❌ Own heel angle (not queried from Signal K)
- ❌ True wind speed from Signal K (NDBC used instead, with age)

## Logging

### Service Logs (When Enabled)

Location: `/var/log/mediaman/mediaman.log`

Example output (DRY_RUN=true):

```
[2026-08-27T15:30:00] [INFO] [mediaman] STARTUP dry_run=True
[2026-08-27T15:30:00] [INFO] [mediaman] CONTENT_VALIDATION race_id=... cycle=... length=450 valid=True
[2026-08-27T15:30:00] [INFO] [mediaman] SEND_ATTEMPT dry_run=True chat_id=***** length=450 execution_id=...
[2026-08-27T15:30:01] [INFO] [mediaman] SEND_RESULT dry_run=True success=True provider_status=DRY_RUN error_code= execution_id=...
[2026-08-27T15:30:01] [INFO] [mediaman] HEARTBEAT provider=test
[2026-08-27T15:30:01] [INFO] [mediaman] SHUTDOWN execution_count=1
```

**Security note:** No credentials are logged. Chat ID is masked. Token is never included.

## Security & Privacy

### What's Protected

- ✅ Telegram bot token: never logged or exposed
- ✅ Chat ID: masked in logs (`-*******`)
- ✅ Message bodies: not logged (only length)
- ✅ Credentials: environment variables only (not code)
- ✅ No personal Telegram accounts
- ✅ No inbound message processing
- ✅ No webhook listener
- ✅ One-way flow enforced

### What You Must Protect

Once production credentials are configured:

- `/etc/mediaman/mediaman.env` → `chmod 600`
- Telegram bot token → rotate regularly via @BotFather
- Group membership → admins only
- Chat ID → not shared publicly

## State Management (SQLite)

MediaMan uses SQLite for idempotent delivery tracking:

```sql
CREATE TABLE deliveries (
    delivery_key TEXT PRIMARY KEY,
    race_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    state TEXT CHECK (state IN ('PENDING', 'SENDING', 'SENT', 'FAILED')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    sent_at INTEGER,
    provider_message_id TEXT,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    UNIQUE(race_id, cycle_id, target_id)
);
```

**Recovery:**
- Stale SENDING (> 3600s): retryable
- SENT: never retried
- FAILED: remains retryable
- PENDING: transient

## Troubleshooting (Development Phase)

### Running a Dry-Run Test

```bash
export TELEGRAM_BOT_TOKEN is read from secured environment
export TELEGRAM_CHAT_ID is read from secured environment
export DRY_RUN=true
export MEDIAMAN_CONTENT_PROVIDER=test

python3 -m mediaman.mediaman
```

Expected: Exit 0, no network I/O, SQLite state transitions.

### Checking SQLite State

```bash
sqlite3 /var/lib/mediaman/state.sqlite3 \
  "SELECT state, race_id, cycle_id FROM deliveries ORDER BY created_at DESC LIMIT 5;"
```

### Viewing Logs

```bash
tail -20 /var/log/mediaman/mediaman.log
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
- **Architecture:** See SYSTEM-SUMMARY.md

---

**Last Updated:** 2026-08-27
**Status:** Foundation Phase (DRY-RUN Validated, Production Blocked)
**Next Step:** Implement real content provider (OpenClaw or Regatta-based)

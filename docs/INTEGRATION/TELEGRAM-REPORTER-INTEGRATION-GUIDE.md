# Telegram Reporter (MediaMan) Integration Guide

**Status:** Foundation phase - production ready for safe deployment

## System Overview

MediaMan is a **one-way outbound reporter** for Telegram group messages. It publishes race performance articles every 15 minutes to a temporary regatta group.

- **No inbound processing** – read-only sender
- **No webhook** – systemd timer-triggered one-shot
- **No personal accounts** – dedicated bot account required
- **No credentials in code** – environment variables only
- **Idempotent delivery** – 15-minute cycle buckets prevent duplicates

## Architecture

### Data Flow

```
SK System → MediaMan → Telegram Bot API → Group Chat
(one-way, no replies, no callbacks)
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
2026-08-26T19:00:00Z → same send, if retried
2026-08-26T19:14:59Z → same cycle
2026-08-26T19:15:00Z → new cycle
```

## Setup

### 1. Telegram Bot Account

Create a bot via @BotFather:

```
/newbot
Name: Midnight Rider Reporter
Username: midnight_rider_reporter_bot
```

You will receive: `TELEGRAM_BOT_TOKEN=123456:ABC...`

### 2. Telegram Group (Temporary per Regatta)

Create a private group for each regatta:

- Group name: `Midnight Rider — Block Island 2026`
- Make the bot an admin (required for posting)
- Only admins can send messages

### 3. Environment Configuration

Create `/etc/mediaman/mediaman.env`:

```bash
# Required for production
TELEGRAM_BOT_TOKEN=<bot-token-from-botfather>
TELEGRAM_CHAT_ID=<group-id>

# Production activation (defaults to false for safety)
MEDIAMAN_PRODUCTION_MODE=true

# Content provider (future: "gateway" for SK integration)
MEDIAMAN_CONTENT_PROVIDER=test

# Dry-run disabled (required for real sends)
DRY_RUN=false

# Race identifier
MEDIAMAN_RACE_ID=block-island-2026
```

**⚠️ Security:** This file must be protected:

```bash
sudo chmod 600 /etc/mediaman/mediaman.env
```

### 4. Systemd Activation

```bash
sudo systemctl enable mediaman.timer
sudo systemctl start mediaman.timer
```

Monitor:

```bash
sudo journalctl -u mediaman -f
```

## Testing

### Dry-Run (No Network I/O)

```bash
export DRY_RUN=true
python3 -m mediaman.mediaman
```

Expected: Logs show "DRY_RUN" and no network requests.

### Real Test (With Real Bot)

```bash
export TELEGRAM_BOT_TOKEN=<your-token>
export TELEGRAM_CHAT_ID=<your-chat-id>
export MEDIAMAN_PRODUCTION_MODE=true
export DRY_RUN=false
python3 -m mediaman.mediaman
```

Expected: One message sent to group.

## Logging

### Service Logs

```bash
/var/log/mediaman/mediaman.log
```

Structured output (rotated at 5 MB, 3 backups):

```
[2026-08-26T19:00:00] [INFO] [mediaman] STARTUP dry_run=False
[2026-08-26T19:00:00] [INFO] [mediaman] CONTENT_VALIDATION race_id=block-island cycle=2026-08-26T19:00:00Z length=450 valid=True
[2026-08-26T19:00:00] [INFO] [mediaman] SEND_ATTEMPT dry_run=False chat_id=-******* length=450 execution_id=abc12345
[2026-08-26T19:00:01] [INFO] [mediaman] SEND_RESULT dry_run=False success=True provider_status=OK error_code= execution_id=abc12345
[2026-08-26T19:00:01] [INFO] [mediaman] HEARTBEAT cycle=2026-08-26T19:00:00Z provider=test
[2026-08-26T19:00:01] [INFO] [mediaman] SHUTDOWN execution_count=1
```

### Data-Flow Logs

```bash
/var/log/mediaman/data-flow.log
```

## Idempotency & Locking

MediaMan uses **fcntl file locking** for safe concurrent access:

1. Lock on `/var/lib/mediaman/idempotency.lock`
2. Load state from `/var/lib/mediaman/idempotency.json`
3. Check if cycle was already sent
4. If not sent: write temp file → fsync → atomically rename
5. Release lock

This prevents:

- Duplicate sends (same cycle)
- Concurrent state corruption
- Lost updates

## Security & Privacy

✅ **What's protected:**

- Telegram bot token never logged
- Chat IDs masked in logs (`-*******`)
- Message bodies not logged (only length)
- Credentials in environment, not code
- No personal Telegram accounts
- No inbound message processing
- No webhook listener

⚠️ **What you must protect:**

- `/etc/mediaman/mediaman.env` – chmod 600
- Telegram bot token – rotate regularly
- Group membership – admins only
- Chat ID – not shared publicly

## Recovery

### Stale SENDING State

If the process crashes during send, the state remains "SENDING". On next run:

```
Check timestamp → if > stale_timeout: retry
```

This is safe: a stale send is retried, duplicate is prevented by cycle ID.

### Failed Send

```
State: FAILED
Error: "NETWORK_ERROR" (or Telegram error code)

Next cycle: automatically retried
Manual retry: run same MEDIAMAN_RACE_ID within same 15-minute bucket
```

### Production Activation

To go live:

1. Create bot + group (Telegram)
2. Write `/etc/mediaman/mediaman.env`
3. Run one-shot test: `python3 -m mediaman.mediaman`
4. Verify message in group
5. Enable timer: `sudo systemctl enable mediaman.timer`
6. Start timer: `sudo systemctl start mediaman.timer`
7. Monitor logs: `journalctl -u mediaman -f`

## Future: OpenClaw Gateway Integration

The `OpenClawGatewayProvider` is a placeholder for fetching French race articles directly from the SK system. When implemented, it will:

1. Call local Gateway API (documented path TBD)
2. Fetch race-specific article content
3. Validate French output
4. Send via Telegram

This allows real-time race reporting instead of test articles.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Timer not running | `sudo systemctl status mediaman.timer` |
| No message in group | Check logs: `journalctl -u mediaman -n 20` |
| "FAILED" state persists | Verify token/chat ID in .env, then retry |
| "SENDING" for >1 hour | Stale state: manual restart of timer |
| Token leaked in logs | Update token via @BotFather, rotate immediately |

## References

- Telegram Bot API: https://core.telegram.org/bots/api
- MediaMan README: `mediaman/README.md`
- Systemd units: `etc/systemd/system/mediaman.{service,timer}`
- Configuration schema: `.env.example`

---

**Last Updated:** 2026-08-27  
**Version:** 1.0 (Foundation)  
**Status:** Production-ready for safe deployment

# MediaMan — Telegram Outbound Reporter

Outbound-only race reporting publisher for Telegram groups.

## Architecture

- **One-shot execution**: MediaMan runs once per 15 minutes (via systemd timer), generates content, sends to Telegram, exits.
- **Outbound only**: No webhooks, no getUpdates, no inbound message processing.
- **No port exposure**: No listening port, no API endpoint exposed via portal/regatta.
- **Local content**: Articles generated locally (test provider or future OpenClaw Gateway).
- **Idempotent**: Same cycle never sent twice to same group.
- **Dry-run capable**: Run with `DRY_RUN=true` for testing without network I/O.

## Components

### `telegram_sender.py`
Telegram Bot API abstraction for `sendMessage` operation.

```python
sender = TelegramSender()
result = sender.send("Article text")
print(result.success)  # True/False
```

**Environment variables:**
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `TELEGRAM_CHAT_ID`: Target group ID (e.g., `-123456789`)
- `DRY_RUN`: Set to `"true"` for test mode

**Returns:** `SendResult` with sanitized fields (no token, no full chat ID).

### `content_provider.py`
Pluggable content generators.

**TestContentProvider**: Deterministic test article in French.

```python
provider = TestContentProvider()
content = provider.get_content("race-id", "2026-08-26T18:00:00")
```

**OpenClawGatewayProvider** (placeholder): Future integration with local Gateway (not yet implemented).

### `idempotency.py`
Tracks sends to prevent duplicate cycles.

```python
store = IdempotencyStore()
key = IdempotencyKey("race-id", "2026-08-26T18:00:00", "-123456789")
if store.check_and_record(key):
    send()  # New cycle, safe to send
```

**State file:** `~/.openclaw/mediaman/idempotency.json` (outside Git)

### `logging_utils.py`
Structured logging with sanitization.

- **Service logs**: `logs/services/mediaman.log` (5 MB rotating)
- **Data flow logs**: `logs/debug/data-flow.log`
- **Sanitization**: Tokens redacted, chat IDs masked, no sensitive data

### `mediaman.py`
Main orchestration script.

```bash
DRY_RUN=true python3 -m mediaman.mediaman
```

## Testing

### Dry-run (no network I/O)

```bash
export DRY_RUN=true
python3 -m mediaman.mediaman
```

Expected:
- ✅ Content generated
- ✅ Validation passes
- ✅ Idempotency key calculated
- ✅ No network request made
- ✅ Logs written to `logs/services/mediaman.log`

### With pytest

```bash
python3 -m pytest -q tests/mediaman
```

## Environment Variables

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `TELEGRAM_BOT_TOKEN` | Yes (for real sends) | `123456:ABC...` | From @BotFather |
| `TELEGRAM_CHAT_ID` | Yes (for real sends) | `-123456789` | Group ID (negative) |
| `DRY_RUN` | No | `true` | Simulate without network I/O |
| `MEDIAMAN_CONTENT_PROVIDER` | No | `test` | `test` or `gateway` (default: test) |
| `MEDIAMAN_RACE_ID` | No | `alir2026` | Race identifier |

## Systemd Integration

**Service file** (not enabled): `etc/systemd/system/mediaman.service`

```bash
sudo systemctl start mediaman.service    # One-shot execution
```

**Timer** (not enabled): `etc/systemd/system/mediaman.timer`

```bash
sudo systemctl start mediaman.timer      # Run every 15 minutes
sudo systemctl status mediaman.timer
```

**To enable for production** (requires Denis validation):
```bash
sudo systemctl enable mediaman.timer
sudo systemctl start mediaman.timer
```

## Security & Privacy

- ✅ No inbound message processing
- ✅ No webhook or listener
- ✅ No getUpdates API call
- ✅ No personal Telegram account
- ✅ Token never logged
- ✅ Chat ID masked in logs
- ✅ Content articles not logged (only length)
- ✅ One-way communication only

## Logging Format

### Service log (`logs/services/mediaman.log`)

```
[2026-08-26T18:00:00] [INFO] [mediaman] STARTUP dry_run=False
[2026-08-26T18:00:00] [INFO] [mediaman] CONTENT_VALIDATION race_id=alir2026 cycle=2026-08-26T18:00:00 length=450 valid=True
[2026-08-26T18:00:00] [INFO] [mediaman] SEND_ATTEMPT dry_run=False chat_id=****6789 length=450 execution_id=abc12345
[2026-08-26T18:00:01] [INFO] [mediaman] SEND_RESULT dry_run=False success=True provider_status=OK error_code= execution_id=abc12345
[2026-08-26T18:00:01] [INFO] [mediaman] SHUTDOWN execution_count=1
```

### Data-flow log (`logs/debug/data-flow.log`)

```
[2026-08-26T18:00:00] DATA_OUT provider_status=OK success=True length=450
```

## Future: OpenClaw Gateway Provider

The `OpenClawGatewayProvider` is a placeholder for integration with the local OpenClaw Gateway. When implemented, it will:

1. Call `http://localhost:18789/api/mediaman/article?race_id=...&cycle_ts=...`
2. Fetch French article from Gateway (outbound only)
3. Send to Telegram
4. **Never forward Telegram messages back to Gateway**

This integration requires:
- OpenClaw Gateway API to be documented
- No credentials in the request
- Testable without real send operations

## Troubleshooting

### `TELEGRAM_BOT_TOKEN not configured`

Make sure the environment variable is set:

```bash
echo $TELEGRAM_BOT_TOKEN
```

Or use dry-run to test without token:

```bash
DRY_RUN=true python3 -m mediaman.mediaman
```

### `Content does not appear to be in French`

The TestContentProvider checks for French characters or words. Verify content includes:
- Accented characters: é, è, ê, ç
- Or common French words: le, la, et, un, une

### Duplicate cycle skipped

If MediaMan skips a cycle, it means the same race+timestamp+chat_id combination was already sent. Check `~/.openclaw/mediaman/idempotency.json`.

To clear for testing:

```python
from mediaman.idempotency import IdempotencyStore
store = IdempotencyStore()
store.clear_for_testing()
```

## Status: Foundation Phase

✅ **Complete**
- Telegram sender (no inbound)
- Content provider (test + placeholder)
- Idempotency tracking
- Structured logging
- Unit tests
- Systemd files (not enabled)

⏳ **Pending Production**
- Denis validation of Telegram bot account setup
- Timer enabled only after validation
- Integration with OpenClaw Gateway (future)
- Real race data provider (future)

---

**Last Updated**: 2026-08-26  
**Version**: 1.0.0 (Foundation)  
**Architecture**: Outbound-only, one-shot, no inbound processing

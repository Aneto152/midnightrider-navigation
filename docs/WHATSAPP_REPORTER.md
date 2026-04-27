# WhatsApp Race Reporter — "Media Man" Agent

**Status:** 🚀 In Development  
**Purpose:** Send narrative race updates via WhatsApp during Block Island Race 2026  
**Target Audience:** Family, friends, colleagues  
**Tone:** Engaging play-by-play commentary (like a sports announcer)

---

## Architecture

```
Data Sources (via MCP)
    ↓
Media Man Agent (orchestrator)
    ├─→ Narrator (formats messages)
    ├─→ WhatsApp Sender (Twilio API)
    └─→ InfluxDB (logs)
         ↓
    WhatsApp Group/Recipients
```

---

## Recipients

Recipients stored in `.env.local`:
```
WHATSAPP_RECIPIENTS="33612345678,33698765432,33555123456"
WHATSAPP_ACCOUNT_SID="AC..."
WHATSAPP_AUTH_TOKEN="..."
TWILIO_PHONE_FROM="+1234567890"
```

---

## Message Types

### 1. Position Updates (Every 30 min)

**Trigger:** Timer  
**Format:** Brief narrative with location, speed, wind

Example:
```
⛵ Midnight Rider — Pos Update
Position: 41°25'N, 71°54'W
Speed: 7.2 kt, Heading: 095°
Wind: 12 kt from SE
Distance to mark: 4.2 nm
Status: On course ✅
```

### 2. Race Start

**Trigger:** Manual command or auto-detect (gun time)  
**Format:** Energetic announcement

Example:
```
🏁 RACE START!
Midnight Rider crossed the line clean!
Wind: 14 kt, Seas: 2-3 ft
Competitors: Sailing Eutopia (left), Cats Meow (right)
Go Denis! 🚀
```

### 3. Wind Alert

**Trigger:** TWS > WIND_ALERT_KT (e.g., 18 kt)  
**Limit:** Max 1 per 30 min  
**Format:** Warning tone

Example:
```
⚠️ WIND ALERT
Gust to 22 kt detected!
We've reefed main, holding 6.8 kt
Keep it steady! 💪
```

### 4. Speed Record

**Trigger:** SOG > previous max + 0.5 kt  
**Format:** Celebration

Example:
```
🔥 NEW RECORD!
8.4 knots — best speed of the day!
Wind's picking up. Excellent boat handling 👏
```

### 5. Mark Rounding

**Trigger:** Manual command or auto-detect (waypoint)  
**Format:** Narrative milestone

Example:
```
🎯 MARK 2 ROUNDED!
Clean turn, heading for Mark 3
Current position: 4.2 nm from finish
ETA: 2 hours 45 min
Keep pushing! ⛵
```

### 6. Finish

**Trigger:** Boat crosses finish line (GPS)  
**Format:** Celebration

Example:
```
🏆 FINISHED!
Midnight Rider crosses the finish line!
Elapsed time: 7 hours 23 minutes
Congrats team! 🎉⛵
Celebrating at the club... 🍾
```

---

## Contextual Logic

### Boat Allure Detection

From TWD (true wind direction) and COG:
- **Close-hauled:** TWD ± 45° from COG → "beating", "hard on the wind"
- **Reaching:** TWD 45-135° from COG → "reaching", "nice reach"
- **Running:** TWD > 135° from COG → "running", "spinnaker mode"

### Day/Night Tone

- **Day (sunrise to sunset):** Energetic, detailed
- **Night (sunset to sunrise):** Safety-focused, minimal detail (reduce screen time)

### Wind Context

- **Light (< 10 kt):** "Conditions light... looking for pressure"
- **Moderate (10-15 kt):** "Nice wind, boat's moving"
- **Fresh (15-20 kt):** "Building conditions, crew's busy"
- **Strong (> 20 kt):** "Significant breeze! Careful sailing"

---

## Queue & Offline Mode

### Message Queue

File: `/var/lib/midnight-reporter/queue.json`

```json
{
  "messages": [
    {
      "recipient": "33612345678",
      "text": "Position update...",
      "timestamp": "2026-05-22T12:34:56Z",
      "retry_count": 0,
      "status": "pending"
    }
  ],
  "max_size": 20
}
```

### Offline Handling

1. If WhatsApp send fails → queue message
2. On reconnect → drain_queue() sends all queued messages
3. Max 20 messages in queue (FIFO drop if exceeded)
4. Retry up to 3 times before dropping

---

## MCP Tools Used

**Existing MCP Tools (do not modify):**
- `boat_performance(minutes)` → SOG, VMG, heel
- `race_context()` → marks, distance, ETA
- `weather_lis_now()` → wind, pressure
- `current_polar()` → TWS, TWA, target speed
- `fleet_status()` → competitors (if available)

---

## Configuration

### .env.local

```
# WhatsApp Configuration
WHATSAPP_RECIPIENTS="33612345678,33698765432,33555123456"  # Comma-separated
WHATSAPP_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
WHATSAPP_AUTH_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_PHONE_FROM="+1234567890"

# Reporter Configuration
WIND_ALERT_KT=18
SPEED_RECORD_THRESHOLD_KT=0.5
POSITION_UPDATE_INTERVAL_MIN=30
```

### Recipients

Example group:
- Denis Lafarge (skipper) - 33612345678
- Anne-Sophie (crew) - 33698765432
- Shore team lead - 33555123456
- Family WhatsApp group - [group ID]

---

## Services & Logging

### Systemd Service

File: `/etc/systemd/system/midnight-reporter.service`

```ini
[Unit]
Description=Midnight Rider WhatsApp Race Reporter
After=network.target signalk.service

[Service]
Type=simple
User=aneto
WorkingDirectory=/home/aneto/.openclaw/workspace
ExecStart=/usr/bin/python3 src/reporter/media_man.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### InfluxDB Logging

Each message logged to:
- Measurement: `reporter_log`
- Fields: `message_type`, `recipient_count`, `queue_size`
- Tags: `status` (sent/queued/failed)

Query example:
```
from(bucket:"midnight_rider")
  |> filter(fn: (r) => r._measurement == "reporter_log")
  |> range(start: -24h)
```

---

## Testing

### Phase 1 Test

```bash
python3 src/mcp_tools/whatsapp_send.py --test
# Expected: Denis receives "✅ Test Media Man — système opérationnel"
```

### Phase 2 Test

```bash
python3 src/reporter/narrator.py --mock
# Expected: Sample messages printed to console
```

### Phase 3 Test

```bash
systemctl start midnight-reporter
# Check logs: journalctl -u midnight-reporter -f
```

### Pre-Race Test (May 19)

1. **Static test (2h at dock):**
   - Send position update every 30 min
   - Verify WhatsApp reception
   - Check queue handling

2. **Offline test (10 min):**
   - Disconnect network
   - Send 5 messages to queue
   - Reconnect
   - Verify drain_queue() sends all messages

3. **Manual commands:**
   - Send "DÉPART" → race start message
   - Send "MARK1" → mark rounding message
   - Send "FINISH" → finish message

---

## Tone Examples

### Conservative (Morning, Light Wind)

```
⛵ Good morning from Midnight Rider!
Position: 41°30'N, 71°52'W
Speed: 5.2 knots (light air)
We're working the shifts, looking for breeze
Radio check: all systems go ✅
```

### Excited (Afternoon, Fresh Wind)

```
🔥 MIDNIGHT RIDER IS FLYING!
8.1 knots, close-hauled, perfect conditions!
The whole team's dialed in
Competitors: Sailing Eutopia 0.3nm to port
Let's GO! ⚡
```

### Cautious (Night, Strong Wind)

```
🌙 Night sailing, 16 kt wind
Midnight Rider: 7.2 kt, under control
Sea state building 3-4 ft
All hands alert, watch rotation active
Stay safe out there ⛵
```

---

## FAQ

**Q: Can we send photos?**
A: Phase 1 is text-only. Photos later if time permits.

**Q: What if no internet at start?**
A: Messages queue in `queue.json`, drain when connection restored.

**Q: Can Denis trigger messages manually?**
A: Yes — via command/button on iPad, or verbal instructions logged.

**Q: What if Twilio is down?**
A: Messages queue and retry. Dashboard shows queue status.

**Q: How do we test without race data?**
A: Use `--mock` flag with faker data. See Phase 2 test.

---

## Success Criteria

- [x] Doc created (this file)
- [ ] Phase 1: WhatsApp tool works (test message sent)
- [ ] Phase 2: Narrator formats messages correctly
- [ ] Phase 3: Media Man agent runs without errors
- [ ] Phase 4: Full integration test passes

---

**Next:** Proceed to Phase 1 implementation (whatsapp_send.py)

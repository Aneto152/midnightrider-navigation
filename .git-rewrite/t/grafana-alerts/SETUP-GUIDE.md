# Grafana Alerts Setup Guide — MidnightRider

**Status:** Ready for Implementation  
**Date:** 2026-04-20  
**Estimated Time:** 20-30 minutes

---

## Quick Start

### Step 1: Create Telegram Bot (5 minutes)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Follow prompts:
   - Name: "MidnightRider Alerts"
   - Username: "midnight_rider_bot" (or similar)
4. Copy the **bot token** (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Get Your Chat ID (2 minutes)

1. In Telegram, add the bot you just created to a chat/group
2. Send any message to the bot (or `/start`)
3. Open this URL in browser (replace TOKEN with your bot token):
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. Look for the `"id"` field under `"chat"`
5. Copy this ID (it's a number, like: `-1001234567890` or `12345678`)

### Step 3: Set Environment Variables (2 minutes)

On the server where Grafana runs:

```bash
# Option A: Export in shell
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234..."
export TELEGRAM_CHAT_ID="12345678"

# Option B: Add to /etc/default/grafana-server (permanent)
sudo nano /etc/default/grafana-server

# Add these lines:
# TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234..."
# TELEGRAM_CHAT_ID="12345678"
```

### Step 4: Configure in Grafana UI (10 minutes)

#### 4.1 Create Contact Point

1. Open Grafana: http://localhost:3001
2. Login: admin / Aneto152
3. Go to: **Alerting** → **Contact Points**
4. Click **+ New Contact Point**
5. Fill in:
   - Name: `Telegram - Denis`
   - Contact Type: `Telegram`
   - Bot Token: (paste your bot token)
   - Chat ID: (paste your chat ID)
6. Click **Test** (should send test message to Telegram)
7. Click **Save**

#### 4.2 Configure Notification Policy

1. Still in **Alerting**, click **Notification Policies**
2. Click **Edit** on default policy
3. Set:
   - Receiver: `Telegram - Denis`
   - Group by: `alertname, instance`
   - Group interval: `5m`
   - Group wait: `10s`
   - Repeat interval: `4h`
4. Click **Save**

#### 4.3 Create Alert Rules

1. Go to: **Alerting** → **Alert Rules**
2. Click **+ Create Alert Rule**
3. For each alert, fill in:

**Alert 1: Sunset Approaching**
```
Name: Sunset Approaching (2h)
Query: 
  - Metric: environment.sun.sunsetTime
  - Condition: < now + 120 minutes
Evaluate: Every 1 hour
For: 5 minutes
Severity: warning
Receiver: Telegram - Denis
```

**Alert 2: Night Critical (30 min)**
```
Name: CRITICAL - Night in 30 Minutes
Query:
  - Metric: environment.sun.sunsetTime
  - Condition: < now + 30 minutes
Evaluate: Every 5 minutes
For: 1 minute
Severity: critical
Receiver: Telegram - Denis
```

**Alert 3: Distance to Start Line**
```
Name: Distance to Start Line (< 300m)
Query:
  - Metric: regatta.start_line
  - Condition: < 300 meters
Evaluate: Every 10 seconds
For: 10 seconds
Severity: warning
Receiver: Telegram - Denis
```

**Alert 4: Pressure Drop**
```
Name: Pressure Drop (> 3 hPa/3h)
Query:
  - Metric: Calculate 3-hour trend of pressure
  - Condition: > 3 hPa drop
Evaluate: Every 30 minutes
For: 5 minutes
Severity: warning
Receiver: Telegram - Denis
```

---

## Testing Alerts

### Test 1: Telegram Connection

1. In Grafana, go to **Alerting** → **Contact Points**
2. Find "Telegram - Denis"
3. Click the **three dots** → **Test**
4. Should receive test message in Telegram

### Test 2: Sunset Alert

1. Create a test dashboard with a stat panel
2. Query: `SELECT sunset_time FROM environment.sun`
3. Set alert threshold: < 120 minutes
4. Trigger manually: Set fake data < 120 min
5. Alert should fire → Telegram message

### Test 3: Race Alert

1. Create stat panel for `regatta.start_line`
2. Set alert: < 300m
3. Manually set value to 250m
4. Alert should fire → Telegram message received

---

## Alert Types & Behaviors

### INFO (Informational)
- Dashboard color changes only
- No Telegram notification
- Examples: Rate of turn, speed changes
- Repeat: Never

### WARNING
- Telegram notification sent
- Repeats every 30 seconds - 10 minutes
- Examples: Sunset approaching, distance to line
- Action: Visual + notification

### CRITICAL
- Immediate Telegram notification
- Repeats every 1 minute
- Examples: Night in 30 min, race start imminent
- Action: Urgent notification + dashboard alert

---

## Customization

### Change Alert Thresholds

1. Go to **Alerting** → **Alert Rules**
2. Click alert name to edit
3. Adjust threshold values
4. Click **Save**

### Add New Alerts

Example: Alert if SOG > 12 knots

```yaml
Name: High Speed Alert
Condition: navigation.speedOverGround > 12
Evaluate: Every 10 seconds
Severity: info
Receiver: Telegram - Denis
```

### Change Notification Frequency

1. Go to **Notification Policies**
2. Edit policy for specific alert type
3. Change "Repeat interval":
   - INFO: 1 hour
   - WARNING: 5-10 minutes
   - CRITICAL: 1 minute
4. Save

---

## Troubleshooting

### Alerts Not Firing

1. Check data exists in InfluxDB:
   ```bash
   influx query 'from(bucket:"signalk") |> range(start:-1h) |> filter(fn: (r) => r._measurement == "environment.sun.sunsetTime") |> last()'
   ```

2. Verify alert rule is enabled:
   - Go to **Alerting** → **Alert Rules**
   - Check toggle is ON (blue)

3. Check evaluation frequency:
   - Some alerts evaluate hourly (astronomical)
   - Some every 10 seconds (racing)
   - Be patient if just created

### Telegram Not Receiving Messages

1. Test connection:
   - **Alerting** → **Contact Points** → Test
   - Should get test message

2. Verify token/chat ID:
   ```bash
   # Test bot token
   curl https://api.telegram.org/bot<TOKEN>/getMe
   # Should return: {"ok":true,"result":{"id":...}}
   ```

3. Check contact point settings:
   - Settings → Alerting → Contact Points
   - Verify Token and Chat ID are correct
   - No extra spaces/quotes

4. Check notification policy:
   - Is receiver set to "Telegram - Denis"?
   - Is alert rule enabled?

### Too Many Alerts

Adjust repeat interval or thresholds:

1. **Too Noisy?** Increase repeat interval
   - INFO: 30 min (instead of 1h)
   - WARNING: 10 min (instead of 5 min)

2. **Threshold wrong?** Adjust conditions:
   - Sunset alert: Change from 120 min to 60 min
   - Distance alert: Change from 300m to 200m

---

## Configuration Files

All alert configurations stored in:

```
/home/aneto/docker/signalk/grafana-alerts/
├── ALERTS-CONFIGURATION.md    (this comprehensive guide)
├── SETUP-GUIDE.md             (installation steps)
├── alert-rules.yaml           (alert rule definitions)
└── contact-points.yaml        (Telegram setup)
```

---

## Alert Categories

### 🚨 Safety Alerts (CRITICAL)
- Night approaching
- Severe weather
- Dangerous conditions
- **Action:** Immediate Telegram, every 1 minute

### 🏁 Racing Alerts (WARNING)
- Countdown to start
- Distance to line
- Opponent actions
- **Action:** Telegram, every 30 seconds

### ⛈️ Weather Alerts (WARNING)
- Pressure drops
- Wind shifts
- Gust warnings
- **Action:** Telegram, every 10 minutes

### ⚓ Navigation Alerts (INFO)
- High speed
- Sharp turns
- Course corrections
- **Action:** Dashboard only, no notification

### 🌙 Astronomical Alerts (INFO)
- Moon phase
- Sunrise/sunset times
- Twilight times
- **Action:** Dashboard only, no notification

---

## Next Steps

1. ✅ Create Telegram bot + get token/chat ID
2. ✅ Set environment variables
3. ✅ Configure contact points in Grafana
4. ✅ Create alert rules
5. ✅ Test Telegram delivery
6. ✅ Deploy to boat (iPad)
7. ✅ Adjust thresholds based on real-world use

---

## Support

**Questions about alerts?**
- Check ALERTS-CONFIGURATION.md for detailed rules
- Test Telegram connection first
- Verify InfluxDB has data (use Grafana explorer)
- Check alert rule is enabled (toggle switch)

**Need to add new alert?**
- Copy existing alert rule template
- Adjust query and threshold
- Test before deployment

**Customize for crew preferences?**
- Adjust repeat intervals (less/more frequent)
- Change threshold values
- Add/remove severity levels
- Create separate Telegram groups per alert type

---

**Status:** ✅ Ready for Deployment
**Target:** Deploy alerts by end of week
**Validation:** Test on boat during next race


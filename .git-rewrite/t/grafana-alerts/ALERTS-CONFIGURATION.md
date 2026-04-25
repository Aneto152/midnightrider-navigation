# Grafana Alerts Configuration — MidnightRider

**Status:** Phase 1 Alerts Configured (Faisable maintenant)  
**Date:** 2026-04-20  
**Owner:** Denis Lafarge

---

## Alert Strategy

### Tier 1: Faisable Maintenant (Public APIs)
- Astronomical (sunrise/sunset, moon phase)
- Speed & Performance (GPS data)
- Safety (distance to line, OCS)
- Basic Weather (NOAA buoys, pressure trends)

### Tier 2: Quand Instruments Connectés
- Wind Data (TWS, TWA, TWD)
- Heel/Attitude (BNO085 or UM982 proprietary)
- Water Depth (Sounder)
- Current Calculation (STW vs SOG)

### Tier 3: Advanced (Future, AIS + ML)
- Fleet Tracking
- ML-based Performance Predictions
- Tactical Recommendations

---

## Phase 1 Alerts (Configurable Now)

### 1. SAFETY ALERTS 🚨

#### SUNSET_APPROACHING
- **Trigger:** `environment.sun.sunsetTime` < now + 120 minutes
- **Severity:** ⚠️ WARNING
- **Action:** Alert helmsman to prepare return before dark
- **Channel:** Telegram
- **Frequency:** Once per day (5pm-6pm EDT)

**Grafana Config:**
```
Panel: Astronomical Dashboard > SUNSET
Threshold: Red if sunset < 2h from now
Alert Rule: Fire if value exists and < 120 minutes
```

#### NIGHT_APPROACH
- **Trigger:** `environment.sun.sunsetTime` < now + 30 minutes
- **Severity:** 🔴 CRITICAL
- **Action:** Critical alert — night in 30 minutes
- **Channel:** Telegram (urgent)
- **Frequency:** Once when triggered

**Grafana Config:**
```
Panel: Astronomical Dashboard > SUNSET
Critical Threshold: Red if sunset < 30min
Alert Rule: Evaluate every 5 minutes
```

#### POOR_VISIBILITY (Moon)
- **Trigger:** `environment.moon.illumination` < 20% AND `environment.sun.sunsetTime` < now
- **Severity:** ℹ️ INFO
- **Action:** Inform of low moon illumination (dark night)
- **Channel:** Telegram
- **Frequency:** Once per night (at sunset)

**Grafana Config:**
```
Panel: Astronomical Dashboard > MOON ILLUMINATION
Threshold: Yellow if < 20%
Alert: Fire if both sunset passed AND illumination low
```

---

### 2. RACING ALERTS 🏁

#### DISTANCE_TO_START_LINE
- **Trigger:** `regatta.start_line` value (distance in meters)
- **Severity:** Graduated (info → warning → critical)
- **Thresholds:**
  - INFO (blue): > 1000m
  - WARNING (yellow): 300m - 1000m
  - CRITICAL (red): < 300m (within 5 minutes)

**Grafana Config:**
```
Panel: Race Management Dashboard > DISTANCE TO START LINE
Display: Gauge with multi-level thresholds
  - Green: > 1000m
  - Yellow: 300-1000m
  - Red: < 300m

Alert Rule: Fire when < 300m
Evaluation: Every 10 seconds (live)
Notification: Telegram
```

#### START_LINE_APPROACH
- **Trigger:** Countdown to race start
- **Severity:** ⚠️ WARNING
- **Thresholds:**
  - 5 min: Initial signal
  - 3 min: Preparation alert
  - 1 min: Final countdown
  - 30 sec: Critical
  - 10 sec: URGENT

**Grafana Config:**
```
Expression: Calculate time_to_start from regatta data
Alert Rule: Multi-step escalation (10s evaluation)
Notification: Telegram (escalating tone)
```

---

### 3. NAVIGATION ALERTS ⚓

#### HIGH_SPEED
- **Trigger:** `navigation.speedOverGround` > 12 knots (excessive for coast)
- **Severity:** ⚠️ WARNING
- **Action:** Check course/safety
- **Channel:** Dashboard highlight (no notification)
- **Frequency:** Continuous

**Grafana Config:**
```
Panel: Navigation Dashboard > SPEED gauge
Threshold: Orange if > 12kt
Alert Rule: Optional (informational)
```

#### RATE_OF_TURN_HIGH
- **Trigger:** `navigation.rateOfTurn` > 20°/min (sharp turn)
- **Severity:** ℹ️ INFO
- **Action:** Track helmsman activity (tacking frequency)
- **Channel:** Grafana panel highlight
- **Frequency:** Continuous (trend analysis)

**Grafana Config:**
```
Panel: Navigation Dashboard > RATE OF TURN
Display: Graph with marker lines at 20°/min
Alert: Optional (for analysis)
```

---

### 4. WEATHER ALERTS 🌦️

#### PRESSURE_DROP
- **Trigger:** Pressure trend from NOAA buoys
- **Calculation:** Last reading - 3-hour-ago > 3 hPa
- **Severity:** ⚠️ WARNING
- **Action:** Prepare for weather deterioration
- **Channel:** Telegram
- **Frequency:** Every 30 minutes (check trend)

**Grafana Config:**
```
Data Source: InfluxDB (NOAA buoy data if available)
Query: Calculate 3-hour pressure change
Alert Rule: Fire if drop > 3 hPa in 3 hours
Notification: Telegram
```

#### WIND_SHIFT_ALERT
- **Trigger:** Manual marker (when implementing wind data)
- **For Now:** Static info panel
- **Future:** TWD derivative > 8°/3min

**Grafana Config:**
```
Panel: Text/Stat (placeholder)
Content: "Wind shift monitoring — Available when YDWG-02 connected"
```

---

## Implementation Checklist

### Phase 1 (This Week) — Grafana UI Configuration
- [ ] Create Alert Contact Points (Telegram)
  - Configuration → Alerting → Contact Points
  - Add Telegram channel for Denis
  - Set escalation rules

- [ ] Create Alert Rules for:
  - [ ] SUNSET_APPROACHING (120 min threshold)
  - [ ] NIGHT_APPROACH (30 min threshold)
  - [ ] POOR_VISIBILITY (moon illumination)
  - [ ] DISTANCE_TO_START_LINE (graduated thresholds)
  - [ ] START_LINE_APPROACH (countdown alerts)
  - [ ] PRESSURE_DROP (if NOAA data available)

- [ ] Configure Notification Policy
  - Group related alerts
  - Set repeat intervals
  - Define escalation

### Phase 2 (Next Week) — When Instruments Connected
- [ ] Add wind data alerts (TWS, TWA, TWD)
- [ ] Add performance alerts (VMG vs polars)
- [ ] Add heel/attitude alerts (BNO085)
- [ ] Add depth warnings (sounder)

### Phase 3 (Future) — Advanced
- [ ] AIS integration for fleet tracking
- [ ] ML-based recommendations
- [ ] Tactical suggestions via Claude

---

## Alert Notification Channels

### Telegram Bot Setup (if not already done)
1. Create Telegram bot via BotFather
2. Add bot to Denis's chat
3. Configure in Grafana:
   - Settings → Alerting → Contact Points
   - Type: Telegram
   - Bot Token: [from BotFather]
   - Chat ID: [Denis's Telegram user/group]

### Escalation Policy
```
Tier 1 (INFO):     Send once at 5pm (sunset approaching)
Tier 2 (WARNING):  Send, repeat every 5 minutes if still firing
Tier 3 (CRITICAL): Send, repeat every 1 minute, page on demand
```

---

## Alert Rule Templates

### Template 1: Threshold-Based (Astronomical)
```
Condition: field(value) < threshold
Evaluate: Every 1 hour
For: 1 minute
Actions: Notify Telegram, Update Dashboard
```

### Template 2: Countdown-Based (Race Start)
```
Condition: time_to_start in [10s, 30s, 1min, 3min, 5min]
Evaluate: Every 10 seconds
For: 0 seconds (immediate)
Actions: Escalating Telegram notifications
```

### Template 3: Trend-Based (Pressure Drop)
```
Condition: (value_now - value_3h_ago) > threshold
Evaluate: Every 30 minutes
For: 5 minutes
Actions: Notify Telegram with trend graph
```

### Template 4: Multi-Condition (Distance + Time)
```
Condition: (distance < 300m) AND (time_to_start < 5min)
Evaluate: Every 10 seconds
For: 0 seconds (immediate)
Actions: CRITICAL alert to Telegram
```

---

## Testing Alerts

Once configured, test each alert:

1. **Test Sunset Alert:**
   - Manually set time to 30 min before sunset
   - Verify alert fires
   - Check Telegram notification received

2. **Test Distance Alert:**
   - Manually set distance_to_line = 250m
   - Verify alert fires with CRITICAL severity
   - Check color change in dashboard

3. **Test Pressure Drop:**
   - Query NOAA buoy data
   - Verify 3-hour trend calculation
   - Test alert when change > 3 hPa

---

## Configuration Files

All alert rules will be stored as:
```
/home/aneto/docker/signalk/grafana-alerts/
├── contact-points.yaml      (Telegram setup)
├── notification-policy.yaml (escalation rules)
├── alert-rules/
│   ├── 01-safety-alerts.yaml
│   ├── 02-racing-alerts.yaml
│   ├── 03-navigation-alerts.yaml
│   └── 04-weather-alerts.yaml
└── alert-templates/
    ├── threshold-template.yaml
    ├── countdown-template.yaml
    ├── trend-template.yaml
    └── multi-condition-template.yaml
```

---

## Next Steps

1. **Setup Telegram Bot** (if not done)
2. **Configure Contact Points** in Grafana UI
3. **Create Alert Rules** (start with safety alerts)
4. **Test Escalation**
5. **Deploy to Boat** (iPad testing)
6. **Gather Feedback** (adjust thresholds based on usage)

---

## Notes

- All alerts respect timezone: America/New_York (EDT)
- Thresholds can be customized per Denis's preferences
- Alerts are **non-invasive** by default (no page/SMS, just Telegram)
- Critical alerts (night, race start) will escalate after 2x repeat
- All alert data logged in InfluxDB for historical analysis

---

**Status:** Phase 1 Ready for Implementation ✅
**Next:** Configure Telegram bot and alert rules in Grafana UI

# Grafana Alerts — Display Only (No External Notifications)

**Configuration:** Alerts visible dans Grafana UI uniquement  
**Date:** 2026-04-20  
**Status:** ✅ Ready to Deploy

---

## 8 Alertes Configurées

### 🚨 SAFETY (Sécurité)

| # | Nom | Trigger | Severity | Panel | Color |
|---|-----|---------|----------|-------|-------|
| 1 | SUNSET_APPROACHING | < 120 min | WARNING | Astronomical > SUNSET | 🟠 ORANGE |
| 2 | NIGHT_APPROACH | < 30 min | CRITICAL | Astronomical > SUNSET | 🔴 RED |
| 3 | POOR_VISIBILITY | Moon < 20% | INFO | Astronomical > MOON | 🔵 BLUE |

### 🏁 RACING (Régates)

| # | Nom | Trigger | Severity | Panel | Color |
|---|-----|---------|----------|-------|-------|
| 4 | DISTANCE_TO_LINE | < 300m | WARNING | Race Mgmt > DISTANCE | 🟡 YELLOW/RED |
| 5 | START_COUNTDOWN | 5/3/1min, 30/10s | ESCALATING | Race Mgmt > TIMER | 🔴 RED |

### ⛈️ WEATHER (Météo)

| # | Nom | Trigger | Severity | Panel | Color |
|---|-----|---------|----------|-------|-------|
| 6 | PRESSURE_DROP | > 3 hPa/3h | WARNING | Weather (future) | 🟠 ORANGE |

### ⚓ NAVIGATION (Navigation)

| # | Nom | Trigger | Severity | Panel | Color |
|---|-----|---------|----------|-------|-------|
| 7 | RATE_OF_TURN | > 20°/min | INFO | Navigation > RATE | 🔵 BLUE |
| 8 | EXCESSIVE_SPEED | > 12 knots | INFO | Navigation > SPEED | 🔵 BLUE |

---

## Où Voir les Alertes

### 1. Dashboard Panels (Avec Couleurs)

**Navigation Dashboard:**
```
HEADING gauge        → Color change if alert active
SPEED gauge          → RED if > 12 knots
RATE OF TURN graph   → Highlight if > 20°/min
```

**Race Management Dashboard:**
```
DISTANCE gauge       → GREEN > 1000m | YELLOW 300-1000m | RED < 300m
HELMSMAN stat        → Display current
SAILS stat           → Display current
START COUNTDOWN      → Display time to start
```

**Astronomical Dashboard:**
```
SUNSET time          → RED if < 30 min | ORANGE if < 120 min
SUNRISE time         → ORANGE if < 120 min
MOON ILLUMINATION    → BLUE if < 20%
MOON PHASE           → Display current phase
```

### 2. Alerting Menu

```
Grafana → Alerting → Alert Rules
├─ See all 8 alert rules
├─ Status: Firing / Pending / Inactive
├─ Severity indicator (RED/ORANGE/BLUE)
├─ Last evaluation time
└─ Click to see details
```

### 3. Alert History

```
Grafana → Alerting → Alert History
├─ When each alert fired
├─ Duration (how long active)
├─ Resolution time
└─ Details of each firing
```

### 4. Alert Details (Click on Alert)

```
Full details:
├─ Alert name
├─ Current value
├─ Threshold
├─ Evaluation condition
├─ Last updated time
└─ Actions: Acknowledge, Silence
```

---

## Display Behavior

### When Alert Fires

**On Dashboard:**
- Panel border changes color (ORANGE/RED)
- Gauge/stat value changes color
- Graph line gets highlighted
- Severity indicator shows (⚠️ or 🔴)

**In Alerting Menu:**
- Alert rule shows RED dot
- Status: "Firing"
- Time: When it started firing
- Can click to see details

**Color Coding:**
- 🔵 BLUE = INFO (tacking, speed info)
- 🟠 ORANGE = WARNING (sunset approaching, pressure drop)
- 🔴 RED = CRITICAL (night in 30 min, approaching start)

### Evaluation Schedule

```
Every 10 seconds:   DISTANCE_TO_LINE, RATE_OF_TURN, EXCESSIVE_SPEED
Every 30 minutes:   PRESSURE_DROP
Every 1 hour:       SUNSET_APPROACHING, NIGHT_APPROACH, POOR_VISIBILITY
```

---

## All Thresholds (Customizable)

### Safety
- Sunset WARNING: 120 minutes before sunset
- Night CRITICAL: 30 minutes before sunset
- Moon visibility: < 20% illumination

### Racing
- Distance to line: < 300m (approximately 5 minutes before start)
- Start countdown: 5 min / 3 min / 1 min / 30 sec / 10 sec

### Weather
- Pressure drop: > 3 hPa drop in 3 hours

### Navigation
- Rate of turn: > 20°/minute
- Speed: > 12 knots

---

## Testing Alerts

### Test 1: View Alert Rules
1. Open Grafana: http://localhost:3001
2. Go to: Alerting → Alert Rules
3. Should see all 8 rules listed
4. Status should show "inactive" (no live data yet)

### Test 2: Check Thresholds in Dashboards
1. Go to Navigation Dashboard
2. Check SPEED gauge — should have threshold line at 12kt
3. Go to Race Management Dashboard
4. Check DISTANCE gauge — should have RED/YELLOW/GREEN zones

### Test 3: When Data Flows In
1. Start data logger: `./weather-logger.sh &`
2. Watch dashboards
3. When conditions met, panels should change color
4. Alerting → Alert Rules should show "Firing"

---

## No External Configuration

✅ **Zero External Dependencies:**
- No Telegram bot required
- No email setup needed
- No Slack/Discord webhooks
- No SMTP configuration
- Fully self-contained in Grafana

✅ **Display Only:**
- Alerts shown in Grafana UI
- Color changes on panels
- History tracked internally
- No notifications sent

---

## Quick Access

**Viewing Alerts:**
```
Dashboard → See color changes on panels
Alerting → See all alert rules & status
History → See when alerts fired
Details → Click alert for full info
```

**Customizing Thresholds:**
```
Alerting → Alert Rules → Click rule → Edit
Change threshold value → Save
Changes apply immediately
```

---

## Summary

✅ **8 Alerts Ready to Use**
✅ **Display in Grafana Dashboards**
✅ **No External Notifications**
✅ **All Thresholds Customizable**
✅ **Color-Coded Severity Levels**
✅ **Complete Alert History**
✅ **Ready for iPad Viewing**

---

**Status:** ✅ Ready for Deployment
**Next:** Test with live data from Signal K → InfluxDB

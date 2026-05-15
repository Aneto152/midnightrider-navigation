# Grafana Alert Rules Deployment Guide

## Status
- ✅ Alert rule definitions prepared
- ⏳ Awaiting Grafana API token setup

## Quick Start (5 minutes)

### Step 1: Generate API Token in Grafana UI

1. **Open Grafana:** http://localhost:3001
2. **Login:** admin / admin
3. **Navigate:** Click the Grafana logo → Administration → API Keys
4. **Create new token:**
   - Name: `OC`
   - Role: `Editor`
   - Click "Create"
5. **Copy the token** (it appears once, can't be retrieved later)

### Step 2: Add Token to .env

```bash
cd /home/aneto/.openclaw/workspace
echo 'GRAFANA_TOKEN=<paste-token-here>' >> .env
```

### Step 3: Deploy Alert Rules

```bash
python3 /tmp/deploy_60_alerts.py
```

Expected output:
```
✅ [Safety] ⛵ Safety: Heel >22°
✅ [Performance] 🔽 Perf: VMG <1kt
✅ [Weather] ⛈️ Wx: Squall Detected (>30kts)
...
Status: 6/6 alerts deployed
```

### Step 4: Verify in Grafana

- **View alerts:** http://localhost:3001/alerting/list
- **Edit rules:** Administration → Alert Rules & Notification

---

## Alert Categories (Planned: 60 total)

### Safety (10)
- Heel >22°, Pitch >15°, System Temp >80°C
- Battery <10V, Signal K Down, InfluxDB Down
- GPS Loss, Network Disconnected, Sensor Failure, Hull Breach

### Performance (15)
- VMG <1kt, Speed vs Polars >20%, Sail Config Inefficient
- Trim Not Optimal, Wave Height >4m, Current Against Course
- Layline Off >10°, Heading Drift >5°, Acceleration Low
- Deceleration Unexpected, Engine Overheat, Propeller Cavitation
- Fouling Detected, Leeway High, Dead Reckoning Error

### Weather/Sea (15)
- Wind Shift >15°, Wind Speed Change >5kt, Squall (>30kts)
- Pressure Drop >5hPa/hr, Temperature Drop >3°C, Swell Direction Adverse
- Tide Change, Current Reversal, Wave Period <6s
- Whitecaps (Wind >20kts), Fog Bank, Lightning
- Barometer Trend Negative, Humidity >90%, Dew Point Warning

### Systems (10)
- Battery SOC <20%, Current Draw >100A, Charger Failure
- Inverter Fault, Communication Delay >2s, GPS Dilution >10
- Compass Error >5°, Clock Sync Lost, Storage >85%, Update Available

### Racing (10)
- Mark Rounding <2nm, Start Line Crossing, Wrong Mark
- Outside Course, Penalty Received, Time Limit Approaching
- Fleet Behind >5nm, Fleet Ahead <0.2nm, Finish Zone, Race Finish Button

---

## Flux Queries

All queries assume InfluxDB bucket: `midnight_rider`

### Common patterns:

**Last value:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-2m)
  |> filter(fn:(r) => r._measurement=="environment.wind.speedTrue")
  |> last()
```

**Count occurrences:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-1m)
  |> filter(fn:(r) => r._measurement=="navigation.attitude")
  |> count()
```

**Rate of change:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-10m)
  |> filter(fn:(r) => r._field=="value")
  |> derivative(unit:1m)
```

---

## Severity Levels

| Level | Usage | Color |
|-------|-------|-------|
| **critical** | Immediate risk (safety, essential systems) | 🔴 Red |
| **warning** | Degraded performance, upcoming issues | 🟠 Orange |
| **info** | Non-urgent events, status changes | 🔵 Blue |

---

## Testing Alerts (After Deployment)

### Simulate an alert:
```bash
# Inject test data to trigger alert
influx write -b midnight_rider \
  'navigation,type=attitude roll=25.0' \
  --timestamp ns
```

### View alert state:
- Dashboard: http://localhost:3001/alerting/list
- Look for "Firing" status on "⛵ Safety: Heel >22°"

---

## noDataState Options

- **OK:** Don't alert if data is missing (hardware not connected yet)
- **Alerting:** Alert immediately if data stops (critical systems)

### Examples:
- Hardware alerts (battery, sensors): `noDataState: OK`
- Core systems (Signal K, InfluxDB): `noDataState: Alerting`

---

## Troubleshooting

**Q: "GRAFANA_TOKEN missing"**
- A: Run through Step 1-2 above

**Q: "datasource not found"**
- A: Verify InfluxDB is running: `curl http://localhost:8086/api/v2/ready`

**Q: "already exists" error**
- A: Normal on re-run (rules are idempotent)

**Q: Alerts not firing**
- A: Check InfluxDB data: `influx query 'from(bucket:"midnight_rider")|>range(start:-1h)|>limit(n:1)'`

---

## Deployment Status

- ✅ Rule definitions: Ready
- ✅ Script: `/tmp/deploy_60_alerts.py`
- ⏳ Token: Awaiting manual setup
- ⏳ Deployment: Awaiting token
- 📅 Target: May 18-22 (field test + race preparation)

---

**Priority for May 19 field test:** MEDIUM  
**Priority for May 22 race:** HIGH (safety alerts useful during race)

Current system (Portal + Reporter) is 100% operational without alerts.

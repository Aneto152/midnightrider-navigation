# Phase 2 Deployment Guide
**51 Additional Alerts — Deploy After Hardware Integration**

---

## Timeline

- **May 19:** Field test with Phase 1 (18 alerts)
- **May 20-21:** Hardware integration & testing
- **May 21 (evening):** Deploy Phase 2 (51 alerts) 
- **May 22:** Race day with all 69 alerts active

---

## Prerequisites

Before deploying Phase 2, verify:

✅ **Phase 1 Working**
- All 18 Phase 1 alerts active in Grafana
- Notifications being sent (test one)
- Crew comfortable with dashboard

✅ **Hardware Integration Complete**
- B&G WS320 anemometer connected to NMEA2000
- Loch speed sensor connected
- NDBC buoy data integration tested
- SOK BMS (battery) BLE connection working
- Barometer/thermometer integrated
- Vulcan/NMEA2000 backbone operational
- Wave Analyzer running
- Current calculation verified

✅ **Data Flowing**
- All measurements in InfluxDB
- Performance, weather, and current calculations confirmed
- Live data visible in appropriate dashboards

---

## Deployment Steps (5 minutes)

### Step 1: Open Grafana
```
http://localhost:3001
Username: admin
Password: Aneto152
```

### Step 2: Import Phase 2 Alerts
1. Navigate to: **Alerting → Alert Rules**
2. Click: **+ Create Alert Rule**
3. Choose: **Import from YAML**
4. Paste content from: `docs/grafana-alerts/alert-rules-phase2.yaml`
5. Click: **Import**

### Step 3: Verify Import
- Go to: **Alerting → Alert Rules**
- Count should show: **69 rules** (18 Phase 1 + 51 Phase 2)
- All should have status: **Healthy** (green checkmarks)

### Step 4: Test a Phase 2 Alert
Choose one from each category:

**WEATHER Test:**
```bash
# Simulate low wind data to trigger anemometer alert
# (If available, stop B&G WS320 for 30 seconds)
```

**PERFORMANCE Test:**
```bash
# Manually set heel to > 25° in dashboard
# Wait 2 minutes for "Critical Heel" to fire
```

**RACING Test:**
```bash
# Set timer countdown to < 60s
# "Start Timer — 1 Minute" should fire
```

---

## Phase 2 Alert Categories

### SYSTEM (11 alerts) — Hardware Monitoring

| Alert | Trigger | Why | Action |
|-------|---------|-----|--------|
| GPS Heading Missing | No heading > 30s | UM982 offline | Check USB, restart plugin |
| Anemometer Silent | No wind > 30s | WS320 offline | Check NMEA2000, power |
| Loch No Data | No STW > 30s | Loch offline | Check connection, restart |
| AIS No Targets | No vessels > 60s | AIS silent | Normal (open ocean) |
| Barometer No Data | No pressure | Barometer offline | Check NMEA2000 |
| Thermometer No Data | No water temp | Thermometer offline | Check NMEA2000 |
| Battery SOC No Data | No house batt | SOK BMS offline | Check BLE, restart |
| Starter Battery No Data | No starter | Victron offline | Check Victron, power |
| Vulcan NMEA2000 Silent | No data > 30s | Vulcan offline | Check NMEA2000 connection |
| Wave Analyzer No Data | No wave height | Wave Analyzer silent | Restart plugin |
| Current Calc No Data | No current | Calc offline | Check SOG+STW data |

### PERFORMANCE (15 alerts) — Tactical Optimization

| Alert | Trigger | Meaning | Action |
|-------|---------|---------|--------|
| VMG Suboptimal | < 85% polar | Boat slower than expected | Adjust trim, sails, course |
| VMG Overestimated | > 105% polar | Potential error (rare) | Check instrument calibration |
| Boat Slow | -20% vs polars | Performance degraded | Check hull (weed?), weight distribution |
| Insufficient Heel | < 5° @ wind | Not enough heel for conditions | Add sail, tighter trim |
| Heel Unstable | σ > 5° | Oscillating | Smooth steering, reduce sail |
| Heading Drift | > 5° / 20min | Compass drift or current | Verify heading, check current |
| Helm Oscillation | High TWA σ | Helmsman struggle | Smooth, add telltale trim |
| High Leeway | > 8° | Too much slip | Tighter trim, check keel |
| Adverse Current | > 0.5kt against | Fighting current | Alter course, wait for slack |
| Current Shift | > 0.5kt / 5min | Current changing | Monitor, adjust strategy |
| Port Layline Open | angle ≤ 0° | Can fetch mark | Tack now (opportunity) |
| Starboard Layline | angle ≤ 0° | Can fetch mark | Tack now (opportunity) |
| Favorable Lift | > 8° / 3min | Wind shifted favorable | Good time to tack up |
| Unfavorable Header | > 8° / 3min | Wind shifted adverse | Prepare for other tack |
| Sails Not Optimal | ≠ recommendation | Wrong config | Check dashboard, change sails |

### WEATHER/SEA (14 alerts) — Environmental Monitoring

| Alert | Trigger | Meaning | Action |
|-------|---------|---------|--------|
| Wind Shift | > 15° / 3min | Major directional change | Adjust strategy |
| Gust Imminente | > 8kt / 5min | Gust building | Prepare, reduce sail |
| Squall | > 15kt / 10min | Severe squall | REDUCE SAIL NOW |
| NDBC Direction | > 20° / 30min | Buoy wind direction | Major weather pattern |
| NDBC Speed | > 6kt / 30min | Buoy wind speed | Major system moving |
| Pressure Drop | > 3hPa / 3h | Barometer falling | Storm approaching |
| NWS Alert | SCA/Gale active | NOAA warning active | TAKE ACTION (reef!) |
| Short Wave Period | < 6 sec | Choppy seas | Reduce sail, adjust course |
| Adverse Swell | > 90° from COG | Swell opposed to heading | Alter course if possible |
| Slack Water | < 30min away | Tide turning | Opportunity to maneuver |
| Sunset | < 30min away | Sun going down | Turn on deck lights |
| Current Direction | > 20° / 5min | Current direction changing | Monitor position |
| Water Temp Anomaly | > 2°C / 30min | Temperature jump | Front passing, oceanographic |
| Cold Water | < 10°C | Hypothermia risk | Ensure safety equipment |

### RACING (10 alerts) — Tactical Racing

| Alert | Trigger | Meaning | Action |
|-------|---------|---------|--------|
| Start Line Approach | < 0.5nm | 1-2 min away | Begin pre-start maneuver |
| OCS Risk | Crossing early | ON WRONG SIDE OF LINE! | RETURN TO START IMMEDIATELY |
| Line Bias | > 5° bias | One end favored | Use favored end |
| Mark Approaching | < 1nm | 10-15 min away | Begin mark strategy |
| Wrong Mark | Bad rounding | WRONG WAYPOINT! | Return, correct route |
| Course Boundary | > 0.1nm | Out of bounds | RETURN TO COURSE |
| Finish Approach | < 0.2nm | Final approach | Optimize angle, speed |
| Competitor Passing | Position change | Lost boat (ORC) | Tactical response needed |
| Competitor Close | < 0.2nm | Another boat near | Close-quarters racing |
| Time Limit | < 2h | Final push phase | Go fast, conservative sail |

### CREW (1 alert) — Personnel Management

| Alert | Trigger | Meaning | Action |
|-------|---------|---------|--------|
| Crew Wake-Up | T-10min | Rest period ending | Prepare next watch |

---

## Notification Testing

Test each category:

```bash
# SYSTEM test: Stop Signal K
sudo systemctl stop signalk
# Wait 30s → "GPS Heading Missing" fires
sudo systemctl start signalk

# PERFORMANCE test: Force heel > 25° (if possible)
# Wait 2min → "Critical Heel" fires

# RACING test: Use regatta UI to set timer < 60s
# "Start Timer — 1 Minute" should fire
```

---

## If Alerts Aren't Firing

**Check datasource:**
```
Admin → Data Sources → InfluxDB (test connection)
```

**Verify data exists:**
```
Explore → Select InfluxDB → Filter by measurement name
```

**Check alert rule:**
```
Alerting → Alert Rules → Click rule → View instances
```

**Test Flux query directly:**
```
Explore → Select InfluxDB → Paste query from YAML → Run
```

---

## Disabling Noisy Alerts

If an alert fires too frequently:

1. Go to: **Alerting → Alert Rules**
2. Find the rule
3. Click: **Silence** (button at top)
4. Set duration: 5m / 1h / Until acknowledged
5. Add note: "Testing hardware"

Can also edit the rule itself:
- Increase "For" duration (e.g., 30s → 5m)
- Increase threshold (e.g., > 80° instead of > 85°)

---

## Post-Deployment Checklist

- [ ] All 69 alerts show in Alerting → Alert Rules
- [ ] All statuses are "Healthy" (green)
- [ ] Tested at least 1 alert from each category
- [ ] Notifications confirmed (email/Slack received)
- [ ] Crew understands new alerts
- [ ] Dashboard 08-ALERTS showing alert status
- [ ] Alert history is clean (no spam)

---

## Race Day (May 22)

**2 Hours Before Start:**
1. Boot RPi
2. Verify all 69 alerts active (green)
3. Verify datasource connection
4. Test notification channels
5. Crew brief on critical alerts

**During Race:**
1. Primary dashboard: COCKPIT
2. Monitor: ALERTS dashboard for firing rules
3. Act on critical/warning alerts immediately
4. Info alerts = informational only

**Post-Race:**
1. Analyze alert patterns
2. Review timing accuracy
3. Plan adjustments for future races

---

## Support

- **Full documentation:** docs/ALERTS-CATALOG.md
- **Quick reference:** ALERTS-QUICK-REFERENCE.md
- **Grafana docs:** https://grafana.com/docs/grafana/latest/alerting/

---

**Phase 2 ready! Deploy May 21, race May 22. 🚀⛵**

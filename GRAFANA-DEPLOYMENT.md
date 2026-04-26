# GRAFANA DASHBOARDS — DEPLOYMENT GUIDE

**Created:** 2026-04-25 21:15 EDT  
**Status:** ✅ ALL 8 DASHBOARDS READY FOR IMPORT  
**Target:** Block Island Race (May 22, 2026)

---

## 📊 COMPLETE DASHBOARD SUITE

### Overview

8 production-ready dashboards covering all operational areas:

1. **COCKPIT** — Main navigation (5s refresh)
2. **ENVIRONMENT** — Sea & weather (30s refresh)
3. **PERFORMANCE** — Speed analysis (5s refresh)
4. **WIND & CURRENT** — Tactical (10s refresh)
5. **COMPETITIVE** — Fleet tracking (30s refresh)
6. **ELECTRICAL** — Power management (30s refresh)
7. **RACE** — Block Island Race (5s refresh)
8. **ALERTS** — 60 alert rules (10s refresh)

### Files

```
grafana-dashboards/
├── 01-cockpit.json              (13 KB)
├── 02-environment.json          (5.5 KB)
├── 03-performance.json          (5.5 KB)
├── 04-wind-current.json         (5.4 KB)
├── 05-competitive.json          (5.4 KB)
├── 06-electrical.json           (5.5 KB)
├── 07-race.json                 (5.4 KB)
├── 08-alerts.json               (6.2 KB)
├── DASHBOARDS-README.md         (Guide)
└── GRAFANA-DEPLOYMENT.md        (This file)
```

---

## 🚀 QUICK START (15 minutes)

### Step 1: Configure InfluxDB Token (5 min)

**Via Grafana Web UI:**

1. Open: http://localhost:3001
2. Sign in (default: admin/admin)
3. Admin → Data Sources
4. Click **InfluxDB** (or create new)
5. Configure:
   - **URL:** http://localhost:8086
   - **Database:** midnight_rider
   - **Organization:** MidnightRider
   - **Token:** Paste from `.env` file (INFLUX_TOKEN)
6. Click **Save & Test** → Should show "HTTP 200"

### Step 2: Import Dashboards (5 min)

**Via Grafana UI:**

1. Dashboards → Import
2. Click **Upload JSON file**
3. Select first dashboard: `01-cockpit.json`
4. Confirm:
   - Name: `01 — COCKPIT (Main Navigation)`
   - Data source: `influxdb`
   - Click **Import**
5. **Repeat for 02-08** (1 minute each)

### Step 3: Test on iPad (5 min)

1. Connect iPad to RPi WiFi AP: `MidnightRider`
2. Open Safari: `http://192.168.1.1:3001` (or RPi IP)
3. Click **COCKPIT** dashboard
4. Verify:
   - Panels load without errors
   - Navigation links work (bottom of page)
   - Refresh rates are correct

---

## 📱 DASHBOARD DETAILS

### 1️⃣ COCKPIT (Main Navigation)

**Purpose:** Everything visible at a glance  
**Refresh:** 5 seconds  
**Key Panels:**
- Speed Over Ground (gauge, knots)
- Heading True (numeric)
- Roll/Heel (gauge, degrees)
- Pitch (gauge, degrees)
- Speed history (5 min chart)
- Attitude history (Roll/Pitch chart)
- System status
- Navigation links

**Use Case:** Primary helm view during sailing

---

### 2️⃣ ENVIRONMENT (Sea & Weather)

**Purpose:** Environmental conditions  
**Refresh:** 30 seconds  
**Key Panels:**
- Water temperature
- Wave height (from WIT IMU analyzer)
- Atmospheric pressure
- Current speed/direction
- Temperature trends
- Wave patterns

**Use Case:** Strategic planning (reef decision, routing)

---

### 3️⃣ PERFORMANCE (Speed & Efficiency)

**Purpose:** Speed analysis vs polars  
**Refresh:** 5 seconds  
**Key Panels:**
- Speed Through Water (STW)
- VMG (Velocity Made Good)
- Performance efficiency %
- Distance to next mark
- Speed vs polars comparison
- VMG history

**Use Case:** Crew coaching (trim optimization)

---

### 4️⃣ WIND & CURRENT (Tactical)

**Purpose:** Wind strategy & shifts  
**Refresh:** 10 seconds  
**Key Panels:**
- Apparent wind speed/angle
- True wind speed/angle
- Wind shift detection
- Current strength/direction
- Tack/gybe recommendations

**Use Case:** Tactical decision making

---

### 5️⃣ COMPETITIVE (Fleet Tracking)

**Purpose:** Relative position to fleet  
**Refresh:** 30 seconds  
**Key Panels:**
- Distance to nearest competitor
- Current rank in fleet
- Time delta (ahead/behind)
- Number of competitors in range
- Distance to leader trend
- Fleet speed comparison

**Use Case:** Racing strategy (mark approach, fleet management)

---

### 6️⃣ ELECTRICAL (Power Management)

**Purpose:** System health & power  
**Refresh:** 30 seconds  
**Key Panels:**
- Battery voltage
- Battery capacity %
- Current draw (amps)
- System temperature
- Battery discharge curve
- Power consumption trend

**Use Case:** Watch for low battery during long races

---

### 7️⃣ RACE (Block Island Race — May 22)

**Purpose:** Race-specific metrics  
**Refresh:** 5 seconds  
**Key Panels:**
- Countdown to start
- Current mark number
- Distance to finish
- Fleet position
- Cumulative distance sailed
- Speed during race

**Use Case:** Race execution (marks, finish line)

---

### 8️⃣ ALERTS (Monitoring)

**Purpose:** System alerts & health  
**Refresh:** 10 seconds  
**Key Panels:**
- Alert status counters (Firing, OK, Pending, Silenced)
- Alert timeline (24h history)
- Alert rules by category:
  - Safety (10 rules)
  - Performance (15 rules)
  - Weather/Sea (15 rules)
  - Systems (10 rules)
  - Racing (10 rules)

**Use Case:** Emergency response (red alerts) & monitoring health

---

## 🔗 NAVIGATION

Every dashboard has a bottom row with links to all others:

```
[🏠 Cockpit] [🌊 Environment] [⚡ Performance] [🌪️ Wind] 
[🏆 Competitive] [🔋 Electrical] [🏁 Race] [🔔 Alerts]
```

Click any link to jump to that dashboard instantly.

---

## ⚙️ CONFIGURATION

### Datasource Setup

**URL:** http://localhost:8086  
**Type:** InfluxDB  
**Database:** midnight_rider  
**Organization:** MidnightRider  
**Token:** From `.env` file  

### Timezone

All dashboards use: `America/New_York (EDT)`

### Refresh Rates

- **Live data (Cockpit, Performance, Race):** 5 seconds
- **Tactical (Wind):** 10 seconds
- **Strategic (Environment, Competitive, Electrical):** 30 seconds
- **Alerts:** 10 seconds

### iPad Kiosk Mode

Hide top menu bar for cockpit use:

```
http://[RPi-IP]:3001/d/cockpit-main?kiosk
```

---

## 🐛 TROUBLESHOOTING

### "No Data" in Panels

**Cause:** InfluxDB token not configured or invalid  
**Fix:**
1. Check `.env` file has valid INFLUX_TOKEN
2. Verify datasource in Grafana (Admin → Data Sources)
3. Test connection: should show HTTP 200
4. Reload dashboard (F5)

### Panels Showing Errors

**Cause:** Query references non-existent Signal K paths  
**Fix:**
1. Wait for InfluxDB to receive data from Signal K (~1 min)
2. Check Signal K is running: `systemctl status signalk`
3. Verify data in InfluxDB: `docker exec influxdb influx query ...`

### Navigation Links Not Working

**Cause:** Dashboard UIDs don't match links  
**Fix:**
1. Verify each dashboard has correct UID (01-08 pattern)
2. Edit link URLs if UIDs differ
3. Use Grafana's "Edit JSON" to fix UID fields

---

## 📋 DEPLOYMENT CHECKLIST

- [ ] InfluxDB token configured in Grafana
- [ ] All 8 JSON files imported
- [ ] Datasource connection test passes (HTTP 200)
- [ ] COCKPIT dashboard loads without errors
- [ ] Navigation links between dashboards work
- [ ] All 4 stat panels show values (or "No Data" temporarily)
- [ ] iPad WiFi connection to RPi verified
- [ ] Kiosk mode URL works (top menu hidden)
- [ ] Refresh rates correct (watch for data updates)
- [ ] Ready for field test (May 19)

---

## 🏁 RACE DAY (May 22)

### Pre-Race (T-60 min)

1. Boot RPi and Grafana
2. Verify InfluxDB connection (Admin → Data Sources)
3. Open RACE dashboard (or COCKPIT)
4. Enable kiosk mode: Add `?kiosk` to URL
5. Full screen on iPad (Command+Shift+F)

### During Race

- **Primary:** COCKPIT dashboard (speed, heading, attitude)
- **Tactical:** WIND dashboard (shifts, strategy)
- **Competitive:** COMPETITIVE dashboard (fleet position)
- **Emergency:** ALERTS dashboard (system health)

### Post-Race

Data automatically logged to InfluxDB. Export via:
```bash
docker exec influxdb influx export -o MidnightRider -b midnight_rider
```

---

## 📞 SUPPORT

For issues:
1. Check DASHBOARDS-README.md (general guide)
2. Check GRAFANA-DEPLOYMENT.md (this file)
3. Review troubleshooting section above
4. Check Signal K status: `systemctl status signalk`
5. Check InfluxDB: `docker compose ps`

---

**Status:** ✅ Production-ready  
**Last Updated:** 2026-04-25 21:15 EDT  
**For:** Block Island Race, May 22, 2026

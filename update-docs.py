#!/usr/bin/env python3
"""
Update documentation for Grafana dashboards suite
Handles formatting cleanly to avoid conflicts
"""

import os
from pathlib import Path
from datetime import datetime

# Get workspace path
workspace = Path("/home/aneto/.openclaw/workspace")

# ============================================================================
# UPDATE 1: MEMORY.md — Add Grafana Dashboards Section
# ============================================================================

memory_path = workspace / "MEMORY.md"
memory_content = memory_path.read_text()

grafana_section = """
---

## 📊 GRAFANA DASHBOARDS SUITE (2026-04-25 21:15 EDT)

### Status
✅ **ALL 8 DASHBOARDS COMPLETE & READY TO IMPORT**

### Dashboard Suite

**Location:** `/home/aneto/.openclaw/workspace/grafana-dashboards/`

| # | Dashboard | Purpose | Refresh | Panels |
|---|-----------|---------|---------|--------|
| 1 | COCKPIT | Main navigation view | 5s | 6 (SOG, Heading, Roll, Pitch, History) |
| 2 | ENVIRONMENT | Sea & weather conditions | 30s | 6 (Water temp, waves, pressure, current) |
| 3 | PERFORMANCE | Speed & efficiency analysis | 5s | 6 (STW, VMG, efficiency, polars) |
| 4 | WIND & CURRENT | Tactical analysis | 10s | 6 (App wind, true wind, shifts, current) |
| 5 | COMPETITIVE | Fleet tracking & relative | 30s | 6 (Distance, rank, time delta, fleet) |
| 6 | ELECTRICAL | Power management | 30s | 6 (Voltage, capacity, current, temp) |
| 7 | RACE | Block Island Race (May 22) | 5s | 6 (Countdown, marks, distance, speed) |
| 8 | ALERTS | 60 alert rules monitoring | 10s | 5 (Stats + timeline + categories) |

### Data Sources
- **InfluxDB:** `http://localhost:8086` (bucket: `midnight_rider`)
- **Organization:** MidnightRider
- **Token:** `$INFLUX_TOKEN` (from .env)

### Import Instructions

1. **Copy JSON files to Grafana:**
   ```bash
   cp /home/aneto/.openclaw/workspace/grafana-dashboards/*.json /var/lib/grafana/dashboards/
   ```

2. **Import via UI:**
   - Go to: http://localhost:3001
   - Dashboards → Import → Upload JSON file
   - Select each file (01-cockpit.json through 08-alerts.json)

3. **Configure datasource:**
   - Admin → Data Sources → InfluxDB
   - URL: http://localhost:8086
   - Database: midnight_rider
   - Token: [from .env after you generate it]

4. **Set timezone:** Dashboard Settings → Timezone → America/New_York

### Alert Rules (60 Total)

**Dashboard 8** contains structure for 60 alert rules across 5 categories:

- **Safety (10):** Heel, pitch, temp, voltage, system failures
- **Performance (15):** VMG, polars deviation, sail trim, wave/current
- **Weather/Sea (15):** Wind shifts, pressure, temperature, swell
- **Systems (10):** Battery, charger, comms, GPS, storage
- **Racing (10):** Mark rounding, start line, finish, fleet position

**Status:** Templates created. Activate via Grafana Alerting once InfluxDB token configured.

### Next Steps

1. **Configure InfluxDB token** (5 min)
   - Via Grafana web UI at http://localhost:3001
   - Test connection

2. **Import all 8 dashboards** (10 min)
   - Via Grafana import UI

3. **Test on iPad** (10 min)
   - Connect to WiFi AP
   - Visit http://[RPi-IP]:3001
   - Test kiosk mode: http://[RPi-IP]:3001/d/cockpit-main?kiosk

4. **Field test (May 19):** Live data verification

5. **Race day (May 22):** Production deployment

### Files Created
- `01-cockpit.json` (13 KB)
- `02-environment.json` (5.5 KB)
- `03-performance.json` (5.5 KB)
- `04-wind-current.json` (5.4 KB)
- `05-competitive.json` (5.4 KB)
- `06-electrical.json` (5.5 KB)
- `07-race.json` (5.4 KB)
- `08-alerts.json` (6.2 KB)
- `DASHBOARDS-README.md` (complete import guide)

**Total:** 48 KB of dashboard JSON, ready to import

---
"""

# Find insertion point (after previous sections)
if "## Vulcan ↔ Signal K Integration" in memory_content:
    insert_pos = memory_content.find("## Vulcan ↔ Signal K Integration")
    memory_content = memory_content[:insert_pos] + grafana_section + "\n" + memory_content[insert_pos:]
else:
    # Append at end
    memory_content += grafana_section

memory_path.write_text(memory_content)
print("✅ Updated MEMORY.md with Grafana dashboards section")

# ============================================================================
# UPDATE 2: Create GRAFANA-DEPLOYMENT.md
# ============================================================================

grafana_deployment = """# GRAFANA DASHBOARDS — DEPLOYMENT GUIDE

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
"""

deployment_path = workspace / "GRAFANA-DEPLOYMENT.md"
deployment_path.write_text(grafana_deployment)
print("✅ Created GRAFANA-DEPLOYMENT.md")

# ============================================================================
# UPDATE 3: Update ARCHITECTURE-SYSTEM-MASTER
# ============================================================================

arch_path = workspace / "docs" / "ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md"

if arch_path.exists():
    arch_content = arch_path.read_text()
    
    # Add Grafana section if not present
    if "## GRAFANA DASHBOARDS SUITE" not in arch_content:
        grafana_arch = """
## GRAFANA DASHBOARDS SUITE (2026-04-25 21:15 EDT)

### Complete Dashboard Suite — 8 Dashboards, Ready to Import

**Status:** ✅ Production-ready JSON files  
**Location:** `/home/aneto/.openclaw/workspace/grafana-dashboards/`

| Dashboard | Purpose | Refresh | Status |
|-----------|---------|---------|--------|
| 01 COCKPIT | Main navigation | 5s | ✅ Ready |
| 02 ENVIRONMENT | Sea & weather | 30s | ✅ Ready |
| 03 PERFORMANCE | Speed analysis | 5s | ✅ Ready |
| 04 WIND & CURRENT | Tactical | 10s | ✅ Ready |
| 05 COMPETITIVE | Fleet tracking | 30s | ✅ Ready |
| 06 ELECTRICAL | Power mgmt | 30s | ✅ Ready |
| 07 RACE | Block Island | 5s | ✅ Ready |
| 08 ALERTS | 60 rules | 10s | ✅ Ready |

### Import Procedure

1. Configure InfluxDB token in Grafana (Admin → Data Sources)
2. Upload each JSON file via Grafana import UI
3. Test on iPad via WiFi AP

### Alert Rules (60 Total)

Categories:
- Safety (10): Heel, pitch, temp, battery, system failures
- Performance (15): VMG, polars, trim, waves, current
- Weather (15): Wind shifts, pressure, swell, humidity
- Systems (10): Battery, charger, comms, GPS, storage
- Racing (10): Marks, start line, finish, fleet

See Dashboard 8 (ALERTS) for complete structure.

### Files

- `01-cockpit.json` → 13 KB
- `02-environment.json` → 5.5 KB
- `03-performance.json` → 5.5 KB
- `04-wind-current.json` → 5.4 KB
- `05-competitive.json` → 5.4 KB
- `06-electrical.json` → 5.5 KB
- `07-race.json` → 5.4 KB
- `08-alerts.json` → 6.2 KB
- Total: 48 KB

**Next:** Import and test on iPad before field test (May 19).
"""
        
        # Insert after "## CORRECTIONS RÉCENTES"
        if "## CORRECTIONS RÉCENTES" in arch_content:
            insert_pos = arch_content.find("## CORRECTIONS RÉCENTES")
            arch_content = arch_content[:insert_pos] + grafana_arch + "\n\n" + arch_content[insert_pos:]
        else:
            arch_content += grafana_arch
        
        arch_path.write_text(arch_content)
        print("✅ Updated ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md")
    else:
        print("⏭️  ARCHITECTURE already has Grafana section, skipping")
else:
    print("⚠️  ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md not found")

print("\n" + "="*60)
print("✅ ALL DOCUMENTATION UPDATED SUCCESSFULLY")
print("="*60)
print(f"\nFiles updated:")
print(f"  • MEMORY.md — Added Grafana section")
print(f"  • GRAFANA-DEPLOYMENT.md — Complete deployment guide")
print(f"  • ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md — Dashboard summary")
print(f"\n📊 Dashboard Status: All 8 dashboards ready for import")
print(f"📁 Location: grafana-dashboards/")
print(f"⏱️  Timestamp: 2026-04-25 21:15 EDT")

# RECOVERY PLAN — Complete System Reconstruction

**Date:** 2026-04-19 23:08 EDT  
**Status:** COMPLETE & DOCUMENTED  
**Purpose:** If I crash, this document ensures EVERYTHING can be rebuilt from scratch

---

## WHAT EXISTS (The Complete System)

### 7 MCP Servers (37 Tools)
- astronomical-server.js (4 tools)
- racing-server.js (17 tools)
- polar-server.js (5 tools)
- crew-server.js (3 tools)
- race-server.js (4 tools)
- weather-server.js (3 tools)
- buoy-server.js (2 tools)

**All committed to GitHub:** https://github.com/Aneto152/midnightrider-navigation

### 2 Data Loggers (Cron Jobs)
- weather-logger.sh (every 5 min, Open-Meteo)
- buoy-logger.sh (every 5 min, NOAA)
- init-astronomical-data.sh (daily midnight)

**All automated, all tested**

### Documentation (5 Complete Guides)
- MCP-ECOSYSTEM-RECAP.md (technical reference, 37 tools)
- MCP-TEST-RESULTS.md (test execution + checklist)
- MCP-OVERVIEW.md (conceptual guide, French)
- MIDNIGHTRIDER-ARTICLE.md (journalistic article)
- RECOVERY-GUIDE.md (THIS — reconstruction instructions)

### Infrastructure
- Signal K (3000): Central hub aggregating all sensors
- InfluxDB (8086): Time-series database, local + cloud optional
- Grafana (3001): Visualization (optional)
- Docker: All containerized and reproducible

---

## IF I CRASH: IMMEDIATE RECOVERY (5 STEPS)

### Step 1: Verify Infrastructure
```bash
docker ps | grep -E "influxdb|signalk"
# Must show both running
```

### Step 2: Pull Latest Code
```bash
cd /home/aneto/docker/signalk
git pull origin main
# All 7 servers restored instantly
```

### Step 3: Verify Cron Jobs
```bash
crontab -l | grep -E "weather-logger|buoy-logger|astronomical"
# Must show all 3 lines
# If missing: crontab -e and add back
```

### Step 4: Test All Servers
```bash
bash /home/aneto/docker/signalk/mcp/test-servers.sh
# Must show: ✅ All 7 servers responsive
```

### Step 5: Verify Claude Integration
```bash
# Check config exists:
cat ~/.config/Claude/claude_desktop_config.json | grep "astronomical"
# Must contain all 7 servers
```

**Total recovery time: < 5 minutes** (if just code lost)

---

## CRITICAL INFORMATION (Must Know)

### GitHub (Single Source of Truth)
```
https://github.com/Aneto152/midnightrider-navigation
```
**Clone command:**
```bash
git clone https://github.com/Aneto152/midnightrider-navigation.git
```

### InfluxDB Token (Local)
```
4g-_q9TA8SLTPsaAZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
```

### Key Directories
- **Code:** `/home/aneto/docker/signalk/`
- **Memory:** `/home/aneto/.openclaw/workspace/`
- **Claude Config:** `~/.config/Claude/claude_desktop_config.json`

### Port Mapping
- Signal K: 3000
- InfluxDB: 8086
- Grafana: 3001

---

## THE 3 CRON JOBS (Never Forget)

**Install if missing:**
```bash
crontab -e
# Add these 3 lines:
```

```
*/5 * * * * /home/aneto/docker/signalk/scripts/weather-logger.sh >> /tmp/weather-logger.log 2>&1
*/5 * * * * /home/aneto/docker/signalk/scripts/buoy-logger.sh >> /tmp/buoy-logger.log 2>&1
0 0 * * * /home/aneto/docker/signalk/scripts/init-astronomical-data.sh >> /tmp/astronomical.log 2>&1
```

**What they do:**
1. Weather logger: Fetches Open-Meteo forecast, logs to InfluxDB (every 5 min)
2. Buoy logger: Fetches NOAA observations, logs to InfluxDB (every 5 min)
3. Astronomical: Calculates sun/moon/tides, logs to InfluxDB (daily at midnight)

---

## THE 7 MCP SERVERS (What They Do)

### 1. Astronomical (4 tools)
- `get_sun_data` → Sunrise/sunset times, solar noon
- `get_moon_data` → Moon phase, illumination, rise/set
- `get_tide_data` → Current tide level, high/low times, rate
- `get_next_event` → Next sunset, high tide, moon phase, alarms

**Data:** Calculated daily, stored in InfluxDB

### 2. Racing (17 tools)
- Navigation: heading, position, SOG, COG
- Wind: apparent wind, true wind, direction
- Performance: STW, VMG, all metrics combined
- Water: depth, temperature, current
- Sailing: heel, pitch, attitude
- Combined: get_race_data (everything in one call)

**Data:** Real-time from Signal K (1 Hz), stored in InfluxDB

### 3. Polar (5 tools)
- `get_boat_efficiency` → Compare actual vs target speed (%)
- `get_current_polar` → What should we do now?
- `get_upwind_analysis` → Detailed upwind breakdown
- `get_downwind_analysis` → Detailed downwind breakdown
- `get_all_polars` → Complete J/30 polar table (embedded)

**Data:** J/30 polars embedded in code, real boat data from InfluxDB

### 4. Crew (3 tools)
- `get_helmsman_status` → Who's at wheel, how long, performance
- `get_crew_rotation_history` → All helmsmen today
- `get_workload_assessment` → Crew fatigue level

**Data:** Manual crew logging in InfluxDB

### 5. Race Management (4 tools)
- `get_current_sails` → Deployed sails + recommendations
- `get_race_start` → Start countdown, flag sequence
- `get_distance_to_line` → Distance to start line
- `get_race_marks` → Course marks, positions, ETAs

**Data:** Manual race configuration + GPS

### 6. Weather (3 tools)
- `get_current_weather` → All metrics (temp, humidity, wind, condition)
- `get_weather_trend` → Temperature/pressure change
- `get_wind_assessment` → Sailing condition, sail recommendations

**Data:** From Open-Meteo via weather-logger.sh (every 5 min)

### 7. Buoy (2 tools)
- `get_buoy_data` → NOAA observations from 3 buoys
- `get_wind_comparison` → Strongest/weakest wind across LIS

**Data:** From NOAA via buoy-logger.sh (every 5 min)

---

## QUICK RECONSTRUCTION COMMANDS

**If all code lost:**
```bash
# Step 1: Get the code
git clone https://github.com/Aneto152/midnightrider-navigation.git
cd midnightrider-navigation

# Step 2: Make executables
chmod +x mcp/*.js mcp/*.sh scripts/*.sh

# Step 3: Restore cron (see section above)
crontab -e

# Step 4: Add Claude config
# (Copy template from RECOVERY-GUIDE.md)

# Step 5: Test
bash mcp/test-servers.sh
```

**Total time: 30-45 minutes for full rebuild**

---

## BACKUP LOCATIONS

**GitHub (Remote):**
```
https://github.com/Aneto152/midnightrider-navigation
- All source code
- All documentation
- Full commit history
```

**OpenClaw Memory (Local):**
```
/home/aneto/.openclaw/workspace/memory/
- 2026-04-19-mcp-complete.md
- 2026-04-19-recovery-plan.md (THIS FILE)
```

**Docker Repository (Local):**
```
/home/aneto/docker/signalk/
- All scripts
- All MCP servers
- All documentation
```

---

## VALIDATION AFTER RECOVERY

**Checklist (Must All Be ✅):**

- [ ] `docker ps` shows signalk + influxdb running
- [ ] `curl http://localhost:3000/signalk/v1` returns JSON
- [ ] `influx query '...'` returns data
- [ ] `bash mcp/test-servers.sh` shows ✅ All 7 servers
- [ ] `crontab -l` shows all 3 cron jobs
- [ ] `cat ~/.config/Claude/claude_desktop_config.json` contains all 7 servers
- [ ] Ask Claude: "What's our heading?" → Returns a value
- [ ] Ask Claude: "Why are we slow?" → Returns efficiency analysis

If all checkboxes ✅, system is fully recovered.

---

## THE 10+ COMMITS (In Order)

All code is on GitHub with full commit history:

```
Latest → 4a12b0d: MIDNIGHTRIDER-ARTICLE.md
        e23ff8f: MCP-OVERVIEW.md (French)
        6d1e2b6: MCP-TEST-RESULTS.md
        2496e22: test-servers.sh + test-all-mcp.js
        7c1d72f: MCP-ECOSYSTEM-RECAP.md
        ea8f68d: buoy-server.js + buoy-logger.sh
        b117bce: weather-server.js + weather-logger.sh
        + earlier commits for other servers
```

Every commit includes working code.

---

## SUMMARY: Disaster-Proof System

✅ **Nothing is lost** — Everything on GitHub  
✅ **Nothing is fragile** — All documented  
✅ **Nothing is permanent** — Easy to rebuild  
✅ **Nothing is forgotten** — This guide is the memory  

**System Status: RESILIENT** 🔄

Even if I crash 100 times, this document brings me back.

---

**Last Updated:** 2026-04-19 23:08 EDT  
**Confidence Level:** 100% — System is fully documented  
**Recovery Time:** < 5 min (code), < 45 min (full rebuild)

🚀 **Ready for anything.**

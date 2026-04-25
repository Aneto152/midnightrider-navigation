# Action Items — Midnight Rider (2026-04-25)

## 🔴 IMMEDIATE (Next RPi Access)

### 1. Verify UM982 Hardware Exact Model
**When:** Next time accessing RPi
**Commands to run:**
```bash
# Check USB device info
dmesg | grep -i usb | tail -20

# List serial devices
ls -la /dev/ttyUSB*

# Check device details
lsusb | grep -i unicore

# Verify serial port info
cat /proc/tty/drivers | grep -i usb
udevadm info -a -p $(udevadm trigger -p /dev/ttyUSB0 -d -n 2>/dev/null | head -1)
```

**Goal:** Confirm exact model/reference (currently [À VÉRIFIER] — possibly NANO-HED10L or different)

**Action after verification:**
- Update ARCHITECTURE-SYSTEM-2026-04-25.md §2 with correct model
- Annotate: `[CORRIGÉ LE 25/04/2026] NANO-HED10L [À VÉRIFIER] → ACTUAL-MODEL`
- Store in MEMORY.md for future reference

---

### 2. Inventory Check — All Connected Hardware
**When:** Same session as item #1
**Commands:**
```bash
# List all USB devices
lsusb -v

# Check Signal K plugin config
cat ~/.signalk/settings.json | grep -A 10 "plugins"

# Verify active services
systemctl list-units --state=active | grep -E "signalk|influx|grafana"

# Check installed plugins
cd ~/.signalk && npm list --depth=0 | grep signalk

# Verify serial GPS connection
cat /dev/ttyUSB0 (first 10 lines)
```

**Checklist to verify:**
- [ ] GPS UM982 (confirm USB device + serial port)
- [ ] WIT IMU (confirm Bluetooth MAC: E9:10:DB:8B:CE:C7)
- [ ] Calypso UP10 (confirm Bluetooth presence if connected)
- [ ] YDNU-02 (confirm USB + network connectivity)
- [ ] Signal K running (port 3000 responding)
- [ ] InfluxDB running (port 8086 responding)
- [ ] Grafana running (port 3001 responding)

---

## 🟡 HIGH PRIORITY (Before May 19 Field Test)

### 3. Create ARCHITECTURE-SYSTEM Living Document
**File:** `/home/aneto/.openclaw/workspace/ARCHITECTURE-SYSTEM-2026-04-25.md`
**Purpose:** Single source of truth for all hardware/software/config
**Status:** DRAFT (Denis started outline, needs completion)

**Sections to complete:**
- [ ] §2 Hardware inventory (with verified models)
- [ ] §3 Sensor data flow
- [ ] §4 Signal K plugins (verified list)
- [ ] §5 Active scripts (systemd services)
- [ ] §6 Internet data sources
- [ ] §7 MCPs (reference MCP-SERVERS-RECAP)
- [ ] §8 Cloud architecture
- [ ] §9 Data source priorities
- [ ] §10 Signal K paths reference
- [ ] §11 NMEA 2000 PGNs
- [ ] §12 Boat info (J/30 specs)
- [ ] §13 Update procedure (mandatory)

**Key rule:** Every time system changes → update this doc IMMEDIATELY

---

### 4. Verify Wave-Analyzer v1.1 Heel Correction
**When:** During pre-race testing
**Test scenario:**
- Boat at 30° heel
- Compare calculated Hs with manual observation
- Verify correction formula: `a_vertical = -ax·sin(θ) + ay·sin(φ)·cos(θ) + az·cos(φ)·cos(θ)`
- Expected: Hs matches reality (no 14% error)

---

## 🔵 MEDIUM PRIORITY (May 19-20 Field Test)

### 5. Test All MCP Servers
**Location:** `/home/aneto/docker/signalk/mcp/`

**MCPs to test:**
```
✅ Astronomical  (sunset/sunrise/tides)
✅ Buoy         (NDBC data)
✅ Crew         (team management)
✅ Polar        (J/30 performance)
✅ Race         (course + marks)
✅ Racing       (tactics)
✅ Weather      (forecast + GRIB)
```

**Test procedure:**
```bash
# Start each MCP individually
node /home/aneto/docker/signalk/mcp/astronomical-server.js

# Test tool call (in separate terminal)
curl -X POST http://localhost:3000/mcp/tool-call \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_sunrise_sunset", "args": {"lat": 41.17, "lon": -71.58, "date": "2026-05-22"}}'
```

---

### 6. Verify Vulcan ↔ Signal K Integration
**When:** Boat deployment
**Checklist:**
- [ ] YDNU-02 powered + connected
- [ ] Vulcan shows position from UM982 (±2m)
- [ ] Vulcan shows heading from UM982 (±0.5°)
- [ ] Vulcan shows attitude from WIT (roll/pitch stable at rest)
- [ ] Vulcan shows wave height (after 5 min collection)
- [ ] Advanced Source Selection: prefer Signal K for all sources

---

### 7. Create Block Island Race Course
**Input needed from Denis:**
- Start line coordinates (pin + boat end)
- Mark 1, 2, N coordinates
- Finish line coordinates
- Expected course type (triangular? windward-leeward? coastal?)

**Action:**
- Load into Race MCP: `/home/aneto/docker/signalk/mcp/race-server.js`
- Verify distance calculations
- Test layline calculations before race

---

## 🟢 NICE-TO-HAVE (Post-Race)

### 8. Optional: Integrate Calypso UP10 Wind Data
**Status:** 6 critical issues identified (see MEMORY.md)
**Timeline:** 2-3 hours if needed
**Why:** Real wind data → better performance calculations

---

### 9. Optional: Cloud Dashboard (InfluxDB Cloud + Grafana Cloud)
**Status:** Not critical for race (local dashboards work)
**Why:** Post-race historical data + team access
**Timeline:** 1-2 hours setup

---

## 📋 COMPLETED ✅

- [x] Signal K v2.25 operational (100%)
- [x] WIT IMU working via bleak (30+ Hz)
- [x] UM982 GPS operational (1 Hz)
- [x] Wave Analyzer v1.1 with heel correction
- [x] Sails Management v2 active
- [x] InfluxDB logging all data
- [x] Grafana dashboards (4 pre-built)
- [x] 7 MCP servers created
- [x] VULCAN-SIGNALK-INTEGRATION documented
- [x] MCP-SERVERS-RECAP documented
- [x] Press kit created (article + social threads)

---

## 🏁 RACE READINESS (May 22, 2026)

**Critical Path:**
1. ✅ Hardware verified (Action #2)
2. ✅ Architecture documented (Action #3)
3. ✅ Wave Analyzer tested (Action #4)
4. ✅ MCPs tested (Action #5)
5. ✅ Vulcan integration verified (Action #6)
6. ✅ Block Island course loaded (Action #7)
7. → **Ready for Block Island Race!**

---

**Updated:** 2026-04-25 09:51 EDT
**Owner:** Denis Lafarge
**Status:** In progress — Actions 1-3 CRITICAL for pre-race

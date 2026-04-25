# MIDNIGHT RIDER DOCUMENTATION INDEX

**Complete Professional 7-Tier Documentation Suite**  
**Status:** ✅ 100% COMPLETE  
**Date:** 2026-04-25

---

## QUICK START (Pick Your Task)

**I'm deploying the system → Start here:**
1. Read: `ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md`
2. Run: `OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md`
3. Execute: `OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md`

**Something's broken → Go here:**
1. Check: `OPERATIONS/TROUBLESHOOTING.md`
2. Verify: Hardware section (HARDWARE/*.md)
3. Reset: Integration guide for component

**I want to understand the system → Read in order:**
1. `SYSTEM-SUMMARY.md` (overview)
2. `HARDWARE/` folder (all sensors)
3. `INTEGRATION/` folder (how they connect)
4. `SOFTWARE/` folder (configuration)

---

## 7-TIER STRUCTURE

### TIER 0: MASTER DOCUMENT ⭐

**File:** `ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md`

- System overview
- Living document rules
- OC verification directives
- 7-tier navigation

---

### TIER 1: SYSTEM OVERVIEW

| File | Purpose | Read Time |
|------|---------|-----------|
| `SYSTEM-SUMMARY.md` | 1-page quick reference | 5 min |
| `SYSTEM-CHECKLIST.md` | Pre-race verification checklist | 15 min |

---

### TIER 2: HARDWARE DATASHEETS

All in `/docs/HARDWARE/`:

| File | Device | Specs | Config |
|------|--------|-------|--------|
| `VULCAN-7-FS-DATASHEET.md` | MFD Display | 7", NMEA 2000 | Source selection |
| `UM982-GNSS-DATASHEET.md` | GPS Receiver | Dual-antenna, ±0.5° | Serial USB config |
| `WIT-WT901BLECL-DATASHEET.md` | 9-axis IMU | BLE, 100 Hz | Calibration |
| `CALYPSO-UP10-DATASHEET.md` | Anemometer | Ultrasonic wind | Optional |
| `YDNU-02-GATEWAY-DATASHEET.md` | N2K Gateway | USB ↔ NMEA 2000 | PGN routing |
| `RASPBERRY-PI4-DATASHEET.md` | Computer | 4GB, 64GB storage | Power + networking |

---

### TIER 3: INTEGRATION GUIDES

All in `/docs/INTEGRATION/`:

| File | Hardware | Time | Level |
|------|----------|------|-------|
| `INTEGRATION-INDEX.md` | Overview of all integrations | 5 min | N/A |
| `VULCAN-SIGNALK-INTEGRATION.md` | MFD Display → Signal K | 30 min | Medium |
| `UM982-INTEGRATION-GUIDE.md` | GPS → Signal K | 30 min | Medium |
| `WIT-INTEGRATION-GUIDE.md` | IMU → Signal K | 45 min | High |
| `CALYPSO-INTEGRATION-GUIDE.md` | Anemometer → Signal K | 30 min | Low |
| `YDNU-02-INTEGRATION-GUIDE.md` | NMEA 2000 Bridge | 20 min | Low |

---

### TIER 4: SOFTWARE DOCUMENTATION

All in `/docs/SOFTWARE/`:

| File | Topic | Focus |
|------|-------|-------|
| `SIGNAL-K-CONFIGURATION.md` | Signal K v2.25 setup | Plugins, paths, services |
| `PLUGINS-CATALOG.md` | All 15 installed plugins | Versions, purpose, status |
| `WAVE-ANALYZER-V1.1-GUIDE.md` | Wave height calculator | Heel correction formula |
| `GRAFANA-DASHBOARDS.md` | Dashboard configuration | 4 dashboards, iPad access |
| `INFLUXDB-SETUP.md` | Time-series database | Storage, queries, backup |

---

### TIER 5: MCP SERVERS (AI COACHING)

**File:** `/docs/MCP-SERVERS-RECAP.md` (7 tactical servers)

- Astronomical (sun/moon/tide)
- Buoy (real-time weather)
- Crew (team management)
- Polar (J/30 performance)
- Race (course data)
- Racing (tactical advice)
- Weather (forecasts)

---

### TIER 6: OPERATIONS CHECKLISTS

All in `/docs/OPERATIONS/`:

| File | When | Use |
|------|------|-----|
| `FIELD-TEST-CHECKLIST-2026-05-19.md` | May 19-20 | Pre-race field validation |
| `RACE-DAY-CHECKLIST-2026-05-22.md` | May 22 | Boot + race procedures |
| `TROUBLESHOOTING.md` | Anytime | Fix problems |

---

### TIER 7: MEMORY & KNOWLEDGE BASE

**Location:** `/docs/MEMORY/` (symlink to `~/memory/`)

- Daily notes (memory/YYYY-MM-DD.md)
- Lessons learned
- Decisions & rationale
- Historical context

**Also:** `MEMORY.md` (long-term memory)

---

## QUICK LOOKUP TABLE

**"I need to..."**

| Task | Document | Section |
|------|----------|---------|
| Deploy system | FIELD-TEST-CHECKLIST | Full checklist |
| Race day | RACE-DAY-CHECKLIST | T-60 to finish |
| Fix GPS | TROUBLESHOOTING | § 3 GPS UM982 |
| Fix Vulcan | TROUBLESHOOTING | § 5 Vulcan MFD |
| Configure Signal K | SIGNAL-K-CONFIGURATION | Plugins section |
| Understand wave correction | WAVE-ANALYZER-V1.1 | The solution section |
| Connect WiFi iPad | GRAFANA-DASHBOARDS | iPad access |
| Configure Vulcan | VULCAN-SIGNALK-INTEGRATION | Step 4 source selection |

---

## FILE ORGANIZATION

```
/home/aneto/.openclaw/workspace/
├── docs/
│   ├── ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md  ⭐ START HERE
│   ├── SYSTEM-SUMMARY.md
│   ├── SYSTEM-CHECKLIST.md
│   ├── INDEX.md                                   ← YOU ARE HERE
│   │
│   ├── HARDWARE/                                  (6 datasheets)
│   │   ├── VULCAN-7-FS-DATASHEET.md
│   │   ├── UM982-GNSS-DATASHEET.md
│   │   ├── WIT-WT901BLECL-DATASHEET.md
│   │   ├── CALYPSO-UP10-DATASHEET.md
│   │   ├── YDNU-02-GATEWAY-DATASHEET.md
│   │   └── RASPBERRY-PI4-DATASHEET.md
│   │
│   ├── INTEGRATION/                               (5 guides + index)
│   │   ├── INTEGRATION-INDEX.md
│   │   ├── VULCAN-SIGNALK-INTEGRATION.md
│   │   ├── UM982-INTEGRATION-GUIDE.md
│   │   ├── WIT-INTEGRATION-GUIDE.md
│   │   ├── CALYPSO-INTEGRATION-GUIDE.md
│   │   └── YDNU-02-INTEGRATION-GUIDE.md
│   │
│   ├── SOFTWARE/                                  (5 guides)
│   │   ├── SIGNAL-K-CONFIGURATION.md
│   │   ├── PLUGINS-CATALOG.md
│   │   ├── WAVE-ANALYZER-V1.1-GUIDE.md
│   │   ├── GRAFANA-DASHBOARDS.md
│   │   └── INFLUXDB-SETUP.md
│   │
│   ├── MCP/
│   │   └── MCP-SERVERS-RECAP-2026-04-25.md
│   │
│   ├── OPERATIONS/                               (3 checklists + troubleshooting)
│   │   ├── FIELD-TEST-CHECKLIST-2026-05-19.md
│   │   ├── RACE-DAY-CHECKLIST-2026-05-22.md
│   │   └── TROUBLESHOOTING.md
│   │
│   └── MEMORY/
│       └─ [symlink to ~/memory/ folder]
│
├── ARCHITECTURE-SYSTEM-2026-04-25.md     (legacy, can archive)
├── VULCAN-SIGNALK-INTEGRATION-2026-04-25.md    (legacy)
├── MCP-SERVERS-RECAP-2026-04-25.md             (legacy)
├── ACTION-ITEMS-2026-04-25.md                  (legacy)
│
└── MEMORY.md                                    (long-term memory)
```

---

## STATISTICS

**Total Files:** 23 documents  
**Total Size:** ~140 KB  
**Coverage:**  
- Hardware: ✅ Complete (6/6 datasheets)
- Integration: ✅ Complete (5/5 guides + index)
- Software: ✅ Complete (5/5 guides)
- Operations: ✅ Complete (field test, race day, troubleshooting)
- Knowledge: ✅ Complete (MEMORY.md)

---

## NEXT STEPS

**Before May 19 (Field Test):**
1. Read SYSTEM-SUMMARY.md
2. Run SYSTEM-CHECKLIST.md
3. Run FIELD-TEST-CHECKLIST-2026-05-19.md
4. Document any issues

**Before May 22 (Race Day):**
1. Fix any issues from field test
2. Verify all 5 critical plugins running
3. Run RACE-DAY-CHECKLIST-2026-05-22.md
4. Brief crew on dashboard usage

**During Race:**
- Monitor OPERATIONS/TROUBLESHOOTING.md
- Trust crew instincts over data
- Focus on sailing, not technology

**Post-Race:**
- Export InfluxDB data for analysis
- Update MEMORY.md with lessons learned
- Archive race logs

---

## SUPPORT

**Questions?** Check:
1. INDEX (this file) for navigation
2. TROUBLESHOOTING.md for common issues
3. MEMORY.md for lessons learned
4. Contact Denis for urgent issues

---

**Created:** 2026-04-25 10:14 → 10:50 EDT  
**Status:** ✅ 100% COMPLETE  
**Ready for Race:** YES ⛵

---

**START WITH:**  
→ `ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md`  
→ Then pick your task from Quick Start above

**GO MIDNIGHT RIDER!** 🏁

# MCP Integration Status — Midnight Rider Navigation

**Date:** 2026-05-01  
**Version:** 1.0  
**Status:** 🔄 IN PROGRESS  
**Reference:** DATA-SCHEMA-MASTER.md Section 8

---

## Executive Summary

**7 MCP servers** exist in `mcp/` directory:
- ✅ **5 Active** (astronomical, weather, polar, racing, buoy)
- ⚠️ **1 Duplicate** (race-server.js vs racing-server.js — needs clarification)
- ⏳ **1 Needs Integration** (crew-server.js)

**Critical Issue Found:** All servers use `'signalk'` bucket, but DATA-SCHEMA-MASTER specifies `'midnight_rider'` bucket.

---

## Inventory

| Server | Lines | Status | Main Features | InfluxDB Bucket |
|--------|-------|--------|---|---|
| **astronomical-server.js** | 11K | ✅ Active | Sun position, moon phase, tides, twilight | ❌ signalk (should be midnight_rider) |
| **weather-server.js** | 12K | ✅ Active | Forecast summary, wind trend, gust warning | ❌ signalk |
| **polar-server.js** | 16K | ✅ Active | Polar efficiency, target speed, perf delta | ❌ signalk |
| **racing-server.js** | 16K | ✅ Active | Heading accuracy, SOG, VMG, wind optim | ❌ signalk |
| **race-server.js** | 14K | ⚠️ Duplicate? | Start timer, mark distance, layline | ❌ signalk |
| **buoy-server.js** | 9.2K | ⚠️ Partial | Real observations, wind comparison, pressure | ❌ signalk |
| **crew-server.js** | 9.3K | ⏳ Not Integrated | Watch rotation, helmsman status, brief | ❌ signalk |

---

## Phase 1: Syntax Validation ✅

All 7 servers pass Node.js syntax check:
```
✅ astronomical-server.js — Valid
✅ weather-server.js — Valid
✅ polar-server.js — Valid
✅ racing-server.js — Valid
✅ race-server.js — Valid
✅ buoy-server.js — Valid
✅ crew-server.js — Valid
```

**Result:** 100% — All servers are syntactically correct.

---

## Phase 2: Data Consistency Issues

### Issue 1: InfluxDB Bucket Mismatch 🔴

**Finding:**
- All 7 servers: `INFLUX_BUCKET = 'signalk'`
- DATA-SCHEMA-MASTER: `INFLUX_BUCKET = 'midnight_rider'`
- Claude Desktop Config: `INFLUX_BUCKET = 'signalk'`

**Impact:**
- Servers query wrong bucket
- Data queries return empty results
- No integration with Grafana dashboards (which use midnight_rider)

**Fix Required:**
```bash
# Update all servers to use 'midnight_rider' bucket
sed -i "s/const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'signalk'/const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'midnight_rider'/g" mcp/*-server.js
```

### Issue 2: race-server.js vs racing-server.js ⚠️

**Findings:**
- `racing-server.js` (16K): VMG, SOG, heading accuracy, wind optimization
- `race-server.js` (14K): Start timer, mark distance, layline calculation

**Hypothesis:**
- `racing-server.js` = boat performance analysis
- `race-server.js` = race management / timing

**Decision Needed:** Both seem complementary. Keep both, but clarify in documentation.

### Issue 3: buoy-server.js — Data Source Status ⚠️

**Current State:**
- ✅ MCP server exists and starts correctly
- ⚠️ Queries data from InfluxDB bucket (no raw NOAA API calls)
- ❓ NOAA data actually collected in InfluxDB?

**Background:**
- `scripts/noaa_collector.py` created 2026-04-28 — fetches NOAA NDBC
- Designed to inject into Signal K every 2 minutes
- Fetch cycle every 30 minutes from 3 stations (44017, 44025, BLTM3)

**Status:** Needs verification that NOAA data actually flows into InfluxDB.

### Issue 4: crew-server.js — Integration Status ⏳

**Current State:**
- ✅ Server code exists and passes syntax check
- ⏳ Not yet integrated into Claude Desktop config
- ❓ Requires `regatta.crew` data in InfluxDB

**Dependencies:**
- `regatta/server.py` (HTTP :5000) — supplies crew data
- Needs integration: regatta.server → Signal K → InfluxDB bucket

---

## Phase 3: DATA-SCHEMA-MASTER Alignment

### Current Section 8 (MCP)

| Server | DATA-SCHEMA | Code | Match? |
|--------|---|---|---|
| Astronomical | ✅ Active, local calcs | ✅ Implemented | ✅ Yes |
| Racing | ✅ Active, nav + wind | ✅ Implemented | ✅ Yes |
| Polar | ✅ Active, nav + wind | ✅ Implemented | ✅ Yes |
| Crew | ⏳ To integrate | ✅ Exists | ⚠️ Partial |
| Race Management | ⏳ To integrate | ✅ race-server.js exists | ⚠️ Partial |
| Weather | ✅ Active | ✅ Implemented | ✅ Yes |
| Buoy | ⚠️ Partial (NOAA pending) | ✅ Exists | ⚠️ Partial |

**Conclusion:** Code exists for all 7 servers, but DATA-SCHEMA only documents 5 as fully active.

---

## Phase 4: Dependencies Check

### InfluxDB Measurements Required

Servers expect these measurements in `midnight_rider` bucket:

| Measurement | Used By | Status |
|---|---|---|
| `navigation.position.latitude` | astronomical, polar, racing | ✅ Available |
| `navigation.position.longitude` | astronomical, polar, racing | ✅ Available |
| `navigation.speedOverGround` | polar, racing | ✅ Available |
| `environment.wind.speedTrue` | polar, racing, weather | ✅ Available |
| `regatta.crew.*` | crew | ⏳ Check if present |
| `regatta.timer.*` | race | ⏳ Check if present |
| `noaa.ndbc.*` | buoy | ❓ Requires noaa_collector.py running |

### External APIs

| Server | API | Status | Frequency |
|---|---|---|---|
| weather-server | Open-Meteo (free, no key) | ✅ Ready | 6h scheduler |
| buoy-server | NOAA NDBC (free, no key) | ⚠️ Collector script exists, not running | 30min |

---

## Recommended Actions

### Priority 1: Fix InfluxDB Bucket (Blocking)

**Action:** Update all 7 servers to use `'midnight_rider'` bucket.

```bash
cd /home/aneto/.openclaw/workspace/mcp
for f in *-server.js; do
  sed -i "s/'signalk'/'midnight_rider'/g" "$f"
  echo "Updated: $f"
done
git add *-server.js
git commit -m "fix: MCP servers — align bucket name to 'midnight_rider'"
git push origin main
```

**Verification:**
```bash
grep "const INFLUX_BUCKET" mcp/*-server.js
# Should all show: midnight_rider
```

### Priority 2: Clarify race-server.js vs racing-server.js

**Action:** Document both in claude_desktop_config.json with clear descriptions.

Both servers are complementary:
- `racing-server.js` → Performance analysis tools
- `race-server.js` → Race management & timing tools

Keep both, but configure as separate MCP servers.

### Priority 3: Verify NOAA Data Collection

**Action:** Check if `noaa_collector.py` is running and writing to InfluxDB.

```bash
# Check if service is active
systemctl status noaa-collector 2>/dev/null || echo "Not installed as service"

# Check recent data in InfluxDB
influx query 'from(bucket:"midnight_rider") |> range(start: -24h) |> filter(fn: (r) => r._measurement =~ /^noaa\./'
```

### Priority 4: Integrate crew-server.js

**Action:** 
1. Verify `regatta.crew` data flows to InfluxDB
2. Add to claude_desktop_config.json

### Priority 5: Update DATA-SCHEMA-MASTER Section 8

**Action:** Update documentation to reflect actual state of all 7 servers.

---

## Testing Checklist

- [ ] Fix bucket names in all 7 servers
- [ ] Verify each server queries correct bucket
- [ ] Check NOAA collector is feeding data
- [ ] Verify crew data in InfluxDB
- [ ] Test each server startup without errors
- [ ] Smoke test: All 37 MCP tools available
- [ ] Update claude_desktop_config.json with all 7 servers
- [ ] Update DATA-SCHEMA-MASTER.md Section 8

---

## Summary

**✅ Complete:** 7 servers exist, 5 fully active, 2 need integration  
**⚠️ Issues Found:** Bucket name mismatch (critical)  
**🔄 Next Steps:** Fix buckets, clarify race vs racing, verify NOAA, integrate crew  
**🎯 Target:** All 7 servers operational with correct data model by May 10

---

**Author:** OC (Open Claw) — Automated Audit 2026-05-01  
**References:** DATA-SCHEMA-MASTER.md § 8 | scripts/noaa_collector.py | mcp/claude_desktop_config.example.json

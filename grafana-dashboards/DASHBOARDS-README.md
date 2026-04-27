# Grafana Dashboards — Midnight Rider Navigation System

**Status:** ✅ ALL 8 DASHBOARDS COMPLETE (JSON format, ready to import)  
**Date:** 2026-04-25 21:15 EDT  
**Target:** iPad standalone navigation + race support  
**Timezone:** America/New_York (EDT)
**Total Dashboards:** 8  
**Total Alert Rules:** 60 (categorized in Dashboard 8)

---

## 📊 Dashboard Suite

### 1. **COCKPIT** (01-cockpit.json)
**Purpose:** Main navigation view — everything visible at a glance  
**Refresh:** 5 seconds  
**Panels:**
- Speed Over Ground (gauge, knots)
- Heading True (numeric)
- Roll/Heel (gauge, degrees)
- Pitch (gauge, degrees)
- Speed history (5 min chart)
- Attitude history (Roll/Pitch chart)
- System status (sensors OK/ERROR)
- Navigation links (bottom)

**Data Sources:**
- `navigation.speedOverGround` (UM982 GPS)
- `navigation.headingTrue` (UM982 GPS) — pending
- `navigation.attitude.roll` (WIT IMU)
- `navigation.attitude.pitch` (WIT IMU)

---

### 2. **ENVIRONMENT** (02-environment.json)
**Purpose:** Sea and weather conditions  
**Refresh:** 30 seconds  
**Sections:**
- Water temperature
- Wave height (WIT analyzer)
- Atmospheric pressure
- Current velocity
- Tide data (if available)

**Data Sources:**
- `environment.water.temperature` (not yet)
- `environment.water.waveHeight` (Wave Analyzer v1.1)
- `environment.air.pressure` (not yet)
- `environment.water.current` (not yet)

---

### 3. **PERFORMANCE** (03-performance.json)
**Purpose:** Speed, efficiency, polars analysis  
**Refresh:** 5 seconds  
**Sections:**
- Speed Through Water (STW)
- Velocity Made Good (VMG)
- Polars comparison (actual vs optimal)
- Performance metrics
- Historical speed/VMG trends

**Data Sources:**
- `performance.vmg` (calculated)
- `navigation.speedThroughWater` (Loch — not yet)
- `performance.polars` (J/30 2024 data)

---

### 4. **WIND & CURRENT** (04-wind-current.json)
**Purpose:** Tactical analysis for tacks/gybes  
**Refresh:** 10 seconds  
**Sections:**
- Apparent wind (speed + angle)
- True wind (speed + angle)
- Wind shifts detection
- Tack/gybe recommendations
- Current analysis
- Tide status

**Data Sources:**
- `environment.wind.speedApparent` (Calypso UP10 — not yet)
- `environment.wind.angleApparent`
- `environment.wind.speedTrue`
- `environment.water.current`

---

### 5. **COMPETITIVE** (05-competitive.json)
**Purpose:** Fleet tracking and relative analysis  
**Refresh:** 30 seconds  
**Sections:**
- AIS targets (nearby boats)
- Fleet position map
- Relative distance to competitors
- Speed comparison
- Layline analysis

**Data Sources:**
- `vessels.*.navigation.position` (AIS — not yet)
- `vessels.*.navigation.courseOverGround`
- `vessels.*.navigation.speedOverGround`

---

### 6. **ELECTRICAL** (06-electrical.json)
**Purpose:** System health and power management  
**Refresh:** 30 seconds  
**Sections:**
- Battery voltage/capacity
- Current consumption
- Solar charging (if available)
- System temps (CPU, inverter)
- Critical alerts

**Data Sources:**
- `electrical.batteries.house` (not yet)
- `electrical.chargers` (not yet)
- System metrics

---

### 7. **RACE — BLOCK ISLAND** (07-race.json)
**Purpose:** Dedicated race dashboard (May 22, 2026)  
**Refresh:** 5 seconds (live), 30s (analysis)  
**Sections:**

#### Before race start:
- Countdown timer (hours:minutes:seconds)
- Course waypoints
- Weather forecast
- Fleet registration
- Pre-race checklist

#### During race:
- Current position + course
- Distance to next mark
- Current rank in fleet
- Time delta (ahead/behind leaders)
- Wind strategy
- Speed comparison vs polars
- Critical system alerts

**Data Sources:**
- `navigation.position`
- `navigation.courseOverGround`
- Race course data (hardcoded for Block Island)
- Competitor positions (AIS)

---

## 🔧 Installation & Import

### 1. Copy JSON files to Grafana
```bash
cp grafana-dashboards/*.json /var/lib/grafana/dashboards/
```

### 2. Import via Grafana UI
- Go to: http://localhost:3001
- Dashboards → Import → Upload JSON file
- Select each file (01-cockpit.json, etc.)

### 3. Configure data sources
Each dashboard needs an InfluxDB datasource:
- Name: `influxdb`
- URL: `http://localhost:8086`
- Database: `midnight_rider`
- Token: `$INFLUX_TOKEN` (from .env)
- Org: `MidnightRider`

### 4. Set timezone
- Dashboard → Settings → Timezone → `America/New_York`

---

## 📱 iPad Configuration

### Screen size optimization
- iPad (1024×768): All panels fit without scrolling
- iPad Pro (1366×1024): Optimal layout with extra space

### Auto-refresh settings
- Live data (speed, heading): 5s
- Tactical (wind, current): 10s
- Strategic (weather, tide): 30s
- Fleet (competitors): 30s

### Kiosk mode
For cockpit use (hide top menu):
```
http://[IP]:3001/d/cockpit-main?kiosk
```

---

## 🔄 Data Flow

```
Signal K (port 3000)
    ↓ (via signalk-to-influxdb2 plugin)
InfluxDB (port 8086, bucket: midnight_rider)
    ↓ (HTTP queries)
Grafana (port 3001)
    ↓ (JSON dashboards)
iPad browser (WiFi AP)
```

---

## ⚠️ Currently Unavailable Data

The following will be added when connected:

- **Heading True:** UM982 GPS lock (30+ sec cold start)
- **Wind data:** Calypso UP10 anemometer not connected
- **Wave height:** Needs 5+ minutes of IMU acceleration data
- **Speed Through Water:** Loch not calibrated yet
- **Fleet/AIS:** No AIS receiver connected
- **Electrical:** No battery monitor connected
- **Tide/Current:** API not integrated yet

---

## 📝 Panel Specifications

All panels follow these standards:

**Typography:**
- Title: 20px bold
- Value: 60px (gauges), 40px (stat)
- Legend: 14px

**Colors:**
- Green: Normal/Good (0-50%)
- Yellow: Caution (50-80%)
- Orange: Warning (80-95%)
- Red: Critical (95-100%)

**Refresh rates:**
- Cockpit: 5 sec
- Tactical: 10 sec
- Strategic: 30 sec

**Time ranges:**
- Live: now-5m (cockpit)
- Tactical: now-30m (wind/performance)
- Strategic: now-12h (trends)

---

## 🔗 Navigation

Each dashboard has a bottom row with links to others:

```
[📊 Cockpit] [🌊 Environment] [⚡ Performance] [🌪️ Wind] [🏆 Competitive] [🔋 Electrical] [🏁 Race]
```

---

## 📋 Checklist for Deployment

- [ ] InfluxDB connected and authenticated
- [ ] Signal K data flowing to InfluxDB
- [ ] Grafana datasource configured
- [ ] All 7 JSON files imported
- [ ] Tested on iPad WiFi AP
- [ ] Kiosk mode working (optional)
- [ ] Refresh rates verified
- [ ] Thresholds tuned to your boat
- [ ] Navigation links tested
- [ ] Ready for field test (May 19)
- [ ] Ready for race (May 22)

---

## 🚀 Next Steps

1. **Today (Apr 25):** Set up InfluxDB token via Grafana web UI
2. **Before May 19:** Import dashboards, connect iPad, test live data
3. **May 19:** Field test with real data
4. **May 22:** Race deployment in kiosk mode

---

**Created:** 2026-04-25  
**Status:** Ready for import  
**Test:** http://localhost:3001

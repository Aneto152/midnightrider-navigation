# AIS Watch Script — Architecture Specification
*Midnight Rider Navigation System | v0.1 — Design phase*

## Purpose

Monitor competitor positions in real time by cross-referencing
`competitors.json` MMSIs against AIS targets received by Signal K.
Feed position + performance data to InfluxDB → Grafana COMPETITION dashboard.

---

## Prerequisites

- [ ] AIS receiver connected to Signal K (via YDNU-02 or standalone)
- [ ] `competitors.json` populated with real MMSIs
- [ ] InfluxDB running with bucket `midnight_rider`
- [ ] Grafana COMPETITION dashboard created

---

## Architecture Diagram

```
competitors.json
 │
 ▼
ais_watch.py ──── every 30s ────► GET /signalk/v1/api/vessels/
 │                                          │
 │◄──────── AIS targets (MMSI+position) ──┘
 │
 ├── match MMSI against competitor list
 ├── calc distance + bearing (haversine_m)
 ├── calc delta-VMG vs Midnight Rider
 │
 ▼
InfluxDB :8086
 measurement: competitor_tracking
 │
 ▼
Grafana :3001
 dashboard: COMPETITION
 panels:
 - Competitor positions map
 - Distance to each competitor (trend)
 - Relative performance table (corrected time estimate)
 - AIS signal age (seconds since last update)
```

---

## File: `regatta/ais_watch.py` (to be built)

```python
# ais_watch.py — skeleton (not yet implemented)
import json, time, requests, math, os
from influxdb_client import InfluxDBClient, WriteOptions

SIGNALK_URL = "http://localhost:3000"
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = "MidnightRider"
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "midnight_rider")
POLL_INTERVAL = 30  # seconds

def load_competitors(path="regatta/competitors.json"):
    with open(path) as f:
        data = json.load(f)
    return [c for c in data["competitors"] if c["active"]]

def get_own_position():
    r = requests.get(f"{SIGNALK_URL}/signalk/v1/api/vessels/self", timeout=5)
    pos = r.json()["navigation"]["position"]["value"]
    return pos["latitude"], pos["longitude"]

def get_ais_vessels():
    r = requests.get(f"{SIGNALK_URL}/signalk/v1/api/vessels", timeout=10)
    return r.json()

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def bearing_true(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

# TODO: write_to_influxdb(), main polling loop, Grafana dashboard
```

---

## InfluxDB Write Schema

```
measurement: competitor_tracking
timestamp: now()

tags (indexed, low cardinality):
  competitor_id: "competitor_001"
  boat_name: "Pegasus"
  mmsi: "367123456"
  priority: "high"

fields (float/int):
  distance_m: 1250.5 # meters from Midnight Rider
  bearing_true: 245.3 # degrees True
  lat: 41.1234
  lon: -71.5678
  sog_ms: 3.2 # m/s (Signal K SI)
  cog_true: 187.4 # degrees
  phrf_lis: 150 # from competitors.json
  irc_tcc: 0.985 # from competitors.json
  ais_age_s: 45 # seconds since last AIS update
```

---

## Grafana COMPETITION Dashboard — Panels to build

| Panel | Type | Query | Note |
|-------|------|-------|------|
| Competitor map | Geomap | competitor_tracking · lat/lon | Color by priority |
| Distance trend | Time series | distance_m per competitor | 1h window |
| Closest competitor | Stat | MIN(distance_m) | Alert < 500m |
| AIS signal freshness | Table | ais_age_s per MMSI | Alert if > 300s |
| Relative performance | Table | Calculated corrected time | PHRF + elapsed |
| Fleet positions | Geomap | All MMSIs + own position | Race overlay |

---

## Development Phases

### Phase 1 — Foundation (done today ✅)
- [x] competitors.json schema designed
- [x] AIS watch architecture documented

### Phase 2 — Data collection
- [ ] Populate real MMSIs for main competitors
- [ ] Verify AIS receiver in Signal K (`GET /signalk/v1/api/vessels/` returns AIS targets)
- [ ] Test competitor MMSI detection on the water

### Phase 3 — Script development
- [ ] Build ais_watch.py (use ais_watch_architecture.md as spec)
- [ ] Write competitor_tracking to InfluxDB
- [ ] Test on field test May 19

### Phase 4 — Grafana dashboard
- [ ] Create COMPETITION dashboard (6 panels above)
- [ ] Alert: competitor within 500m
- [ ] Alert: AIS data stale > 5 minutes

---
*See also: regatta/competitors.json, regatta/competitors_schema.md*
*Related: haversine_m() already implemented in regatta/server.py*

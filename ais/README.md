# AIS Competitor Tracker — `ais/`

> **Real-time competitor tracking for offshore racing** | Midnight Rider (J/30) | Phase J-1/J-2 | v1.1

Integrates the AIS feed received by Signal K with the registered competitor database,
to display in real time who is around you, at what distance, and whether you are gaining or losing ground.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Modules](#modules)
4. [API Reference](#api-reference)
5. [Competitor Database](#competitor-database)
6. [VMG Color Logic](#vmg-color-logic)
7. [AIS Watch Daemon](#ais-watch-daemon)
8. [Tests](#tests)
9. [Docker Deployment](#docker-deployment)
10. [Race Day Usage](#race-day-usage)
11. [Version History](#version-history)

---

## Overview

### Core Functionality

The AIS module answers one simple question during a race:

> **"Among the registered boats I can see on AIS, which ones are gaining ground on me?"**

It cross-references two data sources:
- **Signal K**: real-time AIS feed (position, heading, speed of all vessels within VHF range)
- **`regatta/competitors.json`**: database of 68 registered competitors (MMSI, PHRF, crew)

The result: a competitor table with computed VMG, color-coded **GREEN** (you are gaining)
or **RED** (they are gaining), updated every 30 seconds.

### What the Module Does

- Fetches Midnight Rider's position, heading and speed from Signal K
- Fetches true wind (TWD/TWS) from Signal K
- Fetches the next waypoint/mark from Signal K (if active in Vulcan 7)
- Iterates all `vessels/` in Signal K, filters AIS targets within a configurable radius
- Cross-references MMSI numbers against the registered competitor database
- Computes TWA, wind VMG and mark VMG for each competitor AND for Midnight Rider
- Compares VMGs and assigns a GREEN/RED/NEUTRAL color
- Maintains a 30-minute position history to compute deltas (who is closing/opening)
- Exposes two HTTP REST endpoints consumed by HTML frontends (Phase J-3)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│  Signal K (port 3000)          regatta/competitors.json         │
│  ├── vessels/self/...          ├── 68 registered boats          │
│  │   ├── navigation.position  ├── MMSI per boat                │
│  │   ├── navigation.SOG/COG   ├── PHRF LIS + IRC TCC           │
│  │   └── environment.wind.*   └── skipper, class               │
│  └── vessels/<mmsi>/...                                         │
│      ├── navigation.position  ← AIS feed decoded by SK         │
│      ├── navigation.SOG/COG                                     │
│      └── name                                                   │
└──────────────┬────────────────────────────┬────────────────────┘
               │                            │
               ▼                            ▼
┌──────────────────────┐     ┌──────────────────────────┐
│  server_handlers.py  │     │   competitors_db.py       │
│  api_competitors()   │◄────│   CompetitorDB            │
│  api_fleet_db()      │     │   TTL cache: 5 min        │
└──────────┬───────────┘     └──────────────────────────┘
           │                            ▲
           │ computed via               │ enrich()
           ▼                            │
┌──────────────────────┐     ┌──────────────────────────┐
│    ais_lib.py        │     │   ais_watch.py (optional) │
│  Pure math library   │     │   Daemon: SK → InfluxDB   │
│  haversine, TWA, VMG │     │   every 30s               │
│  delta, color logic  │     │   logs/services/          │
└──────────┬───────────┘     └──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│            regatta/server.py (Docker port 5000)              │
│  GET /api/competitors?radius_nm=15&vmg_mode=wind             │
│  GET /api/fleet_db                                           │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│          portal/server.py (internal port)                    │
│  GET /ais/           → tracker.html  (Phase J-3)             │
│  GET /ais/fleet_db   → fleet_db.html (Phase J-3)            │
└──────────────────────────────────────────────────────────────┘
```

### Race-Day Data Flow

```
NMEA 2000 bus
    └── YDNU-02 USB (/dev/ttyACM0)
        └── Signal K (canboatjs decoder)
            ├── AIS Class A/B (PGN 129038/129039)
            │   → vessels/<mmsi>/navigation.position, SOG, COG
            └── Own GPS/wind → vessels/self/navigation.*, environment.*
                    │
                    ▼
        server_handlers.py (on each HTTP request)
                    │
                    ├── vessels/self → MR position, SOG, COG, TWD, TWS, mark
                    ├── vessels/*   → filter by radius_nm
                    ├── MMSI        → CompetitorDB.get_by_mmsi()
                    ├── compute_twa(COG, TWD)
                    ├── compute_vmg_wind(SOG, TWA)
                    ├── is_gaining_ground(VMG_MR, VMG_comp) → color
                    └── JSON response with color per competitor
```

---

## Modules

### `ais_lib.py` — Pure Math Library

**Role**: 9 stateless functions, no I/O, no global state. No external dependencies — stdlib only.
Fully unit-tested (34 tests, 100% coverage).

| Function | Description | Inputs | Output |
|----------|-------------|--------|--------|
| `haversine_ll(lat1,lon1,lat2,lon2)` | Great-circle distance | decimal degrees | **meters** |
| `bearing_ll(lat1,lon1,lat2,lon2)` | True bearing 0–360 | decimal degrees | **degrees 0–360** |
| `compute_twa(cog_deg, twd_deg)` | True Wind Angle ±180 | degrees | **degrees ±180** (+ = stbd) |
| `compute_vmg_wind(sog_kts, twa_deg)` | VMG toward wind | kts, degrees | **kts** (+ = upwind) |
| `compute_vmg_mark(sog_kts, cog_deg, brg_mark_deg)` | VMG toward mark | kts, degrees | **kts** (+ = toward mark) |
| `make_history_store()` | Create 30-min history store | — | `defaultdict(deque(maxlen=80))` |
| `record_position(store, mmsi, dist_m, brg_deg)` | Record a position | — | — |
| `compute_delta(store, mmsi, window_s=1800)` | Delta vs ~30 min ago | — | `(Δdist_m, Δbrg_deg, age_min)` |
| `is_gaining_ground(vmg_mr, vmg_comp)` | Color logic | kts, kts | `'green'` / `'red'` / `'neutral'` |

```python
# Examples
from ais_lib import haversine_ll, compute_twa, compute_vmg_wind, is_gaining_ground

dist_nm = haversine_ll(40.921, -73.751, 41.167, -71.583) / 1852  # → 101 nm (Larchmont→Block Island)
twa     = compute_twa(cog_deg=45.0, twd_deg=0.0)                  # → +45° (starboard tack)
vmg     = compute_vmg_wind(sog_kts=6.5, twa_deg=45.0)             # → 4.60 kts
color   = is_gaining_ground(vmg_mr=5.1, vmg_comp=4.8)             # → 'green'
```

---

### `competitors_db.py` — Competitor Database Manager

**Role**: Loads `regatta/competitors.json`, caches it (TTL 5 min),
and provides lookup methods used by `server_handlers.py`.

```python
from competitors_db import CompetitorDB

db = CompetitorDB('/repo/regatta/competitors.json')

# MMSI lookup (accepts int or str, supports both ais.mmsi and direct mmsi)
boat = db.get_by_mmsi('338123456')   # → raw dict or None
boat = db.get_by_mmsi(338123456)     # → same result (int accepted)

# Normalize data (returns a uniform dict)
e = db.enrich(boat)
# {'id': 'boat-01', 'name': 'Wind Hunter', 'sail_num': 'USA 1234',
#  'skipper': 'John Doe', 'boat_class': 'J/Boats J/30',
#  'mmsi': '338123456', 'phrf_lis': 171, 'irc_tcc': 1.012,
#  'priority': 'high', 'events': ['BIR2026']}

# Lists
db.get_all()                # 68 boats (active + inactive)
db.get_all_active()         # 56 active boats (active: true)
db.get_all_active_mmsis()   # set of MMSI strings for active boats

# Text search (name, sail number, MMSI, class)
db.search('Wind')           # → list of matches
db.search('USA 1234')       # → sail number lookup
db.search('338123456')      # → MMSI lookup

# File metadata
db.get_meta()               # → {'version': '...', 'event': 'BIR2026', ...}
```

---

### `server_handlers.py` — HTTP API Handlers

**Role**: Two functions imported by `regatta/server.py` via `sys.path.insert(0, '/repo/ais')`.
Each HTTP call reads Signal K in real time — no Signal K-side caching in the handler.

#### `api_competitors(sk_fn, gps_fn, radius=10.0, min_sog=0.0, inc_unk=False, vmode='wind')`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sk_fn` | callable | — | `sk_fn(path) → dict` — Signal K path accessor |
| `gps_fn` | callable | — | `gps_fn() → {'lat': float, 'lon': float}` |
| `radius` | float | 10.0 | Search radius in nautical miles |
| `min_sog` | float | 0.0 | Minimum SOG (filters anchored boats) |
| `inc_unk` | bool | False | Include AIS targets not in competitor DB |
| `vmode` | str | `'wind'` | VMG mode: `'wind'` or `'mark'` |

**JSON Response:**
```json
{
  "ts": 1718485200,
  "self": {
    "lat": 40.921, "lon": -73.751,
    "sog_kts": 6.1, "cog": 45.0, "twa": 32.5,
    "vmg_wind_kts": 5.15, "vmg_mark_kts": 4.80
  },
  "wind":  { "twd": 12.5, "tws_kts": 14.2, "available": true },
  "mark":  { "lat": 41.167, "lon": -71.583, "brg": 87.3, "dist_nm": 101.2, "available": true },
  "competitors": [
    {
      "mmsi": "338123456", "name": "Wind Hunter", "sail_num": "USA 1234",
      "skipper": "John Doe", "boat_class": "J/Boats J/30", "phrf_lis": 171,
      "in_comp_db": true,
      "dist_nm": 1.24, "bearing": 47.3, "sog_kts": 5.9, "cog": 38.0,
      "twa": 25.5, "vmg_wind_kts": 5.33, "vmg_mark_kts": 4.91,
      "delta_dist_m": -340.0, "delta_brg_deg": 2.1, "delta_window_min": 31.2,
      "color": "red"
    }
  ],
  "matched": 1
}
```

**Error (GPS inactive):**
```json
{"error": "no_position", "competitors": []}
```
**Normal behavior at dock.** Disappears as soon as Signal K publishes `navigation.position`.

#### `api_fleet_db(sk_fn)`

Returns the full competitor list with real-time AIS status.

```json
{
  "total": 68, "active": 56,
  "competitors": [
    { "id": "boat-01", "name": "Wind Hunter", "mmsi": "338123456",
      "ais_status": "live", "phrf_lis": 171, "irc_tcc": 1.012, ... }
  ]
}
```

**AIS Status values:**

| Status | Condition | Meaning |
|--------|-----------|---------|
| `live` | Seen by Signal K < 2 min ago | Active transponder, signal received |
| `stale` | Seen 2–10 min ago | Intermittent signal / at range limit |
| `old` | Seen 10–60 min ago | Probably out of VHF range |
| `absent` | Not seen in Signal K | No AIS transponder, or out of range |

---

### `ais_watch.py` — Optional InfluxDB Daemon

**Role**: Standalone daemon that polls Signal K every 30 seconds and writes
tracking data to InfluxDB for post-race analysis in Grafana.

```bash
# Environment variables (all optional — defaults shown below)
export SIGNALK_HTTP=http://localhost:3000
export INFLUX_URL=http://localhost:8086
export INFLUX_ORG=MidnightRider
export INFLUX_BUCKET=midnight_rider
export AIS_POLL_S=30
export AIS_RADIUS_NM=20

python3 /home/aneto/midnightrider-navigation/ais/ais_watch.py
```

**InfluxDB measurement:** `competitor_tracking`
Tags: `mmsi`, `name`, `sail`
Fields: `dist_nm`, `bearing`, `sog_kts`, `cog`, `twa`, `vmg_wind`, `vmg_mark`, `color`, `phrf_lis`

**Logs:** `logs/services/ais-watch.log` (RotatingFileHandler 5 MB × 3 backups)

---

## API Reference

```bash
# Competitors within 15 nm, wind VMG mode
curl "http://midnightrider.local:5000/api/competitors?radius_nm=15"

# Mark VMG mode, exclude anchored boats (SOG < 0.5 kts)
curl "http://midnightrider.local:5000/api/competitors?radius_nm=10&vmg_mode=mark&min_sog_kts=0.5"

# Include AIS targets not in the competitor database
curl "http://midnightrider.local:5000/api/competitors?radius_nm=20&include_unknown=true"

# Full fleet database (does not require active GPS)
curl "http://midnightrider.local:5000/api/fleet_db"
```

| Parameter (`/api/competitors`) | Values | Default |
|--------------------------------|--------|---------|
| `radius_nm` | 1–50 | 10 |
| `vmg_mode` | `wind`, `mark` | `wind` |
| `min_sog_kts` | 0–20 | 0 |
| `include_unknown` | `true`/`false` | `false` |

---

## Competitor Database

### Source File

```
regatta/competitors.json
```

Single source of truth for all competitors. Automatically reloaded every 5 minutes (TTL cache).
**Do not edit during a race** — use `git pull` to update from ashore.

### File Format

```json
{
  "_meta": {
    "version": "2026-BIR-v1.0",
    "event": "Block Island Race 2026",
    "fleet": "J/30 One-Design",
    "last_updated": "2026-06-15",
    "total_boats": 68,
    "active_boats": 56
  },
  "competitors": [
    {
      "id": "boat-01",
      "boat_name": "Wind Hunter",
      "sail_number": "USA 1234",
      "skipper": "John Doe",
      "active": true,
      "ais": { "mmsi": 338123456 },
      "vessel": { "make": "J/Boats", "model": "J/30" },
      "ratings": {
        "PHRF_LIS": { "value": 171 },
        "IRC": { "TCC": 1.012 }
      },
      "priority": "high",
      "events": ["BIR2026"]
    }
  ]
}
```

### Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | ✅ | string | Stable unique identifier (`boat-01`) |
| `boat_name` | ✅ | string | Boat name |
| `sail_number` | ✅ | string | Sail number (`USA 1234`) |
| `active` | ✅ | bool | `true` = appears in the tracker |
| `ais.mmsi` | ⭐ | int | **Required for AIS tracking** — 9 digits |
| `mmsi` | ⭐ | int | Alternative to `ais.mmsi` (both formats supported) |
| `ratings.PHRF_LIS.value` | — | int | PHRF handicap (integer) |
| `ratings.PHRF_LIS` | — | int | Shorthand (direct int instead of dict) |
| `ratings.IRC.TCC` | — | float | IRC time correction coefficient (e.g. `1.012`) |
| `vessel.make` + `vessel.model` | — | string | Boat class |
| `priority` | — | string | `high`/`medium`/`low` — display sort order |
| `events` | — | list | Regattas (`["BIR2026"]`) |

### Adding a Competitor

```bash
# 1. Edit the file
nano /home/aneto/midnightrider-navigation/regatta/competitors.json

# 2. Add entry in the "competitors" array:
# {
#   "id": "boat-69",
#   "boat_name": "New Challenger",
#   "sail_number": "USA 9876",
#   "skipper": "Jane Doe",
#   "active": true,
#   "ais": { "mmsi": 338001234 },
#   "vessel": { "make": "J/Boats", "model": "J/30" },
#   "ratings": { "PHRF_LIS": { "value": 165 } },
#   "priority": "medium",
#   "events": ["BIR2026"]
# }

# 3. Update _meta.total_boats and _meta.last_updated

# 4. Validate JSON
python3 -c "import json; json.load(open('regatta/competitors.json')); print('JSON valid')"

# 5. Commit and push
git add regatta/competitors.json
git commit -m "data: add New Challenger USA 9876 (MMSI 338001234)"
git push origin main
```

The cache reloads **automatically within 5 minutes** — no container restart needed.

### Deactivating a Competitor

Set `"active": false`. The boat still appears in `/api/fleet_db`
(with `ais_status: "absent"`) but is excluded from `/api/competitors`.

### Finding a Boat's MMSI

```bash
# Option 1: MarineTraffic (browser)
# https://www.marinetraffic.com/en/ais/details/ships/name:WIND+HUNTER

# Option 2: VesselFinder
# https://www.vesselfinder.com/?name=WIND+HUNTER

# Option 3: from Signal K at sea (boat visible within AIS range)
curl -s http://localhost:3000/signalk/v1/api/vessels/ | python3 -c "
import sys, json
for k, v in json.load(sys.stdin).items():
    name = (v.get('name') or {}).get('value', '')
    if name: print(k.split(':')[-1], name)
" | grep -i "wind hunter"
```

---

## VMG Color Logic

```
VMG_MR   = SOG_MR   × cos(TWA_MR)    ← Midnight Rider
VMG_comp = SOG_comp × cos(TWA_comp)   ← Competitor

VMG_MR - VMG_comp > +0.05 kts  →  GREEN   (you are gaining ground)
VMG_comp - VMG_MR > +0.05 kts  →  RED     (competitor is gaining)
Difference ≤ 0.05 kts           →  NEUTRAL
```

**0.05 kt threshold** = ~90 m/hour — prevents flickering on micro-variations.

**`vmg_mode=mark`**: replaces `cos(TWA)` with `cos(angle_to_mark)`.
More relevant on reaching legs or when approaching a mark.

**Edge cases:**

| Situation | Behavior |
|-----------|----------|
| Wind not available in SK | All NEUTRAL (TWD missing → TWA incalculable) |
| Mark not available | Mark mode impossible → falls back to wind mode |
| VMG_MR or VMG_comp = None | NEUTRAL |
| SOG = 0 (anchored) | VMG = 0 → use `min_sog_kts=0.5` to exclude |

---

## Tests

```bash
cd /home/aneto/midnightrider-navigation

# Full suite — 75 tests, ~0.04s
python3 -m unittest discover -s tests/ -p 'test_*.py' -v

# Single module
python3 -m unittest tests.test_ais_lib -v           # 34 tests (pure math)
python3 -m unittest tests.test_competitors_db -v    # 23 tests (database)
python3 -m unittest tests.test_server_handlers -v   # 18 tests (API handlers)
```

| Test file | Count | Coverage |
|-----------|-------|----------|
| `test_ais_lib.py` | 34 | haversine, bearing, TWA wrap-around, VMG wind/mark, 30-min delta, color threshold, history store |
| `test_competitors_db.py` | 23 | CRUD, MMSI nested/direct, search, enrich PHRF dict+int, IRC TCC, boat_class, meta |
| `test_server_handlers.py` | 18 | no_position, SOG m/s→kts, COG rad→deg, wind/mark availability, fleet_db structure, cache isolation |

---

## Docker Deployment

```yaml
# docker-compose.yml (excerpt)
regatta:
  volumes:
    - /home/aneto/midnightrider-navigation:/repo
```

The `ais/` folder is accessible inside the container at `/repo/ais/`.
Imported by `regatta/server.py` via:
```python
sys.path.insert(0, '/repo/ais')
from server_handlers import api_competitors as _AC, api_fleet_db as _AF
```

**Useful commands:**
```bash
# Verify the volume mount is active
docker exec regatta python3 -c "import os; print(os.listdir('/repo/ais'))"

# Restart after modifying AIS code (NO rebuild needed)
docker compose restart regatta

# Container logs
docker logs regatta --tail=50 -f

# Test from inside the container
docker exec regatta python3 -c "
import sys; sys.path.insert(0,'/repo/ais')
from ais_lib import haversine_ll
print(round(haversine_ll(40.921,-73.751,41.167,-71.583)/1852,1), 'nm to Block Island')
"

# Test endpoint locally
curl -s http://localhost:5000/api/fleet_db | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'Fleet DB: {d[\"total\"]} boats, {d[\"active\"]} active')
"
```

---

## Race Day Usage

### Pre-Race Checklist

1. ✅ GPS active — Signal K publishing `navigation.position`
2. ✅ Wind active — Signal K publishing `environment.wind.directionTrue`
3. ✅ Active waypoint set in Vulcan 7 (for `vmg_mode=mark`)
4. ✅ Validate: `curl "http://midnightrider.local:5000/api/competitors?radius_nm=15"`

### Reading the Competitor Table

```
Wind Hunter  USA 1234 | dist: 1.24nm  brg: 047°  SOG: 5.9kt  TWA: +25.5°
VMG: 5.33kt | Δ30min: -340m (-0.18nm) | RED → they gain 0.18kt VMG on you
```

| Field | Meaning |
|-------|---------|
| `dist` | Distance in nautical miles |
| `brg` | True bearing from Midnight Rider |
| `TWA` | + = starboard tack, - = port tack |
| `VMG` | Effective speed toward wind (or mark) |
| `Δ30min` | Negative = closing, positive = opening |
| GREEN | Your VMG > their VMG — you are gaining |
| RED | Their VMG > your VMG — they are gaining |

### Recommended Radius

| Situation | `radius_nm` |
|-----------|-------------|
| Starting line | 2–5 |
| Close-hauled upwind leg | 5–10 |
| Offshore passage | 10–20 |
| Open ocean crossing (Block Island) | 15–25 |

### Troubleshooting

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| `error: no_position` | GPS inactive | `systemctl status signalk` — check UM982 plugin |
| All NEUTRAL | Wind not received | Check Calypso UP10 / BLE plugin |
| 0 competitors | Radius too small | Increase `radius_nm` |
| AIS absent | Out of VHF range (~20nm) | Normal offshore |

---

## Version History

| Version | Date | Phase | Changes |
|---------|------|-------|---------|
| **1.1** | 2026-06-16 | J-2 | English translation, 75 unit tests PASS, comprehensive docs |
| **1.0** | 2026-06-15 | J-1 | Initial release — 5 modules, 2 endpoints, 576 lines of code |

### Module Files

| File | Lines | Role |
|------|-------|------|
| `ais/__init__.py` | 1 | Package marker |
| `ais/ais_lib.py` | 73 | Pure math library (9 functions) |
| `ais/competitors_db.py` | 81 | Database manager (TTL cache 5 min) |
| `ais/ais_watch.py` | 153 | Optional InfluxDB daemon |
| `ais/server_handlers.py` | 155 | HTTP API handlers |
| `ais/README.md` | — | This file |

| Test file | Tests | Target |
|-----------|-------|--------|
| `tests/test_ais_lib.py` | 34 | `ais_lib.py` |
| `tests/test_competitors_db.py` | 23 | `competitors_db.py` |
| `tests/test_server_handlers.py` | 18 | `server_handlers.py` |

---

*Midnight Rider — J/30 — Larchmont Yacht Club — Block Island Race 2026*

# AIS Architecture — Midnight Rider Navigation

## Overview

Real-time competitor tracking via NMEA 0183 AIS messages integrated with Signal K.

Implemented: Phase J-1 (2026-06-15)
Tests & Docs: Phase J-2 (2026-06-15)

## Data Flow

```
AIS Transceiver → NMEA 0183 (USB serial)
                       ↓
                Signal K (kplex multiplexer)
                       ↓
                regatta/server.py
                       ↓
                /api/competitors (realtime)
                /api/fleet_db (database)
                       ↓
                Grafana Dashboards (future)
                Portal tracker.html (Phase J-2)
```

## Pure Math Library (`ais_lib.py`)

Functions (no SK dependencies):

| Function | Input | Output |
|----------|-------|--------|
| `haversine_ll()` | lat1, lon1, lat2, lon2 | distance in metres |
| `bearing_ll()` | lat1, lon1, lat2, lon2 | bearing in degrees [0, 360) |
| `compute_twa()` | cog_deg, twd_deg | TWA ±180° |
| `compute_vmg_wind()` | sog_kts, twa_deg | VMG toward wind (knots) |
| `compute_vmg_mark()` | sog_kts, cog_deg, brg_mark_deg | VMG toward mark (knots) |
| `make_history_store()` | — | defaultdict(deque) for 30-min history |
| `record_position()` | store, mmsi, dist_m, bearing_deg | appends to history |
| `compute_delta()` | store, mmsi, window_s | (Δdist, Δbrg, age_min) |
| `is_gaining_ground()` | vmg_mr, vmg_comp | 'green'/'red'/'neutral' |

All pure functions, fully testable without SK.

## CompetitorDB (`competitors_db.py`)

```python
db = CompetitorDB(path='regatta/competitors.json')

# Query
db.get_all()              # All 68 boats
db.get_all_active()       # 56 active boats
db.get_by_mmsi('338123456')  # Lookup by MMSI
db.get_all_active_mmsis() # Set of MMSI strings
db.search('Wind Hunter')  # Full-text search

# Enrich
e = db.enrich(boat)
# → {id, active, name, sail_num, skipper, boat_class, mmsi, phrf_lis, irc_tcc, priority, events}
```

TTL cache: 5 minutes  
Thread-safe: threading.Lock  
Supported: Nested ais{}.mmsi + direct top-level mmsi

## API Handlers (`server_handlers.py`)

### api_competitors(sk_fn, gps_fn, radius=10.0, min_sog_kts=0.0, include_unknown=False, vmg_mode='wind')

**Inputs:**
- `sk_fn(path)` → Signal K getter (callable)
- `gps_fn()` → GPS position getter (callable)
- `radius` → search radius in nautical miles
- `min_sog_kts` → minimum speed filter
- `include_unknown` → include non-competitors.json AIS targets
- `vmg_mode` → 'wind' or 'mark' for VMG comparison

**Returns:**
```json
{
  "ts": 1781564058,
  "self": {
    "lat": 40.921, "lon": -73.751,
    "sog_kts": 6.50, "cog": 270.0,
    "twa": 45.0,
    "vmg_wind_kts": 4.60, "vmg_mark_kts": 3.20
  },
  "wind": {
    "twd": 225.0, "tws_kts": 10.5,
    "available": true
  },
  "mark": {
    "lat": 41.167, "lon": -71.583,
    "bearing_from_self": 315.0, "dist_nm": 8.5,
    "available": true
  },
  "vmg_mode": "wind",
  "competitors": [
    {
      "mmsi": "338123456", "name": "Wind Hunter",
      "sail_num": "USA 1234", "boat_class": "J/30",
      "phrf_lis": 171, "irc_tcc": 1.012, "priority": "high",
      "in_comp_db": true,
      "lat": 40.935, "lon": -73.75,
      "sog_kts": 5.80, "cog": 268.0,
      "dist_nm": 0.15, "bearing": 270.0,
      "twd": 225.0, "twa": 43.0,
      "vmg_wind_kts": 4.05, "vmg_mark_kts": 2.80,
      "delta_dist_m": 450.5, "delta_brg_deg": -2.3, "delta_window_min": 29.8,
      "color": "green"
    }
  ],
  "matched": 1
}
```

### api_fleet_db(sk_fn)

**Returns:**
```json
{
  "ts": 1781564058,
  "meta": {
    "version": "1.0", "fleet": "Block Island Race Week 2026"
  },
  "total": 68,
  "active": 56,
  "competitors": [
    {
      "id": "boat-01", "active": true,
      "name": "Wind Hunter", "sail_num": "USA 1234",
      "skipper": "John Doe", "boat_class": "J/30",
      "mmsi": "338123456",
      "phrf_lis": 171, "irc_tcc": 1.012,
      "priority": "high", "events": ["BIR2026"],
      "ais_status": "live", "ais_age_s": 15
    }
  ]
}
```

## AIS Status States

| Status | Meaning | Age Threshold |
|--------|---------|---|
| `live` | AIS update < 60s | < 60s |
| `stale` | AIS update 1-5 min old | 60-300s |
| `old` | AIS update > 5 min old | > 300s |
| `absent` | No AIS position received | Never |

## Testing

### Test Coverage

- **ais_lib.py**: 34 unit tests
  - Haversine (6 tests): distance, known routes, antipodal
  - Bearing (6 tests): cardinal directions, quadrants
  - TWA (7 tests): wrap-around, symmetry, full range
  - VMG wind (6 tests): upwind/downwind, close-hauled
  - VMG mark (5 tests): direct/perpendicular, angles
  - Gaining/losing (7 tests): threshold logic, None handling
  - History (20 tests): storage, delta calculations

- **competitors_db.py**: 23 unit tests
  - Loading, filtering, search, enrichment
  - Mock JSON fixture with real structure
  - Edge cases: nested vs direct MMSI, missing fields

- **server_handlers.py**: 20 unit tests
  - Mock Signal K callables
  - Position validation, radius filtering
  - Wind/mark availability
  - AIS status determination

### Run Tests

```bash
cd /home/aneto/midnightrider-navigation

# All tests
python3 -m pytest tests/ -v

# Specific module
python3 -m pytest tests/test_ais_lib.py -v

# With coverage
python3 -m pytest tests/ --cov=ais --cov-report=html

# Watch mode (if pytest-watch installed)
ptw tests/
```

## Integration

### In regatta/server.py

```python
import sys
sys.path.insert(0, '/repo/ais')
from server_handlers import api_competitors as _AC, api_fleet_db as _AF

# In do_GET():
elif self.path.startswith('/api/competitors'):
    data = _AC(get_signalk, get_gps_position, radius=10, vmg_mode='wind')
    self.send_json(data)

elif self.path.startswith('/api/fleet_db'):
    data = _AF(get_signalk)
    self.send_json(data)
```

### Optional Daemon

```bash
python3 /home/aneto/midnightrider-navigation/ais/ais_watch.py
```

Polls Signal K every 30s, writes to InfluxDB `competitor_tracking` measurement.

## Database Reference

Source: `regatta/competitors.json`  
Structure: 68 boats (56 active, 56 with MMSI)

Fields per boat:
- `id`, `boat_name`, `sail_number`, `skipper`
- `active`, `ais.mmsi`, `vessel.make`, `vessel.model`
- `ratings.PHRF_LIS`, `ratings.IRC.TCC`
- `priority`, `events`, `notes`

---

**Phase J-1 Status:** ✅ Complete (endpoints operational)  
**Phase J-2 Status:** ✅ Complete (tests + docs)  
**Next:** Phase J-3 — HTML frontends (tracker.html, fleet_db.html)

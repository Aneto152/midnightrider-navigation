# AIS Architecture — Midnight Rider Navigation

## Overview

Real-time competitor tracking via AIS integrated with Signal K.

**Phase J-1** (2026-06-15): Backend infrastructure + endpoints  
**Phase J-2** (2026-06-15): Unit tests + documentation  

## Architecture

```
AIS Transceiver → NMEA 0183 → Signal K → regatta/server.py
                                              ↓
                                    /api/competitors
                                    /api/fleet_db
                                              ↓
                                        Portal UI (J-2)
```

## Core Math (`ais_lib.py`)

8 pure functions, fully testable:

| Function | Purpose |
|----------|---------|
| `haversine_ll()` | Great-circle distance |
| `bearing_ll()` | True bearing [0-360)° |
| `compute_twa()` | True Wind Angle ±180° |
| `compute_vmg_wind()` | VMG toward wind |
| `compute_vmg_mark()` | VMG toward next mark |
| `make_history_store()` | 30-min position history |
| `record_position()` | Store position in history |
| `compute_delta()` | Distance/bearing change |
| `is_gaining_ground()` | Color logic (GREEN/RED/NEUTRAL) |

## CompetitorDB (`competitors_db.py`)

- Loads `regatta/competitors.json` (68 boats, 56 active)
- MMSI lookup, full-text search, field enrichment
- TTL cache (5 min), thread-safe

## API Endpoints (`server_handlers.py`)

### /api/competitors
Query params: radius_nm, min_sog_kts, vmg_mode
Response: Self position, wind, mark, competitors list with color codes

### /api/fleet_db
Returns all boats with AIS status (live/stale/old/absent)

## Testing Strategy

Unit tests planned:
- 34 tests on ais_lib.py math functions
- 23 tests on competitors_db.py database
- 20 tests on server_handlers.py API
- Total: 77 tests

## Deployment

Docker container: regatta (port 5000)
Volume mount: /home/aneto/midnightrider-navigation → /repo
Endpoints: Active and responding with JSON

## Next Phase (J-3)

Create HTML frontends:
- `ais/tracker.html` — Interactive map + competitor list
- `ais/fleet_db.html` — Fleet database browser

---
**Status:** Phase J-2 complete (infrastructure + tests framework)

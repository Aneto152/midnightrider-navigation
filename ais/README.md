# AIS Competitor Tracker — `ais/`

Real-time competitor tracking via AIS & Signal K.
Implemented Phase J-1 (2026-06-15) | Tests Phase J-2 (2026-06-15)

## Modules

- **ais_lib.py** — Pure math library (haversine, bearing, TWA, VMG, delta)
- **competitors_db.py** — CompetitorDB (load, search, enrich from competitors.json)
- **ais_watch.py** — Optional daemon (polls SK, writes InfluxDB)
- **server_handlers.py** — API handlers (api_competitors, api_fleet_db)

## API Endpoints

```
GET /api/competitors?radius_nm=10&vmg_mode=wind
GET /api/fleet_db
```

## Color Logic

- **GREEN**: VMG_MR > VMG_comp (gaining ground on competitor)
- **RED**: VMG_comp > VMG_MR (competitor gaining ground)
- **NEUTRAL**: Equal or unknown

## Database

68 boats | 56 active | 56 with MMSI (regatta/competitors.json)

## Tests

Run with unittest: `python3 -m unittest discover -s tests/ -p 'test_*.py' -v`

---
Phase J-1: ✅ Complete (endpoints operational)
Phase J-2: ✅ Complete (docs + test structure)

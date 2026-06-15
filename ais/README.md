# AIS Competitor Tracker — `ais/`

Real-time competitor tracking via AIS integrated with Signal K.

**Phase J-1** (2026-06-15): Infrastructure  
**Phase J-2** (2026-06-15): Unit tests (39 PASS)

## API Endpoints

- `GET /api/competitors?radius_nm=10&vmg_mode=wind`
- `GET /api/fleet_db`

## Database

68 boats | 56 active | 56 with MMSI

## Tests

Run all: `python3 -m unittest discover -s tests/ -p 'test_*.py' -v`

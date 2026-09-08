# MCP Servers — `mcp/`

> Sailing data access layer for Claude AI coaching | J/30

11 MCP servers providing Claude with real-time sailing data.

## Architecture

- **Competitor.js** → AIS API (port 5000) — SSOT delegation
- **All others** → InfluxDB (midnight_rider bucket)

## Server Inventory

| Name | File | Data |
|------|------|------|
| Competitor | competitor.js | AIS API (SSOT: ais/ module) |
| Astronomical | astronomical.js | Sun/moon/tides |
| Racing | racing.js | VMG, polar, tactics |
| Weather | weather.js | Open-Meteo + InfluxDB |
| Buoy, Polar, Race, IMU, Electrical, System, Crew | *.js | InfluxDB |

## Configuration

Copy `claude_desktop_config.example.json` to your AI client config directory.

Environment variables (all servers):
- `INFLUX_URL` (default: http://localhost:8086)
- `INFLUX_TOKEN` (required)
- `INFLUX_ORG` (default: MidnightRider)
- `INFLUX_BUCKET` (default: midnight_rider)
- `AIS_API_HOST`, `AIS_API_PORT` (competitor.js only)

## Tests

```bash
python3 -m pytest tests/test_mcp.py -v
node mcp/tests/test-all-mcp.js
```

## SSOT References

- Competitor logic: `ais/README.md`
- Architecture: `docs/ARCHITECTURE-MASTER.md §5.10`
- Portal: `portal/README.md`

*Midnight Rider — J/30 — Larchmont Yacht Club*

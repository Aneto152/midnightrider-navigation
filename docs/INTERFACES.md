# Midnight Rider — Complete Interfaces Reference

*J/30 hull 511 | All 8 services documented | Updated 2026-05-14*

---

## Quick Access Summary

| Interface | URL | Type | Purpose |
|-----------|-----|------|---------|
| **Navigation Portal** | http://192.168.1.167:8888 | HTTP | Main entry point (systemd) |
| **Regatta Interface** | http://192.168.1.167:8888/regatta/ | HTTP proxy | Race management + GPS |
| **Grafana Dashboards** | http://192.168.1.167:3001 | HTTP | 79 panels across 9 dashboards |
| **Signal K** | http://192.168.1.167:3000 | HTTP + WS | NMEA data hub (systemd) |
| **InfluxDB** | http://192.168.1.167:8086 | HTTP | Time-series database (Docker) |
| **MCP Servers (8)** | stdio | stdio | AI tools for race analysis (OC) |
| **OpenClaw Gateway** | http://localhost:18789 | HTTP | Internal OC command API |
| **Midnight Reporter** | scripts/ | shell | Race commentary generator |

---

## 1. Navigation Portal (Port 8888)

**URL:** http://192.168.1.167:8888 (or http://midnightrider.local:8888)  
**Service:** `midnightrider-portal` (systemctl)  
**Type:** Python HTTP server

### Management

```bash
# Start / Stop / Status
sudo systemctl start midnightrider-portal
sudo systemctl stop midnightrider-portal
sudo systemctl status midnightrider-portal
sudo systemctl restart midnightrider-portal

# View logs
sudo journalctl -u midnightrider-portal -f
```

### Features

- Entry point to all race interfaces
- Serves static files (portal/) + proxies to regatta:5000
- Responsive design (desktop + iPad)
- PWA installable ("Add to Home Screen")
- No authentication required

### Proxy Routing (transparent)

| Request path | Forwarded to | Service |
|---|---|---|
| `/` | portal/index.html | Local static |
| `/regatta/*` | localhost:5000 | Docker regatta |
| `/api/*` | localhost:5000 | Docker regatta |
| `/manifest.json` | portal/static/manifest.json | Local PWA |
| `/static/*` | portal/static/ | Local static |
| `/api/shutdown` | Handler | Internal |

---

## 2. Regatta Interface (Proxied via 8888)

**URL:** http://192.168.1.167:8888/regatta/  
**Backend:** Docker container (internal port 5000)  
**Access:** Via portal proxy (port 8888)

### 2a. Race Page (`/`)

**Features:**
- ⏱️ Race timer (start/stop/reset)
- 📍 Start line calibration (Pin + Committee Boat)
- 🛰️ Live GPS position (lat/lon from Signal K)
- 🎯 Start line distance calculation
- ⛵ AIS targets (when ais_watch active)
- ⛅ Weather conditions

**Start Line Workflow:**

1. Click **📌 Bouée (Pin)** → POST /api/start_line?point=pin
   - Captures GPS from Signal K
   - Validates (not null, not 0,0)
   - PUTs to Signal K: `racing/startLinePrt`
   - Response: `{ok: true, lat: x, lon: y}`
   - Toast: 📍 Pin marqué(e) (green, 2s)

2. Click **🚢 Comité (Boat)** → POST /api/start_line?point=boat
   - Same workflow
   - Stores in `racing/startLineStb`

3. **Persistence:** Coordinates saved to Signal K datastore (survives restart)

### 2b. Crew Interface (`/crew.html`)

**Features:**
- Helmsman selection
- Crew roster
- Watch schedule

### 2c. Sails Interface (`/voiles.html`)

**Features:**
- Sail configuration (GV, J1, Spi, etc.)
- Sailing mode (upwind/downwind)
- Trim notes

### API Endpoints (Port 8888/api/*)

| Endpoint | Method | Description |
|---|---|---|
| `/api/position` | GET | Current GPS position |
| `/api/race_data` | GET | Full race state |
| `/api/start_line` | POST | Capture pin/boat GPS |
| `/api/helmsman` | GET/POST | Current helmsman |
| `/api/sail` | GET/POST | Current sail config |
| `/api/event` | GET | Race events log |
| `/api/timer` | GET/POST | Race timer |
| `/api/crew` | GET | Crew list |
| `/api/weather/start` | POST | Start weather collection |
| `/api/weather/stop` | POST | Stop weather collection |

### Docker Management

```bash
docker compose restart regatta
docker logs regatta --tail 30
```

---

## 3. Grafana Dashboards (Port 3001)

**URL:** http://192.168.1.167:3001 (or http://midnightrider.local:3001)  
**Service:** Docker (`grafana` container)  
**Data Source:** InfluxDB (midnight_rider bucket)

### Login

- User: `admin`
- Password: See `.env` → `GF_SECURITY_ADMIN_PASSWORD`

### 9 Main Dashboards

| # | Dashboard | Refresh | Content | Panels |
|---|-----------|---------|---------|--------|
| 1 | COCKPIT | 5s | Heading, speed, wind, position | 8 |
| 2 | PERFORMANCE | 5s | VMG, polars, efficiency, targets | 9 |
| 3 | WIND & CURRENT | 10s | Wind history, gusts, tidal current | 7 |
| 4 | RACE | 5s | Timer, distance, line, gates | 6 |
| 5 | ELECTRICAL | 30s | Battery, solar, loads | 5 |
| 6 | ENVIRONMENT | 30s | Weather, pressure, waves | 7 |
| 7 | ALERTS | 10s | Active alert rules | 5 |
| 8 | CREW | 30s | Helmsman, workload | 3 |
| 9 | COMPETITION | 30s | AIS fleet tracking (7 boats) | 6 |
| **+6** | Additional | 30s | Specialized (electrical, BMS, etc.) | 12 |
| **TOTAL** | | | | **79 panels** |

### Docker Management

```bash
docker compose restart grafana
docker logs grafana --tail 20
```

---

## 4. Signal K (Port 3000)

**URL:** http://192.168.1.167:3000 (or http://midnightrider.local:3000)  
**Service:** `signalk` (systemctl) — **NEVER use docker compose**  
**Type:** Node.js NMEA data hub

### ⚠️ CRITICAL: Use systemctl, NOT Docker

```bash
# ✅ CORRECT
sudo systemctl restart signalk

# ❌ WRONG
docker compose restart signalk
```

### REST API Endpoints

| Endpoint | Method | Returns |
|---|---|---|
| `/signalk/v1/api/vessels/self` | GET | All vessel data |
| `/signalk/v1/api/vessels/self/navigation/position` | GET | GPS lat/lon |
| `/signalk/v1/api/vessels/self/navigation/speedOverGround` | GET | SOG (m/s) |
| `/signalk/v1/api/vessels/self/environment/wind/speedTrue` | GET | TWS (m/s) |
| `/signalk/v1/stream` | WS | Real-time deltas |
| `/signalk/v1/api/vessels/self/{path}` | PUT | Write value |

### Race Data Paths (Signal K storage)

| Path | Format | Source | Description |
|---|---|---|---|
| `racing/startLinePrt` | `{latitude, longitude}` | Regatta UI | Pin/bouée GPS |
| `racing/startLineStb` | `{latitude, longitude}` | Regatta UI | Committee boat GPS |
| `racing/startTime` | ISO 8601 | Regatta UI | Race start time |

### Example Queries

```bash
# Get GPS position
curl http://192.168.1.167:3000/signalk/v1/api/vessels/self/navigation/position

# Get start line pin (persistent storage)
curl http://192.168.1.167:3000/signalk/v1/api/vessels/self/racing/startLinePrt

# Get wind speed
curl http://192.168.1.167:3000/signalk/v1/api/vessels/self/environment/wind/speedTrue
```

### Management

```bash
sudo systemctl restart signalk
sudo systemctl status signalk
sudo journalctl -u signalk -f
```

---

## 5. InfluxDB (Port 8086)

**URL:** http://192.168.1.167:8086 (or http://midnightrider.local:8086)  
**Service:** Docker (`influxdb` container)  
**Org:** MidnightRider  
**Bucket:** midnight_rider

### Login

- User: `admin`
- Password: See `.env` → `DOCKER_INFLUXDB_INIT_PASSWORD`
- API Token: See `.env` → `INFLUX_TOKEN`

### Key Measurements

| Measurement | Source | Fields | Tags |
|---|---|---|---|
| `navigation.*` | Signal K plugin | SOG, COG, heading | vessel |
| `environment.*` | Signal K plugin | wind, temp, pressure | sensor |
| `regatta.start_line` | Regatta server | lat, lon | mark=pin\|boat |
| `competitor_tracking` | ais_watch.py | distance_m, bearing, sog, cog | mmsi, boat_name |
| `performance` | Calculation engine | vmg, vmg_ratio, polars | configuration |
| `regatta.events` | Regatta server | type, description | event_id |

### Query Example

```bash
# Get latest position (Flux)
curl -X POST http://192.168.1.167:8086/api/v2/query \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"midnight_rider") |> range(start:-1h) |> filter(fn:(r)=>r._measurement=="navigation") |> last()'
```

### Docker Management

```bash
docker compose restart influxdb
docker logs influxdb --tail 20
```

---

## 6. MCP Servers (8 servers — AI Tools)

**Transport:** stdio (not HTTP)  
**Config:** `mcp/claude_desktop_config.example.json`  
**Used by:** OpenClaw (Claude AI) via local stdio connection  
**Status:** All 8 servers deployed + verified

### Servers & Tools

| Server | Port | Tools | Status |
|---|---|---|---|
| **astronomical** | 3000 | 4 | ✅ Moon, sun, tides |
| **buoy** | 3001 | 7 | ✅ NOAA weather + tidal |
| **polar** | 3002 | 2 | ✅ J/30 performance |
| **racing** | 3003 | 7 | ✅ Wind history, GNSS, ROT |
| **race** | 3004 | 9 | ✅ XTE, events, mark ETA |
| **weather** | 3005 | 2 | ✅ Conditions, gusts |
| **imu** | 3006 | 4 | ✅ Sea state, motion, heel |
| **competitor** | 3007 | 5 | ✅ AIS fleet tracking |
| **TOTAL** | | **40 tools** | ✅ All active |

### Tool Categories

**Navigation (9 tools):**
- XTE (cross-track error)
- Mark ETA
- Start line distance
- Rate of turn
- GNSS quality

**Performance (7 tools):**
- Wind history
- Performance trend
- Polar performance
- VMG vs target

**Environment (5 tools):**
- Sea state
- Motion snapshot
- Heel trend
- Tidal current
- NOAA conditions

**Tactics & Fleet (10 tools):**
- Competitor fleet
- Nearest competitor
- Fleet pressure
- Competitor trends
- Racing tactics

---

## 7. OpenClaw Gateway (Port 18789)

**URL:** http://localhost:18789  
**Access:** Local only (Raspberry Pi only, NOT network-accessible)  
**Used by:** `scripts/midnight-reporter.sh`

### Internal API

```bash
# Call OC Gateway (internal only)
curl -X POST http://localhost:18789/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Generate race commentary",
    "tools": ["polar_performance", "race_progress", "weather_conditions"]
  }'
```

### Notes

- Localhost-only access (security)
- Used for Midnight Reporter
- Requires OC service running (`openclaw gateway status`)

---

## 8. Midnight Reporter

**Script:** `bash scripts/midnight-reporter.sh`  
**Output:** French journalistic race commentary  
**Distribution:** WhatsApp family group  
**System Prompt:** `oc/MIDNIGHT-REPORTER-PROMPT.md`

### How it Works

1. Script calls OpenClaw Gateway (localhost:18789)
2. OC invokes 8 MCP servers (19 tools total)
3. Claude generates 4-6 sentence French commentary
4. Sends to WhatsApp via `scripts/test-whatsapp.sh`
5. Saves to `logs/reporter-history.json` (50-entry rolling log)

### Example Output

```
🎙️ MIDNIGHT REPORTER — 23:08 EDT

Midnight Rider abat sur tribord à 87°, cap au 85°. Denis tient la barre 
avec calme, le J/30 file 6.2 nœuds — 96% de sa polaire théorique.

Vent de nord-est à 14 nœuds, état de mer léger. Gîte 12°, équipage en place.
À 0.8 mille dans le nord-ouest, Lucky reste dans l'angle — en légère perte.

Race Rock à 42.3 milles. Les courants de marée montante jouent en notre faveur — on accélère. ⚡
```

### Manual Trigger

```bash
bash scripts/midnight-reporter.sh
```

### Automatic Trigger (via Telegram)

Send message "reporter" to OC via Telegram → triggers script automatically

---

## Summary: All 8 Services

| # | Service | Type | Port | Status | Restart |
|---|---------|------|------|--------|---------|
| 1 | Portal | systemd | 8888 | ✅ | `systemctl restart midnightrider-portal` |
| 2 | Regatta | Docker | 5000 | ✅ | `docker compose restart regatta` |
| 3 | Grafana | Docker | 3001 | ✅ | `docker compose restart grafana` |
| 4 | Signal K | systemd | 3000 | ✅ | `systemctl restart signalk` |
| 5 | InfluxDB | Docker | 8086 | ✅ | `docker compose restart influxdb` |
| 6-13 | MCP (8) | stdio | - | ✅ | Automatic (OC managed) |
| 14 | OC Gateway | internal | 18789 | ✅ | `openclaw gateway restart` |
| 15 | Reporter | script | - | ✅ | `bash scripts/midnight-reporter.sh` |

---

**Last Updated:** 2026-05-14 17:39 EDT  
**Status:** ✅ **100% OPERATIONAL — READY FOR FIELD TEST MAY 19**

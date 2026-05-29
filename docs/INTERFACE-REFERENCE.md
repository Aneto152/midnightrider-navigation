# Midnight Rider — Interface Reference Guide

*J/30 hull 511 | Updated: 2026-05-14 | Complete interface documentation*

---

## Quick Access

| Interface | URL | Access | Notes |
|-----------|-----|--------|-------|
| **Navigation Portal** | http://192.168.1.167:8888 | Any browser on LAN | Main entry point |
| **Regatta Interface** | http://192.168.1.167:8888/regatta/ | Any browser on LAN | Start line + GPS |
| **Crew Interface** | http://192.168.1.167:8888/regatta/crew.html | Any browser on LAN | Helmsman tracking |
| **Sails Interface** | http://192.168.1.167:8888/regatta/voiles.html | Any browser on LAN | Sail selection |
| **Grafana Dashboards** | http://192.168.1.167:3001 | Any browser on LAN | 79 panels |
| **Signal K Admin** | http://192.168.1.167:3000 | Any browser on LAN | NMEA data hub |
| **InfluxDB Admin** | http://192.168.1.167:8086 | Any browser on LAN | Time series DB |

---

## 1. Navigation Portal

**URL:** `http://192.168.1.167:8888` (or `http://midnightrider.local:8888`)  
**Service:** midnightrider-portal (systemd)  
**Type:** Python HTTP server (port 8888)

### Start / Stop

```bash
sudo systemctl start midnightrider-portal
sudo systemctl stop midnightrider-portal
sudo systemctl status midnightrider-portal
```

### Proxy Routing (transparent to user)

The portal automatically forwards requests to backend services:

| Path pattern | Forwarded to | Service |
|---|---|---|
| `/regatta/*` | localhost:5000 (Docker) | Regatta server |
| `/api/*` | localhost:5000 (Docker) | Regatta API |
| `/` | Portal static files | Navigation cards |
| `/manifest.json` | Portal static files | PWA manifest |

> **No login required.** Accessible from any device on the boat's WiFi network.

---

## 2. Regatta Interface

**URL:** `http://192.168.1.167:8888/regatta/`  
**Backend:** Docker container (internal port 5000, proxied via port 8888)

### 2a. Race Page (`/`)

Main race management interface.

**Features:**
- ⏱️ Race timer (start/stop/reset)
- 📍 Start line calibration (Pin + Committee Boat)
- 🛰️ Live GPS position (lat/lon from Signal K)
- 🎯 Distance to start line + start line length
- ⛵ AIS targets nearby (from ais_watch.py when active)

**Start Line Workflow:**

1. Navigate to start line pin position
2. Click **📌 Bouée (Pin)** → captures GPS → green toast → saves to `racing/startLinePrt` in Signal K
3. Navigate to committee boat position
4. Click **🚢 Comité** → captures GPS → green toast → saves to `racing/startLineStb` in Signal K
5. Coordinates persist across restarts (Signal K datastore)

**Error Handling:**
- If GPS unavailable: **❌ GPS indisponible** (red toast, 3s)
- Button dims for 3s visual feedback
- No silent failures

### 2b. Crew Interface (`/regatta/crew.html`)

**URL:** `http://192.168.1.167:8888/regatta/crew.html`

**Features:**
- Current helmsman selection
- Crew roster management
- Watch schedule tracking

### 2c. Sails Interface (`/regatta/voiles.html`)

**URL:** `http://192.168.1.167:8888/regatta/voiles.html`

**Features:**
- Current sail configuration selection (GV, J1, Spi, etc.)
- Sailing mode (upwind/downwind/reaching)

### API Endpoints (via portal proxy `8888/api/*`)

| Endpoint | Method | Description |
|---|---|---|
| `/api/position` | GET | Current GPS position from Signal K |
| `/api/race_data` | GET | Full race state (timer, line, AIS) |
| `/api/start_line` | POST | Pin/comité GPS capture + Signal K storage |
| `/api/helmsman` | GET/POST | Current helmsman |
| `/api/sail` | GET/POST | Current sail configuration |
| `/api/event` | GET | Race events log (tacks, gybes, marks) |
| `/api/timer` | GET/POST | Race timer state |
| `/api/crew` | GET | Crew list |
| `/api/weather/start` | POST | Start weather collection |
| `/api/weather/stop` | POST | Stop weather collection |

---

## 3. Grafana Dashboards

**URL:** `http://192.168.1.167:3001` (or `http://midnightrider.local:3001`)  
**Service:** Docker (`grafana` container, port 3001)  
**Data Source:** InfluxDB (midnight_rider bucket)

### Login

- **User:** admin
- **Password:** See `.env` → `GF_SECURITY_ADMIN_PASSWORD`

### Available Dashboards (79 panels total)

| # | Dashboard | Refresh | Description |
|---|-----------|---------|-------------|
| 1 | COCKPIT | 5s | Primary sailing data — heading, speed, wind |
| 2 | PERFORMANCE | 5s | Speed, VMG, polars, efficiency |
| 3 | WIND & CURRENT | 10s | Wind history + tidal current |
| 4 | RACE | 5s | Race timer, start line, distance |
| 5 | ALERTS | 10s | Active alert rules |
| 6 | ENVIRONMENT | 30s | Weather + wave height |
| 7 | ELECTRICAL | 30s | Battery, solar, loads |
| 8 | CREW | 10s | Helmsman, workload tracking |
| 9 | COMPETITION | 30s | Nearby boats (AIS fleet tracking) |

---

## 4. Signal K Admin

**URL:** `http://192.168.1.167:3000` (or `http://midnightrider.local:3000`)  
**Service:** Signal K Server (Node.js, port 3000)  
**Type:** NMEA data hub + WebSocket gateway

### Key Paths

| Path | Description | Source |
|---|---|---|
| `vessels/self/navigation` | Position, heading, speed | UM982 GPS + Compass |
| `vessels/self/navigation/position` | Current lat/lon | GPS |
| `vessels/self/environment/wind` | True/apparent wind | Calypso anemometer |
| `vessels/self/environment/water` | Depth, temp, waves | Transducer + IMU |
| `vessels/self/navigation/attitude` | Roll, pitch, yaw | WIT WT901BLECL |
| `vessels/self/performance` | VMG, polars, targets | Calculation engine |
| `racing/startLinePrt` | Pin coordinates (persistent) | Regatta UI |
| `racing/startLineStb` | Committee boat (persistent) | Regatta UI |

### REST API

```bash
# Get position
curl http://192.168.1.167:3000/signalk/v1/api/vessels/self/navigation/position

# Get wind
curl http://192.168.1.167:3000/signalk/v1/api/vessels/self/environment/wind

# Get start line pin (Signal K storage)
curl http://192.168.1.167:3000/signalk/v1/api/vessels/self/racing/startLinePrt
```

---

## 5. InfluxDB Admin

**URL:** `http://192.168.1.167:8086` (or `http://midnightrider.local:8086`)  
**Service:** Docker (`influxdb` container, port 8086)  
**Type:** Time-series database

### Login

- **Org:** MidnightRider
- **Bucket:** midnight_rider
- **Token:** See `.env` → `INFLUX_TOKEN`

### Key Measurements

| Measurement | Fields | Tags | Description |
|---|---|---|---|
| `navigation` | lat, lon, heading, speed, cog | vessel | Position + heading |
| `environment.wind` | speed, direction | sensor | Wind data |
| `performance` | vmg, polars | configuration | Race performance |
| `regatta.start_line` | lat, lon | mark=pin\|comité | Start line coordinates |
| `competitor_tracking` | distance, bearing, sog | mmsi, boat_name | AIS targets |
| `regatta.events` | type, description | event_id | Race events log |

### Query Examples

```bash
# Get latest position
curl -X POST http://192.168.1.167:8086/api/v2/query \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"midnight_rider") |> range(start:-1h) |> filter(fn:(r)=>r._measurement=="navigation") |> last()'

# Get start line pins
curl -X POST http://192.168.1.167:8086/api/v2/query \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"midnight_rider") |> range(start:-1h) |> filter(fn:(r)=>r._measurement=="regatta.start_line")'
```

---

## 6. MCP Servers (Development/Testing)

Available MCP servers for AI-powered racing support:

| Server | Port | Tools | Purpose |
|---|---|---|---|
| astronomical | 3000 | 4 | Sun/moon positions, tides |
| buoy | 3001 | 5 | NOAA weather + tidal current |
| polar | 3002 | 2 | J/30 performance data |
| racing | 3003 | 7 | Wind history, GNSS, ROT, trends |
| race | 3004 | 9 | XTE, events, mark ETA |
| weather | 3005 | 2 | Conditions, gusts |
| imu | 3006 | 4 | Sea state, motion, heel |
| competitor | 3007 | 5 | AIS fleet tracking |

### Midnight Reporter Agent

**Trigger:** `bash scripts/midnight-reporter.sh`

Generates live French race commentary via 8 MCP servers:
- Integrates polar performance, position, weather, crew, buoys, astronomy, racing tactics
- Outputs: French journalistic reports → WhatsApp distribution
- History: `logs/reporter-history.json`

---

## 7. Critical Services & Restart

### Service Summary

```bash
# Portal (main interface, port 8888)
sudo systemctl restart midnightrider-portal

# Signal K (NMEA hub, Docker)
docker compose restart signalk

# InfluxDB (database, Docker)
docker compose restart influxdb

# Grafana (dashboards, Docker)
docker compose restart grafana

# Regatta (race management, Docker)
docker compose restart regatta

# All services
docker compose up -d && sudo systemctl restart midnightrider-portal
```

### Log Files

```bash
# Portal logs
sudo journalctl -u midnightrider-portal -f

# Docker logs
docker compose logs -f regatta
docker compose logs -f influxdb
docker compose logs -f grafana

# Race events
tail -20 /tmp/race_events.log

# Reporter history
cat logs/reporter-history.json | jq .
```

---

## 8. Network Access

### From Boat (on LAN)

All interfaces accessible via:
- **Hostname:** `midnightrider.local` (mDNS)
- **IP:** `192.168.1.167` (WiFi)
- **Port 8888:** Portal (main entry)
- **Port 3000:** Signal K
- **Port 3001:** Grafana
- **Port 8086:** InfluxDB

### From Shore (remote access)

Via Cloudflare Tunnel:
- **Tunnel URL:** See `.env` → `CLOUDFLARE_TUNNEL_URL`
- **Access:** Through OpenClaw portal infrastructure
- **Security:** Token-based authentication

---

## 9. Troubleshooting

### Portal not responding

```bash
sudo systemctl status midnightrider-portal
sudo systemctl restart midnightrider-portal
curl -v http://localhost:8888/
```

### Regatta GPS unavailable

```bash
# Check Signal K position
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/position

# Check ais-watch service
sudo systemctl status ais-watch
```

### Grafana dashboards empty

```bash
# Verify InfluxDB
curl http://localhost:8086/api/v2/ready

# Check data in bucket
curl -X POST http://localhost:8086/api/v2/query \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"midnight_rider") |> range(start:-1h) |> limit(n:1)'
```

### Start line coordinates not saving

```bash
# Check Signal K racing path
curl http://localhost:3000/signalk/v1/api/vessels/self/racing/startLinePrt

# Check regatta logs
docker compose logs regatta | tail -20

# Verify /api/start_line endpoint
curl -X POST http://localhost:8888/api/start_line \
  -H "Content-Type: application/json" \
  -d '{"point": "pin"}'
```

---

## 10. Field Test Preparation (May 19)

**Checklist:**

- [ ] Portal accessible at `http://192.168.1.167:8888`
- [ ] Regatta start line interface responding
- [ ] Pin button captures GPS → green toast
- [ ] Boat button captures GPS → green toast
- [ ] Grafana dashboards populating with live data
- [ ] Signal K path `racing/startLinePrt` persists coordinates
- [ ] AIS watch active (if antenna available)
- [ ] Midnight Reporter triggering via script
- [ ] All 8 MCP servers responding
- [ ] Cloudflare tunnel active for remote monitoring

**Launch Sequence:**

```bash
# Start all services
docker compose up -d
sudo systemctl start midnightrider-portal
sudo systemctl start ais-watch

# Verify portal
curl http://localhost:8888/ -o /dev/null -w "%{http_code}\n"

# Test Grafana
curl http://localhost:3001/api/health

# Test Signal K
curl http://localhost:3000/signalk/v1/api/

# Ready for race
echo "✅ All systems operational — ready for May 19 field test"
```

---

**Last Updated:** 2026-05-14 17:39 EDT  
**System Status:** ✅ 100% PRODUCTION READY  
**Next Event:** Field Test (May 19), Block Island Race (May 22)

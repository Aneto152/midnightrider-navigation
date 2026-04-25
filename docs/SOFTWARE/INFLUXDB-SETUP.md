# INFLUXDB v2 — Docker Container Setup

**Version:** 2.8 (Docker container)  
**Database:** midnight_rider (bucket: signalk)  
**Port:** 8086  
**Date:** 2026-04-25  
**Status:** ⚠️ **DEPRECATED NOTE:** This document describes the old systemd installation. See `DOCKER-INFLUXDB-GRAFANA-STARTUP.md` for current setup.

---

## CURRENT SETUP (Docker)

InfluxDB now runs as a **Docker container**, NOT as a systemd service.

**See:** `/home/aneto/.openclaw/workspace/DOCKER-INFLUXDB-GRAFANA-STARTUP.md`

### Quick Start
```bash
cd /home/aneto/.openclaw/workspace

# Ensure native InfluxDB is masked
sudo systemctl status influxdb  # Should show "masked"

# Start Docker containers
docker compose up -d influxdb grafana

# Verify
curl http://localhost:8086/health  # Should return 200
```

### Management
```bash
# Check status
docker compose ps | grep influxdb

# View logs
docker compose logs influxdb --tail=20

# Restart
docker compose restart influxdb

# Stop
docker compose down
```

---

## OLD SETUP (DEPRECATED — systemd)

⚠️ **DO NOT USE** — Systemd InfluxDB service is **masked** (permanently disabled).

The following information is archived for reference only.

### Historical Service Management

```bash
# These commands no longer work (service is masked):
sudo systemctl start influxdb     # ❌ DO NOT USE
sudo systemctl restart influxdb   # ❌ DO NOT USE
sudo systemctl stop influxdb      # ❌ DO NOT USE
```

**Why it was changed:**
- Port conflicts between systemd and Docker
- Inconsistent behavior across deployments
- Docker containers are more reproducible for racing

---

## DATA STRUCTURE (Still Valid)

### Organization
- **Org:** midnight_rider

### Buckets
- **signalk** — Time-series navigation data (1-10 Hz)
- **metrics** — System metrics (CPU, RAM, disk)
- **archive** — Historical race data (long-term storage)

### Data Retention
- **signalk:** 30 days (auto-purge after 30 days)
- **metrics:** 7 days
- **archive:** 1 year

### Key Measurements

**Navigation (from Signal K):**
```
navigation.position (lat, lon)
navigation.headingTrue (degrees)
navigation.speedThroughWater (knots)
navigation.speedOverGround (knots)
navigation.attitude (roll, pitch, yaw)
```

**Performance:**
```
performance.sails (jib%, main%)
performance.vmg (knots)
performance.windAngleApparent (degrees)
performance.windSpeedApparent (knots)
```

**Environmental:**
```
environment.water.waveHeight (meters)
environment.air.temperature (°C)
environment.water.temperature (°C)
```

---

## QUERIES (Still Valid)

### Get Latest Position
```bash
docker exec influxdb influx query '
from(bucket:"signalk")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "navigation" AND r._field == "position")
  |> last()
'
```

### Get Last Hour of Attitude
```bash
curl -X POST "http://localhost:8086/api/v2/query?org=MidnightRider" \
  -H "Authorization: Token ${INFLUX_TOKEN}" \
  -H "Content-type: application/vnd.flux" \
  -d 'from(bucket:"signalk")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "navigation")
    |> filter(fn: (r) => r._field == "roll" or r._field == "pitch" or r._field == "yaw")'
```

---

## TROUBLESHOOTING

**See:** `TROUBLESHOOTING.md` Section 6 (InfluxDB)

### Common Issues

**InfluxDB not responding:**
```bash
# Check if container is running
docker compose ps | grep influxdb

# Check logs for errors
docker compose logs influxdb --tail=50

# Restart
docker compose restart influxdb
```

**Data not arriving:**
```bash
# Check Signal K is writing
docker exec influxdb influx bucket list

# Verify plugin configuration
curl http://localhost:3000/skServer/plugins | grep influxdb
```

**Port 8086 in use by something else:**
```bash
# Find what's using it
lsof -i :8086

# Make sure native service is masked
sudo systemctl status influxdb  # Should show masked
```

---

## RELATED FILES

- `DOCKER-INFLUXDB-GRAFANA-STARTUP.md` — **Main reference**
- `TROUBLESHOOTING.md` — Section 6
- `docker-compose.yml` — Container definitions
- `.env` — Environment variables (token, etc.)

---

**Last Updated:** 2026-04-25  
**Status:** Docker containerized (systemd deprecated)

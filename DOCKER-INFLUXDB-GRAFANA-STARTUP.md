# Docker InfluxDB & Grafana — Startup Guide & Troubleshooting

**Status:** ✅ OPERATIONAL (2026-04-25 11:42 EDT)  
**Last Updated:** 2026-04-25  
**Author:** OC + Denis Lafarge

---

## QUICK START

```bash
cd /home/aneto/.openclaw/workspace

# Make sure native InfluxDB is NOT running
sudo systemctl stop influxdb 2>/dev/null

# Start containers
docker compose up -d influxdb grafana

# Verify
docker compose ps
curl http://localhost:8086/health  # Should return 200
curl http://localhost:3001/api/health  # Should return 200
```

---

## WHAT HAPPENED (2026-04-25 Diagnostic)

### Problem
InfluxDB and Grafana containers would not start because:
1. **Docker daemon:** ✅ Running
2. **docker-compose.yml:** ✅ Correct syntax
3. **Port 8086 conflict:** ❌ **ALREADY IN USE**

### Root Cause
**InfluxDB v2.8 was installed as a native systemd service** (not Docker).

```bash
# System process found:
PID 1651: /usr/bin/influxd

# This monopolized port 8086, preventing Docker container from binding
```

### Solution Applied
1. **Stop native InfluxDB service:**
   ```bash
   sudo systemctl stop influxdb
   ```

2. **Remove any orphaned containers:**
   ```bash
   docker compose down
   ```

3. **Start Docker containers fresh:**
   ```bash
   docker compose up -d influxdb grafana
   ```

4. **Verify both services are responding:**
   ```bash
   curl -s http://localhost:8086/health
   # Response: {"message":"ok","status":"ok"} ✅
   
   curl -s http://localhost:3001/api/health
   # Response: {"database":"ok","ok":true} ✅
   ```

---

## Why This Happened

**Root cause chain:**

1. **Original setup:** InfluxDB was installed system-wide via package manager
   - Created systemd service `/usr/lib/systemd/system/influxdb.service`
   - Auto-starts on boot
   - Listens on port 8086

2. **Later migration:** docker-compose.yml created to run InfluxDB + Grafana in containers
   - But **systemd service was never disabled**
   - Conflicts on port 8086 when containers tried to start

3. **Result:** 
   - `docker compose up` would fail silently
   - Native process kept running
   - Containers never started
   - check-system.sh would report "InfluxDB not responding"

---

## Configuration Status

### Current Setup (2026-04-25 11:42 EDT)

| Component | Type | Status | Port | Notes |
|-----------|------|--------|------|-------|
| **InfluxDB v2.8** | Docker container | ✅ RUNNING | 8086 | Responds HTTP 200 |
| **Grafana v12.3.1** | Docker container | ✅ RUNNING | 3001 | Responds HTTP 200 |
| **Signal K v2.25** | systemd native | ✅ RUNNING | 3000 | Separate service |
| **Native InfluxDB** | systemd service | ❌ STOPPED | - | Disabled to prevent conflicts |

### docker-compose.yml Configuration

```yaml
services:
  influxdb:
    image: influxdb:2.8
    container_name: influxdb
    restart: unless-stopped
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    environment:
      - INFLUX_TOKEN=${INFLUX_TOKEN}  # From .env file
      - INFLUX_ORG=MidnightRider
      - INFLUX_BUCKET=signalk

  grafana:
    image: grafana/grafana:12.3.1
    container_name: grafana
    restart: unless-stopped
    network_mode: host
    ports:
      - "3001:3001"
    volumes:
      - grafana-data:/var/lib/grafana
      - grafana-config:/etc/grafana
    environment:
      - GF_SERVER_HTTP_PORT=3001
    depends_on:
      - influxdb
```

---

## Startup Procedure (for Race Day or Field Test)

### Pre-Flight Check (T-60 minutes)

```bash
# 1. Verify no port conflicts
lsof -i :8086 || echo "Port 8086 available ✅"
lsof -i :3001 || echo "Port 3001 available ✅"

# 2. Ensure native InfluxDB is stopped
sudo systemctl stop influxdb
sudo systemctl disable influxdb  # (optional: prevent auto-start)

# 3. Load environment variables
cd /home/aneto/.openclaw/workspace
source .env

# 4. Start containers
docker compose up -d influxdb grafana

# 5. Verify all systems
docker compose ps
sleep 5
curl http://localhost:8086/health
curl http://localhost:3001/api/health
```

### Boot Sequence

**Expected boot order:**
1. Docker daemon (already running via systemd)
2. InfluxDB container (initializes, responds ~10 sec)
3. Grafana container (initializes, responds ~15 sec)
4. Signal K (running separately, unaffected)

**Total startup time:** ~30 seconds from `docker compose up -d`

### Verification

After startup, run:
```bash
# Full health check
/home/aneto/check-system.sh --full

# Should show:
# ✅ Signal K (systemctl)
# ✅ Signal K API (port 3000)
# ✅ InfluxDB (port 8086)
# ✅ Grafana (port 3001)
```

---

## Troubleshooting

### Symptom: "Address already in use :8086"

**Cause:** Native InfluxDB or another service listening

**Fix:**
```bash
# Find what's using port 8086
lsof -i :8086

# If it's /usr/bin/influxd (native):
sudo systemctl stop influxdb
sudo systemctl disable influxdb

# If it's something else, kill it:
sudo kill -9 <PID>

# Then retry:
docker compose up -d influxdb
```

### Symptom: Grafana not responding (HTTP 000)

**Cause:** Still initializing or port conflict

**Fix:**
```bash
# Wait 20 seconds for Grafana to fully boot
sleep 20

# Test again
curl http://localhost:3001/api/health

# Check logs
docker compose logs grafana
```

### Symptom: InfluxDB responding but no data

**Cause:** Signal K not configured to write to container, or token mismatch

**Fix:**
1. Verify .env file has valid INFLUX_TOKEN
2. Check Signal K config: `~/.signalk/settings.json`
3. Verify signalk-to-influxdb2 plugin is configured
4. Restart Signal K: `systemctl restart signalk`

---

## Important Notes

### Native InfluxDB vs Docker

- **Native (systemd):** Good for local dev, but not recommended for production
- **Docker:** Isolated, reproducible, recommended for race deployment

### Token Management

- InfluxDB token stored in `.env` (gitignored)
- Never commit `.env` to git
- Token is read via `${INFLUX_TOKEN}` in docker-compose.yml

### Signal K Integration

Signal K is **NOT** in docker-compose. It runs as systemd service:
```bash
systemctl status signalk
systemctl restart signalk
```

This is intentional — Signal K is the data hub, containers are storage/viz.

---

## Related Files

- **docker-compose.yml** — Container definitions
- **.env** — Environment variables (gitignored, contains tokens)
- **.env.example** — Template for .env
- **check-system.sh** — Automated health verification
- **SECURITY-TOKEN-DONE.md** — Token management guide

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Created: Documented port conflict issue + startup procedures | OC + Denis |
| 2026-04-25 | Fixed: Disabled native InfluxDB, migrated to Docker containers | OC |

---

**Last Status:** ✅ InfluxDB (200) + Grafana (200) OPERATIONAL  
**Next Check:** Before field test (May 19)

# Midnight Rider Navigation System — J/30

**Status:** ✅ Production-ready for Block Island Race (May 22, 2026)

---

## Quick Start

```bash
cd /home/aneto/.openclaw/workspace

# 1. Ensure native InfluxDB is masked
sudo systemctl status influxdb  # Should show "masked"

# 2. Start Docker containers (InfluxDB + Grafana)
docker compose up -d influxdb grafana

# 3. Verify
docker compose ps
curl http://localhost:8086/health      # Should return 200
curl http://localhost:3001/api/health  # Should return 200

# 4. Check Signal K
systemctl status signalk
curl http://localhost:3000/signalk/v1/api

# 5. Run diagnostic
./check-system.sh --full
```

---

## Architecture

| Component | Type | Port | Status |
|-----------|------|------|--------|
| **Signal K v2.25** | systemd service | 3000 | ✅ Native |
| **InfluxDB v2.8** | Docker container | 8086 | ✅ Containerized |
| **Grafana v12.3.1** | Docker container | 3001 | ✅ Containerized |

**Note:** Signal K runs as systemd. InfluxDB and Grafana run as Docker containers (NOT systemd).

---

## Hardware

- **Platform:** Raspberry Pi 4 (8GB RAM)
- **GPS:** Unicore UM982 GNSS
- **IMU:** WIT WT901BLECL (BLE)
- **Anemometer:** Calypso UP10 (optional)
- **NMEA 2000 Gateway:** YDNU-02
- **MFD:** Vulcan 7 FS

See: `docs/HARDWARE/` for datasheets

---

## Software Stack

### Plugins (Signal K)
- `signalk-um982-gnss` — GPS heading + position
- `signalk-wit-imu-ble` — Attitude (roll/pitch/yaw)
- `signalk-wave-analyzer-v1.1` — Wave height from IMU
- `signalk-sails-management-v2` — Jib/main recommendations
- `signalk-performance-polars` — J/30 polars + VMG

### Data Storage
- **InfluxDB** — Time-series database (Docker container)
- **Grafana** — Visualization dashboards (Docker container)

### AI Coaching (MCP Servers)
- Racing optimizer
- Crew communication
- Weather analysis
- Buoy data

See: `docs/SOFTWARE/` for guides

---

## Startup Procedure

### Before Leaving Dock (T-60 min)

```bash
# 1. Stop native InfluxDB (should already be masked)
sudo systemctl stop influxdb 2>/dev/null

# 2. Start Docker containers
cd /home/aneto/.openclaw/workspace
docker compose up -d influxdb grafana

# 3. Start Signal K (usually auto-starts)
sudo systemctl start signalk

# 4. Wait for initialization (~30 sec)
sleep 30

# 5. Run diagnostics
./check-system.sh --full

# Expected: GO FOR DEPLOYMENT (exit code 0 or 1)
# If exit code 2, see TROUBLESHOOTING.md
```

### Troubleshooting

See: `docs/OPERATIONS/TROUBLESHOOTING.md`

**If containers won't start:**
```bash
docker compose logs influxdb | tail -20
docker compose logs grafana | tail -20

# Common issue: Native InfluxDB still running
lsof -i :8086
sudo systemctl stop influxdb
sudo systemctl mask influxdb
docker compose up -d influxdb
```

---

## Documentation

- **`docs/ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md`** — Complete system architecture
- **`docs/OPERATIONS/`** — Field test, race day, troubleshooting checklists
- **`docs/HARDWARE/`** — Sensor datasheets and specs
- **`docs/INTEGRATION/`** — Hardware-software integration guides
- **`docs/SOFTWARE/`** — Signal K plugins, InfluxDB, Grafana setup
- **`DOCKER-INFLUXDB-GRAFANA-STARTUP.md`** — Docker container management
- **`MEMORY.md`** — Recent lessons and fixes

---

## Key Files

```
/home/aneto/.openclaw/workspace/
├── docker-compose.yml          # InfluxDB + Grafana definition
├── .env                         # Environment variables (token, etc.)
├── check-system.sh              # Pre-race diagnostic script
├── scripts/                     # Operational scripts
├── docs/                        # Professional documentation
├── mcp/                         # AI coaching servers
└── regatta/                     # Race management tools
```

---

## Environment Variables

Create `.env` file (git-ignored):

```bash
INFLUX_TOKEN=your_secure_token_here
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk
```

See: `SECURITY-TOKEN-DONE.md` for token management

---

## Testing

**Before field test (May 19):**
```bash
./check-system.sh --full
```

**On race day (May 22):**
```bash
# T-60 min
./check-system.sh --full

# T-15 min
./check-system.sh --quick
```

---

## Race Day Commands

```bash
# Start system (T-60)
sudo systemctl stop influxdb
docker compose up -d influxdb grafana

# Enable race mode
./race-mode.sh

# Monitor during race
./check-system.sh --watch

# Export data after race
./race-debrief.sh
```

---

## Support

- **Troubleshooting:** See `docs/OPERATIONS/TROUBLESHOOTING.md`
- **Field test:** See `docs/OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md`
- **Race day:** See `docs/OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md`
- **Architecture:** See `docs/ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md`

---

## Version

- **v1.0** — 2026-04-25 — Production-ready for May 22 Block Island Race
  - Docker containerized deployment
  - 5 Signal K plugins
  - 7 MCP AI servers
  - Professional documentation suite
  - Full diagnostics and troubleshooting guides

---

**Status:** ✅ Ready for deployment  
**Last Updated:** 2026-04-25 12:02 EDT  
**For:** Denis Lafarge, J/30 Midnight Rider crew

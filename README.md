# Midnight Rider ⛵

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Boat: J/30 #511](https://img.shields.io/badge/Boat-J%2F30%20%23511-blue)
![Race: Block Island 2026](https://img.shields.io/badge/Race-Block%20Island%202026-red)
![Status: Production](https://img.shields.io/badge/Status-Production-green)

> Open-source marine racing instrumentation system for a J/30 sailboat.
> Real-time navigation data, performance analytics, and AI race coaching —
> running on a Raspberry Pi 4 aboard the sailing vessel *Midnight Rider*.

**Block Island Race 2026 — 186 nm, 15+ hours — ✅ COMPLETE**

---

## 📖 How to Read This Repo

This README gives you an **end-to-end map** of the system. Use the layers:

| Layer | Where to start |
|-------|---------------|
| 🗺️ **Architecture** (full design) | [`docs/ARCHITECTURE-MASTER.md`](docs/ARCHITECTURE-MASTER.md) |
| ⚡ **Quick system status** | [`docs/SYSTEM-SUMMARY.md`](docs/SYSTEM-SUMMARY.md) |
| 🔌 **Hardware specs** | [`docs/HARDWARE/`](docs/HARDWARE/) |
| 🔧 **Component integration** | [`docs/INTEGRATION/`](docs/INTEGRATION/) |
| 🧩 **Plugin development** | [`plugins/PLUGIN-DEVELOPMENT-GUIDE.md`](plugins/PLUGIN-DEVELOPMENT-GUIDE.md) |
| 🚨 **Recovery / ops** | [`docs/ops/RECOVERY-GUIDE-SAFE.md`](docs/ops/RECOVERY-GUIDE-SAFE.md) |
| 📚 **Full doc index** | [`docs/INDEX.md`](docs/INDEX.md) |

---

## ⚡ What It Does

**Midnight Rider** is a complete, self-contained navigation and race analytics system:

- 🛰️ **True heading** from dual-antenna GNSS (not a compass)
- 🌊 **Real-time wave height** from IMU acceleration with heel correction
- 💨 **Wind performance** vs. polar diagrams (ORC VPP data)
- 📐 **Leeway, current, VMG** calculated by custom Signal K plugins
- 📊 **13 Grafana dashboards** live on iPad via mDNS
- 🤖 **AI race coaching** via Claude + 10 MCP server tools
- 🔋 **Battery monitoring** (LiFePO4 BMS via Bluetooth)
- 📡 **NMEA 2000 output** back to Vulcan 7 MFD chartplotter

---

## 🗺️ Data Pipeline

```
INSTRUMENTS (9)    PROCESSING       STORAGE / DISPLAY
───────────────    ──────────────   ──────────────────
UM982 GNSS (USB) ──┐
WIT IMU (BLE) ──┤
Calypso UP10(BLE)──┤ Signal K :3000 ── InfluxDB :8086 (Docker)
B&G WS320 (N2K) ──┤                   │
YDNU-02 (N2K) ──┤ ├─ Plugins P1–P5  ├─ Grafana :3001 (13 dashboards)
AIS700 (N2K) ──┤ │                   │
Vulcan 7 (N2K) ──┤ └─ YDNU-02 ────── NMEA 2000 output
SOK BMS (BLE) ──┘    (N2K gateway)
```

**Absolute Rule:** Signal K = `systemctl` ONLY — never `docker compose`

---

## 🏗️ Repository Structure

```
midnightrider-navigation/
│
├── 📄 README.md ← You are here
├── 📄 docker-compose.yml ← InfluxDB + Grafana (Docker)
├── 📄 .env.example ← Config template (never commit .env.local)
│
├── 📁 ble/ ← BLE device drivers (Python)
│ ├── wit-ble-direct.py ← WIT IMU — 10 Hz attitude (PRODUCTION)
│ ├── calypso_direct.py ← Calypso UP10 anemometer — 4 Hz (PRODUCTION)
│ ├── sok_direct.py ← SOK BMS battery monitor (PRODUCTION)
│ └── ble_common.py ← Shared BLE infrastructure
│
├── 📁 plugins/ ← Signal K plugins (Node.js)
│ ├── signalk-heading-true-calculator.js ← P1: GPS heading
│ ├── signalk-j30-leeway.js ← P2: Leeway angle
│ ├── signalk-current-calculator.js ← P3: Ocean current
│ ├── signalk-truewind-calculator.js ← P4: True wind
│ ├── signalk-n2k-bridge.js ← P5: SK → N2K output
│ ├── signalk-astronomical.js ← Sun/moon data
│ ├── signalk-um982-gnss.js ← GNSS serial driver
│ └── n2k-conversions/ ← N2K PGN conversion modules
│
├── 📁 mcp/ ← AI integration (Claude MCP servers)
│ ├── race-server.js ← Race data & tactics
│ ├── polar-server.js ← Polar performance analysis
│ ├── electrical-server.js ← Battery monitoring
│ ├── imu-server.js ← Motion data
│ ├── weather-server.js ← Weather data
│ ├── competitor-server.js ← AIS fleet tracking
│ ├── crew-server.js ← Watch management
│ ├── buoy-server.js ← Mark data
│ ├── astronomical-server.js ← Sun/moon/tide data
│ └── racing-server.js ← Racing metrics
│
├── 📁 grafana-dashboards/ ← 13 dashboard JSON files (00–12)
├── 📁 grafana-provisioning/ ← Datasources + alerting
├── 📁 config/ ← Configuration files
├── 📁 etc/systemd/system/ ← Systemd services
├── 📁 portal/ ← iPad web portal (Flask)
├── 📁 scripts/ ← Utility scripts
├── 📁 data/polars/ ← J30 ORC VPP polar data
├── 📁 docs/ ← Full documentation (start here)
│ ├── ARCHITECTURE-MASTER.md ← ⭐ CANONICAL system design
│ ├── SYSTEM-SUMMARY.md ← 1-page operational reference
│ ├── INDEX.md ← Documentation map
│ └── HARDWARE/, INTEGRATION/, ops/ ← Guides
│
└── 📁 logs/ ← Execution journals
 ├── latest.json ← Last session status
 ├── oc-actions.log ← Detailed action log
 └── debug/ ← Error reports
```

---

## 🔌 Stack at a Glance

| Service | Port | Manager | Status |
|---------|------|---------|--------|
| Signal K v2.25 | 3000 | systemctl | ✅ LIVE |
| InfluxDB 2.8 | 8086 | Docker | ✅ LIVE |
| Grafana 12.3.1 | 3001 | Docker | ✅ LIVE |
| Portal (Flask) | 8888 | systemctl | ✅ LIVE |
| Regatta Server | 5000 | Docker | ✅ LIVE |

Access (on local network via mDNS):
- Grafana: http://MidnightRider.local:3001
- Signal K: http://MidnightRider.local:3000
- Portal: http://MidnightRider.local:8888

---

<details>
<summary>📡 Instruments (9 total) — click to expand</summary>

| # | Instrument | Model | Protocol | Role |
|---|-----------|-------|----------|------|
| 1 | GPS + Heading | Unicore UM982 | USB serial | Position, true heading (±0.5°), SOG, COG |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE | Roll, pitch, acceleration @ 10 Hz |
| 3 | Wind masthead | Calypso UP10 | Bluetooth LE | Apparent/true wind + air temp @ 4 Hz |
| 4 | Wind masthead (N2K) | B&G WS320 | NMEA 2000 | Apparent wind → Vulcan 7 direct |
| 5 | N2K Gateway | Yacht Devices YDNU-02 | USB + NMEA 2000 | Bridge Signal K ↔ N2K |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | Helm display + secondary GPS |
| 7 | Battery | SOK SK12V100PC LiFePO4 | Bluetooth LE | BMS (SoC, cells, temp) |
| 8 | Barometer | Yacht Devices YDBC-05 | NMEA 2000 | Atmospheric pressure |
| 9 | AIS Transponder | B&G AIS700 Class B | NMEA 2000 | AIS TX/RX + fleet tracking |

BLE drivers: all publish to Signal K via UDP:4123 (delta format).
Shared infrastructure: `ble/ble_common.py` (reconnect, logging, locks).

</details>

---

<details>
<summary>🧩 Signal K Plugins (P1–P5) — click to expand</summary>

Custom plugins extend Signal K with derived navigation data:

| ID | Plugin | Version | Output | Status |
|----|--------|---------|--------|--------|
| P1 | signalk-heading-true-calculator | v1.0.6 | navigation.headingTrue | ✅ Active |
| P2 | signalk-j30-leeway | v1.0.4 | performance.leewayAngle | ✅ Active |
| P3 | signalk-current-calculator | v1.0.4 | environment.current.* | ✅ Active |
| P4 | signalk-truewind-calculator | v1.0.1 | environment.wind.angleTrueGround | ✅ Active |
| P5 | signalk-n2k-bridge | v1.0.1 | N2K PGN output → Vulcan 7 | ✅ Active |
| — | signalk-um982-gnss | v2.0.0 | GNSS position + heading | ✅ Active |
| — | signalk-astronomical | v1.0.0 | Sun/moon altitude | ✅ Active |
| — | signalk-wave-analyzer | v2.0.0 | Wave spectrum | ✅ Active |

Full inventory: `docs/SIGNALK-PLUGINS-INVENTORY.md`

</details>

---

<details>
<summary>📊 Grafana Dashboards (13 total, 00–12) — click to expand</summary>

| ID | Name | Purpose | Refresh |
|----|------|---------|---------|
| 00 | System Status | RPi health, services, uptime | 30s |
| 01 | Cockpit | Heading, SOG, COG, heel/pitch | 5s |
| 02 | Environment | Wind, pressure, temp, waves | 10s |
| 03 | Performance | Polars, VMG, ORC efficiency | 5s |
| 04 | Wind & Current | Tactical shifts + current vector | 10s |
| 05 | Competitive | Fleet tracking (AIS) | 30s |
| 06 | Electrical | SOK BMS — SoC, cells, temp | 30s |
| 07 | Race Enriched | Race-specific metrics | 5s |
| 08 | Alerts | 60+ alert rules | 10s |
| 09 | Crew | Watch rotation, fatigue | 30s |
| 10 | LIS Wind | Long Island Sound data | 5m |
| 11 | Astronomical | Sun/moon altitude, tides | 5m |
| 12 | Alerts Filtered | Active alert summary | 30s |

Dashboard JSON files: `grafana-dashboards/`

</details>

---

<details>
<summary>🤖 AI Integration (Claude + MCP) — click to expand</summary>

10 MCP (Model Context Protocol) servers expose Midnight Rider data to Claude:

- **race-server** — Race state, marks, times, VMG
- **polar-server** — Performance vs. ORC polars
- **electrical-server** — Battery SoC, power
- **imu-server** — Motion, heel, pitch, wave height
- **weather-server** — Wind trends, pressure, forecasts
- **competitor-server** — AIS fleet positions
- **crew-server** — Watch schedule, fatigue
- **buoy-server** — Mark positions & vectors
- **astronomical-server** — Sun/moon/tide data
- **racing-server** — Race tactics & metrics

See `mcp/README.md` for setup.

</details>

---

## ⚙️ Quick Start

```bash
# 1. Clone
git clone https://github.com/Aneto152/midnightrider-navigation.git
cd midnightrider-navigation

# 2. Configure
cp .env.example .env.local
nano .env.local  # Fill in InfluxDB token, Grafana password

# 3. Create Docker volumes (first time only)
docker volume create influxdb-data
docker volume create grafana-data

# 4. Start InfluxDB + Grafana
docker compose up -d influxdb grafana

# 5. Start Signal K (systemctl — NEVER docker)
sudo systemctl start signalk

# 6. Verify
curl http://localhost:3000/signalk/v1/api  # Signal K ✅
curl http://localhost:8086/health          # InfluxDB ✅
curl http://localhost:3001/api/health      # Grafana ✅
```

For full installation on a fresh Raspberry Pi:
```bash
bash scripts/install-midnight-rider.sh
```

---

## 🔑 Configuration

Copy `.env.example` → `.env.local` and set:

```bash
INFLUXDB_TOKEN=<your-token>      # InfluxDB read/write token
INFLUXDB_ORG=midnight-rider      # Organization name
INFLUXDB_BUCKET=midnight-rider   # Data bucket
GRAFANA_PASSWORD=<admin-password> # Grafana admin password
```

⚠️ Never commit `.env.local` to git. It is in .gitignore.

---

## 🏁 Production Status

| Event | Date | Result |
|-------|------|--------|
| Initial deployment | 2026-05-10 | ✅ |
| Field test | 2026-05-19 | ✅ |
| Block Island Race | 2026-05-22 | ✅ 186 nm, 15+ hours |
| Repository cleanup | 2026-06-15 | ✅ |

Current version: `docs/ARCHITECTURE-MASTER.md` v5.1 — canonical reference.

---

## 📜 License

MIT — see LICENSE

---

**Last updated:** 2026-06-15 | **Status:** Production Ready ⛵

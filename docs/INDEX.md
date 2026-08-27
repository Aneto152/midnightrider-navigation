# Midnight Rider Documentation Index

Complete reference guide for the Midnight Rider navigation system.

---

## 📚 Quick Navigation

### Getting Started
- **[README](../README.md)** — Project overview & quick start
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — How to contribute

### System Architecture
- **[docs/ARCHITECTURE-MASTER.md](docs/ARCHITECTURE-MASTER.md)** — Full system design
- **[System Summary](SYSTEM-SUMMARY.md)** — High-level overview

---

## 🔧 Hardware Documentation

### Datasheets & Integration

| Device | Datasheet | Integration Guide |
|--------|-----------|-------------------|
| **Unicore UM982** | [HARDWARE/UM982-GNSS-DATASHEET.md](HARDWARE/UM982-GNSS-DATASHEET.md) | [INTEGRATION/UM982-INTEGRATION-GUIDE.md](INTEGRATION/UM982-INTEGRATION-GUIDE.md) |
| **WIT WT901BLECL** | [HARDWARE/WIT-WT901BLECL-DATASHEET.md](HARDWARE/WIT-WT901BLECL-DATASHEET.md) | [INTEGRATION/WIT-INTEGRATION-GUIDE.md](INTEGRATION/WIT-INTEGRATION-GUIDE.md) |
| **Calypso UP10** | [HARDWARE/CALYPSO-UP10-DATASHEET.md](HARDWARE/CALYPSO-UP10-DATASHEET.md) | [INTEGRATION/CALYPSO-UP10-INTEGRATION-GUIDE.md](INTEGRATION/CALYPSO-UP10-INTEGRATION-GUIDE.md) |
| **SOK 12V 100Ah** | [HARDWARE/SOK-BMS-BLE-PROTOCOL.md](HARDWARE/SOK-BMS-BLE-PROTOCOL.md) | [INTEGRATION/SOK-BMS-INTEGRATION.md](INTEGRATION/SOK-BMS-INTEGRATION.md) |
| **Vulcan 7 FS (×2)** | [HARDWARE/AIRMAR-DST810-DATASHEET.md — Loch + sonde + temp eau (N2K)
- `VULCAN-7-FS-DATASHEET.md`](HARDWARE/VULCAN-7-FS-DATASHEET.md) | [INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md](INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md) |
| **Raspberry Pi 4** | [HARDWARE/RASPBERRY-PI4-DATASHEET.md](HARDWARE/RASPBERRY-PI4-DATASHEET.md) | — |
| **YDNU-02 Gateway** | [HARDWARE/YDNU-02-DATASHEET.md](HARDWARE/YDNU-02-DATASHEET.md) | [INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md](INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md) |
| **YDBC-05 Barometer** | [HARDWARE/YDBC-05-DATASHEET.md](HARDWARE/YDBC-05-DATASHEET.md) | [INTEGRATION/YDBC-05-INTEGRATION-GUIDE.md](INTEGRATION/YDBC-05-INTEGRATION-GUIDE.md) |
| **B&G WS320** | [HARDWARE/BG-WS320-DATASHEET.md](HARDWARE/BG-WS320-DATASHEET.md) | [INTEGRATION/WS320-N2K-INTEGRATION-GUIDE.md](INTEGRATION/WS320-N2K-INTEGRATION-GUIDE.md) |
| **AIS700 Class B** | [HARDWARE/AIS700-DATASHEET.md](HARDWARE/AIS700-DATASHEET.md) | [INTEGRATION/AIS700-INTEGRATION-GUIDE.md](INTEGRATION/AIS700-INTEGRATION-GUIDE.md) |

---

## 🌐 N2K Network Architecture (SSOT)

> **📌 Single Source of Truth** for NMEA 2000 bus design, topology, and system PGN flows.

- **[N2K-NETWORK-ARCHITECTURE.md](INTEGRATION/N2K-NETWORK-ARCHITECTURE.md)** — Complete system-level reference
  - Network topology (7 devices, 7 LEN / 50 max)
  - PGN flow matrix (N2K ↔ Signal K)
  - YDNU-02 bridge configuration
  - Data source priorities
  - Failure modes & troubleshooting

- **[SK-TO-N2K-BRIDGE.md](INTEGRATION/SK-TO-N2K-BRIDGE.md)** — Signal K → NMEA 2000 plugin details
  - signalk-to-nmea2000 plugin (v2.24.0, Plugin ID: `sk-to-nmea2000`)
  - 7 active conversions (TRUE_HEADING, WINDv2, WIND_TRUE_GROUND, WIND_TRUE, ATTITUDE, LEEWAY, SetDrift)
  - Heading & wind data flows (critical paths)
  - Plugin configuration & troubleshooting

---

## 💻 Software Documentation

### Configuration & Setup

| Topic | File |
|-------|------|
| **Signal K Configuration** | [SOFTWARE/SIGNAL-K-CONFIGURATION.md](SOFTWARE/SIGNAL-K-CONFIGURATION.md) |
| **InfluxDB Setup** | [SOFTWARE/INFLUXDB-SETUP.md](SOFTWARE/INFLUXDB-SETUP.md) |
| **Grafana Dashboards** | [SOFTWARE/GRAFANA-DASHBOARDS.md](SOFTWARE/GRAFANA-DASHBOARDS.md) |
| **Plugins Catalog** | [SOFTWARE/PLUGINS-CATALOG.md](SOFTWARE/PLUGINS-CATALOG.md) |
| **Scripts Catalog** | [SOFTWARE/SCRIPTS-CATALOG.md](SOFTWARE/SCRIPTS-CATALOG.md) |
| **Wave Analyzer v1.1** | [SOFTWARE/WAVE-ANALYZER-V1.1-GUIDE.md](SOFTWARE/WAVE-ANALYZER-V1.1-GUIDE.md) |

### Race Reporting (MediaMan)

- **[TELEGRAM-REPORTER-INTEGRATION-GUIDE.md](INTEGRATION/TELEGRAM-REPORTER-INTEGRATION-GUIDE.md)** — Telegram outbound reporter (foundation phase)
  - DRY-RUN validated, production blocked
  - SQLite delivery state machine
  - One-way outbound only (no inbound)
  - Setup & activation procedures

---

## 🚤 Integration Guides

Complete step-by-step integration for each hardware component:

| Component | Guide |
|-----------|-------|
| **UM982 GNSS** | [INTEGRATION/UM982-INTEGRATION-GUIDE.md](INTEGRATION/UM982-INTEGRATION-GUIDE.md) |
| **WIT IMU (BLE)** | [INTEGRATION/WIT-INTEGRATION-GUIDE.md](INTEGRATION/WIT-INTEGRATION-GUIDE.md) |
| **Calypso Anemometer** | [INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md](INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md) |
| **SOK Battery BMS** | [INTEGRATION/SOK-BMS-INTEGRATION.md](INTEGRATION/SOK-BMS-INTEGRATION.md) |
| **Vulcan 7 FS MFD** | [INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md](INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md) |
| **YDNU-02 Gateway** | [INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md](INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md) |
| **YDBC-05 Barometer** | [INTEGRATION/YDBC-05-INTEGRATION-GUIDE.md](INTEGRATION/YDBC-05-INTEGRATION-GUIDE.md) |
| **WS320 N2K** | [INTEGRATION/WS320-N2K-INTEGRATION-GUIDE.md](INTEGRATION/WS320-N2K-INTEGRATION-GUIDE.md) |
| **AIS700 N2K** | [INTEGRATION/AIS700-INTEGRATION-GUIDE.md](INTEGRATION/AIS700-INTEGRATION-GUIDE.md) |

---

## 🎯 Operations & Checklists

### Pre-Race & Deployment

| Checklist | File |
|-----------|------|
| **Field Test (May 19)** | [OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md](OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md) |
| **Race Day (May 22)** | [OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md](OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md) |
| **System Health Check** | [OPERATIONS/CHECK-SYSTEM-QUICK-REFERENCE.md](OPERATIONS/CHECK-SYSTEM-QUICK-REFERENCE.md) |
| **Troubleshooting** | [OPERATIONS/TROUBLESHOOTING.md](OPERATIONS/TROUBLESHOOTING.md) |

---

## 📊 Dashboards & Alerts

### Dashboard Suite

- **DASHBOARDS-README.md** — Complete 9-dashboard reference with UIDs, refresh rates, access methods



- **[GRAFANA-DASHBOARDS.md](SOFTWARE/GRAFANA-DASHBOARDS.md)** — 16 dashboards reference
  - COCKPIT (main navigation)
  - ENVIRONMENT (sea & weather)
  - PERFORMANCE (speed analysis)
  - WIND & CURRENT (tactical)
  - COMPETITIVE (fleet tracking)
  - ELECTRICAL (power management)
  - RACE (race-specific)
  - ALERTS (60+ alert rules)
  - CREW (watch management)

### Alert Rules (65 Total)

Alert categories:
- **Safety:** Heel, pitch, temperature, voltage, system failures
- **Performance:** VMG, polars, sail trim, waves, current
- **Weather/Sea:** Wind shifts, pressure, swell, humidity
- **Systems:** Battery, charger, comms, GPS, storage
- **Racing:** Mark rounding, start line, finish, fleet position
- **Crew:** Watch duration, rest, fatigue tracking

---



---


---

## 🌐 Portal (port 8888)

Main web interface — serves HTML pages and proxies API calls.

| File | Route | Description |
|------|-------|-------------|
| **[portal/README.md](../portal/README.md)** | — | Portal documentation |
| `portal/server.py` | — | HTTP server: threaded, proxy, security |
| `portal/index.html` | `/` | Dashboard grid |
| `portal/viewer.html` | `/viewer.html?dashboard=X` | Grafana iframe |
| `portal/reporter.html` | `/reporter` | Family flash generator |
| `portal/static/css/night-mode.css` | `/static/css/night-mode.css` | Shared CSS |

## ⚙️ System Configuration Backup

Reference copies of all RPi system configuration files.

| File | Live path | Purpose |
|------|-----------|---------|
| **[config/README.md](../config/README.md)** | — | Inventory + sync/restore procedures |
| `config/docker-daemon.json` | `/etc/docker/daemon.json` | Docker data root |
| `config/grafana-custom.ini` | Docker volume | Grafana: iframes + 1s refresh |
| `config/signalk-package.json` | `.signalk/package.json` | Installed SK plugins |
| `config/signalk-to-influxdb2.json` | SK plugin-config/ | InfluxDB config (token via env) |
| `config/ufw-rules.txt` | Reference only | Firewall rules snapshot |
| `config/signalk/settings-sanitized.json` | `.signalk/settings.json` | SK settings (sanitized) |
| `config/system/avahi-daemon.conf` | `/etc/avahi/avahi-daemon.conf` | mDNS → midnightrider.local |
| `config/system/dhcpcd.conf` | `/etc/dhcpcd.conf` | Static IP on eth0 |
| `config/system/hostname` | `/etc/hostname` | Hostname: midnightrider |
| `config/system/hosts` | `/etc/hosts` | Local DNS |
| `config/system/rfkill-wifi-block.sh` | `/usr/local/bin/` | Disable WiFi at boot |
| `config/system/90-NM-*.yaml` | NetworkManager/ | Static IP profile |

## 🔐 Security & Configuration

### Configuration

- **[.env.example](../.env.example)** — Configuration template (no secrets)
- **[LICENSE](../LICENSE)** — MIT License

### Best Practices

- Never commit `.env.local` (it's in `.gitignore`)
- Use `.env.example` as your template
- Rotate tokens every 90 days
- Enable 2FA on Grafana admin account

---

## 🌊 Hardware Integration Procedures

### Step-by-Step Guides

1. **UM982 GNSS Setup** → [INTEGRATION/UM982-INTEGRATION-GUIDE.md](INTEGRATION/UM982-INTEGRATION-GUIDE.md)
2. **WIT IMU via BLE** → [INTEGRATION/WIT-INTEGRATION-GUIDE.md](INTEGRATION/WIT-INTEGRATION-GUIDE.md)
3. **Calypso Wind** → [INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md](INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md)
4. **SOK Battery Monitor** → [HARDWARE/SOK-BMS-BLE-PROTOCOL.md](HARDWARE/SOK-BMS-BLE-PROTOCOL.md)
5. **Vulcan 7 FS NMEA2000** → [INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md](INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md)

---

## 📱 iPad Portal & Dashboard Access

- **Portal HTML:** `dashboard-portal.html` (landing page)
- **Viewer:** `dashboard.html` (individual dashboards)
- **Guide:** [DASHBOARD-PORTAL-GUIDE.md](DASHBOARD-PORTAL-FINAL.md)

### Access Methods

- **Desktop:** http://localhost:3001 (Grafana)
- **iPad WiFi:** http://MidnightRider.local:8888 (Portal)
- **Portal Landing:** 16 dashboard buttons
- **Kiosk Mode:** Full-screen with no menus

---

## 🚀 Development & Contributing

- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — How to contribute
- **[README.md](../README.md)** — Project overview

---

## 📖 File Organization

```
docs/
├── INDEX.md (this file)
├── docs/ARCHITECTURE-MASTER.md
├── SYSTEM-SUMMARY.md
├── SYSTEM-CHECKLIST.md
├── HARDWARE/
│   ├── UM982-GNSS-DATASHEET.md
│   ├── WIT-WT901BLECL-DATASHEET.md
│   ├── CALYPSO-UP10-DATASHEET.md
│   ├── SOK-BMS-BLE-PROTOCOL.md
│   ├── VULCAN-7-FS-DATASHEET.md
│   ├── RASPBERRY-PI4-DATASHEET.md
│   └── YDNU-02-GATEWAY-DATASHEET.md
├── INTEGRATION/
│   ├── UM982-INTEGRATION-GUIDE.md
│   ├── WIT-INTEGRATION-GUIDE.md
│   ├── CALYPSO-INTEGRATION-GUIDE.md
│   ├── VULCAN-SIGNALK-INTEGRATION.md
│   ├── YDNU-02-INTEGRATION-GUIDE.md
│   └── INTEGRATION-INDEX.md
├── SOFTWARE/
│   ├── SIGNAL-K-CONFIGURATION.md
│   ├── INFLUXDB-SETUP.md
│   ├── GRAFANA-DASHBOARDS.md
│   ├── PLUGINS-CATALOG.md
│   ├── SCRIPTS-CATALOG.md
│   └── WAVE-ANALYZER-V1.1-GUIDE.md
└── OPERATIONS/
    ├── FIELD-TEST-CHECKLIST-2026-05-19.md
    ├── RACE-DAY-CHECKLIST-2026-05-22.md
    ├── CHECK-SYSTEM-QUICK-REFERENCE.md
    └── TROUBLESHOOTING.md
```

---

## 🎯 Where to Start

1. **New to the project?** Start with [README.md](../README.md)
2. **Setting up hardware?** Go to [INTEGRATION/](INTEGRATION/)
3. **Running the system?** Check [OPERATIONS/](OPERATIONS/)
4. **Understanding architecture?** Read [docs/ARCHITECTURE-MASTER.md](docs/ARCHITECTURE-MASTER.md)
5. **Need help?** See [OPERATIONS/TROUBLESHOOTING.md](OPERATIONS/TROUBLESHOOTING.md)

---

**Last updated:** 2026-06-15  
**Status:** ✅ Production v1.0 — All phases A-E complete, SSOT enforced

---

## 🧭 AIS Competitor Tracker

| File | Role |
|------|------|
| **[ais/README.md](../ais/README.md)** | Module documentation |
| `ais/ais_lib.py` | Math: haversine, bearing, TWA, VMG, delta, color |
| `ais/competitors_db.py` | CompetitorDB: load/enrich/search, TTL 5min |
| `ais/ais_watch.py` | Daemon: SK → InfluxDB every 30s |
| `ais/server_handlers.py` | API: `/api/competitors` + `/api/fleet_db` |

**| `ais/tracker.html` | Live competitor tracker UI — accessible at `/ais/` on portal |
| `ais/fleet_db.html` | Fleet database browser — accessible at `/ais/fleet_db` on portal |

Unit tests:** `tests/test_ais_lib.py` (34) · `tests/test_competitors_db.py` (23) · `tests/test_server_handlers.py` (18) · `tests/test_ais_html.py` (35) — **110 total**

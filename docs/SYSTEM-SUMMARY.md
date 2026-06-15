# MIDNIGHT RIDER SYSTEM — 1-PAGE SUMMARY

**Version:** 2.1 | **Date:** 2026-06-14 | **Status:** ✅ Production (Block Island Race 2026-05-22 COMPLETE)

---

## WHAT IS MIDNIGHT RIDER?

Advanced J/30 yacht racing system with real-time data analytics:
- **GPS:** Dual-antenna heading (±0.5°) — Unicore UM982
- **IMU:** 9-axis motion sensor (roll, pitch, heading @ 10 Hz) — WIT WT901BLECL via BLE
- **Wind:** Calypso UP10 anemometer via BLE (true + apparent wind)
- **Processing:** Signal K v2.25 hub + custom plugins (on RPi 4)
- **Display:** B&G Vulcan 7 FS MFD (NMEA 2000)
- **Dashboards:** Grafana (13 custom dashboards, real-time iPad display)
- **Data:** InfluxDB time-series logging (race replay capability)
- **AI:** 7+ MCP servers for Claude (tactical decisions)

**Key Innovation:** Real-time wave height from IMU acceleration with heel correction (fixes 14% error at 30° heel)

---

## HARDWARE STACK

| Component | Model | Purpose |
|-----------|-------|---------|
| GPS | Unicore UM982 | Position + true heading (dual antenna) |
| IMU | WitMotion WT901BLECL | Roll/pitch/heading/accel (10 Hz, BLE) |
| Anemometer | Calypso UP10 | Wind speed/direction (BLE) |
| Gateway | Yacht Devices YDNU-02 | Signal K → NMEA 2000 bridge |
| Computer | Raspberry Pi 4 | Runs Signal K hub (midnightrider.local) |
| Display | B&G Vulcan 7 FS | NMEA 2000 MFD (heel, wind, polars) |
| Power | SOK SK12V100PC | House battery with BLE BMS |

---

## SOFTWARE STACK

| Layer | Component | Port | Manager | Status |
|-------|-----------|------|---------|--------|
| Hub | Signal K v2.25 | 3000 | systemctl | ✅ LIVE |
| BLE IMU | wit-ble-direct.py | — | systemctl | ✅ LIVE |
| BLE Wind | calypso_direct.py | — | systemctl | ✅ LIVE |
| Database | InfluxDB | 8086 | Docker | ✅ LIVE |
| Dashboard | Grafana | 3001 | Docker | ✅ LIVE |
| Race | Regatta server | 5000 | Docker | ✅ LIVE |
| Portal | Portal HTML | 8888 | systemctl | ✅ LIVE |
| AI | 7 MCP servers | — | — | ✅ READY |

**Absolute Rule:** Signal K = systemctl ONLY — NEVER docker compose

---

## BLE DRIVERS (Current Architecture — 2026-05-30)

| File | Device | MAC | Service | Status |
|------|--------|-----|---------|--------|
| ble/wit-ble-direct.py | WIT WT901BLECL | E9:10:DB:8B:CE:C7 | wit-ble-direct | ✅ Active |
| ble/calypso_direct.py | Calypso UP10 | F8:5F:12:9D:D2:EE | calypso_direct | ✅ Active |
| ble/sok_direct.py | SOK BMS | TBD (discovery pending) | manual | 🟡 Ready |
| ble/ble_common.py | Shared infrastructure | — | — | ✅ Module |

**All drivers:** Publish to Signal K via UDP:4123 (delta format)

**Shared Infrastructure (ble_common.py):**
- `setup_logger()` — RotatingFileHandler (5MB max, 3 backups)
- `acquire_singleton()` / `release_singleton()` — PID file locking
- `publish_delta()` — UDP:4123 → Signal K
- `check_ble_adapter()` — hci0 availability
- `check_sk_reachable()` — Signal K HTTP health
- `bt_recovery()` — bluetoothctl zombie cleanup
- `setup_signal_handlers()` — graceful SIGTERM/SIGINT

---

## DATA FLOW (SIMPLIFIED)

```
BLE SENSORS (WIT + Calypso)
    ↓ (via wit-ble-direct.py & calypso_direct.py)
    ↓ (UDP:4123 delta format)
SIGNAL K HUB (localhost:3000)
    ├── InfluxDB (docker) → Grafana (dashboard)
    ├── YDNU-02 gateway → NMEA 2000 → Vulcan 7 MFD
    └── MCP servers (AI/Claude integration)
```

---

## DASHBOARDS (13 Total)

| ID | Name | Purpose |
|----|------|---------|
| **00** | System Status | RPi health, services, uptime |
| **01** | Cockpit | Heading, SOG, COG, roll/pitch |
| **02** | Environment | Wind, pressure, temperature, waves |
| **11** | Astronomical | Sun/moon altitude, tides |
| **03** | Performance | Polars, VMG, efficiency |
| **12** | Alerts Filtered | Active alert rules |
| **04** | Wind & Current | Tactical analysis |
| **05** | Competitive | Fleet tracking (AIS) |
| **06** | Electrical | SOK BMS — SoC, cells, temperature |
| **07** | Race Enriched | Race-specific metrics (not used 2026-05-22) |
| **08** | Alerts | 60+ alert rules (comprehensive) |
| **09** | Crew | Watch rotation, fatigue management |
| **10** | LIS Wind | Long Island Sound wind data |

---

## CRITICAL FEATURES ✅

**Real-time Wave Height Calculation (v1.1)**
- From IMU acceleration with heel correction
- Eliminates 14% error at 30° heel
- Accuracy: ±5% typical

**Dual-Antenna True Heading**
- UM982 GPS (not magnetic compass)
- ±0.5° precision
- Continuous in all conditions

**9-Axis IMU (Quaternion-Based)**
- WIT WT901BLECL — 10 Hz, no gimbal lock
- Companionway mounting: WIT-X=port, WIT-Y=masthead(up), WIT-Z=bow
- Mount correction: MOUNT_Q=(0.5,-0.5,0.5,-0.5) verified 2026-05-31
- FILTK=200 required (set via WitMotion app, NOT via BLE)

**Complete Data Recording**
- Every sensor reading logged to InfluxDB
- Full race replay capability (Block Island 2026-05-22: 186 nm, 15+ hours)

---

## KEY DOCUMENTS

| Need | Document | Location |
|------|----------|----------|
| **Full Architecture** | System design + decisions | docs/ARCHITECTURE-MASTER.md |
| **Hardware Specs** | Equipment datasheets | docs/HARDWARE/*.md |
| **WIT IMU Guide** | Complete protocol + calibration + troubleshooting | docs/HARDWARE/WIT-WT901BLECL-DATASHEET.md |
| **Integration Guides** | Setup for each component | docs/INTEGRATION/*.md |
| **Grafana Dashboards** | Dashboard inventory + editing | docs/grafana-dashboards/README.md |
| **BLE Drivers** | Architecture + state machines | ble/README.md |
| **Execution Log** | OC task journal | logs/latest.json |

---

## RACE RESULTS (2026-05-22 Block Island Race)

| Metric | Value |
|--------|-------|
| Distance | 186 nm (Stamford CT → Block Island RI) |
| Duration | 15 hours 47 minutes |
| Configuration | J/30 double-handed (ORC rating) |
| System Uptime | 100% (no data loss, no service interruptions) |
| Data Quality | Excellent (13 dashboards, 60+ alerts, AI decision support) |

---

**SYSTEM STATUS:** ✅ **POST-RACE — PRODUCTION READY**

*Last updated: 2026-05-31 by OC*

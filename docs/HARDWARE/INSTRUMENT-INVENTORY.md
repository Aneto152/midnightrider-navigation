# Midnight Rider — Instrument Inventory
*J/30 hull 511 | Updated: 2026-05-13 | Audit-verified*

## Active Instruments

| # | Instrument | Role | Protocol | Signal K Source | Refresh | Status |
|---|-----------|------|----------|-----------------|---------|--------|
| 1 | Unicore UM982 NANO-HED10L | Primary GPS + True Heading | NMEA 0183 / USB | `um982-proprietary` | 1 Hz | ✅ Active |
| 2 | WIT WT901BLECL | Hull motion — roll/pitch/yaw/accel | Bluetooth LE | `wit_hull` | 30 Hz | ✅ Active |
| 3 | B&G WS320 | Primary wind (TWS/TWD/AWA/AWS) | NMEA 2000 | `nmea2000_ws320` | 1 Hz | ✅ Active |
| 4 | Yacht Devices YDNU-02 | NMEA 2000 ↔ USB bridge | USB / NMEA 2000 | transparent | N/A | ✅ Active |
| 5 | B&G Vulcan 7 FS | Secondary GPS + chartplotter | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Active |
| 6 | Raspberry Pi 4 | System metrics (CPU/RAM/temp) | Internal | `signalk-system-stats` | 0.2 Hz | ✅ Active |

## Planned / Optional Instruments

| # | Instrument | Role | Protocol | Signal K Source | Refresh | Status |
|---|-----------|------|----------|-----------------|---------|--------|
| 7 | SOK Battery BMS LiFePO4 | House battery monitoring | Bluetooth LE | Direct → InfluxDB | 0.2 Hz | ⏳ Planned May 2026 |
| 8 | Calypso UP10 | Backup wind (masthead BLE) | Bluetooth LE | `calypso_ble` | 1 Hz | ⏳ Optional (not active) |

## Not Installed

| # | Instrument | Role | Notes |
|---|-----------|------|-------|
| 9 | Speed through water (STW) | Boat speed, leeway | NMEA 2000 via YDNU-02 when installed |
| 10 | Barometer | Air pressure | NMEA 2000 or standalone |
| 11 | AIS transceiver | Traffic + collision avoidance | NMEA 2000 or NMEA 0183 |
| 12 | Depth sounder | Depth, water temperature | NMEA 2000 via YDNU-02 |

---

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|-----------|-------|
| `um982-proprietary` | Unicore UM982 | Proprietary #HEADINGA sentences for dual-antenna heading |
| `wit_hull` | WIT WT901BLECL | Hull mount, 30 Hz |
| `nmea2000_ws320` | B&G WS320 | Primary wind source |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `calypso_ble` | Calypso UP10 | Optional backup (not active) |
| `sok_bms` | SOK BMS | Direct InfluxDB — bypasses Signal K |

---

## Data Flow Architecture

```
UM982 (USB) ──NMEA 0183──► Signal K :3000 ──► InfluxDB :8086 ──► Grafana :3001
WIT IMU (BLE) ──JSON──────► │ │
YDNU-02 (USB) ──NMEA 2000──► │ (B&G WS320 + Vulcan via YDNU-02) │
RPi stats ──internal──► │ Portal :8888
 ▼
SOK BMS (BLE) ──────────────────────────────► InfluxDB :8086 (direct, bypasses SK)
```

---

## Refresh Rate Summary

| Layer | UM982 | WIT IMU | WS320 | Vulcan | RPi | SOK BMS |
|-------|-------|---------|-------|--------|-----|---------|
| Hardware output | 1 Hz | 100 Hz max | 1 Hz | 1 Hz | — | 0.2 Hz |
| Signal K polling | 1 Hz | 30 Hz | 1 Hz | 1 Hz | 0.2 Hz | N/A |
| InfluxDB writes | ~60/min | ~1800/min | ~60/min | ~60/min | ~12/min | ~12/min |
| Grafana display | 5–30s | 5–30s | 5–30s | 5–30s | 30s | 30s |

---

## SI Units Reference (Signal K internal)

| Measurement | Signal K SI unit | Grafana display | Conversion factor |
|-------------|-----------------|-----------------|-------------------|
| Speed (SOG, STW, wind) | m/s | knots | × 1.94384 |
| Heading, bearing, angle | radians | degrees | × 57.2958 |
| Temperature | Kelvin (K) | °C | − 273.15 |
| Pressure | Pascal (Pa) | hPa | ÷ 100 |
| Rate of turn | rad/s | °/s | × 57.2958 |
| State of charge | ratio 0–1 | % | × 100 |
| Position | decimal degrees | decimal degrees | none |

---
*Canonical reference for Grafana queries, Signal K config and documentation.*
*See also: DATA-SCHEMA-MASTER.md, GRAFANA-UNIT-CONVERSIONS.md*

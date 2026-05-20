# Midnight Rider — Instrument Inventory
*(J/30 hull 511 | Updated: 2026-05-20 | Audit-verified)*

---

## Active Instruments

| # | Instrument | Role | Protocol | Signal K Source | Refresh | Status |
|---|------------|------|----------|-----------------|---------|--------|
| 1 | Unicore UM982 NANO-HED10L | Primary GPS + True Heading | NMEA 0183 / USB | `signalk-um982-gnss.UM982-HDG` | 1 Hz | ✅ Active |
| 2 | WIT WT901BLECL | Hull motion — roll/pitch/yaw/accel | Bluetooth LE | `signalk-wit-imu-ble.XX` | 30 Hz | ✅ Active |
| 3 | B&G WS320 | Wind masthead — AWS/AWA (5 Hz) → Vulcan + SK via YDNU-02 | NMEA 2000 | `nmea2000_ws320` | 5 Hz | ✅ Active |
| 4 | Calypso UP10 | Wind + air temp — AWS/AWA/TWS/TWD → SK primary wind source | Bluetooth LE | `calypso-up10` | 1 Hz | ✅ Active |
| 5 | Yacht Devices YDNU-02 | NMEA 2000 ↔ USB bridge (Signal K ↔ Vulcan) | USB / NMEA 2000 | transparent | N/A | ✅ Active |
| 6 | B&G Vulcan 7 FS | Secondary GPS + chartplotter + AIS display | NMEA 2000 | `vulcan_internal` | 1 Hz | ✅ Active |
| 7 | Raspberry Pi 4 | Navigation server — Signal K / InfluxDB / Grafana | Internal | `signalk-system-stats` | 0.2 Hz | ✅ Active |
| 8 | SOK Battery BMS LiFePO4 100Ah | House battery monitoring | Bluetooth LE | Direct → InfluxDB only | 0.2 Hz | ✅ Active |
| 9 | Yacht Devices YDBC-05 | Atmospheric pressure | NMEA 2000 | `nmea2000_ydbc05` | 0.5 Hz | ✅ Active |
| 10 | B&G AIS700 Class B SOTDMA | AIS transceiver — traffic + collision avoidance | NMEA 2000 | `nmea2000_ais700` | event-driven | ✅ Active |

---

## Not Installed

| # | Instrument | Role | Notes |
|---|------------|------|-------|
| 11 | Speed through water (STW) / loch | Boat speed, leeway | Via NMEA 2000 → YDNU-02 when installed |
| 12 | Depth sounder | Depth, water temperature | Via NMEA 2000 → YDNU-02 when installed |

---

## Signal K Source Name Reference

| Signal K Source | Instrument | Notes |
|-----------------|------------|-------|
| `signalk-um982-gnss.UM982-HDG` | Unicore UM982 | Proprietary #UNIHEADING sentences — dual-antenna heading. HEADINGOFFSET 90 applied 2026-05-17 |
| `signalk-wit-imu-ble.XX` | WIT WT901BLECL | Hull mount, 30 Hz — primary attitude source (highest SK priority) |
| `nmea2000_ws320` | B&G WS320 | Apparent wind via N2K backbone → YDNU-02 → SK. Also feeds Vulcan 7 directly at 5 Hz |
| `calypso-up10` | Calypso UP10 | Primary SK wind source (BLE → UDP port 4123). Active via systemd service |
| `vulcan_internal` | B&G Vulcan 7 FS | Secondary GPS/COG/SOG from Vulcan internal GNSS |
| `signalk-system-stats` | Raspberry Pi 4 | CPU temp (K), load, RAM |
| `nmea2000_ydbc05` | Yacht Devices YDBC-05 | Atmospheric pressure via N2K → YDNU-02 → SK |
| `nmea2000_ais700` | B&G AIS700 | AIS vessel targets via N2K → YDNU-02 → SK (`vessels.*` namespace) |
| `sok_bms` | SOK Battery BMS | Direct InfluxDB — bypasses Signal K entirely |

---

## Wind Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `calypso-up10` | `environment.wind.*` | Primary — masthead BLE sensor, 1 Hz |
| 2 | `nmea2000_ws320` | `environment.wind.*` | Secondary — N2K via YDNU-02, 5 Hz |

> The WS320 also feeds the Vulcan 7 FS **directly** at 5 Hz without going through Signal K
> (N2K backbone shortcut). The Vulcan uses this for real-time sail trim display.

## Attitude Data Source Priority (Signal K)

| Priority | Source | Path | Notes |
|----------|--------|------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` | `navigation.attitude.*` | WIT IMU — 30 Hz. Also feeds PGN 127257 → Vulcan 7 via YDNU-02 |
| 2 | `calypso-up10` | `navigation.attitude.*` | Compass mode only (if `--compass=on`) — overridden by WIT |

---

## NMEA 2000 Bus — Load Summary

| Device | LEN | Role |
|--------|-----|------|
| Yacht Devices YDNU-02 | 1 | SK ↔ N2K gateway |
| B&G Vulcan 7 FS | 1 | Chartplotter + AIS display |
| B&G WS320 Base Station | 2 | Wireless wind receiver |
| Yacht Devices YDBC-05 | 1 | Barometer |
| B&G AIS700 | 1 | Class B AIS transceiver |
| **Total** | **6 / 50 max** | ✅ Well within limits |

---

## Data Flow Architecture

```
UM982 (USB) ──── NMEA 0183 ──────────────────────────────► Signal K :3000 ──── InfluxDB :8086 ──── Grafana :3001
WIT IMU (BLE) ── JSON/BLE ──────────────────────────────► │
Calypso UP10 (BLE) ── UDP :4123 ────────────────────────► │          ──── signalk-to-nmea2000 ──── YDNU-02 (USB)
RPi stats ─── internal ─────────────────────────────────► │                                            │
                                                           │                                     N2K backbone
YDNU-02 (USB) ── NMEA 2000 ─────────────────────────────► │                                            │
  (receives from N2K bus):                                 │                                   ┌────────┴────────┐
    - WS320 wind (PGN 130306)                              │                              Vulcan 7 FS      AIS700
    - YDBC-05 pressure (PGN 130314)                        │                              WS320 (5Hz)      YDBC-05
    - AIS700 targets (PGN 129038-129810)                   │
    
SOK BMS (BLE) ──────────────────────────────────────────────────────────────────────────► InfluxDB :8086 (direct)
```

---

## Refresh Rate Summary

| Layer | UM982 | WIT IMU | WS320 | Calypso | Vulcan | RPi | SOK BMS | YDBC-05 | AIS700 |
|-------|-------|---------|-------|---------|--------|-----|---------|---------|--------|
| Hardware output | 1 Hz | 200 Hz max | 5 Hz | 1 Hz | 1 Hz | — | 0.2 Hz | 0.5 Hz | event |
| Signal K polling | 1 Hz | 30 Hz | 5 Hz | 1 Hz | 1 Hz | 0.2 Hz | N/A | 0.5 Hz | event |
| InfluxDB writes | ~60/min | ~1800/min | ~300/min | ~60/min | ~60/min | ~12/min | ~12/min | ~30/min | ~5/min |
| Grafana display | 5–30s | 5–30s | 5–30s | 5–30s | 5–30s | 30s | 30s | 30s | 30s |

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

## Key Events Log

| Date | Event |
|------|-------|
| 2026-04-25 | Initial system deployment |
| 2026-05-12 | SOK BMS integration complete — field test ready |
| 2026-05-13 | Inventory last formal audit |
| 2026-05-17 | UM982 HEADINGOFFSET 90 applied permanently (NVRAM) |
| 2026-05-17 | attitude.js patch — PGN 127257 (Roll/Pitch/Yaw) now emits to Vulcan 7 |
| 2026-05-19 | Calypso UP10 confirmed active (systemd service + watchdog running) |
| 2026-05-19 | YDBC-05 barometer installed on NMEA 2000 backbone |
| 2026-05-19 | B&G AIS700 installed on NMEA 2000 backbone |
| 2026-05-20 | Full hardware documentation revision (all datasheets updated/created) |

---

*Canonical reference for Grafana queries, Signal K config and documentation.*
*See also: DATA-SCHEMA-MASTER.md, GRAFANA-UNIT-CONVERSIONS.md*

# Midnight Rider Navigation — System Architecture (2026-06-13)

**Status: ✅ PRODUCTION READY FOR BLOCK ISLAND RACE (2026-05-22)**

---

## Overview

Three main BLE/GNSS sensor streams → Signal K → InfluxDB → Grafana dashboards

| Component | Type | Device | Port | Data |
|-----------|------|--------|------|------|
| **Calypso** | BLE Anemometer | E0:B7:FD:84:6D:2A | 4123 UDP | Wind speed/dir (4Hz) |
| **WIT IMU** | BLE Inertial | E9:10:DB:8B:CE:C7 | 4123 UDP | Attitude/accel (10Hz) |
| **UM982 GNSS** | Serial GNSS | /dev/ttyUM982 | 115200 | Position/heading (5Hz) |

---

## UM982 Dual-Antenna GNSS — Architecture V2 (Updated 2026-06-13)

### Hardware
- **Device**: Unicore UM982 dual-antenna GNSS/INS receiver
- **Port**: `/dev/ttyUM982` (udev symlink → `/dev/ttyUSB0`)
- **Baud rate**: 115200
- **Antennas**: 2 × active GNSS antenna, baseline = 4.29m (mast-to-mast)
- **Output sentences**: 
  - `$GNGGA` (1Hz) — GNSS position + altitude
  - `$GNRMC` (1Hz) — position + SOG + COG
  - `#HEADINGA` (5Hz) — dual-antenna heading, roll, pitch
- **Solution status**: SOL_COMPUTED / NARROW_FLOAT (RTK-class precision)

### Plugin (Active): signalk-um982-gnss V2

**File**: `plugins/signalk-um982-gnss.js` (v2.0.0)

**Architecture**: Direct serial reader via `serialport` npm package
- Bypasses Signal K NMEA0183 provider (no validateChecksum issue)
- Opens `/dev/ttyUM982` directly at plugin startup
- Auto-reconnects on port error (10s delay, exponential backoff)
- Structured logging: `logs/services/um982-gnss.log`

**Sentences parsed**:
- `$GNGGA` → `navigation.position` (lat/lon/alt)
- `$GNRMC` → `navigation.position` + `navigation.speedOverGround` + `navigation.courseOverGroundTrue`
- `#HEADINGA` → `navigation.headingTrue` + `navigation.attitude.roll` + `navigation.attitude.pitch`

**Source label**: `um982-gnss`

### Signal K Data Published

| Path | Rate | Value | Source | Units |
|------|------|-------|--------|-------|
| `navigation.position` | 1 Hz | {lat, lon, alt} | um982-gnss | deg, m |
| `navigation.speedOverGround` | 1 Hz | 0.0-20.0 | um982-gnss | m/s |
| `navigation.courseOverGroundTrue` | 1 Hz | 0-2π | um982-gnss | rad |
| `navigation.headingTrue` | 5 Hz | 0-2π | um982-gnss | rad |
| `navigation.attitude.roll` | 5 Hz | -π to +π | um982-gnss | rad |
| `navigation.attitude.pitch` | 5 Hz | -π to +π | um982-gnss | rad |

### Signal K Providers (pipedProviders)

Current active providers in `config/signalk-settings.json`:

| ID | Type | Address | Purpose | Status |
|----|------|---------|---------|--------|
| Calypso | SignalK UDP | port 4123 | Calypso ultrasonic anemometer | ✅ Active |
| qtVLM-NMEA-Input | NMEA0183 TCP | 127.0.0.1:10111 | qtVLM navigation software | ✅ Active |
| N2K | NMEA2000 | /dev/ttyACM0 | NMEA2000 backbone (B&G instruments) | ✅ Active |

**Note**: The legacy `UM982-Serial` provider has been **removed on 2026-06-13** (was blocking headingTrue due to port conflict).

### Removed/Disabled Plugins

**These should NEVER be re-enabled:**

| Plugin | Status | Reason | Disabled Date |
|--------|--------|--------|---|
| `signalk-um982-proprietary` | DELETED | Redundant with V2, listened on nmea0183out (never received #HEADINGA) | 2026-06-13 |
| `@tkurki/um982` | DISABLED | Superseded by V2 direct serial | 2026-06-13 |
| `signalk-gps-um982-nmea-parser` | DISABLED | Superseded by V2 direct serial | 2026-06-13 |
| `signalk-um982-custom` | DISABLED | Superseded by V2 direct serial | 2026-06-13 |

---

## Calypso Anemometer (BLE)

**Plugin**: Signal K native BLE bridge (via `ble_common.py`)

**Device**: Calypso UP10 (Ultrasonic, €1200)
- MAC: `E0:B7:FD:84:6D:2A`
- Rate: 4 Hz (verified stable 2026-05-29)
- Recovery: BT_RECOVERY on 'not found' + 'le-connection-abort'
- Watchdog: 60s timeout → auto-restart

**Published**:
- `environment.wind.speedApparent` (m/s)
- `environment.wind.angleApparent` (rad)

---

## WIT WT901BLECL IMU (BLE)

**Service**: `wit-ble-direct.service`

**Device**: WIT WT901BLECL 6-axis IMU (€150)
- MAC: `E9:10:DB:8B:CE:C7`
- Rate: 10 Hz (quaternion one-shot requests)
- Recovery: L1 reconnect (5-60s backoff), L2 clean exit after 30 failures
- Mount correction: Q_mount = (1, 0, 0, 0) identity (calibrated 2026-05-31)

**Published**:
- `navigation.attitude.roll` (rad)
- `navigation.attitude.pitch` (rad)
- `navigation.attitude.yaw` (rad)
- `navigation.headingMagnetic` (rad)
- `navigation.acceleration.{x,y,z}` (m/s²)
- `navigation.rateOfTurn` (rad/s)
- `sensors.wit.quaternion.{w,x,y,z}` (raw)

---

## Signal K Server

**Service**: `signalk` (systemd)
**Port**: 3000
**REST API**: `http://localhost:3000/signalk/v1/api/`
**Data Plugins**: See providers table above

**Key plugins**:
- `signalk-um982-gnss` (V2, direct serial)
- `signalk-to-influxdb2` (writes deltas to InfluxDB)
- `signalk-wave-height-simple` (calculates wave height from accel)
- `signalk-performance-polars` (J30 polars for performance calc)

---

## InfluxDB

**Service**: Docker container
**Port**: 8086
**Bucket**: `midnight_rider`
**Organization**: `MidnightRider`
**Retention**: 30 days

**Measurements stored**:
- `navigation.position`
- `navigation.courseOverGroundTrue`
- `navigation.speedOverGround`
- `navigation.attitude.{roll,pitch,yaw}`
- `navigation.headingTrue`
- `navigation.headingMagnetic`
- `environment.wind.{speedApparent,angleApparent}`
- `environment.water.temperature`

---

## Grafana

**Service**: Docker container
**Port**: 3001
**Datasource**: InfluxDB bucket `midnight_rider`
**Dashboards**: 13 dashboards (provisioned from `grafana-dashboards/`)

**Key dashboards**:
- 01-cockpit.json — Real-time yacht attitude + wind
- 02-environment.json — Temperature, pressure, humidity
- 07-race.json — Race-specific metrics (polars, current vector)
- 08-alerts.json — Alert history (battery low, wind excessive, etc.)

---

## Data Flow Diagram

```
┌─────────────────┐
│  Calypso UP10   │ → UDP:4123 → Signal K → InfluxDB → Grafana
│  (Wind 4Hz)     │             Deltas
└─────────────────┘

┌─────────────────┐
│  WIT WT901BLECL │ → UDP:4123 → Signal K → InfluxDB → Grafana
│  (IMU 10Hz)     │             Deltas
└─────────────────┘

┌─────────────────┐
│UM982 GNSS (5Hz) │ → Serial    → Signal K → InfluxDB → Grafana
│  (Position)     │   /dev/ttyUM982
└─────────────────┘
```

---

## Verification Checklist (2026-06-13)

- ✅ headingTrue: 3.0°T | source: um982-gnss.XX
- ✅ position: 40.83433, -73.71333 (Stamford CT harbor)
- ✅ Signal K: active and stable
- ✅ InfluxDB: receiving deltas
- ✅ Grafana: all 13 dashboards responsive
- ✅ Calypso: 4Hz stable (10+ hours uptime)
- ✅ WIT IMU: reconnect robustness verified
- ✅ UM982 GNSS: dual-antenna baseline 4.29m LOCKED
- ✅ System memory: 37%, disk: 23%, temp: 48°C

---

## Next Steps

1. Field test headingTrue on water (Block Island Race prep)
2. Verify InfluxDB archival pipeline (post-race)
3. Dashboard refinement based on crew feedback
4. Documentation of edge cases discovered during race

---

**Last Updated**: 2026-06-13 12:25 EDT  
**Author**: OC + Denis Lafarge  
**Version**: v2.0 (UM982 V2 direct serial, production ready)

---

## Update — V2.1 (2026-06-13) — Athwartships Antenna Configuration

**Critical discovery**: UM982 antennas are mounted TRANSVERSELY (port ↔ starboard), NOT longitudinally (bow ↔ stern).

### Consequences

With transversal antennas:
- ✅ **Heading (azimuth)** — fully determined from antenna baseline angle (corrected by UM982)
- ✅ **Roll (heel)** — vessel heel angle from antenna tilt
- ❌ **Pitch** — CANNOT be determined from transversal baseline geometry (antenna separation is E-W only)

### Changes in V2.1

| Removed | Reason |
|---------|--------|
| `navigation.attitude.pitch` | Athwartships geometry artifact: field data[3] varies with heading, not pitch. Publishing meaningless data removed. |

| Added | Source | Details |
|-------|--------|---------|
| `navigation.gnss.satellites` | $GNGGA f[7] | Number of satellites used for fix |
| `navigation.gnss.horizontalDilution` | $GNGGA f[8] | HDOP (horizontal dilution of precision) |
| `navigation.gnss.methodQuality` | $GNGGA f[6] | Fix type string (e.g., "RTK fixed integer") |
| `navigation.gnss.antennaAltitude` | $GNGGA f[9] | MSL altitude (meters) |
| `navigation.gnss.geoidalSeparation` | $GNGGA f[11] | Geoidal separation (meters) |
| `navigation.gnss.antennaBaseline` | #HEADINGA f[6] | Distance between antennas (m), health check (~2.8m nominal) |
| `navigation.magneticVariation` | $GNRMC f[10/11] | Magnetic variation (radians), E/W direction |
| `navigation.datetime` | $GNRMC f[1]+f[9] | UTC datetime (ISO 8601 format) |

### Verification (2026-06-13)

✅ **Pitch is correctly ABSENT** from Signal K navigation.attitude
✅ **headingTrue: 8.20°T** (from #HEADINGA data[4])
✅ **magneticVariation: -12.80°W** (from $GNRMC)
✅ **datetime: 2026-06-13T16:57:57Z** (from $GNRMC)

### Physical Configuration (to verify)

- **Antenna 1**: Port side, higher position
- **Antenna 2**: Starboard side, lower position
- **Baseline**: ~2.8 meters (expected ~4.29m from May diagnostic, need re-check)

Next: Denis to confirm actual antenna separation and orientation on vessel.


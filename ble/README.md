# ble/ — Bluetooth Low Energy Scripts

> Last updated: 2026-05-29  
> Centralized from `/home/aneto/` — previously scattered across the Pi filesystem

Custom BLE bridge scripts for Midnight Rider sensors.  
These scripts handle the BLE ↔ Signal K / InfluxDB data pipeline.

---

## Architecture

```
BLE Sensors → [ble/ scripts] → Signal K OR InfluxDB

Calypso UP10 Anemometer
  ├─ calypso-ble-reader.py → raw BLE serial packets
  ├─ calypso_filter_proxy.py → filters + UDP/Signal K delta
  └─ calypso_robust_watchdog.py → connection watchdog

WIT WT901BLECL IMU (Attitude)
  ├─ wit-ble-reader.py → raw BLE advertisement packets
  ├─ wit-final-ble.py → complete BLE parser (roll/pitch/yaw)
  ├─ wit-ble-handler.py → connection manager
  ├─ wit-imu-complete.py → full IMU (accel/gyro/mag)
  └─ bleak_wit.py → Bleak library test

WIT Data Pipeline → Signal K
  ├─ signalk-wit-nmea.js → plugin receives NMEA 0183 from wit-nmea-server.py
  └─ wit-nmea-server.py → outputs \$HEATT, \$HEAPH, \$HEADM to TCP

UM982 GNSS (RTK + Heading)
  ├─ send_um982_headinga.py → inject HEADINGA sentence
  ├─ enable_gnhpr.py → enable on hardware
  └─ signalk-um982-proprietary.js → plugin parses proprietary sentences
```

---

## Files

### Calypso UP10 Anemometer (BLE)

#### `calypso-ble-reader.py` (9.6 KB)

| Field | Value |
|---|---|
| **Purpose** | Raw Calypso BLE device reader — connects to MAC `F8:5F:12:9D:D2:EE`, reads BLE advertisements |
| **BLE Device** | Calypso UP10 anemometer (wind speed/direction) |
| **Output** | Wind speed (m/s), direction (°) on serial-like BLE stream |
| **Destination** | → calypso_filter_proxy.py |
| **Runs as daemon** | ❌ No — used by filter proxy |
| **Status** | ⚠️ Reference; calypso-anemometer (pip package) is preferred |

#### `calypso_filter_proxy.py` (2.4 KB)

| Field | Value |
|---|---|
| **Purpose** | BLE to UDP bridge — filters sentinel values (999.0), outputs Signal K delta packets |
| **Input** | Calypso BLE device via `calypso-anemometer` CLI tool |
| **Output** | UDP delta packets → `localhost:4122` (Signal K) |
| **Destination** | Signal K server |
| **systemd service** | `N/A` — started by calypso_anemometer.service |
| **Runs as daemon** | ✅ Yes (PID 1177 observed) |
| **Status** | ✅ **ACTIVE** — primary Calypso ingestion |

#### `calypso_robust_watchdog.py` (4.2 KB)

| Field | Value |
|---|---|
| **Purpose** | Connection monitor — restarts Calypso service if BLE device goes offline |
| **Monitors** | Calypso BLE device responsiveness |
| **Action** | Restarts `calypso_anemometer.service` on timeout |
| **Status** | ⚠️ **DEPRECATED** — systemd `Restart=on-failure` is preferred (see AGENTS.md) |
| **Reason** | Multiple managers race condition (see 2026-05-22 race debrief) |

#### `calypso-health-check.sh` (2.1 KB)

| Field | Value |
|---|---|
| **Purpose** | Diagnostic — check Calypso BLE device status, connection quality |
| **Usage** | `bash ble/calypso-health-check.sh` |
| **Output** | Device MAC, signal strength, last update timestamp |
| **Status** | ✅ Operational — use before race |

#### `calypso-restart.sh` (1.3 KB)

| Field | Value |
|---|---|
| **Purpose** | Manual restart of Calypso service |
| **Usage** | `sudo bash ble/calypso-restart.sh` |
| **Action** | `systemctl restart calypso_anemometer` |
| **Status** | ✅ Working — emergency recovery |

---

### WIT WT901BLECL IMU (Attitude)

#### `wit-ble-reader.py` (4.8 KB)

| Field | Value |
|---|---|
| **Purpose** | Raw WIT BLE advertisement scanner — finds device, reads packets |
| **BLE Device** | WIT WT901BLECL (9-DOF IMU) — MAC varies per unit |
| **Output** | Roll, pitch, yaw (degrees) |
| **Destination** | → Signal K (via plugin) OR InfluxDB |
| **Status** | ⚠️ Reference; `signalk-wit-imu-ble` plugin is preferred |

#### `wit-final-ble.py` (7.8 KB)

| Field | Value |
|---|---|
| **Purpose** | Complete WIT BLE parser — robust attitude extraction with calibration |
| **Input** | WIT WT901BLECL BLE advertisements |
| **Output** | Roll/pitch/yaw (radians + degrees), calibration info |
| **Destination** | Signal K or direct InfluxDB |
| **Status** | ✅ Mature — used in production tests |

#### `wit-ble-handler.py` (4.0 KB)

| Field | Value |
|---|---|
| **Purpose** | WIT connection state machine — handles pairing, reconnection, errors |
| **Function** | Maintains persistent BLE connection despite transient failures |
| **Status** | ⚠️ Utility — not used standalone |

#### `wit-battery-loop.py` (2.5 KB)

| Field | Value |
|---|---|
| **Purpose** | WIT battery status monitor — periodic checks |
| **Output** | Battery voltage, charging state |
| **Status** | ⚠️ Reference — not actively used |

#### `wit-imu-complete.py` (9.7 KB)

| Field | Value |
|---|---|
| **Purpose** | Full 9-DOF IMU readout — accel, gyro, mag, attitude |
| **Output** | All sensor axes (x/y/z) + derived roll/pitch/yaw |
| **Destination** | InfluxDB or debug |
| **Status** | ✅ Working — comprehensive data capture |

#### `bleak_wit.py` (2.7 KB)

| Field | Value |
|---|---|
| **Purpose** | Bleak library test — low-level BLE characteristic read/write |
| **Use case** | Debug BLE stack issues, verify device responsiveness |
| **Status** | ✅ Diagnostic tool |

---

### WIT Data Pipeline → Signal K

#### `wit-nmea-server.py` (6.0 KB)

| Field | Value |
|---|---|
| **Purpose** | WIT → NMEA 0183 bridge — outputs Signal K-compatible NMEA sentences |
| **Output** | `$HEATT` (attitude), `$HEAPH` (pitch), `$HEADM` (heading) via TCP |
| **Destination** | TCP localhost:10110 → received by `signalk-wit-nmea.js` plugin |
| **systemd service** | ❌ None (run manually or via docker) |
| **Status** | ✅ Working — part of WIT→SK pipeline |

#### `wit-tcp-bridge.py` (3.5 KB)

| Field | Value |
|---|---|
| **Purpose** | TCP bridge for WIT data — legacy approach |
| **Status** | ⚠️ Deprecated — wit-nmea-server is preferred |

#### `wit-signalk-bridge-direct.py` (8.4 KB)

| Field | Value |
|---|---|
| **Purpose** | Direct WIT → Signal K delta bridge (no NMEA intermediate) |
| **Output** | Signal K delta packets directly |
| **Destination** | Signal K WebSocket or HTTP POST |
| **Status** | ✅ Alternative — more direct but less integration |

---

### Signal K Plugins

#### `signalk-wit-nmea.js` (4.8 KB)

| Field | Value |
|---|---|
| **Purpose** | Signal K plugin — receives NMEA 0183 from wit-nmea-server.py |
| **Input** | TCP stream: `$HEATT`, `$HEAPH`, `$HEADM` sentences |
| **Output** | `navigation.attitude` (roll/pitch/yaw) into Signal K tree |
| **Location** | `~/.signalk/plugins/signalk-wit-nmea/` |
| **Enabled** | ✅ Yes (in settings.json) |
| **Status** | ✅ **ACTIVE** — WIT IMU data ingestion |

#### `signalk-um982-proprietary.js` (6.5 KB)

| Field | Value |
|---|---|
| **Purpose** | Signal K plugin — parses Unicore UM982 proprietary GNSS sentences |
| **Input** | UM982 via serial (kplex bridge) |
| **Sentences** | `HEADINGA` (RTK heading), `GPGGA` (position), pitch/roll (proprietary) |
| **Output** | `navigation.attitude`, `navigation.position`, `navigation.courseOverGround` |
| **Features** | **Pitch normalization bugfix** (2026-05-29) — converts 0-360° to -180°/+180° |
| **Location** | `~/.signalk/plugins/signalk-um982-proprietary/` |
| **Enabled** | ✅ Yes (in settings.json) |
| **Status** | ✅ **ACTIVE** — UM982 RTK/GNSS ingestion + heading |

---

### UM982 GNSS Utilities

#### `send_um982_headinga.py` (3.0 KB)

| Field | Value |
|---|---|
| **Purpose** | Inject HEADINGA sentence into UM982 for testing |
| **Usage** | `python3 ble/send_um982_headinga.py` |
| **Status** | ⚠️ Debug tool — not production |

#### `enable_gnhpr.py` (3.1 KB)

| Field | Value |
|---|---|
| **Purpose** | Enable GNSS + Heading + Pitch/Roll output on UM982 hardware |
| **Usage** | `python3 ble/enable_gnhpr.py` (one-time setup) |
| **Status** | ✅ Used during initial UM982 configuration |

---

## Summary

### Active BLE Data Sources

| Sensor | Status | SK Plugin | Output |
|--------|--------|-----------|--------|
| **Calypso UP10** | ✅ ACTIVE | `calypso_anemometer.service` | Wind speed/direction |
| **WIT WT901BLECL** | ✅ ACTIVE | `signalk-wit-nmea.js` | Roll/pitch/yaw (attitude) |
| **UM982 GNSS** | ✅ ACTIVE | `signalk-um982-proprietary.js` | RTK heading, position, attitude |

### Deprecated/Reference Scripts

- `calypso_robust_watchdog.py` — Use systemd `Restart=on-failure` instead
- `wit-tcp-bridge.py` — Use `wit-nmea-server.py` + NMEA plugin instead
- `wit-ble-handler.py` — Utility, not standalone
- `wit-battery-loop.py` — Monitor tool, not mission-critical

---

## Quick Reference

### Check Running BLE Services

```bash
ps aux | grep -E "calypso|wit|um982" | grep -v grep
```

**Expected output:**
- PID 1177: `calypso_filter_proxy.py` (running)
- SK plugins loaded (check logs: `journalctl -u signalk -n 50`)

### Check BLE Device Connectivity

```bash
# Calypso
bash ble/calypso-health-check.sh

# WIT (if running diagnostics)
bluetoothctl devices | grep -i wit
```

### Restart BLE Systems

```bash
# Calypso
sudo systemctl restart calypso_anemometer

# Signal K (reloads plugins)
sudo systemctl restart signalk

# Both
sudo systemctl restart calypso_anemometer signalk
```

### View Logs

```bash
# Calypso filter proxy (stderr)
journalctl -u calypso_anemometer -n 50

# Signal K (all plugins)
journalctl -u signalk -n 50 | grep -iE "wit|um982|calypso"

# InfluxDB writes
curl -s http://localhost:8086/api/v2/ready && echo "InfluxDB OK"
```

---

## Deployment Notes

### systemd Services

- ✅ `calypso_anemometer.service` — Managed by repo
- ✅ `signalk.service` — System-wide, loads plugins from `~/.signalk/settings.json`
- ⚠️ WIT IMU — No dedicated service; managed by Signal K plugin

### Environment Variables

See `.env` for:
- `CALYPSO_BLE_ADDRESS=F8:5F:12:9D:D2:EE` (used by calypso service)
- `WIT_BLE_ADDRESS=` (for future use)

### Pre-Race Checklist

1. ✅ Test Calypso: `bash ble/calypso-health-check.sh`
2. ✅ Check WIT pairing: `bluetoothctl devices | grep -i wit`
3. ✅ Restart all: `sudo systemctl restart signalk calypso_anemometer`
4. ✅ Monitor: `journalctl -u signalk -f` (watch for errors)
5. ✅ Verify data: Check Grafana dashboard for attitude + wind

---

**Source:** Centralized from `/home/aneto/` on 2026-05-29  
**Repository:** [midnightrider-navigation](https://github.com/Aneto152/midnightrider-navigation)  
**Contact:** Denis Lafarge (Midnight Rider J/30 Hull 511)

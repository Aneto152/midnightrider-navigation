# CALYPSO UP10 — ULTRASONIC ANEMOMETER DATASHEET

**Manufacturer:** Calypso Instruments  
**Model:** Ultrasonic Portable Solar (UP10)  
**Interface:** Bluetooth Low Energy (BLE)  
**Date:** 2026-05-31  
**Status:** ✅ Operational (systemd service running)

---

## DEVICE SPECIFICATIONS

| Spec | Value |
|------|-------|
| **Sensor Type** | Ultrasonic (zero moving parts, maintenance-free) |
| **Wind Speed Range** | 0 – 60 knots (0 – 31 m/s) |
| **Wind Speed Accuracy** | ±3% or ±0.5 knot (whichever is greater) |
| **Wind Direction Range** | 0 – 360° |
| **Wind Direction Accuracy** | ±5° |
| **Update Rate** | Configurable: **1 Hz / 4 Hz / 8 Hz** — 4 Hz default (stable). 8Hz oversaturates BLE CI. 10Hz NOT supported (0x0A ignored) |
| **Power** | Solar panel (built-in, self-charging) |
| **Battery Backup** | Lithium, ~48h autonomy |
| **BLE Range** | ~30 m line-of-sight |
| **Operating Temp** | -20°C to +70°C |
| **IP Rating** | IPX7 (waterproof — 1m depth, 30 min) |
| **Size** | Compact masthead unit |

> ⚠️ The UP10 is made by **Calypso Instruments** (Spain/USA/Singapore).
> It is NOT a B&G product. The B&G WS320 is a completely separate device
> (NMEA 2000 wired sensor, also on the boat).

---

## BLUETOOTH LE PROTOCOL

### Device Discovery

```bash
# BLE device name advertised: "ULTRASONIC"
# Discovery via calypso-anemometer CLI:
calypso-anemometer info

# Or with known BLE address (faster, skip scan):
calypso-anemometer info --ble-address=<MAC_ADDRESS>
```

### BLE Data Available

The device exposes the following data via BLE GATT characteristics:

| Field | Unit | Notes |
|-------|------|-------|
| **Wind Speed** | m/s | Converted by driver from raw BLE |
| **Wind Direction** | degrees (0–360) | Relative to device mounting |
| **Battery Level** | % | 0–100 |
| **Temperature** | °C | Air temperature at masthead |
| **Heading** | degrees | Built-in compass (optional, `--compass=on`) |
| **Roll** | degrees | Built-in IMU (optional) |
| **Pitch** | degrees | Built-in IMU (optional) |

### Configurable Data Rates

```bash
--rate=hz_1   → 1 Hz   (used on Midnight Rider)
--rate=hz_8   → 8 Hz   (driver default — max confirmed rate)
--rate=hz_8   → 8 Hz   (max rate)
```

---

## NMEA-0183 OUTPUT (via calypso-anemometer driver)

When the driver uses NMEA-0183 output mode (UDP broadcast), it emits
Calypso-prefixed `$ML` sentences:

| Sentence | Description | Example |
|----------|-------------|---------|
| **`$MLHDT`** | True heading (from compass, if enabled) | `$MLHDT,235.0,T*27` |
| **`$MLVWR`** | Relative wind (apparent wind vector) | `$MLVWR,154.0,L,11.06,N,5.69,M,20.48,K*64` |
| **`$MLXDR`** | Transducer measurements (temp, battery, roll, pitch) | `$MLXDR,C,33.0,C,AIRTEMP#CAL*6A` |

Example NMEA stream:
```
$MLHDT,235.0,T*27
$MLVWR,154.0,L,11.06,N,5.69,M,20.48,K*64
$MLXDR,A,-60.0,D,PTCH#CAL,A,30.0,D,ROLL#CAL*75
$MLXDR,C,33.0,C,AIRTEMP#CAL*6A
$MLXDR,L,0.9,R,BATT#CAL*18
```

> On Midnight Rider, the driver uses **Signal K Delta UDP mode** (not NMEA-0183).
> The NMEA output mode is an alternative available for other software (OpenCPN, etc.)

---

## SIGNAL K INTEGRATION — MIDNIGHT RIDER

### Architecture

The Calypso UP10 is **not** integrated via a Signal K plugin.
It uses a standalone Python driver (`calypso-anemometer` by maritime-labs)
running as a **systemd service**, injecting data directly into Signal K via UDP.

```
Calypso UP10 (BLE)
     ↓ Bluetooth LE (~30m range)
RPi 4 (midnightrider.local) — hci0 BLE adapter
     ↓ calypso-anemometer Python service
     ↓ Signal K Delta UDP → port 4123
Signal K (port 3000, systemctl)
     ↓
environment.wind.* / environment.outside.temperature
     ↓
InfluxDB (port 8086) → Grafana (port 3001)
```

### systemd Services

| Service | Status | Role |
|---------|--------|------|
| `calypso_anemometer` | ✅ running | BLE connection + UDP injection to Signal K |
| `calypso_watchdog` | ✅ running | Watchdog to auto-restart on BLE disconnect |

```bash
# Check service status
sudo systemctl status calypso_anemometer
sudo systemctl status calypso_watchdog

# Restart if needed
sudo systemctl restart calypso_anemometer
```

### Signal K Paths Published

| SK Path | Unit | Source |
|---------|------|--------|
| `environment.wind.speedApparent` | m/s | calypso-up10 |
| `environment.wind.angleApparent` | radians | calypso-up10 |
| `environment.wind.speedTrue` | m/s | calypso-up10 |
| `environment.wind.directionTrue` | radians | calypso-up10 |
| `environment.outside.temperature` | K | calypso-up10 |
| `navigation.attitude.roll` | radians | calypso-up10 (if `--compass=on`) |
| `navigation.attitude.pitch` | radians | calypso-up10 (if `--compass=on`) |
| `navigation.headingTrue` | radians | calypso-up10 (if `--compass=on`) |

> ⚠️ Signal K stores wind speeds in **m/s**. Multiply by 1.94384 for knots.
> Angles are stored in **radians**. Multiply by 180/π for degrees.

### Signal K Source Reference

| Parameter | Value |
|-----------|-------|
| **Signal K source name** | `calypso-up10` |
| **Driver** | `calypso-anemometer` (Python, maritime-labs) |
| **Injection method** | UDP Signal K Delta → port 4123 |
| **Physical connection** | Bluetooth LE (BLE adapter `hci0` on RPi) |
| **Data rate** | 4 Hz (configured via `CALYPSO_RATE_HZ=4`). 8Hz oversaturates BLE CI. |

### UDP Receiver in Signal K

Signal K must have a UDP receiver configured on port 4123:
```
Signal K → Server → Data Connections → UDP → port 4123
```

---

## DATA SOURCE PRIORITY (Signal K)

When multiple sources provide the same SK paths, Signal K applies priority:

| Priority | Source | Paths |
|----------|--------|-------|
| 1 (highest) | `signalk-wit-imu-ble` (WIT WT901BLECL) | `navigation.attitude.*` |
| 2 | `calypso-up10` | `environment.wind.*`, `environment.outside.temperature` |
| 3 (lowest) | UDP injection (debug/test) | Any path |

> The Calypso attitude data (roll/pitch if `--compass=on`) is **overridden** by
> the WIT IMU, which is the primary attitude source. The Calypso is authoritative
> for all wind and temperature data.

---

## MOUNTING

- **Location:** Masthead (top of mast)
- **Alignment:** Arrow pointing toward bow (forward) when mounted
- **Height:** As high as possible — above sails to avoid turbulence
- **Wiring:** None — fully wireless BLE, solar self-powered
- **BLE clearance:** Ensure RPi BLE adapter (hci0) has clear line-of-sight
  (stay clear of large metal obstructions between mast and cockpit)

---

## WIND DATA — SAILING CONTEXT

### Apparent vs True Wind

| Type | Description | Use |
|------|-------------|-----|
| **Apparent Wind** | Wind felt by the boat (boat speed + true wind vector) | Sail trim |
| **True Wind** | Actual meteorological wind | Tactics, routing |
| **Wind Angle** | Angle between bow and wind direction | VMG calculations |

### Key Paths for Racing

```bash
# Verify wind data in Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/wind | jq '{
  speedApparent:  .speedApparent,
  angleApparent:  .angleApparent,
  speedTrue:      .speedTrue,
  directionTrue:  .directionTrue
}'

# Convert apparent wind speed to knots (m/s × 1.94384)
# Convert angles to degrees (radians × 180 / π)
```

---

## PRE-RACE VERIFICATION

```bash
# 1. Check BLE device is visible
calypso-anemometer info
# Expected: device "ULTRASONIC" found, battery %, firmware version

# 2. Check systemd services
sudo systemctl status calypso_anemometer calypso_watchdog

# 3. Check Signal K wind paths
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/wind | jq .

# 4. Check data freshness in Grafana
# Dashboard 04 - Wind/Current → apparent wind speed and direction
# Values should update at 1 Hz, values should be non-zero in any wind

# 5. Quick sanity check: face device into wind manually
# Apparent wind angle should approach 0° (headwind)
```

---

## KNOWN ISSUES & STATUS

| Issue | Severity | Status |
|-------|----------|--------|
| UUID parsing errors (v1.0 script) | High | ✅ RESOLVED — replaced by calypso-anemometer Python library |
| Payload parsing bugs (v1.0) | High | ✅ RESOLVED — calypso-anemometer handles all payload variants |
| Temperature conversion (v1.0) | Medium | ✅ RESOLVED — driver handles K/°C conversion correctly |
| Battery monitoring logic (v1.0) | Medium | ✅ RESOLVED — driver provides battery % via $MLXDR |
| BLE disconnect / reconnect | Medium | ✅ MITIGATED — `calypso_watchdog` service auto-restarts |
| Wind angle calculation accuracy | Low | ⏳ Pending field validation |
| `--compass=on` attitude vs WIT IMU | Note | Calypso attitude data overridden by WIT IMU (by design) |

---

## RELATIONSHIP WITH OTHER WIND SOURCES

The boat has two wind-related data sources:

| Source | Type | Status | Role |
|--------|------|--------|------|
| **Calypso UP10** | BLE wireless, masthead | ✅ Active | Primary wind sensor |
| **B&G WS320** | NMEA 2000, wired | 📍 Present on boat | Legacy instrument (Vulcan 7 FS display) |

> The B&G WS320 is a separate wired NMEA 2000 sensor connected to the Vulcan 7 FS
> chartplotter display. It does NOT feed Signal K. The Calypso UP10 is the
> **sole wind data source for Signal K, InfluxDB, and Grafana dashboards**.

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial documentation (v1.0 — incomplete, wrong manufacturer) | OC |
| 2026-05-19 | Full datasheet revision: corrected manufacturer, updated status to ✅ ACTIVE, corrected architecture (systemd + UDP, not plugin), added NMEA sentences, BLE protocol, data priority table, field verification commands | Denis / Dust |
| 2026-05-31 | Four bugs fixed: (1) bluetoothctl remove per-connection destroys bond → moved to startup-only; (2) _last_data_ts not reset on reconnect → added reset after start_notify; (3) rate 0x0A (10Hz) invalid → use 0x08 (8Hz max); (4) L2_THRESHOLD 20→10 for faster recovery. Valid rates: 0x01(1Hz) / 0x04(4Hz) / 0x08(8Hz) confirmed. | OC |

---

**Last Updated:** 2026-05-31  
**Next Action:** Validate apparent wind angle during field test (May 19) — verify sensor orientation matches boat bow

---

## DEBUG HISTORY — 2026-05-31

Four critical bugs found and fixed in field testing:

### Bug #1: bluetoothctl remove per-connection (FIXED)

**Symptom:** Connection time degraded over retries: 18min → 12min → 6min → 1.6min

**Root Cause:** Calling `bluetoothctl remove {MAC}` before EVERY connection attempt destroys the BLE bond repeatedly. Calypso firmware gets confused by bond destruction.

**Fix:** Removed per-connection remove from retry loop. Keep startup-only remove (once, + sleep 2). Bond maintained across retries.

**SHA:** b8f1c91

### Bug #2: watchdog false-positive (FIXED)

**Symptom:** Watchdog fires immediately after reconnect, before first packet arrives.

**Root Cause:** `_stats['last_data_ts']` not reset on reconnect. Watchdog uses stale timestamp from previous session.

**Fix:** Reset `_stats['last_data_ts'] = time.time()` after `start_notify`, before watchdog loop.

**SHA:** 6af4fff

### Bug #3: Invalid GATT rate byte 0x0A (FIXED)

**Symptom:** Rate configured to 10Hz, but data arriving at ~1Hz (default).

**Root Cause:** 0x0A is not a valid rate byte in Calypso UP10 firmware. Firmware silently ignores invalid byte and uses default (1Hz).

**Fix:** Changed default rate from 10 → 8 Hz. Confirmed valid rates: 0x01(1Hz) / 0x04(4Hz) / 0x08(8Hz).

**SHA:** 3ca367e

### Bug #4: L2_THRESHOLD=20 too high (OPTIMIZED)

**Symptom:** Long delay before systemd restart on persistent BLE failure.

**Root Cause:** L2_THRESHOLD=20 requires 20 L1 failures before clean exit. With exponential backoff (5s→60s), this takes ~10+ minutes.

**Fix:** Reduced L2_THRESHOLD to 10. Systemd restart now within ~2 minutes.

**SHA:** n/a (config change)

### Valid GATT Rate Bytes (Confirmed 2026-05-31)

| Byte | Rate | Status | Evidence |
|------|------|--------|----------|
| 0x01 | 1 Hz | ✅ Valid | Tested, working |
| 0x04 | 4 Hz | ✅ Valid | Original default, tested |
| 0x08 | 8 Hz | ✅ Valid | Maximum — confirmed hardware capable, rate diagnostic |
| 0x0A | 10 Hz | ❌ Invalid | Firmware ignores, falls back to 1Hz. "10" in "UP10" = max measurments, not GATT rate. |

### BLE Stability Rules (Confirmed 2026-05-31)

1. **`bluetoothctl remove {MAC}` is ONLY for startup** (once, + sleep 2)
   - Do NOT call before every retry — destroys bond
   - Do NOT call after disconnect — let bond persist across reconnects
   - If zombie detected (3+ failures), use BT_RECOVERY handler

2. **`_stats['last_data_ts']` MUST be reset after `start_notify`**
   - Fresh connection = fresh timestamp baseline
   - Prevents watchdog from seeing stale data

3. **Calypso has NO physical power button**
   - Software "power cycle" = stop service + wait 3min + start
   - Allows capacitive discharge, full BLE reset

4. **Calypso can have only ONE active BLE connection**
   - If user's phone connects, RPi BLE disconnects
   - Monitor logs for "Connection closed by peer" on demand

5. **Rate configuration must use valid GATT bytes**
   - Use CALYPSO_RATE_HZ environment variable (values: 1/4/8)
   - Driver internally maps to GATT bytes (0x01/0x04/0x08)
   - Invalid values default to 1Hz (firmware fallback)

---
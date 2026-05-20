# WITMOTION WT901BLECL — 9-AXIS IMU DATASHEET

**Manufacturer:** WitMotion Shenzhen Co., Ltd  
**Model:** WT901BLECL BLE 5.0 (AHRS IMU Sensor)  
**SoC:** Nordic nRF52832  
**Interface:** Bluetooth Low Energy 5.0 + USB Type-C (serial)  
**Date:** 2026-05-19  
**Status:** ✅ Operational — Primary attitude source (highest SK priority)

---

## SENSOR SPECIFICATIONS

### Physical

| Spec | Value |
|------|-------|
| **Dimensions** | 51.3 × 36 × 15 mm |
| **Weight** | 20 g (± 0.2 g) |
| **Battery** | 250 mAh, 3.7V lithium |
| **Battery Life** | ~10 hours continuous BLE |
| **Charging** | USB Type-C, 5V |
| **Shock Resistance** | 20,000 g |
| **Operating Temp** | -20°C to +60°C |
| **Storage Temp** | -40°C to +85°C |
| **Certifications** | CE |

### Electrical

| Spec | Value |
|------|-------|
| **Supply Voltage** | 3.3V – 5V |
| **Current Consumption** | < 40 mA |
| **BLE Chip** | Nordic nRF52832 |
| **BLE Version** | Bluetooth 5.0 |
| **BLE Range** | ≤ 50 m (open environment) |
| **Serial Baud Rate** | 115200 bps (fixed, cannot be changed) |
| **Interface** | USB Type-C (wired) + BLE 5.0 (wireless) |

---

## SENSORS & ACCURACY

### Accelerometer (MPU-9250)

| Parameter | Condition | Value |
|-----------|-----------|-------|
| **Measurement Range** | — | ±16 g (selectable: ±2/4/8/16 g) |
| **Resolution** | ±16 g | 0.0005 g/LSB |
| **RMS Noise** | BW = 100 Hz | 0.75 – 1 mg-rms |
| **Static Zero Drift** | Horizontal | ±20 – 40 mg |
| **Temperature Drift** | -40°C to +85°C | ±0.15 mg/°C |
| **Bandwidth (configurable)** | — | 5 – 256 Hz |

### Gyroscope (MPU-9250)

| Parameter | Condition | Value |
|-----------|-----------|-------|
| **Measurement Range** | — | ±2000°/s (selectable: ±250/500/1000/2000°/s) |
| **Resolution** | ±2000°/s | 0.061 (°/s)/LSB |
| **RMS Noise** | BW = 100 Hz | 0.028 – 0.07 (°/s)-rms |
| **Static Zero Drift** | Horizontal | ±0.5 – 1 °/s |
| **Temperature Drift** | -40°C to +85°C | ±0.005 – 0.015 (°/s)/°C |
| **Bandwidth (configurable)** | — | 5 – 256 Hz |

### Magnetometer (AK8963)

| Parameter | Value |
|-----------|-------|
| **Measurement Range** | ±2 Gauss |
| **Resolution** | 0.0667 mGauss/LSB |

### Attitude Angles (Fused — Kalman Filter)

| Parameter | Condition | Value |
|-----------|-----------|-------|
| **Roll Range** | X-axis | ±180° |
| **Pitch Range** | Y-axis | ±90° (singular at ±90°) |
| **Heading Range** | Z-axis | ±180° |
| **Roll/Pitch Accuracy** | — | **0.2°** |
| **Heading Accuracy** | 9-axis, magnetic calibrated | **1°** (no magnetic interference) |
| **Heading Accuracy** | 6-axis, static | **0.5°** (cumulative drift in dynamic) |
| **Angle Resolution** | Horizontal | 0.0055° |
| **Angle Temp Drift** | -40°C to +85°C | ±0.5 – 1° |

### Output Rate

| Rate | Value |
|------|-------|
| **Default** | 10 Hz |
| **Maximum** | **200 Hz** |
| **Minimum** | 0.1 Hz |
| **Configurable** | 0.1 / 0.5 / 1 / 2 / 5 / 10 / 20 / 50 / 100 / 200 Hz |

---

## ALGORITHM MODES

### 9-Axis (Default — Midnight Rider)

Uses accelerometer + gyroscope + **magnetometer** fusion via Kalman filter.
- Z-axis (heading) derived from magnetic field → stable, minimal drift
- **Requires magnetic field calibration** in deployment environment
- Recommended for marine use when away from magnetic interference (motors, alternators)

### 6-Axis (Alternative)

Uses accelerometer + gyroscope only (no magnetometer).
- Z-axis from gyroscope integration → cumulative drift over time
- Useful when significant magnetic interference present (engine room, etc.)
- Reset Z-axis angle at start of use

### Kalman Filter

Dynamic sensor fusion algorithm that:
- Reduces measurement noise
- Maintains accuracy in dynamic conditions (waves, heeling, acceleration)
- Outputs quaternions + Euler angles simultaneously

---

## OUTPUT DATA

### Default Bluetooth Packet (Flag = 0x61)

Frame structure: `0x55` + `0x61` + 18 data bytes

| Field | Bytes | Calculation | Unit |
|-------|-------|-------------|------|
| Accel X | AxL + AxH | ((AxH << 8) \| AxL) / 32768 × 16 | g (× 9.81 = m/s²) |
| Accel Y | AyL + AyH | ((AyH << 8) \| AyL) / 32768 × 16 | g |
| Accel Z | AzL + AzH | ((AzH << 8) \| AzL) / 32768 × 16 | g |
| Gyro X | WxL + WxH | ((WxH << 8) \| WxL) / 32768 × 2000 | °/s |
| Gyro Y | WyL + WyH | same | °/s |
| Gyro Z | WzL + WzH | same | °/s |
| Roll | RollL + RollH | ((RollH << 8) \| RollL) / 32768 × 180 | ° |
| Pitch | PitchL + PitchH | same | ° |
| Yaw | YawL + YawH | same | ° |

> All multi-byte data: **low byte first, high byte last** (little-endian).
> Data types are **signed short** (int16).

### Additional Data (request via register)

| Data | Command | Flag |
|------|---------|------|
| Magnetic field (Hx, Hy, Hz) | `FF AA 27 3A 00` | 0x71 |
| Quaternion (Q0, Q1, Q2, Q3) | `FF AA 27 51 00` | 0x71 |
| Temperature | `FF AA 27 40 00` | 0x71 |
| Battery voltage | `FF AA 27 64 00` | 0x71 |

---

## BLE PROTOCOL (via bleak Python library)

### Connection

```bash
# BLE device name advertised: "WT901BLE" + last 3 MAC bytes
# Example: "WT901BLE68" → MAC ending in :68

# Discovery
bluetoothctl scan on
# Look for: [NEW] Device XX:XX:XX:XX:XX:XX WT901BLEXX

# Trust and pair
bluetoothctl pair XX:XX:XX:XX:XX:XX
bluetoothctl trust XX:XX:XX:XX:XX:XX
```

### Configuration Commands

| Command | Hex | Function |
|---------|-----|---------|
| Accel calibration | `FF AA 01 01 00` | Remove accelerometer zero bias |
| Magnetic calibration | `FF AA 01 07 00` | Start 360° magnetic calibration |
| Quit calibration | `FF AA 01 00 00` | End calibration mode |
| Gyro auto-calibrate | `FF AA 01 05/06 00` | Left/Right tilt auto-cal |
| Set output rate | `FF AA 03 [RATE] 00` | See rate codes below |
| Save settings | `FF AA 00 00 00` | Persist to NVRAM |
| Restore defaults | `FF AA 00 01 00` | Factory reset |

**Output rate codes (register `0x03`):**

| Code | Rate |
|------|------|
| `0x03` | 1 Hz |
| `0x06` | 10 Hz (default) |
| `0x08` | 50 Hz |
| `0x09` | 100 Hz |
| `0x0A` | **200 Hz** (max) |

### Key Registers

| Address | Symbol | Function |
|---------|--------|---------|
| `0x03` | RATE | Output rate |
| `0x34–0x36` | AX/AY/AZ | Accelerometer X/Y/Z |
| `0x37–0x39` | GX/GY/GZ | Gyroscope X/Y/Z |
| `0x3A–0x3C` | HX/HY/HZ | Magnetometer X/Y/Z |
| `0x3D–0x3F` | Roll/Pitch/Yaw | Euler angles |
| `0x40` | TEMP | Module temperature |
| `0x51–0x54` | Q0/Q1/Q2/Q3 | Quaternion |
| `0x64` | VBAT | Battery voltage |

---

## LED STATUS

| LED | Meaning |
|-----|---------|
| 🔴 Red steady | Charging (via USB-C) |
| 🔵 Blue flash once → off | Standby (BLE advertising) |
| 🔵 Blue flashing | Pairing succeeded / connected |
| No LED | Battery depleted or off |

---

## MOUNTING — MIDNIGHT RIDER

### Physical Installation

| Parameter | Value |
|-----------|-------|
| **Location** | Center of gravity (CG) of boat hull |
| **Connection** | BLE wireless (no wiring needed) |
| **BLE reach** | ~15m to RPi (well within 50m spec) |

### Coordinate System (Physical Axes)

The WT901BLECL uses a **Northeast-Sky** frame:

```
X-axis → Forward (BOW direction)
Y-axis → Left (PORT side) ← per WitMotion official spec
Z-axis → Up (vertical)
```

> ⚠️ **Midnight Rider mounting note:** Verify Y-axis orientation during calibration.
> If Y is mounted toward starboard, roll sign will be inverted from default.
> The integration guide assumes X=bow, Y=starboard, Z=up — check against
> actual live output with boat heeled to port.

### Calibration Procedure

```bash
# 1. Static calibration (boat level at dock)
# Hold boat level — expected readings:
#   accel_x ≈ 0 g, accel_y ≈ 0 g, accel_z ≈ 1 g (9.81 m/s²)
#   roll ≈ 0°, pitch ≈ 0°

# 2. Magnetic calibration (required for 9-axis mode)
# Send: FF AA 01 07 00
# Slowly rotate sensor 360° around X, Y, Z axes (3 full rotations each)
# Send: FF AA 01 00 00 (quit calibration)

# 3. Save calibration
# Send: FF AA 00 00 00 (SAVE)

# 4. Verify via Signal K
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .value
# Expected at dock (level): roll=0.0, pitch=0.0
```

---

## SIGNAL K INTEGRATION — MIDNIGHT RIDER

### Architecture

```
WIT WT901BLECL (BLE 5.0)
     ↓ Bluetooth LE (~15m range, ~30 Hz polling)
RPi 4 (192.168.1.167) — hci0 BLE adapter
     ↓ bleak_wit.py (Python BLE driver)
     ↓ signalk-wit-imu-ble plugin (v2.2)
Signal K (port 3000, systemctl)
     ↓
navigation.attitude.{roll, pitch, yaw}    ← HIGHEST PRIORITY source
navigation.acceleration.{x, y, z}         ← Wave Analyzer input
navigation.rateOfTurn                      ← from gyro_z
     ↓
InfluxDB (port 8086) → Grafana (port 3001)
Signal K → signalk-to-nmea2000 → PGN 127257 → YDNU-02 → Vulcan 7 FS
```

### Signal K Paths Published

| SK Path | Unit | Source | Notes |
|---------|------|--------|-------|
| `navigation.attitude.roll` | radians | signalk-wit-imu-ble.XX | ± π |
| `navigation.attitude.pitch` | radians | signalk-wit-imu-ble.XX | ± π |
| `navigation.attitude.yaw` | radians | signalk-wit-imu-ble.XX | 0 – 2π |
| `navigation.rateOfTurn` | rad/s | signalk-wit-imu-ble.XX | from gyro_z |
| `navigation.acceleration.x` | m/s² | signalk-wit-imu-ble.XX | Wave Analyzer input |
| `navigation.acceleration.y` | m/s² | signalk-wit-imu-ble.XX | Wave Analyzer input |
| `navigation.acceleration.z` | m/s² | signalk-wit-imu-ble.XX | Wave Analyzer input |

### Signal K Source Reference

| Parameter | Value |
|-----------|-------|
| **SK source name** | `signalk-wit-imu-ble.XX` |
| **Plugin** | `signalk-wit-imu-ble` (v2.2) |
| **Python driver** | `/home/aneto/bleak_wit.py` |
| **Physical connection** | Bluetooth LE (hci0) |
| **Update rate in SK** | 30+ Hz |
| **Data priority** | **HIGHEST** for `navigation.attitude.*` |

### Data Source Priority

| Priority | Source | Paths |
|----------|--------|-------|
| 1 (highest) | `signalk-wit-imu-ble.XX` (WIT IMU) | `navigation.attitude.*` |
| 2 | `calypso-up10` | `environment.wind.*` |
| 3 (lowest) | UDP injection (debug) | Any path |

> The WIT IMU is the **sole source of real-time attitude** for the entire navigation stack.
> It feeds both Grafana (via InfluxDB) and the Vulcan 7 (via N2K PGN 127257).

### N2K Output — PGN 127257 (Attitude)

The WIT attitude data reaches the Vulcan 7 FS chartplotter via:

```
navigation.attitude.roll/pitch/yaw (individual scalars, WIT IMU)
     ↓
signalk-to-nmea2000 plugin
     ↓ (attitude.js — patched 2026-05-17 for Signal K 2.x compatibility)
PGN 127257 (Attitude: Roll/Pitch/Yaw)
     ↓
YDNU-02 (N2K gateway)
     ↓
Vulcan 7 FS (heel angle display)
```

> ⚠️ **Critical patch (2026-05-17):** `attitude.js` was patched to listen to
> individual scalar paths (`navigation.attitude.roll/pitch/yaw`) instead of
> the composite `navigation.attitude` object, which does NOT trigger callbacks
> in Signal K 2.x. PGN 127257 now fires correctly.

---

## WAVE ANALYZER v1.1 INTEGRATION

The WIT acceleration data is the **sole input** for the Wave Analyzer plugin:

```
navigation.acceleration.{x, y, z} (from WIT)
     ↓
Wave Analyzer v1.1
     ├─ Heel correction formula:
     │  a_vertical = -ax·sin(pitch) + ay·sin(roll)·cos(pitch) + az·cos(roll)·cos(pitch)
     │
     └─ Outputs:
          environment.water.waves.significantWaveHeight (m)
          environment.water.waves.period (s)
          environment.water.waves.seaState (0-8, Douglas scale)
```

### Why the Heel Correction Matters

| Condition | Without Correction | With v1.1 Correction |
|-----------|-------------------|---------------------|
| 0° heel | Hs = X m | Hs = X m (no difference) |
| 30° heel | Hs = **14% too low** ❌ | Hs = **correct** ✅ |

> The raw Z-axis acceleration projects less vertical component when the boat
> heels. Without correction, the wave height would be systematically
> underestimated at racing heel angles (15–35°).

---

## PLUGIN CONFIGURATION

```json
{
  "plugins": {
    "signalk-wit-imu-ble": {
      "enabled": true,
      "macAddress": "XX:XX:XX:XX:XX:XX",
      "updateRate": 30,
      "calibration": {
        "roll_offset": 0.0,
        "pitch_offset": 0.0,
        "yaw_offset": 0.0
      }
    }
  }
}
```

Config file location: `/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-ble.json`

---

## FIELD VERIFICATION

```bash
# 1. Check BLE connection
bluetoothctl info XX:XX:XX:XX:XX:XX
# Expected: "Connected: yes"

# 2. Check Signal K attitude data
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .value
# Expected at dock (level):
#   roll:  ~0.0 rad
#   pitch: ~0.0 rad
#   yaw:   any value (heading)

# 3. Check acceleration data
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation | jq '{
  attitude: .attitude.value,
  rateOfTurn: .rateOfTurn.value
}'

# 4. Check Wave Analyzer output
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/water/waves | jq .value
# Expected: significantWaveHeight, period, seaState

# 5. Heel test validation (30° heel)
# Expected: roll ≈ 0.524 rad (30°), accel_z ≈ 8.5 m/s²
# Wave Analyzer Hs should be CORRECTED (not 14% low)

# 6. Verify PGN 127257 on Vulcan 7
# Physically heel boat → observe real-time heel angle on Vulcan 7 display
# Should track WIT IMU within 1-2 seconds lag
```

---

## BATTERY MANAGEMENT

| Status | Indicator |
|--------|-----------|
| Charging | 🔴 Red LED steady |
| Full / Standby | 🔵 Blue LED (single flash) |
| Connected via BLE | 🔵 Blue LED flashing |
| Depleted | No LED |

**Pre-Race Checklist:**
- [ ] Fully charge via USB-C (≥ 1 hour before race, ideally overnight)
- [ ] Verify Blue LED flashing → BLE connected
- [ ] Verify `navigation.attitude` live in Signal K
- [ ] Verify roll/pitch ≈ 0 when boat level
- [ ] Verify Vulcan 7 shows heel angle

---

## TROUBLESHOOTING

| Issue | Cause | Fix |
|-------|-------|-----|
| No BLE connection | Battery depleted or out of range | Charge WIT, confirm Blue LED, reduce distance |
| BLE connects but no SK data | Plugin not running | `sudo systemctl restart signalk` |
| Roll/pitch drifting at rest | Accelerometer needs calibration | Run accel calibration (hold level, send `FF AA 01 01 00`) |
| Heading drifting (Z-axis) | Magnetic interference or no calibration | Run magnetic calibration or switch to 6-axis mode |
| Acceleration noisy | Normal at 30 Hz | Wave Analyzer filters this → not a problem |
| Wrong roll direction | Y-axis inverted vs mounting | Check physical mounting, adjust `roll_offset` in plugin config |
| PGN 127257 not on Vulcan 7 | SK 2.x composite path issue | ✅ FIXED in attitude.js patch (2026-05-17) |
| Data stops after 10+ hours | Battery depleted | Recharge between long sessions |

---

## KNOWN LIMITATIONS

⚠️ **Battery life:** ~10 hours. For all-day racing, charge overnight.

⚠️ **Magnetic heading:** 9-axis mode requires calibration away from magnetic sources (motors, alternators, steel). In the cockpit, proximity to the engine may affect heading accuracy.

⚠️ **Euler angle singularity:** Pitch angle has a ±90° singularity. Values beyond ±90° cause cross-coupling with roll and yaw — normal for Euler angles, not a bug.

⚠️ **6-axis dynamic drift:** If switched to 6-axis mode (no magnetometer), yaw will drift during long passages. Acceptable for short races.

---

## RACING ADVANTAGES

✅ **9-axis full motion:** Roll, pitch, yaw + acceleration all in one wireless sensor  
✅ **200 Hz capable, 30 Hz in Signal K:** Sufficient for wave analysis (Nyquist > 2× wave frequency)  
✅ **0.2° roll/pitch accuracy:** Better than most marine inclinometers  
✅ **Heel correction v1.1:** Eliminates 14% wave height error at racing heel angles  
✅ **N2K output:** Feeds Vulcan 7 FS heel display via PGN 127257  
✅ **Wireless:** No cable runs, easy seasonal installation/removal  
✅ **Compact & light:** 51.3×36×15 mm, 20g  

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial documentation (multiple spec errors) | OC |
| 2026-05-17 | attitude.js patched for SK 2.x (individual scalar paths → PGN 127257 now fires) | OC |
| 2026-05-19 | Full datasheet revision: corrected BLE version (5.0), dimensions (51.3×36×15mm), weight (20g), range (50m), accuracy (0.2°/1°), max rate (200Hz), added BLE protocol, register map, N2K integration, Wave Analyzer context | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Operational — Critical component (Wave Analyzer + Vulcan 7 heel)  
**Next Action:** Validate heel angle on Vulcan 7 during field test + confirm Wave Analyzer Hs correction

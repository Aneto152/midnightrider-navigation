# WITMOTION WT901BLECL — 9-AXIS IMU DATASHEET

**Manufacturer:** WitMotion Shenzhen Co., Ltd  
**Model:** WT901BLECL BLE 5.0 (AHRS IMU Sensor)  
**Firmware Version:** 13115 (confirmed 2026-05-30)  
**Interface:** Bluetooth Low Energy 5.0 + USB Type-C (serial)  
**Date:** 2026-05-31  
**Status:** ✅ Operational — Primary attitude source (Midnight Rider)

---

## SENSOR SPECIFICATIONS

### Physical

| Specification | Value |
|---------------|-------|
| Dimensions | 51.3 × 36 × 15 mm |
| Weight | 20 g |
| Battery | 250 mAh, 3.7V lithium-polymer |
| Battery Life | ~10 hours continuous BLE streaming |
| Charging | USB Type-C, 5V @ 500mA |
| Shock Resistance | 20,000 g peak |
| Operating Temperature | -20°C to +60°C |
| Storage Temperature | -40°C to +85°C |
| Water Resistance | IP67 (tested, conformal coating) |

### Electrical

| Specification | Value |
|---------------|-------|
| Supply Voltage | 3.3V – 5V DC |
| Current Draw | < 40 mA (BLE active) |
| BLE Chip | Nordic nRF52832 ARM Cortex-M4F |
| BLE Version | Bluetooth 5.0 (LE) |
| BLE Transmission Power | +4 dBm |
| BLE Range | ≈ 50 m (open air, -40 dBm sensitivity) |
| Serial Interface | USB CDC (115200 bps fixed) |
| GATT Services | 4 custom services (0000fff0–0000fff3) |
| Notification UUID | 0000ffe4-0000-1000-8000-00805f9a34fb |
| Write UUID | 0000ffe9-0000-1000-8000-00805f9a34fb |

### Accelerometer (Invensense MPU-9250)

| Parameter | Value |
|-----------|-------|
| Sensor Type | 3-axis MEMS accelerometer |
| Measurement Range | ±16 g (configurable: ±2/4/8/16 g) |
| Resolution | 0.0005 g/LSB |
| RMS Noise | 0.75–1 mg-rms (BW=100 Hz) |
| Zero Offset | ±20–40 mg |
| Temperature Drift | ±0.15 mg/°C |
| Response Time | ~5 ms |

### Gyroscope (Invensense MPU-9250)

| Parameter | Value |
|-----------|-------|
| Sensor Type | 3-axis MEMS gyroscope |
| Measurement Range | ±2000°/s (configurable: ±250/500/1000/2000°/s) |
| Resolution | 0.061 (°/s)/LSB |
| RMS Noise | 0.028–0.07 (°/s)-rms |
| Zero Offset | ±0.5–1°/s |
| Temperature Drift | ±0.005–0.015 (°/s)/°C |
| Response Time | ~2 ms |

### Magnetometer (Asahi Kasei AK8963)

| Parameter | Value |
|-----------|-------|
| Sensor Type | 3-axis fluxgate magnetometer |
| Measurement Range | ±2 Gauss (±200 μT) |
| Resolution | 0.0667 mGauss/LSB (≈ 0.007 μT/LSB) |
| RMS Noise | ~1.5 μT-rms |
| Scale Factor | Raw int16 → divide by 10 for μT |
| Typical Field (Earth) | 25–65 μT (latitude/location dependent) |
| Factory Calibration | Pre-calibrated (ASA sensitivity adjustment included) |
| Saturation Field | ±8 Gauss |

### Temperature Sensor (Internal, BMP280)

| Parameter | Value |
|-----------|-------|
| Sensor Type | Bosch BMP280 (barometric pressure + temp) |
| Temperature Range | -40°C to +85°C |
| Temperature Resolution | 0.01°C |
| Temperature Error | ±1°C typical |
| Pressure Range | 300–1100 hPa |
| Pressure Resolution | 0.18 Pa |
| Pressure Accuracy | ±100 Pa typical |
| Auto-stream Packet | 0x54 (every 100 ms @ 10 Hz) |

### Attitude Accuracy (9-Axis Kalman Filter)

| Parameter | Condition | Value |
|-----------|-----------|-------|
| Roll/Pitch Accuracy | Static, calibrated | ±0.2° |
| Yaw/Heading Accuracy | 9-axis, calibrated, static | ±1° |
| Yaw/Heading Accuracy | 9-axis, calibrated, dynamic | ±2–3° |
| Angle Resolution | — | 0.0055° (0.002 rad) |
| Euler Convention | Output format | ZYX (Yaw-Pitch-Roll) |
| Response Time | 10 Hz update | ~100 ms |
| Convergence Time | Power-on to stable | 60–90 s (FILTK=30) / 30–45 s (FILTK=200) |

### Output Rates (Configurable via Register 0x0C)

| Frequency | Command | Remarks |
|-----------|---------|---------|
| 0.1 Hz | — | Not recommended (async BLE buffering) |
| 0.5 Hz | — | — |
| 1 Hz | — | — |
| 2 Hz | — | — |
| 5 Hz | — | — |
| **10 Hz** | **Default (Midnight Rider)** | **Optimal for sailing (10× per second)** |
| 20 Hz | — | Higher power consumption |
| 50 Hz | — | Reserved for research |
| 100 Hz | — | Maximum for USB serial |
| 200 Hz | Maximum BLE | Minimal buffer, real-time only |

---

## ALGORITHM & FILTERING

### 9-Axis Mode (Default — Recommended for Midnight Rider)

Uses accelerometer + gyroscope + magnetometer Kalman fusion:

- **X-axis (Roll):** Primarily from accelerometer gravity projection + gyro rate integration
- **Y-axis (Pitch):** Primarily from accelerometer gravity projection + gyro rate integration
- **Z-axis (Heading/Yaw):** From magnetometer field direction (most accurate when calibrated)

**Advantages:**
- Magnetic north reference → zero long-term heading drift
- Stable heading even with extended sailing (hours)
- Requires calibration in local magnetic environment

**Disadvantages:**
- Sensitive to ferrous materials (engine, rigging)
- Requires magnetic declination adjustment for accurate compass heading
- Initial calibration time ~30–60 seconds

### 6-Axis Mode (Alternative)

Uses accelerometer + gyroscope only (magnetometer disabled):

- **X/Y (Roll/Pitch):** From accelerometer + gyroscope fusion
- **Z-axis (Yaw):** From gyroscope integration only (no magnetic reference)

**Advantages:**
- No magnetic interference → suitable for engine compartments
- Faster convergence (~15 s)

**Disadvantages:**
- **Heading drifts ~1°/minute** during dynamic motion (due to gyro bias)
- Not recommended for unattended sailing > 30 minutes

> **Midnight Rider uses 9-axis mode permanently** (per 2026-05-29 testing)

---

## KALMAN FILTER TUNING — FILTK PARAMETER

Register 0x25 (FILTK) controls the Kalman filter's process noise covariance (Q matrix):

| FILTK Value | Behavior | Response Time | Use Case |
|-------------|----------|----------------|----------|
| 1 | Unstable, max real-time | < 50 ms | Research only |
| 10 | Very noisy, fast response | ~100 ms | High-dynamic maneuvers |
| 30 | **Default factory** | ~300 ms | General IMU use |
| 50 | Moderate smoothing | ~500 ms | Slow vehicles |
| 100 | Strong smoothing | ~1–2 s | Stable platforms |
| **200** | **Recommended for sailing** | **~800 ms** | **Optimal for 10 Hz maritime** |
| 1000 | Very smooth, slow response | ~5–10 s | Stationary/mapping |
| 10000 | Maximum averaging | > 30 s | Extreme stability |

### Setting FILTK=200 (Official Method via WitMotion App)

**Mobile App Path:**
1. Download WitMotion app (iOS/Android)
2. Connect to WT901BLECL via Bluetooth
3. Navigate: **Settings** → **Filter** → **K-value**
4. Input `200`
5. Press **Save** button
6. Firmware will reboot (~2–3 seconds)
7. Verify: Reconnect and read K-value to confirm persistence

**BLE Register Write Method (Not Recommended)**
- Command: `FF AA 27 25 C8 00` (where 0xC8 0x00 = 200 in little-endian)
- Requires UNLOCK command first: `FF AA 69 88 B5`
- Persist with SAVE command: `FF AA 00 00 00`
- **Challenge:** Requires precise timing and ACK verification
- **Midnight Rider:** Use official WitMotion app (more reliable)

---

## BLUETOOTH LOW ENERGY (BLE) INTERFACE

### GATT Services & Characteristics

| Service UUID | Characteristic | UUID | Type | Notes |
|---|---|---|---|---|
| 0000fff0 | — | — | Service | Private service 1 |
| 0000fff1 | — | — | Service | Private service 2 |
| 0000fff2 | — | — | Service | Private service 3 |
| 0000fff3 | — | — | Service | Private service 4 |

### Key UUIDs (Midnight Rider Implementation)

| UUID | Function | Direction | Purpose |
|------|----------|-----------|---------|
| `0000ffe4-0000-1000-8000-00805f9a34fb` | **Notify** | Device → RPi | Receive sensor data packets |
| `0000ffe9-0000-1000-8000-00805f9a34fb` | **Write** | RPi → Device | Send commands (ENABLE_QUAT, CMD_MAG, CMD_PRES) |

### Connection Parameters (Typical)

| Parameter | Value |
|-----------|-------|
| Connection Interval | 7.5 ms (min) – 4000 ms (max) |
| Supervision Timeout | 32 s |
| MTU Size | 20 bytes (standard BLE) |
| Packet Loss Threshold | ~5% before reconnection |

---

## PACKET FORMATS (FIRMWARE PROTOCOL)

### Packet Structure

All packets follow standard WitMotion frame format:

```
0x55 [Flag] [REG_L] [REG_H] [Data0] [Data1] ... [Checksum]
```

- **Byte 0:** `0x55` (frame start)
- **Byte 1:** `Flag` (0x71 for sensor data, 0x5F for register read response, etc.)
- **Byte 2:** `REG_L` (low byte of register address, 0x51 for quaternion)
- **Byte 3:** `REG_H` (high byte, typically 0x00)
- **Bytes 4+:** Sensor data or register values
- **Last:** Checksum (sum of all bytes mod 256)

### Quaternion Packet (0x55 0x71 0x51 ...)

**Command to enable:** `FF AA 27 51 00` (ENABLE_QUAT_CMD)

**Response format:**
```
0x55 0x71 0x51 0x00 [Q0_L] [Q0_H] [Q1_L] [Q1_H] [Q2_L] [Q2_H] [Q3_L] [Q3_H] [Checksum]
```

| Field | Offset | Type | Range | Notes |
|-------|--------|------|-------|-------|
| Q0 | 4–5 | int16 LE | ±32768 | X-component / 32768.0 |
| Q1 | 6–7 | int16 LE | ±32768 | Y-component / 32768.0 |
| Q2 | 8–9 | int16 LE | ±32768 | Z-component / 32768.0 |
| Q3 | 10–11 | int16 LE | ±32768 | W-component (real part) / 32768.0 |

**WitMotion Quaternion Convention:** `(Q0, Q1, Q2, Q3) = (x, y, z, w)`

> **Critical:** W-component (Q3) is always last in the frame; not first as in typical graphics libraries.

### Magnetic Field Packet (0x55 0x71 0x3A ... — CMD_MAG Response)

**Command to poll:** `FF AA 27 3A 00` (CMD_MAG)

**Response format:**
```
0x55 0x71 0x3A 0x00 [HX_L] [HX_H] [HY_L] [HY_H] [HZ_L] [HZ_H] [Checksum]
```

| Field | Offset | Type | Range | Conversion |
|-------|--------|------|-------|------------|
| HX | 4–5 | int16 LE | ±32768 | HX / 10.0 → μT |
| HY | 6–7 | int16 LE | ±32768 | HY / 10.0 → μT |
| HZ | 8–9 | int16 LE | ±32768 | HZ / 10.0 → μT |

**Polling Rate:** ~1 Hz (every 10 quaternion packets at 10 Hz output rate)

### Pressure Packet (0x55 0x71 0x45 ... — CMD_PRES Response)

**Command to poll:** `FF AA 27 45 00` (CMD_PRES)

**Response format:**
```
0x55 0x71 0x45 0x00 [PRES_LL] [PRES_LH] [PRES_HL] [PRES_HH] [Checksum]
```

| Field | Offset | Type | Range | Conversion |
|-------|--------|------|-------|------------|
| Pressure | 4–7 | uint32 LE | 50000–110000 | Pa (direct) or / 1000 → kPa |

**Valid Range:** 500–1100 hPa (5 km altitude to sea level)  
**Polling Rate:** ~0.3 Hz (every 30 quaternion packets)

### Temperature Packet (0x55 0x54 ... — Auto-Stream)

**Auto-stream (no polling required)** — sent every 100 ms with quaternion

**Response format:**
```
0x55 0x54 [HX_L] [HX_H] [HY_L] [HY_H] [HZ_L] [HZ_H] [T_L] [T_H] [Checksum]
```

| Field | Offset | Type | Range | Conversion |
|-------|--------|------|-------|------------|
| HX | 2–3 | int16 LE | ±32768 | Raw magnetic (internal cal) |
| HY | 4–5 | int16 LE | ±32768 | — |
| HZ | 6–7 | int16 LE | ±32768 | — |
| Temperature | 8–9 | int16 LE | -4000 to 8500 | / 100.0 → °C |

**Temperature Accuracy:** ±1°C typical  
**Update Rate:** 10 Hz (same as primary output rate)

---

## CALIBRATION PROCEDURES

### Magnetic Calibration (9-Axis Mode)

**Factory Default:** Pre-calibrated for Earth's magnetic field at specific location

**Re-calibration (if heading drifts in local environment):**

1. **Figure-8 Motion (Recommended for maritime):**
   - Hold WIT level
   - Rotate 360° around vertical Z-axis (2–3 full rotations)
   - Rotate 360° around forward X-axis (2–3 full rotations)
   - Rotate 360° around starboard Y-axis (2–3 full rotations)
   - Takes ~1–2 minutes total

2. **Verification:**
   - Heading should stabilize to ±1° within 30 s
   - Check against compass app on phone (must account for magnetic declination)

3. **Save to NVRAM:**
   - WitMotion app → Settings → Calibration → Magnetic → Save
   - Firmware reboots (~3 s)

### Gyroscope Zero-Offset Calibration

**Factory Default:** Pre-calibrated to ±0.5°/s

**Re-calibration (if gyro bias drifts):**

1. **Static Placement:**
   - Place WIT on perfectly level surface
   - Do not move for 10 seconds
   - App will auto-detect and calibrate

2. **Save to NVRAM:**
   - Settings → Calibration → Gyroscope → Save

---

## INTEGRATION WITH SIGNAL K (Midnight Rider)

### Primary Data Paths

| Signal K Path | Data Type | Rate | Source Register | Notes |
|---|---|---|---|---|
| `navigation.attitude.roll` | rad | 10 Hz | 0x71 (q_raw) | ±π radians |
| `navigation.attitude.pitch` | rad | 10 Hz | 0x71 | ±π/2 radians |
| `navigation.attitude.yaw` | rad | 10 Hz | 0x71 | ±π radians |
| `navigation.headingMagnetic` | rad | 10 Hz | 0x71 | 0–2π (compass) |
| `sensors.wit.quaternion.w` | unitless | 10 Hz | 0x71 reg 0x51 | W component (real) |
| `sensors.wit.quaternion.x` | unitless | 10 Hz | 0x71 reg 0x51 | X component |
| `sensors.wit.quaternion.y` | unitless | 10 Hz | 0x71 reg 0x51 | Y component |
| `sensors.wit.quaternion.z` | unitless | 10 Hz | 0x71 reg 0x51 | Z component |
| `sensors.wit.magneticField.x` | μT | ~1 Hz | 0x71 reg 0x3A | CMD_MAG polling |
| `sensors.wit.magneticField.y` | μT | ~1 Hz | 0x71 reg 0x3A | — |
| `sensors.wit.magneticField.z` | μT | ~1 Hz | 0x71 reg 0x3A | — |
| `environment.inside.temperature` | K | ~10 Hz | 0x54 | From auto-stream |
| `environment.outside.pressure` | Pa | ~0.3 Hz | 0x71 reg 0x45 | CMD_PRES polling |

### Attitude Transform (Boat Frame)

WIT outputs Euler angles in sensor-native frame. Midnight Rider applies mounting correction:

**Mount Orientation:** Z-axis vertical (accelerometer Y points forward along boat centerline)

**Transform:** 90° rotation around Z-axis (starboard = +X)

```
Roll_boat = -Pitch_sensor
Pitch_boat = Roll_sensor
Yaw_boat = Yaw_sensor (unchanged)
```

**Result:** Roll/Pitch/Yaw now match boat-frame convention (ISO 11783)

---

## RECOVERY & RELIABILITY

### Bluetooth Connection Stability

| Issue | Root Cause | Mitigation |
|-------|-----------|-----------|
| Frequent disconnects | BlueZ cache corruption | Clear cache: `bluetoothctl remove [MAC]` |
| No data after connect | GATT discovery timeout | Hardcode notify/write UUIDs |
| Slow reconnection | Device in advertising state | Poll ENABLE_QUAT after reconnect |
| Data loss during reconfig | WIT firmware busy | Add 5s delay after ENABLE_QUAT write |

### Recovery Layers (Midnight Rider Driver)

| Layer | Trigger | Action | Timeout |
|-------|---------|--------|---------|
| **L0** | Data missing < 2 packets | None (expected gaps) | — |
| **L1** | No data > 200 ms | Backoff reconnection (5–60 s) | 10× retry |
| **L2** | No data > 10 s | Clean disconnect + systemd restart | Infinite |
| **BT_RECOVERY** | hci0 adapter hang | `bluetoothctl remove MAC` + reconnect | On-demand |

---

## POWER BUDGET (Battery Life Estimation)

### Continuous Operation

| Scenario | Current Draw | Battery Life |
|----------|--------------|--------------|
| 10 Hz BLE only | 12 mA | ~20 hours |
| 10 Hz BLE + USB powered | 30 mA | ∞ (external power) |
| Active calibration (mag figure-8) | 35 mA | ~7 hours |
| Idle (BLE advertising) | 5 mA | ~50 hours |

> **Midnight Rider Deployment:** Always power-coupled to 12V yacht electrical system via USB power bank (no battery degradation)

---

## FIRMWARE UPGRADE

### Current Version

**Firmware:** 13115 (confirmed stable 2026-05-30)

**Source:** WitMotion official tools (Windows/Mac application)

**Procedure:**
1. Connect WT901BLECL via USB Type-C to laptop
2. Run WitMotion firmware updater
3. Select latest .bin file from WitMotion website
4. Press **Update** and wait ~30 s
5. Device reboots automatically

---

## TROUBLESHOOTING

### "No quaternion data flowing"

**Check:**
- BLE connected via `bluetoothctl info [MAC]`
- Notify UUID subscribed: `gatttool -b [MAC] --characteristics | grep ffe4`
- Send ENABLE_QUAT: `gatttool -b [MAC] --char-write-req -a 0x[HANDLE] -n FFAA275100`
- Wait 5 seconds
- Check for incoming notifications: `gatttool -b [MAC] --listen`

### "Heading stuck / not updating"

**Check:**
- 9-axis mode enabled (Settings → Algorithm → 9-axis)
- Magnetic calibration recent (< 1 month)
- No ferrous objects within 30 cm of device
- Magnetic declination configured (if using compass navigation)

### "Temperature reading -40°C or +85°C"

**Check:**
- BLE packet 0x54 being received
- Offset 8–9 bytes parsed correctly
- Sanity check: -40 < temp_c < 85 (WIT spec limits)
- Device mounted away from heat sources (engine, cabin roof)

### "Pressure always 50 kPa (min value)"

**Check:**
- CMD_PRES being sent: `FF AA 27 45 00`
- Response packet flag 0x71 and register 0x45
- Barometric sensor not blocked (small vent hole on device)
- Altitude < 5000 m above sea level

---

## REFERENCES

- **Official Datasheet:** WitMotion WT901BLECL v1.4 (Chinese + English)
- **BLE GATT:** https://www.bluetooth.com/xml-resources/documents/

---

**Last Updated:** 2026-05-31  
**Maintained By:** Midnight Rider Navigation Project  
**Operational Since:** 2026-05-19 (field test)  
**Production Deployment:** 2026-05-22 (Block Island Race)

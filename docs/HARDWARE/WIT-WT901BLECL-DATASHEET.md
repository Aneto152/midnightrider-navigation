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
| Water Resistance | None (no IP rating — protect from spray) |

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
| Temperature Source | 0x54 auto-stream packet (NOT 0x40 register — returns 0 via BLE poll) |

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

## PACKET FORMATS (FIRMWARE PROTOCOL — Firmware 13115)

### Packet Structure (Critical Fix — 2026-05-30)

⚠️ **CRITICAL:** Byte offsets corrected from earlier erroneous documentation.

All packets follow standard WitMotion frame format:

```
0x55 [Flag] [REG_L] [REG_H] [Data0] [Data1] ... [CheckSum]
```

- **Byte 0:** `0x55` (frame start sync)
- **Byte 1:** `Flag` (0x71 for read response, 0x54 for auto-stream, etc.)
- **Byte 2:** `REG_L` (low byte of register address — **NOT data, just echo**)
- **Byte 3:** `REG_H` (high byte, typically 0x00 — **NOT data, just echo**)
- **Bytes 4–19:** **Register data starts here** (8 consecutive registers, 2 bytes each)
- **Byte 20:** Checksum (sum of all bytes mod 256)

> ⚠️ **Bug fixed 2026-05-30:** Old code incorrectly read data from offset 2 (the register address itself). Correct data offset is 4.

### Quaternion Packet (0x55 0x71 0x51 ... — register 0x51)

**Command to request:** `FF AA 27 51 00` (read register 0x51)

**Response format:**
```
0x55 0x71 0x51 0x00 [Q0_L] [Q0_H] [Q1_L] [Q1_H] [Q2_L] [Q2_H] [Q3_L] [Q3_H] [CheckSum]
```

| Field | Offset | Type | Range | Formula |
|-------|--------|------|-------|----------|
| Q0 | 4–5 | int16 LE | ±32768 | / 32768.0 = **x component** |
| Q1 | 6–7 | int16 LE | ±32768 | / 32768.0 = **y component** |
| Q2 | 8–9 | int16 LE | ±32768 | / 32768.0 = **z component** |
| Q3 | 10–11 | int16 LE | ±32768 | / 32768.0 = **w component (scalar)** |

**WitMotion Quaternion Convention:** `(Q0, Q1, Q2, Q3) = (x, y, z, w)`

> ⚠️ **Critical:** W-component (scalar) is Q3, NOT Q0. This differs from graphics/robotics libraries that often use (w, x, y, z). **WitMotion always places w last.**

**Example from app (2026-05-30):**
```
App display: Q0=-0.007  Q1=0.064  Q2=0.016  Q3=0.997
             [x]       [y]       [z]       [w=scalar, dominant]
```

**Python decoder:**
```python
def decode_0x71_packet(data: bytes) -> dict | None:
    if len(data) < 12 or data[0] != 0x55 or data[1] != 0x71 or data[2] != 0x51:
        return None
    def s16(off): return struct.unpack_from('<h', data, off)[0]
    return {
        'q0': s16(4) / 32768.0,   # x
        'q1': s16(6) / 32768.0,   # y
        'q2': s16(8) / 32768.0,   # z
        'q3': s16(10) / 32768.0,  # w (scalar)
    }

# Usage in math (standard w, x, y, z convention):
q_normalized = (q_raw['q3'], q_raw['q0'], q_raw['q1'], q_raw['q2'])
```

### Magnetic Field Packet (0x55 0x71 0x3A ... — register 0x3A)

**Command to poll:** `FF AA 27 3A 00` (read register 0x3A)

**Response format:**
```
0x55 0x71 0x3A 0x00 [HX_L] [HX_H] [HY_L] [HY_H] [HZ_L] [HZ_H] ...
                     [Roll_L] [Roll_H] [Pitch_L] [Pitch_H] [Yaw_L] [Yaw_H]
                     [Temp_L] [Temp_H] [D0_L] [D0_H] [CheckSum]
```

| Field | Offset | Type | Range | Conversion |
|-------|--------|------|-------|------------|
| HX | 4–5 | int16 LE | ±32768 | / 10.0 → **μT (magnetic X)** |
| HY | 6–7 | int16 LE | ±32768 | / 10.0 → **μT (magnetic Y)** |
| HZ | 8–9 | int16 LE | ±32768 | / 10.0 → **μT (magnetic Z)** |
| Roll (internal) | 10–11 | int16 LE | — | **NOT published to Signal K** |
| Pitch (internal) | 12–13 | int16 LE | — | **NOT published — gimbal lock singularity** |
| Yaw (internal) | 14–15 | int16 LE | — | **NOT published** |
| Temperature | 16–17 | int16 LE | -4000 to 8500 | **Returns 0 via BLE poll — use 0x54 auto-stream instead** |
| D0Status | 18–19 | int16 LE | — | Status flags |

> ⚠️ **Temperature:** The 0x3A response always returns 0 for temperature when polled via BLE. Use the 0x54 auto-stream packet instead (see below).

> ⚠️ **WIT Internal Euler:** The Roll/Pitch/Yaw values in this packet are WIT's internal Euler representation. In Midnight Rider's vertical mounting (Z=bow, Y=keel=vertical), the Pitch axis has a ±90° gimbal lock singularity when heading changes ±90° from North. We use quaternion instead to avoid this.

**Polling Rate:** ~1 Hz (every 10 quaternion packets at 10 Hz output rate)

### Pressure Packet (0x55 0x71 0x45 ... — register 0x45)

**Command to poll:** `FF AA 27 45 00` (read register 0x45)

**Response format:**
```
0x55 0x71 0x45 0x00 [PRES_L] [PRES_H] [HEIGHT_L] [HEIGHT_H] ...
```

| Field | Offset | Type | Range | Conversion |
|-------|--------|------|-------|------------|
| Pressure (L) | 4–5 | uint16 LE | 0–65535 | Lower 16 bits |
| Pressure (H) | 6–7 | uint16 LE | 0–65535 | Upper 16 bits |
| Height (L) | 8–9 | int16 LE | — | Altitude lower |
| Height (H) | 10–11 | int16 LE | — | Altitude upper |

**Pressure Calculation:**
```python
pressure_pa = (pressure_h << 16) | pressure_l
# Example: 101599 Pa = 101.599 kPa ≈ 1 atm
```

**Valid Range:** 50000–110000 Pa (500–1100 hPa)  
**Sanity Check:** Reject outside this range (error condition)  
**Polling Rate:** ~0.3 Hz (every 30 quaternion packets)

### Temperature Packet (0x55 0x54 ... — Auto-Stream, NOT polled)

**Auto-stream (no polling required)** — WIT broadcasts every 100 ms automatically

> ℹ️ This is the **ONLY reliable source of temperature via BLE**. Register 0x40 and the 0x3A response both return 0 on BLE.

**Packet format:**
```
0x55 0x54 [HX_L] [HX_H] [HY_L] [HY_H] [HZ_L] [HZ_H] [T_L] [T_H] [CheckSum]
```

| Field | Offset | Type | Range | Conversion |
|-------|--------|------|-------|------------|
| HX (mag) | 2–3 | int16 LE | ±32768 | Raw magnetic X (internal calibration) |
| HY (mag) | 4–5 | int16 LE | ±32768 | Raw magnetic Y |
| HZ (mag) | 6–7 | int16 LE | ±32768 | Raw magnetic Z |
| **Temperature** | **8–9** | **int16 LE** | **-4000 to 8500** | **/ 100.0 → °C** |

**Example:** Temperature bytes `0xBD 0x09` → `int16(0x09BD)` = 2493 → 2493/100 = **24.93°C** (matches app reading 24.5°C ± rounding)

**Temperature Accuracy:** ±1°C typical  
**Update Rate:** 10 Hz (same as quaternion/primary output rate)  
**Source:** Bosch BMP280 sensor mounted inside WIT enclosure

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

### Attitude Transform (Boat Frame — Midnight Rider J/30)

WIT physical mounting (inside companionway bulkhead):
- **WIT-X axis** → STARBOARD (tribord, rightward)
- **WIT-Y axis** → toward KEEL (downward, -masthead, vertical in boat)
- **WIT-Z axis** → BOW (forward, longitudinal along boat centerline)

**Boat attitude mapping:**
- **Boat ROLL** (heel) = rotation around WIT-Z (bow axis)
- **Boat PITCH** (trim) = rotation around WIT-X (starboard axis)
- **Boat YAW** (heading) = rotation around WIT-Y (keel = vertical axis)

**Why Quaternion (not Euler)?**
In this vertical mounting, a heading change (rotating around the vertical WIT-Y axis) directly rotates around WIT's Pitch axis. At heading ±90° from calibration North, WIT internal Pitch = ±90° → **gimbal lock singularity**. Quaternion avoids this entirely.

**Mount Correction Applied (quaternion space):**
```python
MOUNT_AXIS = 'z'      # Rotation axis (Z=bow)
MOUNT_DEG = 90.0      # Rotation magnitude (degrees)
# Theoretical: q_mount = (0.5, 0.5, 0.5, 0.5) for 120° around (1,1,1) axis
```

**Result:** Quaternion output in boat-frame convention, then converted to ISO 11783 Roll/Pitch/Yaw

> ⚠️ **Physical verification on boat required** to confirm rotation direction signs.

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

## CALIBRATION PROCEDURE (Critical — Install Direction = Vertical)

> ⚠️ **Root cause of original malfunction (2026-05-30):** WIT was calibrated upside down (tête en bas) + in Horizontal mode (default). The Kalman filter's gravity reference was inverted, causing ALL angles to converge to 0° regardless of actual physical orientation.

### Step-by-Step Calibration

**1. SET INSTALL DIRECTION (CRITICAL):**
   - Open WitMotion app (iOS/Android)
   - Connect to WT901BLECL via Bluetooth
   - Navigate: **Settings** → **Configuration** → **Installation Direction**
   - Select **"Vertical"** (not the default "Horizontal")
   - Tap **Save** → Device reboots (~2–3 seconds)
   - Verify LED pattern after save

> ⚠️ This setting tells the Kalman filter which axis is vertical (gravity reference). "Vertical" means Y-axis points toward Earth's center (keel direction in boat).

**2. ACCELEROMETER CALIBRATION:**
   - Hold WIT in actual mounted position (Z=bow, horizontal, as installed on boat)
   - App → **Calibrate** → **Acceleration Calibration**
   - Hold perfectly still for 5 seconds
   - Press **Finish** → **Save** → Device reboots
   - Verify: Roll/Pitch should read ≈ 0° when boat is level

**3. MAGNETIC CALIBRATION (for 9-axis heading accuracy):**
   - App → **Calibrate** → **Magnetic Calibration**
   - Slowly rotate WIT 360° around **X-axis** (2–3 full rotations) — side to side
   - Slowly rotate WIT 360° around **Y-axis** (2–3 full rotations) — up/down
   - Slowly rotate WIT 360° around **Z-axis** (2–3 full rotations) — front to back
   - Press **Finish** → **Save**
   - Total time: ~2–3 minutes per axis (6–9 minutes total)

**4. HEADING REFERENCE CALIBRATION (set Z-axis = 0° = Magnetic North):**
   - Orient WIT-Z axis (bow marking) toward magnetic North (compass, phone app)
   - App → **Calibrate** → **Reset Z-axis Angle** (or "Heading Reset")
   - Press **Save**
   - This sets heading zero reference for navigation

**5. FILTER TUNING (FILTK Parameter):**
   - App → **Settings** → **Filter** → **K-value**
   - Set to **200** (optimal for sailing; default 30 is too conservative)
   - Press **Save** → Device reboots
   - Convergence time should improve: 60–90s (FILTK=30) → ~10s (FILTK=200)

**6. FINAL VERIFICATION:**
   ```bash
   # Check SK attitude (boat level expected: roll≈0, pitch≈0)
   curl -s localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | python3 -c "
   import sys, json, math
   d = json.load(sys.stdin)
   v = d.get('value', {})
   print(f'Roll: {math.degrees(v.get("roll",0)):.1f}° (expected ≈ 0)')
   print(f'Pitch: {math.degrees(v.get("pitch",0)):.1f}° (expected ≈ 0)')
   print(f'Yaw: {math.degrees(v.get("yaw",0)):.1f}° (compass heading)')
   "
   ```

**7. QUICK TILT TEST:**
   - Tilt WIT ~30° in roll direction (heel direction)
   - Signal K should show ≈30° within < 5 seconds (FILTK=200)
   - Response should NOT take 60+ seconds

---

## SIGNAL K INTEGRATION — MIDNIGHT RIDER (2026-05-30 Architecture)

### Data Flow

```
WT901BLECL BLE 5.0 (companionway bulkhead)
  ↓ Bluetooth LE (~15m range, 10 Hz polling)
RPi 4 (192.168.1.167) — hci0 BLE adapter
  ↓
ble/wit-ble-direct.py (Python BLE driver — wit-ble-direct systemd service)
  ├─ Imports ble_common.py (shared BLE infrastructure)
  ├─ decode_0x71_packet() → quaternion (register 0x51)
  ├─ decode_0x71_mag_packet() → magnetic field (register 0x3A)
  ├─ decode_0x71_pres_packet() → pressure (register 0x45)
  ├─ decode_0x54_packet() → temperature (0x54 auto-stream)
  ├─ decode_0x61_packet() → accel + gyro (0x61 auto-stream)
  ├─ apply_mounting_and_extract() → quaternion math + boat frame
  └─ publish_delta() → UDP:4123 → Signal K delta format
  ↓
Signal K (localhost:3000, systemd service)
  ├─ Stores 13 data paths (attitude, quaternion, mag, accel, temp, pressure)
  ├─ Exposes REST API (http://localhost:3000/signalk/v1/api/...)
  └─ WebSocket (ws://localhost:3000/signalk/v1/stream)
  ↓
InfluxDB (localhost:8086, docker) ← Time-series data
  ↓
Grafana (localhost:3001, docker) ← Dashboards
```

### BLE Driver State Machine

```
UNINITIALIZED:
  → Send ENABLE_QUAT_CMD (FF AA 27 51 00) once
  → Wait 5 seconds (WIT applies config internally)
  → WIT auto-resets after 3+ seconds
  → State → WAIT_RECONNECT

WAIT_RECONNECT:
  → Poll ENABLE_QUAT_CMD every 100ms (10 Hz) to trigger response
  → Reconnect to BLE when first data arrives
  → Subscribe to NOTIFY UUID (0000ffe4-...)
  → State → STREAMING

STREAMING:
  → Poll ENABLE_QUAT_CMD every 100ms (10 Hz output rate)
  → Poll CMD_MAG every 1s (~1 Hz)
  → Poll CMD_PRES every 3s (~0.3 Hz)
  → Receive 0x61 auto-stream (accel + gyro, 10 Hz)
  → Receive 0x54 auto-stream (temperature, 10 Hz)
  → Publish all data to SK via UDP:4123
  → If no data for 10s → L2 recovery
```

### Recovery Mechanisms

| Layer | Trigger | Action | Result |
|-------|---------|--------|--------|
| **L0** | Single packet gap | None (normal BLE buffering) | — |
| **L1** | No data > 200 ms | Exponential backoff (5s → 30s → 60s) | Reconnect N times |
| **L2** | No data > 10 s | Clean disconnect + systemd restart | Service auto-restarts via Restart=on-failure |
| **BT_RECOVERY** | Zombie BLE session | `bluetoothctl disconnect MAC`, `bluetoothctl remove MAC` | Fresh adapter state |

> ⚠️ **No hci0 resets:** L2 clean exit preserves Bluetooth adapter state. This prevents disruption to Calypso anemometer (also on hci0).

### Shared Infrastructure (ble_common.py)

All BLE drivers (WIT, Calypso, SOK) share:
- `setup_logger()` — RotatingFileHandler, 5MB max, 3 backups
- `acquire_singleton()` / `release_singleton()` — PID file locking (prevent multiple instances)
- `publish_delta()` — UDP:4123 → Signal K delta format
- `check_ble_adapter()` — hci0 availability check
- `check_sk_reachable()` — Signal K HTTP health check (localhost:3000)
- `bt_recovery()` — bluetoothctl zombie cleanup
- `setup_signal_handlers()` — graceful SIGTERM/SIGINT (no sys.exit() calls)

### Signal K Data Paths Published

| SK Path | Unit | Rate | Source Packet | Notes |
|---------|------|------|---------------|-------|
| navigation.attitude.roll | rad | 10 Hz | 0x71 quat | + = starboard down (heel) |
| navigation.attitude.pitch | rad | 10 Hz | 0x71 quat | + = bow up (trim) |
| navigation.attitude.yaw | rad | 10 Hz | 0x71 quat | magnetic heading, 0–2π |
| navigation.headingMagnetic | rad | 10 Hz | 0x71 quat | same as yaw |
| navigation.acceleration.x | m/s² | 10 Hz | 0x61 accel | along bow axis |
| navigation.acceleration.y | m/s² | 10 Hz | 0x61 accel | along port axis |
| navigation.acceleration.z | m/s² | 10 Hz | 0x61 accel | vertical |
| navigation.rateOfTurn | rad/s | 10 Hz | 0x61 gyro_z | yaw angular velocity |
| sensors.wit.quaternion.w | — | 10 Hz | 0x71 quat | raw Q3 (scalar/w-component) |
| sensors.wit.quaternion.x | — | 10 Hz | 0x71 quat | raw Q0 (x-component) |
| sensors.wit.quaternion.y | — | 10 Hz | 0x71 quat | raw Q1 (y-component) |
| sensors.wit.quaternion.z | — | 10 Hz | 0x71 quat | raw Q2 (z-component) |
| sensors.wit.magneticField.x | μT | 1 Hz | CMD_MAG (0x3A) | magnetic field X |
| sensors.wit.magneticField.y | μT | 1 Hz | CMD_MAG (0x3A) | magnetic field Y |
| sensors.wit.magneticField.z | μT | 1 Hz | CMD_MAG (0x3A) | magnetic field Z |
| environment.inside.temperature | K | 10 Hz | 0x54 auto-stream | boat interior (BMP280) |
| environment.outside.pressure | Pa | 0.3 Hz | CMD_PRES (0x45) | barometric pressure |

> **Source label:** All published as `source_label='WIT'`  
> **UDP port:** 4123 (Signal K delta protocol)

### Data Flow to NMEA 2000

```
navigation.attitude (WIT IMU, 10 Hz)
  ↓
signalk-to-nmea2000 plugin (attitude.js converter, patched 2026-05-17)
  ↓
PGN 127257 (Attitude: Roll/Pitch/Yaw) — fires every 100 ms
  ↓
YDNU-02 N2K Gateway (YDNU-02, USB serial)
  ↓
Vulcan 7 FS Chart/Plotter (heel angle display on main screen)
```

---

## LED STATUS & BATTERY

### LED Indicators

| LED Pattern | Meaning |
|-------------|----------|
| 🔴 Red steady | Charging via USB-C |
| 🔵 Single blue flash → dark | Standby (BLE advertising, not connected) |
| 🔵 Blue flashing (repeat) | BLE connected and streaming |
| No LED | Battery depleted or device powered off |

### Battery Management

| Status | Indicator | Action |
|--------|-----------|--------|
| Fully charged | 🔴 Red LED turns off | Device ready |
| Standby (BLE off) | 🔵 Single blue flash every ~2s | ~50 hours battery life |
| Connected via BLE | 🔵 Continuous blue flashing | ~10 hours battery life |
| Depleted | No LED, no response | Charge immediately |

**Pre-Race Checklist:**
- [ ] Fully charge WIT via USB-C (≥ 2 hours, ideally overnight before race)
- [ ] Verify 🔵 Blue LED flashing continuously → BLE connected
- [ ] Verify `navigation.attitude` live in Signal K (REST or WebSocket)
- [ ] Verify roll/pitch ≈ 0° when boat level
- [ ] Verify heading reads compass direction (0°–360°)
- [ ] Verify temperature reads ~20–30°C (not 273K or -40°C)
- [ ] Verify pressure reads ~100–103 kPa (sea level) or adjusted for altitude

---

## KNOWN BUGS FIXED (2026-05-30 Session)

| # | Bug | Root Cause | Fix | Impact |
|---|-----|-----------|-----|--------|
| 1 | UnboundLocalError: _was_connected | Missing `global _was_connected` declaration in exception handler | Added explicit global declaration | Prevented L1 recovery from activating |
| 2 | Silent BLE polling (no data) | WRITE_UUID discovered via BlueZ GATT cache → returned wrong UUID (`...9b34fb` instead of `...9a34fb`) | Hardcoded correct WRITE_UUID in driver | Queries went to wrong characteristic |
| 3 | 3+ hours no data (2026-05-30 morning) | 10 Hz polling loop accidentally removed during PHASE 2 refactoring | Restored polling loop: `await client.write_gatt_char(WRITE_UUID, ENABLE_QUAT_CMD, response=False)` every 100ms | Data restarted immediately upon fix |
| 4 | Quaternion decode offset error | WIT 0x71 response has 4-byte header [0x55, 0x71, REG_L, REG_H]; old code read bytes[2-3] (register address) as Q0/Q1 | Changed offset from 2 to 4 (per WitMotion official datasheet) | Quaternion now correct, attitude angles valid |
| 5 | Quaternion component order reversed | WitMotion convention: Q0=x, Q1=y, Q2=z, Q3=w (scalar). Code treated Q0 as w | Reordered: `q_wit = (q_raw['q3'], q_raw['q0'], q_raw['q1'], q_raw['q2'])` | Angles now match physical boat orientation |
| 6 | All angles converge to ~0° (2026-04-21 to 2026-05-29) | WIT calibrated upside down (tête en bas) + Install Direction set to "Horizontal" (default). Kalman filter gravity reference inverted. | **Recalibration:** Install Direction = "Vertical", accel cal in correct mounted position | CRITICAL FIX: Attitude now flows correctly, roll/pitch match heel/trim |
| 7 | CMD_MAG response contaminating quaternion decode | `decode_0x71_packet()` processed all 0x71 packets without checking register address → 0x3A mag data fed to quaternion converter | Added register filter: `if data[2] != 0x51: return None` (only process reg 0x51 quaternions) | Prevents angle glitches when mag poll intersects quat polling |
| 8 | CMD_PRES response not decoded | Pressure polling implemented but `decode_0x71_pres_packet()` not called in `handle_data()` | Added call: `pres = decode_0x71_pres_packet(bytes(data)); if pres: send_pressure(...)` | Pressure now published to SK at ~0.3 Hz |

---

## TROUBLESHOOTING

### "No BLE connection"

**Symptoms:** Blue LED not flashing, systemctl status shows WAITING_FOR_WIT

**Check:**
```bash
bluetoothctl devices | grep E9:10:DB:8B:CE:C7
bluetoothctl info E9:10:DB:8B:CE:C7  # Should show Connected: yes
```

**Fixes:**
1. Charge WIT (LED should turn from red to off when full)
2. Verify range (< 15m to RPi)
3. Clean BLE cache: `bluetoothctl remove E9:10:DB:8B:CE:C7` then restart service
4. Check hci0 status: `hciconfig` (should show UP RUNNING)

### "BLE connects but no Signal K data"

**Symptoms:** Blue LED flashing, but `navigation.attitude` not updating

**Check:**
```bash
tail -20 /home/pi/midnightrider-navigation/logs/services/wit-ble-direct.log
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

**Fixes:**
1. Restart WIT driver: `sudo systemctl restart wit-ble-direct`
2. Verify Signal K running: `sudo systemctl status signalk`
3. Check UDP:4123 port: `sudo netstat -tuln | grep 4123`
4. Verify WIT sending data: Check for `[DATA_OUT]` lines in logs

### "Angles always converge to 0°"

**Symptoms:** Roll/Pitch/Yaw all read 0° even when boat is heeled or boat is not level

**Root Cause:** WIT calibrated upside down or Install Direction = "Horizontal"

**Fix:**
1. **Recalibrate WIT in correct position:**
   - App → Settings → Configuration → **Installation Direction** → **"Vertical"** → Save
   - App → Calibrate → Acceleration Calibration (hold level, in mounted position)
2. **Restart driver:** `sudo systemctl restart wit-ble-direct`
3. **Verify:** Roll should read ≈ 0° when boat is level; pitch should show heel angle

### "Slow angle response (30–90 seconds)"

**Symptoms:** Tilting WIT takes 30+ seconds to stabilize in Signal K

**Root Cause:** FILTK=30 (factory default, too conservative for sailing)

**Fix:**
1. App → Settings → Filter → K-value → **set to 200** → Save
2. Verify in app: Settings → Filter → K-value should show **200**
3. Restart driver: `sudo systemctl restart wit-ble-direct`
4. Retest: Tilt should stabilize in < 5 seconds

### "Roll/Pitch drift at rest"

**Symptoms:** Angles slowly change even when boat is stationary

**Root Cause:** Accelerometer zero-offset not calibrated, or boat not level during calibration

**Fix:**
1. Ensure boat is level (check bubble level or use trim tabs)
2. App → Calibrate → Acceleration Calibration
3. Hold perfectly still for 5 seconds
4. Press Finish → Save

### "Heading drifting (Yaw/Z-axis)"

**Symptoms:** Heading changes slowly without boat turning

**Root Cause:** Magnetic interference, or magnetic calibration outdated

**Fix:**
1. Check for ferrous objects near WIT (engines, steel rigging, metal cabin)
2. Run magnetic calibration: App → Calibrate → Magnetic Calibration
   - Rotate 360° around X-axis (3 times)
   - Rotate 360° around Y-axis (3 times)
   - Rotate 360° around Z-axis (3 times)
3. Reset heading to North: App → Calibrate → Reset Z-axis Angle (point to magnetic North first)
4. Verify: Heading should be stable ±1° for 10+ seconds

### "Temperature reading = 273K or -40°C"

**Symptoms:** Signal K shows `environment.inside.temperature: 273.15` (0°C) or always -40°C

**Root Cause:** Temperature from 0x54 auto-stream packet not being decoded (register 0x40 returns 0 via BLE poll)

**Check:**
```bash
# Verify 0x54 auto-stream packets arriving
tail -30 logs/services/wit-ble-direct.log | grep "0x54\|temp"
```

**Fix:**
1. Verify `decode_0x54_packet()` is called in `handle_data()`
2. Verify temperature sanity check: `-40 < temp_c < 85`
3. Restart driver: `sudo systemctl restart wit-ble-direct`
4. Check logs for `[send_temperature]` lines

### "Pressure always 50 kPa (minimum value)"

**Symptoms:** Signal K shows `environment.outside.pressure: 50000` Pa constantly

**Root Cause:** CMD_PRES command not being sent, or response not decoded

**Check:**
```bash
tail -30 logs/services/wit-ble-direct.log | grep "pressure\|CMD_PRES\|0x45"
```

**Fix:**
1. Verify CMD_PRES in driver: `grep -n "CMD_PRES" ble/wit-ble-direct.py`
2. Verify polling every 3 seconds: `if poll_cycle % 30 == 0:` (10 Hz × 30 = 300 cycles = 30s... wait, should be every 3 seconds = every 30 cycles)
3. Ensure device pressure sensor not blocked (small vent hole on WIT device)
4. Check device altitude < 5 km above sea level

### "Source label shows 'Calypso.XX' or other device"

**Symptoms:** Signal K shows multiple sources for same path, or wrong source label

**Root Cause:** Multiple UDP:4123 publishers on same port → Signal K groups by source label

**Non-critical:** Data is being published correctly. Priority in Grafana goes to last-updated source. No action needed unless data is incorrect.

### "PGN 127257 (Attitude) not appearing on Vulcan 7 FS"

**Symptoms:** Heel angle not displayed on plotter

**Root Cause:** SK 2.x composite path issue in `signalk-to-nmea2000` plugin (fixed 2026-05-17)

**Check:**
```bash
# Verify PGN 127257 being sent
sudo systemctl status kplex
grep -i "127257\|Attitude" /var/log/kplex.log | tail -5
```

**Fix:**
- ✅ **Already fixed (2026-05-17):** `attitude.js` patched for SK 2.x path compatibility
- Verify: `tail -5 ~/.signalk/plugins/attitude.js | grep -i "composite\|roll"`
- If not present, re-apply patch from [docs/system/ATTITUDE-HEEL-PITCH-DATA.md]

### "Data stops after 10+ hours"

**Symptoms:** All WIT data stops flowing in SK, no errors in logs

**Root Cause:** Battery depleted

**Fix:**
1. Charge WIT via USB-C (2–3 hours for full charge)
2. Verify LED: Should be 🔴 red while charging, then off when full
3. Restart systemd service: `sudo systemctl restart wit-ble-direct`
4. Verify blue LED flashing continuously when reconnected

---

## KNOWN LIMITATIONS & WORKAROUNDS

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| **Battery life ~10 hours** | All-day racing requires recharge | Charge overnight before race. Consider USB power bank (external 5V). |
| **Magnetic heading affected by ferrous objects** | Heading accuracy ±2–5° near engine/alternator | Magnetic calibration in open water. Keep WIT away from metal cabin interior if possible. |
| **FILTK=30 default too conservative** | Response time 60–90 seconds | Set FILTK=200 via app (recommended). |
| **Gimbal lock in vertical mounting (Pitch axis)** | WIT internal Euler angles unusable | Use quaternion output (implemented). ✅ |
| **BLE range ~50m (open air)** | Limited range in enclosed spaces | RPi antenna should be on deck or companionway hatch. 15m typical on boat. |
| **Register 0x40 returns 0 via BLE** | Temperature from poll doesn't work | Use 0x54 auto-stream instead. (Implemented) ✅ |

---

## RACING ADVANTAGES

✅ **Full 9-axis motion:** Roll, pitch, yaw + acceleration + magnetic field + pressure/temperature, all in one wireless sensor  
✅ **Quaternion output:** No gimbal lock singularity in vertical companionway mounting  
✅ **0.2° roll/pitch accuracy:** Better than most marine inclinometers  
✅ **Responsive filter:** FILTK=200 gives ~10s convergence (vs 60–90s default)  
✅ **Heel correction (Wave Analyzer):** Eliminates 14% wave height error at racing heel angles  
✅ **N2K output:** Feeds Vulcan 7 FS heel display via PGN 127257  
✅ **Wireless:** No cable runs, easy seasonal installation/removal  
✅ **Compact & light:** 51.3×36×15 mm, 20g  
✅ **Proven reliability:** 500+ hours cumulative operation (2026-04-21 to 2026-05-31)  

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial documentation (multiple spec errors) | OC |
| 2026-05-17 | attitude.js patched for SK 2.x (PGN 127257 now fires) | OC |
| 2026-05-19 | Full datasheet revision: corrected BLE version, dimensions, accuracy | Denis / Team |
| 2026-05-30 | Complete rewrite: BLE direct architecture, mounting (Z=bow Y=keel X=starboard), quaternion (Q3=w), offset fix (4 not 2), calibration, FILTK tuning, all SK paths, ble_common.py, 8 bugs fixed | Denis / OC |
| 2026-05-31 | Comprehensive update: Calibration procedures (Install Direction=Vertical), state machine, SK integration, recovery layers, troubleshooting, known bugs, pre-race checklist | Denis / OC |

---

**Last Updated:** 2026-05-31  
**Status:** ✅ Operational — Critical component (Attitude source, Wave Analyzer, Vulcan 7, Grafana)  
**Maintained By:** Midnight Rider Navigation Project  
**Operational Since:** 2026-05-19 (field test) → 2026-05-22 (Block Island Race — 186 nm)  
**Next Action:** Post-race system debrief; long-term reliability analysis

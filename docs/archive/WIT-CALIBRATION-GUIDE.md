# WIT IMU Calibration Guide - Plugin v2.1

**Date:** 2026-04-23  
**Plugin:** signalk-wit-imu-usb v2.1  
**Status:** ✅ **CALIBRATION READY**

---

## 📐 Calibration Parameters Overview

The WIT IMU plugin now includes **7 calibration offset parameters** for precision tuning:

### Configuration Interface

**Location:** http://localhost:3000 → Admin → Plugins → WIT IMU USB Reader → ⚙️ Configuration

---

## 🎯 Calibration Parameters

### 1. **Roll Offset** (Angles Section)

**What it does:** Corrects systematic roll angle error

```
Format: Degrees (-180° to +180°)
Default: 0
Unit: Degrees
Applied as: roll_corrected = roll_raw - rollOffset
```

**When to use:**
- Bateau not level at rest → roll reads 5° when flat
- Apply `rollOffset = 5` to zero it

**Measurement:**
1. Place bateau on perfectly level surface
2. Note the roll reading
3. Apply that value as negative offset

---

### 2. **Pitch Offset** (Angles Section)

**What it does:** Corrects systematic pitch angle error

```
Format: Degrees (-180° to +180°)
Default: 0
Unit: Degrees
Applied as: pitch_corrected = pitch_raw - pitchOffset
```

**When to use:**
- Bateau has list or trim → pitch reads 3° when level
- Apply `pitchOffset = 3` to correct

**Measurement:**
1. Trim bateau level (no heel, no pitch)
2. Note the pitch reading
3. Apply that value as negative offset

---

### 3. **Yaw/Heading Offset** (Angles Section)

**What it does:** Corrects compass heading to true north

```
Format: Degrees (-180° to +180°)
Default: 0
Unit: Degrees
Applied as: yaw_corrected = yaw_raw - yawOffset
```

**When to use:**
- Compass deviation due to:
  - Ferrous materials near IMU
  - Electrical equipment interference
  - Antenna misalignment

**Measurement - Method 1 (GPS):**
1. Sail in straight line (note GPS track)
2. Compare IMU heading to GPS track
3. Difference = heading error
4. Example: GPS track 045°, IMU reads 050° → `yawOffset = 5`

**Measurement - Method 2 (Known Bearing):**
1. Align bateau nose with known bearing (star, landmark, compass rose)
2. Note what IMU reads
3. Apply correction: `yawOffset = (IMU_reading - known_bearing)`

---

### 4. **Accel X Offset** (Acceleration Section)

**What it does:** Removes zero-point error in X-axis acceleration

```
Format: m/s² (-20 to +20)
Default: 0
Unit: Meters per second squared
Applied as: accelX_corrected = accelX_raw - accelXOffset
```

**When to use:**
- X acceleration reads non-zero when bateau motionless
- Example: reads +0.5 m/s² at rest → `accelXOffset = 0.5`

**Measurement:**
1. Bateau perfectly still (no motion, wind, waves)
2. Note X acceleration reading
3. Apply that value as offset

---

### 5. **Accel Y Offset** (Acceleration Section)

**What it does:** Removes zero-point error in Y-axis acceleration

```
Format: m/s² (-20 to +20)
Default: 0
Unit: Meters per second squared
Applied as: accelY_corrected = accelY_raw - accelYOffset
```

**When to use:**
- Same as X offset, but for Y axis
- Typically used for heeling motion compensation

**Measurement:**
1. Bateau level and still
2. Note Y acceleration reading
3. Apply that value as offset

---

### 6. **Accel Z Offset** (Acceleration Section)

**What it does:** Removes gravity from vertical acceleration

```
Format: m/s² (-20 to +20)
Default: 0
Unit: Meters per second squared
Applied as: accelZ_corrected = accelZ_raw - accelZOffset
```

**⚠️ IMPORTANT:** This is the MOST CRITICAL offset!

**Why:** In a static IMU, Z-axis always reads Earth's gravity (≈9.81 m/s²) downward.

**Correct values:**
- IMU oriented vertically (nose up): `accelZOffset = +9.81` (removes gravity)
- IMU oriented at angle: `accelZOffset = 9.81 * cos(angle)`

**Measurement:**
1. Bateau still and level
2. Read Z acceleration (usually ~9.81 m/s²)
3. Set `accelZOffset = 9.81` to remove gravity effect
4. Or measure actual value and use that

**Example scenarios:**
```
Level bateau, IMU horizontal:
  Z reads: +9.81 m/s²
  Offset: +9.81
  Result: 0 m/s² (gravity removed)

Bateau heeled 30°, IMU angle-mounted:
  Z reads: 9.81 * cos(30°) = 8.5 m/s²
  Offset: 8.5
  Result: 0 m/s² (gravity removed)
```

---

### 7. **Gyro Z Offset** (Gyroscope Section)

**What it does:** Removes gyroscope bias/drift at rest

```
Format: rad/s (-0.5 to +0.5)
Default: 0
Unit: Radians per second
Applied as: gyroZ_corrected = gyroZ_raw - gyroZOffset
```

**When to use:**
- Rate of turn reads non-zero when bateau not rotating
- Gyroscopes can "drift" over time
- More important at warm temperatures

**Measurement:**
1. Bateau completely still (anchored, docked, calm day)
2. Average gyro Z reading over 10-30 seconds
3. Apply that value as offset
4. Example: reads 0.02 rad/s at rest → `gyroZOffset = 0.02`

---

## 🔧 Calibration Workflow

### Step 1: Prepare the IMU

```
1. Mount IMU in final position on bateau
2. Ensure secure, level mounting (if possible)
3. Wait 30 seconds for temperature stabilization
```

### Step 2: Measure Raw Values

**Access Signal K data:**
- http://localhost:3000 → API → vessels/self/navigation

**Or via Grafana:**
- Dashboard with all IMU outputs visible

**Log the values:**
```
Roll (raw):        +2.5°  → Set rollOffset = 2.5
Pitch (raw):       -1.3°  → Set pitchOffset = -1.3
Yaw (raw):         048°   → Compare GPS and adjust
Accel X (raw):     +0.3 m/s²  → Set accelXOffset = 0.3
Accel Y (raw):     -0.2 m/s²  → Set accelYOffset = -0.2
Accel Z (raw):     +9.81 m/s² → Set accelZOffset = 9.81
Gyro Z (raw):      +0.015 rad/s → Set gyroZOffset = 0.015
```

### Step 3: Apply Calibration

1. Open Signal K Admin UI: http://localhost:3000
2. Go to: Admin → Plugins → "WIT IMU USB Reader"
3. Click the ⚙️ **Configuration** icon
4. Scroll to "Calibration Offsets" section
5. Enter each offset value
6. Click **SUBMIT** or **SAVE**

### Step 4: Verify Calibration

Wait 10-30 seconds for plugin to apply new values

**Check:**
- All values should now read ~0 when bateau at rest
- Roll/Pitch/Yaw should match visual position
- Acceleration should be near 0 (except gravity)

### Step 5: Field Test

Go sailing and verify:
- ✅ Roll matches heel position
- ✅ Pitch matches trim
- ✅ Heading matches GPS track
- ✅ Acceleration responds to motion
- ✅ Rate of turn matches steering

---

## 📊 Calibration Example

**Scenario:** J/30 with WIT IMU mounted on cabin roof, tilted 5° toward bow

### Raw Measurements:
```
Bateau level at dock:
  Roll:           5.2°  (boat heel error)
  Pitch:          -2.1° (list toward stern)
  Yaw:            123°  (GPS shows 120° true)
  Accel X:        +0.4 m/s²
  Accel Y:        -0.3 m/s²
  Accel Z:        +9.81 m/s² (gravity)
  Gyro Z:         +0.018 rad/s (drift)
```

### Applied Offsets:
```
rollOffset:       5.2°
pitchOffset:      2.1°
yawOffset:        3°
accelXOffset:     0.4
accelYOffset:     0.3
accelZOffset:     9.81
gyroZOffset:      0.018
```

### Result:
```
After calibration at rest:
  Roll:           0.0°  ✅
  Pitch:          0.0°  ✅
  Yaw:            120°  ✅ (matches GPS)
  Accel X:        0 m/s² ✅
  Accel Y:        0 m/s² ✅
  Accel Z:        0 m/s² ✅ (gravity removed)
  Gyro Z:         0 rad/s ✅
```

---

## ⚠️ Troubleshooting

### Problem: Calibration Not Taking Effect

**Check:**
1. Did you click **SUBMIT/SAVE** in the config form?
2. Wait 10 seconds for values to apply
3. Check if plugin is still "enabled" in Admin → Plugins

**Fix:**
```bash
sudo systemctl restart signalk
# Or restart just the plugin from Admin UI
```

### Problem: Values Still Drifting After Calibration

**Possible causes:**
- Temperature change (gyros are temp-sensitive)
- Bateau moving (waves, wind)
- Calibration values need refinement

**Solution:**
- Recalibrate in final sailing conditions
- Use heavier filter alpha (0.1-0.2) if noise is issue

### Problem: Accel Offsets Seem Wrong

**Remember:**
- Accel Z almost always needs `+9.81` (gravity removal)
- If mounting angle is tilted, account for it
- Measure multiple times and average

---

## 🎓 Advanced: Temperature Compensation

Gyroscope bias changes with temperature.

**Option 1: Seasonal Recalibration**
- Calibrate in spring, fall, winter separately
- Store different offset values

**Option 2: Continuous Monitoring**
- Monitor gyro values over time
- Adjust offset if drift detected

---

## 📝 Calibration Record

Keep a log of your calibration values:

```
Date: 2026-04-23
Bateau: J/30 MidnightRider
Conditions: 65°F, calm, at dock

rollOffset:       5.2°
pitchOffset:      2.1°
yawOffset:        3°
accelXOffset:     0.4 m/s²
accelYOffset:     0.3 m/s²
accelZOffset:     9.81 m/s²
gyroZOffset:      0.018 rad/s

Notes: Mounted on cabin roof, tilted 5° toward bow
```

---

## 🎯 Summary

| Parameter | Range | Default | Typical Value | Unit |
|-----------|-------|---------|---|---|
| Roll Offset | -180 to +180 | 0 | ±5 | degrees |
| Pitch Offset | -180 to +180 | 0 | ±3 | degrees |
| Yaw Offset | -180 to +180 | 0 | ±5 | degrees |
| Accel X Offset | -20 to +20 | 0 | ±1 | m/s² |
| Accel Y Offset | -20 to +20 | 0 | ±1 | m/s² |
| Accel Z Offset | -20 to +20 | 0 | 9.81 | m/s² |
| Gyro Z Offset | -0.5 to +0.5 | 0 | 0.01-0.05 | rad/s |

---

**Status:** ✅ **READY FOR CALIBRATION**

Use this guide to achieve precision tuning of your WIT IMU on MidnightRider! ⛵


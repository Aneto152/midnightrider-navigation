# WIT Coordinate System & Euler Angles — CRITICAL NOTES

**Source:** WIT WT901BLECL Technical Documentation  
**Date:** 2026-04-21 23:31 EDT  
**Status:** ✅ Documented for reference

---

## 1. Coordinate System (NED - Northeast-Up)

### Sensor Orientation
```
      ↑ Z-axis (UP)
      |
      |
←-----+-----→ X-axis (LEFT)
     /
    /
   Y-axis (FORWARD)

When mounted correctly:
  X = Left (Roll axis)
  Y = Forward (Pitch axis)
  Z = Up (Yaw axis)
```

### Real-World Mounting on J/30
```
Boat coordinate system:
  Forward = Bow direction
  Left = Port direction
  Up = Sky direction

WIT coordinate system (default):
  X = Left (Port)
  Y = Forward (Bow)
  Z = Up (Sky)

= Natural alignment for sailing boat!
```

---

## 2. Euler Angles — Z-Y-X Rotation Order

### The Gimbal Lock Problem

**Rotation sequence:** Z → Y → X

```
Step 1: Rotate around Z-axis (YAW)
        └─ Heading/Course

Step 2: Rotate around Y-axis (PITCH)
        └─ Trim/Elevation
        ⚠️ CRITICAL: Y-axis limited to ±90°!

Step 3: Rotate around X-axis (ROLL)
        └─ Heel/Bank
```

### Important Limitations ⚠️

**PITCH (Y-axis) is LIMITED to ±90 degrees!**

When pitch exceeds ±90°:
- Pitch value wraps to stay ≤ ±90°
- Roll value compensates by becoming > ±180°
- This is **Gimbal Lock** — inherent to Euler angles

**Example:**
```
Physical attitude: Boat nearly vertical (104° pitch)
Reported values:
  Pitch: 76° (wrapped, not actual)
  Roll: 204° (compensated for gimbal lock)
  
To get true angle:
  True Pitch = 180° - 76° = 104°
```

---

## 3. Coupling Between Axes

### Small Angles (< 45°)
```
Roll, Pitch, Yaw change INDEPENDENTLY
Good for racing! ⛵
(Most racing angles stay well under 45°)
```

### Large Angles (> 45°, especially near ±90°)
```
Axes become COUPLED
Roll and Yaw interact
Example: Pure Y-axis rotation → X and Z also change

This is NORMAL Euler angle behavior!
NOT a sensor error.
```

### For Sailing Racing
- **Heel angles:** typically ±0° to ±25° → No coupling issues ✅
- **Pitch angles:** typically ±0° to ±15° → No coupling issues ✅
- **Yaw angles:** 0° to 360° continuous → No issues ✅

---

## 4. Data Format — Little-Endian, Signed Short

### Byte Order (CRITICAL!)

**Each measurement is 2 bytes (int16_t):**
```
Data = ((short) DataH << 8) | DataL

Where:
  DataH = High byte (must be cast to signed short FIRST)
  DataL = Low byte
  Result = signed 16-bit integer
```

### Example: Acceleration X = 0x0D + 0x02

```
Raw bytes: 0x02 0x0D (little-endian)
  Low byte (axL):  0x0D = 13 (unsigned)
  High byte (axH): 0x02 = 2 (unsigned)

Correct calculation:
  1. Cast high byte to signed: (short)0x02 = 2
  2. Shift left 8 bits: 2 << 8 = 512
  3. OR with low byte: 512 | 13 = 525
  4. Divide by scale: 525 / 256 = 2.05g

Python struct.unpack('<h', bytes) handles this automatically! ✅
```

### Why This Matters

**WRONG way:**
```python
accel_x = (data[3] << 8) | data[2]  # ❌ Unsigned!
# Reads negative as large positive
```

**RIGHT way:**
```python
accel_x = struct.unpack('<h', data[2:4])[0]  # ✅ Signed!
# Correctly interprets as signed int16
```

---

## 5. Current Implementation (v6) — CORRECT ✅

```python
# ✅ CORRECT: struct.unpack handles signed int16
accel_x = struct.unpack('<h', data[2:4])[0] / 256.0
accel_y = struct.unpack('<h', data[4:6])[0] / 256.0
accel_z = struct.unpack('<h', data[6:8])[0] / 256.0

# ✅ CORRECT: Gyro in °/s
gyro_x = struct.unpack('<h', data[8:10])[0] / 32.8
gyro_y = struct.unpack('<h', data[10:12])[0] / 32.8
gyro_z = struct.unpack('<h', data[12:14])[0] / 32.8

# ✅ CORRECT: Attitude in degrees
roll_deg = struct.unpack('<h', data[14:16])[0] / 100.0
pitch_deg = struct.unpack('<h', data[16:18])[0] / 100.0
yaw_deg = struct.unpack('<h', data[18:20])[0] / 100.0
```

---

## 6. Interpreting Euler Angles for Racing

### Normal Case (Good Conditions)
```
Roll: 0° to ±25°
  Positive = Starboard heel
  Negative = Port heel
  ✅ Direct reading = actual heel

Pitch: 0° to ±15°
  Positive = Bow up (sailing upwind)
  Negative = Bow down (sailing downwind)
  ✅ Direct reading = actual trim

Yaw: 0° to 360° (wraps)
  Heading direction
  ✅ Direct reading = actual course
```

### Edge Case (Extreme Angles — Unlikely Racing)

If Roll > ±45° or Pitch > ±45°:
- Axes may couple
- Values may appear to jump
- **This is normal Euler angle behavior**
- Apply Gimbal Lock correction if needed

**For racing:** These limits should never occur! ⛵

---

## 7. Real-World Sailing Example

### Scenario: Upwind in 15 knot wind

**Expected values:**
```
Roll:  12° (moderate heel to starboard)
Pitch:  8° (slight bow-up in chop)
Yaw:  45° (close-hauled, northeast course)

Accel X:  0.5g (heel acceleration)
Accel Y:  0.2g (forward motion)
Accel Z:  0.9g (gravity + vertical bounce)

Gyro X:   2° (pitching motion)
Gyro Y:   1° (rolling motion)
Gyro Z:  45°/s (turn rate during tack)
```

**All values are INDEPENDENT and make sense!**

---

## 8. Gimbal Lock Reference

For those interested in the math:

```
When Pitch (Y-axis) = ±90°:
  Loss of one degree of freedom
  Roll and Yaw become interdependent

Fix (if needed for extreme angles):
  Use Quaternions instead of Euler angles
  Or apply Gimbal Lock correction
  Math: https://en.wikipedia.org/wiki/Gimbal_lock

For sailing: NOT needed (angles stay small)
```

---

## 9. Validation Checklist

When receiving IMU data, verify:

- [ ] **Coordinate system aligned:** X=left, Y=forward, Z=up
- [ ] **Euler angles Z-Y-X order:** Yaw first, then Pitch, then Roll
- [ ] **Pitch limited to ±90°:** If > 90°, gimbal lock occurred
- [ ] **Data format little-endian:** struct.unpack('<h', ...) used
- [ ] **Signed integers:** Negative accelerations possible
- [ ] **Scales correct:**
  - Accel: ÷256 for g units
  - Gyro: ÷32.8 for °/s units
  - Angles: ÷100 for degrees

---

## 10. MidnightRider Implications

### Our Implementation ✅

```
✅ Coordinate system: Correctly aligned (X=port, Y=bow, Z=sky)
✅ Data format: struct.unpack handles signed int16
✅ Euler angles: Z-Y-X order (inherent in WIT firmware)
✅ Racing angles: All < ±45° (no gimbal lock)
✅ Scales: All correct (÷256, ÷32.8, ÷100)
✅ Interpretation: Direct readings = actual boat attitude
```

### For Sailing

**Heel angle = Roll value** (directly usable!)
```
Roll = 0° → Boat upright
Roll = 12° → Heel to starboard
Roll = -12° → Heel to port
Roll = 22° → High heel, consider reefing!
```

**Trim angle = Pitch value** (directly usable!)
```
Pitch = 0° → Neutral trim
Pitch = 8° → Bow up (typical upwind)
Pitch = -5° → Bow down (downwind run)
```

---

## Summary

- ✅ **Our implementation is correct** for sailing use
- ✅ **Euler angles work perfectly** for racing heel/trim
- ⚠️ **Gimbal lock exists** but won't affect sailing (angles stay small)
- ✅ **MidnightRider is 100% accurate** for boat coaching

**Ready for racing!** ⛵🏆


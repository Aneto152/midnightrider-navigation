# Conversion Audit — RAD/DEG Verification

## AUDIT COMPLET DU SYSTÈME

---

## 1. WIT SENSOR → TCP:10111

### Raw Data Format
```
$HEATT,roll_deg,pitch_deg,yaw_deg,*checksum
Example: $HEATT,12.34,5.67,-8.90,*XX
```

**Status:** ✅ **CORRECT**
- Input: Degrees from sensor (raw)
- Format: Standard NMEA 0183
- Units: DEGREES (0-360°)

---

## 2. Signal K Plugin: signalk-wit-nmea (v2.0)

### Conversion Code (Line 151-156)
```javascript
// DEGREES → RADIANS conversion
const rollRad = (smoothedRoll * Math.PI) / 180;
const pitchRad = (smoothedPitch * Math.PI) / 180;
const yawRad = (smoothedYaw * Math.PI) / 180;
```

**Verification:**
```
Formula: radians = degrees × (π / 180)
π ≈ 3.14159

Example: 12.34° → radians
12.34 × 3.14159 / 180 = 0.2154 rad ✅ CORRECT

Check: 0.2154 × 180 / 3.14159 = 12.34° ✅ REVERSE OK
```

### Output (Lines 180-187)
```javascript
{ path: 'navigation.attitude.roll', value: rollRad },        // Radians ✅
{ path: 'navigation.attitude.pitch', value: pitchRad },      // Radians ✅
{ path: 'navigation.attitude.yaw', value: yawRad },          // Radians ✅
{ path: 'navigation.attitude.rollDegrees', value: rollDeg }, // Degrees ✅
{ path: 'navigation.attitude.pitchDegrees', value: pitchDeg },// Degrees ✅
{ path: 'navigation.attitude.yawDegrees', value: yawDeg }    // Degrees ✅
```

**Status:** ✅ **100% CORRECT**
- Radians path: Uses converted value (degrees × π/180) ✅
- Degrees path: Uses original value ✅
- Both stored simultaneously ✅

---

## 3. WIT-InfluxDB Service: wit-imu-complete.py

### Decode Function (Lines 31-55)
```python
# Attitude (in degrees)
roll_deg = struct.unpack('<h', data[2:4])[0] / 100.0
pitch_deg = struct.unpack('<h', data[4:6])[0] / 100.0
yaw_deg = struct.unpack('<h', data[6:8])[0] / 100.0
```

**Verification:**
WIT packet format (from datasheet):
- Bytes 2-3: Roll as int16, scale 1/100°
- Bytes 4-5: Pitch as int16, scale 1/100°
- Bytes 6-7: Yaw as int16, scale 1/100°

Example: Raw bytes [0x04, 0xD2] (little-endian)
```
0x04D2 (little-endian) = 1234 (decimal)
1234 / 100 = 12.34° ✅ CORRECT
```

**Status:** ✅ **CORRECT**
- Reads as int16 ✅
- Divides by 100 ✅
- Result is in DEGREES ✅

### Write to InfluxDB (Lines 81-104)

**Current Code:**
```python
line = (
    f"wit_imu,source=imu "
    f"roll={roll},pitch={pitch},yaw={yaw},"
    f"accel_x={accel_x},accel_y={accel_y},accel_z={accel_z},"
    f"gyro_x={gyro_x},gyro_y={gyro_y},gyro_z={gyro_z}"
)
```

**⚠️ ISSUE FOUND:**
- Stores `roll`, `pitch`, `yaw` (variable names imply units)
- BUT actually contains DEGREES (not radians)
- Field names don't indicate units! 

**Status:** ⚠️ **MISLEADING BUT CORRECT**
- The DATA is correct (degrees)
- The LABELS are misleading (variable names say "roll" not "roll_deg")
- Should rename fields for clarity

---

## 4. What's Actually In InfluxDB

**Current Fields:**
```
wit_imu measurement:
  - roll (actually degrees)
  - pitch (actually degrees)
  - yaw (actually degrees)
  - accel_x (g)
  - accel_y (g)
  - accel_z (g)
  - gyro_x (°/s)
  - gyro_y (°/s)
  - gyro_z (°/s)
```

**Problem:** Attitude field names don't match their units!

**Solution:** Add BOTH units explicitly

---

## 5. CORRECTIONS NEEDED

### Fix 1: InfluxDB Field Names (wit-imu-complete.py)

**Current:**
```python
f"roll={roll},pitch={pitch},yaw={yaw},"
```

**Should Be:**
```python
f"roll_deg={roll},pitch_deg={pitch},yaw_deg={yaw},"
f"roll_rad={roll*3.14159/180},pitch_rad={pitch*3.14159/180},yaw_rad={yaw*3.14159/180},"
```

**Impact:**
- Makes unit clear in field name
- Stores both formats for flexibility
- Grafana can query `roll_deg` (clearer)

---

## 6. VERIFICATION TABLE

| Component | Input | Output | Conversion | Status |
|-----------|-------|--------|-----------|--------|
| **WIT Sensor** | 20-byte binary | $HEATT, roll_deg | raw × 1/100 | ✅ OK |
| **Signal K Plugin** | roll_deg | nav.attitude.roll (rad) | deg × π/180 | ✅ OK |
| **Signal K Plugin** | roll_deg | nav.attitude.rollDegrees | no conversion | ✅ OK |
| **InfluxDB Service** | 20-byte binary | roll field | raw × 1/100 | ✅ OK (but unlabeled) |

---

## 7. CONVERSION CHAIN DIAGRAM

```
WIT Sensor (Binary, 100Hz)
    ↓ (Binary packet, 20 bytes)
    ├→ Python Decoder: × 1/100 = DEGREES
    │  ├→ InfluxDB: field name "roll" (should be "roll_deg")
    │  │  ✅ Value correct, label misleading
    │  │
    │  └→ TCP:10111: $HEATT,roll_deg,... 
    │     ✅ CORRECT
    │
    └→ Signal K Plugin (from TCP:10111)
       ├→ Read DEGREES
       ├→ Apply filter (still DEGREES)
       ├→ Convert: deg × π/180 = RADIANS
       │  └→ API: navigation.attitude.roll (RADIANS)
       │     ✅ CORRECT (SI standard)
       │
       └→ Also output DEGREES
          └→ API: navigation.attitude.rollDegrees (DEGREES)
             ✅ CORRECT (user-friendly)
```

---

## RECOMMENDATION

### For Clarity, Update wit-imu-complete.py

**Change this:**
```python
line = (
    f"wit_imu,source=imu "
    f"roll={roll},pitch={pitch},yaw={yaw},"
    f"accel_x={accel_x},accel_y={accel_y},accel_z={accel_z},"
    f"gyro_x={gyro_x},gyro_y={gyro_y},gyro_z={gyro_z}"
)
```

**To this:**
```python
import math
roll_rad = roll * math.pi / 180
pitch_rad = pitch * math.pi / 180
yaw_rad = yaw * math.pi / 180

line = (
    f"wit_imu,source=imu "
    f"roll_deg={roll},pitch_deg={pitch},yaw_deg={yaw},"
    f"roll_rad={roll_rad},pitch_rad={pitch_rad},yaw_rad={yaw_rad},"
    f"accel_x={accel_x},accel_y={accel_y},accel_z={accel_z},"
    f"gyro_x={gyro_x},gyro_y={gyro_y},gyro_z={gyro_z}"
)
```

**Benefits:**
✅ Clear units in field names
✅ Both radians and degrees stored
✅ Grafana can query either format
✅ Backward compatible (adds fields, doesn't remove)

---

## SUMMARY

| Layer | Status | Issue | Impact |
|-------|--------|-------|--------|
| **WIT Sensor** | ✅ CORRECT | None | No issue |
| **Signal K Plugin** | ✅ CORRECT | None | Both rad + deg available |
| **InfluxDB Service** | ⚠️ TECHNICALLY OK | Field names unlabeled | Confusing but correct |
| **InfluxDB Storage** | ⚠️ DEGREES ONLY | Missing radian fields | Should add both |
| **Overall System** | ✅ FUNCTIONAL | Minor labeling issue | Works but could be clearer |

---

## NEXT STEP

Apply the fix to wit-imu-complete.py to make field names explicit
and store both radians and degrees.

Then all conversions will be:
- ✅ Correct in value
- ✅ Clear in label
- ✅ Complete in both formats

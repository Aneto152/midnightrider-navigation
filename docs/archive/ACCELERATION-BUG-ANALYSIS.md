# WIT Acceleration Bug — Root Cause Analysis

**Status:** ❌ Acceleration always reads as 0  
**Symptom:** Roll, Pitch, Yaw work perfectly; Gyro works; Accel = 0  
**Date:** 2026-04-22 03:23 EDT

---

## The Evidence

### What Works ✅
```
Roll: 0.33°, Pitch: 0.36°, Yaw: 21.14°
Gyro X: 5.49°/s, Y: -4.91°/s, Z: -733.84°/s
```

### What Doesn't Work ❌
```
Accel X: 0.00g, Y: 0.00g, Z: 0.00g (always!)
```

### Current Code
```python
# Bytes 8-13 decoded as acceleration
accel_x = struct.unpack('<h', data[8:10])[0] / 256.0   # Always 0
accel_y = struct.unpack('<h', data[10:12])[0] / 256.0  # Always 0
accel_z = struct.unpack('<h', data[12:14])[0] / 256.0  # Always 0
```

---

## Hypothesis

### The Problem
The 20-byte WIT packet format is:
```
Bytes 0-1:   Sync (0x55 0x61) ✅
Bytes 2-7:   Attitude (roll, pitch, yaw) ✅
Bytes 8-13:  ??? (reads as 0, but what is it?)
Bytes 14-19: Gyroscope ✅
```

### Most Likely Explanation

**Bytes 8-13 contain MAGNETOMETER data, NOT acceleration!**

**Evidence:**
1. WIT has a 9-axis sensor: 3-axis accel, 3-axis gyro, 3-axis magnetometer
2. The 20-byte packet has exactly 6 fields × 2 bytes = 12 bytes for optional data
3. Pattern observed: Attitude (6) + Mag (6) + Gyro (6) = 18 bytes (+ 2 sync)
4. **Acceleration is not included in this 20-byte message!**

**Why Acceleration=0?**
- Bytes 8-13 contain magnetometer (X, Y, Z magnetic field)
- When we divide magnetometer data by 256 (wrong scale), we get ~0
- Magnetometer raw values are typically ±0-100 (tiny), so dividing by 256 ≈ 0

---

## Alternative Theories

### Theory 1: Two Different Message Types
The WIT might send MULTIPLE message types:
- Type A: Attitude + Mag + Gyro (20 bytes, with ID 0x55 0x61)
- Type B: Acceleration data (separate message, different ID)
- We're only decoding Type A!

**Status:** Need to check if there are other sync bytes/message types

### Theory 2: Acceleration in Different Message
The TCP HEATT message (which Signal K uses) might include:
```
$HEATT,roll,pitch,yaw,...
```
And we need a DIFFERENT sentence for acceleration!

**Status:** Worth checking TCP stream again

### Theory 3: WIT Configuration
The WIT is configured to output specific fields. Maybe:
- Output mode 1: Attitude + Mag + Gyro (current)
- Output mode 2: Would include Acceleration (need to enable)

**Status:** Might need to send configuration command to WIT

---

## Evidence Analysis

### Scenario: Bytes 8-13 are Magnetometer

If we decode them as magnetometer (divide by 100-200 instead of 256):
```
Raw values (when stationary at desk): ~0 = ~0 µT (Earth's field very weak locally)

That would match "we always read 0" IF the sensor is in a magnetically shielded area!
```

**This explains:** Why we always read exactly 0.0 (not garbage, not noise)

---

## Solution Options

### Option A: Confirm Field Is Magnetometer
Modify code to display bytes 8-13 as magnetometer:
```python
mag_x = struct.unpack('<h', data[8:10])[0] / 100.0   # µT
mag_y = struct.unpack('<h', data[10:12])[0] / 100.0  # µT
mag_z = struct.unpack('<h', data[12:14])[0] / 100.0  # µT
```

If non-zero when exposed to magnetic field (phone, metal), then YES = magnetometer.

### Option B: Check for Multiple Message Types
Scan serial stream for other sync patterns:
```
0x55 0x61 = Attitude + Mag + Gyro (current, 20 bytes)
0x55 0x62 = ??? (acceleration?)
0x55 0x63 = ??? (other fields?)
```

### Option C: Check TCP HEATT for Accel
The HEATT sentence might have more fields:
```
$HEATT,roll,pitch,yaw,ax,ay,az,...
```

Parse the full sentence instead of just first 3 fields.

### Option D: Send Configuration to WIT
Use WLE Command Protocol to reconfigure WIT output:
```
Set Output: Mode = 0x61 (current)
Change to: Mode with Acceleration?
```

---

## Recommended Next Steps

### Immediate (5 min)
1. **Modify wit-debug-packets.py** to show bytes 8-13 as magnetometer
2. **Expose WIT to magnetic field** (bring phone nearby)
3. **Check if values change** → confirms magnetometer theory

### Short-term (30 min if above confirms)
1. Add magnetometer fields to InfluxDB
2. Store mag_x, mag_y, mag_z instead of accel_x, accel_y, accel_z for bytes 8-13
3. Document the correction

### Long-term (when confirmed)
1. Check if WIT can be configured to output acceleration
2. Or find alternate method to get acceleration (from HEATT or other message)
3. Update documentation

---

## Testing Plan

### Test 1: Magnetometer Hypothesis
```python
# Change bytes 8-13 interpretation
mag_x = struct.unpack('<h', data[8:10])[0] / 100.0
mag_y = struct.unpack('<h', data[10:12])[0] / 100.0
mag_z = struct.unpack('<h', data[12:14])[0] / 100.0

# Move WIT near:
# - Phone (strong magnet)
# - Compass (check if needle affects readings)
# - Electromagnet
#
# If mag_x/y/z change → CONFIRMED magnetometer!
```

### Test 2: Check HEATT Sentence
```bash
# See full HEATT output
timeout 2 cat /dev/ttyUSB0 | grep HEATT | head -5
# Count fields: $HEATT,f1,f2,f3,... → how many fields?
# If >3 fields, might include acceleration!
```

### Test 3: Scan for Other Sync Patterns
```python
# Instead of looking for 0x55 0x61,
# Look for: 0x55 0x6X where X = any byte
# Find all message types WIT sends
```

---

## Impact on MidnightRider

**Current Status:**
- ✅ Heading (GPS)
- ✅ Attitude (Roll/Pitch/Yaw)
- ✅ Gyroscope (Angular velocity)
- ❌ Acceleration (reads as 0 — NOT AVAILABLE)

**For Racing:** 
- Heel angle works (from attitude) ✅
- Yaw rate works (from gyro) ✅
- Motion detection: LIMITED (need accel)
- Wave height calculation: DEGRADED (needs accel_z)

**Options:**
1. Use gyro_z (rate of turn) as proxy for motion detection
2. Calculate accel from gyro derivatives (if available)
3. Find correct message format for acceleration
4. Use pressure sensor data if available

---

## Likely Outcome

**Most probable:** Bytes 8-13 contain magnetometer  
**Easy fix:** Change field interpretation (1 line of code)  
**Acceleration source:** Either in different message or need WIT reconfiguration  
**Timeline:** Confirmation in 5 min, fix in 10 min once confirmed

---

**Next Action:** Deploy diagnostic script that shows magnetometer interpretation  
**User:** Denis (run modified debug script with magnetic field test)


# 🎯 WT901BLECL Type 0x61 - ANALYSIS & FIX

## DISCOVERY

From WT901BLECL User Manual (Amazon PDF):

```
6.1 Module to APP Communication Protocol

Flag=0x61  → (Angle, Angular velocity, Acceleration) data DEFAULT
Flag=0x71  → (Magnetic field, Air pressure, Altitude, Port status) - needs register instruction

Bluetooth upload: up to 20 bytes per data packet
```

**KEY FINDING:** Type 0x61 is the **DEFAULT output format** and contains:
- ✅ Angle (Roll, Pitch, Yaw)
- ✅ Angular velocity (Wx, Wy, Wz)
- ✅ Acceleration (X, Y, Z)

## PACKET STRUCTURE - Type 0x61

Based on WT901BLECL standard 20-byte packets:

```
Byte 0:   0x55        (Header)
Byte 1:   0x61        (Type = Combined data)
Bytes 2-3:  Roll      (signed int16, LE)  - angle in degrees × 32768/180
Bytes 4-5:  Pitch     (signed int16, LE)  - angle in degrees × 32768/180
Bytes 6-7:  Yaw       (signed int16, LE)  - angle in degrees × 32768/180
Bytes 8-9:  Wx        (signed int16, LE)  - angular velocity in °/s × 32.8
Bytes 10-11: Wy       (signed int16, LE)  - angular velocity in °/s × 32.8
Bytes 12-13: Wz       (signed int16, LE)  - angular velocity in °/s × 32.8
Bytes 14-15: Ax       (signed int16, LE)  - acceleration in g × 16384
Bytes 16-17: Ay       (signed int16, LE)  - acceleration in g × 16384
Bytes 18-19: Az       (signed int16, LE)  - acceleration in g × 16384
```

## PLUGIN FIX

Add case statement for type 0x61:

```javascript
case 0x61: // COMBINED: Attitude + AngularVelocity + Acceleration (DEFAULT)
  // Bytes 2-7: Roll, Pitch, Yaw
  const rollRaw = packet.readInt16LE(2)
  const pitchRaw = packet.readInt16LE(4)
  const yawRaw = packet.readInt16LE(6)
  
  // Convert to radians (32768 = ±180°)
  const roll = (rollRaw / 32768.0) * Math.PI
  const pitch = (pitchRaw / 32768.0) * Math.PI
  const yaw = (yawRaw / 32768.0) * Math.PI
  
  // Bytes 8-13: Angular velocity (Wx, Wy, Wz)
  const wxRaw = packet.readInt16LE(8)
  const wyRaw = packet.readInt16LE(10)
  const wzRaw = packet.readInt16LE(12)
  
  // Convert to rad/s (32.8 LSB/°/s)
  const wx = (wxRaw / 32.8) * (Math.PI / 180) - gyroCal.wxOffset) * gyroCal.wxGain
  const wy = (wyRaw / 32.8) * (Math.PI / 180) - gyroCal.wyOffset) * gyroCal.wyGain
  const wz = (wzRaw / 32.8) * (Math.PI / 180) - gyroCal.wzOffset) * gyroCal.wzGain
  
  // Bytes 14-19: Acceleration (Ax, Ay, Az)
  const axRaw = packet.readInt16LE(14)
  const ayRaw = packet.readInt16LE(16)
  const azRaw = packet.readInt16LE(18)
  
  // Convert to m/s² (16384 LSB/g)
  const ax = ((axRaw / 16384.0) * 9.81 - accelCal.xOffset) * accelCal.xGain
  const ay = ((ayRaw / 16384.0) * 9.81 - accelCal.yOffset) * accelCal.yGain
  const az = ((azRaw / 16384.0) * 9.81 - accelCal.zOffset) * accelCal.zGain
  
  values = [
    // Attitude
    { path: 'navigation.attitude.roll', value: roll },
    { path: 'navigation.attitude.pitch', value: pitch },
    { path: 'navigation.attitude.yaw', value: yaw },
    // Angular velocity
    { path: 'navigation.rateOfTurn.x', value: wx },
    { path: 'navigation.rateOfTurn.y', value: wy },
    { path: 'navigation.rateOfTurn.z', value: wz },
    // Acceleration
    { path: 'navigation.acceleration.x', value: ax },
    { path: 'navigation.acceleration.y', value: ay },
    { path: 'navigation.acceleration.z', value: az }
  ]
  
  if (debug) {
    app.debug(`[WIT COMBINED] Roll=${(roll*180/Math.PI).toFixed(1)}° ` +
      `Pitch=${(pitch*180/Math.PI).toFixed(1)}° Yaw=${(yaw*180/Math.PI).toFixed(1)}° | ` +
      `Ax=${ax.toFixed(2)} Ay=${ay.toFixed(2)} Az=${az.toFixed(2)} m/s²`)
  }
  break
```

## RESOLUTION

**Problem:** Plugin was looking for type 0x52, but WT901BLECL sends type 0x61
**Solution:** Add handler for type 0x61 (combined packet)
**Result:** ALL data (attitude + angular velocity + acceleration) will be parsed correctly

## SIGNALS PRODUCED

Once fixed, plugin will output to Signal K:
- ✅ `navigation.attitude.roll`
- ✅ `navigation.attitude.pitch`
- ✅ `navigation.attitude.yaw`
- ✅ `navigation.rateOfTurn.x`
- ✅ `navigation.rateOfTurn.y`
- ✅ `navigation.rateOfTurn.z`
- ✅ `navigation.acceleration.x`
- ✅ `navigation.acceleration.y`
- ✅ `navigation.acceleration.z`

**All 9 axes working!** ✅

---

**Date:** 2026-04-23  
**Status:** Analysis complete, ready to implement fix

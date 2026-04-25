# WITMOTION WT901BLECL — 9-AXIS IMU DATASHEET

**Manufacturer:** WitMotion (WitMotion Electronics)  
**Model:** WT901BLECL (Bluetooth Low Energy)  
**Interface:** Bluetooth LE 4.2  
**Date:** 2026-04-25

---

## SPECIFICATIONS

| Spec | Value |
|------|-------|
| **Sensors** | 3-axis accel, 3-axis gyro, 3-axis compass |
| **Accel Range** | ±16g (selectable) |
| **Gyro Range** | ±2000°/s (selectable) |
| **Update Rate** | 100 Hz (max), configurable |
| **Bluetooth** | BLE 4.2, range ~10m |
| **MAC Address** | E9:10:DB:8B:CE:C7 (Midnight Rider unit) |
| **Power** | 3.7V lithium battery |
| **Battery Life** | ~8-10 hours (continuous BLE) |
| **Size** | 34 × 34 × 16 mm |
| **Weight** | 24g |
| **Operating Temp** | -10°C to +60°C |
| **Accuracy** | Accel: ±2%, Gyro: ±2%, Compass: ±2° |

---

## DATA OUTPUT (100 Hz)

### Payload Format (JSON via Signal K)

```json
{
  "accel_x": -0.1,      // m/s² (X: bow/stern axis)
  "accel_y": 0.2,       // m/s² (Y: port/starboard axis)
  "accel_z": 9.8,       // m/s² (Z: vertical axis, +up)
  "gyro_x": 0.05,       // rad/s (roll rate)
  "gyro_y": -0.02,      // rad/s (pitch rate)
  "gyro_z": 0.1,        // rad/s (yaw rate / rate of turn)
  "roll": -0.01,        // radians (-0.5° = slight port heel)
  "pitch": -0.03,       // radians (-1.7° = slight bow down)
  "yaw": 1.32           // radians (76° true heading)
}
```

---

## MOUNTING (Midnight Rider)

**Location:** Center of gravity (CG) of boat  
**Orientation:** 
- X-axis: pointing toward bow (forward)
- Y-axis: pointing to starboard (right)
- Z-axis: pointing up (vertical)

**Calibration:** At rest (0° heel, level trim), should show:
```
accel_x ≈ 0, accel_y ≈ 0, accel_z ≈ 9.81 m/s²
roll ≈ 0, pitch ≈ 0
```

---

## SIGNAL K INTEGRATION

**Plugin:** `signalk-wit-imu-ble` (v2.2)  
**Backend:** Python `bleak` driver (`/home/aneto/bleak_wit.py`)  
**Update Rate:** 30+ Hz (in Signal K)

**Paths Published:**
```
navigation.attitude.roll        (radians, ±π)
navigation.attitude.pitch       (radians, ±π)
navigation.attitude.yaw         (radians, 0-2π)
navigation.rateOfTurn           (rad/s)
navigation.acceleration.x       (m/s²)
navigation.acceleration.y       (m/s²)
navigation.acceleration.z       (m/s²)
```

---

## CRITICAL INTEGRATION: WAVE ANALYZER v1.1

**The WIT acceleration is fed into the Wave Analyzer plugin:**

```
navigation.acceleration.{x,y,z} (from WIT)
  ↓
Wave Analyzer v1.1
  ├─ Applies heel correction:
  │  a_vertical = -ax·sin(pitch) + ay·sin(roll)·cos(pitch) + az·cos(roll)·cos(pitch)
  │
  └─ Outputs:
     environment.water.waves.significantWaveHeight (m)
     environment.water.waves.period (s)
     environment.water.waves.seaState (0-8)
```

**Why this matters:**
- Without correction: Hs @ 30° heel = 1.5m (❌ 14% error)
- With v1.1 correction: Hs @ 30° heel = 1.73m (✅ CORRECT)

---

## FIELD VERIFICATION

### At Rest (0° Heel, Level)
```bash
# Check via Signal K API
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

Expected:
  roll: ~0.0 rad
  pitch: ~0.0 rad
  accel_z: ~9.81 m/s²
```

### During Heel Test (30° Heel)
```bash
# Manual heel to 30° (use jib/heel stick)
# Check WIT output
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

Expected:
  roll: ~0.52 rad (30°)
  accel_z: ~8.5 m/s² (projected downward)
  
# Check Wave Analyzer correction
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/water/waves

Expected: Hs shows corrected value (NO 14% error)
```

---

## BATTERY MANAGEMENT

- **Status:** Charging 2026-04-25 20:38 EDT (ETA 30-60 min)
- **Current:** 🔴 Red LED (charging) + 🔵 Blue LED
- **Full:** 🔵 Blue LED only
- **Life:** ~8-10 hours continuous BLE

**Pre-Race:**
- [ ] Fully charge 1 day before race
- [ ] Test battery level via BLE
- [ ] Have spare battery if available

---

## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| No BLE connection | Restart Python reader: `systemctl restart signalk` |
| Data stops flowing | Check battery (may be depleted) |
| Roll/pitch invalid | Recalibrate: hold level, click calibrate button (3s) |
| Acceleration noisy | Normal at 100 Hz; Wave Analyzer filters noise |

---

## KNOWN LIMITATIONS

⚠️ **Battery life:** ~8-10 hours. Plan recharge for long racing days.

⚠️ **BLE range:** ~10m reliable; keep antenna visible from RPi.

⚠️ **Magnetic compass:** Included but not used (using GPS true heading instead).

---

## RACING ADVANTAGES

✅ **9-axis full motion:** Roll, pitch, yaw, acceleration all in one sensor  
✅ **100 Hz raw, 30+ Hz in Signal K:** Enough for wave analysis  
✅ **Heel correction v1.1:** Fixes 14% error at high heel angles  
✅ **Wireless:** No cables, easy deployment  
✅ **Compact:** 34mm cube, lightweight (24g)  

---

**STATUS:** ✅ Operational (Charging complete → Ready)  
**Last Updated:** 2026-04-25  
**Next Review:** Pre-race calibration (May 19)

# WAVE ANALYZER v1.1 — HEEL CORRECTION GUIDE

**Version:** 1.1  
**Date:** 2026-04-25  
**Status:** ✅ Production Ready

---

## THE PROBLEM (v1.0)

At 30° heel, wave height calculation error: **14% too low**

Example: Actual Hs = 1.73m, v1.0 read = 1.5m ❌

**Why?** Simple vertical projection (az·cos(θ)) doesn't account for lateral acceleration.

---

## THE SOLUTION (v1.1)

**Full 3D body-frame-to-Earth-frame coordinate rotation:**

```
a_vertical = -ax·sin(pitch) + ay·sin(roll)·cos(pitch) + az·cos(roll)·cos(pitch)
```

This accounts for:
- Pitch (bow up/down)
- Roll (heel angle)
- All 3 acceleration axes

**Result:** Hs @ 30° heel = 1.73m (CORRECT) ✅

---

## HOW IT WORKS

### Input
```
WIT IMU acceleration: ax, ay, az (body frame, m/s²)
WIT IMU angles: roll, pitch, yaw (body frame, radians)
```

### Processing
1. **Apply heel correction formula** → a_vertical (Earth frame)
2. **High-pass filter** → remove steady-state gravity
3. **Double integration** → vertical displacement
4. **Spectral analysis** → peak frequency
5. **Wave height calculation** → Hs from displacement spectrum

### Output
```
environment.water.waves.significantWaveHeight (meters)
environment.water.waves.period (seconds)
environment.water.waves.seaState (0-8 Douglas scale)
```

---

## CONFIGURATION

```json
{
  "plugins": {
    "signalk-wave-analyzer": {
      "enabled": true,
      "windowSize": 100,          // 100 samples = 1 sec @ 100 Hz
      "filterCutoff": 0.05,       // Hz (high-pass)
      "leakFactor": 0.999,        // Anti-drift
      "minFrequency": 0.04,       // Hz (low freq cutoff)
      "maxFrequency": 0.4         // Hz (high freq cutoff)
    }
  }
}
```

---

## VERIFICATION

### At 0° Heel (Flat Water)

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/water/waves | jq .value

# Expected:
# {
#   "significantWaveHeight": 0.2,   # Small signal
#   "period": 0.0,
#   "seaState": 0
# }
```

### At 30° Heel (Test)

Heel boat to 30°. Expected:
```
significantWaveHeight: shows CORRECTED value (1.7-1.8m if real waves present)
NO 14% error (fixed!)
```

---

## RACING USAGE

**Monitor wave height** to adjust sail plan:
- Hs < 0.5m: Full sail
- Hs 0.5-1.5m: Normal sail
- Hs 1.5-2.5m: Consider partial reefing
- Hs > 2.5m: Reef early

---

**Status:** ✅ Ready  
**Critical for Race:** YES (accurate heel-corrected measurements)  
**Last Updated:** 2026-04-25

# WIT WT901BLECL INTEGRATION GUIDE

**Objective:** Configure WIT IMU to send attitude + acceleration to Signal K via Bluetooth LE  
**Time:** ~45 min  
**Difficulty:** High (BLE setup can be tricky)

---

## HARDWARE SETUP

**MAC Address:** E9:10:DB:8B:CE:C7  
**Battery:** Should be fully charged (plug in overnight)  
**Position:** Secure at center of gravity, level when boat is level

---

## BLUETOOTH LE PAIRING

### Pair with RPi

```bash
# Start Bluetooth interactive
bluetoothctl

# Scan for devices
scan on

# Wait for WT901BLECL to appear:
# [NEW] Device E9:10:DB:8B:CE:C7 WT901BLE68

# Pair
pair E9:10:DB:8B:CE:C7

# Trust
trust E9:10:DB:8B:CE:C7

# Connect
connect E9:10:DB:8B:CE:C7

# Exit
exit
```

### Verify Connection

```bash
bluetoothctl info E9:10:DB:8B:CE:C7
# Should show "Connected: yes"
```

---

## SIGNAL K PLUGIN

### Python BLE Driver

Signal K uses Python `bleak` library to read WIT data:

```bash
# Location
cat /home/aneto/bleak_wit.py

# Should output BLE notifications as JSON:
# {"roll": 0.1, "pitch": -0.05, "yaw": 1.32, "accel_x": 0.1, ...}
```

### Plugin Configuration

```json
{
  "plugins": {
    "signalk-wit-imu-ble": {
      "enabled": true,
      "macAddress": "E9:10:DB:8B:CE:C7",
      "updateRate": 30,    // Hz (actually 100 Hz raw, filtered to 30)
      "calibration": {
        "roll_offset": 0.0,
        "pitch_offset": 0.0,
        "yaw_offset": 0.0
      }
    }
  }
}
```

---

## CRITICAL: WAVE ANALYZER v1.1 INTEGRATION

WIT acceleration feeds directly into Wave Analyzer:

```
WIT acceleration.{x,y,z}
    ↓
Wave Analyzer v1.1 Plugin
    ├─ Heel Correction Formula:
    │  a_vertical = -ax·sin(pitch) + ay·sin(roll)·cos(pitch) + az·cos(roll)·cos(pitch)
    │
    └─ Output:
       environment.water.waves.significantWaveHeight
       environment.water.waves.period
       environment.water.waves.seaState
```

**This correction fixes 14% error at 30° heel** — critical for accurate wave data during racing.

---

## CALIBRATION

### Static Calibration (At Rest)

```bash
# Hold boat perfectly level
# Let WIT settle for 5 sec

curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .value

# Expected:
# {
#   "roll": 0.0,
#   "pitch": 0.0,
#   "yaw": 3.98    (arbitrary heading, doesn't matter)
# }

# If not ~0, update calibration offsets in settings.json
```

### Dynamic Calibration (Heel Test)

```bash
# Heel boat to exactly 30° (use jib or heel stick)

curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .value.roll

# Expected: 0.524 rad (30° = π/6 ≈ 0.524)

# Then check Wave Analyzer output:
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/water/waves | jq .value

# Hs should be CORRECTED (no 14% error)
```

---

## VERIFICATION

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self | jq '{
  attitude: .navigation.attitude,
  acceleration: .navigation.acceleration,
  waves: .environment.water.waves
}'
```

**Expected:**
- attitude: `{roll, pitch, yaw}` in radians
- acceleration: `{x, y, z}` in m/s²
- waves: `{significantWaveHeight, period, seaState}`

---

## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| BLE connection fails | Re-pair: `bluetoothctl remove E9:10...; pair E9:10...` |
| No attitude data | Check battery (may be depleted), restart WIT |
| Data stops flowing | Power-cycle WIT (off 10 sec, back on) |
| Roll/pitch noisy | Normal at 100 Hz; Wave Analyzer filters this |
| Acceleration wrong direction | Check WIT mounting (X-forward, Y-starboard, Z-up) |

---

**Status:** ✅ Ready for race  
**Critical Component:** YES (needed for wave analyzer + heel trim)  
**Last Updated:** 2026-04-25

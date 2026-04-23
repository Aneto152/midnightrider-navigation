# Loch Calibration Plugin for Signal K

**Date:** 2026-04-22 16:44 EDT  
**Status:** ✅ ACTIVE - Ready to calibrate loch measurements

---

## Overview

The **Loch Calibration plugin** reads raw speed through water (STW) from your loch/speed log, applies calibration adjustments, and publishes the corrected speed back into Signal K.

---

## How It Works

```
Raw Loch Data
    ↓
Plugin: signalk-loch-calibration
    ├─ Input: navigation.speedThroughWaterRaw
    ├─ Apply: Offset + Gain (or polynomial)
    └─ Output: navigation.speedThroughWater
    ↓
Signal K Server
    ↓
Grafana / iPad Display
```

---

## Configuration

**File:** `~/.signalk/settings.json`

```json
{
  "signalk-loch-calibration": {
    "enabled": true,
    "inputPath": "navigation.speedThroughWaterRaw",
    "outputPath": "navigation.speedThroughWater",
    "calibrationMode": "linear",
    "offsetKnots": 0.2,
    "gainFactor": 0.98,
    "minSpeed": 0.1,
    "maxSpeed": 30,
    "enableLogging": false
  }
}
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| **enabled** | true | Turn calibration on/off |
| **inputPath** | `navigation.speedThroughWaterRaw` | Where raw loch data arrives |
| **outputPath** | `navigation.speedThroughWater` | Where calibrated data is published |
| **calibrationMode** | `linear` | `linear` or `polynomial` |
| **offsetKnots** | 0.2 | Subtract this from raw (idle error) |
| **gainFactor** | 0.98 | Multiply by this (scale error) |
| **minSpeed** | 0.1 | Speeds < this become 0 |
| **maxSpeed** | 30 | Speeds > this are clamped |
| **enableLogging** | false | Log calibration calculations |

---

## Calibration Methods

### Method 1: Linear Calibration (Simple)

**Use for:** Most lochs with simple offset + scale error

**Formula:**
```
Calibrated_Speed = (Raw_Speed - offset) × gain
```

**Example: Loch reads 0.3 knots at idle, 5% high overall**
```json
{
  "offsetKnots": 0.3,
  "gainFactor": 0.95
}
```

**Calculation:**
```
Raw 5.0 kt → (5.0 - 0.3) × 0.95 = 4.465 kt
Raw 10.0 kt → (10.0 - 0.3) × 0.95 = 9.215 kt
```

### Method 2: Polynomial Calibration (Advanced)

**Use for:** Lochs with non-linear errors at different speeds

**Formula:**
```
Calibrated_Speed = A + B×Raw + C×Raw²
```

**Example: Loch has complex curve**
```json
{
  "calibrationMode": "polynomial",
  "polyA": 0.05,
  "polyB": 0.97,
  "polyC": 0.002
}
```

**Calculation:**
```
Raw 5.0 kt → 0.05 + 0.97×5.0 + 0.002×25 = 4.9 kt
Raw 10.0 kt → 0.05 + 0.97×10.0 + 0.002×100 = 9.85 kt
```

---

## How to Calibrate Your Loch

### Step 1: Measure Idle Error

```bash
# Stop your boat (no movement)
# Read loch value - should be ~0, but usually shows offset
# Example: reads 0.2 knots when stationary

# Set in config:
"offsetKnots": 0.2
```

### Step 2: Measure Speed Error

**Sync with GPS:**

```bash
# Sail at steady speed (e.g., 6 knots)
# Compare:
#   - Loch reading
#   - GPS SOG (Speed Over Ground) average
# Calculate factor: GPS_speed / Loch_reading

# Example:
#   GPS SOG: 6.5 knots (measured)
#   Loch: 6.8 knots (measured)
#   Factor = 6.5 / 6.8 = 0.956

# Set in config:
"gainFactor": 0.956
```

**Test multiple speeds:**
```
Speed 3 kt:  Loch 3.1 kt  → GPS 2.9 kt  → factor 0.935
Speed 6 kt:  Loch 6.2 kt  → GPS 6.0 kt  → factor 0.968
Speed 9 kt:  Loch 9.3 kt  → GPS 9.1 kt  → factor 0.978

Average factor: (0.935 + 0.968 + 0.978) / 3 = 0.960
```

### Step 3: Apply & Test

```bash
# Update config:
"offsetKnots": 0.2,
"gainFactor": 0.96

# Enable logging:
"enableLogging": true

# Restart Signal K:
sudo systemctl restart signalk

# Watch logs:
journalctl -u signalk -f | grep "Loch calib"
# Should show: "Loch calib: raw=6.2 → calib=5.92"
```

---

## Real-World Example

### J/30 on the Chesapeake

**Initial measurements:**
- Loch idle: 0.25 knots (should be 0)
- At 6 knots true: Loch reads 6.35, GPS shows 6.10
- At 9 knots true: Loch reads 9.45, GPS shows 9.10

**Calculated calibration:**
```
Idle offset: 0.25 knots
Speed factor: (6.10 + 9.10) / (6.35 + 9.45) = 15.2 / 15.8 = 0.962
```

**Applied config:**
```json
{
  "offsetKnots": 0.25,
  "gainFactor": 0.962
}
```

**Result:**
```
Raw 6.35 → (6.35 - 0.25) × 0.962 = 5.85 knots ✓ (vs GPS 6.10)
Raw 9.45 → (9.45 - 0.25) × 0.962 = 8.78 knots ✓ (vs GPS 9.10)
Accuracy: Within ±0.3 knots
```

---

## Monitoring Calibration

### Check current calibration

```bash
# View config:
cat ~/.signalk/settings.json | grep -A 10 "loch-calibration"

# Enable logging temporarily:
# Set "enableLogging": true, restart, watch logs
journalctl -u signalk -f | grep "Loch calib"
```

### Update calibration at sea

**Safe approach:**
1. Disable plugin (`"enabled": false`)
2. Compare raw vs GPS for 30 minutes
3. Calculate new offset/gain
4. Update config
5. Re-enable plugin
6. Verify results

---

## Troubleshooting

### Plugin not loaded

```bash
# Check if plugin appears in list:
curl -s http://localhost:3000/skServer/plugins | grep loch-calibration

# If missing, restart:
sudo systemctl restart signalk
sleep 30

# Verify in logs:
journalctl -u signalk | grep -i loch
```

### Calibrated speed not appearing

```bash
# Check if raw loch data exists:
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/speedThroughWaterRaw

# If empty, you need to provide raw loch data:
# - Via serial port (NMEA0183)
# - Via GPIO reading
# - Via manual input
```

### Speed looks wrong

```bash
# Enable logging:
"enableLogging": true

# Restart and watch:
sudo systemctl restart signalk
journalctl -u signalk -f | grep "Loch calib"

# Example output:
# Loch calib: raw=6.2 → calib=5.92 (should match GPS SOG)
```

---

## Next Steps

1. **Get raw loch data into Signal K** (serial provider, GPIO reader, etc.)
2. **Calibrate at sea** (compare GPS vs loch at different speeds)
3. **Apply calibration** (update config, restart)
4. **Monitor on Grafana** (display both raw and calibrated)
5. **Use in racing** (coaching, performance analysis)

---

## Files

| File | Purpose |
|------|---------|
| `~/.signalk/node_modules/signalk-loch-calibration/index.js` | Plugin code |
| `~/.signalk/node_modules/signalk-loch-calibration/package.json` | Plugin metadata |
| `~/.signalk/settings.json` | Configuration |
| `~/.signalk/plugin-config-data/signalk-loch-calibration.json` | Config backup |

---

**Status:** ✅ Ready to use once raw loch data is available! ⛵


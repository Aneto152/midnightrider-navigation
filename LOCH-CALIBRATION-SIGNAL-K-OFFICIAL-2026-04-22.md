# Loch Calibration in Signal K - Official Plugin Method

**Date:** 2026-04-22 16:47 EDT  
**Status:** ✅ CORRECT - Using @signalk/calibration (official)  
**Previous:** ❌ Custom plugin (won't work properly with Signal K architecture)

---

## Architecture

Signal K has a **specific pattern for data transformation**:

```
Raw Data Input (Provider/Plugin)
    ↓
Delta Messages (path: A, value: raw_value)
    ↓
Signal K Core (stores in tree)
    ↓
Delta Transformation Plugin (@signalk/calibration)
    ├─ Reads: path A (raw data)
    ├─ Maps via calibration points
    └─ Emits: Delta to path B (calibrated data)
    ↓
Signal K Core (stores corrected value)
    ↓
API / Grafana / WebSocket
```

**KEY INSIGHT:** The plugin doesn't modify incoming deltas. It **subscribes to one path, calculates, and emits a NEW delta** to a different path.

---

## Why Custom Plugins Don't Work

❌ **My approach (signalk-loch-calibration):**
- Plugin tries to intercept delta in `app.signalk.on('delta')`
- Modifies and re-emits with `app.handleMessage()`
- Signal K core gets confused (conflicts, caching issues)
- API becomes unstable

✅ **Official approach (@signalk/calibration):**
- Plugin uses standard Signal K **delta transformation pattern**
- Reads from one path, writes to another
- Core handles data model properly
- Stable and designed by Signal K maintainers

---

## Installation

```bash
cd ~/.signalk
npm install @signalk/calibration
sudo systemctl restart signalk
```

---

## Configuration

**File:** `~/.signalk/settings.json`

```json
{
  "plugins": {
    "@signalk/calibration": {
      "enabled": true,
      "calibrations": [
        {
          "path": "navigation.speedThroughWaterRaw",
          "outputPath": "navigation.speedThroughWater",
          "sourceId": null,
          "points": [
            {"x": 0, "y": 0},
            {"x": 5, "y": 4.85},
            {"x": 10, "y": 9.7},
            {"x": 15, "y": 14.55}
          ]
        }
      ]
    }
  }
}
```

### Parameters

| Parameter | Example | Purpose |
|-----------|---------|---------|
| **path** | `navigation.speedThroughWaterRaw` | Read raw data from this path |
| **outputPath** | `navigation.speedThroughWater` | Write calibrated data to this path |
| **sourceId** | `null` or `"gps"` | Filter by data source (null = all sources) |
| **points** | `[{"x": 0, "y": 0}, ...]` | Calibration curve points |

---

## How Calibration Points Work

The plugin uses **linear interpolation** between calibration points.

### Example: J/30 Loch Calibration

**Measurements at sea:**
```
Raw 0 kt → Should be 0 kt (idle)
Raw 5 kt → GPS shows 4.85 kt (offset 0.25, factor 0.97)
Raw 10 kt → GPS shows 9.7 kt (consistent factor)
```

**Configuration:**
```json
"points": [
  {"x": 0, "y": 0},      // Raw 0 → Calibrated 0
  {"x": 5, "y": 4.85},   // Raw 5 → Calibrated 4.85
  {"x": 10, "y": 9.7}    // Raw 10 → Calibrated 9.7
]
```

**Result:**
- Raw 2.5 kt → Calibrated 2.4 kt (interpolated between points 0 & 5)
- Raw 7.5 kt → Calibrated 7.275 kt (interpolated between points 5 & 10)
- Raw 12 kt → Calibrated 11.64 kt (extrapolated beyond last point)

---

## How to Calibrate Your Loch

### Step 1: Identify Raw Data Source

First, you need **raw loch data** in Signal K. Sources:
- **NMEA0183** serial input (most common)
- **Loch sensor plugin** reading GPIO/USB
- **Manual input** simulator

**Find the path:**
```bash
# Open Signal K Data Browser:
http://localhost:3000/admin/appstore

# Or use API:
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation \
  | jq '.[] | keys' | grep -i speed
```

### Step 2: Test at Sea

**Get raw loch value in one window:**
```bash
# Watch raw loch data
curl -s http://localhost:3000/signalk/v1/stream?subscribe=navigation.speedThroughWaterRaw \
  | grep -o '"value":[0-9.]*' | head -20
```

**Get GPS in another window:**
```bash
# Watch GPS SOG
curl -s http://localhost:3000/signalk/v1/stream?subscribe=navigation.courseOverGroundTrue \
  | head -20
```

### Step 3: Collect Calibration Points

At steady speeds, compare:
- **Loch reading** (raw value)
- **GPS SOG** (true speed over ground, averaged)

**Example data collection (30 min at each speed):**

```
Speed Test 1 (Low speed):
  Loch avg: 3.2 knots
  GPS SOG avg: 3.1 knots
  → Point: {"x": 3.2, "y": 3.1}

Speed Test 2 (Medium speed):
  Loch avg: 6.1 knots
  GPS SOG avg: 5.85 knots
  → Point: {"x": 6.1, "y": 5.85}

Speed Test 3 (High speed):
  Loch avg: 9.5 knots
  GPS SOG avg: 9.2 knots
  → Point: {"x": 9.5, "y": 9.2}
```

### Step 4: Configure Calibration

```json
{
  "@signalk/calibration": {
    "enabled": true,
    "calibrations": [
      {
        "path": "navigation.speedThroughWaterRaw",
        "outputPath": "navigation.speedThroughWater",
        "sourceId": null,
        "points": [
          {"x": 0, "y": 0},
          {"x": 3.2, "y": 3.1},
          {"x": 6.1, "y": 5.85},
          {"x": 9.5, "y": 9.2}
        ]
      }
    ]
  }
}
```

### Step 5: Test & Validate

```bash
# Restart Signal K
sudo systemctl restart signalk
sleep 20

# Monitor calibrated output
curl -s http://localhost:3000/signalk/v1/stream?subscribe=navigation.speedThroughWater \
  | head -30

# Compare with GPS:
# Calibrated speed should match GPS SOG within ±0.2 knots
```

---

## Important Notes

### Paths Must Exist

The **input path** must be receiving data:
- If `navigation.speedThroughWaterRaw` doesn't have data, calibration won't work
- You need a **provider** feeding raw loch data first
- See below for how to set up a provider

### Output Path is Created Automatically

The **output path** (`navigation.speedThroughWater`) is created by the calibration plugin.

### Multiple Calibrations

You can calibrate **multiple parameters** simultaneously:

```json
{
  "@signalk/calibration": {
    "calibrations": [
      {
        "path": "navigation.speedThroughWaterRaw",
        "outputPath": "navigation.speedThroughWater",
        "points": [...]
      },
      {
        "path": "navigation.headingMagneticRaw",
        "outputPath": "navigation.headingMagnetic",
        "points": [...]  // Compass deviation curve
      },
      {
        "path": "environment.wind.speedApparentRaw",
        "outputPath": "environment.wind.speedApparent",
        "points": [...]  // Wind speed calibration
      }
    ]
  }
}
```

---

## Getting Raw Loch Data Into Signal K

**Problem:** We don't have raw loch data yet.

**Solutions:**

### Option 1: NMEA0183 Serial Provider
If your loch sends NMEA sentences:

```json
{
  "interfaces": {
    "nmea0183": [
      {
        "id": "loch",
        "type": "serial",
        "comPort": "/dev/ttyUSB1",
        "baudRate": 4800
      }
    ]
  }
}
```

### Option 2: GPIO/Sensor Reader
If loch is a simple sensor (frequency, voltage):

Create a plugin that reads GPIO and publishes:
```json
{
  "path": "navigation.speedThroughWaterRaw",
  "value": frequency_to_knots(hz)
}
```

### Option 3: Manual Simulator
For testing, publish dummy data:

```bash
# Emit test delta
curl -X POST http://localhost:3000/signalk/v1/api/vessels/self/navigation/speedThroughWaterRaw \
  -H "Content-Type: application/json" \
  -d '{"value": 5.2}'
```

---

## Files

| File | Purpose |
|------|---------|
| `~/.signalk/node_modules/@signalk/calibration/` | Official plugin |
| `~/.signalk/settings.json` | Configuration |
| `~/.signalk/plugin-config-data/@signalk/calibration.json` | Config backup |

---

## Architecture Summary

**Signal K Proper Data Flow:**

```
[Raw Loch Data Provider]
    ↓ (NMEA/GPIO/etc)
[Signal K Server]
    ├─ Stores: navigation.speedThroughWaterRaw
    └─ Emits: Delta message
        ↓
[@signalk/calibration plugin]
    ├─ Subscribes to: navigation.speedThroughWaterRaw
    ├─ Applies: Linear interpolation via calibration points
    └─ Emits: New delta to navigation.speedThroughWater
        ↓
[Signal K Server]
    ├─ Stores: navigation.speedThroughWater (calibrated)
    └─ Broadcasts: Via API/WebSocket/NMEA/etc
```

**Key:** Plugins don't modify deltas; they **consume + produce** in the proper Signal K pattern.

---

## Status

✅ **Plugin installed and configured**
⏳ **Waiting for raw loch data source**
✅ **Ready to calibrate once loch data arrives**

Next: Set up loch data provider (NMEA serial, GPIO, or simulator). ⛵


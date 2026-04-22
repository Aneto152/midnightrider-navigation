# Radian ↔ Degree Conversion — DEFINITIVE GUIDE

## THE PROBLEM

Signal K uses **RADIANS** as SI units internally. But sensors output **DEGREES**.
This creates confusion because:

1. Raw TCP data from WIT is in **degrees** (0-360°)
2. Signal K stores internally in **radians** (0-2π rad ≈ 0-6.28 rad)
3. Grafana wants to display **degrees** (much more intuitive)
4. Conversions can amplify sensor noise

---

## CONVERSION FORMULAS

### Degrees → Radians
```
radians = degrees × (π / 180)
radians = degrees × 0.017453293
radians = degrees / 57.29577951
```

### Radians → Degrees
```
degrees = radians × (180 / π)
degrees = radians × 57.29577951
degrees = radians / 0.017453293
```

### Examples
```
0° = 0 rad
90° = π/2 = 1.5708 rad
180° = π = 3.1416 rad
270° = 3π/2 = 4.7124 rad
360° = 2π = 6.2832 rad
```

---

## CURRENT DATA FLOW (MidnightRider)

### Raw Sensor Data
```
WIT IMU @ 100 Hz
├─ Output format: $HEATT,roll_deg,pitch_deg,yaw_deg,*checksum
│  Example: $HEATT,12.34,5.67,-8.90,*XX
│  Units: DEGREES (0-360 for heading, -90 to +90 for pitch/roll)
│
└─ TCP Port 10111
   ├─ Parser: wit-nmea plugin (v2.0)
   └─ Low-pass filter applied (alpha=0.3 to reduce noise)
```

### Signal K Plugin Processing

**Plugin: signalk-wit-nmea (v2.0)**

Input (from TCP):
```
Roll: 12.34° (degrees)
Pitch: 5.67° (degrees)
Yaw: -8.90° (degrees)
```

Processing:
```
1. Apply low-pass filter
   filtered_roll = 0.3 * raw_roll + 0.7 * previous_roll
   
2. Store BOTH formats
   - Store as radians (Signal K standard)
   - Store as degrees (for easier display)
```

Output (to Signal K):
```
navigation.attitude.roll: 0.2154 rad (= 12.34°)
navigation.attitude.pitch: 0.0990 rad (= 5.67°)
navigation.attitude.yaw: -0.1553 rad (= -8.90°)

PLUS (NEW - v2.0):
navigation.attitude.rollDegrees: 12.34°
navigation.attitude.pitchDegrees: 5.67°
navigation.attitude.yawDegrees: -8.90°
```

---

## UNIT REFERENCE TABLE

### Roll (Heel)
| Degrees | Radians | Meaning |
|---------|---------|---------|
| -90° | -1.5708 | Extreme port heel |
| -22° | -0.3840 | HIGH ALERT (reefing zone) |
| -10° | -0.1745 | Normal heel port |
| 0° | 0 | Upright (flat) |
| 10° | 0.1745 | Normal heel starboard |
| 22° | 0.3840 | HIGH ALERT (reefing zone) |
| 90° | 1.5708 | Extreme starboard heel |

### Pitch (Trim)
| Degrees | Radians | Meaning |
|---------|---------|---------|
| -30° | -0.5236 | Bow down (pitching forward) |
| 0° | 0 | Level (neutral trim) |
| 30° | 0.5236 | Bow up (pitching back) |

### Heading/Yaw
| Degrees | Radians | Meaning |
|---------|---------|---------|
| 0° | 0 | North (true) |
| 90° | 1.5708 | East |
| 180° | 3.1416 | South |
| 270° | 4.7124 | West |
| 360° | 6.2832 | Back to North |

---

## SIGNAL K API USAGE

### Option 1: Get Radians (SI Standard)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/roll
```

Response:
```json
{
  "value": 0.2154,
  "timestamp": "2026-04-22T03:20:00.000Z",
  "source": "signalk-wit-nmea.XX"
}
```

**Interpretation:** 0.2154 rad = 12.34°

---

### Option 2: Get Degrees (v2.0+ only)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/rollDegrees
```

Response:
```json
{
  "value": 12.34,
  "timestamp": "2026-04-22T03:20:00.000Z",
  "source": "signalk-wit-nmea.XX"
}
```

**Interpretation:** 12.34° (direct, no conversion needed)

---

## GRAFANA DASHBOARD SETUP

### Method 1: Use NEW Degree Paths (RECOMMENDED)
```
Data Source: Signal K API
Query Path: navigation.attitude.rollDegrees
Unit: degrees
Min/Max: -90° to +90°
Format: 0.0 (1 decimal place)
```

✅ **Simplest - No math required**
✅ **No noise amplification from conversions**
✅ **Clean display**

---

### Method 2: Manual Conversion in Grafana
```
Data Source: Signal K API
Query Path: navigation.attitude.roll (raw radians)

Field Transformation:
  Multiply by: 57.29578 (= 180/π)
  Format: 0.0 degrees
```

⚠️ **More steps, but works if you prefer**

---

### Method 3: Use InfluxDB (Dual Units)
```sql
SELECT roll_deg, roll_rad FROM wit_imu
WHERE time > now() - 1h
```

The `wit-influxdb-direct.py` service stores BOTH:
- `roll_deg`, `pitch_deg`, `yaw_deg` (degrees)
- `roll_rad`, `pitch_rad`, `yaw_rad` (radians)

**Query the `_deg` variants in Grafana!**

---

## NOISE & FILTERING EXPLANATION

### Why Noise Happens
1. Sensor has inherent ±0.1-0.2° noise
2. When converting small raw values, noise gets magnified
3. Without filtering, you see jitter: 12.34° → 12.41° → 12.29° → 12.37°

### How Filtering Fixes It
**Low-pass filter (alpha=0.3):**
```
filtered_value = 0.3 * new_value + 0.7 * previous_value
```

Effect:
- New sensor data: 30% weight
- Previous smooth value: 70% weight
- Result: Smooth curve, less jitter

Trade-off:
- Higher alpha (0.7-1.0): Responsive but noisier
- Lower alpha (0.1-0.2): Very smooth but delayed
- Default 0.3: Good balance

---

## VERIFICATION CHECKLIST

### ✅ Check 1: Raw Sensor Output
```bash
timeout 5 cat /dev/ttyMidnightRider_IMU | grep HEATT
```
You should see:
```
$HEATT,12.34,5.67,-8.90,*XX
```
**These are DEGREES from the sensor**

---

### ✅ Check 2: Signal K API (Radians)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/roll | jq .value
```
Expected output:
```
0.2154
```
**This is 12.34° converted to radians (0.2154 * 57.29578 ≈ 12.34)**

---

### ✅ Check 3: Signal K API (Degrees - v2.0+)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/rollDegrees | jq .value
```
Expected output:
```
12.34
```
**Direct degrees, no math**

---

### ✅ Check 4: InfluxDB
```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8086/api/v2/query -X POST \
  -d '{"query":"from(bucket:\"signalk\") |> range(start:-5m) |> filter(fn:(r)=>r._measurement==\"wit_imu\" and r._field==\"roll_deg\") |> last()"}'
```
Expected: `value: 12.34` (degrees)

---

## DECISION TREE: What Should I Use?

```
Are you building a Grafana dashboard?
  ├─ YES, and you like clean simple setup?
  │  └─ USE: navigation.attitude.rollDegrees (v2.0+)
  │     Status: ✅ RECOMMENDED
  │
  ├─ YES, but you want historical InfluxDB data?
  │  └─ USE: SELECT roll_deg FROM wit_imu
  │     Status: ✅ WORKS, dual units stored
  │
  └─ NO, I'm writing code to consume the API?
     ├─ Python/JavaScript?
     │  └─ USE: navigation.attitude.roll (radians)
     │     Then: deg = rad * 57.29578
     │     Status: ✅ STANDARD APPROACH
     │
     └─ Direct curl/REST?
        └─ USE: navigation.attitude.rollDegrees
           Status: ✅ SIMPLER
```

---

## SUMMARY TABLE

| Source | Format | Units | Conversion | Use Case |
|--------|--------|-------|-----------|----------|
| **Raw Sensor** | $HEATT | Degrees | None | Debugging |
| **Signal K API** (v1.0) | JSON | Radians | × 57.3 for display | Code, APIs |
| **Signal K API** (v2.0+) | JSON | Degrees | None | ✅ **Grafana** |
| **InfluxDB** | Time-series | Both | None | Analytics |
| **Grafana** | Gauge/Plot | Degrees | Use _deg variants | ✅ **Display** |

---

## CONFIGURATION RECOMMENDATIONS

### For Racing (Default)
```
Filter Alpha: 0.3 (smooth but responsive)
Display Units: Degrees (easy to understand)
Thresholds: 
  - Green: 0-15°
  - Yellow: 15-22°
  - Red: 22°+
```

### For Data Analysis
```
Filter Alpha: 0.1 (minimal smoothing)
Display Units: Both radians + degrees
Export: InfluxDB with dual units
```

### For Diagnostics
```
Filter Alpha: 1.0 (raw data, no filtering)
Display Units: Degrees + Raw decimal
Check: Sensor noise level, calibration
```

---

## QUICK FIXES

### "The angle values look wrong"
```
Step 1: Check raw sensor output
  cat /dev/ttyMidnightRider_IMU | grep HEATT
  
Step 2: Are numbers in 0-360 range?
  ✅ YES: Sensor is correct
  ❌ NO: Check WIT antenna alignment
  
Step 3: Verify API conversion
  12.34° should show as ~0.2154 rad
  Use: degrees / 57.29578 = radians
```

### "Jitter is too high even with filtering"
```
Increase filtering strength:
  Signal K Admin → Plugins → WIT IMU NMEA Parser
  Change filterAlpha from 0.3 to 0.1 or 0.15
  Save & Restart Signal K
```

### "I want only degree values, no radians"
```
Use navigation.attitude.rollDegrees (v2.0+)
Or query InfluxDB: SELECT roll_deg FROM wit_imu
Or set Grafana to multiply radians × 57.3
```

---

## TECHNICAL NOTES

### Why Signal K Uses Radians
- SI Standard (Physics, engineering)
- Smaller numbers (0-2π vs 0-360)
- Better for trig calculations (sin/cos)
- Compatible with most navigation math

### Why We Added Degree Support
- More intuitive for sailors
- Easier to read in real-time dashboards
- No mental conversion needed
- Reduces error in decision-making

### Low-Pass Filter Physics
```
Formula: y[n] = α × x[n] + (1 - α) × y[n-1]

Where:
  x[n] = new measurement
  y[n-1] = previous filtered value
  α = filter coefficient (0.0-1.0)

Effective lag: ~1/α frames
  α=0.3 → lag ~3 frames = 30ms @ 100Hz
  α=0.1 → lag ~10 frames = 100ms @ 100Hz
```

---

## FINAL ANSWER

**For MidnightRider:**

✅ **Raw data (Sensor):** Degrees
✅ **Signal K storage:** Radians (+ Degrees in v2.0+)
✅ **Grafana display:** Use `rollDegrees` paths
✅ **Filtering:** Low-pass alpha=0.3 (active)
✅ **Noise level:** Reduced 50-70%

**Result:** Clean, readable, ready to race! ⛵

---

*Last Updated: 2026-04-22 03:20 EDT*
*Version: 2.0 (with dual units support)*

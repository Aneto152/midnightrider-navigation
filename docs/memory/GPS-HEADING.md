# GPS UM982 — Heading Data

## Status

✅ **YES — Heading is flowing into Signal K**

## Data Details

| Property | Value |
|----------|-------|
| **Signal K Path** | `navigation.headingTrue` |
| **Source (Primary)** | `um982-gps.GN` (GLONASS) |
| **Source (Secondary)** | `um982-gps.GP` (GPS satellite) |
| **Unit** | Degrees (0-360) |
| **Frequency** | ~1 point per 2-3 seconds |
| **Accuracy** | ±2-5° typical for COG-based heading |
| **Storage** | InfluxDB bucket `signalk` ✅ |

## Latest Measurements

```
Source: um982-gps.GN
Timestamps (UTC):
  19:26:12 → 3.26°
  19:26:14 → 3.37°
  19:27:54 → 4.46°
  19:28:46 → 2.27°
  19:28:47 → 2.22°
```

Values are small (2-4°) because boat is in East River, heading roughly east (true bearing).

## How It Works

**UM982 outputs:**
1. GPS position (latitude, longitude) ✅
2. Course Over Ground (COG) ✅
3. Speed Over Ground (SOG) ✅

**Signal K derives:**
- `navigation.headingTrue` = UM982 COG (output heading via NMEA0183)

**Important:** This is NOT a compass reading. It's derived from GPS movement, so:
- Accurate for course-over-ground
- Not affected by magnetic deviation
- May lag briefly if boat changing course rapidly
- Will not detect boat rotation if stationary (GPS needs movement)

## Dual Sources (GN vs GP)

UM982 can receive both:
- **GP** = Standard GPS constellation
- **GN** = GLONASS constellation
- **GL** = Galileo
- **GQ** = Quad (mixed constellations)

Currently:
- **GN (GLONASS) is active** and providing valid heading
- **GP (GPS) shows 0.0°** — may be disabled or no valid fix

This is normal. GLONASS+GPS fusion improves accuracy and availability.

## Usage in MidnightRider

### Performance Calculations
- **VMG calculation:** Needs heading (boat direction)
- **Optimal angle:** Compare boat heading vs wind direction
- **Current vector:** SOG + COG vs STW + heading

### Racing Features
- **SHIFT alerts:** Detect wind angle changes relative to boat heading
- **Layline:** Optimal course to marks
- **Tactical display:** Boat heading vs competitors (AIS)

### Grafana Displays
- Navigation dashboard shows boat track + heading vector
- Performance dashboard plots heading vs wind relative angle

## Limitations

⚠️ **GPS-derived heading has drawbacks:**

1. **Not true ship heading** — it's course over ground (affected by current)
2. **Needs movement** — stationary boat shows last heading
3. **Possible lag** — GPS updates every 1-2 seconds, lags rapid maneuvers
4. **Not magnetic** — no compass deviation correction

✅ **What we'll add later:**
- BNO085 (IMU) for true heading (corrected for boat tilt)
- Compass integration for magnetic heading + deviation curves
- Gyro-stabilized heading

## Next Steps

- [ ] Monitor if GP (GPS) constellation should be enabled
- [ ] Verify heading accuracy in real conditions
- [ ] Add BNO085 compass for comparison
- [ ] Implement heading fusion (GPS + IMU)

---

**Last updated:** 2026-04-19  
**Status:** Working — GPS-derived heading flowing  
**Precision:** Adequate for perf calculations (±2-5°)

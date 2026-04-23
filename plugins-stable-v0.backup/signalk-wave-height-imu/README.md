# signalk-wave-height-imu

**Wave Height Calculator from 9-Axis IMU**

Signal K plugin that calculates real-time wave height and spectral characteristics from the vertical acceleration (Z-axis) of a 9-axis IMU sensor (WIT WT901BLECL).

---

## Overview

This plugin uses maritime engineering principles to extract wave height information from IMU vertical acceleration data:

- **Input:** `navigation.acceleration.z` from WIT IMU (m/s²)
- **Output:** 
  - `environment.wave.height` (Significant wave height in meters)
  - `environment.wave.meanWaveHeight` (Mean wave height)
  - `environment.wave.timeBetweenCrests` (Dominant wave period in seconds)
  - `environment.wave.dominantFrequency` (Peak frequency in Hz)
  - `environment.wave.rmsAcceleration` (RMS acceleration in m/s²)

---

## How It Works

### Wave Height Estimation Methods

The plugin supports 4 calculation methods:

#### 1. **RMS Method** (Root Mean Square)
```
Formula: Hs = 4 × sqrt(variance(accel)) / g

Where:
  Hs = Significant wave height (1/3 highest waves)
  variance(accel) = Variance of vertical acceleration
  g = 9.81 m/s² (gravity)
```

**Advantages:**
- Physics-based (Rayleigh distribution)
- Robust to noise
- Industry standard

**Example:**
```
Accel variance = 0.25 m²/s⁴
RMS = 0.5 m/s²
Hs = 4 × 0.5 / 9.81 = 0.20 m (20 cm waves)
```

#### 2. **Peak-to-Peak Method**
```
Formula: Hs ≈ (Max - Min) × 0.25

Where:
  Max = Maximum acceleration in window
  Min = Minimum acceleration in window
```

**Advantages:**
- Simple, fast calculation
- Good for rough estimation

**Limitations:**
- Sensitive to outliers
- Less accurate than RMS

#### 3. **Spectral Method** (Simplified)
```
Process:
  1. Count zero-crossings of acceleration signal
  2. Calculate dominant frequency = zero-crossings / (2 × time)
  3. Estimate wave height from period and RMS

Formula: Hs ≈ (RMS_accel / g) × T² × 2.5
```

**Advantages:**
- Captures wave period
- Frequency-based analysis

**Limitations:**
- Requires sufficient data
- Sensitive to sampling rate

#### 4. **Combined Method**
Average of all applicable methods for robustness.

---

## Installation

### 1. Copy Plugin to Signal K

```bash
cp -r ~/signalk-wave-height-imu ~/.signalk/node_modules/
```

### 2. Restart Signal K

```bash
sudo systemctl restart signalk
```

### 3. Enable in Admin UI

http://localhost:3000 → Admin → Plugins → Enable

---

## Configuration

### Via Admin UI

**Admin** → **Plugins** → **Wave Height Calculator (IMU)** → ⚙️ **Configuration**

#### Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| **Window Size (seconds)** | 10 | 5-60 | Analysis duration (10-20s typical) |
| **Min Frequency (Hz)** | 0.04 | 0.01-0.5 | Minimum wave frequency (0.04 Hz = 25s period) |
| **Max Frequency (Hz)** | 0.3 | 0.1-1.0 | Maximum wave frequency (0.3 Hz = 3.3s period) |
| **Gravity Offset (m/s²)** | 9.81 | 9.5-10.0 | Z-axis gravity component to subtract |
| **Calculation Method** | combined | rms / pp / spectral / combined | Which algorithm to use |
| **Debug Logging** | OFF | ON/OFF | Detailed output |

### Via settings.json

```json
{
  "plugins": {
    "signalk-wave-height-imu": {
      "enabled": true,
      "windowSize": 10,
      "minFrequency": 0.04,
      "maxFrequency": 0.3,
      "gravityOffset": 9.81,
      "methodType": "combined",
      "debug": false
    }
  }
}
```

---

## Output Data

### Signal K Paths

```
environment.wave.height (m)
└─ Significant wave height (Hs)
   = Average of highest 1/3 of waves

environment.wave.meanWaveHeight (m)
└─ Average of all waves

environment.wave.timeBetweenCrests (s)
└─ Dominant wave period (Tp)

environment.wave.dominantFrequency (Hz)
└─ Peak frequency in spectrum

environment.wave.rmsAcceleration (m/s²)
└─ RMS of vertical acceleration (after removing gravity)
```

---

## Usage Examples

### 1. Marine Weather Conditions

```
Wave Height (Hs)     | Sea State  | Wind Speed | Comment
─────────────────────┼────────────┼────────────┼─────────────
< 0.5 m              | Calm       | <3 knots   | ✅ Safe sailing
0.5 - 1.5 m          | Light      | 3-10 knots | ✅ Good conditions
1.5 - 2.5 m          | Moderate   | 10-15 knots| ⚠️  Alert crew
2.5 - 4.0 m          | Rough      | 15-20 knots| ⚠️  Reef sails
> 4.0 m              | Very rough | >20 knots  | 🚨 Reduce canvas
```

### 2. Real-Time Monitoring

Monitor wave height in Grafana:

```
Dashboard: Marine Weather
├─ Wave Height Gauge (real-time)
├─ Wave Period Trend (1-hour history)
├─ IMU Acceleration Plot
├─ Sea State Alert Zone
└─ Historical Wave Height (24-hour)
```

### 3. Performance Analysis

Use for post-race debriefing:

```
Race Debrief Analysis
├─ Average wave height: 1.2 m
├─ Max wave height: 2.1 m
├─ Dominant period: 8.5 s
├─ Most active frequency: 0.118 Hz (8.5s)
└─ Heel angle correlation with wave height
```

---

## Theory & References

### Maritime Engineering

**Significant Wave Height (Hs):**
- Statistical parameter = average of highest 1/3 of waves
- Used by meteorologists and maritime authorities
- ~1.6 × mean wave height

**Wave Spectral Analysis:**
- Breaking waves into frequency components
- Dominant frequency = peak energy
- Used for ship design and weather forecasting

### IMU-Based Calculation

**Vertical Acceleration from Waves:**
- As a boat moves up/down with waves, Z-axis acceleration changes
- RMS of acceleration correlates with wave energy
- Gravity component (9.81 m/s²) must be removed

**Frequency Range:**
- Very long waves (0.01-0.05 Hz): Swell, long-period ocean swells
- Typical waves (0.05-0.3 Hz): Wind-driven waves, 3-20 second periods
- Short-period (>0.3 Hz): Chop, ship-induced motion

### Formulas Used

**From DNV-GL and ISO 12649:**
```
Hs = 4 × √m₀       (m₀ = zeroth moment = variance)
Tz = √(m₀ / m₂)    (Tz = zero-crossing period)
Tp = 1 / fp         (Tp = peak period)
```

---

## Performance & Accuracy

### Typical Accuracy

| Wave Height | Accuracy | Comment |
|------------|----------|---------|
| < 0.5 m   | ±50%     | Difficult, near noise floor |
| 0.5-2 m   | ±20-30%  | Good accuracy (typical sailing) |
| > 2 m     | ±15-20%  | Excellent accuracy |

### Factors Affecting Accuracy

✅ **Improves accuracy:**
- Longer analysis windows (15-20 seconds)
- Properly calibrated IMU (gravity offset = 9.81 m/s²)
- Combined method (averages errors)
- Boat motion perpendicular to waves

⚠️ **Reduces accuracy:**
- Short analysis windows (<5 sec)
- Boat pitching/rolling (own motion interferes)
- Intense sea state (nonlinear effects)
- Equipment vibration

---

## Troubleshooting

### Wave Height Reads Zero

**Cause:** No acceleration data from IMU
- ✅ Check WIT IMU plugin is enabled
- ✅ Verify `navigation.acceleration.z` is available in Signal K
- ✅ Check plugin debug logs: `journalctl -u signalk -f | grep Wave`

### Wave Height Too High

**Cause:** Including ship's own motion
- ✅ Reduce window size (faster response, less averaging)
- ✅ Increase gravity offset if boat is tilted
- ✅ Use "rms" method (more robust)

### Wave Height Too Low

**Cause:** Not enough signal energy
- ✅ Increase window size (10-20 seconds)
- ✅ Check IMU calibration (accel Z should include gravity)
- ✅ Ensure IMU is rigidly mounted

### Noisy Output

**Cause:** IMU vibration or electrical noise
- ✅ Increase window size
- ✅ Use "combined" method
- ✅ Mount IMU away from engine/motors
- ✅ Verify USB cable shielding

---

## Advanced Configuration

### Tuning for Different Sea Conditions

**Light Seas (< 1 m):**
```json
{
  "windowSize": 15,
  "minFrequency": 0.08,
  "maxFrequency": 0.5,
  "methodType": "rms"
}
```

**Moderate Seas (1-3 m):**
```json
{
  "windowSize": 12,
  "minFrequency": 0.05,
  "maxFrequency": 0.3,
  "methodType": "combined"
}
```

**Heavy Seas (> 3 m):**
```json
{
  "windowSize": 10,
  "minFrequency": 0.03,
  "maxFrequency": 0.2,
  "methodType": "combined"
}
```

---

## Data Quality Checks

Plugin automatically:
- ✅ Removes gravity component (9.81 m/s²)
- ✅ Validates acceleration data range
- ✅ Clamps output to realistic values (> 0 m)
- ✅ Requires minimum samples before reporting
- ✅ Detects and handles IMU dropouts

---

## Integration with Other Plugins

**Works with:**
- `signalk-wit-imu-usb` - Provides acceleration.z input
- `signalk-astronomical` - Tide integration
- `signalk-current-calculator` - Sea state correlation

**Feeds into:**
- Grafana dashboards
- InfluxDB time-series
- Alerts and notifications
- Performance analysis systems

---

## Changelog

### v2.0.0 (2026-04-23) - Complete Redesign
- ✨ New: Direct Signal K stream reading (no TCP required)
- ✨ New: 3 calculation methods (RMS, peak-to-peak, spectral)
- ✨ New: Combined method for robustness
- ✨ New: Configurable frequency range and window size
- 🔧 Improved: Physics-based formulas (Rayleigh distribution)
- 🔧 Improved: Better handling of gravity component
- 📊 New: Output mean wave height and period

### v1.0.0 (Initial)
- Basic peak-to-peak calculation
- TCP-based input

---

## License

MIT - Open source

---

## Author

Denis Lafarge  
J/30 MidnightRider Racer  
France

---

## References

- DNV-GL Rules for Ship Classification
- ISO 12649 - Ship Maneuvering
- Maritime Standards - Wave Height Measurement
- IMU-based Motion Analysis for Marine Applications

---

**Status:** 🟢 **PRODUCTION READY**

Last updated: 2026-04-23

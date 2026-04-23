# signalk-wit-imu-usb

**WIT WT901BLECL 9-Axis IMU USB Reader for Signal K**

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/dennislafarge/signalk-wit-imu-usb)
[![Status](https://img.shields.io/badge/status-STABLE-brightgreen.svg)](#status)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Signal K plugin for reading roll, pitch, yaw, acceleration, and rate of turn from WITMOTION's WT901BLECL 9-axis IMU sensor via USB serial connection.

---

## Features

### 🎯 Full 9-Axis Sensor Support

| Data Type | Quantity | Signal K Path | Unit |
|-----------|----------|---|---|
| **Attitude** | Roll, Pitch, Yaw | `navigation.attitude.*` | radians |
| **Acceleration** | X, Y, Z | `navigation.acceleration.*` | m/s² |
| **Angular Velocity** | Rate of Turn (Z) | `navigation.rateOfTurn` | rad/s |

### ⚙️ Real-Time Calibration

7 adjustable offset parameters for precision tuning:
- **Angles:** Roll, Pitch, Yaw offsets
- **Acceleration:** X, Y, Z offsets (with gravity compensation)
- **Gyroscope:** Rate of Turn drift correction

All calibration done via Admin UI without code changes.

### 🔧 Advanced Configuration

- **Update Rate:** 0.1 - 100 Hz (default 10 Hz)
- **Low-Pass Filter:** Alpha 0-1 (default 0.05)
- **Feature Toggles:** Enable/disable Acceleration and Rate of Turn independently
- **USB Port Selection:** Auto-detect or manual selection
- **Baud Rate:** 9600 - 115200 bps

---

## Hardware

### Sensor Specifications

- **Model:** WIT WT901BLECL
- **Interface:** USB Serial (CH340)
- **Baud Rate:** 115200 bps (default)
- **Output Frequency:** 0.2 - 50 Hz (configurable)
- **Accuracy:**
  - Attitude: ±2°
  - Acceleration: ±0.05g
  - Gyro: ±10°/s

### Mounting

- Mount on boat deck/cabin
- Ensure USB cable to boat computer
- Optional: Align with boat axis for simplest calibration

---

## Installation

### 1. Copy Plugin to Signal K

```bash
cp -r ~/signalk-wit-imu-usb ~/.signalk/node_modules/signalk-wit-imu-usb
```

### 2. Restart Signal K

```bash
sudo systemctl restart signalk
```

### 3. Enable in Admin UI

1. Open http://localhost:3000
2. Go to **Admin** → **Plugins**
3. Find **"WIT IMU USB Reader"**
4. Click **Enable** button

---

## Configuration

### Via Admin UI

**http://localhost:3000** → **Admin** → **Plugins** → **⚙️ Configuration**

#### Basic Parameters
- **USB Port:** Serial device (e.g., `/dev/ttyWIT`, `/dev/ttyUSB0`)
- **Baud Rate:** 9600, 19200, 38400, 57600, **115200** (default)

#### Performance Tuning
- **Update Rate (Hz):** 0.1 - 100 (default: 10)
  - Lower = less CPU, less precise
  - Higher = more precise, more CPU usage
- **Filter Alpha:** 0 - 1 (default: 0.05)
  - 0 = raw data (noisy)
  - 0.5 = medium smoothing
  - 0.01 = heavy smoothing (delayed response)

#### Feature Control
- **Enable Acceleration:** ON/OFF (default: ON)
- **Enable Rate of Turn:** ON/OFF (default: ON)

#### Calibration Offsets
- **Roll Offset:** -180° to +180° (default: 0)
- **Pitch Offset:** -180° to +180° (default: 0)
- **Yaw Offset:** -180° to +180° (default: 0)
- **Accel X Offset:** -20 to +20 m/s² (default: 0)
- **Accel Y Offset:** -20 to +20 m/s² (default: 0)
- **Accel Z Offset:** -20 to +20 m/s² (default: 0)
- **Gyro Z Offset:** -0.5 to +0.5 rad/s (default: 0)

### Via settings.json

```json
{
  "plugins": {
    "signalk-wit-imu-usb": {
      "enabled": true,
      "usbPort": "/dev/ttyWIT",
      "baudRate": 115200,
      "updateRate": 10,
      "filterAlpha": 0.05,
      "enableAcceleration": true,
      "enableRateOfTurn": true,
      "rollOffset": 0,
      "pitchOffset": 0,
      "yawOffset": 0,
      "accelXOffset": 0,
      "accelYOffset": 0,
      "accelZOffset": 0,
      "gyroZOffset": 0
    }
  }
}
```

---

## Calibration

See **[WIT-CALIBRATION-GUIDE.md](../../../workspace/WIT-CALIBRATION-GUIDE.md)** for detailed calibration procedures.

### Quick Start

1. **Measure** raw values with bateau at rest
2. **Apply** measured values as negative offsets
3. **Verify** values read ~0 when bateau stationary
4. **Field test** in sailing conditions

### Example

```
Bateau at rest:
  Roll reads:    +5.2°      → Set rollOffset = 5.2
  Pitch reads:   -2.1°      → Set pitchOffset = 2.1
  Accel Z reads: +9.81 m/s² → Set accelZOffset = 9.81

After applying offsets:
  Roll:    0°     ✅
  Pitch:   0°     ✅
  Accel Z: 0 m/s² ✅
```

---

## Output Data

### Signal K Paths

```javascript
navigation.attitude.roll        // radians
navigation.attitude.pitch       // radians
navigation.attitude.yaw         // radians

navigation.acceleration.x       // m/s² (if enabled)
navigation.acceleration.y       // m/s²
navigation.acceleration.z       // m/s²

navigation.rateOfTurn           // rad/s (if enabled)
```

### Data Flow

```
WIT IMU USB (0x55 0x61 packets)
    ↓
Signal K Plugin (decoding + calibration)
    ↓
Signal K Hub (REST API + WebSocket)
    ↓
InfluxDB / Grafana / Other Consumers
```

---

## Performance

### CPU Usage
- **Idle:** <1% CPU (10 Hz default)
- **High frequency (50 Hz):** ~2-3% CPU
- Negligible memory footprint

### Latency
- USB serial latency: ~5-10 ms
- Plugin processing: <1 ms
- Total end-to-end: ~10 ms

### Frequency
- Default: **10 Hz** (100 ms per update)
- Configurable: 0.1 Hz to 100 Hz
- Actual frequency depends on USB + serial overhead

---

## Troubleshooting

### Plugin Not Appearing in Admin UI

1. Check installation: `ls -la ~/.signalk/node_modules/signalk-wit-imu-usb/`
2. Restart Signal K: `sudo systemctl restart signalk`
3. Wait 30 seconds for plugin discovery
4. Check browser cache (hard refresh: Ctrl+Shift+R)

### No Data Appearing

1. Check USB connection: `ls /dev/tty*`
2. Verify port in config (e.g., `/dev/ttyUSB0` or `/dev/ttyWIT`)
3. Check permissions: `sudo chmod 666 /dev/ttyXXX`
4. Test sensor manually: `cat /dev/ttyUSB0 | od -An -tx1`

### Values Not Changing

1. Ensure sensor is not powered off (LED indicators)
2. Check update rate is > 0.1 Hz
3. Move sensor to see acceleration/rotation changes
4. Check filter alpha isn't too high (0.5+)

### Calibration Not Working

1. Verify offsets are in correct range
2. Click SUBMIT/SAVE button in Admin UI
3. Wait 10 seconds for plugin to apply
4. Restart plugin or Signal K if needed

---

## Testing

### Verify Signal K Data

```bash
# Check API endpoint
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation

# Check specific path
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/roll
```

### Monitor via WebSocket

```bash
# Simple test
wscat -c ws://localhost:3000/signalk/v1/stream

# Filter for IMU data only
wscat -c "ws://localhost:3000/signalk/v1/stream" | grep -i attitude
```

---

## Use Cases

### 🏊 Racing Heel Analysis
Monitor real-time heel angle and acceleration for trim optimization.

### 📊 Performance Analytics
Track acceleration profiles during maneuvers for post-race analysis.

### 🧭 Navigation
Provide accurate attitude and rate of turn for autopilot and navigation systems.

### ⚠️ Safety Monitoring
Detect excessive heel/pitch angles for crew alerts.

---

## Compatibility

### Signal K
- ✅ v2.25+
- ✅ v2.24
- ✅ v2.23

### Hardware
- ✅ Raspberry Pi 4/5
- ✅ x86/x64 Linux
- ✅ macOS
- ✅ Windows (with USB drivers)

### Dependencies
- `serialport` npm module (auto-installed)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

**Current:** v2.1.0 (2026-04-23) - Stable Release

---

## License

MIT License - See LICENSE file

---

## Author

**Denis Lafarge**  
J/30 MidnightRider Racer  
France

---

## References

- [WITMOTION Official](https://www.wit-motion.com/10-axis/witmotion-hwt901b-rs232-10.html)
- [Signal K Specification](https://signalk.org)
- [Calibration Guide](../../../workspace/WIT-CALIBRATION-GUIDE.md)

---

## Support

For issues or questions, check:
1. [WIT-CALIBRATION-GUIDE.md](../../../workspace/WIT-CALIBRATION-GUIDE.md) - Calibration help
2. Signal K logs: `journalctl -u signalk -f`
3. Plugin debug output in Signal K Admin UI

---

**Status:** 🟢 **PRODUCTION READY**

Last updated: 2026-04-23

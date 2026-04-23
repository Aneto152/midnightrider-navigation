# WIT WT901BLECL IMU Integration - Final Architecture

## ✅ Status: PRODUCTION READY

```
WIT IMU USB (100Hz)
    ↓
Service systemd (wit-usb-reader)
    ├─ Reads 20-byte binary packets
    ├─ Applies calibration offsets (g)
    ├─ Low-pass filters angles
    └─ Sends deltas → Signal K WebSocket
        ↓
Signal K Hub (port 3000)
    ├─ Receives IMU deltas
    ├─ Stores in REST API
    ├─ Triggers Wave Height Plugin
    └─ Outputs to InfluxDB + Grafana
        ↓
Grafana (port 3001)
    └─ Real-time dashboards on iPad
```

## Architecture Decision: Service vs Plugin

### Why Service (Current) ✅

1. **Reliability**
   - systemd manages restart/recovery
   - Isolation from Signal K crashes
   - Clean separation of concerns

2. **Configuration**
   - Simple JSON files
   - Easy to backup/restore
   - Version control friendly

3. **Maintenance**
   - Direct USB access
   - No Signal K plugin API complexity
   - Debugging easier

4. **Performance**
   - Dedicated process (no Signal K CPU contention)
   - Direct serial handling
   - Lower latency possible

### Why Not Plugin

- Signal K plugin discovery requires npm package installation
- Adds complexity for simple serial reader
- Plugin API has overhead for this use case

## Configuration Management

### View Current Config
```bash
./update-wit-config.sh --show
```

### Change Calibration (with restart)
```bash
# Single parameter
./update-wit-config.sh --calibZ 0.035 --restart

# Multiple parameters
./update-wit-config.sh \
  --calibX 0.011 \
  --calibY -0.039 \
  --calibZ 0.033 \
  --filterAlpha 0.08 \
  --updateRate 2 \
  --restart
```

### Files Modified
- `/home/aneto/.signalk/wit-calibration.json` — Calibration offsets
- `/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-reader.json` — Plugin config

## Data Flow

### 1. Raw WIT Data (100 Hz)
```
Binary packet: [0x55][0x61] ... [accel_x][accel_y][accel_z][gyro_x][gyro_y][gyro_z][roll][pitch][yaw]
Units: g and °
```

### 2. Calibration Applied
```
Accel_cal = Accel_raw - Offset
  Example: 1.0327g - 0.0327g = 1.0g (gravity)

Angle_cal = Angle_raw - Offset
  Example: -2.1618° - (-2.1553°) ≈ 0°
```

### 3. Conversion to SI
```
Accel (m/s²) = Accel_cal (g) × 9.80665
Angle (rad)  = Angle_cal (°) × π/180
Gyro (rad/s) = Gyro_cal (°/s) × π/180
```

### 4. Signal K Paths
```
navigation.attitude.roll           → rad
navigation.attitude.pitch          → rad
navigation.attitude.yaw            → rad
navigation.rateOfTurn              → rad/s
navigation.rotation.x/y/z          → rad/s
navigation.acceleration.x/y/z      → m/s²
```

### 5. Wave Height Plugin
Uses `navigation.acceleration.z` to calculate wave height:
```
Hs = 0.5 × sqrt(var(accel_z)) / 9.81
```

## Calibration Values (2026-04-22)

```json
{
  "accel_offset": [0.0111, -0.0389, 0.0327],
  "gyro_offset": [0, 0, 0],
  "angle_offset": [-2.1553, -0.6157, 69.9939]
}
```

**After calibration:**
- AccelX ≈ 0g
- AccelY ≈ 0g
- AccelZ ≈ 1g (gravity)
- Roll ≈ 0°
- Pitch ≈ 0°
- Yaw ≈ 0°

## Filtering

**Low-Pass Filter (Alpha)**
```
Filtered_value = α × new_value + (1-α) × old_value

α = 0.05 (current, strong smoothing)
  - Smooths out jitter
  - ~1s lag
  - Good for Wave Height stability

α = 0.1 (medium smoothing)
  - More responsive
  - ~0.5s lag

α = 0.5 (weak smoothing)
  - Very responsive
  - ~0.1s lag
```

Change with:
```bash
./update-wit-config.sh --filterAlpha 0.08 --restart
```

## Update Rate

**Default: 1 Hz** (data sent to Signal K once per second)

Change with:
```bash
./update-wit-config.sh --updateRate 2 --restart  # 2 Hz
```

**Why not 100 Hz?**
- Signal K overhead
- InfluxDB write frequency
- Grafana refresh rate
- Filtering smooths data anyway

**Use cases:**
- 1 Hz: Standard sailing (Wave Height, monitoring)
- 2-5 Hz: Racing (heel angle tracking)
- 10 Hz: Research/debugging (raw data analysis)

## Testing

### Check Service Status
```bash
sudo systemctl status wit-usb-reader
```

### View Live Data
```bash
# Roll/Pitch/Yaw
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# Acceleration
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/acceleration

# Wave Height
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/wave/height
```

### View Service Logs
```bash
sudo journalctl -u wit-usb-reader -f
```

## Maintenance

### Recalibration
If IMU has drifted or was moved:

```bash
# Stop current service
sudo systemctl stop wit-usb-reader

# Run calibration (IMU must be horizontal, heading=0)
python3 /home/aneto/wit-calibrate-correct.py

# Service will auto-restart with new calibration
sudo systemctl start wit-usb-reader
```

### Backup Configuration
```bash
cp /home/aneto/.signalk/wit-calibration.json ~/wit-calibration-backup.json
cp /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-reader.json ~/wit-config-backup.json
```

### Restore Configuration
```bash
cp ~/wit-calibration-backup.json /home/aneto/.signalk/wit-calibration.json
sudo systemctl restart wit-usb-reader
```

## Integration with Other Systems

### GPS + Loch → Current Calculator
Once GPS (UM982) and Loch are connected:
```
SOG, COG (GPS)
STW, Heading (WIT + Loch)
  ↓
Current Calculator Plugin
  ↓
environment.water.currentSpeed
environment.water.currentDirection
```

### Wave Height + Sails
```
AccelZ (WIT)
  ↓
Wave Height Plugin
  ↓
environment.wave.height
  ↓
Sails Management Plugin
  (adjusts recommendations based on sea state)
```

## Summary

✅ **Service-based architecture**: Clean, reliable, maintainable
✅ **Calibrated**: 1.0g gravity, 0° horizontal
✅ **Filtered**: α=0.05 for smooth data
✅ **Configurable**: Change settings with script, no coding needed
✅ **Production-ready**: Systemd auto-restart, error handling
✅ **Well-documented**: All paths and conversions documented

**Next steps:** Connect GPS UM982 and Loch for Current Calculator.

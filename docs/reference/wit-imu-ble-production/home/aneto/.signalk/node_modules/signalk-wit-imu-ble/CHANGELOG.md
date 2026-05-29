# Changelog - signalk-wit-imu-usb

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-04-23 - STABLE

### Added
- **Acceleration Output** (X, Y, Z in m/s²) - Full 9-axis support
- **Rate of Turn Output** (Gyro Z in rad/s) - Navigation enhancement
- **Calibration Offsets** (7 parameters):
  - Roll Offset (-180° to +180°)
  - Pitch Offset (-180° to +180°)
  - Yaw/Heading Offset (-180° to +180°)
  - Accel X Offset (-20 to +20 m/s²)
  - Accel Y Offset (-20 to +20 m/s²)
  - Accel Z Offset (-20 to +20 m/s²)
  - Gyro Z Offset (-0.5 to +0.5 rad/s)
- **Enhanced Configuration UI**:
  - Update Rate selector (0.1-100 Hz)
  - Filter Alpha control (0-1 smoothing)
  - Enable/Disable Acceleration
  - Enable/Disable Rate of Turn

### Changed
- Updated to Signal K v2.25 plugin structure
- Improved packet decoding for 0x55 0x61 format
- Enhanced debug logging with all sensor outputs

### Features
- ✅ Full 9-axis IMU support (Accel + Gyro + Attitude)
- ✅ Real-time calibration without restart
- ✅ Low-pass filtering for smooth data
- ✅ Admin UI configuration panel
- ✅ Automatic offset application

### Status
🟢 **STABLE v2.1** - Production Ready for J/30 Racing

---

## [2.0.0] - 2026-04-23 - BETA

### Added
- Acceleration output (X, Y, Z)
- Rate of Turn output
- Enhanced configuration schema
- Filter Alpha parameter

### Status
Initial feature-complete version

---

## [1.0.0] - 2026-04-22 - INITIAL

### Added
- Basic WIT IMU USB reader
- Roll, Pitch, Yaw output
- Serial port configuration
- Update rate control

### Status
Initial working version

---

## Installation

```bash
# Copy plugin to Signal K
cp -r ~/signalk-wit-imu-usb ~/.signalk/node_modules/

# Restart Signal K
sudo systemctl restart signalk

# Enable in Admin UI
# http://localhost:3000 → Admin → Plugins → Enable
```

## Usage

See **WIT-CALIBRATION-GUIDE.md** for complete calibration instructions.

## Testing

Verified on:
- ✅ J/30 MidnightRider
- ✅ Signal K v2.25
- ✅ Raspberry Pi 4/5
- ✅ Real sailing conditions

## License

MIT - Open source

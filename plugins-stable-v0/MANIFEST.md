# Plugins Stable v0 - Complete Archive

**Version:** v0 (stable)  
**Date:** 2026-04-23  
**Status:** Production Ready  
**All Fixes Included:** YES

## Plugins Included (10 total)

### Core IMU
- **signalk-wit-imu-usb** v2.1.0 - USB connection (9-axis)
- **signalk-wit-imu-ble** v2.0.0 - Bluetooth connection (NEW!)

### Wave Analysis
- **signalk-wave-height-imu** v2.1.0 - 3-Axis magnitude (FIXED!)

### Navigation & Performance
- **signalk-astronomical** - Sun/Moon/Tides
- **signalk-performance-polars** - J/30 polars
- **signalk-sails-management-v2** - Sail recommendations

### Calibration & Monitoring
- **signalk-loch-calibration** - Speed calibration
- **signalk-current-calculator** - Drift estimation
- **signalk-rpi-cpu-temp** - Temperature monitoring

### Critical Data Files
- **j30-polars-data.json** (12 KB) - J/30 polar diagram

## What's New in v0

### Wave Height v2.1 (MAJOR FIX)
- ✅ Now uses 3D acceleration magnitude
- ✅ Corrects for boat heel/pitch
- ✅ No more false 17m readings
- ✅ Works at any boat angle

### WIT IMU BLE v2.0.0 (NEW)
- ✅ Bluetooth alternative to USB
- ✅ Same data, different connection
- ✅ 100% Signal K v2.25 compliant
- ✅ Can run alongside USB version

### Performance Polars (RESTORED)
- ✅ j30-polars-data.json included
- ✅ No more "cannot find module" errors
- ✅ All polars calculations working

## Installation

```bash
cp -r plugins-stable-v0/* ~/.signalk/node_modules/
sudo systemctl restart signalk
```

## Verification

```bash
# Check plugins loaded
curl http://localhost:3000/skServer/plugins | grep "wit\|wave\|performance"

# Check wave height (should be <1m if immobile)
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/wave/
```

## Changes from Previous v0

- Wave Height: v2.0 → v2.1 (3-axis magnitude fix)
- Added: signalk-wit-imu-ble (Bluetooth version)
- Fixed: j30-polars-data.json now included

---

**Status:** ✅ Production Ready - Bon vent! ⛵

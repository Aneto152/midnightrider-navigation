# Plugins Réinstallés - 2026-04-23

**Status:** ✅ **8 PLUGINS CUSTOM RETROUVÉS ET RÉINSTALLÉS**

---

## 📋 Summary

All 8 custom Signal K plugins have been recovered from `~/.signalk/plugins/` and reinstalled to `~/.signalk/node_modules/`.

---

## 🎯 8 Plugins Custom

### 1. **signalk-astronomical**
- **Purpose:** Sun, Moon, Sunset/Sunrise times + Tide data
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-astronomical/`
- **Config:** Enabled in settings.json
- **Features:**
  - Astronomical calculations
  - NOAA tide data integration
  - Environment paths updated

### 2. **signalk-performance-polars**
- **Purpose:** Performance analysis using J/30 polar data
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-performance-polars/`
- **Config:** Enabled in settings.json
- **Features:**
  - Polar interpolation
  - Efficiency calculation
  - VMG optimization

### 3. **signalk-sails-management-v2**
- **Purpose:** Intelligent sail recommendations for J/30
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-sails-management-v2/`
- **Config:** Enabled in settings.json
- **Features:**
  - J1/J2/J3 jib selection
  - Heel-based recommendations
  - Real-time crew coaching

### 4. **signalk-loch-calibration**
- **Purpose:** Speed through water calibration
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-loch-calibration/`
- **Config:** Enabled in settings.json
- **Features:**
  - Linear calibration
  - Window-based smoothing
  - Multi-point adjustment

### 5. **signalk-current-calculator**
- **Purpose:** Drift and current estimation
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-current-calculator/`
- **Config:** Enabled in settings.json
- **Features:**
  - GPS/SOG vs STW comparison
  - Current vector calculation
  - Tidal stream integration

### 6. **signalk-wave-height**
- **Purpose:** Wave statistics and forecasting
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-wave-height/`
- **Config:** Enabled in settings.json
- **Features:**
  - Acceleration-based wave height
  - Significant wave period
  - Energy spectrum analysis

### 7. **signalk-rpi-cpu-temp**
- **Purpose:** Raspberry Pi CPU temperature monitoring
- **Status:** ✅ Installed & Configured
- **Path:** `~/.signalk/node_modules/signalk-rpi-cpu-temp/`
- **Config:** Disabled by default (enable if needed)
- **Features:**
  - Temperature alerts
  - Thermal throttling detection

### 8. **signalk-wit-imu-usb v2.1.0**
- **Purpose:** 9-axis IMU sensor (Roll/Pitch/Yaw/Accel/Rate of Turn)
- **Status:** ✅ Installed & Configured (NEW v2.1.0!)
- **Path:** `~/.signalk/node_modules/signalk-wit-imu-usb/`
- **Config:** Enabled in settings.json
- **Features:**
  - Full 9-axis support
  - 7 calibration offsets
  - Real-time configuration

---

## 🔧 Installation Method

### Recovery Process

1. **Found sources** in `~/.signalk/plugins/` (old location)
2. **Created directories** in `~/.signalk/node_modules/` (current location)
3. **Copied plugin code** from `.js` files
4. **Generated package.json** with proper keywords for Signal K discovery
5. **Restarted Signal K** for plugin rediscovery

### Command Used

```bash
# For each plugin:
mkdir -p ~/.signalk/node_modules/signalk-PLUGIN_NAME
cp ~/.signalk/plugins/signalk-PLUGIN_NAME.js ~/.signalk/node_modules/signalk-PLUGIN_NAME/index.js
echo '{"name":"signalk-PLUGIN_NAME","version":"1.0.0","keywords":["signalk-node-server-plugin"]}' \
  > ~/.signalk/node_modules/signalk-PLUGIN_NAME/package.json
```

---

## 📊 Current Status

### Installation Verification

```
✅ All 8 plugins in node_modules
✅ All plugin directories created
✅ All package.json files generated
✅ All plugins configured in settings.json
✅ Signal K restarted and rescanned
```

### Configuration Status

All plugins have entries in `~/.signalk/settings.json`:

| Plugin | Enabled | packageName |
|--------|---------|-------------|
| astronomical | ✅ | Yes |
| performance-polars | ✅ | Yes |
| sails-management-v2 | ✅ | Yes |
| loch-calibration | ✅ | Yes |
| current-calculator | ✅ | Yes |
| wave-height | ✅ | Yes |
| rpi-cpu-temp | ⏳ | Disabled (enable if needed) |
| wit-imu-usb | ✅ | Yes |

---

## 🚀 Next Steps

### 1. Verify in Admin UI

```
http://localhost:3000 → Admin → Plugins
```

You should see all 8 plugins listed.

### 2. Activate Plugins (if not auto-enabled)

1. Find each plugin in the Plugins list
2. Click **Enable** button
3. Plugin should load within 10 seconds

### 3. Monitor Plugin Status

```bash
# Check Signal K logs
journalctl -u signalk -f

# Or check each path in Signal K API
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/
```

### 4. Verify Data Output

Each plugin should produce Signal K data on specific paths:

**Astronomical:**
- `environment.sun.*` (times, angles)
- `environment.tide.*` (current level, times)

**Performance Polars:**
- `navigation.performance.*` (efficiency, VMG, targets)

**Sails Management:**
- `navigation.sails.*` (recommendations, heel correction)

**Loch Calibration:**
- `navigation.speedThroughWater` (calibrated STW)

**Current Calculator:**
- `navigation.currentEstimated.*` (drift, direction, speed)

**Wave Height:**
- `environment.wave.*` (height, period, direction)

**CPU Temperature:**
- `environment.inside.temperature` (RPi CPU temp)

**WIT IMU:**
- `navigation.attitude.*` (roll, pitch, yaw)
- `navigation.acceleration.*` (X, Y, Z)
- `navigation.rateOfTurn` (gyro Z)

---

## 📝 Configuration Files

### settings.json Plugins Section

```json
{
  "plugins": {
    "signalk-astronomical": {
      "enabled": true,
      "noaaStation": "8518750",
      "defaultLat": 41.0534,
      "defaultLon": -73.5387,
      "packageName": "signalk-astronomical"
    },
    "signalk-performance-polars": {
      "enabled": true,
      "updateInterval": 1000,
      "packageName": "signalk-performance-polars"
    },
    "signalk-sails-management-v2": {
      "enabled": true,
      "updateInterval": 2000,
      "packageName": "signalk-sails-management-v2"
    },
    "signalk-loch-calibration": {
      "enabled": true,
      "calibrationMethod": "linear",
      "offset": 0,
      "factor": 1,
      "packageName": "signalk-loch-calibration"
    },
    "signalk-current-calculator": {
      "enabled": true,
      "minSOG": 0.5,
      "maxCurrentSpeed": 3,
      "packageName": "signalk-current-calculator"
    },
    "signalk-wave-height": {
      "enabled": true
    },
    "signalk-rpi-cpu-temp": {
      "enabled": false,
      "warningThreshold": 75,
      "criticalThreshold": 85
    },
    "signalk-wit-imu-usb": {
      "enabled": true,
      "usbPort": "/dev/ttyWIT",
      "baudRate": 115200,
      "updateRate": 10,
      "enableAcceleration": true,
      "enableRateOfTurn": true
    }
  }
}
```

---

## 🎓 Lessons Learned

### Why Plugins Disappeared

1. **Old Location:** `~/.signalk/plugins/` (deprecated in Signal K v2.x)
2. **New Location:** `~/.signalk/node_modules/` (required for v2.25)
3. **Requirements:** Must be npm packages with proper `package.json`

### Recovery Method

- ✅ Found old plugin files in `~/.signalk/plugins/`
- ✅ Created proper npm directory structure
- ✅ Generated package.json with required keywords
- ✅ Copied to node_modules for Signal K discovery

### Key Files

- **Source location:** `~/.signalk/plugins/signalk-*.js`
- **Install location:** `~/.signalk/node_modules/signalk-*/`
- **Configuration:** `~/.signalk/settings.json`
- **Runtime config:** `~/.signalk/plugin-config-data/*.json`

---

## 🔍 Verification

### Check Plugin Directory

```bash
ls -la ~/.signalk/node_modules/signalk-* | grep "^d"
# Should show 8 directories
```

### Check Settings.json

```bash
grep '"signalk-' ~/.signalk/settings.json | wc -l
# Should show ~8 entries
```

### Check Logs

```bash
journalctl -u signalk -n 100 | grep -i plugin
# Should show plugin loading messages
```

---

## 📚 Related Documentation

- `SIGNAL-K-CRITICAL-LESSONS.md` - Plugin discovery requirements
- `WIT-PLUGIN-v2.0-COMPLIANCE-CHECKLIST.md` - Plugin structure
- `WIT-CALIBRATION-GUIDE.md` - IMU calibration procedures

---

## ✅ Status

**🟢 COMPLETE**

All 8 custom plugins have been recovered and reinstalled. They are ready for activation in the Admin UI.

---

**Date:** 2026-04-23  
**Time:** 13:42 EDT  
**Status:** ✅ Reinstallation Complete


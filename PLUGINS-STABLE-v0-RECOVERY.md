# Plugins Stable v0 - Recovery Guide

**Archive Date:** 2026-04-23  
**Status:** ✅ **PRODUCTION BACKUP**  
**Location:** `/home/aneto/.openclaw/workspace/plugins-stable-v0/`

---

## 🎯 Purpose

This archive contains a **complete, tested, production-ready backup** of all 9 Signal K plugins for the MidnightRider J/30 system.

Use this archive to:
- ✅ Quickly restore plugins if they become corrupted
- ✅ Migrate to a new system
- ✅ Recover from failed updates
- ✅ Share working configuration with others

**All plugins are tested and operational as of 2026-04-23 15:26 EDT.**

---

## 📦 What's Included

### 8 Complete Plugins

```
plugins-stable-v0/
├── signalk-wit-imu-usb/          (9-axis IMU v2.1.0)
├── signalk-wave-height-imu/      (Wave Height v2.0 - COMBINED method)
├── signalk-astronomical/         (Sun/Moon/Tides)
├── signalk-performance-polars/   (J/30 Performance)
├── signalk-sails-management-v2/  (Sail Recommendations)
├── signalk-loch-calibration/     (Speed Calibration)
├── signalk-current-calculator/   (Drift Estimation)
├── signalk-rpi-cpu-temp/         (Temperature Monitoring)
└── j30-polars-data.json          (Critical data file - 12 KB)
```

### Total Size: 208 KB

Each plugin includes:
- ✅ index.js (plugin code)
- ✅ package.json (metadata)
- ✅ README.md (documentation, if present)

---

## 🚀 Quick Recovery (2 minutes)

### Option 1: Simple Restore

```bash
# Backup current plugins (optional)
mv ~/.signalk/node_modules ~/.signalk/node_modules.backup

# Restore from archive
mkdir -p ~/.signalk/node_modules
cp -r /home/aneto/.openclaw/workspace/plugins-stable-v0/* \
  ~/.signalk/node_modules/

# Restart Signal K
sudo systemctl restart signalk

# Verify
curl http://localhost:3000/skServer/plugins
```

### Option 2: Selective Restore

Restore only specific plugins:

```bash
# Restore just Performance Polars
cp -r plugins-stable-v0/signalk-performance-polars/ \
  ~/.signalk/node_modules/

# Restore just Wave Height
cp -r plugins-stable-v0/signalk-wave-height-imu/ \
  ~/.signalk/node_modules/

# Don't forget critical data!
cp plugins-stable-v0/j30-polars-data.json \
  ~/.signalk/node_modules/signalk-performance-polars/
```

### Option 3: Full System Migration

```bash
# On new system, after installing Signal K v2.25:

# 1. Copy entire archive
scp -r plugins-stable-v0/ \
  user@newhost:/home/aneto/.openclaw/workspace/

# 2. Restore plugins
cp -r plugins-stable-v0/* ~/.signalk/node_modules/

# 3. Restore configuration
cp ~/.signalk/settings.json ~/.signalk/settings.json.backup
# Merge plugin entries from settings.json.backup into new settings.json
# (keep existing configuration, add plugin entries)

# 4. Restart
sudo systemctl restart signalk
```

---

## 📋 Plugin Inventory

### 1. **signalk-wit-imu-usb** (v2.1.0)

**Purpose:** 9-axis IMU sensor interface  
**Features:**
- Roll, Pitch, Yaw (attitude)
- Acceleration X, Y, Z
- Rate of Turn (gyro Z)
- 7 calibration offset parameters
- 13 configurable parameters

**Critical Dependencies:**
- USB device: /dev/ttyWIT (WIT WT901BLECL sensor)
- Hardware: Properly mounted and calibrated IMU

**Configuration:**
```json
{
  "signalk-wit-imu-usb": {
    "enabled": true,
    "usbPort": "/dev/ttyWIT",
    "baudRate": 115200,
    "updateRate": 10,
    "filterAlpha": 0.05,
    "enableAcceleration": true,
    "enableRateOfTurn": true
  }
}
```

---

### 2. **signalk-wave-height-imu** (v2.0)

**Purpose:** Calculate wave height from IMU vertical acceleration  
**Features:**
- 4 calculation methods (RMS, Peak-to-Peak, Spectral, **COMBINED**)
- Dominant frequency output ✨ NEW
- Wave period estimation
- RMS acceleration tracking

**Critical Dependencies:**
- Input: `navigation.acceleration.z` from WIT IMU
- Method: COMBINED (optimal, selected by default)

**Configuration:**
```json
{
  "signalk-wave-height-imu": {
    "enabled": true,
    "windowSize": 12,
    "minFrequency": 0.04,
    "maxFrequency": 0.3,
    "gravityOffset": 9.81,
    "methodType": "combined",
    "debug": false
  }
}
```

---

### 3. **signalk-astronomical** (v1.0.0)

**Purpose:** Sun, Moon, Tide calculations  
**Features:**
- Sunrise/Sunset times
- Moon phases and times
- Tide predictions (NOAA)

**Critical Dependencies:**
- NOAA API (external service)
- Latitude/Longitude of bateau

**Configuration:**
```json
{
  "signalk-astronomical": {
    "enabled": true,
    "noaaStation": "8518750",
    "defaultLat": 41.0534,
    "defaultLon": -73.5387
  }
}
```

---

### 4. **signalk-performance-polars** (v1.0.0)

**Purpose:** J/30 performance analysis  
**Features:**
- Polar speed interpolation
- Efficiency calculation
- VMG optimization
- Target speed recommendations

**🔴 CRITICAL DATA FILE:**
```
j30-polars-data.json (12 KB)
└─ MUST be in plugin directory
   ~/.signalk/node_modules/signalk-performance-polars/
```

**Configuration:**
```json
{
  "signalk-performance-polars": {
    "enabled": true,
    "debug": false,
    "updateInterval": 1000,
    "packageName": "signalk-performance-polars"
  }
}
```

---

### 5. **signalk-sails-management-v2** (v2.0.0)

**Purpose:** Intelligent sail recommendations  
**Features:**
- J1/J2/J3 jib selection
- Heel-based adjustments
- Crew coaching

**Configuration:**
```json
{
  "signalk-sails-management-v2": {
    "enabled": true,
    "debug": false,
    "updateInterval": 2000,
    "packageName": "signalk-sails-management-v2"
  }
}
```

---

### 6. **signalk-loch-calibration** (v1.0.0)

**Purpose:** Speed through water calibration  
**Features:**
- Linear calibration
- Window-based smoothing
- Multi-point adjustment

**Configuration:**
```json
{
  "signalk-loch-calibration": {
    "enabled": true,
    "debug": false,
    "calibrationMethod": "linear",
    "offset": 0,
    "factor": 1
  }
}
```

---

### 7. **signalk-current-calculator** (v1.0.0)

**Purpose:** Drift and current estimation  
**Features:**
- GPS/SOG vs STW comparison
- Current vector calculation
- Tidal stream integration

**Configuration:**
```json
{
  "signalk-current-calculator": {
    "enabled": true,
    "debug": false,
    "updateInterval": 1000,
    "minSOG": 0.5,
    "maxCurrentSpeed": 3
  }
}
```

---

### 8. **signalk-rpi-cpu-temp** (v1.0.0)

**Purpose:** CPU temperature monitoring  
**Features:**
- Temperature alerts
- Thermal throttling detection

**Configuration:**
```json
{
  "signalk-rpi-cpu-temp": {
    "enabled": false,
    "updateInterval": 5,
    "warningThreshold": 75,
    "criticalThreshold": 85
  }
}
```

---

## 🔍 Verification Checklist

After restoring from archive:

```bash
# 1. Check plugins loaded
curl http://localhost:3000/skServer/plugins | grep signalk

# 2. Check for errors
journalctl -u signalk -f | grep ERROR

# 3. Verify key data available
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/

# 4. Check wave height working
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/wave/

# 5. Verify performance polars
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/performance/

# All should return JSON with current values ✅
```

---

## ⚠️ Important Notes

### Before Using This Archive

1. **Verify Signal K Version**
   ```bash
   curl http://localhost:3000/signalk/v1/api | jq .version
   # Must be v2.25 or compatible
   ```

2. **Verify Required Hardware**
   ```bash
   # WIT IMU must be connected
   ls /dev/ttyWIT
   
   # Or other serial port
   ls /dev/ttyUSB*
   ```

3. **Backup Current Installation**
   ```bash
   cp -r ~/.signalk/node_modules ~/.signalk/node_modules.backup
   ```

4. **Restore settings.json Entries**
   - Archive doesn't include your custom settings.json
   - Merge plugin entries manually
   - Or restore from your backup

### After Restoring

1. **Test Each Plugin**
   - Check Signal K Admin UI
   - Enable plugins if disabled
   - Verify data flow

2. **Review Configuration**
   - Update settings.json paths (lat/lon, station IDs, etc.)
   - Adjust calibration values if needed
   - Test hardware connections

3. **Monitor Logs**
   ```bash
   journalctl -u signalk -f
   ```

---

## 🚑 Emergency Recovery

### If Everything is Broken

```bash
# 1. Stop Signal K
sudo systemctl stop signalk

# 2. Clear everything
rm -rf ~/.signalk/node_modules/*

# 3. Restore archive
cp -r /home/aneto/.openclaw/workspace/plugins-stable-v0/* \
  ~/.signalk/node_modules/

# 4. Restart
sudo systemctl start signalk

# 5. Check status
sleep 10
curl http://localhost:3000/skServer/plugins
```

### If Just One Plugin is Broken

```bash
# 1. Identify broken plugin (check logs)
journalctl -u signalk | grep "cannot find\|require"

# 2. Restore from archive
cp -r plugins-stable-v0/[plugin-name]/ ~/.signalk/node_modules/

# 3. Restart Signal K
sudo systemctl restart signalk
```

---

## 📝 Maintenance

### Update Archive Periodically

When you make improvements or fix bugs:

```bash
# Update archive with latest working version
cp -r ~/.signalk/node_modules/signalk-NAME/ \
  plugins-stable-v0/

# Commit to git
git add plugins-stable-v0/
git commit -m "Update plugin archive - [description of changes]"
```

### Version Control

Keep archive in git for:
- ✅ Version history
- ✅ Rollback capability
- ✅ Easy sharing
- ✅ Change tracking

---

## 🎯 Archive Contents Detailed

### File Structure

```
plugins-stable-v0/
├── signalk-wit-imu-usb/
│   ├── index.js              (7.0 KB)
│   └── package.json          (600 B)
│
├── signalk-wave-height-imu/
│   ├── index.js              (9.9 KB)
│   ├── package.json          (401 B)
│   └── README.md             (9.3 KB)
│
├── signalk-astronomical/
│   ├── index.js
│   └── package.json
│
├── signalk-performance-polars/
│   ├── index.js              (9.4 KB)
│   └── package.json
│
├── signalk-sails-management-v2/
│   ├── index.js
│   └── package.json
│
├── signalk-loch-calibration/
│   ├── index.js
│   └── package.json
│
├── signalk-current-calculator/
│   ├── index.js
│   └── package.json
│
├── signalk-rpi-cpu-temp/
│   ├── index.js
│   └── package.json
│
└── j30-polars-data.json      (12 KB) ⚠️ CRITICAL
```

---

## ✅ Verification Stamp

**Archive verified:** 2026-04-23 15:26 EDT  
**All plugins operational:** ✅ YES  
**Critical data files present:** ✅ YES  
**Ready for production use:** ✅ YES

**Created by:** Automated backup system  
**MidnightRider J/30:** Ready for regatta! ⛵

---

**Use this archive for quick recovery, migration, or sharing.**  
**All plugins tested and production-ready.**  

🎉 **Bon vent!** 🌊⛵


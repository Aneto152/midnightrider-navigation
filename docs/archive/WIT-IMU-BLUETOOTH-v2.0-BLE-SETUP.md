# WIT IMU Bluetooth v2.0 - Setup & Configuration Guide

**Date Created:** 2026-04-23  
**Plugin Version:** 2.0.0-ble  
**Status:** ✅ **READY FOR TESTING**

---

## 🎯 Overview

**signalk-wit-imu-ble** is a Bluetooth Low Energy (BLE) version of the WIT IMU plugin.

- ✅ Same behavior as USB version
- ✅ No USB cable required
- ✅ Native Linux gatttool (no npm dependencies)
- ✅ Same 10 Hz data rate
- ✅ Identical data outputs and calibration
- ✅ Automatic reconnection on disconnect

---

## 📦 Installation

### Step 1: Plugin Already Installed

The plugin is already in:
```
~/.signalk/node_modules/signalk-wit-imu-ble/
```

Package structure verified:
- ✅ index.js (main plugin)
- ✅ package.json (metadata)
- ✅ No npm dependencies required

### Step 2: Verify Prerequisites

```bash
# Check gatttool installed
which gatttool
# Should output: /usr/bin/gatttool

# Check timeout command
which timeout
# Should output: /usr/bin/timeout

# If missing, install:
sudo apt-get install bluez
```

### Step 3: Find Your WIT Device

```bash
# 1. Ensure Bluetooth is on
sudo hciconfig hci0 up

# 2. Scan for BLE devices
sudo hciconfig hci0 reset
sudo hcitool lescan

# Look for your WIT device (WT901BLE68 or MAC E9:10:DB:8B:CE:C7)
```

---

## ⚙️ Configuration

### Basic Setup

Enable plugin in Signal K Admin UI:

1. Go to http://localhost:3000
2. Admin panel
3. Find "WIT IMU Bluetooth Reader"
4. Enable the plugin

### Configuration Parameters

**Required Settings:**

| Parameter | Default | Example | Notes |
|-----------|---------|---------|-------|
| **Bluetooth MAC Address** | E9:10:DB:8B:CE:C7 | E9:10:DB:8B:CE:C7 | Your WIT device MAC |
| **Bluetooth Device Name** | WT901BLE68 | WT901BLE68 | For reference |

**Optional Settings:**

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| Auto Reconnect | true | true/false | Reconnect on disconnect |
| Update Rate | 10 Hz | 0.1-100 | Data frequency |
| Filter Alpha | 0.05 | 0-1 | Smoothing factor |

**Calibration Offsets:**

All offsets identical to USB version:

```
Roll Offset:          ±180° (zero correction)
Pitch Offset:         ±180° (zero correction)
Yaw Offset:           ±180° (compass correction)
Accel X/Y/Z Offset:   ±20 m/s² (zero-point)
Gyro Z Offset:        ±0.5 rad/s (drift correction)
```

### Example Configuration

```json
{
  "signalk-wit-imu-ble": {
    "enabled": true,
    "bleAddress": "E9:10:DB:8B:CE:C7",
    "bleName": "WT901BLE68",
    "characteristicHandle": "0x0030",
    "autoReconnect": true,
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
```

---

## 🔍 Finding Your Characteristic Handle

The characteristic handle (default `0x0030`) is where WIT sends data.

### Method 1: Use gatttool

```bash
# Connect to device
gatttool -b E9:10:DB:8B:CE:C7 -I

# In gatttool prompt:
connect

# Discover characteristics
characteristics

# Look for:
# handle = 0x0030, char properties = 0x10, char value handle = 0x0031
# (0x10 = notify, 0x0031 = notification data)

# The value handle (0x0031) should be your characteristic
# Some systems use 0x0030 for writing enable, 0x0031 for notifications
```

### Method 2: Use hcitool

```bash
# Scan for device
hcitool -i hci0 lescan

# Once address known:
hcitool -i hci0 leinfo E9:10:DB:8B:CE:C7

# Then inspect with gatttool
gatttool -b E9:10:DB:8B:CE:C7 --characteristics
```

---

## 🚀 Testing

### Quick Test

```bash
# 1. Start Signal K
sudo systemctl start signalk

# 2. Check plugin loaded
curl http://localhost:3000/skServer/plugins | grep "wit-imu-ble"

# 3. Watch Signal K logs
journalctl -u signalk -f | grep -i "wit"

# 4. Check data flowing
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/
```

### Expected Output

```json
{
  "roll": 0.125,      // radians (-π to π)
  "pitch": -0.042,
  "yaw": 3.98,
  "source": {
    "label": "signalk-wit-imu-ble"
  }
}
```

### Test Data Flow

```bash
# Monitor acceleration data
watch -n 1 'curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/acceleration/ | jq'

# Monitor rate of turn
watch -n 1 'curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/rateOfTurn | jq'
```

---

## 🔧 Troubleshooting

### Plugin Doesn't Load

**Symptom:** "WIT IMU Bluetooth Reader" not in plugin list

```bash
# 1. Check file exists
ls -la ~/.signalk/node_modules/signalk-wit-imu-ble/

# 2. Check package.json valid
cat ~/.signalk/node_modules/signalk-wit-imu-ble/package.json

# 3. Check Signal K logs
journalctl -u signalk | grep "wit-imu-ble"
```

### Connection Failed

**Symptom:** "Connecting to WT901BLE68..." but never connects

```bash
# 1. Check Bluetooth service
sudo systemctl status bluetooth

# 2. Check device discoverable
gatttool -b E9:10:DB:8B:CE:C7 -I
# In prompt: connect
# Should show: [LE]> connect
# Attribute handle = 0x0001

# 3. Check MAC address
hcitool lescan
# Look for your device

# 4. Update MAC in config if needed
```

### No Data Flowing

**Symptom:** Plugin connected, but no updates in Signal K

```bash
# 1. Check notifications enabled
gatttool -b E9:10:DB:8B:CE:C7 -I
connect
char-write-req 0x0030 0100

# 2. Check Signal K logs for errors
journalctl -u signalk | grep "WIT"

# 3. Verify characteristic handle
characteristics
# Note the correct handle number
# Update in config: characteristicHandle

# 4. Test manually
gatttool -b E9:10:DB:8B:CE:C7 --char-read-uuid=ffe1
# Should return hex data
```

### Frequent Disconnects

**Symptom:** BLE connects but drops frequently

```bash
# 1. Check signal strength
hcitool -i hci0 rssi E9:10:DB:8B:CE:C7

# 2. Reduce update rate in config
# Try: "updateRate": 2

# 3. Check for interference
# Move away from WiFi, other BLE devices

# 4. Enable auto-reconnect
# "autoReconnect": true
```

---

## 📊 Behavior vs USB Version

### Identical:

✅ Data format (0x55 0x61 packets)  
✅ Output paths (attitude, acceleration, rate-of-turn)  
✅ Calibration parameters (7 offsets)  
✅ Update rate (10 Hz)  
✅ Packet decoding  
✅ Signal K integration  

### Different:

⚠️ Connection method (BLE vs Serial)  
⚠️ Configuration UI parameters (MAC vs USB port)  
⚠️ Underlying protocol (gatttool vs SerialPort)  

---

## 🔌 Running Both USB and BLE

You can run **both plugins simultaneously:**

```json
{
  "signalk-wit-imu-usb": {
    "enabled": true,
    "usbPort": "/dev/ttyWIT"
  },
  "signalk-wit-imu-ble": {
    "enabled": false,
    "bleAddress": "E9:10:DB:8B:CE:C7"
  }
}
```

Switch by disabling one, enabling the other.

---

## 📋 Complete Testing Checklist

- [ ] Bluetooth is enabled and working
- [ ] WIT device powers on
- [ ] MAC address verified (hcitool lescan)
- [ ] Plugin loads (Admin UI)
- [ ] "Connecting..." status appears
- [ ] Status changes to "Connected"
- [ ] Attitude data appears in API
- [ ] Acceleration data appears (if enabled)
- [ ] Rate of turn data appears (if enabled)
- [ ] Data updates at ~10 Hz
- [ ] Grafana shows real-time updates
- [ ] Manual disconnect/reconnect works

---

## 🎓 Technical Details

### gatttool Protocol

```bash
# gatttool flow:
gatttool -b MAC -I              # Start interactive mode
connect                         # Connect to device
char-write-req HANDLE 0100     # Enable notifications (CCCD)
# Device now sends notifications
# Each notification = one packet (20 bytes)
exit                            # Disconnect
```

### Packet Processing

```
BLE Notification (hex string)
  ↓ (parse hex string to bytes)
Buffer object
  ↓ (look for 0x55 0x61 header)
Valid WIT packet (20 bytes)
  ↓ (extract and convert values)
Attitude + Acceleration + Rate-of-Turn
  ↓ (apply calibration offsets)
Signal K deltas
  ↓ (send to app.handleMessage)
Signal K API
```

### Why Native gatttool?

- ✅ No npm dependencies (no compilation needed)
- ✅ Linux native (already installed)
- ✅ Simpler than noble (which requires node-gyp)
- ✅ Proven stable for Raspberry Pi
- ✅ Easy to debug (CLI available)

---

## 📝 Advanced: Custom Characteristic Handle

If your WIT device uses different handles:

```bash
# 1. Connect and discover
gatttool -b E9:10:DB:8B:CE:C7 -I

# 2. In gatttool:
connect
characteristics

# Output like:
# handle = 0x0001, char properties = 0x02
# handle = 0x0003, char properties = 0x02
# handle = 0x0008, char properties = 0x10, char value handle = 0x0009
# handle = 0x000b, char properties = 0x10, char value handle = 0x000c
# handle = 0x000e, char properties = 0x10, char value handle = 0x000f

# Find one with properties = 0x10 (notify)
# The "char value handle" is what you need

# Example: if handle = 0x000f, use:
# characteristicHandle: "0x000f"
```

---

## 🎯 Next Steps

1. **Test with USB disabled** (keep USB as backup)
2. **Verify 10 Hz data flow** (same as USB)
3. **Test sailing conditions** (real-world performance)
4. **Compare with USB** (should be identical)
5. **Switch to BLE if satisfied** (unplug USB for cleaner setup)

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Find WIT device | `hcitool lescan` |
| Check Bluetooth | `sudo hciconfig hci0` |
| Interactive test | `gatttool -b MAC -I` |
| View plugin logs | `journalctl -u signalk -f \| grep WIT` |
| Test API data | `curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/` |
| Check plugin list | `curl http://localhost:3000/skServer/plugins` |

---

**Status:** ✅ **READY TO TEST**

Both USB and BLE versions available side-by-side.
Switch easily via Signal K Admin UI configuration.

**Bon vent!** ⛵


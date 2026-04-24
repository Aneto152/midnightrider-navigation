# WIT IMU Bluetooth Activation

**Date:** 2026-04-23  
**Status:** ✅ **CONFIGURED FOR BLE MODE**

---

## 🔧 What Was Changed

### Before
- ❌ `signalk-wit-imu-usb`: ENABLED
- ❌ `signalk-wit-imu-ble`: DISABLED
- **Problem:** USB plugin was active, blocking BLE

### After
- ✅ `signalk-wit-imu-usb`: DISABLED
- ✅ `signalk-wit-imu-ble`: ENABLED
- **Benefit:** Now using Bluetooth, no USB cable needed

---

## 📋 Configuration Applied

**File:** `~/.signalk/settings.json`

```json
{
  "plugins": {
    "signalk-wit-imu-usb": {
      "enabled": false,  // Disabled
      "usbPort": "/dev/ttyWIT",
      "baudRate": 115200
    },
    "signalk-wit-imu-ble": {
      "enabled": true,   // ENABLED ✅
      "bleAddress": "E9:10:DB:8B:CE:C7",
      "bleName": "WT901BLE68",
      "autoReconnect": true,
      "updateRate": 10,
      "calibrationOffsets": {
        "rollOffset": 0,
        "pitchOffset": 0,
        "yawOffset": 0,
        "accelXOffset": -0.89,
        "accelYOffset": -0.35,
        "accelZOffset": 0.33,
        "gyroZOffset": 0
      }
    }
  }
}
```

---

## ✅ Expected Behavior

### Signal K Should Receive

```
navigation.attitude:
  - roll (heel angle)
  - pitch (trim angle)
  - yaw (heading)

navigation.acceleration:
  - x, y, z (3-axis acceleration)

navigation.rateOfTurn:
  - (Z-axis rotation rate)
```

### On iPad/Browser

```
http://midnightrider.local:3000
→ Attitude gauge should show real-time heel angle
```

---

## 🚨 Troubleshooting

### If No Data Received

#### 1. Check WIT is Powered On

```bash
# Visual check
# WIT LED should be BLUE (not off, not red)
# If charging: blue + red lights
```

#### 2. Check WIT is Paired

```bash
# View paired Bluetooth devices
bluetoothctl paired-devices

# Should see something like:
# Device E9:10:DB:8B:CE:C7 WT901BLE68
```

#### 3. If Not Paired - Pair Now

```bash
# Scan for WIT
bluetoothctl scan on
# Wait 5 seconds, look for: E9:10:DB:8B:CE:C7 WT901BLE68

# Pair it
bluetoothctl pair E9:10:DB:8B:CE:C7

# Trust it
bluetoothctl trust E9:10:DB:8B:CE:C7

# Connect it
bluetoothctl connect E9:10:DB:8B:CE:C7
```

#### 4. Check Signal K Logs

```bash
# Watch Signal K startup
journalctl -u signalk -f

# Look for:
# - "BLE scanning"
# - "Connected to WT901"
# - "Receiving attitude"

# If errors, check:
# journalctl -u signalk -n 50 | grep -i "error\|fail\|ble"
```

#### 5. Restart Signal K

```bash
sudo systemctl restart signalk
sleep 5

# Check status
systemctl status signalk | grep Active

# Check logs again
journalctl -u signalk -n 10
```

---

## 🔍 Verification Checklist

Before assuming it works:

- [ ] WIT powered on (blue LED visible)
- [ ] WIT paired in Bluetooth (`bluetoothctl paired-devices`)
- [ ] Signal K service running (`systemctl status signalk`)
- [ ] Attitude data available (`curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude`)
- [ ] Roll angle changes when tilting WIT
- [ ] Grafana shows heel gauge updating
- [ ] iPad dashboard shows real-time attitude

---

## 🔄 Switching Between USB and BLE

### To Use USB Instead (if needed)

```bash
# Edit settings.json
nano ~/.signalk/settings.json

# Change:
# "signalk-wit-imu-usb": { "enabled": true, ...
# "signalk-wit-imu-ble": { "enabled": false, ...

# Restart
sudo systemctl restart signalk
```

### To Use BLE (current)

```bash
# Change:
# "signalk-wit-imu-usb": { "enabled": false, ...
# "signalk-wit-imu-ble": { "enabled": true, ...

# Restart
sudo systemctl restart signalk
```

---

## 📊 Performance Notes

### BLE Advantages
- ✅ No USB cable needed (wireless)
- ✅ Cleaner installation
- ✅ Can place WIT anywhere in boat
- ✅ Same data quality as USB

### BLE Limitations
- ⚠️ Range: ~10 meters (adequate for small boat)
- ⚠️ Battery powered (must keep WIT charged)
- ⚠️ Auto-reconnect if connection drops

### Typical Battery Life
- WT901BLECL: ~48 hours continuous
- USB alternative if battery dies: Use USB mode

---

## 🎯 Current Status

| Aspect | Status |
|--------|--------|
| BLE Plugin | ✅ Installed |
| BLE Enabled | ✅ Yes |
| USB Plugin | ✅ Installed |
| USB Enabled | ❌ No (disabled to avoid conflict) |
| Signal K Version | 2.25 ✅ |
| MAC Address | E9:10:DB:8B:CE:C7 ✅ |

---

## 📝 Configuration File Location

```
~/.signalk/settings.json
~/.signalk/plugin-config-data/signalk-wit-imu-ble.json
```

---

## 🚀 Next Steps

1. **Power on WIT** (press button, blue LED should light)
2. **Wait for Signal K boot** (~40 seconds)
3. **Check for attitude data** (`curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude`)
4. **Verify in Grafana** (heel gauge should update)
5. **Test on iPad** (http://midnightrider.local:3000)

---

## 📞 If Still Not Working

Check:
1. WIT battery level (may be dead after switching)
2. Bluetooth pairing status
3. Signal K logs for error messages
4. RPi Bluetooth service status (`sudo systemctl status bluetooth`)

---

**Status:** ✅ **CONFIGURATION COMPLETE**  
**Ready for:** Bluetooth mode sailing  
**Fallback:** USB mode still available (just flip enabled flag)

⛵ WIT BLE is ready for navigation!

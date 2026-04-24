# WIT WT901BLE68 Bluetooth Pairing Guide

**Date:** 2026-04-23  
**Status:** In Progress - Device Detection Working

---

## ✅ What Was Done

1. **Bluetooth Service Activated**
   - ✅ `sudo systemctl enable bluetooth`
   - ✅ `sudo systemctl start bluetooth`
   - ✅ Bluetooth now ACTIVE on RPi

2. **Device Detection**
   - ✅ WIT was DETECTED via Bluetooth scan
   - ✅ MAC Address: E9:10:DB:8B:CE:C7
   - ✅ Device Name: WT901BLE68

3. **Plugin Configured**
   - ✅ WIT BLE plugin: ENABLED in Signal K
   - ✅ USB plugin: DISABLED (to avoid conflict)
   - ✅ autoReconnect: enabled

---

## ❓ Why Pairing Failed

**Error:** `Authentication Failed (0x05)`

**Reason:** WIT WT901BLE68 doesn't use traditional Bluetooth pairing with PIN. It requires:
- Direct connection (no PIN)
- Or automatic reconnection via plugin

**Solution:** Let the Signal K BLE plugin handle connection automatically

---

## 🔄 How to Make It Work

### Option 1: Manual Connection (if not auto-connecting)

```bash
# 1. Remove old pairing attempt
sudo bluetoothctl remove E9:10:DB:8B:CE:C7

# 2. Try direct connect (no pairing)
sudo bluetoothctl connect E9:10:DB:8B:CE:C7

# 3. Restart Signal K
sudo systemctl restart signalk
```

### Option 2: Let Plugin Handle It (Preferred)

The Signal K BLE plugin should auto-connect if:
- ✅ WIT is powered on
- ✅ WIT is in range (≤10m)
- ✅ autoReconnect: true (already configured)

**Just restart Signal K:**

```bash
sudo systemctl restart signalk
sleep 10
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

### Option 3: Use USB Instead (Fallback)

If BLE won't work:

```bash
# Edit settings.json
nano ~/.signalk/settings.json

# Change:
# "signalk-wit-imu-usb": { "enabled": true,
# "signalk-wit-imu-ble": { "enabled": false,

# Restart Signal K
sudo systemctl restart signalk
```

---

## 📋 Checklist Before Testing

- [ ] **WIT Power:** Is it ON? (blue LED visible, not blinking)
- [ ] **WIT Battery:** Is it charged? (charging = red + blue, charged = blue only)
- [ ] **Bluetooth RPi:** Is enabled? (`systemctl status bluetooth`)
- [ ] **Plugin:** BLE enabled? (check settings.json)
- [ ] **Range:** WIT within 10 meters of RPi?

---

## 🧪 Testing Steps

### 1. Power on WIT
```
Press button → LED should be BLUE (stable)
Wait 2 seconds
```

### 2. Scan for WIT
```bash
sudo bluetoothctl scan on
# Wait 5-10 seconds
# Look for: E9:10:DB:8B:CE:C7 WT901BLE68

# If you see it: ✅ WIT is broadcasting
# If not: ❌ WIT is off or out of range
```

### 3. Restart Signal K
```bash
sudo systemctl restart signalk
sleep 10
```

### 4. Check for Attitude Data
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# Should see: { "roll": ..., "pitch": ..., "yaw": ... }
# If empty: WIT not connected yet, try reconnecting
```

### 5. Monitor Logs
```bash
journalctl -u signalk -f

# Look for:
# - "BLE device detected"
# - "Connecting to WT901BLE68"
# - "Successfully connected"
# - Error messages if any
```

---

## 🔧 If Still Not Working

### Check Bluetooth Status
```bash
sudo bluetoothctl show
# Should show: Powered: yes, Discovering: yes/no
```

### Force Reconnect
```bash
sudo bluetoothctl disconnect E9:10:DB:8B:CE:C7
sudo bluetoothctl connect E9:10:DB:8B:CE:C7
```

### Restart Bluetooth Daemon
```bash
sudo systemctl restart bluetooth
sudo systemctl restart signalk
```

### Check Plugin Loading
```bash
curl http://localhost:3000/skServer/plugins | jq '.[] | select(.id | contains("wit")) | {id, enabled}'
```

---

## 📊 Current Status

| Item | Status |
|------|--------|
| Bluetooth Service | ✅ ACTIVE |
| Bluetooth at Boot | ✅ ENABLED |
| WIT Detection | ✅ FOUND (E9:10:DB:8B:CE:C7) |
| BLE Plugin | ✅ ENABLED |
| USB Plugin | ✅ DISABLED |
| autoReconnect | ✅ YES |
| Data Reception | ❓ PENDING (awaiting WIT connection) |

---

## 🎯 Next Actions

1. **Ensure WIT is fully charged**
   - Press button
   - LED should be BLUE (not blinking)

2. **Restart Signal K**
   ```bash
   sudo systemctl restart signalk
   ```

3. **Monitor logs**
   ```bash
   journalctl -u signalk -f
   ```

4. **Check data**
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
   ```

---

## 💡 Why BLE Is Better Than USB

- ✅ No cable needed
- ✅ Can place WIT anywhere on boat
- ✅ Same data quality
- ✅ Automatic reconnection
- ⚠️ Battery-powered (must keep charged)

---

## 🆘 Need USB Mode?

If BLE doesn't work and you need to sail:

```bash
# Switch to USB mode
nano ~/.signalk/settings.json

# Change both:
# "signalk-wit-imu-usb": { "enabled": true,
# "signalk-wit-imu-ble": { "enabled": false,

# Restart
sudo systemctl restart signalk
```

USB mode is always an option.

---

**Status:** BLE infrastructure ready, awaiting device connection

⛵ WIT Bluetooth should connect automatically once powered on and in range!

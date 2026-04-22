# USB Device Mapping Strategy — MidnightRider

**Date:** 2026-04-21 21:54 EDT  
**Status:** PLANNING → IMPLEMENTATION  

---

## 🎯 The Real Problem

Both GPS and IMU use **CH340 USB-to-Serial adapters** (vendor ID `1a86:7523`).

When connected, they could be on **any port** depending on **connection order**:
- First connected → `/dev/ttyUSB0`
- Second connected → `/dev/ttyUSB1`
- Or vice versa!

**Current situation (2026-04-21 21:54):**
```
/dev/ttyUSB0: WIT IMU (detected, connected via USB Type-C)
/dev/ttyUSB1: (not connected or not visible)
```

**Problem:** Signal K config hardcodes `/dev/ttyUSB0`, so it conflicts with WIT!

---

## ✅ Solution: Three-Layer Approach

### Layer 1: Device Detection Script
**Purpose:** Identify which device is on which port by **testing the data format**

```bash
# Test data patterns
cat /dev/ttyUSB0 | od -x | grep "5561"  # WIT pattern (0x55 0x61)
cat /dev/ttyUSB0 | head -c 100 | grep "^\$"  # GPS pattern (NMEA: $GNRMC, etc.)
```

### Layer 2: Persistent Udev Rules
**Purpose:** Create symlinks `/dev/ttyMidnightRider_GPS` and `/dev/ttyMidnightRider_IMU`

```
# 99-midnightrider-usb.rules
SUBSYSTEMS=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", \
  ATTRS{serial}=="GPS_SERIAL_HERE", SYMLINK+="ttyMidnightRider_GPS"

SUBSYSTEMS=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", \
  ATTRS{serial}=="IMU_SERIAL_HERE", SYMLINK+="ttyMidnightRider_IMU"
```

**Challenge:** Both devices might have same vendor/product ID
**Solution:** Use **DEVPATH** (USB hub port) which is stable:

```
# Map by physical port connection
SUBSYSTEMS=="usb", DEVPATH=="*/1-1.3/*", SYMLINK+="ttyMidnightRider_GPS"    # USB hub port 3 = GPS
SUBSYSTEMS=="usb", DEVPATH=="*/1-1.4/*", SYMLINK+="ttyMidnightRider_IMU"    # USB hub port 4 = IMU
```

### Layer 3: Service Configuration
**Update Signal K & WIT configs to use symlinks**

```json
// Signal K (settings.json)
{
  "providers": [
    {
      "id": "signalk-core-NMEA-0183",
      "options": {
        "device": "/dev/ttyMidnightRider_GPS"  // Use symlink
      }
    }
  ]
}
```

```bash
# WIT service
ExecStart=/usr/bin/python3 /home/aneto/wit-ble-reader.py --port /dev/ttyMidnightRider_IMU
```

---

## 📋 Implementation Steps

### Step 1: Get Serial Numbers (if available)
```bash
lsusb -v | grep -A2 "iSerial"
udevadm info -q all /dev/ttyUSB0 | grep SERIAL
```

### Step 2: Create Udev Rules
```bash
sudo nano /etc/udev/rules.d/99-midnightrider-usb.rules

# Add rules based on DEVPATH or serial
# Reload: sudo udevadm control --reload
#         sudo udevadm trigger
```

### Step 3: Verify Symlinks
```bash
ls -la /dev/ttyMidnightRider_*
# Should show:
#   /dev/ttyMidnightRider_GPS -> ttyUSB0
#   /dev/ttyMidnightRider_IMU -> ttyUSB1
```

### Step 4: Update Configs
- Signal K: `/home/aneto/.signalk/settings.json` → point to `/dev/ttyMidnightRider_GPS`
- WIT service: `wit-ble-reader.py` → point to `/dev/ttyMidnightRider_IMU`

### Step 5: Test
```bash
sudo systemctl restart signalk wit-sensor
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/position
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

---

## 🔍 Current State Analysis

**What we know (2026-04-21):**
```
$ lsof /dev/ttyUSB0
COMMAND  PID  USER FD   TYPE DEVICE SIZE/OFF NODE NAME
python3 8689 aneto  3u   CHR  188,0      0t0  569 /dev/ttyUSB0  ← WIT
node    8900 aneto 27uW  CHR  188,0      0t0  569 /dev/ttyUSB0  ← Signal K

$ udevadm info /dev/ttyUSB0
DEVPATH=/devices/.../1-1.4/1-1.4:1.0/ttyUSB0
ID_SERIAL=1a86_USB_Serial  ← Generic, both devices have same!
```

**Interpretation:**
- Only ONE port visible: `/dev/ttyUSB0`
- It's the WIT (most recently connected)
- GPS might be:
  - Not connected right now
  - On a different connection type (Ethernet? NMEA0183 direct?)
  - Not visible in lsusb

---

## 🚀 Next Actions

### Option A: Use Symlinks by DEVPATH (Recommended)
1. Connect GPS to **port 1-1.3** of USB hub
2. Connect IMU to **port 1-1.4** of USB hub
3. Create udev rules mapping:
   ```
   DEVPATH=="*/1-1.3/*" → /dev/ttyMidnightRider_GPS
   DEVPATH=="*/1-1.4/*" → /dev/ttyMidnightRider_IMU
   ```
4. No manual port selection ever needed again!

### Option B: Use Serial Numbers (If available)
1. Get serial numbers: `lsusb -v | grep iSerial`
2. Create udev rules based on serial:
   ```
   ATTRS{serial}=="ABC123", SYMLINK+="ttyMidnightRider_GPS"
   ATTRS{serial}=="XYZ789", SYMLINK+="ttyMidnightRider_IMU"
   ```

### Option C: Simple Port Assignment (Temporary)
1. Configure GPS on `/dev/ttyUSB0`
2. Configure IMU on `/dev/ttyUSB1`
3. Always connect in same order
4. ⚠️ Fragile if cables reversed!

---

## 📝 Decision for Denis

**Which approach do you prefer?**

- **Option A (DEVPATH):** Most robust, but requires knowing USB hub port numbers
- **Option B (Serial):** Very clean, but requires serial numbers
- **Option C (Order):** Simple, but error-prone

---

## 💡 Why Kflex Would Have Helped

Kflex (Kayak Flexible Configuration) is designed exactly for this:
- Detects devices by data patterns
- Creates persistent mappings
- Handles dynamic USB port changes
- Provides web UI for configuration

Without Kflex, we need to:
1. **Manually identify devices** (what data they send)
2. **Create udev rules** (persistent mappings)
3. **Update configs** (point to correct ports)

---

## ⏭️ Immediate Next Step

Can you clarify:
1. **Is the GPS (UM982) currently connected?**
   - If yes: Which port?
   - If no: When will it be connected?

2. **Do you want to set up persistent mappings now, or test with manual assignment first?**

Once answered, I can implement the final solution! 🎯

---

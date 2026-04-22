# udev Alias for WIT IMU - /dev/ttyWIT

**Date:** 2026-04-22 13:42 EDT  
**Status:** ✅ Installed & Active  
**Purpose:** Stable device reference independent of USB enumeration

---

## Problem Solved

Previously:
- WIT USB device = `/dev/ttyUSB0` (can change!)
- If USB reorders: might become `/dev/ttyUSB1`, `/dev/ttyUSB2`, etc.
- Kplex config hardcoded `/dev/ttyUSB0` → breaks if order changes

**Solution:**
- Create udev SYMLINK: `/dev/ttyWIT` → `/dev/ttyUSB0`
- Kplex & Signal K reference `/dev/ttyWIT` (stable!)
- Even if USB order changes, `/dev/ttyWIT` always points to WIT

---

## Implementation

### udev Rule

**File:** `/etc/udev/rules.d/99-wit-imu.rules`

```ini
# CH340 Serial Converter (WIT WT901BLECL IMU)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="ttyWIT"

# Fallback if above doesn't match
SUBSYSTEM=="tty", ATTRS{product}=="USB2.0-Serial", SYMLINK+="ttyWIT"
```

**How it works:**
1. udev detects USB device with vendor ID `1a86` (CH340)
2. Creates symlink `/dev/ttyWIT` pointing to `/dev/ttyUSB0`
3. If USB reorders, `/dev/ttyWIT` still points to correct device

### Verification

```bash
$ ls -la /dev/ttyWIT*
lrwxrwxrwx 1 root root 7 Apr 22 13:42 /dev/ttyWIT -> ttyUSB0

$ readlink /dev/ttyWIT
ttyUSB0
```

✅ Alias is active and working

---

## Kplex Update

**File:** `/etc/kplex/kplex.conf`

Changed from:
```ini
[serial]
filename=/dev/ttyUSB0
```

To:
```ini
[serial]
filename=/dev/ttyWIT
```

**Benefit:** Kplex now uses stable reference

---

## Signal K Integration (Future)

When Signal K needs to read WIT directly (fallback scenario):

```json
{
  "signalk-wit-imu": {
    "usbPort": "/dev/ttyWIT",
    "baudRate": 115200
  }
}
```

Instead of `/dev/ttyUSB0`

---

## Advantages

| Aspect | Before | After |
|--------|--------|-------|
| **Device Reference** | `/dev/ttyUSB0` (changes!) | `/dev/ttyWIT` (stable!) |
| **USB Reorder Handling** | Breaks | Works automatically |
| **Multiple USB Devices** | Conflicts | Each has own alias |
| **Config Portability** | Device-specific | Works on any RPi |
| **Human Readability** | Generic | Descriptive (`ttyWIT`) |

---

## How It Works (Technical)

### USB Device Detection
```
Hardware: CH340 (vendor 1a86, product 7523)
    ↓
Kernel udev subsystem
    ↓
Rule matches → SYMLINK+="ttyWIT"
    ↓
/dev/ttyWIT created (points to kernel device)
    ↓
Applications use /dev/ttyWIT
```

### Dynamic Mapping
- If `/dev/ttyUSB0` → `/dev/ttyUSB1` (due to cable plug order)
- udev detects CH340 again
- Updates `/dev/ttyWIT` → `/dev/ttyUSB1`
- Applications see no change (still `/dev/ttyWIT`)

---

## Testing

Verify the alias works:

```bash
# 1. Check symlink exists
ls -la /dev/ttyWIT

# 2. Test reading from alias
timeout 2 cat /dev/ttyWIT | od -x | head -3

# 3. Verify Kplex can use it
/usr/bin/kplex -f /etc/kplex/kplex.conf
```

---

## If Alias Doesn't Show

### Troubleshooting

```bash
# 1. Check if udev rule exists
ls -la /etc/udev/rules.d/99-wit-imu.rules

# 2. Check rule syntax
udevadm test /sys/bus/usb-serial/drivers/ch341/1-1:1.0

# 3. Reload and trigger
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo udevadm monitor  # Watch for events

# 4. Check USB device details
lsusb | grep 1a86
dmesg | grep -i ch340
```

### Manual Creation (if udev fails)

```bash
# Temporary (until next boot)
sudo ln -s ttyUSB0 /dev/ttyWIT

# Permanent approach: add to /etc/udev/rules.d/
```

---

## Benefits for Reboot

When system reboots:

1. **Kplex starts** → reads `/dev/ttyWIT`
2. udev automatically creates alias
3. Kplex connects successfully
4. No hardcoded `/dev/ttyUSB0` dependency
5. Works even if USB enumeration changes

---

## Summary

| Component | Improvement |
|-----------|------------|
| **Kplex** | Uses `/dev/ttyWIT` (stable) |
| **Signal K** | Can use `/dev/ttyWIT` if fallback needed |
| **Portability** | Works on any RPi with CH340 USB |
| **Robustness** | Immune to USB enumeration order |

---

**Status:** ✅ READY FOR REBOOT

The udev alias will persist across reboots automatically!

⛵


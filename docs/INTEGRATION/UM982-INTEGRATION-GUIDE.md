# UM982 GPS INTEGRATION GUIDE

**Objective:** Configure UM982 GPS to feed position and heading into Signal K  
**Time:** ~30 min  
**Difficulty:** Medium

---

## PHYSICAL SETUP

### Antenna Installation

**Spacing:** 20cm apart (critical for dual-antenna heading)  
**Alignment:** Perpendicular to boat axis (port/starboard)  
**Clearance:** No metal, sailcloth, or rigging nearby (interferes with signal)  
**Height:** Masthead or cabin top (clear view of sky)

### Serial Connection

```bash
# USB cable to RPi4 (USB 2.0 or 3.0 port)
# Speed: 115200 baud (auto-configured by plugin)
# Check device:
ls -la /dev/ttyUSB*

# Should show something like:
# /dev/ttyUSB0 (UM982)
```

---

## SIGNAL K PLUGIN CONFIGURATION

### Install Plugin (if not already)

```bash
cd ~/.signalk/node_modules
npm install @tkurki/um982
```

### Enable in settings.json

```json
{
  "plugins": {
    "@tkurki/um982": {
      "enabled": true,
      "port": "/dev/ttyUSB0",
      "baudrate": 115200,
      "allowUpdate": true
    }
  }
}
```

### Restart Signal K

```bash
sudo systemctl restart signalk
```

---

## VERIFICATION

```bash
# Check Signal K paths
curl -s http://localhost:3000/signalk/v1/api/vessels/self | jq '{
  position: .navigation.position,
  heading: .navigation.headingTrue,
  sog: .navigation.speedOverGround,
  cog: .navigation.courseOverGround
}'
```

**Expected output:**
```json
{
  "position": {"latitude": 41.1720, "longitude": -71.5509},
  "heading": 3.98,           // radians (228°)
  "sog": 2.5,                // m/s (~5 knots)
  "cog": 4.10                // radians
}
```

---

## ANTENNA OFFSET (TO VERIFY)

**Current status:** [À VÉRIFIER]

If boat has special antenna mounting:
```json
{
  "plugins": {
    "@tkurki/um982": {
      "antennaOffset": 1.57        // Add ±π/2 if needed (in radians)
    }
  }
}
```

**How to test:**
1. Point boat directly north (compass + visual)
2. Check heading in Signal K
3. Should read ~0° (or 360°)
4. If reads 90° or 270°, antenna offset needed

---

## COLD START TIMING

**First boot:** May take 30-60 sec to acquire GPS lock  
**Subsequent boots:** 10-30 sec  
**Data quality:** Check for satellites (need ≥4 for accuracy)

---

## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| No /dev/ttyUSB0 | Check USB cable, restart RPi, try different port |
| Heading reads 0° | Wait cold start (30 sec), check antenna alignment |
| Position stale | Verify GPS lock via `gpsmon` if available |
| Data drops | Check Signal K logs: `journalctl -u signalk` |

---

**Status:** ✅ Operational  
**Last Updated:** 2026-04-25

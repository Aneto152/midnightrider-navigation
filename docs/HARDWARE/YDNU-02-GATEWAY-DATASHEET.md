# YACHT DEVICES YDNU-02 — NMEA 2000 GATEWAY DATASHEET

**Manufacturer:** Yacht Devices (Russian, professional marine)  
**Model:** YDNU-02 (Dual-interface gateway)  
**Interface:** USB ↔ NMEA 2000 (bidirectional)  
**Date:** 2026-04-25

---

## SPECIFICATIONS

| Spec | Value |
|------|-------|
| **USB Interface** | USB 2.0 Full-Speed |
| **NMEA 2000** | Micro-C connector (standard) |
| **Data Rate** | 250 kbps (NMEA 2000 standard) |
| **Power** | USB-powered + 12V option |
| **Direction** | Bidirectional (read/write) |
| **Supported PGNs** | All standard NMEA 2000 PGNs |
| **LED Indicators** | Power (green), Activity (yellow) |
| **Size** | 90 × 60 × 30 mm |
| **Temperature** | -10°C to +50°C |
| **IP Rating** | IP67 (sealed) |

---

## FUNCTION IN MIDNIGHT RIDER

Acts as **bridge** between Signal K (on RPi) and NMEA 2000 bus (on boat):

```
Signal K Hub (port 3000, RPi4)
        ↓ (USB)
   YDNU-02 Gateway
        ↓ (NMEA 2000 Micro-C)
   NMEA 2000 Backbone
        ↓
   Vulcan 7 FS MFD
   + Loch instruments
   + AIS transponder
   + Other N2K devices
```

---

## SIGNAL K PLUGIN

**Plugin:** `signalk-to-nmea2000` (built-in Signal K)  
**Status:** ✅ Operational

**PGNs Sent (Signal K → NMEA 2000):**
- 127250 (Vessel Heading)
- 127251 (Rate of Turn)
- 127257 (Attitude)
- 129025 (GNSS Position Rapid)
- 129026 (COG & SOG)
- 130306 (Wind Data) — if available
- 130312 (Temperature) — if available

**PGNs Received (NMEA 2000 → Signal K):**
- All PGNs from connected instruments
- Loch (STW, depth, temp)
- AIS transponder (target data)
- Baromete (pressure)

---

## MOUNTING & SETUP

### Physical Installation
1. **Mount near RPi4** (short USB cable, ~0.5m)
2. **Connect NMEA 2000:** Micro-C to existing N2K backbone
3. **Power:** USB from RPi (self-powered) OR separate 12V supply
4. **LED check:** Green (power) solid, yellow (activity) blinking

### Software Configuration
1. Signal K auto-detects YDNU-02
2. Add to `/etc/udev/rules.d/` (optional, for consistent device name)
3. Configure in Signal K settings.json:
```json
{
  "plugins": {
    "signalk-to-nmea2000": {
      "enabled": true,
      "interface": "/dev/ttyUSB0"
    }
  }
}
```

---

## PRE-RACE VERIFICATION

```bash
# Check USB device
lsusb | grep -i yacht

# Check Signal K sees it
curl http://localhost:3000/skServer/interfaces

# Monitor NMEA 2000 traffic (if analyzer available)
candump can0  # (requires CANdump tool + SocketCAN)

# Check Vulcan receives data
# (Manual: look at Vulcan display for position/heading/attitude)
```

---

## KNOWN ISSUES & FIXES

| Issue | Fix |
|-------|-----|
| Device not recognized | Restart RPi USB hub: `sudo usb_reset` |
| PGNs not transmitting | Verify Signal K plugin enabled in settings.json |
| Vulcan no data | Check NMEA 2000 network (shorts in connector?) |
| LED not blinking | Check USB power + NMEA 2000 connection |

---

## CRITICAL NOTES

⚠️ **Direction:** YDNU-02 is BIDIRECTIONAL (both read and write). Configure carefully to avoid conflicts if other devices on NMEA 2000 send same PGNs.

⚠️ **Power:** In racing, ensure stable 12V supply (LiFePO4 battery is ideal). USB power may be insufficient under heavy load.

---

## RACING ADVANTAGES

✅ **Bidirectional:** Can send Signal K data TO other instruments (not just receive)  
✅ **Professional:** Used on commercial vessels, very reliable  
✅ **Standard NMEA 2000:** Fully compatible with all N2K devices  
✅ **No proprietary:** Works with B&G, Simrad, Garmin, etc.  

---

**STATUS:** ✅ Operational  
**Last Updated:** 2026-04-25  
**Critical for Race:** YES (essential bridge)

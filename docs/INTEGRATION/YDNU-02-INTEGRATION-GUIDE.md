# YDNU-02 GATEWAY INTEGRATION GUIDE

**Objective:** Configure YDNU-02 as bidirectional NMEA 2000 ↔ Signal K bridge  
**Time:** ~20 min  
**Difficulty:** Low

---

## PHYSICAL SETUP

### USB Connection

```bash
# Short USB cable to RPi (≤0.5m)
# Check device:
lsusb | grep -i yacht
# Should show: Yacht Devices YDNU-02

# Check device file:
ls -la /dev/ttyACM*
# Likely /dev/ttyACM0
```

### NMEA 2000 Connection

1. Micro-C connector to existing NMEA 2000 backbone
2. Ensure secure fit (torque properly)
3. Verify no corrosion on connector
4. Power: USB-powered (self-powered) OR separate 12V supply

### LED Indicators

- **Green (Power):** Should be solid on
- **Yellow (Activity):** Should blink every 1-2 sec (when data flowing)

---

## SIGNAL K PLUGIN CONFIGURATION

### Built-in Plugin

Signal K includes `signalk-to-nmea2000` by default.

### Enable in settings.json

```json
{
  "plugins": {
    "signalk-to-nmea2000": {
      "enabled": true,
      "interface": "/dev/ttyACM0",
      "baudrate": 250000,
      "sendPGNs": [
        127250,    // Vessel Heading
        127257,    // Attitude
        129025,    // GNSS Position
        129026,    // COG & SOG
        130306     // Wind (optional)
      ]
    }
  }
}
```

### Restart Signal K

```bash
sudo systemctl restart signalk
```

---

## VERIFY DATA FLOW

### Transmit (Signal K → NMEA 2000)

```bash
# Check plugin active
curl http://localhost:3000/skServer/plugins | jq '.[] | select(.id | contains("nmea2000"))'

# Should show: "running": true
```

### Receive (NMEA 2000 → Signal K)

YDNU-02 can also RECEIVE from other NMEA 2000 devices (loch, AIS transponder, etc.):

```bash
# If loch connected, should appear as:
curl -s http://localhost:3000/signalk/v1/api/vessels/self | jq '.navigation.speedThroughWater'

# Or:
curl -s http://localhost:3000/signalk/v1/api/vessels/self | jq '.environment.water.depth'
```

---

## PGNs (System-Level Flow)

> **📌 SSOT:** For complete PGN flow diagram and specifications:
> - Network system view: [`docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md`](N2K-NETWORK-ARCHITECTURE.md)
> - Per-device specs: [`docs/HARDWARE/YDNU-02-DATASHEET.md`](../HARDWARE/YDNU-02-DATASHEET.md)

The YDNU-02 acts as a transparent bridge — it receives N2K frames from the bus
and relays them to Signal K, and receives Signal K deltas and transmits them as N2K PGNs.


## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| Device not found | Check USB cable, restart RPi |
| Yellow LED not blinking | Check NMEA 2000 network connection |
| Vulcan sees no data | Restart YDNU-02 USB (unplug 5 sec, replug) |
| PGN conflicts | Check settings.json filters (may be dropping PGNs) |

---

## RACING DEPLOYMENT

**During race:**
- YDNU-02 transmits live data to Vulcan MFD
- Crew sees position, heading, attitude in real-time
- No manual configuration needed (plug & play)

---

**Status:** ✅ Critical component  
**Last Updated:** 2026-04-25

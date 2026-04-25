# VULCAN 7 FS ↔ SIGNAL K INTEGRATION GUIDE

**Objective:** Configure Vulcan to receive real-time data from Signal K via YDNU-02 gateway  
**Time Required:** ~30-45 minutes  
**Difficulty:** Medium

---

## ARCHITECTURE

```
Signal K Hub (RPi4, port 3000)
    ↓ (HTTP POST to signalk-to-nmea2000 plugin)
PGN Messages (127257, 127250, 129025, etc.)
    ↓ (USB)
YDNU-02 Gateway
    ↓ (NMEA 2000 Micro-C)
NMEA 2000 Network
    ↓
Vulcan 7 FS MFD (Display)
```

---

## STEP 1: VERIFY YDNU-02 CONNECTION

```bash
# Check USB device visible
lsusb | grep -i yacht

# Verify Signal K plugin active
curl http://localhost:3000/skServer/plugins | jq '.[] | select(.id | contains("nmea2000")) | {id, running}'

# Should output:
# {
#   "id": "signalk-to-nmea2000",
#   "running": true
# }
```

**Expected:** Device shows up, plugin is running.

---

## STEP 2: VULCAN — INITIAL SETUP

### Power On
1. Power Vulcan 7 FS from 12V battery
2. Wait for boot (~30 sec)
3. Accept any setup wizard (or skip)

### Network Configuration
1. **Settings → Network → Device List**
2. Should auto-detect YDNU-02
3. If not visible:
   - Restart YDNU-02 USB
   - Restart Vulcan (power off 10 sec, back on)
   - Check NMEA 2000 connector (loose?)

---

## STEP 3: ENABLE PGN RECEPTION

In Vulcan **Settings → NMEA 2000 Input:**

| PGN | Name | Enable | Purpose |
|-----|------|--------|---------|
| 127250 | Vessel Heading | ✅ YES | True heading from UM982 |
| 127251 | Rate of Turn | ⏸ Optional | Not critical for racing |
| 127257 | Attitude | ✅ YES | Roll/pitch/yaw from WIT v1.1 |
| 129025 | GNSS Position Rapid | ✅ YES | Position from UM982 |
| 129026 | COG & SOG | ✅ YES | Speed/course from UM982 |
| 130306 | Wind Data | ⏸ Optional | If Calypso working |
| 130312 | Temperature | ⏸ Optional | Not critical |

---

## STEP 4: SOURCE SELECTION (CRITICAL)

**Settings → Advanced → Source Selection:**

Set **Primary Sources:**
```
Heading:     Signal K (UM982)    ← NOT magnetic compass
Position:    Signal K (UM982)    ← NOT loran
Attitude:    Signal K (WIT)      ← From IMU
Speed STW:   Loch (when available)
Speed SOG:   Signal K (GPS)
```

**Why:**
- GPS-derived heading is more accurate for racing (independent of magnetic variation)
- WIT IMU provides real heel angle (critical for Sails Management v2)
- Dual-source strategy: if one fails, Vulcan falls back automatically

---

## STEP 5: VERIFY DATA FLOW

### On Vulcan Display
1. Open **Navigation** page
2. Check for live data:
   - Position: should show lat/lon (updating every 1 sec)
   - Heading: should show degrees (0-360)
   - Speed: should show knots
   - Depth: N/A (not connected)

3. Open **Attitude** page (if available)
   - Roll: should show ~0° at rest
   - Pitch: should show ~0° at rest

### Via Signal K API

```bash
# Check what Vulcan is receiving
curl -s http://localhost:3000/signalk/v1/api/vessels/self | jq '{
  position: .navigation.position,
  heading: .navigation.headingTrue,
  attitude: .navigation.attitude,
  sog: .navigation.speedOverGround
}'
```

**Expected:** All values present, updating in real-time.

---

## STEP 6: VULCAN RACING CONFIGURATION

### Dashboard Setup
1. **Home screen:** Add gauges for:
   - True Heading
   - Position (lat/lon)
   - Speed Over Ground
   - Attitude (Roll)
   - Wind (if available)

2. **Race screen:** Add gauges for:
   - VMG (Velocity Made Good)
   - Heel angle
   - Wave height (if available)
   - Time to mark

### Alarms

**Settings → Alarms:**
- Heel > 22°: Set alarm (visual + audible)
- Wave Hs > 2.5m: Set alarm
- Speed < 2 kts: Warning (bad weather or equipment failure)

---

## PRE-RACE VERIFICATION

```bash
# 1. Verify PGNs transmitting from Signal K
curl http://localhost:3000/skServer/interfaces | jq '.[] | select(.id | contains("nmea2000"))'

# 2. Check Vulcan sees data (visual inspection of display)
# Should show: heading, position, speed all live and updating

# 3. Test with known waypoint
# Set go-to-waypoint, verify distance decreases as you sail
```

---

## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| Vulcan shows "YDNU-02 offline" | Restart YDNU-02 USB + power cycle Vulcan |
| Heading reads 0° constantly | Check UM982 GPS lock (may need 1-2 min) |
| Position jumps wildly | Wait for GPS cold start (may take 30+ sec) |
| Attitude blank | Verify WIT IMU charging + BLE connected |
| Data freezes mid-race | Restart Signal K: `systemctl restart signalk` |

---

## RACING USAGE

**During Race:**
- Glance at Vulcan for heading/position/heel
- Use iPad Grafana for detailed analysis (VMG, wave height, trends)
- Trust your crew's sail trim more than the numbers

**Critical Data to Monitor:**
- Heel: >22° = consider reefing
- Wave Hs: >2.5m + building = reduce sail area
- VMG: <50% optimal = adjust trim or course

---

**Status:** ✅ Ready for race  
**Last Updated:** 2026-04-25

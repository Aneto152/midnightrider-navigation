# Signal K → NMEA 2000 Bridge — Integration Guide

**Plugin**: signalk-to-nmea2000  
**Plugin ID (SK internal)**: `sk-to-nmea2000`  
**Version installed**: 2.24.0  
**Status**: ✅ **ENABLED** — 7 active conversions  
**Last verified**: 2026-07-20  

> 📁 **Reference code in Git**: `plugins/sk-to-nmea2000-reference/`  
> 📋 **Active config in Git**: `config/signalk-plugins/sk-to-nmea2000-config.json`

---

## 1. Architecture

```
Signal K data store (REST API :3000)
 │
 ▼
sk-to-nmea2000 plugin (npm @signalk/signalk-to-nmea2000 v2.24.0)
~/.signalk/node_modules/signalk-to-nmea2000/
 ├── index.js ← loads all conversions/*.js at startup
 └── conversions/ (28 modules, 7 enabled)
     ├── trueheading.js ← ACTIVE: headingTrue → PGN 127250 (True)
     ├── wind.js ← ACTIVE: apparent wind → PGN 130306 (Apparent)
     ├── windTrueGround.js ← ACTIVE: true wind ground → PGN 130306 (True-0)
     ├── windTrueWater.js ← ACTIVE: true wind water → PGN 130306 (True-1)
     ├── attitude.js ← ACTIVE: roll/pitch/yaw → PGN 127257
     ├── leeway.js ← ACTIVE: leeway angle → PGN 128000
     ├── setdrift.js ← ACTIVE: set/drift → PGN 129291
     ├── heading.js ← DISABLED (HEADINGv2 option not enabled)
     └── [20 other modules — environmental, engine, etc. — disabled]
 │
YDNU-02 (USB /dev/ttyACM0, 250 kbps)
 │
N2K Backbone (NMEA 2000 bus)
 │
Vulcan 7 FS (×2 chart plotters) + other N2K devices

```

---

## 2. Active Conversions — Detailed

| optionKey | File | SK Input | PGN | N2K Field | Status |
|-----------|------|----------|-----|-----------|--------|
| **TRUE_HEADING** | trueheading.js | `navigation.headingTrue` | 127250 | Heading (rad); Reference=True | ✅ Active |
| **WINDv2** | wind.js | `angleApparent` + `speedApparent` | 130306 | Angle+Speed; Reference=Apparent | ✅ Active |
| **WIND_TRUE_GROUND** | windTrueGround.js | `directionTrue` + `speedOverGround` | 130306 | Angle+Speed; Reference=True (0) | ✅ Active |
| **WIND_TRUE** | windTrueWater.js | `directionTrue` + `speedTrue` | 130306 | Angle+Speed; Reference=True (1) | ✅ Active |
| **ATTITUDE** | attitude.js | `attitude.roll/pitch/yaw` | 127257 | Yaw/Roll/Pitch | ✅ Active |
| **LEEWAY** | leeway.js | `performance.leeway` | 128000 | Leeway angle | ✅ Active |
| **SetDrift** | setdrift.js | `current.setTrue` + `drift` | 129291 | Set+Drift (ref=True) | ✅ Active |
| HEADINGv2 | heading.js | `headingMagnetic` + `magneticVariation` | 127250 | Heading (mag); Reference=Magnetic | ❌ Disabled |

---

## 3. Heading Data Flow (Critical Path)

```
WIT WT901BLECL (BLE, via signalk-wit-imu-ble plugin)
 └─→ navigation.headingMagnetic (rad)

Vulcan 7 FS internal GPS (via N2K PGN 127258 parser)
 └─→ navigation.magneticVariation (rad)

signalk-heading-true-calculator (plugin P1)
 └─→ navigation.headingTrue = headingMagnetic + magneticVariation (rad)

sk-to-nmea2000 plugin → TRUE_HEADING conversion
 └─→ PGN 127250:
     - Heading: headingTrue (in radians)
     - Reference: "True"
     - Variation: undefined (already baked into headingTrue)

YDNU-02 gateway (USB /dev/ttyACM0)
 └─→ N2K bus (CAN 250 kbps)

Vulcan 7 FS receives PGN 127250
 └─→ Displays as true heading (T)
```

### Why TRUE_HEADING not HEADINGv2?

- **TRUE_HEADING**: Sends pre-calculated `headingTrue` (variation already applied)
  - Source: signalk-heading-true-calculator
  - Vulcan 7 FS gets ready-to-use true heading
  - Simpler pipeline, fewer conversions

- **HEADINGv2** (disabled): Would send `headingMagnetic` + `magneticVariation` separately
  - Vulcan 7 FS would apply variation correction itself
  - Only useful if chartplotter wants raw components
  - Not needed here (variation already in headingTrue)

---

## 4. Wind Data Flow (3 Simultaneous PGN 130306 Emissions)

```
Calypso UP10 (BLE → UDP)
 └─→ environment.wind.angleApparent (rad)
 └─→ environment.wind.speedApparent (m/s)

WS320 N2K Base Station
 └─→ environment.wind.angleApparent (direct N2K PGN 130306)
 └─→ Direct: Vulcan 7 FS (lower latency)

signalk-truewind-calculator (plugin, v1.0.4)
 └─→ environment.wind.directionTrue (rad)
 └─→ environment.wind.speedOverGround (m/s)
 └─→ environment.wind.speedTrue (m/s, if STW available)

sk-to-nmea2000 → THREE parallel PGN 130306 emissions:

1) WINDv2 (Apparent)
   Input:  angleApparent, speedApparent (from Calypso)
   Output: PGN 130306 with Reference=Apparent (2)
   Vulcan sees apparent wind in real-time

2) WIND_TRUE_GROUND (True over ground)
   Input:  directionTrue, speedOverGround
   Output: PGN 130306 with Reference=True-Ground (0)
   Vulcan sees true wind over ground (includes current effect)

3) WIND_TRUE (True relative to water, if STW available)
   Input:  directionTrue, speedTrue (from truewind calculator)
   Output: PGN 130306 with Reference=True-Water (1)
   Vulcan sees true wind relative to boat's movement through water

```

### Which Does Vulcan 7 FS Use?

The chartplotter displays whichever PGN 130306 Reference code matches its configuration:
- **Reference=Apparent (2)**: Displays apparent wind (from WS320 or WINDv2)
- **Reference=True-Ground (0)**: Displays true wind over ground (from WIND_TRUE_GROUND)
- **Reference=True-Water (1)**: Displays true wind relative to water (from WIND_TRUE, if available)

All three streams are live on the bus; Vulcan selects by Reference field.

---

## 5. Plugin Configuration

**Location on RPi**: `~/.signalk/plugin-config-data/sk-to-nmea2000.json`  
**Git copy**: `config/signalk-plugins/sk-to-nmea2000-config.json`

To modify enable/disable conversions:
1. Signal K Admin UI → Plugins → Signal K to NMEA 2000 → Configuration
2. OR edit `sk-to-nmea2000.json` and restart Signal K:
   ```bash
   sudo systemctl restart signalk
   ```

### Config Structure (excerpt)

```json
{
  "configuration": {
    "TRUE_HEADING": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30,
      "navigationheadingTrue": "signalk-heading-true-calculator.XX"
    },
    "WINDv2": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30
    },
    "WIND_TRUE_GROUND": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30
    },
    "WIND_TRUE": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30
    },
    "ATTITUDE": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30
    },
    "LEEWAY": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30
    },
    "SetDrift": {
      "enabled": true,
      "resend": 0,
      "resendTime": 30
    },
    "HEADINGv2": {
      "enabled": false,
      "resend": 0,
      "resendTime": 30
    }
  },
  "enabled": true,
  "enableLogging": false,
  "enableDebug": false
}
```

---

## 6. Troubleshooting

### Vulcan 7 FS not receiving heading updates

**Check**:
1. Is plugin enabled? `sk-to-nmea2000.json` → `"enabled": true`
2. Is TRUE_HEADING active? `"TRUE_HEADING": { "enabled": true }`
3. Is Signal K publishing `navigation.headingTrue`?
   ```bash
   curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation | grep -i headingtrue
   ```
4. Is YDNU-02 connected? `ls -la /dev/ttyACM0`
5. Check N2K bus: Vulcan 7 FS → Diagnostics → NMEA 2000 bus status

### Vulcan 7 FS not receiving wind data

**Check**:
1. Which Reference code is Vulcan expecting? (Apparent=2, True-Ground=0, True-Water=1)
2. Are the wind conversions enabled in config?
3. Is Signal K publishing the required wind paths? (angleApparent, speedApparent, directionTrue, etc.)
4. Multiple PGN 130306 streams are on the bus; verify Vulcan's wind source selection

### Plugin not starting

**Check**:
```bash
sudo systemctl status signalk
sudo journalctl -u signalk --since '5 minutes ago' | grep -i 'nmea\|wind\|heading'
```

**Restart plugin**:
```bash
sudo systemctl restart signalk
```

---

## 7. Testing

### Live N2K Traffic (YDNU-02)

Monitor real-time PGN messages:
```bash
candump vcan0 -d | grep "127250\|130306"
```

or

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self | python3 -m json.tool | \
  grep -A5 '"navigation":\|"environment":'
```

### Verify Conversions Firing

Check Signal K logs:
```bash
sudo journalctl -u signalk -f | grep -i "wind\|heading\|attitude"
```

Enable debug logging in config:
```json
"enableDebug": true
```

Then restart:
```bash
sudo systemctl restart signalk
```

---

## 8. References

- **Official Plugin**: https://github.com/SignalK/signalk-to-nmea2000
- **PGN Specifications**:
  - PGN 127250: Vessel Heading
  - PGN 130306: Wind Data
  - PGN 127257: Attitude
  - PGN 128000: Leeway
  - PGN 129291: Set and Drift
- **YDNU-02**: NMEA 2000 USB Gateway
- **Vulcan 7 FS**: Multi-function chart plotter

---

**Last Updated**: 2026-07-20  
**Status**: ✅ PRODUCTION (7/7 active conversions verified)

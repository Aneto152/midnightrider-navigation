# Quick Reference: Radians ↔ Degrees

## ONE-PAGE CHEAT SHEET

### The Golden Rule
```
SENSOR OUTPUTS:    Degrees
SIGNAL K STORES:   Radians
GRAFANA DISPLAYS:  Degrees (use rollDegrees path!)
```

---

## COMMON CONVERSIONS

| Degrees | Radians | Context |
|---------|---------|---------|
| **0°** | **0** | Upright / North |
| **10°** | **0.175** | Slight heel |
| **22°** | **0.384** | ⚠️ ALERT threshold |
| **45°** | **0.785** | Moderate |
| **90°** | **1.571** | Perpendicular |
| **180°** | **3.142** | Opposite direction |
| **360°** | **6.283** | Full circle |

---

## CONVERSION CALCULATOR

**Degrees to Radians:**
```
radians = degrees × 3.14159 ÷ 180
radians = degrees × 0.017453
radians = degrees ÷ 57.2958
```

**Radians to Degrees:**
```
degrees = radians × 180 ÷ 3.14159
degrees = radians × 57.2958
degrees = radians ÷ 0.017453
```

---

## SIGNAL K API PATHS (MidnightRider v2.0)

### For Radians (SI Standard)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/roll
```
Response: `0.2154` (radians)

### For Degrees (Recommended for Grafana!)
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/rollDegrees
```
Response: `12.34` (degrees)

---

## GRAFANA SETUP (Simplest)

**Query Path:**
```
navigation.attitude.rollDegrees
```

**Unit:** degrees
**Min/Max:** -90 to 90
**Decimals:** 1

✅ **Done! No math needed.**

---

## IF YOU STILL SEE NOISE

**Check 1: Is filter working?**
```bash
sudo systemctl restart signalk
sudo journalctl -u signalk | grep "filter\|WIT"
```

**Check 2: Raw sensor value**
```bash
timeout 2 cat /dev/ttyMidnightRider_IMU | grep HEATT
```
You should see smooth increments, not wild jumps.

**Check 3: Increase filter smoothing**
Signal K Admin UI → Plugins → WIT IMU NMEA Parser
Set `filterAlpha` to 0.1 or 0.15 (smoother)

---

## DEBUGGING COMMANDS

```bash
# Test raw sensor
cat /dev/ttyMidnightRider_IMU | grep HEATT

# Test Signal K API (radians)
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .roll.value

# Test Signal K API (degrees) - v2.0+
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/rollDegrees | jq .value

# Check plugin status
curl http://localhost:3000/skServer/plugins | jq '.[] | select(.id=="signalk-wit-nmea")'

# View logs
sudo journalctl -u signalk --no-pager | tail -50
```

---

## DECISION: What Do I Use?

```
Building a Grafana dashboard?
  → Use: navigation.attitude.rollDegrees
  → DONE!

Need historical data from InfluxDB?
  → Query: SELECT roll_deg FROM wit_imu
  → Works perfectly

Writing custom code?
  → Use: navigation.attitude.roll (radians)
  → Then multiply by 57.2958 to get degrees

Debugging raw sensor?
  → Check: /dev/ttyMidnightRider_IMU
  → Units: DEGREES from the start
```

---

## REFERENCE: Heel Angle Meanings

| Angle | Risk Level | Action |
|-------|-----------|--------|
| 0-10° | ✅ Safe | Normal sailing |
| 10-15° | ✅ Good | Optimal trim |
| 15-22° | ⚠️ Watch | Monitor carefully |
| 22-30° | 🔴 High | Consider reefing |
| 30°+ | 🛑 Danger | REEF NOW |

---

## THE MOST IMPORTANT LINE

**For Grafana:** 
Use `navigation.attitude.rollDegrees` 
**Don't convert anything. It's already clean degrees!**

---

*Bookmark this page!* ⛵

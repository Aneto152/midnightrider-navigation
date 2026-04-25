# CALYPSO UP10 INTEGRATION GUIDE (OPTIONAL)

**Status:** ⏳ Optional for race (works, known bugs)  
**Objective:** Configure Calypso anemometer BLE connection  
**Time:** ~30 min  
**Difficulty:** Low

---

## HARDWARE

**Model:** Calypso UP10 Portable Solar  
**Interface:** Bluetooth LE  
**Range:** ~30m  
**Data:** Wind speed (knots) + direction (degrees) + temperature

---

## BLE PAIRING

```bash
bluetoothctl

scan on
# Look for "Calypso" or "UP10"

pair <MAC_ADDRESS>

trust <MAC_ADDRESS>

connect <MAC_ADDRESS>

exit
```

---

## SIGNAL K PLUGIN

### Configuration

```json
{
  "plugins": {
    "signalk-calypso-ultrasonic": {
      "enabled": true,
      "macAddress": "<MAC_from_pairing>",
      "updateRate": 1
    }
  }
}
```

### Restart

```bash
sudo systemctl restart signalk
```

---

## EXPECTED DATA

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment | jq '.wind'

# Output:
# {
#   "speedTrue": 3.6,              // m/s (from knots)
#   "directionTrue": 5.5,          // radians (from degrees)
#   "speedApparent": 4.2,          // m/s
#   "directionApparent": 0.785     // radians
# }
```

---

## KNOWN ISSUES (NOT CRITICAL FOR RACE)

| Issue | Severity | Timeline |
|-------|----------|----------|
| UUID parsing errors | High | Post-race fix (1-2h rewrite) |
| Payload format incorrect | High | Post-race fix |
| Temperature conversion wrong | Medium | Post-race |
| Battery logic flawed | Low | Post-race |

**Recommendation:** If data appears reasonable during field test, use it. If buggy, skip for race (not critical).

---

## PRE-RACE DECISION

```
IF Calypso BLE connects AND data looks reasonable:
  USE IT (bonus wind data)

ELSE:
  SKIP IT (system works without wind sensor)
  → Polars plugin can estimate wind from GPS/IMU
```

---

## POST-RACE IMPROVEMENTS

Planned rewrites:
- [ ] Fix UUID discovery (currently hardcoded)
- [ ] Rewrite payload parser (handle all variants)
- [ ] Implement temperature correctly (K ← °C conversion)
- [ ] Add battery level monitoring

---

**Status:** ⏳ Optional  
**Critical for Race:** NO  
**Last Updated:** 2026-04-25

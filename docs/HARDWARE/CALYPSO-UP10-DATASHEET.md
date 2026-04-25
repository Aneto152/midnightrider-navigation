# CALYPSO UP10 — ULTRASONIC ANEMOMETER DATASHEET

**Manufacturer:** B&G (Garmin/Navico)  
**Model:** Calypso UP10 Portable Solar  
**Interface:** Bluetooth LE  
**Date:** 2026-04-25

---

## SPECIFICATIONS

| Spec | Value |
|------|-------|
| **Sensor Type** | Ultrasonic (no moving parts) |
| **Wind Speed Range** | 0-60 knots |
| **Wind Speed Accuracy** | ±3% or ±0.5 knot |
| **Wind Direction Range** | 0-360° |
| **Wind Direction Accuracy** | ±5° |
| **Update Rate** | 1 Hz |
| **Bluetooth** | BLE, range ~30m |
| **Power** | Solar panel (built-in) |
| **Battery** | Lithium, 48h backup |
| **Size** | Compact masthead unit |
| **Temperature Range** | -20°C to +70°C |
| **IP Rating** | IPX7 (waterproof) |

---

## DATA OUTPUT

### Bluetooth LE Payload (JSON)

```json
{
  "wind_speed_true": 14.2,      // knots
  "wind_direction_true": 315,    // degrees (0-360)
  "wind_speed_apparent": 18.5,   // knots (relative to boat)
  "wind_direction_apparent": 45, // degrees
  "temperature": 18.5,           // °C
  "battery_level": 95            // percentage
}
```

---

## SIGNAL K INTEGRATION

**Plugin:** `signalk-calypso-ultrasonic` (optional)  
**Status:** ✅ Connected (BLE)

**Paths Published (when enabled):**
```
environment.wind.speedTrue      (m/s, converted from knots)
environment.wind.directionTrue  (radians)
environment.wind.speedApparent  (m/s)
environment.wind.directionApparent (radians)
environment.outside.temperature (K, converted from °C)
```

---

## MOUNTING (Masthead)

- **Location:** Mast top (clear of obstructions)
- **Alignment:** Into the wind when boat is head-to-wind
- **Height:** As high as possible (above sails)
- **Cable:** BLE wireless (no cable runs needed)

---

## OPTIONAL STATUS

⚠️ **Current status:** 
- ✅ Hardware present on boat
- ⏳ Integration with Signal K: optional (nice-to-have)
- 🔴 6 issues identified in implementation (see ACTION-ITEMS)

**Decision for Block Island Race:** 
- Can use GPS-derived wind (approximate) if Calypso integration not complete
- Ideal if working, but NOT critical for racing

---

## KNOWN ISSUES (v1.0 Script)

| Issue | Severity | Fix Timeline |
|-------|----------|--------------|
| Incorrect UUIDs | High | Post-race (2-3h rewrite) |
| Payload parsing bugs | High | Post-race |
| Temperature conversion | Medium | Post-race |
| Battery check logic | Medium | Post-race |
| Wind angle calculations | Low | Post-race |

---

## PRE-RACE DECISION

**Use this checklist:**
- [ ] Calypso powered + BLE visible
- [ ] Can connect to Signal K
- [ ] Wind data appears reasonable
- **If YES:** Use it  
- **If NO:** Skip it, use GPS wind estimate (via polars plugin)

---

**STATUS:** ⏳ Optional for race (works, minor bugs don't affect racing)  
**Last Updated:** 2026-04-25  
**Post-Race Action:** Rewrite script with fixes

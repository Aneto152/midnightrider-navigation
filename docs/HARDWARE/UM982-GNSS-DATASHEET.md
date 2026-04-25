# UNICORE UM982 — DUAL-ANTENNA GNSS DATASHEET

**Manufacturer:** Unicore Communications  
**Model:** UM982 (Dual-antenna RTK-capable receiver)  
**Interface:** UART/USB  
**Date:** 2026-04-25

---

## SPECIFICATIONS

| Spec | Value |
|------|-------|
| **Antenna Type** | Dual (20cm spacing) |
| **Positioning Accuracy** | Position: ±2m, Heading: ±0.5° |
| **Update Rate** | 1 Hz (configurable) |
| **Cold Start** | <30 sec |
| **Output Sentences** | NMEA 0183: RMC, GGA, GSA, GSV, VTG, HDT, RMC, GLL |
| **Serial Interface** | UART 115200 baud, 8N1 |
| **USB Interface** | USB-Serial converter (CH340 compatible) |
| **Power** | 5V DC, 400mA typical |
| **Size** | 100 × 80 × 20 mm |
| **Operating Temp** | -10°C to +60°C |
| **Antenna Offset** | [À VÉRIFIER] |

---

## KEY SENTENCES (Midnight Rider)

### NMEA 0183 Output

```
$GNRMC,time,status,lat,lon,speed,course,date,magvar,magvar_dir*checksum
$GNGGA,time,lat,lon,fix_quality,num_sats,HDOP,altitude,height_geoid*checksum
$GNHDT,heading_true,T*checksum              ← TRUE HEADING (CRITICAL)
$GNVTG,course_true,T,course_mag,M,speed_kts,N,speed_kmh,K*checksum
```

### Proprietary Sentences (Unicore)

```
#HEADINGA,port,GPS_quality,heading_angle,pitch,roll,gyro_z,...
#UNIHEADINGA,quality,heading,pitch,roll,gyro_z,...
```

---

## CONFIGURATION (Midnight Rider)

### Physical Setup

- **Antennas:** 20cm spacing (across beam, ~perpendicular to boat axis)
- **Antenna offset in config:** [À VÉRIFIER]
- **Serial Port:** /dev/ttyUSB0 (115200 baud)
- **Power:** 5V from RPi USB or external supply

### Signal K Integration

**Plugin:** `signalk-um982-gnss` (v2.0)

**Paths Published:**
```
navigation.position           {lat, lon}
navigation.headingTrue        (degrees, 0-360°)
navigation.speedOverGround    (m/s)
navigation.courseOverGround   (radians, 0-2π)
navigation.rateOfTurn         (derived from dual antenna)
```

**Status:** ✅ Live @ 1 Hz

---

## PRE-RACE VERIFICATION

```bash
# Check device
ls -la /dev/ttyUSB*
dmesg | grep -i usb | tail -20

# Monitor NMEA sentences
cat /dev/ttyUSB0 | grep -E "RMC|HDT|GGA"

# Verify in Signal K
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/
  - .position (should show lat/lon ±2m accuracy)
  - .headingTrue (should show ±0.5° precision)
  - .speedOverGround (should show knots)
```

---

## KNOWN ISSUES

| Issue | Fix |
|-------|-----|
| Device not found | Check USB cable, restart RPi |
| No heading output | Verify dual-antenna alignment |
| Heading jumps | Check antenna separation (must be ≥20cm) |
| Position drift | Wait for cold start to complete |

---

## CRITICAL NOTES

⚠️ **Antenna Offset:** The exact offset angle (if any) needs verification against actual boat orientation. See `ACTION-ITEMS-2026-04-25.md` for next steps.

⚠️ **Heading vs COG:** This GPS sends TRUE HEADING (from dual antennas), NOT Course Over Ground (COG). This is better for racing because it works even at anchor.

⚠️ **Calibration:** After field deployment, validate heading ±0.5° against visual reference or compass.

---

## RACING ADVANTAGES

✅ **Dual-antenna setup:** True heading independent of magnetic variation  
✅ **High precision:** ±0.5° heading, ±2m position  
✅ **Fast update:** 1 Hz, suitable for real-time dashboards  
✅ **Multiple sentences:** Can feed NMEA 0183 to legacy instruments via signal-to-nmea0183 plugin  

---

**STATUS:** ✅ Operational  
**Last Updated:** 2026-04-25  
**Next Action:** Verify antenna offset (ACTION-ITEMS)

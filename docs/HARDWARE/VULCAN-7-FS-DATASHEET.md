# B&G VULCAN 7 FS — HARDWARE DATASHEET

**Manufacturer:** Navico (Garmin/B&G)  
**Model:** Vulcan 7 FS  
**Version:** Software v1.5  
**Date:** 2026-04-25

---

## SPECIFICATIONS

| Spec | Value |
|------|-------|
| **Display** | 7" touchscreen |
| **Resolution** | 800 × 480 pixels |
| **Interface** | NMEA 2000 (Micro-C connector) |
| **Power** | 12V DC, 3A typical |
| **Dimensions** | 215 × 145 × 95 mm |
| **Weight** | 1.2 kg |
| **Temperature** | -10°C to +60°C |
| **IP Rating** | IPX7 (splash-resistant) |
| **Connector** | NMEA 2000 Micro-C + Power 7-pin |

---

## NMEA 2000 CAPABILITIES

### Receive (Input) — PGNs Vulcan Listens To

| PGN | Name | Source | Data |
|-----|------|--------|------|
| 127250 | Vessel Heading | GPS/Compass | True/magnetic heading |
| 127251 | Rate of Turn | Gyro | Rate of turn (°/min) |
| 127257 | Attitude | IMU | Roll, pitch, yaw |
| 128259 | Speed, Water Referenced | Loch | Speed through water |
| 129025 | GNSS Position Rapid | GPS | Lat/lon (updated frequently) |
| 129026 | COG & SOG Rapid | GPS | Course + speed over ground |
| 129029 | GNSS Position Data | GPS | Extended position data |
| 129283 | Cross Track Error | Router | XTE to waypoint |
| 129284 | Navigation Data | Router | BTW, DTW, VMC, ETA |
| 130306 | Wind Data | Anemometer | Wind speed, angle |
| 130312 | Temperature | Sensor | Air, water temp |
| 127508 | Battery Status | Battery monitor | Voltage, current, SOC |

### Transmit (Output) — PGNs Vulcan Sends

| PGN | Name | Data | When |
|-----|------|------|------|
| 127237 | Heading/Track Control | Autopilot commands | When autopilot active |
| 127488 | Engine Parameters | RPM, load | When connected to engine |

---

## CONFIGURATION FOR MIDNIGHT RIDER

### Network Setup

**Physical:**
- Connect NMEA 2000 Micro-C to YDNU-02 gateway
- Connect power (12V+, GND) to house battery (LiFePO4 100Ah)
- Mount on chart table or helm position

**Software (Vulcan Settings):**

1. **Settings → Network → Device List**
   - Look for "YDNU-02" or "Signal K Gateway"
   - Enable it

2. **Advanced Source Selection**
   - Set heading source: Signal K (UM982)
   - Set position source: Signal K (UM982)
   - Set attitude source: Signal K (WIT IMU)
   - Set speed source: Loch (when installed)

3. **PGN Filters**
   - Enable receipt of 127257 (Attitude from WIT)
   - Enable receipt of 127250 (Heading from UM982)
   - Enable receipt of 129025 (Position from UM982)
   - Enable receipt of 130306 (Wind if available)

4. **Display Units**
   - Heading reference: TRUE (not magnetic)
   - Distance units: Nautical miles
   - Speed units: Knots
   - Temperature: Fahrenheit or Celsius (your choice)

---

## PRE-RACE CHECKLIST

- [ ] Power connection: 12V stable (check voltmeter)
- [ ] NMEA 2000 connector: secure, no corrosion
- [ ] Device list: YDNU-02 visible + enabled
- [ ] Source selection: Signal K prioritized
- [ ] Heading display: ±0.5° match with GPS (UM982)
- [ ] Position display: ±2m match with GPS
- [ ] Attitude display: Roll/pitch stable at rest
- [ ] Wave height: Appears after 5+ min data collection
- [ ] Touchscreen: responsive, no dead spots
- [ ] Brightness: sufficient for daylight use
- [ ] Recording: enabled for race data logging

---

## KNOWN ISSUES & WORKAROUNDS

| Issue | Cause | Fix |
|-------|-------|-----|
| No signal from YDNU-02 | Device not visible in list | Restart YDNU-02 USB + Vulcan |
| Heading mismatch | Magnetic vs true setting | Change Settings → Units → True |
| Sluggish response | Network congestion | Check NMEA 2000 bus (should be <10% load) |
| Touchscreen unresponsive | Connector issue | Power cycle: off 10s, back on |

---

## CONNECTIVITY MAP

```
Midnight Rider Data → Signal K Hub
                        ↓
                   YDNU-02 Gateway
                        ↓
                  NMEA 2000 Backbone
                        ↓
                   Vulcan 7 FS
                   (Display on helm)
```

---

## DOCUMENTATION REFERENCES

- **Installation Manual:** B&G Vulcan Series Installation Manual (SW v1.5, ref 988-11099-002)
- **Full Integration:** `/docs/INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md`
- **PGN Details:** `/docs/HARDWARE/YDNU-02-GATEWAY-DATASHEET.md`

---

**STATUS:** ✅ Installed & Operational  
**Last Updated:** 2026-04-25  
**Next Review:** Post-race (May 22)

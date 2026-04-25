# INTEGRATION GUIDES INDEX

All hardware integration guides for Midnight Rider.

---

## QUICK START

**Choose your component:**

1. **Vulcan 7 FS MFD** → See `VULCAN-SIGNALK-INTEGRATION.md`
   - How to configure NMEA 2000 reception
   - Which PGNs to enable
   - Source selection strategy

2. **UM982 GPS** → See `UM982-INTEGRATION-GUIDE.md`
   - Serial port setup (/dev/ttyUSB0)
   - Signal K plugin configuration
   - Antenna offset verification

3. **WIT IMU** → See `WIT-INTEGRATION-GUIDE.md`
   - Bluetooth LE pairing
   - Python bleak driver setup
   - Wave Analyzer v1.1 calibration

4. **Calypso Anemometer** → See `CALYPSO-INTEGRATION-GUIDE.md`
   - Optional wind sensor integration
   - Known issues + post-race fixes

5. **YDNU-02 Gateway** → See `YDNU-02-INTEGRATION-GUIDE.md`
   - USB ↔ NMEA 2000 bridge setup
   - Bidirectional data flow configuration

---

## INTEGRATION ARCHITECTURE

```
Physical Sensors (Boat)
  ├─ GPS UM982 (UART/USB)
  ├─ WIT IMU (Bluetooth LE)
  ├─ Calypso UP10 (Bluetooth LE)
  └─ NMEA 2000 backbone
         ↓
Raspberry Pi 4 (12V power)
  ├─ Signal K v2.25 Hub (port 3000)
  ├─ 5 Custom plugins
  └─ System services
         ↓
Data Processing
  ├─ InfluxDB (time-series)
  ├─ Grafana (dashboards)
  └─ qtVLM (routing)
         ↓
Output
  ├─ YDNU-02 → NMEA 2000 → Vulcan MFD
  └─ WiFi → iPad (optional)
```

---

## FILES IN THIS FOLDER

- **VULCAN-SIGNALK-INTEGRATION.md** (4.8 KB)
  - PGN mapping
  - Vulcan configuration steps
  - Source selection
  - Racing use cases

- **UM982-INTEGRATION-GUIDE.md** (3.2 KB)
  - Serial port setup
  - Signal K plugin config
  - Pre-race verification
  - Antenna offset notes

- **WIT-INTEGRATION-GUIDE.md** (4.1 KB)
  - Bluetooth BLE setup
  - Python bleak driver
  - Wave Analyzer v1.1 link
  - Calibration procedure

- **CALYPSO-INTEGRATION-GUIDE.md** (2.8 KB)
  - Optional anemometer setup
  - Known issues
  - Post-race improvements

- **YDNU-02-INTEGRATION-GUIDE.md** (3.5 KB)
  - Gateway USB connection
  - NMEA 2000 bridge config
  - Bidirectional data flow
  - PGN filtering

---

## COMMON QUESTIONS

**Q: Where do I start?**  
A: Start with VULCAN-SIGNALK-INTEGRATION.md (it's the display you'll see during racing).

**Q: Do I need ALL components?**  
A: No. Required: GPS + YDNU-02 + RPi4. Optional: WIT (for wave height), Calypso (for wind).

**Q: How long to integrate everything?**  
A: GPS: 30 min, WIT: 45 min, Vulcan: 1h, Calypso: 30 min. Total: 2-3 hours if doing all.

**Q: What if something doesn't work?**  
A: Check ACTION-ITEMS-2026-04-25.md for troubleshooting flows.

---

## TROUBLESHOOTING QUICK LINKS

- **GPS not appearing** → UM982-INTEGRATION-GUIDE.md § Troubleshooting
- **Vulcan no data** → VULCAN-SIGNALK-INTEGRATION.md § Troubleshooting
- **WIT data offline** → WIT-INTEGRATION-GUIDE.md § Troubleshooting
- **NMEA 2000 bus issues** → YDNU-02-INTEGRATION-GUIDE.md § Troubleshooting

---

**Status:** ✅ All guides ready  
**Last Updated:** 2026-04-25

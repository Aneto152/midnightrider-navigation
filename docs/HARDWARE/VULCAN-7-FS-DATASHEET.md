# B&G VULCAN 7 FS — HARDWARE DATASHEET

**Manufacturer:** Navico (B&G brand)  
**Model:** Vulcan 7 FS (SKU: 000-14082-001)  
**Type:** Sailing Chartplotter MFD  
**Software Version:** v1.5 (ref. manual 988-11099-004)  
**Date:** 2026-05-19  
**Status:** ✅ Installed & Operational

---

## HARDWARE SPECIFICATIONS

### Display

| Spec | Value |
|------|-------|
| **Screen Size** | 7" TFT Widescreen |
| **Resolution** | 800 × 480 pixels |
| **Brightness** | > 1200 nits |
| **Touch** | Full multi-touch (pinch, swipe, tap) |
| **Viewing Angles** | 80° left/right, 80° top/bottom |
| **Backlight Color** | White |

### Electrical

| Spec | Value |
|------|-------|
| **Supply Voltage** | 12V DC (10 – 17V) |
| **Power Consumption** | 12W typical / 20W max |
| **Recommended Fuse** | 3A |
| **Protection** | Reverse polarity + over-voltage (up to 18V transient) |

### Physical

| Spec | Value |
|------|-------|
| **Dimensions (W × H × D)** | 197 × 141 × 82.7 mm (7.56" × 5.55" × 3.26") |
| **Weight (display only)** | 1.32 kg (2.91 lbs) |
| **Mounting** | Bracket (supplied) or panel flush mount |
| **Protrusion (flush)** | 8 mm proud of surface |

### Environmental

| Spec | Value |
|------|-------|
| **Operating Temperature** | -15°C to +55°C |
| **Storage Temperature** | -20°C to +60°C |
| **Waterproof Rating** | IPX6 and IPX7 |
| **Humidity** | IEC 60945 Damp heat 66°C at 95% RH |
| **Shock/Vibration** | 100,000 cycles at 20G |

### Connectors

| Connector | Type | Purpose |
|-----------|------|---------|
| **NMEA 2000** | Micro-C (5-pin) | Data network (1 LEN) |
| **Power** | 4-pin proprietary | 12V+, GND, Power Control (yellow), Alarm (blue) |
| **Sonar** | 9-pin | CHIRP / DownScan / ForwardScan |
| **Radar/Ethernet** | 5-pin yellow | 100 Mbits/s — radar and networking |

---

## CONNECTIVITY & INTERFACES

| Interface | Detail |
|-----------|--------|
| **NMEA 2000** | 1× Micro-C port, 1 LEN |
| **Ethernet/Radar** | 1× 5-pin, 100 Mbit/s |
| **Wi-Fi** | Internal 802.11 b/g/n |
| **Bluetooth** | Internal |
| **SD Card** | 1× microSD, max 32GB (>32GB: format NTFS) |
| **Internal Storage** | 90 MB |
| **NMEA 0183** | Export over Wi-Fi |

---

## BUILT-IN GPS

| Spec | Value |
|------|-------|
| **Channels** | 32 channels |
| **Update Rate** | 10 Hz |
| **Position Accuracy** | Horizontal ±3 m |
| **Cold Start TTFF** | < 90 s (open sky) |
| **Satellite Reacquisition** | < 5 s |
| **Corrections** | WAAS, MSAS, EGNOS, GLONASS |

---

## SAILING FEATURES

| Feature | Description |
|---------|-------------|
| **SailSteer** | Wind, speed, heading, COG, laylines and waypoint on one screen |
| **RacePanel** | Start line countdown, time/distance/positioning |
| **Laylines** | Chart overlay with tidal and wind shift compensation |
| **SailingTime** | ETA calculation accounting for tacks, wind and tide |
| **Autopilot Control** | Wind, Auto, Nav., No Drift, Follow-up, Non-follow-up, Wind NAV |
| **Autopilot Manœuvres** | Tack/Gybe, depth contour tracking |
| **AIS** | Receive over NMEA 2000 only |
| **MARPA** | Radar target tracking (with radar module) |
| **ForwardScan** | 2D seabed ahead view (with transducer) |
| **Digital Switching** | BEP C-Zone, NaviOP |

### Data Capacity

| Item | Capacity |
|------|---------|
| **Waypoints** | 6,000 |
| **Routes** | 500 (max 100 points per route) |
| **Tracks** | 50 (max 12,000 track points) |

### Chart Compatibility

- Insight (Navico) + Insight Genesis
- Navionics (Gold, NAV+, Platinum+)
- C-MAP (MAX N, MAX N+)
- NV Digital (Raster US Charts)

---

## NMEA 2000 — COMPLETE PGN LIST

> Source: Vulcan Series Installation Manual 988-11099-004 + B&G product specification :cite[cx6]

### PGN RECEIVE (Input — what the Vulcan LISTENS to)

#### ISO / Network Management

| PGN | Name |
|-----|------|
| 59392 | ISO Acknowledgement |
| 59904 | ISO Request |
| 60160 | ISO Transport Protocol, Data Transfer |
| 60416 | ISO Transport Protocol, Connection Management |
| 60928 | ISO Address Claim |
| 65240 | ISO Commanded Address |
| 126208 | ISO Command Group Function |
| 126992 | System Time |
| 126996 | Product Info |
| 126998 | Configuration Information |

#### Navigation & Heading

| PGN | Name | Midnight Rider Source |
|-----|------|-----------------------|
| **127237** | Heading/Track Control | — (autopilot input) |
| **127245** | Rudder | — |
| **127250** | Vessel Heading | ✅ **UM982** (true heading via signalk-to-nmea2000) |
| **127251** | Rate of Turn | ✅ **UM982 / WIT IMU** |
| **127252** | Heave | — |
| **127257** | Attitude (Roll/Pitch/Yaw) | ✅ **WIT WT901BLECL** (PGN fixed 2026-05-17) |
| **127258** | Magnetic Variation | ✅ UM982 (auto-provided) |

#### Position & GPS

| PGN | Name | Midnight Rider Source |
|-----|------|-----------------------|
| **129025** | Position, Rapid Update | ✅ **UM982** |
| **129026** | COG & SOG, Rapid Update | ✅ **UM982** |
| **129029** | GNSS Position Data | ✅ **UM982** |
| **129033** | Time & Date | ✅ UM982 |
| **129283** | Cross Track Error | — (routing only) |
| **129284** | Navigation Data (BTW, DTW, VMC, ETA) | — (routing only) |
| 129539 | GNSS DOPs | UM982 |
| 129540 | GNSS Sats in View | UM982 |
| 129545 | GNSS RAIM Output | — |
| 129549 | DGNSS Corrections | — |
| 129551 | GNSS Differential Correction Receiver Signal | — |

#### AIS

| PGN | Name |
|-----|------|
| 129038 | AIS Class A Position Report |
| 129039 | AIS Class B Position Report |
| 129040 | AIS Class B Extended Position Report |
| 129041 | AIS Aids to Navigation |
| 129793 | AIS UTC and Date Report |
| 129794 | AIS Class A Static and Voyage Related Data |
| 129798 | AIS SAR Aircraft Position Report |
| 129801 | AIS Addressed Safety Related Message |
| 129802 | AIS Safety Related Broadcast Message |
| 129808 | DSC Call Information |
| 129809 | AIS Class B "CS" Static Data Report, Part A |
| 129810 | AIS Class B "CS" Static Data Report, Part B |

#### Speed & Depth

| PGN | Name | Midnight Rider Source |
|-----|------|-----------------------|
| **128259** | Speed, Water Referenced | ⚠️ Configured, no loch installed |
| **128267** | Water Depth | ⚠️ Configured, no depth sounder installed |
| 128275 | Distance Log | — |

#### Wind & Environment

| PGN | Name | Midnight Rider Source |
|-----|------|-----------------------|
| **130306** | Wind Data | ✅ **Calypso UP10** (when active) |
| 130310 | Environmental Parameters | — |
| 130311 | Environmental Parameters | — |
| **130312** | Temperature | ✅ Calypso (air temp) |
| 130313 | Humidity | — |
| 130314 | Actual Pressure | — |
| 130316 | Temperature, Extended Range | — |

#### Electrical & Tank

| PGN | Name | Midnight Rider Source |
|-----|------|-----------------------|
| 127488 | Engine Parameters, Rapid Update | — (no engine gateway) |
| 127489 | Engine Parameters, Dynamic | — |
| 127493 | Transmission Parameters | — |
| 127500 | Load Controller Connection State | — |
| 127501 | Binary Status Report | — |
| 127503 | AC Input Status | — |
| 127504 | AC Output Status | — |
| 127505 | Fluid Level | — |
| **127506** | DC Detailed Status | — (SOK BMS direct to InfluxDB) |
| 127507 | Charger Status | — |
| **127508** | Battery Status | — (SOK bypasses Signal K) |
| 127509 | Inverter Status | — |

#### Safety & Alerts

| PGN | Name |
|-----|------|
| 127233 | Man Overboard Notification (MOB) |
| 130060 | Label |
| 130576 | Small Craft Status |
| 130577 | Direction Data |
| 130578 | Vessel Speed Components |

#### Routes & Waypoints

| PGN | Name |
|-----|------|
| 130074 | Route and WP Service — WP List, WP Name & Position |

#### Entertainment (SonicHub)

| PGN | Range | Name |
|-----|-------|------|
| 130569–130585 | | Entertainment — Library, Config, Bluetooth, Zones, etc. |

---

### PGN TRANSMIT (Output — what the Vulcan SENDS on the network)

| PGN | Name | When |
|-----|------|------|
| 60160 | ISO Transport Protocol, Data Transfer | Always |
| 60416 | ISO Transport Protocol, Connection Mgmt | Always |
| 126208 | ISO Command Group Function | Always |
| 126992 | System Time | Always |
| 126993 | Heartbeat | Always |
| 126996 | Product Info | Always |
| **127237** | Heading/Track Control | When autopilot active |
| **127250** | Vessel Heading | From internal GPS |
| 127258 | Magnetic Variation | From GPS |
| 127502 | Switch Bank Control | When CZone connected |
| **128259** | Speed, Water Referenced | When loch connected |
| **128267** | Water Depth | When sonar connected |
| 128275 | Distance Log | When loch connected |
| **129025** | Position, Rapid Update | From internal GPS |
| **129026** | COG & SOG, Rapid Update | From internal GPS |
| **129029** | GNSS Position Data | From internal GPS |
| **129283** | Cross Track Error | When navigating to waypoint |
| **129284** | Navigation Data | When navigating to waypoint |
| 129285 | Navigation — Route/WP Information | When route active |
| 129539 | GNSS DOPs | From internal GPS |
| 129540 | GNSS Sats in View | From internal GPS |
| 130074 | Route and WP Service | When sharing waypoints |
| **130306** | Wind Data | When wind source active |
| 130310 | Environmental Parameters | When env. sensor active |
| 130311 | Environmental Parameters | When env. sensor active |
| 130312 | Temperature | When temp sensor active |
| 130577 | Direction Data | When heading active |
| 130578 | Vessel Speed Components | When speed active |

---

## NMEA 0183 SENTENCES (via Wi-Fi export)

### GPS / Position

| Sentence | Description | RX | TX |
|----------|-------------|----|----|
| DTM | Datum reference | ✅ | |
| GGA | GPS fix data | ✅ | ✅ |
| GLL | Geographic position lat/lon | ✅ | ✅ |
| GNS | GNSS fix data | ✅ | |
| GSA | GNSS DOP and active satellites | ✅ | ✅ |
| GSV | GNSS satellites in view | ✅ | ✅ |
| VTG | Course over ground and speed | ✅ | ✅ |
| ZDA | Time and date | ✅ | ✅ |

### Navigation

| Sentence | Description | RX | TX |
|----------|-------------|----|----|
| AAM | Waypoint arrival alarm | | ✅ |
| APB | Autopilot sentence B | | ✅ |
| BOD | Bearing origin to destination | | ✅ |
| BWC | Bearing/distance to waypoint (great circle) | | ✅ |
| BWR | Bearing/distance to waypoint (rhumb line) | | ✅ |
| RMB | Recommended minimum navigation | | ✅ |
| RTE | Routes | ✅ | |
| WPL | Waypoint location | ✅ | |
| XTE | Cross-track error | | ✅ |

### Depth / Speed / Sonar

| Sentence | Description | RX | TX |
|----------|-------------|----|----|
| DBT | Depth below transducer | ✅ | ✅ |
| DPT | Depth | ✅ | ✅ |
| MTW | Water temperature | ✅ | ✅ |
| VHW | Water speed and heading | ✅ | ✅ |
| VLW | Dual ground/water distance | ✅ | ✅ |
| VBW | Dual ground/water speed | ✅ | |

### Compass & Wind

| Sentence | Description | RX | TX |
|----------|-------------|----|----|
| HDG | Heading, deviation, variation | ✅ | ✅ |
| HDT | True heading | ✅ | |
| THS | True heading and status | ✅ | ✅ |
| ROT | Rate of turn | ✅ | |
| MWD | Wind direction and speed | ✅ | ✅ |
| MWV | Wind speed and angle | ✅ | ✅ |

### AIS / DSC

| Sentence | Description | RX | TX |
|----------|-------------|----|----|
| DSC | Digital selective calling | ✅ | |
| DSE | Expanded DSC | ✅ | |
| VDM | AIS VHF data-link message | ✅ | |
| VDO | AIS own-vessel report | ✅ | |

> ⚠️ AIS sentences are NOT bridged between NMEA 0183 and NMEA 2000.

### Radar / MARPA

| Sentence | Description | TX |
|----------|-------------|----|
| TLL | Target latitude and longitude | ✅ |
| TTM | Tracked target message | ✅ |
| MOB | Man overboard notification (RX only) | |

### Transducer

| Sentence | Description | RX | TX |
|----------|-------------|----|----|
| XDR | Transducer measurement | ✅ | ✅ |

---

## MIDNIGHT RIDER INTEGRATION

### Architecture

```
Signal K (port 3000, systemctl)
     ↓ signalk-to-nmea2000 plugin
     ↓ USB serial
YDNU-02 Gateway (USB → NMEA 2000 Micro-C)
     ↓ NMEA 2000 backbone
Vulcan 7 FS
     (helm display)
```

### PGNs Actually Transmitted by Signal K → Vulcan

The `signalk-to-nmea2000` plugin is configured to emit the following PGNs:

| PGN | Name | Signal K Source | Status |
|-----|------|-----------------|--------|
| **127250** | Vessel Heading | UM982 (headingTrue) | ✅ Active |
| **127257** | Attitude (Roll/Pitch/Yaw) | WIT IMU | ✅ Active (fixed 2026-05-17) |
| **129025** | Position, Rapid Update | UM982 (position) | ✅ Active |
| **129026** | COG & SOG, Rapid Update | UM982 (SOG/COG) | ✅ Active |
| **129029** | GNSS Position Data / Time & Date | UM982 | ✅ Active |
| **130306** | Wind Data | Calypso UP10 | ⚠️ Active when Calypso connected |
| **128259** | Speed, Water Referenced | — | ⚠️ Configured, no loch installed |
| **128267** | Water Depth | — | ⚠️ Configured, no sonar installed |

> ⚠️ **PGN 127257 (Attitude)** required a critical fix on 2026-05-17: `attitude.js` was
> patched to listen to individual scalar SK paths (`navigation.attitude.roll/pitch/yaw`)
> instead of the composite object, which doesn't trigger callbacks in Signal K 2.x.

### Source Selection (Vulcan Settings)

```
Settings → Advanced → Source Selection:
  Heading source:  Signal K / YDNU-02 (UM982 true heading) ← NOT internal GPS
  Position source: Signal K / YDNU-02 (UM982 position)    ← NOT internal GPS
  Attitude source: Signal K / YDNU-02 (WIT IMU)
  Speed STW:       No loch (use SOG if needed)
  Speed SOG:       Signal K / YDNU-02 (UM982)
  Wind:            Signal K / YDNU-02 (Calypso, if active)
```

> The Vulcan also has an **internal 10 Hz GPS** — it will be used as fallback
> if the UM982 signal is lost.

### Data Displayed on Vulcan 7 (Midnight Rider)

| Data | PGN | Source | Displayed As |
|------|-----|--------|-------------|
| True heading | 127250 | UM982 | Heading gauge, chart orientation |
| Roll (heel angle) | 127257 | WIT IMU | Attitude page |
| Pitch (trim) | 127257 | WIT IMU | Attitude page |
| Position | 129025/129029 | UM982 | Chart position, lat/lon |
| Speed over ground | 129026 | UM982 | Speed gauge (in knots) |
| Course over ground | 129026 | UM982 | COG indicator |
| Apparent wind | 130306 | Calypso | Wind angle gauge |
| True wind | 130306 | Calypso | Wind data page |

---

## CONFIGURATION — MIDNIGHT RIDER

### Physical Setup

- **Power:** 12V from house battery (SOK 100Ah LiFePO4)
- **NMEA 2000:** Micro-C → YDNU-02 gateway → Signal K (RPi 4)
- **GPS offset:** Configure GPS Bow Offset = distance from bow to unit

### Display Units

```
Settings → Units:
  Heading reference: TRUE (not magnetic)
  Distance:          Nautical miles (nm)
  Speed:             Knots
  Temperature:       °C (Celsius)
  Depth:             Meters
```

### Recommended Alarms

```
Settings → Alarms:
  Heel > 30°    → Visual + audible warning (race configuration)
  SOG < 1 kt    → Warning (equipment check)
  AIS CPA < 0.5 nm → Alert
```

---

## PRE-RACE CHECKLIST

- [ ] Power: 12V stable (check voltmeter on Vulcan battery status page)
- [ ] NMEA 2000: YDNU-02 visible in Device List
- [ ] Source selection: Signal K (YDNU-02) prioritized over internal GPS
- [ ] Heading display: matches UM982 (≈ 171.3° when facing south at dock)
- [ ] Position: lat/lon updating every 1s, within ±1.5m of known position
- [ ] Attitude: Roll/Pitch ≈ 0° at rest (dock level)
- [ ] Wind: apparent wind angle/speed live (if Calypso connected)
- [ ] SailSteer: laylines visible on chart
- [ ] RacePanel: countdown timer functional
- [ ] Touchscreen: responsive, no dead spots
- [ ] Brightness: sufficient for daylight (max 1200 nits)
- [ ] Chart: correct region loaded, position matches chart

---

## TROUBLESHOOTING

| Issue | Cause | Fix |
|-------|-------|-----|
| YDNU-02 not in device list | USB or N2K connection issue | Restart YDNU-02 USB + power cycle Vulcan |
| Heading reads 0° constant | No GPS lock on UM982 | Wait 30–60s for UM982 cold start, check BLE/USB |
| Position jumps wildly | GPS cold start not complete | Wait for ≥4 satellites, HDOP < 2 |
| Attitude blank | WIT IMU not sending PGN 127257 | Check WIT BLE connected, restart Signal K |
| Wind data missing | Calypso not connected to Signal K | Check `calypso_anemometer` systemd service |
| Data freezes mid-race | Signal K crash | `sudo systemctl restart signalk` |
| Sluggish N2K response | Bus congestion | Check NMEA 2000 load (<10% bus utilization) |
| Heading magnetic not true | Units not configured | Settings → Units → Heading Reference → True |

---

## DOCUMENTATION REFERENCES

- **Installation Manual:** Vulcan Series IM EN 988-11099-004 (`ref. 988-11099-004`)
- **YDNU-02 Integration:** `docs/HARDWARE/YDNU-02-GATEWAY-DATASHEET.md`
- **Signal K → N2K:** `docs/INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md`
- **signalk-to-nmea2000 config:** `docs/signalk-config/plugin-config-data/`

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial documentation (12 PGNs, incorrect specs) | OC |
| 2026-05-17 | attitude.js patched → PGN 127257 now working correctly | OC |
| 2026-05-19 | Full revision: corrected specs (dimensions, weight, temp), complete PGN list (70+ receive, 30+ transmit), NMEA 0183 sentences, Midnight Rider PGN mapping table | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Operational  
**Next Action:** Validate heel angle on attitude page during field test (May 19)

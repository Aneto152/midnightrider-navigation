# B&G WS320 — WIRELESS WIND SENSOR DATASHEET

**Manufacturer:** Navico (B&G brand)  
**Model:** WS320 Wireless Wind Sensor + Bluetooth Base Station  
**Pack SKU:** 000-14383-001 (sensor + interface)  
**Interface SKU:** 000-14388-001 (interface only)  
**Date:** 2026-05-19  
**Status:** ✅ Installed — Masthead, NMEA 2000 only (does NOT feed Signal K)

---

## SYSTEM OVERVIEW

The WS320 is a **two-component** wireless wind system:

| Component | Role |
|-----------|------|
| **WS320 Wind Sensor** | Masthead unit — measures wind speed and angle, solar powered, transmits via BLE |
| **Bluetooth Base Station** | Cockpit/below-deck unit — receives BLE from sensor, outputs to NMEA 2000 |

```
WS320 Masthead Sensor (solar, BLE TX)
     ↓ Bluetooth 4.0 (≤ 30m range)
Bluetooth Base Station (BLE RX)
     ↓ NMEA 2000 Micro-C (PGN 130306 @ 5 Hz)
NMEA 2000 backbone
     ↓
Vulcan 7 FS (wind speed + angle display)
```

> ⚠️ **The WS320 does NOT feed Signal K.** It is a standalone N2K instrument.
> Wind data for Signal K, InfluxDB and Grafana comes from the **Calypso UP10** (BLE → UDP).

---

## WIND SENSOR SPECIFICATIONS (Masthead Unit)

### Performance

| Spec | Value |
|------|-------|
| **Wind Speed Range** | 0.25 – 50 m/s (0.5 – 97 knots) |
| **Wind Speed Accuracy** | ±0.1 m/s (±0.2 kt) from 1–40 m/s (2–80 kt) |
| **Wind Speed Resolution** | 0.05 m/s (0.1 knots) |
| **Wind Angle Range** | 0 – 360° |
| **Wind Angle Accuracy** | ±0.5° |
| **Wind Angle Resolution** | 0.1° |
| **Data Output Rate** | **5 Hz** (apparent wind speed + angle) |
| **Output Type** | **Apparent wind only** (true wind calculated by Vulcan using SOG/COG) |
| **Wind Tunnel Testing** | > 500 individual tests for calibration validation |
| **Field Validation** | > 200,000 hours combined field testing |

### Physical

| Spec | Value |
|------|-------|
| **Weight** | 0.32 kg (0.7 lbs) |
| **Waterproof Rating** | IPx6 and IPx7 |
| **Operating Temperature** | -25°C to +65°C |
| **Mounting** | Masthead bracket (standard N2K masthead fitting) |

### Power

| Spec | Value |
|------|-------|
| **Power Source** | Solar panel (built-in, self-charging) |
| **Battery** | Rechargeable (included) |
| **Battery note** | **Disconnecting the battery loses BLE pairing** — re-pairing required |
| **Winter storage** | Remove sensor from mast and remove battery to prevent drain |

### Wireless Link (Sensor → Base Station)

| Spec | Value |
|------|-------|
| **Protocol** | Bluetooth 4.0 |
| **Range** | ≤ 30 m (98 ft) line-of-sight |
| **Suitable mast height** | Up to 25 m (80 ft) |
| **Pairing constraint** | Sensor must be ≤ 0.5 m from base station during pairing |

---

## BLUETOOTH BASE STATION SPECIFICATIONS

### Physical

| Spec | Value |
|------|-------|
| **Dimensions** | Ø 90 mm × H 38 mm (3.54" × 1.50") |
| **Waterproof Rating** | IPx7 |

### Electrical

| Spec | Value |
|------|-------|
| **Power Supply** | 9–16V DC via NMEA 2000 Micro-C network |
| **Power Consumption** | 1.2W (< 100 mA at 12V DC) |
| **Network Load** | **2 LEN** (100 mA) |
| **In-Rush Current** | 2A for 20 ms (at internal 5V) |
| **Drop Cable** | Micro-C 1.8m (6 ft) — included |

### Environmental

| Spec | Value |
|------|-------|
| **Operating Temperature** | -25°C to +60°C |
| **Storage Temperature** | -40°C to +85°C |
| **Humidity** | 66°C, 95% RH, 18 hours |

---

## NMEA 2000 OUTPUT

### PGN Transmitted

| PGN | Name | Content | Rate |
|-----|------|---------|------|
| **130306** | Wind Data | Apparent Wind Speed (m/s) + Apparent Wind Angle (rad) | **5 Hz** |

> Only **apparent wind** is transmitted. The Vulcan 7 FS calculates **true wind** 
> internally by combining apparent wind with SOG/COG from the UM982 GPS (PGN 129026).

### NMEA 2000 Connection

```
Micro-C drop cable (1.8m) → T-connector → NMEA 2000 backbone → Vulcan 7 FS
```

- Network load: **2 LEN** — verify NMEA 2000 bus capacity (max 50 LEN per network)
- Must be within 6m drop from backbone (NMEA 2000 specification)

---

## PAIRING PROCEDURE

> ⚠️ **Pairing must be done BEFORE installing the sensor on the mast.**

```
1. Connect base station to NMEA 2000 network
2. Have the sensor battery on hand (do NOT insert yet)
3. Position sensor ≤ 0.5 m from base station
4. Power on the NMEA 2000 network
5. Insert and connect the battery to the wind sensor
6. Base station and sensor will auto-pair (may take up to 5 minutes)
7. On Vulcan 7: Settings → Network → Device List → select WS320
8. Select "Data" → verify apparent wind angle and speed are updating
9. Install sensor at masthead
10. Perform wind angle calibration from Vulcan: Settings → Network → WS320 → Calibrate
```

**LEDs during pairing:**
- Base station LED flashing → searching for sensor
- Base station LED solid → paired successfully

---

## WIND ANGLE CALIBRATION

The wind angle offset corrects for sensor misalignment at the masthead:

```
Vulcan 7: Settings → Network → Device List → WS320 → Calibrate
Method:  Point bow into wind (head-to-wind)
         Wind angle should read 0° (dead ahead)
         Apply offset if deviation observed
Typical offset: ± a few degrees depending on mounting precision
```

---

## MIDNIGHT RIDER — INSTALLATION & CONTEXT

### Physical Setup

| Parameter | Value |
|-----------|-------|
| **Sensor location** | Masthead (top of mast) |
| **Sensor orientation** | Arrow pointing forward (toward bow) |
| **Base station location** | Below deck or cockpit coaming |
| **NMEA 2000 connection** | Via Micro-C T-connector on backbone |
| **Power** | From NMEA 2000 bus (powered by house battery SOK 100Ah) |

### Data Flow on Midnight Rider

```
WS320 Masthead (BLE @ 5 Hz)
     ↓
Bluetooth Base Station
     ↓ PGN 130306 (Apparent Wind)
NMEA 2000 backbone → Vulcan 7 FS

Vulcan 7 FS (internal calculation):
  True Wind = f(Apparent Wind, SOG, COG from UM982 via PGN 129026)
  → Displayed on SailSteer, Wind page
```

### Relationship with Calypso UP10

The boat has **two independent wind sources**:

| Source | Path | Data Available |
|--------|------|---------------|
| **WS320** | NMEA 2000 → Vulcan 7 FS only | Apparent wind → Vulcan display |
| **Calypso UP10** | BLE → Signal K → InfluxDB → Grafana | Apparent + True wind → all dashboards |

> The WS320 and Calypso serve different purposes:
> - WS320 → real-time helm display on Vulcan (fast 5 Hz, low latency)
> - Calypso → data logging, trend analysis, Grafana dashboards

---

## WIND DATA — SAILING CONTEXT

### Apparent vs True Wind (displayed by Vulcan)

| Type | Description | Use |
|------|-------------|-----|
| **Apparent Wind Angle (AWA)** | Wind angle relative to bow as felt by sensor | Direct sail trim |
| **Apparent Wind Speed (AWS)** | Wind speed relative to boat motion | Direct sail trim |
| **True Wind Angle (TWA)** | Actual wind angle relative to bow (Vulcan calculates) | Tactics |
| **True Wind Speed (TWS)** | Actual meteorological wind speed (Vulcan calculates) | Routing |

### Beaufort Scale Reference (True Wind Speed)

| Beaufort | TWS (knots) | Conditions | J/30 Sail Config |
|----------|------------|------------|-----------------|
| 0–1 | 0–3 | Calm | Drifter / full canvas |
| 2–3 | 4–10 | Light breeze | Full canvas |
| 4–5 | 11–21 | Moderate | Full canvas → reef consideration |
| 6 | 22–27 | Strong breeze | 1st reef |
| 7+ | 28+ | Near gale | 2nd reef + storm jib |

---

## PRE-RACE VERIFICATION

```bash
# On Vulcan 7 display:
# 1. Settings → Network → Device List → confirm WS320 listed
# 2. Settings → Network → WS320 → Data → verify:
#    - Apparent Wind Angle: updating, makes sense for current wind
#    - Apparent Wind Speed: non-zero if any wind present
# 3. Open SailSteer page → confirm wind arrow direction and speed
# 4. Rotate boat bow through wind → verify wind angle tracks correctly
```

**Quick sanity checks:**
- At anchor, bow into wind: AWA ≈ 0°
- WS320 visible in Vulcan device list (not greyed out)
- Wind speed ≥ 0.3 kt in any visible breeze
- Wind data updating at 5 Hz (smooth needle movement on Vulcan display)

---

## KNOWN ISSUES & FIXES

| Issue | Cause | Fix |
|-------|-------|-----|
| No wind data on Vulcan | Base station not paired | Re-pair: bring sensor ≤0.5m from base, power cycle both |
| Wind angle reads 180° off | Sensor mounted backward | Verify forward arrow on sensor points to bow, re-calibrate |
| Intermittent data | Mast height > 25m or interference | Check BLE range, move base station higher if possible |
| Wind speed reads 0 in known breeze | Battery depleted | Remove sensor from mast, recharge battery (USB cable) |
| Battery disconnected | Winter storage or crash | Re-pair required after battery reconnection |
| WS320 not in Vulcan device list | N2K bus issue | Check Micro-C connector, verify T-joiner secure |

---

## CERTIFICATIONS

| Standard | Compliance |
|----------|-----------|
| **FCC** | Part 15 |
| **CE** | RED 2014/53/EU |
| **Industry Canada** | ISED license-exempt |
| **ANZ** | Radiocommunications standards |
| **Waterproof** | IPx6 + IPx7 (sensor), IPx7 (base) |

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-05-19 | Initial creation — document did not exist in repo | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Operational — Masthead installed, feeds Vulcan 7 FS via NMEA 2000  
**Next Action:** Verify wind angle calibration during field test (compare WS320 vs Calypso UP10 heading)

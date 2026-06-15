# YACHT DEVICES YDBC-05 — DIGITAL BAROMETER DATASHEET

**Manufacturer:** Yacht Devices Ltd.  
**Model:** YDBC-05 (Digital Barometer)  
**Interface:** NMEA 2000 (bidirectional network device)  
**Certification:** NMEA 2000 certified :cite[eks]  
**Firmware Version:** 1.25  
**Date:** 2026-05-19  
**Status:** ✅ Installed — NMEA 2000 backbone, data via YDNU-02 → Signal K

> ⚠️ **INSTRUMENT-INVENTORY.md mismatch:** The inventory file (updated 2026-05-13)
> lists the barometer as "Not Installed". This datasheet reflects the actual
> current state as confirmed by Denis. **INSTRUMENT-INVENTORY.md requires updating.**

---

## MODELS

| Model | NMEA 2000 Connector | Notes |
|-------|---------------------|-------|
| **YDBC-05N** | NMEA 2000 Micro Male | Standard — compatible with Garmin, DeviceNet |
| **YDBC-05NT** | NMEA 2000 Micro Male + built-in terminator | Replace a terminator on the bus |
| **YDBC-05R** | Raymarine SeaTalk NG Female | Raymarine networks |
| **YDBC-05RT** | Raymarine SeaTalk NG Female + terminator | Replace a terminator on SeaTalk NG |

> **Midnight Rider uses YDBC-05N** (NMEA 2000 Micro Male — compatible with Vulcan 7 FS backbone).
> The `T` suffix models can replace a bus terminator if no free T-connectors are available.

---

## SPECIFICATIONS

### Sensor Performance

| Parameter | Value |
|-----------|-------|
| **Measurement Range** | 300 – 1100 hPa (mbar) / 225 – 825 mmHg |
| **Relative Accuracy** | ± 0.12 hPa |
| **Absolute Accuracy (0°C to +65°C)** | **± 1 hPa** |
| **Absolute Accuracy (outside 0–65°C)** | ± 2.5 hPa |
| **Output Resolution** | **0.01 hPa** |
| **Data Update Rate** | Every **2 seconds** (0.5 Hz) |
| **Sensor Location** | Inside device case (ambient atmospheric pressure) |
| **Historical Storage** | Last **48 hours** stored in RAM |
| **Calibration** | Factory-calibrated, user offset ± 10.0 hPa adjustable |

### Electrical

| Parameter | Value |
|-----------|-------|
| **Supply Voltage** | 7 – 16V DC (from NMEA 2000 network) |
| **Current Consumption** | 24 mA |
| **Network Load** | **1 LEN** (50 mA equivalent) |
| **Reverse Polarity Protection** | Yes |

### Physical

| Parameter | Value |
|-----------|-------|
| **Weight** | 11 g |
| **Operating Temperature** | -40°C to +80°C |
| **Mounting** | Direct to NMEA 2000 backbone (no drop cable required) |
| **LED Indicator** | Yes (power/data/programming confirmation) |
| **Maintenance** | None required (sealed, non-dismountable case) |
| **Warranty** | 2 years |

---

## NMEA 2000 MESSAGES

### Transmitted (factory default Mode 0 — maximum compatibility)

| PGN | Name | Period | Notes |
|-----|------|--------|-------|
| **130310** | Environmental Parameters | 2 s | Atmospheric pressure (instance 0) |
| **130311** | Environmental Parameters | 2 s | Atmospheric pressure (instance 0) |
| **130314** | Actual Pressure | 2 s | Barometer-specific PGN |

> **Factory setting Mode 0** transmits all three PGNs for maximum compatibility.
> All modern chartplotters (post-2012) support PGN 130314.
> Older plotters (pre-2010) may not support 130311. PGN 130310 is universally supported.

### Received

| PGN | Name | Purpose |
|-----|------|---------|
| 59392 | ISO Acknowledgement | Network service |
| 59904 | ISO Request | Network service |
| 60928 | ISO Address Claim | Network address management |
| 126464 | PGN List Group Function | Transmit only |
| 126996 | Product Information | Device identification (every 60s) |
| 127258 | Magnetic Variation | **Used for device programming** |
| 129044 | Datum | **Used for device programming** |

---

## SPECIAL FEATURES

### 48-Hour Pressure History

The barometer stores the last 48 hours of pressure measurements in RAM:
- Retrievable by compatible software (CAN Log Viewer, NMEA 2000 Wi-Fi Gateway)
- Useful for weather trend analysis
- **RAM only — cleared on power loss**

### Digital Switching Control (Advanced)

Can trigger NMEA 2000 digital switching channels (compatible with YDCC-04 Circuit Control) based on:
- Absolute pressure threshold
- Pressure delta over **30 minutes**
- Pressure delta over **1 hour**

Example use: Alarm trigger when pressure drops > 3 hPa/hour (storm warning).

### Configurable Calibration Offset

An offset from -10.0 to +10.0 hPa can be applied to align with other instruments:
- Configured via chartplotter programming interface (datum/magnetic variation method)
- Factory calibration is accurate — offset only needed if aligning to local reference

---

## MIDNIGHT RIDER INTEGRATION

### Architecture

```
YDBC-05N (atmospheric pressure sensor)
     ↓ NMEA 2000 Micro-C (PGNs 130310/130311/130314 @ 0.5 Hz)
NMEA 2000 backbone
     ↓ (shared with Vulcan 7 FS, WS320)
YDNU-02 Gateway (USB → Signal K)
     ↓ signalk-to-nmea2000 plugin (receive mode)
Signal K (port 3000, systemctl)
     ↓ signalk-to-influxdb2 plugin
InfluxDB (port 8086, Docker)
     ↓
Grafana (port 3001) — Dashboard 02: ENVIRONMENT
```

### Signal K Path

| SK Path | Unit | Source | Conversion |
|---------|------|--------|-----------|
| `environment.outside.pressure` | Pa (Pascal) | `nmea2000.*` (via YDNU-02) | ÷ 100 = hPa in Grafana |

> Signal K stores pressure in **Pascals**. Convert to hPa for display: ÷ 100.
> Example: 101325 Pa = 1013.25 hPa (standard atmosphere).

### N2K Bus Load Summary (Midnight Rider)

| Device | LEN | Status |
|--------|-----|--------|
| YDNU-02 Gateway | 1 | ✅ Active |
| Vulcan 7 FS | 1 | ✅ Active |
| B&G WS320 Base Station | 2 | ✅ Active |
| **YDBC-05 Barometer** | **1** | ✅ Active |
| **Total** | **5 / 50 max** | ✅ Well within limits |

### Grafana Panel — Dashboard 02: ENVIRONMENT

```flux
# Pressure query (InfluxDB)
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart)
  |> filter(fn: (r) => r._measurement == "environment" and
                        r._field == "outside.pressure")
  |> map(fn: (r) => ({r with _value: r._value / 100.0}))  // Pa → hPa
```

Expected range: 960 – 1040 hPa (normal conditions)

### Weather Trend Reference

| Change (3h) | Trend | Interpretation |
|-------------|-------|---------------|
| > +3 hPa | Rising rapidly | Clearing, improving |
| +1 to +3 hPa | Rising | Improving |
| ±1 hPa | Steady | Stable |
| -1 to -3 hPa | Falling | Deteriorating |
| < -3 hPa | Falling rapidly | **Storm warning** |

---

## LED SIGNALS

| Signal | Meaning |
|--------|---------|
| Flash every 2s | Normal operation — data transmitting |
| 6 rapid flashes (0.5s period) | PGN 129044 (Datum) or 127258 (Variation) received — correctly connected |
| 1 flash (3s) | Programming command received and confirmed |
| 3 flashes (3s) | Settings saved to non-volatile memory |
| 4 flashes | Programming mode timed out (10 min) — returned to normal |

---

## PROGRAMMING PROCEDURE

> ⚠️ Programming changes message settings only. The barometer always transmits
> **atmospheric pressure** regardless of configuration. Do not change factory
> settings unless aligning to a local reference.

### Method (via Vulcan 7 FS — Datum method)

```
1. STEP 1 — Enter standby mode:
   Vulcan → Settings → Units → Chart Datum → "European 1950 (Mean, European Datum)"
   Wait for 1× LED confirmation signal (3 sec)

2. STEP 2 — Enter programming mode:
   Vulcan → Settings → Units → Chart Datum → "Australian Geodetic 1966"
   Wait for 1× LED confirmation signal

3. STEP 3 — Adjust settings if needed:
   (Factory Mode 0 is recommended — do not change unless necessary)
   "Bermuda 1957" → increment message setting by 1

4. STEP 4 — Save to non-volatile memory:
   Vulcan → Settings → Units → Chart Datum → "WGS 1984"
   Wait for 3× LED confirmation signal

5. Return chartplotter to normal chart datum (WGS 1984 is correct for GPS)
```

---

## INSTALLATION

### Physical

1. Connect **NMEA 2000 Micro-C** directly to backbone T-connector
2. **No drop cable required** — direct backbone connection is supported
3. Install in **dry, ventilated location** — sensor is inside the case
4. Avoid direct solar exposure (will cause elevated readings)
5. Avoid engine room / exhaust vicinity (temperature affects accuracy)
6. Optimal location: nav station below deck or shaded cockpit area

### Verification After Installation

```bash
# 1. Check NMEA 2000 device list on Vulcan 7 FS
# Settings → Network → Device List
# Expected: "Digital Barometer YDBC-05" visible

# 2. Add pressure to Vulcan display page
# Nav page → Add data → Environmental → Barometric Pressure
# Expected: value in hPa, updating every 2 seconds

# 3. Verify Signal K receiving data
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/outside | jq .pressure
# Expected: {"value": 101325, ...}  (Pa — divide by 100 for hPa)

# 4. Check InfluxDB
docker exec influxdb influx query \
  'from(bucket:"midnight_rider") |> range(start: -5m)
   |> filter(fn: (r) => r._field == "outside.pressure") |> last()'
# Expected: recent timestamp, value ~101000-102000 (Pa)

# 5. Cross-check with Grafana Dashboard 02: ENVIRONMENT
# http://192.168.1.131:3001/d/environment
# Expected: pressure ~1010-1020 hPa at dock
```

---

## KNOWN ISSUES & FIXES

| Issue | Cause | Fix |
|-------|-------|-----|
| LED not flashing after power-on | No N2K bus power | Check NMEA 2000 bus 12V supply |
| Not in Vulcan device list | Loose connector | Remove/reseat Micro-C, check T-connector |
| Pressure reading on Vulcan but not Signal K | YDNU-02 filter blocking PGN | Check YDNU-02 filter settings (global_rx filter) |
| Pressure offset vs forecast | Normal — station vs sea level | Apply offset calibration or correct for altitude |
| Value unchanged after 2s | N2K traffic issue | Check bus for errors, verify YDNU-02 yellow LED flashing |

---

## RACING / TACTICAL VALUE

⚠️ **Pressure vs MSL:** The YDBC-05 measures **station pressure** (actual pressure at sensor location).
Weather forecasts use **mean sea level (MSL) pressure**. For a vessel at sea level, difference is negligible.

| Application | Use |
|-------------|-----|
| **Pre-race weather** | Verify forecast vs actual — rising/falling trend assessment |
| **Squall detection** | Rapid pressure drop (> 3 hPa/3h) → storm warning |
| **Routing decisions** | Pressure gradient analysis for wind strength prediction |
| **Grafana Dashboard** | 48h pressure trend visible — compare to weather model |

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-05-19 | Initial creation — device physically installed on N2K backbone (not yet reflected in INSTRUMENT-INVENTORY.md) | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Installed & Operational — NMEA 2000 → YDNU-02 → Signal K → InfluxDB → Grafana  
**Next Actions:**
1. Update `INSTRUMENT-INVENTORY.md` — move barometer from "Not Installed" to "Active"
2. Add `environment.outside.pressure` panel to Grafana Dashboard 02: ENVIRONMENT
3. Verify Signal K source name for barometer data (`nmea2000_ydbc05` or similar)
4. Cross-validate reading vs local weather station

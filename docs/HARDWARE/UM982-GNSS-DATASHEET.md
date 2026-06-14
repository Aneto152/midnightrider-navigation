# UNICORE UM982 — DUAL-ANTENNA GNSS DATASHEET

**Manufacturer:** Unicore Communications  
**Model:** UM982 (Dual-antenna RTK-capable receiver)  
**SoC:** Nebulas IV (UC9810)  
**Interface:** UART (LV-TTL) / USB-Serial  
**Date:** 2026-05-19  
**Status:** ✅ Operational  

---

## MODULE SPECIFICATIONS

> Note: The UM982 is an SMD module (16 × 21 mm). The figures below refer to the module itself.
> The carrier board (TOP982 or equivalent) has different physical dimensions.

### Performance

| Spec | Value |
|------|-------|
| **Channels** | 1408 simultaneous (Nebulas IV SoC) |
| **Cold Start (TTFF)** | < 30 s |
| **Warm Start** | < 10 s |
| **Reacquisition** | < 1 s |
| **RTK Initialization** | < 5 s (typical), > 99.9% reliability |
| **Data Update Rate** | Up to 20 Hz (configured at 1 Hz on Midnight Rider) |
| **Output Protocols** | NMEA-0183 v4.10 (default) / v4.11, Unicore proprietary (ASCII + binary) |
| **Correction Input** | RTCM V3.x (auto-detected format) |

### Accuracy (RMS)

| Mode | Horizontal | Vertical |
|------|-----------|---------|
| **Autonomous (Single Point)** | 1.5 m | 2.5 m |
| **DGPS** | 0.4 m + 1 ppm | 0.8 m + 1 ppm |
| **RTK** | **0.8 cm + 1 ppm** | **1.5 cm + 1 ppm** |
| **Heading** | **0.1° @ 1 m baseline** | — |
| **Velocity** | 0.03 m/s | — |
| **Time** | 20 ns | — |

> ⚠️ RTK accuracy requires a 1 km baseline and quality antenna. Atmospheric conditions,
> baseline length and satellite geometry may affect results.

### Observation Accuracy (Carrier Phase, RMS)

| Band | BDS | GPS | GLONASS | Galileo |
|------|-----|-----|---------|---------|
| **B1I/L1 C/A/G1/E1 Pseudorange** | 10 cm | 10 cm | 10 cm | 10 cm |
| **B1I/L1/G1/E1 Carrier Phase** | 1 mm | 1 mm | 1 mm | 1 mm |
| **B3I/L2/G2 Pseudorange** | 10 cm | 10 cm | 10 cm | 10 cm |
| **B3I/L2/G2 Carrier Phase** | 1 mm | 1 mm | 1 mm | 1 mm |
| **B2I/L5/E5a/E5b Pseudorange** | 10 cm | 10 cm | — | 10 cm |
| **B2I/L5/E5a/E5b Carrier Phase** | 1 mm | 1 mm | — | 1 mm |

### Electrical

| Spec | Value |
|------|-------|
| **Input Voltage (VCC)** | +3.0 V to +3.6 V DC |
| **Ripple Voltage** | 50 mV max (ripple included in VCC range) |
| **Working Current** | 180–300 mA @ 3.3V |
| **Power Consumption** | 600 mW typical (dual antenna, 10 Hz PVT + 10 Hz RTK + 10 Hz Heading) |

### Physical

| Spec | Value |
|------|-------|
| **Module Size** | 16.0 × 21.0 × 2.6 mm |
| **Module Weight** | 1.82 ± 0.03 g |
| **Package** | 48-pin LGA (SMD) |
| **Operating Temp** | -40°C to +85°C |
| **Storage Temp** | -55°C to +95°C |
| **Humidity** | 95% non-condensing |
| **Vibration/Shock** | MIL-STD-810F / GJB150.16A-2009 |

### Communication Interfaces

| Interface | Detail |
|-----------|--------|
| **UART** | 3× UART LV-TTL (COM1, COM2, COM3) — baud rates: 9600 to 921600 |
| **USB** | Via USB-Serial converter on carrier board (CH340 / CP2102 / PL2303) |
| **PPS** | 1 PPS output (configurable polarity, width, period) |
| **EVENT** | Event mark input |
| **RTK_STAT** | RTK status indicator pin (HIGH = RTK fixed) |
| **PVT_STAT** | PVT positioning indicator pin |
| **ERR_STAT** | Error/self-test indicator pin |
| **RESET_N** | Hardware reset (active low, ≥ 5 ms) |
| **I2C / SPI / CAN** | Reserved — not currently supported by firmware |

---

## CONSTELLATION & FREQUENCY SUPPORT

| System | Master Antenna (ANT1) | Slave Antenna (ANT2) |
|--------|----------------------|---------------------|
| **GPS** | L1 C/A, L2P(Y)/L2C, L5 | L1 C/A, L2C |
| **Galileo** | E1, E5a, E5b | E1, E5b |
| **BeiDou** | B1I, B2I, B3I | B1I, B2I, B3I |
| **GLONASS** | L1, L2 | L1, L2 |
| **QZSS** | L1, L2, L5 | L1, L2 |
| **SBAS** | ✅ (MSAS, WAAS, etc.) | — |

> ANT1 (master) = position reference. ANT2 (slave) = heading reference.
> Heading = angle from True North to the ANT1→ANT2 baseline vector (clockwise).

---

## KEY UNICORE TECHNOLOGIES

### INSTANT HEADING
Single-epoch ambiguity resolution algorithm using multi-system, multi-frequency
carrier wide/narrow lane combinations. Provides accurate heading **immediately**,
even when stationary, without requiring movement. Includes cycle-slip detection,
multi-path error correction, and ambiguity validation.

### RTK KEEP
Maintains centimeter-level positioning accuracy for **up to 10 minutes** after loss
of base station RTCM data, using ionospheric and tropospheric delay models
and parameter estimation.

### Dual-RTK Engine
Independent RTK co-processor within the NebulasIV SoC. Handles RTK positioning
and dual-antenna heading simultaneously without performance degradation.

---

## NMEA 0183 OUTPUT SENTENCES

### Standard NMEA v4.10 (Default Firmware)

| Sentence | Description | Key Fields |
|----------|-------------|------------|
| **`$GNGGA`** | GNSS Fix Data | lat, lon, fix quality, num_sats, HDOP, altitude |
| **`$GNRMC`** | Recommended Minimum Navigation | time, status, lat, lon, speed (kts), course, date |
| **`$GNVTG`** | Course Over Ground & Ground Speed | COG true, COG mag, speed kts, speed km/h |
| **`$GNTHS`** / **`$GNHDT`** | True Heading and Status | heading_true (degrees) |
| **`$GNROT`** | Rate of Turn | deg/min |
| **`$GNGLL`** | Geographic Position | lat, lon, time, status |
| **`$GNGNS`** | GNSS Fix Data (multi-system) | lat, lon, mode indicator, num_sats |
| **`$GNGSA`** | DOP and Active Satellites | fix mode, PRN list, PDOP, HDOP, VDOP |
| **`$GNGSV`** | Satellites in View | 3 sets for tri-band (GPS/GAL/BDS each output their own set) |
| **`$GNGST`** | Pseudorange Error Statistics | RMS, sigma lat/lon/alt |
| **`$GNGRS`** | GNSS Range Residuals | residuals per satellite |
| **`$GNZDA`** | Date and Time | UTC time, day, month, year, timezone |
| **`$GNDTM`** | Datum Reference | local datum, lat/lon/alt offset |
| **`$GNGBS`** | GNSS Satellite Fault Detection | lat/lon/alt error estimates |

> ⚠️ By default, NMEA messages are **disabled** on power-up.
> Use commands like `gngga 1` to enable at 1 Hz, `gngga 0.05` for 20 Hz.

### Slave Antenna NMEA Variants (Unicore Extensions)

These mirror standard messages but report data from ANT2 (slave antenna):

| Sentence | Description |
|----------|-------------|
| **`$GPGGAH`** | GGA for slave antenna |
| **`$GPGLLH`** | GLL for slave antenna |
| **`$GPGNSH`** | GNS for slave antenna |
| **`$GPGSAH`** | GSA for slave antenna |
| **`$GPGSTH`** | GST for slave antenna |
| **`$GPGRSH`** | GRS for slave antenna |
| **`$GPGSVH`** | GSV for slave antenna |
| **`$GPRMCH`** | RMC for slave antenna |
| **`$GPVTGH`** | VTG for slave antenna |

### Heading & Attitude NMEA (Unicore Extensions)

| Sentence | Description | Key Fields |
|----------|-------------|------------|
| **`$GPTHS2`** | True Heading and Status (Heading2 mode) | heading, status |
| **`$GPHPR`** | Attitude Parameters | heading, pitch, roll |
| **`$GPHPR2`** | Attitude (Heading2 mode) | heading, pitch, roll, status |
| **`$GPTRA2`** | Heading, Pitch & Roll (Heading2 mode) | heading, pitch, roll |
| **`$GPROT2`** | Rate of Turn (Heading2 mode) | rate of turn |
| **`$GPHPD`** | Positioning and Heading combined | position + heading + pitch |

---

## UNICORE PROPRIETARY DATA OUTPUT (ASCII Format)

These are the high-precision Unicore-format messages (ASCII header `#MSGNAME`):

### Navigation & Position

| Message | Description |
|---------|-------------|
| **`BESTNAV`** | Best position and velocity (RTK/DGPS/Single) with solution status |
| **`BESTNAVXYZ`** | Best position and velocity in ECEF coordinates |
| **`BESTNAVH`** | Best position and velocity for slave antenna |
| **`ADRNAV`** | RTK position and velocity |
| **`SPPNAV`** | Pseudorange (single-point) position and velocity |
| **`PPPNAV`** | PPP position and velocity |
| **`PVTSLN`** | Position and heading combined |
| **`KSXT`** | Compact positioning and heading (popular for autopilot integration) |
| **`MSPOS`** | Best position of dual antennas combined |

### Heading & Attitude

| Message | Description |
|---------|-------------|
| **`UNIHEADING`** | Heading information from dual-antenna (used by `signalk-um982-gnss` plugin) |
| **`UNIHEADING2`** | Heading for Heading2 (moving-base) mode |
| **`HEADINGSTATUS`** | Heading solution status detail |

### Observation & Raw Data

| Message | Description |
|---------|-------------|
| **`OBSVM`** | Raw observations from master antenna (pseudorange, carrier phase, Doppler) |
| **`OBSVH`** | Raw observations from slave antenna |
| **`OBSVMCMP`** | Compressed observations (master) |
| **`OBSVHCMP`** | Compressed observations (slave) |

### Status & Diagnostics

| Message | Description |
|---------|-------------|
| **`RTKSTATUS`** | RTK solution status (fix type, satellite count, baseline) |
| **`STADOP`** | DOP values for BESTNAV |
| **`BESTSAT`** | Satellites used in position solution |
| **`SATSINFO`** | Detailed satellite information |
| **`JAMSTATUS`** | RF jamming detection status |
| **`HWSTATUS`** | Hardware status and self-test |
| **`VERSION`** | Firmware and hardware version |
| **`RECTIME`** | Precise GNSS time information |
| **`TROPINFO`** | Zenith tropospheric delay |

### Midnight Rider — Active Messages

The `signalk-um982-gnss` plugin currently uses:

```
#UNIHEADING  → dual-antenna heading (heading, pitch, baseline, quality)
$GNGGA       → position (lat, lon, altitude, fix quality)
$GNRMC       → speed and course over ground
$GNVTG       → speed and course (redundant, for compatibility)
```

---

## CONFIGURATION — MIDNIGHT RIDER

### Physical Installation

| Parameter | Value |
|-----------|-------|
| **Antenna spacing** | 20 cm (minimum for heading function) |
| **Antenna axis** | Transverse (port–starboard, perpendicular to boat centerline) |
| **ANT1 (master)** | Position reference + heading origin point |
| **ANT2 (slave)** | Heading reference (ANT1→ANT2 defines 0° before offset correction) |
| **Serial port** | `/dev/ttyUSB0` |
| **Baud rate** | 115200, 8N1 |
| **Power supply** | 5V from RPi USB (regulated to 3.3V on carrier board) |

### Firmware Configuration (Permanent — Applied 2026-05-17)

The following commands were sent directly to the UM982 via `/dev/ttyUSB0`
and saved to NVRAM with SAVECONFIG:

```
UNLOGALL                  → Stop all NMEA output before config
HEADINGOFFSET 90          → Correct for transverse antenna mounting (+90° offset)
SAVECONFIG                → Persist to UM982 NVRAM (survives power cycles)
```

**Reason:** Antennas are mounted transversely (across beam, port–starboard axis).
The raw heading without correction is offset by +90°.
The `HEADINGOFFSET 90` command corrects this at firmware level before any data is transmitted.

> ⚠️ **PERMANENT CHANGE** — This is stored in UM982 NVRAM.
> Running `FRESET` would clear it. Do not run `FRESET` without Denis validation.
> Running `SAVECONFIG` with a different `HEADINGOFFSET` requires Denis validation.

### Current Firmware Configuration (Queried via `config` command)

```
$CONFIG,HEADING2,CONFIG HEADING2 FIXLENGTH
$CONFIG,HEADING,CONFIG HEADING FIXLENGTH
$CONFIG,UNDULATION,CONFIG UNDULATION AUTO
$CONFIG,DGPS,CONFIG DGPS TIMEOUT 300
$CONFIG,PPS,CONFIG PPS ENABLE GPS POSITIVE 500000 1000 0 0
$CONFIG,COM1,CONFIG COM1 115200
$CONFIG,COM2,CONFIG COM2 115200
$CONFIG,COM3,CONFIG COM3 115200
```

### Connection Diagram

```
UM982 (ANT1 + ANT2)
     ↓ USB-Serial (/dev/ttyUSB0)
RPi 4 (192.168.1.131)
     ↓ signalk-um982-gnss plugin (115200 baud)
Signal K (port 3000, systemctl)
     ↓
navigation.headingTrue / navigation.position / navigation.speedOverGround
     ↓
InfluxDB (port 8086, Docker) → Grafana (port 3001, Docker)
Signal K                     → N2K via YDNU-02 → Vulcan 7 FS
```

### Signal K Integration

| Parameter | Value |
|-----------|-------|
| **Plugin** | `signalk-um982-gnss` |
| **Signal K source name** | `signalk-um982-gnss.UM982-HDG` |
| **Plugin config file** | `plugin-config-data/signalk-um982-gnss.json` |
| **Physical connection** | USB serial (`/dev/ttyUSB0`) |

**Paths published to Signal K:**

```
navigation.position              {lat, lon}        — from $GNGGA
navigation.headingTrue           (radians, 0–2π)   — from #UNIHEADING (HEADINGOFFSET applied)
navigation.speedOverGround       (m/s)             — from $GNRMC / $GNVTG
navigation.courseOverGroundTrue  (radians, 0–2π)   — from $GNVTG
navigation.rateOfTurn            (rad/s)           — from #UNIHEADING dual-antenna data
```

> ⚠️ Signal K stores `headingTrue` in **radians**. Convert: degrees = radians × 180 / π
> Speed is stored in **m/s**. Convert to knots: × 1.94384

**Verified live data (2026-05-17):**

| Path | Value | Source |
|------|-------|--------|
| `navigation.headingTrue` | 171.3° (2.989 rad) | signalk-um982-gnss.UM982-HDG |
| Status | ✅ Live @ 1 Hz | — |

---

## RTK DOCUMENTATION

### Overview

The UM982 is a full RTK (Real-Time Kinematic) receiver. RTK uses differential corrections
from a nearby base station (sent as RTCM 3.x messages) to achieve centimeter-level
positioning accuracy (0.8 cm + 1 ppm horizontal).

**Current status on Midnight Rider:** RTK **not active**. Operating in Autonomous mode
(1.5 m horizontal accuracy). RTK could be added via NTRIP over internet or a local base station.

### RTK Operating Modes

| Mode | Command | Use Case |
|------|---------|---------|
| **Rover (default)** | `mode rover` | Receiving RTCM corrections from base station |
| **Base (fixed coord)** | `mode base lat lon height` | Acting as a fixed base station |
| **Base (self-survey)** | `mode base time 60` | Auto-surveying base position (60s average) |
| **Heading** | built-in (dual antenna) | No external RTK needed for heading |

### Fix Quality Levels (GNGGA Field 6)

| Value | Type | Accuracy |
|-------|------|---------|
| 1 | Single Point (Autonomous) | ~1.5 m |
| 2 | DGPS / SBAS | ~0.4 m |
| 4 | **RTK Fixed** | **~0.8 cm** ✅ |
| 5 | RTK Float | ~0.1–0.5 m |
| 6 | Dead Reckoning | — |

### RTK Rover Setup (NTRIP — Future Option)

To activate RTK via internet NTRIP corrections:

```bash
# 1. Set rover mode (default on UM982)
mode rover

# 2. Inject RTCM via str2str (RTKLIB) from RPi
str2str -in ntrip://user:pass@caster.example.com:2101/MOUNTPOINT \
        -out serial:///dev/ttyUSB0:115200

# 3. Monitor fix quality in Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/ | \
  jq '.position'
# Fix type 4 in GNGGA = RTK Fixed (centimeter level)
```

### RTK Base Station Setup (Local — Future Option)

To use a second UM982 as a local base station:

```bash
# On the base station receiver (connected to another RPi or PC):
mode base time 60          # Self-survey for 60 seconds
rtcm1006 com2 10           # Antenna reference point
rtcm1033 com2 10           # Receiver description
rtcm1074 com2 1            # GPS corrections
rtcm1084 com2 1            # GLONASS corrections
rtcm1094 com2 1            # Galileo corrections
rtcm1124 com2 1            # BeiDou corrections
saveconfig

# On the rover (Midnight Rider UM982):
# Pipe RTCM from base to /dev/ttyUSB0
# Fix type will change 1→5 (Float)→4 (Fixed) within 5-30s
```

### RTK Key Parameters

| Parameter | Value |
|-----------|-------|
| **RTK Timeout** | 600 s (default for UM982 — data older than 600s ignored) |
| **Initialization time** | < 5 s typical |
| **Initialization reliability** | > 99.9% |
| **RTK KEEP duration** | Up to 10 min without base data |
| **Baseline max (typical)** | 10–30 km (depends on atmospheric conditions) |
| **RTCM auto-detection** | ✅ Format auto-recognized |

### RTK Configuration Commands Reference

```
mode rover                         → Set rover mode
mode base lat lon height           → Fixed base with known coordinates
mode base time 60                  → Self-optimizing base (60s survey)
config rtk timeout 600             → Max age of RTK data (seconds)
config rtk reliability 3           → Relatively high reliability (default)
config rtk reset                   → Reset RTK solution
config standalone enable           → RTK KEEP mode (centimeter hold without base)
rtcm1006 com2 10                  → Output antenna coordinates (base only)
rtcm1074 com2 1                   → Output GPS RTCM MSM7 corrections (base only)
rtcm1084 com2 1                   → Output GLONASS RTCM MSM7 (base only)
rtcm1094 com2 1                   → Output Galileo RTCM MSM7 (base only)
rtcm1124 com2 1                   → Output BeiDou RTCM MSM7 (base only)
saveconfig                         → Save all configuration to NVRAM
freset                             → Factory reset (⚠️ CLEARS ALL CONFIG including HEADINGOFFSET)
```

---

## USEFUL COMMANDS REFERENCE

```bash
# Check UM982 firmware version
versiona
# Expected: #VERSIONA,...;"UM982","R4.10BuildXXXX",...

# Check current configuration
config

# Enable/disable specific NMEA messages
gngga 1           → GGA at 1 Hz
gnrmc 1           → RMC at 1 Hz
gngga 0.05        → GGA at 20 Hz
uniheading 1      → UNIHEADING at 1 Hz (heading data)
unlog gngga       → Disable GGA
unlog             → Disable all messages

# Monitor RTK status
rtkstatus 1       → RTK solution status at 1 Hz

# Check heading status
headingstatus 1   → Heading solution status at 1 Hz

# Antenna detection
antstat           → Antenna status for ANT1 and ANT2

# Enable SBAS (augmented accuracy ~0.4m without RTK base)
config sbas enable msas

# Signal group (default for UM982 = 4/5)
# To enable all bands:
config signalgroup 3 6
```

---

## PRE-RACE VERIFICATION

```bash
# 1. Verify device is detected
ls -la /dev/ttyUSB*
dmesg | grep -i usb | tail -20

# 2. Monitor raw NMEA output (check for valid fix)
cat /dev/ttyUSB0 | grep -E "RMC|GGA|UNIHEADING"
# GGA field 6 should show: 1 (autonomous) or 4 (RTK fixed)

# 3. Verify Signal K paths
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/ | jq '{
  position: .position,
  headingTrue: .headingTrue,
  sog: .speedOverGround,
  cog: .courseOverGroundTrue
}'

# 4. Expected values (at dock, boat pointing ~171°)
#   headingTrue : ~2.989 rad (171.3°)
#   position    : valid lat/lon (±1.5 m accuracy autonomous)
#   sog         : ~0 m/s at dock

# 5. Check Signal K source name
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/headingTrue | jq .
# Source should show: "signalk-um982-gnss.UM982-HDG"
```

---

## KNOWN ISSUES & FIXES

| Issue | Cause | Fix |
|-------|-------|-----|
| Device not found (`/dev/ttyUSB0`) | USB cable or driver | Check cable, try different USB port, `dmesg \| grep usb` |
| No heading output (0°) | No GPS fix or sky blocked | Wait cold start (30s), verify antennas have clear sky view |
| Heading jumps erratically | Antenna separation < 20 cm | Verify physical mounting, minimum 20 cm between ANT1 and ANT2 |
| **Heading offset by 90°** | **Antenna mounted transversely** | **✅ RESOLVED** — `HEADINGOFFSET 90` applied 2026-05-17 |
| Position drift | Cold start incomplete | Wait for ≥ 4 satellites, HDOP < 2.0 |
| Signal K source `null` | Plugin not running | `sudo systemctl restart signalk` |
| NMEA not outputting | Default state is silent | Send `gngga 1` etc. to enable messages |
| `FRESET` ran accidentally | Factory reset clears NVRAM | Re-apply `HEADINGOFFSET 90` + `SAVECONFIG` |

---

## CRITICAL NOTES

⚠️ **Heading vs COG:** UM982 outputs **TRUE HEADING** (from dual-antenna geometry),
NOT Course Over Ground (COG). Heading works even at anchor or at zero speed.

⚠️ **HEADINGOFFSET is NVRAM-permanent:** The 90° correction is stored in UM982 NVRAM.
`FRESET` would erase it and requires immediate reconfiguration.

⚠️ **Antenna axis:** The vector ANT1→ANT2 defines the "0° direction" before HEADINGOFFSET.
With antennas transverse (port–starboard), ANT1 port-side and ANT2 starboard-side
gives a natural 90° reference from bow — corrected by HEADINGOFFSET 90.

⚠️ **RTK not active:** Current mode is Autonomous (1.5 m). RTK activation requires
RTCM source (NTRIP or local base station). Heading precision is NOT affected by RTK status.

⚠️ **NMEA silent by default:** After power cycle, if no SAVECONFIG was run for NMEA
sentences, the module outputs nothing. The plugin handles this automatically.

⚠️ **Voltage:** The UM982 module runs at 3.0–3.6V. The carrier board accepts 5V and
includes a voltage regulator. Do not apply 5V directly to module pins.

---

## RACING ADVANTAGES

✅ **Dual-antenna true heading:** Independent of magnetic variation, works at anchor  
✅ **INSTANT HEADING technology:** No movement required for accurate heading  
✅ **Best-in-class precision:** 0.1° RMS @ 1 m baseline  
✅ **High update rate:** Up to 20 Hz capable (1 Hz currently configured)  
✅ **Multi-constellation tri-band:** GPS + Galileo + BeiDou + GLONASS + QZSS  
✅ **RTK-capable:** Path to centimeter accuracy (0.8 cm) if NTRIP or base added  
✅ **RTK KEEP:** Maintains cm accuracy 10 min after base station loss  
✅ **NMEA 0183 compatible:** Feeds legacy instruments via `signalk-to-nmea0183` plugin  

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial documentation | OC |
| 2026-05-17 | Applied `HEADINGOFFSET 90` (permanent firmware, SAVECONFIG) | OC |
| 2026-05-19 | Full datasheet revision: corrected specs, complete NMEA sentences table (standard + Unicore extensions), full RTK documentation, commands reference | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Next Action:** Validate heading 171.3° against compass bearing during field test

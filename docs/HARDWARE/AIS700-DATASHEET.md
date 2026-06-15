# B&G / RAYMARINE AIS700 — CLASS B TRANSCEIVER DATASHEET

**Manufacturer:** Navico (Raymarine brand — SKU: E70476)  
**Model:** AIS700 Class B SOTDMA Transceiver with built-in VHF splitter  
**AIS Class:** Class B (SOTDMA)  
**Date:** 2026-05-19  
**Status:** ✅ Installed — NMEA 2000 backbone, active

> ⚠️ **INSTRUMENT-INVENTORY.md mismatch:** Item #11 lists AIS transceiver as
> "Not Installed". This datasheet reflects actual current state confirmed by Denis.
> **INSTRUMENT-INVENTORY.md must be updated.**

> Note: The B&G AIS700 and Raymarine AIS700 are the same hardware (E70476)
> sold under different Navico brand names. All specs are identical.

---

## KEY FEATURES

- ✅ **Full Class B SOTDMA transceiver** — transmit AND receive
- ✅ **Built-in VHF antenna splitter** — shares existing VHF antenna
- ✅ **Dual receiver** — simultaneous monitoring of AIS channels 87 & 88
- ✅ **NMEA 2000 + NMEA 0183 + USB** — all major interfaces
- ✅ **Hardware + software Silent Mode** — privacy/security toggle
- ✅ **Built-in GNSS** (GPS + GLONASS, 72 channels)

---

## TECHNICAL SPECIFICATIONS

### AIS Performance

| Spec | Value |
|------|-------|
| **AIS Class** | Class B (SOTDMA) |
| **Transmit Power** | **5 W** |
| **Receivers** | 2× simultaneous (CH 87B + CH 88B) |
| **Transmitters** | 1× |
| **TX Frequency Range** | 156.0 – 162.025 MHz |
| **RX Frequency Range** | 156.0 – 174.0 MHz |
| **Channel Spacing** | 25 kHz |
| **Data Protocol** | ITU-R M.1371 (AIS Class B) |

### Built-in GNSS

| Spec | Value |
|------|-------|
| **Channels** | 72 |
| **Constellations** | GPS + GLONASS |
| **Cold Start** | 26 seconds nominal |
| **GNSS Antenna** | External passive (50Ω TNC — 10m cable supplied) |

### Power

| Spec | Value |
|------|-------|
| **Nominal Supply** | 12V DC / 24V DC |
| **Operating Range** | 9.6V DC to 31.2V DC |
| **Power Consumption** | < 3W (normal operation) |
| **Peak Current @ 12V** | 2.5A |
| **Peak Current @ 24V** | 1.25A |
| **Fuse Rating** | 3A |
| **LEN (NMEA 2000)** | **1 LEN** |

### Environmental

| Spec | Value |
|------|-------|
| **Operating Temperature** | -15°C to +55°C |
| **Storage Temperature** | -20°C to +75°C |
| **Humidity** | 93% @ 40°C |
| **Waterproof Rating** | IPx6 + IPx7 |
| **Compass Safe Distance** | ≥ 1 m (all directions) |
| **VHF antenna safe distance** | ≥ 1 m from GPS/AIS devices |

### Physical

| Spec | Value |
|------|-------|
| **Height** | 132.55 mm (5.22 in) |
| **Width** | 171.65 mm (4.81 in) |
| **Depth** | 57 mm (2.24 in) |
| **Weight** | Not specified in manual |
| **Mounting** | Panel/bulkhead (4× No.8×19 self-tapping screws) |

---

## CONNECTORS & INTERFACES

| Interface | Connector | Purpose |
|-----------|-----------|---------|
| **VHF Antenna** | SO-239 co-axial | Connect VHF antenna (156–174 MHz) |
| **VHF Radio** | SO-239 co-axial | Splitter output to VHF radio |
| **GNSS Antenna** | 50Ω TNC co-axial | External GNSS antenna (supplied) |
| **NMEA 2000** | 5-way DeviceNet Male | N2K backbone connection |
| **Power + NMEA 0183** | 12-way bare-ended wires | Power, 2× NMEA 0183 ports, Silent mode |
| **USB** | Micro-B | Configuration via proAIS2 software |
| **Ground** | M5 stud | RF ground — NOT battery negative |

### NMEA 0183 Ports (Power/Data Cable)

| Wire | Color | Function |
|------|-------|---------|
| HI OUT + | Brown | Port 1 TX+ (to MFD, 38400 baud) |
| HI OUT − | Blue | Port 1 TX− |
| HI IN + | White | Port 1 RX+ |
| HI IN − | Green | Port 1 RX− |
| LO OUT + | Purple | Port 2 TX+ (to instruments, 4800 baud) |
| LO OUT − | Pink | Port 2 TX− |
| LO IN + | Gray | Port 2 RX+ |
| LO IN − | Yellow | Port 2 RX− |
| + | Red | 12V / 24V DC |
| − | Black | Ground |
| Silent mode | Light Green | Silent mode switch (short to Orange = Silent) |
| Silent mode | Orange | Silent mode switch return |

---

## AIS DATA — CLASS B TRANSMIT INTERVALS

| Vessel Speed | Reporting Rate |
|-------------|---------------|
| 0 – 2 knots | **3 minutes** |
| 2 – 14 knots | **30 seconds** |
| 14 – 23 knots | **15 seconds** |
| > 23 knots | **5 seconds** |

Static data (vessel name, MMSI, dimensions) is broadcast every **6 minutes** or on request.

### Data Transmitted (Class B)

| Data Field | Transmitted |
|-----------|------------|
| Ship's name | ✅ |
| Vessel type | ✅ |
| Call sign | ✅ |
| Length & beam | ✅ |
| GNSS antenna location | ✅ |
| Time (UTC) | ✅ |
| Position (lat/lon) | ✅ |
| COG | ✅ |
| SOG | ✅ |
| Gyro heading | ✅ (if NMEA HDT sentence received) |
| IMO number | ❌ Class B limitation |
| Draft | ❌ Class B limitation |
| Destination / ETA | ❌ Class B limitation |
| Rate of turn | ❌ Class B limitation |
| Navigational status | ❌ Class B limitation |

---

## NMEA 0183 SENTENCES

### Transmitted

| Sentence | Description |
|----------|-------------|
| `ABK` | ABM/BBM acknowledgement |
| `THS` | True heading and status |
| `VDM` | AIS VHF data-link message (received AIS targets) |
| `VDO` | AIS VHF data-link own-vessel report |
| `TXT` | Text |

### Received

| Sentence | Description |
|----------|-------------|
| `ABM` | Addressed binary message |
| `ACA` | AIS channel management assignment |
| `ACS` | AIS channel management information source |
| `AIQ` | AIS query |
| `ACK` | Acknowledge alarm |
| `BBM` | Broadcast binary message |
| `HDT` | **Heading true** ← feeds transmitted heading in AIS position reports |
| `RST` | Equipment reset command |
| `SSD` | Ship static data |
| `THS` | True heading and status |
| `TXT` | Text |
| `VSD` | Voyage static data |

---

## NMEA 2000 PGNs

### Transmitted (AIS700 → N2K bus)

| PGN | Name |
|-----|------|
| 59392 | ISO Acknowledgement |
| 59904 | ISO Request |
| 60928 | ISO Address Claim |
| 65240 | ISO Commanded Address |
| 126208 | Request Group Function |
| **126992** | **System Time** |
| 126993 | Heartbeat |
| **126996** | **Product Information** |
| **127250** | **Vessel Heading** (received from external source, re-broadcast) |
| **129025** | **Position, Rapid Update** (own vessel, from built-in GNSS) |
| **129026** | **COG & SOG, Rapid Update** (own vessel) |
| **129029** | **GNSS Position Data** (own vessel) |
| **129038** | **AIS Class A Position Report** (received targets) |
| **129039** | **AIS Class B Position Report** (received targets) |
| **129040** | **AIS Class B Extended Position Report** (received targets) |
| **129041** | **AIS AToN Report** (aids to navigation) |
| **129793** | **AIS UTC and Date Report** |
| **129794** | **AIS Class A Static and Voyage Related Data** |
| 129795 | AIS Addressed Binary Message |
| 129796 | AIS Acknowledge |
| 129797 | AIS Binary Broadcast Message |
| **129798** | **AIS SAR Aircraft Position Report** |
| **129801** | **AIS Addressed Safety Related Message** |
| **129802** | **AIS Safety Related Broadcast Message** |
| **129809** | **AIS Class B CS Static Data Report Part A** |
| **129810** | **AIS Class B CS Static Data Report Part B** |

### Received (N2K bus → AIS700)

| PGN | Name | Purpose |
|-----|------|---------|
| 59392 | ISO Acknowledgement | Network service |
| 59904 | ISO Request | Network service |
| 60928 | ISO Address Claim | Address management |
| 65240 | ISO Commanded Address | Network service |
| 126208 | Request Group Function | Network service |
| 126996 | Product Information | Device ID |

> ⚠️ **Connection rule:** Do NOT connect the AIS700 to a device using BOTH
> NMEA 0183 AND NMEA 2000 simultaneously — data loops will occur.
> On Midnight Rider: **use NMEA 2000 only** (no NMEA 0183 to Vulcan 7 FS).

---

## SILENT MODE

Silent mode stops all AIS transmissions. The AIS700 continues to receive.

| Method | How |
--------|-----|
| **MFD (Vulcan 7)** | Vulcan 7 → Settings → AIS → Silent Mode ON/OFF |
| **Hardware switch** | Short Light Green + Orange wires on power cable |
| **LED indicator** | 🔵 Blue LED = Silent mode active |

> ⚠️ The hardware switch **overrides** the MFD setting.
> Racing context: Silent mode when not wanting to be tracked by competitors.
> Legal note: AIS Class B transmit is not legally mandatory for recreational vessels.

---

## MMSI CONFIGURATION

> ⚠️ **CRITICAL:** The MMSI number can only be entered ONCE.
> If entered incorrectly, a Raymarine dealer must re-programme the unit.

**Required before first use:**
1. Obtain MMSI for Midnight Rider (if not already assigned)
2. Configure via proAIS2 software (USB Micro-B connection to PC)
3. Enter: MMSI, vessel name, call sign, dimensions, GNSS antenna location, vessel type

**Canada:** MMSI from Innovation, Science and Economic Development Canada (ISED) :cite[cx6]

**Vessel static data to configure:**
- MMSI: [configured — do not document here]
- Vessel Name: MIDNIGHT RIDER
- Call Sign: [operator's call sign]
- Vessel Type: Sailing vessel (36)
- Length / Beam: J/30 dimensions (9.07m / 3.05m)
- GNSS Antenna Location: forward offset from bow center

---

## MIDNIGHT RIDER INTEGRATION

### Architecture

```
AIS700 (below deck)
     ├─ GNSS Antenna (external, pole-mounted)
     ├─ VHF Antenna → splitter → (shared with VHF radio if installed)
     │
     ↓ NMEA 2000 DeviceNet Male → T-connector
NMEA 2000 backbone (12V from SOK LiFePO4)
     ├─ Vulcan 7 FS ← PGNs 129038/39/40/41 (AIS targets on chart)
     └─ YDNU-02 → Signal K (port 3000)
                      ↓
                vessels.* namespace (AIS targets)
                      ↓
              InfluxDB (port 8086) → Grafana Dashboard
```

### N2K Bus Load (Updated)

| Device | LEN | Status |
|--------|-----|--------|
| YDNU-02 Gateway | 1 | ✅ Active |
| Vulcan 7 FS | 1 | ✅ Active |
| B&G WS320 Base Station | 2 | ✅ Active |
| YDBC-05 Barometer | 1 | ✅ Active |
| **AIS700** | **1** | ✅ Active |
| **Total** | **6 / 50 max** | ✅ Well within limits |

### Signal K AIS Integration

AIS target data received by YDNU-02 from the N2K bus is mapped to:

```
vessels.<MMSI>
  ├─ name                     ← vessel name
  ├─ mmsi                     ← MMSI number
  ├─ navigation.position      ← {lat, lon} of target
  ├─ navigation.courseOverGroundTrue  ← COG
  ├─ navigation.speedOverGround       ← SOG
  ├─ navigation.headingTrue           ← heading (if transmitted)
  ├─ communication.callsignVhf        ← VHF call sign
  └─ design.aisShipType               ← vessel type
```

**Verification:**

```bash
# List all AIS targets in Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/ | jq 'keys'
# Expected: ["self", "<MMSI_target_1>", "<MMSI_target_2>", ...]

# Get position of specific target
curl -s http://localhost:3000/signalk/v1/api/vessels/<MMSI>/ | \
  jq '{name: .name, position: .navigation.position.value}'
```

---

## LED INDICATORS

| LED Color | Status |
|-----------|--------|
| 🟢 **Green** | Operating normally — has transmitted at least 1 position report |
| 🟡 **Amber** | Not transmitting (no MMSI configured, quiet time, or antenna issue) |
| 🔴 **Red** | Fault — check MMSI, GNSS antenna, VHF antenna, power supply |
| 🔵 **Blue** | **Silent mode active** — receiving only, not transmitting |

---

## PRE-DEPARTURE VERIFICATION

```bash
# 1. Check AIS700 in Vulcan 7 Device List
# Settings → Network → Device List → "AIS700" should appear

# 2. Confirm Green LED on unit
# Green = operating + transmitting

# 3. Verify AIS targets visible on Vulcan 7 chart
# At least 1-2 targets visible in marina/anchorage area

# 4. Confirm Signal K receives AIS data
curl -s http://localhost:3000/signalk/v1/api/vessels/ | jq 'keys | length'
# Expected: ≥ 2 (self + at least 1 AIS target)

# 5. Check own vessel AIS position (from AIS700 GNSS)
curl -s http://localhost:3000/signalk/v1/api/vessels/self/ | \
  jq '.navigation.position.value'
# Expected: lat/lon matching actual position

# 6. Verify CPA/TCPA alerts on Vulcan
# Settings → AIS → CPA Alarm: recommended 0.5 nm
# Settings → AIS → TCPA Alarm: recommended 10 min
```

---

## KNOWN ISSUES & FIXES

| Issue | Cause | Fix |
|-------|-------|-----|
| Red LED | MMSI not configured | Configure via proAIS2 + USB |
| Red LED | GNSS antenna disconnected | Check TNC connector on unit |
| Red LED | VHF antenna issue | Check SO-239 connector, antenna VSWR |
| Amber LED | No MMSI entered | Configure MMSI, unit operates as receive-only |
| Blue LED | Silent mode active | Toggle via Vulcan 7 or check hardware switch wiring |
| No AIS on Vulcan | N2K connection issue | Check DeviceNet connector, verify YDNU-02 also sees AIS data |
| No AIS in Signal K | YDNU-02 filter blocking AIS PGNs | Check YDNU-02 global_rx filter |
| Erratic heading in AIS | No HDT sentence input | Connect NMEA 0183 from UM982 to AIS Port 2 OR rely on GNSS-derived COG |
| Data conflict | N2K + 0183 to same device | Use ONLY N2K on Midnight Rider |

---

## SAFETY & REGULATORY NOTES

⚠️ **AIS is NOT a substitute for radar.** AIS only detects vessels that are:
- Equipped with AIS transceivers
- Actively transmitting (not in silent mode)

⚠️ **NOT all vessels have AIS.** Small boats, fishing vessels, and vessels in silent mode will not appear.

⚠️ **MMSI cannot be changed** once programmed without dealer re-flashing.

⚠️ **Do NOT install near fuel tanks or engine room** — AIS700 is a radio transmitter (potential ignition source).

⚠️ **VHF antenna** must have VSWR ≤ 2:1 and 50Ω impedance. Mismatched antenna reduces range and may damage transmitter.

✅ **Class B SOTDMA** provides longer range and fewer collisions than CSTDMA — racing context: targets detected further out.

---

## SAILING / RACING ADVANTAGES

✅ **Collision avoidance:** Real-time traffic on Vulcan 7 chart at any time of day/night  
✅ **Race safety:** Identify committee boats, mark boats, ferries crossing course  
✅ **Offshore:** Night sailing identification of ships and ferries (Block Island Race)  
✅ **Own vessel visible:** Other ships see Midnight Rider on their AIS — especially important near shipping lanes  
✅ **Silent mode:** Optional for tactical racing (no transmission = not tracked by competitors)  
✅ **Signal K integration:** AIS targets logged to InfluxDB, available for post-race analysis  

---

## CONFIGURATION REFERENCE (proAIS2)

Software: **proAIS2** (free, Raymarine) — Windows/Mac  
Connection: USB Micro-B cable to PC (before or after installation)

Key settings to verify:
- [ ] MMSI: [configured]
- [ ] Vessel Name: MIDNIGHT RIDER
- [ ] Vessel Type: 36 (Sailing vessel)
- [ ] GGA/GLL/RMC output: **DISABLED** (to avoid data conflicts)
- [ ] NMEA 0183 Port 1 baud: 38400 (if used for 0183 MFD connection)
- [ ] NMEA 0183 Port 2 baud: 4800 (if used for instruments)
- [ ] Silent Mode: OFF (default operating)

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-05-19 | Initial creation — unit confirmed installed on N2K backbone (not reflected in INSTRUMENT-INVENTORY.md) | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Installed & Operational  
**File:** `docs/HARDWARE/AIS700-TRANSCEIVER-DATASHEET.md`  
**Next Actions:**
1. Update `INSTRUMENT-INVENTORY.md` — move AIS from "Not Installed" → "Active"
2. Verify Green LED and AIS targets visible on Vulcan 7
3. Confirm MMSI configured correctly (proAIS2 → Connect → read vessel data)
4. Set CPA alarm on Vulcan 7 (0.5 nm / 10 min recommended)

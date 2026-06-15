# N2K Network Architecture — SSOT (Single Source of Truth)

**Version:** 1.0  
**Date:** 2026-06-15  
**Status:** ✅ CANONICAL REFERENCE  
**Maintained by:** OC (OpenClaw)

> This document is the authoritative reference for NMEA 2000 bus topology,
> LEN (Linear Extended Network) budget, and PGN (Parameter Group Number) flow.
> 
> ⚠️ Per-device specifications remain in `docs/HARDWARE/*.md`  
> Per-device integration remains in `docs/INTEGRATION/*.md`

---

## 1. Network Topology

### Physical Layout

```
Yacht Devices YDNU-02 (USB ↔ N2K Bridge)
│
├─────────────────────────────────────────────────────────────────
│                        N2K Backbone (250 kbps)                 │
│                                                                 │
├──T─ Port Vulcan 7 FS (Chartplotter)
│
├──T─ Starboard Vulcan 7 FS (Chartplotter)
│
├──T─ B&G WS320 Base Station (Anemometer TX)
│
├──T─ Yacht Devices YDBC-05 (Barometer)
│
├──T─ B&G AIS700 Class B (AIS Transceiver)
│
└──T─ [End terminator]

[T] = T-connector with 120Ω terminator at both ends
```

### Device Roles on Bus

| Device | Role | PGNs Transmitted | PGNs Received |
|--------|------|-----------------|---|
| **YDNU-02** | Bridge (USB ↔ N2K) | 127250, 127257, 130306, 130314, 130824† | All N2K PGNs |
| **Vulcan 7 FS (×2)** | Chartplotter (Helm + Nav) | 129025, 129026 (GPS) | All except own GPS |
| **WS320 Base** | Wind transmitter | 130306 (Wind) @ 5 Hz | — |
| **YDBC-05** | Barometer | 130310, 130311, 130314 (Pressure) | — |
| **AIS700** | AIS transceiver | 129038–129810 (Targets) | 129794 (AIS broadcast) |

† PGN 130824 (Performance data) — emitted by YDNU-02 from Signal K (via P5 plugin, pending activation)

---

## 2. LEN Budget

### Linear Extended Network Capacity

```
Total backbone capacity: 50 LEN units max
```

### Current Allocation

| Device | LEN | Justification |
|--------|-----|---|
| Yacht Devices YDNU-02 | 1 | Gateway = 1 unit |
| B&G Vulcan 7 FS (PORT) | 1 | Chartplotter = 1 unit |
| B&G Vulcan 7 FS (STBD) | 1 | Chartplotter = 1 unit |
| B&G WS320 Base Station | 2 | Wireless wind base = 2 units |
| Yacht Devices YDBC-05 | 1 | Barometer = 1 unit |
| B&G AIS700 Class B | 1 | AIS transceiver = 1 unit |
| **TOTAL** | **7 / 50** | **14% of capacity** |

✅ **Well within limits.** No congestion risk.

---

## 3. PGN Flow Matrix

### Data Flow Direction

```
Signal K ────────────────── YDNU-02 ──────────────── N2K Backbone
(Raspberry Pi)             (USB gateway)              (Vessel network)
     │                           │                            │
     ├─ P5 plugin converts:       │                            │
     │  • 127250 (Heading)        │                            ├── Vulcan 7 FS (×2)
     │  • 127257 (Attitude)       │                            ├── WS320 Base
     │  • 130306 (Wind)           │                            ├── YDBC-05
     │  • 130314 (Pressure) †     │                            └── AIS700
     │  • 130824 (Performance) †  │
     │                            │ Transmits to:
     └─ Calypso UP10 (BLE)        │   N2K devices receive
        sends ────────────────────┘
        environment.wind.* (Calypso UDP:4123)
```

### PGN Specifications

#### Heading (PGN 127250)

| Field | Source | Value | Note |
|-------|--------|-------|------|
| Heading (radians) | UM982 via `signalk-um982-gnss` | navigation.headingTrue | Dual-antenna GPS (±0.5°) |
| Magnetic variation | Signal K local offset | 0 rad (North Sea) | Set in Settings |
| **TX Device** | **YDNU-02** | **Frequency: 1 Hz** | From `signalk-n2k-bridge` (P5) |
| **RX Devices** | Vulcan 7 FS (×2) | Display heading | Backup GPS + chartplotter display |

#### Attitude (PGN 127257)

| Field | Source | Value | Note |
|-------|--------|-------|------|
| Pitch (radians) | WIT WT901BLECL via `signalk-wit-imu-ble` | navigation.attitude.pitch | 10 Hz BLE sensor |
| Roll (radians) | WIT WT901BLECL | navigation.attitude.roll | Corrected for mount (2026-05-17) |
| Yaw / Heading (radians) | WIT IMU | navigation.attitude.yaw | Low accuracy; use PGN 127250 for heading |
| **TX Device** | **YDNU-02** | **Frequency: 10 Hz** | From P5 (patched 2026-05-17) |
| **RX Devices** | Vulcan 7 FS (×2), B&G WS320 base | Real-time heel display | Critical for sail trim |

#### Wind Data (PGN 130306)

| Field | Source TX | Source RX | Frequency |
|-------|-----------|-----------|-----------|
| **Apparent Wind Speed (AWS)** | B&G WS320 base (primary) | Vulcan 7 FS | 5 Hz |
| **Apparent Wind Angle (AWA)** | B&G WS320 base | Vulcan 7 FS | 5 Hz |
| (True Wind Speed/Dir calculated by Vulcan) | Vulcan 7 internal | Vulcan 7 display | 1 Hz |
| **Signal K**: environment.wind.* | Calypso UP10 (UDP:4123, higher priority) | — | 1 Hz |

**Source Priority in Signal K:**
1. Calypso UP10 (BLE, 1 Hz) — primary
2. WS320 (N2K, 5 Hz via YDNU-02) — secondary

#### Atmospheric Pressure (PGN 130314)

| Field | Source | Frequency | Display |
|-------|--------|-----------|---------|
| Barometric pressure (Pa) | Yacht Devices YDBC-05 | 0.5 Hz | Vulcan 7 FS environment page |
| Signal K path | environment.outside.pressure | — | Grafana 02-Environment |

#### Performance Data (PGN 130824) — B&G Proprietary

| Field | Source | Status | Frequency |
|-------|--------|--------|-----------|
| **Sequence ID** | Calypso UP10 | Placeholder | 1 Hz |
| **Leeway angle** | signalk-j30-leeway (P2) | Via P5 | On request |
| **Beat angle** | signalk-performance-polars | Via P5 | On request |
| **Target angle** | Calculated from polars | Via P5 | On request |
| **Performance ratio (VMG %)** | signalk-performance-polars | Via P5 | On request |
| **Wind shift** | Estimated from time-series | Via P5 | On request |
| **Current set/drift** | signalk-current-calculator (P3) | Via P5 | 1 Hz |

**Status:** Pending P5 activation. See `plugins/signalk-n2k-bridge.js` (v1.0.0).

#### AIS Targets (PGNs 129038–129810)

| Message | Source | Content | Display |
|---------|--------|---------|---------|
| **PGN 129038** | AIS700 (SOTDMA) | Type 1–3 position report | Vulcan 7 FS radar screen |
| **PGN 129039** | AIS700 | Type 4 base station report | Safety alert (if in range) |
| **PGN 129794** | AIS700 | Own vessel AIS broadcast | Other vessels hear us @ 2 min interval |
| **PGN 129810** | AIS700 | Text string (safety data) | Safety messages |

---

## 4. Device Integration Matrix

### Signal K ↔ N2K Mapping

| Signal K Path | Type | PGN | Device TX | Device RX | Frequency |
|---------------|------|-----|-----------|-----------|-----------|
| navigation.headingTrue | Input | 127250 | YDNU-02 (P5) | Vulcan 7 FS ×2 | 1 Hz |
| navigation.attitude.roll | Input | 127257 | YDNU-02 (P5) | Vulcan 7 FS ×2 | 10 Hz |
| navigation.attitude.pitch | Input | 127257 | YDNU-02 (P5) | Vulcan 7 FS ×2 | 10 Hz |
| environment.wind.speedApparent | Output | 130306 | WS320 (N2K) | Vulcan 7 FS ×2 | 5 Hz |
| environment.wind.angleApparent | Output | 130306 | WS320 (N2K) | Vulcan 7 FS ×2 | 5 Hz |
| environment.outside.pressure | Output | 130314 | YDBC-05 (N2K) | Vulcan 7 FS ×2 | 0.5 Hz |
| vessels.* (AIS targets) | Output | 129038–129810 | AIS700 (N2K) | Vulcan 7 FS ×2 | event-driven |
| performance.leewayAngle | Input (P5 pending) | 130824 | YDNU-02 (P5) | Vulcan 7 FS ×2 | on request |

---

## 5. Failure Modes & Redundancy

### Single Points of Failure

| Component | Impact if Down | Mitigation |
|-----------|----------------|-----------|
| **YDNU-02 Gateway** | No N2K ↔ SK bridge | Manual N2K read via dedicated N2K display tool |
| **UM982 GPS** | No true heading (magnetic compass not aboard) | Rely on Vulcan 7 internal GPS |
| **WIT IMU** | No attitude (heel/pitch) data | Vulcan 7 inclinometer (less accurate) |
| **Calypso UP10** | Wind data from WS320 only (5 Hz vs 1 Hz) | Performance degraded but functional |

### Recommended Backups (Future)

- **Speed through water (STW):** Install ultrasonic log on N2K bus
- **Depth sounder:** Install transducer + gauge on N2K
- **Magnetic compass:** Emergency navigation backup

---

## 6. Troubleshooting N2K Issues

### Symptom: YDNU-02 Not Seen

```bash
# Check USB enumeration
lsusb | grep "VID:PID 0483:a217"
# Expected: Yacht Devices YDNU-02

# Check udev assignment
ls -la /dev/ttyACM*
# Expected: /dev/ttyACM0 → YDNU-02

# Test serial connectivity
cat /dev/ttyACM0 | xxd | head -20
# Should see N2K frames (hex bytes)
```

### Symptom: Vulcan 7 FS Shows "NO WIND"

```
Possible causes:
  1. WS320 Base Station offline (check power, BLE range)
  2. YDNU-02 not forwarding PGN 130306
  3. N2K cable disconnect or T-connector issue
  4. Vulcan FS configuration filter (check N2K device config)

Action:
  → Check YDNU-02 LED status (should be green, not red)
  → Check WS320 power indicator
  → Test N2K cable continuity at T-connector
```

### Symptom: Attitude (Roll/Pitch) Not on Vulcan 7

```
Possible causes:
  1. WIT IMU offline or not sending data
  2. YDNU-02 not forwarding PGN 127257
  3. Vulcan FS attitude display disabled in settings
  4. P5 plugin not emitting PGN 127257 (check signalk-n2k-bridge config)

Action:
  → Verify WIT IMU connected: curl http://localhost:3000/signalk/v1/api/ | jq '.attitude'
  → Check YDNU-02: dmesg | grep "ttyACM"
  → Verify P5 enabled in SK settings: grep "signalk-n2k-bridge" ~/.signalk/settings.json
```

---

## 7. Configuration Files

### YDNU-02 Serial Configuration

```bash
# Device: /dev/ttyACM0
# Baud: N/A (USB native)
# Data bits: N/A (USB)
# Stop bits: N/A (USB)
# Parity: N/A (USB)

# Vendor ID / Product ID: 0483:a217 (STMicroelectronics / Yacht Devices)
```

### Signal K Plugin Configuration (P5)

**File:** `~/.signalk/plugin-config-data/signalk-n2k-bridge.json`

```json
{
  "enabled": true,
  "bandgPerformance": {
    "enabled": true,
    "sourceLeeway": "sources.performance.leewayAngle",
    "sourceCurrentSet": "sources.environment.current.setTrue",
    "sourceCurrentDrift": "sources.environment.current.driftSpeed",
    "sourceBeatAngle": "sources.performance.beatAngle",
    "sourceTargetAngle": "sources.performance.targetAngle",
    "sourceVMG": "sources.performance.velocityMadeGood"
  },
  "pgn130833": {
    "enabled": false
  }
}
```

---

## 8. References

### Related Documents

- **Hardware specs:** `docs/HARDWARE/` (device datasheets)
- **Integration guides:** `docs/INTEGRATION/` (per-device setup)
- **Architecture:** `docs/ARCHITECTURE-MASTER.md` (system overview)
- **Signal K plugins:** `plugins/PLUGIN-DEVELOPMENT-GUIDE.md`

### External Standards

- **NMEA 2000 Standard:** IEC 61162-2 (proprietary spec)
- **PGN Definitions:** B&G/Yacht Devices vendor documentation
- **LEN Budget:** N2K topology specification (50 units max)

---

**Last updated:** 2026-06-15 by OC  
**Next review:** After P5 activation (performance data)  
**Authorized by:** Denis LAFARGE

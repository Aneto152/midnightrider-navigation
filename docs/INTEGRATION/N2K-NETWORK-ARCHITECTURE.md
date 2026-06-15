# Midnight Rider — N2K Network Architecture (SSOT)

**Version:** 1.0  
**Date:** 2026-06-15  
**Status:** ✅ CANONICAL REFERENCE — Bus topology, LEN budget, system PGN flow  

> 📌 **Single Source of Truth for system-level N2K design.**
> Per-device specs (voltage, refresh rates, PGN formats) → `docs/HARDWARE/`  
> Per-device setup procedures → `docs/INTEGRATION/`

---

## 1. Network Topology

```
YDNU-02 (USB ↔ N2K Bridge) ──T── /dev/ttyACM0 (RPi4 Signal K)
│
├──T── WS320 Base Station (Wireless wind TX) — LEN 2
├──T── Vulcan 7 FS (PORT helm) — LEN 1
├──T── Vulcan 7 FS (STBD nav) — LEN 1
├──T── YDBC-05 (Barometer) — LEN 1
├──T── AIS700 (Class B AIS) — LEN 1
└──T── [End terminator, 120Ω]

[T] = T-connector with 120Ω terminators at both physical ends
Backbone: Micro-C connector, 250 kbps
```

---

## 2. LEN Budget

| Device | LEN | Datasheet | Role |
|--------|-----|-----------|------|
| YDNU-02 Gateway | 1 | YDNU-02-DATASHEET.md | USB ↔ N2K bridge |
| Vulcan 7 FS (PORT) | 1 | VULCAN-7-FS-DATASHEET.md | Helm chartplotter |
| Vulcan 7 FS (STBD) | 1 | VULCAN-7-FS-DATASHEET.md | Nav chartplotter |
| WS320 Base Station | 2 | BG-WS320-DATASHEET.md | Wind TX (wireless) |
| YDBC-05 Barometer | 1 | YDBC-05-DATASHEET.md | Pressure sensor |
| AIS700 Class B | 1 | AIS700-DATASHEET.md | AIS transponder |
| **TOTAL** | **7 / 50** | — | **14% capacity** ✅ |

**Available future slots:** +43 LEN units for STW/log, depth sounder, VHF DSC

---

## 3. System PGN Flow

### Received from N2K Bus → Signal K (via YDNU-02)

| Source Device | PGN | Data | SK Path | Frequency |
|---|---|---|---|---|
| WS320 | 130306 | Apparent wind (AWS/AWA) | environment.wind.* | 5 Hz |
| WS320 | 130311 | Air temperature (masthead) | environment.outside.temperature | 0.2 Hz |
| YDBC-05 | 130314 | Atmospheric pressure | environment.outside.pressure | 0.5 Hz |
| AIS700 | 129038–129810 | AIS targets (MMSI, position, COG, SOG) | vessels.* | event-driven |
| Vulcan 7 FS | 129025, 129026 | GPS position + COG/SOG (secondary fallback) | navigation.* | 1 Hz |

### Transmitted from Signal K → N2K (via P5 plugin → YDNU-02)

| Destination | PGN | Data | SK Source | Frequency |
|---|---|---|---|---|
| Vulcan 7 FS (×2) | 127250 | True heading | P1: UM982 GPS (dual-antenna) | 1 Hz |
| Vulcan 7 FS (×2) | 127257 | Roll, pitch, yaw | WIT IMU via BLE | 10 Hz |
| Vulcan 7 FS (×2) | 129025 | GNSS position | P1: UM982 GPS | 1 Hz |
| Vulcan 7 FS (×2) | 129026 | COG + SOG | P1: UM982 GPS | 1 Hz |
| (Optional) Vulcan 7 FS (×2) | 130306 | Wind (true/apparent) | Calypso UP10 (via Plugins) | 1 Hz |
| (Pending) Vulcan 7 FS (×2) | 130824 | B&G Performance (leeway, VMG, beat angle) | P5: signalk-n2k-bridge | On request |

### Direct N2K (No Signal K Involvement)

| From | To | PGN | Data | Why Direct |
|---|---|---|---|---|
| WS320 Base | Vulcan 7 FS (×2) | 130306 | Apparent wind | Real-time sail trim display (5 Hz, critical latency) |
| AIS700 | Vulcan 7 FS (×2) | 129038–129810 | AIS targets | Safety-critical vessel tracking |

---

## 4. YDNU-02 Bridge Configuration

### Serial Connection

| Parameter | Value |
|-----------|-------|
| Device Path | `/dev/ttyACM0` (CDC ACM, **not ttyUSB0**) |
| Vendor ID | 0x0483 (STMicroelectronics) |
| Product ID | 0xA217 (Yacht Devices YDNU-02) |
| Baud Rate | 250,000 bps (native N2K) |
| Data Bits | 8 (N2K standard) |
| Stop Bits | 1 |
| Parity | None |
| Direction | Bidirectional |

### Verification

```bash
# Check enumeration
lsusb | grep "0483:a217"

# Check udev assignment
ls -la /dev/ttyACM0

# Read raw N2K traffic
cat /dev/ttyACM0 | xxd | head -20
# Expected: Periodic hex frames (N2K CAN bus data)
```

### Signal K Plugin

| Setting | Value |
|---------|-------|
| Plugin | `@signalk/signalk-to-nmea2000` |
| Config file | `~/.signalk/plugin-config-data/signalk-to-nmea2000.json` |
| Status (June 15) | Enabled, but 0 mappings configured (P5 pending) |

---

## 5. Data Source Priorities (Signal K)

### Wind Heading

| Priority | Source | Protocol | Frequency | Path |
|----------|--------|----------|-----------|------|
| 1 (primary) | Calypso UP10 (`calypso-up10`) | BLE → UDP:4123 | 4 Hz | environment.wind.* |
| 2 (fallback) | WS320 (`nmea2000_ws320`) | N2K via YDNU-02 | 5 Hz | environment.wind.* |

> **Note:** WS320 also feeds Vulcan 7 FS **directly** at 5 Hz via N2K backbone,
> independent of Signal K (for real-time sail trim).

### Attitude (Roll/Pitch/Yaw)

| Priority | Source | Protocol | Frequency | Path |
|----------|--------|----------|-----------|------|
| 1 (primary) | WIT IMU (`wit-ble-direct`) | BLE | 10 Hz | navigation.attitude.* |
| 2 (fallback) | Calypso compass mode | BLE | — | (if enabled) |

---

## 6. Instruments NOT on N2K Bus

| Instrument | Protocol | Device Path | Role |
|---|---|---|---|
| UM982 GNSS + Heading | USB serial | `/dev/ttyUSB0` | Primary GPS + dual-antenna heading |
| WIT WT901BLECL IMU | Bluetooth LE | `hci0` | Roll, pitch, acceleration (10 Hz) |
| Calypso UP10 | Bluetooth LE | `hci0` | Masthead wind (BLE → UDP:4123) |
| SOK BMS | Bluetooth LE | `hci0` | Battery monitoring (direct InfluxDB, bypass SK) |

---

## 7. Future Expansion Slots

| Instrument | PGN | LEN | Notes |
|---|---|---|---|
| Speed through water (STW) | 128259 | 1–2 | Requires ultrasonic/paddlewheel log on hull |
| Depth sounder | 128267 | 1–2 | Requires transducer on hull |
| VHF Radio DSC | Various | 2–3 | Future safety equipment |

---

## 8. Failure Modes & Mitigation

| Component | If Down | Mitigation |
|---|---|---|
| **YDNU-02** | No N2K ↔ SK bridge | Manual N2K display via dedicated reader tool |
| **WS320 Base** | Wind data from Calypso only (1 Hz vs 5 Hz) | Performance degraded but functional |
| **YDBC-05** | No pressure data | Non-critical (Vulcan has internal barometer) |
| **AIS700** | No AIS on Vulcan | Non-critical (backup AIS on Vulcan internal radio) |
| **UM982 GPS** | No true heading (no magnetic compass) | Rely on Vulcan 7 internal GPS (lower accuracy) |

---

## 9. Troubleshooting N2K Issues

### Symptom: "YDNU-02 Not Found"

```bash
# Check USB enumeration
lsusb | grep "VID:PID 0483:a217"

# Check device path
ls -la /dev/ttyACM*
# Expected: /dev/ttyACM0 → YDNU-02

# If missing, replug USB cable and repeat
```

### Symptom: Vulcan 7 FS Shows "NO WIND"

```bash
# Check YDNU-02 LED status (should be green, not red)
# Check WS320 power indicator (should be on)
# Test N2K cable continuity at T-connector (visual inspection)

# In Signal K, verify wind source is active:
curl http://localhost:3000/signalk/v1/api/vessels/self/environment/wind

# If missing, check WS320 battery level
```

### Symptom: Heading / Attitude Not on Vulcan 7

```bash
# Verify WIT IMU connected:
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# Verify P5 plugin enabled:
grep "signalk-n2k-bridge" ~/.signalk/settings.json

# Check YDNU-02 LED (green = healthy, red = fault)
```

### Symptom: "SILENT MODE" (Yellow LED Solid)

```bash
# N2K bus fault (usually termination issue)

# Exit SILENT MODE:
echo "YDNU SILENT OFF" > /dev/ttyACM0

# Or restart cleanly:
sudo systemctl restart signalk
```

---

## 10. References

- **YDNU-02 Datasheet:** `docs/HARDWARE/YDNU-02-DATASHEET.md`
- **Integration Guide:** `docs/INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md`
- **B&G WS320:** `docs/HARDWARE/BG-WS320-DATASHEET.md`
- **Vulcan 7 FS:** `docs/HARDWARE/VULCAN-7-FS-DATASHEET.md`
- **Architecture Master:** `docs/ARCHITECTURE-MASTER.md` (system overview)

---

**Maintained by:** OC (OpenClaw)  
**Last audit:** 2026-06-15  
**Next review:** After P5 activation (performance data PGN 130824)

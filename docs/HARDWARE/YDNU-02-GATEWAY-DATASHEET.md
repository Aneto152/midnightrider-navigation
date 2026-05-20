# YACHT DEVICES YDNU-02 — NMEA 2000 USB GATEWAY DATASHEET

**Manufacturer:** Yacht Devices Ltd. (Russia)  
**Model:** YDNU-02 (Dual-interface bidirectional gateway)  
**Firmware Version:** 1.25 (latest tested)  
**Interface:** USB ↔ NMEA 2000 (bidirectional)  
**Date:** 2026-05-19  
**Status:** ✅ Operational — Critical component (Signal K ↔ Vulcan 7 FS bridge)

---

## MODELS

| Model | NMEA 2000 Connector | USB Connector | Use Case |
|-------|---------------------|---------------|---------|
| **YDNU-02RM** | Raymarine SeaTalk NG | USB-A Male (not waterproof) | Dry interior |
| **YDNU-02RF** | Raymarine SeaTalk NG | USB-A Female IP67 | Exterior/bulkhead |
| **YDNU-02NM** | NMEA 2000 Micro-C Male | USB-A Male (not waterproof) | Dry interior |
| **YDNU-02NF** | NMEA 2000 Micro-C Male | USB-A Female IP67 | Exterior/bulkhead |

> Midnight Rider uses the **YDNU-02NM** or **YDNU-02NF** (Micro-C NMEA 2000 connector).

---

## SPECIFICATIONS

### Electrical

| Spec | Value |
|------|-------|
| **USB Interface** | USB 1.1 / 2.0 / 3.0 compatible |
| **USB VID / PID** | 0x0483 / 0xA217 (STMicroelectronics) |
| **USB Device Class** | Class 2 subclass 2 (Virtual COM Port / CDC ACM) |
| **Current from USB** | 35 mA average |
| **Supply voltage from N2K** | 7 – 16V DC |
| **Current from N2K** | 13 mA (isolated transceiver only) |
| **Network Load** | **1 LEN** (50 mA equivalent) |
| **Galvanic Isolation** | **2500 VRMS** between NMEA 2000 and USB |
| **NMEA 2000 Data Rate** | 250 kbps (standard) |

> ⚠️ The device is **USB-powered** (main electronics). The 13 mA from NMEA 2000 is only
> for the isolated side of the network transceiver. Both power sources must be present.

### Physical

| Spec | Value |
|------|-------|
| **Case Length** | 54 mm |
| **Cable Length** (case to connector) | 450 mm |
| **Weight** | 37 g (RM/NM models) / 51 g (RF/NF models) |
| **Operating Temperature** | -20°C to +55°C |
| **USB Connector Waterproof** | IP67 — RF/NF models only (requires YU-USB cable) |
| **Case** | Non-dismountable, maintenance-free |
| **Warranty** | 2 years |

> ⚠️ **IP67 only applies to the USB connector on RF/NF models.** The device body
> must be installed in a dry location. Do NOT submerge.

---

## OPERATION MODES

The YDNU-02 supports four operation modes (factory default: **AUTO**):

| Mode | Protocol | Compatibility | Use Case |
|------|----------|---------------|---------|
| **AUTO** | Auto-detect | Signal K, OpenCPN | **Recommended — default** |
| **0183** | NMEA 0183 text | All legacy software | Old marine PC apps |
| **N2K** | Binary Yacht Devices | Expedition, Coastal Explorer, Polar View | High-performance apps |
| **RAW** | Text log format | Diagnostics, CAN Log Viewer | Debugging |

> Signal K uses **AUTO** mode (detects N2K or 0183 automatically on port open).
> The YDNU-02 analyzes first bytes received from the application for the first 2000ms.

### Switching Modes (Linux)

```bash
# Set mode (replace /dev/ttyACM0 with actual port)
stty -F /dev/ttyACM0 hupcl
echo YDNU MODE AUTO > /dev/ttyACM0    # Recommended
echo YDNU MODE 0183 > /dev/ttyACM0    # Force NMEA 0183
echo YDNU MODE N2K > /dev/ttyACM0     # Force binary N2K
echo YDNU MODE RAW > /dev/ttyACM0     # Force diagnostic text

# Silent mode (read-only — prevents PC from writing to N2K bus)
echo YDNU SILENT ON > /dev/ttyACM0   # RECOMMENDED when not controlling N2K
echo YDNU SILENT OFF > /dev/ttyACM0  # Restore bidirectional
```

> ⚠️ **Security note:** When `SILENT ON`, the device becomes read-only.
> This prevents any Signal K plugin bug from flooding the NMEA 2000 network.
> The LED will show a RED signal when powered on in silent mode.

---

## LED SIGNALS

| Signal | Meaning |
|--------|---------|
| 1× 0.5s GREEN on power | Normal mode, ready (bidirectional) |
| 1× 0.5s RED on power | **Silent mode** active (read-only) |
| 2× 0.5s per 3s (port not open) | GREEN = N2K data received; RED = no N2K data |
| 4× rapid per 1.5s (port open) | Signal 1: N2K RX; 2: N2K TX; 3: USB TX; 4: USB RX |
| Constant GREEN | Application hung (port open but not reading) |
| 3× RED per second (10s) | Powered but no PC connection (driver issue?) |
| 3s GREEN | Diagnostic recording ON |
| 3s RED | Diagnostic recording OFF (buffer full) |

---

## NMEA 2000 ↔ NMEA 0183 CONVERSIONS (0183 Mode)

### N2K → NMEA 0183 (key conversions)

| PGN | NMEA 2000 Name | NMEA 0183 Output |
|-----|---------------|-----------------|
| 126992 | System Time | ZDA, GLL |
| 127233 | Man Overboard | MOB |
| 127237 | Heading/Track Control | APB, HSC |
| 127245 | Rudder | RSA |
| **127250** | **Vessel Heading** | **HDG, HDM, HDT** |
| 127251 | Rate of Turn | ROT |
| 127488 | Engine Parameters Rapid | RPM, XDR |
| 127489 | Engine Parameters Dynamic | XDR |
| **128259** | **Speed Water Referenced** | **VHW** |
| **128267** | **Water Depth** | **DBT, DBS, DPT** |
| 128275 | Distance Log | VLW |
| **129025** | **Position Rapid Update** | **GLL** |
| **129026** | **COG & SOG Rapid** | **VTG** |
| **129029** | **GNSS Position Data** | **GGA, GLL, RMC, ZDA** |
| 129283 | Cross Track Error | XTE |
| 129284 | Navigation Data | RMB, HSC |
| 129291 | Set & Drift Rapid | VDR |
| 129539 | GNSS DOPs | GSA |
| 129540 | GNSS Sats in View | GSV, GRS |
| **130306** | **Wind Data** | **MWD, MWV, VWR, VWT** |
| 130310 | Environmental Parameters | XDR, MTW, MDA |
| 130311 | Environmental Parameters | XDR, MTW, MDA |
| **130312** | **Temperature** | **XDR, MTW, MDA** |
| 130313 | Humidity | XDR, MDA |
| 130314 | Actual Pressure | XDR, MDA |
| 130578 | Vessel Speed Components | VBW |
| 129038–129810 | **All AIS PGNs** | **VDM, VDO** |

### NMEA 0183 → N2K (key conversions)

| NMEA 0183 | NMEA 2000 PGN | Notes |
|-----------|--------------|-------|
| APB | 129283 Cross Track Error | + 129284 |
| DPT | 128267 Water Depth | |
| GGA | 129029 GNSS Position Data | ZDA/RMC required |
| GLL | 129025 Position Rapid | |
| GSA | 129539 GNSS DOPs | |
| GSV | 129540 GNSS Sats in View | |
| HDG/HDM/HDT | 127250 Vessel Heading | |
| MDA | 130311, 130314, 130306 | Temp, pressure, wind |
| MOB | 127233 Man Overboard | |
| MTW | 130311 Environmental | |
| MWD/MWV | 130306 Wind Data | |
| RMB | 129283, 129284, 129285 | Navigation |
| RMC | 126992, 127258, 129025, 129026 | Full position + time |
| ROT | 127251 Rate of Turn | |
| VBW | 130578 Vessel Speed Components | |
| VHW | 128259 Speed Water Referenced | |
| VLW | 128275 Distance Log | |
| VTG | 129026 COG & SOG Rapid | |
| VWR/VWT | 130306 Wind Data | |
| XTE | 129283 Cross Track Error | |
| ZDA | 126992, 129033 | System Time |
| VDM/VDO | 129038–129810 (all AIS) | Full AIS pass-through |

### True Wind Calculation (built-in)

The YDNU-02 can calculate **true wind internally** in 0183 mode using:

| Setting | Method | Notes |
|---------|--------|-------|
| `WIND_CALC ANY` | Auto-select best available | **Factory default — recommended** |
| `WIND_CALC HDG_SOG` | Heading + SOG | Best for strong currents |
| `WIND_CALC COG_SOG` | COG + SOG | GPS only, no compass |
| `WIND_CALC HDG_STW` | Heading + STW | Traditional, less accurate in current |
| `WIND_CALC DISABLED` | No calculation | Only pass pre-calculated true wind |

> On Midnight Rider: true wind is calculated by the **Vulcan 7 FS** internally.
> The YDNU-02 passes apparent wind (PGN 130306) from Signal K to the N2K bus.

---

## MIDNIGHT RIDER INTEGRATION

### Architecture

```
Signal K (port 3000, systemctl)
     ↓ signalk-to-nmea2000 plugin
     ↓ /dev/ttyACM0 (USB CDC ACM)
YDNU-02 Gateway (USB ↔ NMEA 2000)
     ↓ NMEA 2000 Micro-C (1 LEN)
NMEA 2000 backbone
     ├─ Vulcan 7 FS (PGNs 127250, 127257, 129025, 129026, 130306)
     └─ WS320 Base Station (PGN 130306 ← apparent wind)
```

### Device Path on RPi 4

The YDNU-02 uses the **CDC ACM driver** on Linux (not FTDI):

```bash
# Verify device is detected
lsusb | grep -i yacht
# Expected: "Yacht Devices Ltd NMEA 2000 USB Gateway" (VID: 0483, PID: A217)

# Find correct port (CDC ACM device)
ls /dev/ttyACM*
dmesg | grep -i "NMEA\|ttyACM\|0483" | tail -10
# Expected: cdc_acm driver, /dev/ttyACM0 or /dev/ttyACM1
```

> ⚠️ **Port name:** On Linux, the YDNU-02 uses CDC ACM driver → appears as
> `/dev/ttyACM*` (NOT `/dev/ttyUSB*`). If Signal K is configured with
> `/dev/ttyUSB1`, verify this matches the actual port on the RPi.

### Optional: Persistent Port Name via udev

To prevent port name changes after reboot:

```bash
# Create udev rule for consistent naming
sudo bash -c 'cat > /etc/udev/rules.d/99-ydnu02.rules << EOF
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="a217", SYMLINK+="ttyYDNU"
EOF'

sudo udevadm control --reload
# Device will now also appear as /dev/ttyYDNU
```

### Signal K Plugin Configuration

```json
{
  "plugins": {
    "signalk-to-nmea2000": {
      "enabled": true,
      "interface": "/dev/ttyACM0",
      "sendPGNs": [
        127250,   // Vessel Heading (from UM982)
        127257,   // Attitude Roll/Pitch/Yaw (from WIT IMU)
        129025,   // GNSS Position Rapid (from UM982)
        129026,   // COG & SOG (from UM982)
        130306    // Wind Data (from Calypso, optional)
      ]
    }
  }
}
```

### PGNs Sent: Signal K → Vulcan 7 FS

| PGN | Name | SK Source | Status |
|-----|------|-----------|--------|
| **127250** | Vessel Heading | UM982 headingTrue | ✅ Active |
| **127257** | Attitude (Roll/Pitch/Yaw) | WIT WT901BLECL | ✅ Active (fixed 2026-05-17) |
| **129025** | Position Rapid Update | UM982 position | ✅ Active |
| **129026** | COG & SOG | UM982 SOG/COG | ✅ Active |
| **130306** | Wind Data | Calypso UP10 | ⚠️ Active when Calypso running |

### PGNs Received: Other N2K Devices → Signal K

| PGN | Name | Source Device | SK Path |
|-----|------|--------------|---------|
| **130306** | Wind Data | WS320 base station | `environment.wind.*` |
| **128259** | Speed Water Referenced | Loch (not installed) | `navigation.speedThroughWater` |
| **128267** | Water Depth | Depth sounder (not installed) | `environment.depth.belowTransducer` |
| **129038–129810** | AIS | AIS transponder (if installed) | `vessels.*` |

---

## INSTALLATION

### Physical

1. Mount device in **dry location** (below deck, nav station or near RPi 4)
2. Connect **Micro-C** to NMEA 2000 backbone via T-connector
3. Connect **USB** to RPi 4 (short cable ≤ 0.5m recommended)
4. Verify LED signals after connection

### Prevent ModemManager interference (Linux)

```bash
# Prevent ModemManager from monopolizing the port for 60s on connection
sudo bash -c 'echo "ATTRS{idVendor}==\"0483\" ATTRS{idProduct}==\"a217\", ENV{ID_MM_DEVICE_IGNORE}=\"1\"" > /etc/udev/rules.d/ydnu.rules'
sudo udevadm control --reload
```

---

## ADVANCED FEATURES

### Diagnostics Recording

```bash
# Start recording (1MB EEPROM buffer, ~2-10 minutes)
stty -F /dev/ttyACM0 hupcl
echo YDNU DIAG > /dev/ttyACM0
# LED: 3s GREEN = recording started

# Stop recording
echo YDNU MODE SERVICE > /dev/ttyACM0
# LED: 3s RED = recording stopped (or buffer full)

# View recorded data (requires terminal/screen)
echo YDNU MODE SERVICE > /dev/ttyACM0
screen /dev/ttyACM0
# Then type: DIAG ALL
```

### Firmware Update

```bash
# Copy firmware .BIN file to device port
cp UUPDATE.BIN /dev/ttyACM0
# LED: 3× GREEN = success, 3× RED+GREEN = already up to date
```

### Service Menu Access

```bash
echo YDNU MODE SERVICE > /dev/ttyACM0
screen /dev/ttyACM0
# Available commands: HELP, MODE, FILTER, SET, RESET, DIAG
```

---

## PRE-RACE VERIFICATION

```bash
# 1. Confirm USB device detected
lsusb | grep -i "0483\|yacht"

# 2. Confirm port exists
ls -la /dev/ttyACM*

# 3. Verify Signal K plugin running
curl -s http://localhost:3000/skServer/plugins | \
  jq '.[] | select(.id | contains("nmea2000")) | {id, running}'
# Expected: "running": true

# 4. Verify LED state
# Green flashing = data flowing between Signal K and N2K bus ✅

# 5. Check Vulcan 7 FS device list
# Settings → Network → Device List → YDNU-02 should appear

# 6. Confirm PGNs reaching Vulcan
# Heading, position, attitude should update live on Vulcan display
```

---

## KNOWN ISSUES & FIXES

| Issue | Cause | Fix |
|-------|-------|-----|
| Device not found (`lsusb`) | USB cable issue | Check cable, try different USB port |
| Port appears as `/dev/ttyUSB*` | Unusual kernel config | Use `dmesg` to find actual port name |
| ModemManager takes port for 60s | ModemManager claiming CDC ACM | Add udev ignore rule (see above) |
| Vulcan shows no data | Signal K plugin stopped | `sudo systemctl restart signalk` |
| PGNs not transmitting | signalk-to-nmea2000 not enabled | Check plugin config, restart Signal K |
| N2K bus errors | Termination missing | Verify NMEA 2000 backbone has 2 terminators |
| Yellow LED not blinking | No N2K traffic | Check NMEA 2000 bus power (needs 12V) |
| Signal floods N2K bus | PC app misconfigured | `echo YDNU SILENT ON > /dev/ttyACM0` |

---

## CRITICAL NOTES

⚠️ **Bidirectional:** The YDNU-02 can WRITE to the NMEA 2000 bus. A misconfigured
Signal K plugin or software bug can flood the network. Consider `YDNU SILENT ON`
if only reading is needed.

⚠️ **Port path:** Do NOT assume `/dev/ttyUSB0`. Verify with `dmesg | grep ttyACM`
after connection. The YDNU-02 is a CDC ACM device, not FTDI.

⚠️ **Dual power:** Both USB and NMEA 2000 power must be present. USB powers
the main MCU; N2K powers the isolated transceiver. If NMEA 2000 bus is off,
the device will appear on USB but won't communicate with N2K.

⚠️ **1 LEN load:** Verify NMEA 2000 network bus capacity. Maximum 50 LEN per network.
Midnight Rider N2K bus: YDNU-02 (1 LEN) + Vulcan 7 FS (1 LEN) + WS320 (2 LEN) = 4 LEN total.

---

## RACING ADVANTAGES

✅ **Bidirectional bridge:** Signal K → Vulcan (heading, position, attitude, wind)  
✅ **Universal compatibility:** Works with B&G, Simrad, Garmin, Furuno, Raymarine  
✅ **2500V galvanic isolation:** Protects RPi 4 from N2K bus transients  
✅ **No driver required:** CDC ACM (standard Linux/Mac/Windows 10 driver)  
✅ **Open protocols:** RAW and N2K formats fully documented  
✅ **True wind calc:** Can calculate true wind internally (used as fallback)  
✅ **Professional grade:** Used on commercial vessels, 2-year warranty  

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial documentation (incorrect specs) | OC |
| 2026-05-19 | Full revision: corrected size (54mm), temp (-20/+55°C), IP67 clarification, 1 LEN network load, CDC ACM port path, galvanic isolation, operation modes, N2K↔0183 conversion tables, udev/ModemManager notes | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Operational — Critical bridge Signal K ↔ Vulcan 7 FS  
**Next Action:** Verify `/dev/ttyACM0` vs `/dev/ttyUSB1` port path during field test

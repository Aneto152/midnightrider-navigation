# SOK BATTERY SK12V100PC — HARDWARE DATASHEET & BMS BLE PROTOCOL

**Manufacturer:** SOK Battery (Canada/USA)  
**Model:** SK12V100PC — 12V 100Ah LiFePO4 with Bluetooth BMS  
**Chemistry:** Lithium Iron Phosphate (LiFePO4)  
**BMS Type:** JBD (JiaBaiDa) built-in BLE BMS  
**Date:** 2026-05-19  
**Status:** ✅ Field Test Ready (May 19, 2026)

---

## BATTERY SPECIFICATIONS

### Electrical

| Spec | Value |
|------|-------|
| **Nominal Voltage** | 12.8 V (4S LiFePO4) |
| **Capacity** | 100 Ah @ 0.2C |
| **Energy** | 1280 Wh |
| **Cell Configuration** | 4 cells in series (4S) |
| **Max Continuous Discharge** | 100 A |
| **Peak Discharge Current** | 170 A (≤ 4 s) |
| **Max Charge Current** | 70 A |
| **Recommended Charge Current** | < 50 A |
| **Recommended Charge Voltage** | 13.8 V – 14.6 V |
| **Recommended Low Voltage Disconnect** | 10.4 V |
| **Self-Discharge Rate** | ≤ 3% per month |

### Performance

| Spec | Value |
|------|-------|
| **Cycle Life** | 3000+ cycles @ 100% DoD / 6000+ cycles @ 80% DoD |
| **Operating Temp — Discharge** | -20°C to +60°C |
| **Operating Temp — Charge** | 0°C to +45°C |
| **Storage Temperature** | -10°C to +35°C (recommended: 13.5V–13.6V charge level) |

### Physical

| Spec | Value |
|------|-------|
| **Dimensions (L×W×H)** | 260 × 170 × 210 mm (10.24 × 6.69 × 8.27 in) |
| **Weight** | 11.2 kg (24.7 lbs) |
| **Enclosure** | Clear sealed plastic (PC — polycarbonate) |
| **Certifications** | UL1973 & IEC62619 (cells) |
| **Warranty** | 5 years |

### Cell Voltage Reference (LiFePO4)

| State | Cell Voltage | Battery Voltage |
|-------|-------------|----------------|
| **Full (100% SoC)** | 3.65 V | 14.6 V |
| **Nominal** | 3.20 V | 12.8 V |
| **Low Warning** | 3.00 V | 12.0 V |
| **Low Cutoff (BMS)** | 2.50 V | 10.0 V |
| **Max imbalance threshold** | ΔV > 0.2 V | → Alert |

---

## BUILT-IN BMS

### Overview

The SOK SK12V100PC uses a **JBD (JiaBaiDa) BMS** with an integrated Bluetooth Low Energy
module. The official app is **ABC-BMS** (iOS & Android — `com.sjty.sbs_bms`).

The BLE protocol has been reverse-engineered from the ABC-BMS app, enabling direct
integration with the RPi without the official app.

### BMS Protection Layers

The BMS implements **two layers** of protection:

**Layer 1 — Software Protection (CMOS / DMOS):**

| Trigger | Protection |
|---------|-----------|
| Any cell voltage > charge limit | CMOS OFF (charging disabled) |
| Charge current > limit | CMOS OFF |
| Temperature < 0°C during charge | CMOS OFF (+ heater if model H) |
| Temperature > 45°C during charge | CMOS OFF |
| BMS temp > limit during charge | CMOS OFF |
| Any cell voltage < discharge limit | DMOS OFF (discharging disabled) |
| Battery voltage < discharge limit | DMOS OFF |
| Discharge current > limit | DMOS OFF |
| Temperature > 60°C during discharge | DMOS OFF |
| Short circuit detected | DMOS OFF |

**Layer 2 — Hardware Protection:**

- Short circuit
- Overcurrent (hardware threshold)
- Over-discharge (hardware voltage threshold)
- Overcharge (hardware voltage threshold)

### Cell Balancing

The BMS uses **passive balancing** (resistor drain method):

| Condition | Value |
|-----------|-------|
| **Type** | Passive (resistive drain on high cells) |
| **Balance resistor** | 33–47 Ω (varies by firmware version) |
| **Activation threshold** | Any cell > 3.4V AND ΔV > 25 mV AND charge current ≥ 1A |
| **Fast balance (firmware ≥ v4)** | ΔV > 10 mV if any cell > 3.6V |
| **Balance time (1% imbalance)** | ~12–22 hours (depends on firmware version) |

> ⚠️ Cell imbalance is normal at high and low SoC due to LiFePO4 voltage curve characteristics.
> Monitor imbalance at the same voltage point each time for accurate trending.

### Storage Mode

The BMS has a **storage mode** that completely shuts down the BMS to minimize self-discharge:

- In storage mode: **0V at terminals, BLE invisible to scanners**
- To wake up: connect a LiFePO4 charger for a few seconds
- Storage charge level: 13.5V–13.6V (≈ 50% SoC)

### ABC-BMS App Access

| Parameter | Value |
|-----------|-------|
| **App name** | ABC-BMS |
| **Platforms** | iOS + Android |
| **Package ID** | `com.sjty.sbs_bms` |
| **Basic settings password** | `200010` |

**Key screens:**
- **Home:** voltage, current, individual cell voltages, CMOS/DMOS state
- **PROT State:** active protection triggers (charge and discharge separately)
- **Basic Settings:** idle calibration, sleep time, storage mode, recovery, reboot, reset

---

## BLUETOOTH LE PROTOCOL

### BLE Parameters

| Parameter | Value |
|-----------|-------|
| **BLE Service UUID** | `0000FFF0-0000-1000-8000-00805F9B34FB` |
| **Notify UUID (RX — read data)** | `0000FFF1-0000-1000-8000-00805F9B34FB` |
| **Write UUID (TX — send commands)** | `0000FFF2-0000-1000-8000-00805F9B34FB` |
| **Standard: Manufacturer Name** | `00002a29-0000-1000-8000-00805f9b34fb` |
| **Standard: Model Number** | `00002a24-0000-1000-8000-00805f9b34fb` |
| **Standard: Firmware Revision** | `00002a26-0000-1000-8000-00805f9b34fb` |
| **Standard: Serial Number** | `00002a25-0000-1000-8000-00805f9b34fb` |

### Command Format

Each command is **5 bytes** followed by a **CRC8 checksum** byte:

```
[command_bytes (5)] + [minicrc(command_bytes) (1)]
```

### Available Commands

| Command | Bytes (hex) | Response Code | Data Returned |
|---------|-------------|---------------|---------------|
| `cmd_name` | `[0xee, 0xc0, 0x00, 0x00, 0x00]` | `0xCCF1` | BMS name (e.g., "SK12V100") |
| `cmd_info` | `[0xee, 0xc1, 0x00, 0x00, 0x00]` | `0xccf0` | SoC, current, voltage, cycles |
| `cmd_detail` | `[0xee, 0xc2, 0x00, 0x00, 0x00]` | `0xCCF4` | Individual cell voltages |
| `cmd_setting` | `[0xee, 0xc3, 0x00, 0x00, 0x00]` | `0xCCF3` | BMS config (capacity, year, etc.) |
| `cmd_protection` | `[0xee, 0xc4, 0x00, 0x00, 0x00]` | `0xCCF5` | Protection states (CMOS, DMOS) |
| `cmd_break` | `[0xdd, 0xc0, 0x00, 0x00, 0x00]` | — | Interrupt communication |

### Response Formats

All responses include a **CRC8 checksum** as the last byte. Message type is identified
by the first 2 bytes.

#### `0xccf0` — Status (response to `cmd_info`)

| Offset | Length | Type | Content |
|--------|--------|------|---------|
| 0–1 | 2 | uint16 BE | Message type (`0xccf0`) |
| 2–4 | 3 | int24 LE | Total voltage (mV) |
| 5–7 | 3 | int24 LE | Instantaneous current (µA → divide by 1,000,000 for A) |
| 8–10 | 3 | int24 LE | Power (W) |
| 11–13 | 3 | int24 LE | Average current (µA) |
| 14–15 | 2 | uint16 LE | Cycle count |
| 16–17 | 2 | uint16 LE | SoC (%) |

> Example: current = `0x000100` (µA) → 1A charge

#### `0xCCF4` — Cell Voltages (response to `cmd_detail`)

| Offset | Length | Type | Content |
|--------|--------|------|---------|
| 0–1 | 2 | uint16 BE | Message type (`0xCCF4`) |
| 2+(x×4) | 1 | uint8 | Cell index (1–4) |
| 3+(x×4) | 2 | uint16 LE | Cell voltage (mV) |
| 5+(x×4) | 1 | uint8 | Reserved |

> Total voltage (V) = (cell1 + cell2 + cell3 + cell4) / 1000

#### `0xCCF3` — Manufacturer Info (response to `cmd_setting`)

| Offset | Length | Type | Content |
|--------|--------|------|---------|
| 0–1 | 2 | uint16 BE | Message type (`0xCCF3`) |
| 2 | 1 | uint8 | Manufacturing year (add 2000) |
| 3–4 | 2 | uint16 LE | Month/day of manufacture |
| 5–7 | 3 | uint24 BE | Nominal capacity (Ah, divide by 128) |
| 8–9 | 2 | uint16 LE | Heater state (0=off, 1=on) |
| 10–11 | 2 | uint16 LE | Nominal voltage (V × 100) |

#### `0xCCF5` — Protection State (response to `cmd_protection`)

| Offset | Length | Type | Content |
|--------|--------|------|---------|
| 0–1 | 2 | uint16 BE | Message type (`0xCCF5`) |
| 2 | 1 | uint8 | Protection flags |
| 3 | 1 | uint8 | CMOS state (0=normal, 1=triggered) |
| 4 | 1 | uint8 | DMOS state (0=normal, 1=triggered) |
| 5+ | — | — | Additional protection states |

### CRC8 Algorithm

```python
def minicrc(data):
    """CRC8 algorithm for SOK BMS data verification"""
    i = 0
    for b in data:
        i ^= b & 255
        for _ in range(8):
            if (i & 1) != 0:
                i = (i >> 1) ^ 140
            else:
                i = i >> 1
    return i

# Usage
data = [0xee, 0xc1, 0x00, 0x00, 0x00]  # cmd_info
crc = minicrc(data)
command_with_crc = data + [crc]
```

### Communication Flow

```
1. Scan BLE → find "SOK" or "ABC-BMS" device
2. Connect (bleak.BleakClient)
3. Subscribe to Notify UUID (0000FFF1)
4. Write cmd_info on Write UUID (0000FFF2)
5. Wait for response 0xccf0
6. Parse and verify CRC8
7. Write to InfluxDB
8. Wait 5 seconds
9. Repeat from step 3
```

---

## MIDNIGHT RIDER INTEGRATION

### Architecture

```
SOK Battery (BLE BMS)
     ↓ Bluetooth LE
RPi 4 (midnightrider.local) — hci0 BLE adapter
     ↓ sok_bms_reader.py (Python + bleak)
     ↓ DIRECT write (bypasses Signal K)
InfluxDB (port 8086, Docker)
     ↓ measurement: sok_bms
Grafana (port 3001) — Dashboard 06: ELECTRICAL
```

> ⚠️ The SOK BMS writes **directly to InfluxDB** — it does NOT go through Signal K.
> This is by design (BLE rate limitation of 0.2 Hz is not suited for Signal K real-time paths).

### Python Script

| Parameter | Value |
|-----------|-------|
| **Script** | `sok_bms_reader.py` |
| **Library** | `bleak` (async BLE) + `influxdb-client` |
| **Read rate** | 0.2 Hz (1 read per 5 seconds — BLE constraint) |
| **InfluxDB measurement** | `sok_bms` |
| **Signal K source** | None (direct InfluxDB bypass) |

**Required dependencies:**

```bash
pip3 install bleak influxdb-client
sudo apt-get install -y python3-dbus libglib2.0-dev
```

**Class structure:**

```python
class SOK_BMS:
    async def connect(mac_address)
    async def read_status()      # cmd_info  → 0xccf0
    async def read_detail()      # cmd_detail → 0xCCF4
    async def read_settings()    # cmd_setting → 0xCCF3
    async def write_to_influx()
```

### InfluxDB Data Fields (measurement: `sok_bms`)

| Field | Unit | Source | Calculation |
|-------|------|--------|------------|
| `soc_pct` | % | 0xccf0 offset 16 | Direct value |
| `voltage_v` | V | 0xccf0 offset 2 | Value / 1000 |
| `current_a` | A | 0xccf0 offset 5 | Value / 1,000,000 |
| `power_w` | W | 0xccf0 offset 8 | Direct value |
| `temp_bms_c` | °C | 0xCCF2 offset 5 | Direct value (signed) |
| `temp_mos_c` | °C | 0xCCF2 offset 7 | Direct value (signed) |
| `cycles` | count | 0xccf0 offset 14 | Direct value |
| `cell_1_mv` | mV | 0xCCF4 | Cell 1 voltage |
| `cell_2_mv` | mV | 0xCCF4 | Cell 2 voltage |
| `cell_3_mv` | mV | 0xCCF4 | Cell 3 voltage |
| `cell_4_mv` | mV | 0xCCF4 | Cell 4 voltage |
| `cell_imbalance_mv` | mV | 0xCCF4 | max(cells) − min(cells) |
| `capacity_ah` | Ah | 0xCCF3 | Value / 128 |
| `year_mfg` | year | 0xCCF3 offset 2 | 2000 + value |
| `prot_cmos` | bool | 0xCCF5 | CMOS state |
| `prot_dmos` | bool | 0xCCF5 | DMOS state |

### Grafana Dashboard — 06: ELECTRICAL

Access: `http://midnightrider.local:3001/d/electrical-power`

| Panel | Data | Alert Threshold |
|-------|------|----------------|
| **SoC %** | State of charge gauge (0–100%) | < 20% → warning, < 5% → critical |
| **Cell Voltages** | 4-cell balance chart | ΔV > 0.2V → cell imbalance alert |
| **Current** | Charge/discharge current (A) | — |
| **Temperature** | BMS + MOS temperature (°C) | > 60°C → critical |
| **Cell Imbalance** | Max − Min cell voltage (mV) | > 200 mV → warning |
| **Energy Reserve** | Hours remaining @ current draw | — |

**Alert Rules:**

| Rule | Condition | Severity |
|------|-----------|---------|
| `electrical_soc_low` | SoC < 20% | ⚠️ Warning |
| `electrical_soc_critical` | SoC < 5% | 🔴 Critical |
| `electrical_cell_imbalance` | ΔV > 0.2V | ⚠️ Warning |
| `electrical_bms_overtemp` | Temp > 60°C | 🔴 Critical |
| `electrical_disconnect` | No data > 5 min | 🔴 Critical |

---

## BLE DEVICE DISCOVERY

**When battery is powered and out of storage mode:**

```bash
# Quick scan for SOK BMS
sudo hcitool lescan | grep -i "SOK\|ABC\|BMS"

# Alternative with bluetoothctl
bluetoothctl scan on
# Press Ctrl+C when MAC address found

# Verify BLE connectivity
sudo gatttool -b <MAC_ADDRESS> --interactive
> connect
> char-read-hnd 0x0003
```

> ⚠️ If battery shows 0V at terminals: it is in **storage mode**.
> Connect a LiFePO4 charger briefly to wake up the BMS.
> The BLE device will become visible again within 30 seconds.

---

## PRE-RACE VERIFICATION

```bash
# 1. Verify BLE device visible
sudo hcitool lescan | grep -i "SOK"

# 2. Run BMS reader script
python3 /home/aneto/sok_bms_reader.py --once
# Expected: JSON output with soc_pct, voltage_v, cell voltages

# 3. Verify InfluxDB receiving data
docker exec influxdb influx query \
  -o MidnightRider \
  --token $(grep INFLUXDB_TOKEN .env | cut -d= -f2) \
  'from(bucket:"midnight_rider")
   |> range(start: -5m)
   |> filter(fn: (r) => r._measurement == "sok_bms")
   |> limit(n: 5)'

# 4. Check Grafana dashboard 06
# http://midnightrider.local:3001/d/electrical-power
# Expected: SoC gauge, cell voltages, all panels populated

# 5. Quick health check
# - SoC > 80% before race
# - Cell imbalance < 50 mV (ΔV)
# - Temperature < 40°C
# - No CMOS or DMOS protection active
```

---

## SAFETY NOTES

⚠️ **Never discharge below 10% SoC** → accelerates LiFePO4 cell degradation

⚠️ **Cell imbalance > 0.2V** → indicates BMS issue, inspect immediately

⚠️ **Overtemperature > 60°C** → cease charging, check ventilation

⚠️ **CMOS OFF** → charging disabled by BMS protection — check PROT State in app

⚠️ **DMOS OFF** → discharging disabled by BMS protection — check PROT State in app

⚠️ **Storage mode** → BMS fully shut down (0V at terminals). Wake with LiFePO4 charger.

⚠️ **Do not connect to alternators or non-smart chargers** → risk of overcharge

✅ **Cycle count monitoring** → track degradation (target: 3000+ cycles before replacement)

---

## KNOWN ISSUES & NOTES

| Issue | Status | Note |
|-------|--------|------|
| SOC accuracy on first delivery | Known | SOC/capacity may be inaccurate before full cycle. Use cell voltages for reference. |
| BLE invisible after prolonged inactivity | By design | BMS enters sleep mode. Trigger charge/discharge to wake. |
| BLE invisible after factory delivery | By design | Storage mode (0V). Connect charger briefly to activate. |
| Passive balancing speed | Known | 12–22h to overcome 1% imbalance — normal for LiFePO4 BMS |
| SoC inaccurate after deep discharge | Known | Recalibrate with full charge cycle |

---

## CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-04-25 | Initial BLE protocol documentation (French only, no hardware specs) | OC |
| 2026-05-12 | Integration guide created, field test readiness confirmed | OC |
| 2026-05-19 | Full datasheet revision: added hardware specs, translated to English, corrected status, consolidated BLE protocol + integration reference | Denis / Dust |

---

**Last Updated:** 2026-05-19  
**Status:** ✅ Field Test Ready  
**Crew:** Denis + Anne-Sophie (ORC J/30 — Block Island Race)  
**Next Action:** Validate SoC % accuracy during first on-water session

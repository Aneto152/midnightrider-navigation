# SOK-BMS-INTEGRATION.md — SOK 12V 100Ah LiFePO4 BMS Integration

> Hardware: SOK 12V 100Ah LiFePO4 Battery with BLE BMS  
> Protocol: BLE GATT (see HARDWARE/SOK-BMS-BLE-PROTOCOL.md)  
> Signal K path: `electrical.batteries.house.*`  
> Grafana dashboard: 06 — ELECTRICAL (Power Management)  
> Refresh: 30s  

---

## Overview

The SOK 12V 100Ah LiFePO4 battery integrates with Midnight Rider via
Bluetooth Low Energy (BLE). The BMS broadcasts real-time data including
State of Charge, cell voltages, temperature, and current.

Data flow: SOK BMS (BLE) → RPi4 BLE reader → Signal K → InfluxDB → Grafana

---

## Hardware Requirements

| Component | Detail |
|-----------|--------|
| Battery | SOK 12V 100Ah LiFePO4 |
| BMS | Built-in BLE BMS (JBD protocol) |
| RPi interface | Built-in Bluetooth (RPi 4B) |
| Signal K plugin | signalk-bms-battery or custom BLE reader |

---

## BLE Connection Setup

### 1. Scan for BMS device

```bash
sudo hcitool lescan | grep -i "jbd\|bms\|sok"
```

→ Note the MAC address (format: XX:XX:XX:XX:XX:XX)

### 2. Verify BLE connectivity

```bash
sudo gatttool -b <MAC_ADDRESS> --interactive
> connect
> char-read-hnd 0x0003
```

→ Expected: BMS data bytes returned

### 3. Configure MAC address in Signal K plugin

```bash
# Edit Signal K plugin config (python3 only — never sed)
python3 -c "
import json
config_path = '/home/aneto/.signalk/plugin-config-data/bms-battery.json'
try:
    with open(config_path) as f:
        config = json.load(f)
    config['macAddress'] = '<MAC_ADDRESS>'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print('BMS MAC address configured')
except FileNotFoundError:
    print('Config file not found — check Signal K plugin installation')
"
```

---

## Signal K Data Paths

| Metric | Signal K Path | Unit |
|--------|--------------|------|
| State of Charge | `electrical.batteries.house.capacity.stateOfCharge` | ratio (0-1) |
| Voltage | `electrical.batteries.house.voltage` | V |
| Current | `electrical.batteries.house.current` | A (+ charge, - discharge) |
| Temperature | `electrical.batteries.house.temperature` | K |
| Cell 1 voltage | `electrical.batteries.house.cells.0.voltage` | V |
| Cell 2 voltage | `electrical.batteries.house.cells.1.voltage` | V |
| Cell 3 voltage | `electrical.batteries.house.cells.2.voltage` | V |
| Cell 4 voltage | `electrical.batteries.house.cells.3.voltage` | V |
| Cycle count | `electrical.batteries.house.lifetimeDischarge` | Ah |

---

## InfluxDB Verification

```bash
# Verify data flowing into InfluxDB
docker exec influxdb influx query \
  -o MidnightRider \
  --token $(grep INFLUXDB_TOKEN .env | cut -d= -f2) \
  'from(bucket:"midnight_rider")
   |> range(start: -5m)
   |> filter(fn: (r) => r._measurement =~ /electrical/)
   |> limit(n: 5)'
```

→ Expected: battery measurement rows returned

---

## Grafana Dashboard (06 — ELECTRICAL)

Access: http://192.168.1.131:3001/d/electrical-power

### Panels

- **SOC %** — State of Charge gauge (0-100%)
- **Cell Voltages** — 4-cell balance chart (target: 3.2-3.65V per cell)
- **Current** — Charge/discharge current (A)
- **Temperature** — BMS temperature (°C)
- **Cell Imbalance Alert** — Warning if ΔV > 0.2V between cells
- **Energy Reserve** — Hours remaining at current draw rate

### Alert Rules

- `electrical_soc_low`: SOC < 20% → warning
- `electrical_soc_critical`: SOC < 5% → critical
- `electrical_cell_imbalance`: Cell Δ > 0.2V → warning
- `electrical_bms_overtemp`: Temp > 60°C → critical
- `electrical_disconnect`: No data for 5+ minutes → critical

---

## Testing & Validation

### 1. Verify BLE connection

```bash
sudo hcitool lescan
# Should show SOK device in list
```

### 2. Verify Signal K receives data

```bash
curl -s http://localhost:3000/signalk/v1/vessels/self | \
  python3 -c "import json, sys; d=json.load(sys.stdin); \
  print('SOC:', d.get('electrical',{}).get('batteries',{}).get('house',{}).get('capacity',{}).get('stateOfCharge','?'))"
```

→ Expected: SOC value (0-1 range)

### 3. Verify InfluxDB contains measurements

```bash
docker exec influxdb influx query \
  -o MidnightRider \
  --token $(grep INFLUXDB_TOKEN .env | cut -d= -f2) \
  'from(bucket:"midnight_rider") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "electrical") |> limit(n: 1)'
```

→ Expected: electrical measurement data

### 4. Verify Grafana dashboard

Open http://192.168.1.131:3001/d/electrical-power

→ Expected: SOC gauge, cell voltages, current, temp graphs populated

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| BLE not discoverable | Check BMS is powered & nearby. Run `sudo hcitool lescan` |
| No data in Signal K | Verify plugin is enabled. Check logs: `journalctl -u signalk` |
| InfluxDB no data | Verify signal-to-influxdb2 plugin configured correctly |
| Grafana dashboard empty | Verify InfluxDB datasource (UID: efifgp8jvgj5sf) is healthy |
| Cell imbalance alert | Balance charge with dedicated charger. Check BMS logs |

---

## Safety Notes

- **Never discharge below 10% SOC** → shortens LiFePO4 lifespan
- **Cell imbalance > 0.2V** → indicates BMS issue, inspect immediately
- **Overtemperature > 60°C** → cease charging, check ventilation
- **Cycle count trending** → monitor for degradation (target: 5000+ cycles)

---

## Integration Checklist

- [ ] BLE MAC address scanned and noted
- [ ] Signal K plugin installed and enabled
- [ ] Plugin configured with correct MAC address
- [ ] BLE data appearing in Signal K (WebSocket)
- [ ] InfluxDB bucket `midnight_rider` receiving electrical measurements
- [ ] Grafana 06 — ELECTRICAL dashboard populated
- [ ] All 5 alert rules tested and armed
- [ ] iPad can view dashboard over WiFi (192.168.1.131:3001)

---

## Related Documentation

- HARDWARE/SOK-BMS-BLE-PROTOCOL.md — BLE frame structure & GATT details
- HARDWARE/UM982-GNSS-DATASHEET.md — GPS/heading (not battery-related)
- docs/SOFTWARE/GRAFANA-DASHBOARDS.md — All 16 dashboards
- docs/OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md — Pre-test validation

---

**Status:** ✅ READY FOR FIELD TEST (May 19, 2026)  
**Last Updated:** 2026-05-12  
**Crew:** Denis + Anne-Sophie (ORC J/30 — Block Island Race)

# CALYPSO UP10 — INTEGRATION GUIDE

**Status:** ✅ Operational (8 Hz, direct BLE connection)  
**Updated:** 2026-05-21

## Architecture

- **Service**: `calypso-anemometer` (Python package via pip)
- **Device**: Calypso UP10 ultrasonic anemometer (BLE)
- **Connection**: Direct BLE → UDP bridge → Signal K
- **Rate**: 8 Hz (HZ_8 maximum)
- **Protocol**: NMEA 2000-inspired JSON deltas over UDP/4123

**NOTE**: The old `signalk-calypso-ultrasonic` plugin is **OBSOLETE** — do not use.

## Service File

**Location**: `/etc/systemd/system/calypso-anemometer.service`

```ini
[Unit]
Description=Calypso Instruments Ultrasonic Anemometer for Signal K
After=network.target

[Service]
Type=simple
User=aneto
WorkingDirectory=/home/aneto
ExecStart=/home/aneto/.local/bin/calypso-anemometer read \
  --subscribe \
  --ble-address=F8:5F:12:9D:D2:EE \
  --rate=hz_8 \
  --target=udp+signalk+delta://localhost:4123
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Key Flags**:
- `--subscribe`: Continuous reading mode
- `--ble-address`: Device MAC (ULTRASONIC)
- `--rate=hz_8`: 8 Hz maximum (or hz_1, hz_4)
- `--target`: UDP → Signal K delta submission (port 4123)

## Signal K Data Paths

| Path | Unit | Range |
|------|------|-------|
| `environment.wind.speedApparent` | m/s | 0-35 |
| `environment.wind.angleApparent` | rad | 0-2π |
| `environment.wind.speedTrue` | m/s | derived by SK |
| `environment.wind.directionTrue` | rad | derived by SK |
| `environment.outside.temperature` | K | 250-320 |
| `navigation.attitude.roll` | rad | -π to π |
| `navigation.attitude.pitch` | rad | -π/2 to π/2 |
| `navigation.headingMagnetic` | rad | 0-2π |
| `electrical.batteries.99.capacity.stateOfCharge` | ratio | 0-1 |

## Watchdog (Robust v2)

**Service**: `calypso_robust_watchdog.service`

Escalating BLE recovery:
1. **L1 (60s)**: Restart calypso-anemometer service
2. **L2 (120s)**: Reset hci0 adapter (down → up)
3. **L3 (180s)**: Full BlueZ reset + remove device + re-pair

Monitoring: Checks Signal K `/environment/wind/speedApparent` age every 15 seconds

## Troubleshooting

### Device not connecting
```bash
# Check if device is advertising
sudo hcitool lescan 2>&1 | grep ULTRASONIC

# Manual re-pair
bluetoothctl remove F8:5F:12:9D:D2:EE
bluetoothctl trust F8:5F:12:9D:D2:EE
sudo systemctl restart calypso-anemometer
```

### hci0 soft-locked after phone disconnect
```bash
# Full BLE stack reset
sudo systemctl stop calypso-anemometer
sudo systemctl stop bluetooth
sudo hciconfig hci0 reset
sudo systemctl start bluetooth
sudo systemctl start calypso-anemometer
```

### No wind data in Signal K
```bash
# Check listener is running
ss -ulnp | grep 4123

# Check service status
systemctl status calypso-anemometer --no-pager

# Check logs
journalctl -u calypso-anemometer -n 50
```

## History

- **2026-05-21**: Service fixed (added --ble-address, --target, corrected rate flag, watchdog v2)
- **2026-05-17**: Watchdog deployed (initial L1/L2/L3 escalating recovery)
- **Earlier**: Manual Python script + legacy plugin approach

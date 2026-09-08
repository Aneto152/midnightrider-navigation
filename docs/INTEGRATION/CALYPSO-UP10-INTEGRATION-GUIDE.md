# Calypso UP10 — Integration Guide

**Status**: ✅ Operational (2026-06-28)

Hardware specs and BLE protocol → [CALYPSO-UP10-DATASHEET.md](../HARDWARE/CALYPSO-UP10-DATASHEET.md)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────┐
│   Calypso UP10 Anemometer (BLE)    │
│   MAC: F8:5F:12:9D:D2:EE           │
│   Notify UUID: 00002a39...         │
└──────────────┬──────────────────────┘
               │ BLE advertisement / GATT notifications
               │ 10-byte packets every ~125ms (4 Hz)
               │
┌──────────────▼──────────────────────┐
│  calypso_direct.py (systemd svc)   │
│  ─ BLE scan + connect              │
│  ─ Configure mode/rate/compass     │
│  ─ Decode 10-byte struct           │
│  ─ Apply wind offset correction    │
│  ─ Publish via UDP→Signal K        │
└──────────────┬──────────────────────┘
               │ UDP:4123 (localhost)
               │ Delta: angleApparent, speedApparent
               │
┌──────────────▼──────────────────────┐
│   Signal K Server (UDP listener)   │
│   Path: environment.wind.*         │
│   Subscribers: Grafana, MCP, etc.  │
└──────────────────────────────────────┘
```

---

## 2. Systemd Service

**File**: `/etc/systemd/system/calypso_direct.service`

| Parameter | Value |
|-----------|-------|
| Service Name | `calypso_direct` |
| Script | `/home/aneto/midnightrider-navigation/ble/calypso_direct.py` |
| Type | simple (no daemonize) |
| Restart | on-failure |
| RestartSec | 10 |
| User | aneto |

**Commands**:
```bash
# Status
sudo systemctl status calypso_direct

# Restart
sudo systemctl restart calypso_direct

# Logs (systemd journal)
sudo journalctl -u calypso_direct -f

# Enable on boot
sudo systemctl enable calypso_direct
```

---

## 3. Environment Variables

All parameters are set via the systemd service file (local to RPi, not committed to Git).

| Variable | Default | Current | Description |
|----------|---------|---------|-------------|
| `CALYPSO_BLE_ADDRESS` | `F8:5F:12:9D:D2:EE` | F8:5F:12:9D:D2:EE | Sensor MAC address |
| `CALYPSO_RATE_HZ` | `4` | 4 | Data rate (1/4/8 Hz) — 8Hz recommended for race, 4Hz for stability |
| `CALYPSO_DATA_TIMEOUT_S` | `60` | 60 | Stale data threshold before L1 reconnect (seconds) |
| `CALYPSO_HEARTBEAT_S` | `300` | 300 | Heartbeat log interval (seconds) |
| `CALYPSO_RECONNECT_MAX_S` | `60` | 60 | Maximum backoff for exponential retry (seconds) |
| `CALYPSO_L2_THRESHOLD` | `10` | 10 | L1 failures before L2 (BT recovery + exit) |
| `CALYPSO_WIND_OFFSET_DEG` | `0` | **7** | Wind angle offset (degrees) — **see §4** |

**To change a value**:
1. Edit `/etc/systemd/system/calypso_direct.service`
2. Change the `Environment="CALYPSO_WIND_OFFSET_DEG=7"` line
3. Run: `sudo systemctl daemon-reload && sudo systemctl restart calypso_direct`

---

## 4. Wind Angle Offset Calibration

### Purpose

Corrects for masthead sensor physical misalignment.

**Positive value** = rotate measured angle clockwise (corrects sensor mounted offset to starboard)  
**Negative value** = rotate counter-clockwise (corrects sensor mounted offset to port)

### Current Configuration

| Parameter | Value | Reason |
|-----------|-------|--------|
| `CALYPSO_WIND_OFFSET_DEG` | **+7°** | Masthead unit physically ~7° offset to starboard (measured 2026-06-28) |
| Applied since | 2026-06-28 | Diagnosed from asymmetric port/starboard tack angles in Grafana |
| Method | Software (before SK injection) | No firmware-level offset on Calypso UP10 |

### How the Correction Works

In `calypso_direct.py::decode_packet()`:

```python
wind_deg = raw_dir if wind_ms > 0.0 else 0  # Raw 0-359°

# Apply wind angle offset (corrects masthead misalignment)
if WIND_OFFSET_DEG != 0:
    wind_deg = int((wind_deg + WIND_OFFSET_DEG) % 360)

# Convert to radians and inject to Signal K
angle_rad = math.radians(wind_deg)
```

Example:
- Raw sensor reading (starboard): 45°
- Offset: +7°
- Published to Signal K: 45° + 7° = **52°** ✅

---

## 5. Re-calibration Procedure

**Scenario**: Wind data seems systematically offset after a rig change or sensor remount.

1. **Collect baseline data** (both tacks):
   - Sail port → note AWA in Grafana (e.g., 145°)
   - Sail starboard → note AWA (e.g., 215°)
   - Expected delta: ~70° (symmetric around 180°)

2. **Calculate asymmetry**:
   - If port AWA = 145° and starboard AWA = 210° (instead of 215°), asymmetry = 5°
   - Sensor is offset to **port** by ~5°

3. **Adjust offset value**:
   - Port offset → **decrease** `CALYPSO_WIND_OFFSET_DEG` (e.g., 7 → 2)
   - Starboard offset → **increase** `CALYPSO_WIND_OFFSET_DEG` (e.g., 7 → 12)

4. **Apply and verify**:
   ```bash
   # Edit service file
   sudo nano /etc/systemd/system/calypso_direct.service
   # Change: Environment="CALYPSO_WIND_OFFSET_DEG=2"
   
   # Restart
   sudo systemctl daemon-reload
   sudo systemctl restart calypso_direct
   
   # Repeat tacks and verify symmetry
   ```

---

## 6. BLE Protocol — Writable Characteristics

The Calypso UP10 exposes three writable GATT characteristics for runtime configuration.
**No persistent firmware storage** — values reset on power cycle.

| UUID | Name | Writable Values | Purpose |
|------|------|-----------------|---------|
| `0000a001-...` | Mode | `0x00` (SLEEP), `0x01` (LOW_POWER), `0x02` (NORMAL) | Power mode |
| `0000a002-...` | Rate | `0x01` (1 Hz), `0x04` (4 Hz), `0x08` (8 Hz) | Data rate |
| `0000a003-...` | Compass | `0x00` (OFF), `0x01` (ON) | 3-axis compass output |

**Startup configuration** (applied by `calypso_direct.py`):
- Mode → NORMAL
- Rate → 4 Hz (configurable via `CALYPSO_RATE_HZ`)
- Compass → OFF (prevents stale sentinel values -90/-90/360)

---

## 7. Signal K Data Paths

| SK Path | Unit | Formula | Notes |
|---------|------|---------|-------|
| `environment.wind.speedApparent` | m/s | `raw_speed ÷ 100` | Multiply by 1.94384 for knots |
| `environment.wind.angleApparent` | rad | `math.radians(wind_deg + offset) % 360` | **Offset-corrected**. Multiply by 180/π for degrees |
| `electrical.batteries.calypso.percent` | % | `raw_batt × 10` | 0–100% |
| `environment.outside.temperature` | K | `(raw_temp − 100) + 273.15` | Celsius: `raw_temp − 100` |

---

## 8. Pre-Race Verification Checklist

- [ ] BLE connection established (`journalctl -u calypso_direct` shows `[BLE_CONNECT] Connected ✅`)
- [ ] Wind data flowing (Grafana shows live angleApparent / speedApparent)
- [ ] Wind offset applied correctly (check via: `sudo systemctl cat calypso_direct | grep OFFSET`)
- [ ] Timeout threshold set (default 60s — increase to 120s if BLE is unstable)
- [ ] Heartbeat logging enabled (default 300s — reduces log spam)
- [ ] No L1 reconnects in journal (stable BLE link)
- [ ] Wind angles symmetric on port/starboard (within ±5°)

---

## 9. Troubleshooting

### BLE won't connect

**Error**: `[BLE_SCAN] Connecting to... [timeout]`

1. Check MAC address matches physical device (label on unit)
2. Restart service: `sudo systemctl restart calypso_direct`
3. If still failing, trigger L2 recovery:
   ```bash
   sudo systemctl restart calypso_direct
   # Check journal for: [L2_RECOVERY] bluetoothctl disconnect/remove
   ```
4. If BLE adapter dead, restart BlueZ: `sudo systemctl restart bluetooth`

### Wind angle jumps / noise

**Symptom**: Sudden 180° swings or random spikes

1. Check wind speed threshold: `wind_ms > 0.0` ignores direction when windless
2. Verify BLE link quality: large gaps in `[TIMING]` logs indicate radio interference
3. Increase `CALYPSO_RATE_HZ` from 4 to 8 Hz for smoother data
4. Check offset is correct (§4)

### Temperature or battery reading wrong

1. Verify packet decode: `[DATA_FIRST]` shows raw bytes
   - Byte [4] × 10 should match physical battery %
   - Byte [5] − 100 should match expected °C
2. If values inverted, check struct unpack order (unlikely — use reference firmware)

### High CPU from calypso_direct

1. Check BLE reconnect loop: `journalctl -u calypso_direct -f | grep L1`
2. If reconnecting repeatedly, increase `CALYPSO_DATA_TIMEOUT_S` to 120s
3. Reduce `CALYPSO_RATE_HZ` to 1 Hz (slower but more stable on weak antennas)

---

## 10. Performance Reference

**Tested Configuration** (2026-06-28, race-ready):

| Metric | Value | Notes |
|--------|-------|-------|
| BLE latency | ~10–50ms | Notify callback to SK UDP |
| Data rate | 4 Hz | 8 Hz possible, reduces reliability |
| CPU usage | <2% | Single Python process |
| Memory | ~30 MB | Minimal, no memory leaks (tested 24h continuous) |
| Uptime (last reboot) | Stable | 0 L2 failures since offset applied |

---

## References

- **Hardware**: [CALYPSO-UP10-DATASHEET.md](../HARDWARE/CALYPSO-UP10-DATASHEET.md)
- **Source Code**: [ble/calypso_direct.py](/ble/calypso_direct.py)
- **Service File**: [etc/systemd/system/calypso_direct.service](/etc/systemd/system/calypso_direct.service) (local only)
- **Signal K**: http://localhost:3000/signalk/v1/api/vessels/self/environment/wind

---

**Last Updated**: 2026-06-28  
**Status**: ✅ Operational for Block Island Race  
**Crew**: Denis + Anne-Sophie

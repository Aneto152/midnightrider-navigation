# ble/ — BLE Drivers for Midnight Rider

> Last updated: 2026-05-31  
> Architecture: unified drivers with shared ble_common.py infrastructure

Direct BLE daemon drivers for Midnight Rider sensors.  
Each driver is a standalone Python service managed by systemd.

---

### WIT Physical Mounting (Midnight Rider — confirmed 2026-05-31)

- **WIT-X axis** → PORT (babord)
- **WIT-Y axis** → MASTHEAD (upward, toward mast)
- **WIT-Z axis** → BOW (forward along centerline)
- **Installation Direction:** Vertical (Y=vertical/up axis)
- **MOUNT_Q:** identity (1.0, 0.0, 0.0, 0.0) — no rotation correction when WIT calibrated


## Architecture

```
BLE Sensors → [ble/ drivers] → Signal K UDP:4123 → SK → InfluxDB → Grafana
```

**Three integrated drivers:**

- **Calypso UP10 Anemometer** (F8:5F:12:9D:D2:EE)  
  → `calypso_direct.py` → wind speed/angle, battery %, temperature

- **WIT WT901BLECL IMU** (E9:10:DB:8B:CE:C7)  
  → `wit-ble-direct.py` → quaternion → attitude (roll/pitch/yaw), acceleration, heading

- **SOK SK12V100PC Battery BMS** (MAC via `SOK_BLE_ADDRESS`)  
  → `sok_direct.py` → voltage/current/power, SoC, cell voltages, cycles

**Shared infrastructure:** All drivers use `ble_common.py` for logging, singleton, SK publishing, BLE adapter checks, BT zombie recovery, and graceful shutdown.

---

## Files

### ble_common.py — Shared Infrastructure

Imported by all drivers. Provides:

| Function | Purpose |
|---|---|
| `setup_logger(name)` | RotatingFileHandler (10MB, 3 backups) → logs/services/ |
| `acquire_singleton(pid, log)` | One instance per service via PID file |
| `release_singleton(pid, log)` | Clean PID removal on exit |
| `publish_delta(label, values, log)` | UDP:4123 → Signal K |
| `check_ble_adapter()` | Verify hci0 is UP RUNNING |
| `check_sk_reachable()` | Verify SK UDP port is listening |
| `bt_recovery(mac, log)` | bluetoothctl disconnect + remove for zombie BLE sessions |
| `setup_signal_handlers(fn, log)` | SIGTERM/SIGINT → graceful BLE disconnect (no sys.exit) |

---

### calypso_direct.py — Calypso UP10 Wind Sensor

| Field | Value |
|---|---|
| **Device** | Calypso UP10 anemometer |
| **MAC** | F8:5F:12:9D:D2:EE (env: `CALYPSO_BLE_ADDRESS`) |
| **BLE Protocol** | Auto-notify (no commands) @ 4 Hz |
| **Notify UUID** | 00002a39-0000-1000-8000-00805f9b34fb |
| **Service** | calypso_direct.service |
| **SK Output** | environment.wind.*, electrical.batteries.calypso.*, environment.outside.temperature |
| **Status** | ✅ PRODUCTION |

**Packet Format:** 10 bytes little-endian `<HHBBBBH`
- [0-1] wind speed (÷100 → m/s)
- [2-3] direction (0-359°)
- [4] battery (×10 → %)
- [5] temperature (−100 → °C)

**Recovery:** L1 backoff (5s-60s) + L2 clean exit (L2_threshold=10) + BT zombie recovery + startup-only bluetoothctl remove (NOT per-connection — breaks bond)

---

### wit-ble-direct.py — WIT WT901BLECL IMU

| Field | Value |
|---|---|
| **Device** | WIT WT901BLECL 9-DOF IMU (quaternion native) |
| **MAC** | E9:10:DB:8B:CE:C7 (env: `WIT_BLE_ADDRESS`) |
| **BLE Protocol** | Notify (ffe4-9a34fb) / Write (ffe9-9a34fb) |
| **Init Sequence** | State machine: UNINITIALIZED → send ENABLE_QUAT once → WAIT_RECONNECT → subscribe |
| **Output Rate** | 10 Hz (env: `WIT_OUTPUT_RATE_HZ`) |
| **Mounting** | X=port, Y=masthead(up), Z=bow — MOUNT_Q=identity (env: `WIT_MOUNT_Q`) |
| **Service** | wit-ble-direct.service |
| **SK Output** | navigation.attitude.*, navigation.headingMagnetic, navigation.acceleration.*, navigation.rateOfTurn |
| **Status** | ✅ PRODUCTION |

**UUID Note:** WIT WT901BLECL uses `9a34fb` base (NOT standard Bluetooth SIG `9b34fb`).

**Protocol:**
- Command: `FF AA 27 51 00` = one-shot quaternion request
- WIT responds with one 0x71 packet per request
- State machine prevents reset loop (command sent only once on first connection)

**Coordinate Transform:**
- Mounted vertically on companionway bulkhead
- Native quaternion output (Kalman filter) → boat-frame Euler angles
- Mounting correction applied in quaternion space (no gimbal lock singularity)

**Axis Mapping (Confirmed 2026-05-31, 7 physical orientations):**
- Euler-X formula → SK navigation.headingMagnetic (0=N, +π/2=E, normalized [0,2π])
- Euler-Y formula → SK navigation.attitude.roll (heel: +π/2=starboard, -π/2=port)
- Euler-Z formula → SK navigation.attitude.pitch (trim: +π/2=bow up)
- Q3=w convention (scalar LAST at offset 10) confirmed

---

### sok_direct.py — SOK SK12V100PC Battery BMS

| Field | Value |
|---|---|
| **Device** | SOK SK12V100PC LiFePO4 100Ah BMS (JBD chip) |
| **MAC** | Set in .env: `SOK_BLE_ADDRESS=XX:XX:XX:XX:XX:XX` (discovery required) |
| **BLE Protocol** | Request/response (CRC8-checksummed) @ 0.2 Hz (1 read per 5s) |
| **Service UUID** | 0000FFF0-0000-1000-8000-00805F9B34FB |
| **Notify UUID** | 0000FFF1-0000-1000-8000-00805F9B34FB (RX) |
| **Write UUID** | 0000FFF2-0000-1000-8000-00805F9B34FB (TX) |
| **Commands** | cmd_info (0xEE C1 00 00 00) → 0xCCF0 status  |
| | cmd_detail (0xEE C2 00 00 00) → 0xCCF4 cell voltages |
| | cmd_protection (0xEE C4 00 00 00) → 0xCCF5 CMOS/DMOS states |
| **CRC8** | LSB-first, polynomial 0x8C (per ABC-BMS app spec) |
| **Service** | sok_direct.service (create from template) |
| **SK Output** | electrical.batteries.house.*, electrical.batteries.house.cells.0-3.voltage |
| **Status** | ✅ TEMPLATE (MAC discovery required) |

**Response Format (0xCCF0):** 18 bytes
- [0-1] message type (0xCCF0, big-endian)
- [2-4] total voltage (int24 LE, mV)
- [5-7] current (int24 LE, µA → A)
- [8-10] power (int24 LE, W)
- [11-13] avg current (int24 LE, µA)
- [14-15] cycle count (uint16 LE)
- [16-17] SoC (uint16 LE, %)

**Notes:**
- Storage mode: BMS enters deep sleep (BLE invisible) after prolonged inactivity  
  Wake by connecting LiFePO4 charger briefly
- 0V at terminals = storage mode, not failure
- Read rate limited to 0.2 Hz by BLE handshake overhead

---

## Recovery Mechanisms

All three drivers implement a consistent two-level recovery:

### L1: BLE Reconnect (Exponential Backoff)

- **Trigger:** Connection failure
- **Backoff:** 5s → 10s → 20s → 40s → 60s (max)
- **Action:** Retry `BleakClient(MAC)` connect
- **Threshold:** 3-5 failures before L2

**Examples in logs:**
```
[L1] Connection failed (1): Device not found
[L1] Reconnecting in 5s...
[L1] Connection failed (2): ...
[L1] Reconnecting in 10s...
```

### L2: Clean Exit + systemd Restart

- **Trigger:** L1_FAIL_COUNT ≥ L2_THRESHOLD
- **Action:** Log warning, break main loop (clean exit), release PID file
- **Result:** systemd `Restart=on-failure` restarts service after 5s
- **Benefit:** No hci0 disruption (other drivers unaffected)

**Examples in logs:**
```
[L2] 5 failures — clean exit for systemd restart
[L2] hci0 NOT reset: would disrupt [Calypso|WIT|SOK]
[SHUTDOWN] ... stopped — PID released
```

### L3: BT Zombie Recovery (Within L1)

- **Trigger:** Device was connected before, now "not found" error, 3+ failures
- **Action:** `bluetoothctl disconnect MAC` + `bluetoothctl remove MAC` (clears BlueZ cache)
- **Result:** Fresh BLE discovery on next connect, L1 counters reset
- **Benefit:** Handles BLE dead-lock state (device invisible but still paired)

**Example:**
```
[BT_RECOVERY] Zombie BLE session detected after 3 failures
[BT_RECOVERY] Running: bluetoothctl disconnect E9:10:DB:8B:CE:C7
[BT_RECOVERY] disconnect: [BlueZ output...]
[BT_RECOVERY] Running: bluetoothctl remove ...
[BT_RECOVERY] remove: Device removed
[BT_RECOVERY] Cleared — retrying connection
```

---

## Systemd Services

Each driver has a corresponding `.service` file in `/etc/systemd/system/`:

```bash
systemctl status calypso_direct
systemctl status wit-ble-direct
# systemctl status sok_direct  (not started by default — MAC placeholder)
```

**Common commands:**

```bash
# View logs (follow)
journalctl -u wit-ble-direct -f

# View recent logs (last 50 lines)
journalctl -u wit-ble-direct -n 50

# Restart service
sudo systemctl restart wit-ble-direct

# Check startup status
systemctl is-active wit-ble-direct

# Watch logs while starting
sudo systemctl restart wit-ble-direct && sleep 1 && journalctl -u wit-ble-direct -f
```

---

## Environment Variables

All drivers respect `.env` configuration:

| Variable | Driver | Default | Purpose |
|---|---|---|---|
| `CALYPSO_BLE_ADDRESS` | calypso | F8:5F:12:9D:D2:EE | Device MAC |
| `CALYPSO_RATE_HZ` | calypso | 4 | Data rate Hz (valid: 1/4/8 — 8Hz oversaturates BLE CI) |
| `CALYPSO_DATA_TIMEOUT_S` | calypso | 60 | Staleness threshold |
| `CALYPSO_L2_THRESHOLD` | calypso | 10 | L1 failures before L2 |
| `WIT_BLE_ADDRESS` | wit | E9:10:DB:8B:CE:C7 | Device MAC |
| `WIT_MOUNT_Q` | wit | 1.0,0.0,0.0,0.0 | Mounting quaternion (w,x,y,z) — identity when calibrated |
| `WIT_OUTPUT_RATE_HZ` | wit | 10 | Output rate Hz |
| `WIT_L2_THRESHOLD` | wit | 5 | L1 failures before L2 |
| `SOK_BLE_ADDRESS` | sok | XX:XX:XX:XX:XX:XX | ⚠️ REQUIRED: set via discovery |
| `SOK_POLL_S` | sok | 5 | Poll interval (s) |
| `SOK_DATA_TIMEOUT_S` | sok | 120 | Staleness threshold |
| `SOK_L2_THRESHOLD` | sok | 10 | L1 failures before L2 |

---

## Testing & Debugging

### Quick Health Check

```bash
# All logs at once
tail -5 logs/services/{calypso,wit,sok}-direct.log

# BLE adapter status
hciconfig
bluetoothctl list

# Signal K reachability
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude/roll | jq .
```

### Zombie Recovery Trigger (Manual)

```bash
# Clear WIT from BlueZ cache (for testing L3 recovery)
bluetoothctl remove E9:10:DB:8B:CE:C7

# Service auto-recovers via L3 on next connection attempt
journalctl -u wit-ble-direct -f  # Watch recovery
```

### Grep Patterns

```bash
# See all DATA_OUT packets
grep DATA_OUT logs/services/wit-ble-direct.log

# See all heartbeats
grep HEARTBEAT logs/services/calypso-direct.log

# See all recovery events
grep -E "L1|L2|BT_RECOVERY" logs/services/*.log
```

---

## Architecture Evolution

| Date | Event | Details |
|---|---|---|
| 2026-05-29 | WIT state machine | Prevent reset loop on reconnect |
| 2026-05-30 | ble_common.py | Extract shared infrastructure |
| 2026-05-30 | Phase 1 refactor | calypso_direct.py uses ble_common |
| 2026-05-30 | Phase 2 refactor | wit-ble-direct.py uses ble_common |
| 2026-05-30 | SOK template | sok_direct.py ready (MAC placeholder) |
| 2026-05-31 | WIT Q3=w fix | Confirmed scalar-last convention, unit test proof |
| 2026-05-31 | WIT Euler mapping | Euler-X=heading, Y=heel, Z=pitch (7 orientations verified) |
| 2026-05-31 | WIT MOUNT_Q=identity | No correction needed with proper calibration |
| 2026-05-31 | Calypso rate 8Hz | Valid rates: 1/4/8Hz — 10Hz NOT supported (0x0A ignored) |
| 2026-05-31 | Calypso BlueZ fix | sleep 2 after remove, startup-only remove (bond stability) |
| 2026-05-31 | Calypso L2=10 | Faster systemd restart cycle (was 20) |
| 2026-05-31 | Calypso watchdog fix | _stats[last_data_ts] reset after start_notify (no false-positive) |
| 2026-05-31 | Calypso rate 4Hz default | 8Hz oversaturates BLE connection interval — reverted to proven 4Hz stable |

---

## Related Documentation

- **Hardware:** [docs/HARDWARE/](../docs/HARDWARE/)
  - WIT-WT901BLECL-DATASHEET.md
  - CALYPSO-UP10-DATASHEET.md
  - SOK-BMS-BLE-PROTOCOL.md

- **Operations:** [docs/OPERATIONS/](../docs/OPERATIONS/)
  - FIELD-TEST-CHECKLIST-2026-05-19.md
  - RACE-DAY-CHECKLIST-2026-05-22.md

- **Integration:** [docs/INTEGRATION/](../docs/INTEGRATION/)
  - WIT-INTEGRATION-GUIDE.md
  - CALYPSO-INTEGRATION-GUIDE.md

---

**Status:** ✅ Production ready (WIT + Calypso), SOK template (MAC discovery required)  
**Next:** Discover SOK MAC, set `SOK_BLE_ADDRESS`, enable service  
**Race Day:** May 22, 2026 — Block Island Race (186 nm, Stamford CT)  

⛵ **All BLE drivers unified, self-healing, production-ready.**

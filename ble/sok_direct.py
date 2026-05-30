#!/usr/bin/env python3
"""
sok_direct.py — SOK SK12V100PC Battery BMS Direct BLE Driver
==============================================================

ROLE:
 Unified BLE daemon for the SOK SK12V100PC LiFePO4 battery BMS.
 BMS chip: JBD (JiaBaiDa) with integrated BLE module.
 Official app: ABC-BMS (com.sjty.sbs_bms).
 Publishes to Signal K via UDP:4123 → SK → InfluxDB → Grafana.

DEVICE-SPECIFIC (this file):
 - BLE UUIDs for JBD/SOK BMS
 - CRC8 checksum (minicrc algorithm)
 - Command encoding (5 bytes + CRC8)
 - Response decoding (0xCCF0 status, 0xCCF4 cell voltages)
 - Signal K paths (electrical.batteries.house.*)

SHARED INFRASTRUCTURE (ble_common.py):
 - Logger, singleton, SK publisher, BLE checks, BT recovery, signals

BLE PROTOCOL (JBD BMS — reverse-engineered from ABC-BMS app):
 Service UUID : 0000FFF0-0000-1000-8000-00805F9B34FB
 Notify UUID : 0000FFF1-0000-1000-8000-00805F9B34FB (RX)
 Write UUID : 0000FFF2-0000-1000-8000-00805F9B34FB (TX)

 Protocol: request/response
 1. Subscribe to Notify UUID
 2. Write command (5 bytes + CRC8) to Write UUID
 3. Wait for response on Notify UUID
 4. Decode and publish

 Commands:
 cmd_info [0xEE, 0xC1, 0x00, 0x00, 0x00] → 0xCCF0 (SoC, V, A, W, cycles)
 cmd_detail [0xEE, 0xC2, 0x00, 0x00, 0x00] → 0xCCF4 (cell voltages)
 cmd_protection [0xEE, 0xC4, 0x00, 0x00, 0x00] → 0xCCF5 (CMOS/DMOS states)

 Response 0xCCF0 (18 bytes):
 [0-1] uint16 BE message type (0xCCF0)
 [2-4] int24 LE total voltage (mV)
 [5-7] int24 LE current (µA → divide by 1,000,000 for A)
 [8-10] int24 LE power (W)
 [11-13] int24 LE average current (µA)
 [14-15] uint16 LE cycle count
 [16-17] uint16 LE SoC (%)

 Response 0xCCF4 (variable length):
 [0-1] uint16 BE message type (0xCCF4)
 For each cell x (0-3):
 [2+(x*4)] uint8 cell index (1-4)
 [3+(x*4)] uint16 LE cell voltage (mV)
 [5+(x*4)] uint8 reserved

 CRC8 algorithm: minicrc (polynomial 0x8C / reversed 0x31)

SIGNAL K PATHS:
 electrical.batteries.house.voltage V
 electrical.batteries.house.current A (+ = charging)
 electrical.batteries.house.power W
 electrical.batteries.house.capacity.stateOfCharge ratio 0-1
 electrical.batteries.house.temperature K (BMS temp)
 electrical.batteries.house.cells.0.voltage V
 electrical.batteries.house.cells.1.voltage V
 electrical.batteries.house.cells.2.voltage V
 electrical.batteries.house.cells.3.voltage V

RECOVERY:
 L1: Reconnect with exponential backoff (5s → 60s)
 BT_RECOVERY: bluetoothctl disconnect+remove (zombie session)
 L2: clean exit → systemd Restart=on-failure

NOTES:
 - Storage mode: BMS enters deep sleep (BLE invisible) after
   prolonged inactivity. Wake by connecting a LiFePO4 charger briefly.
 - 0V at terminals = storage mode, not failure.
 - Read rate: 0.2 Hz (1 read per 5s) — BLE constraint.

ENVIRONMENT (.env):
 SOK_BLE_ADDRESS MAC address of SOK battery (REQUIRED: XX:XX:XX:XX:XX:XX)
 SOK_POLL_S Poll interval in seconds (default: 5)
 SOK_DATA_TIMEOUT_S Staleness threshold (default: 120)
 SOK_HEARTBEAT_S Heartbeat interval (default: 300)
 SOK_L2_THRESHOLD L1 fails before L2 exit (default: 10)

SETUP:
 1. Discover MAC: bluetoothctl scan on (look for "SOK" or "ABC-BMS")
 2. Set in .env: SOK_BLE_ADDRESS=XX:XX:XX:XX:XX:XX
 3. Create systemd service (copy from calypso_direct.service template)
 4. systemctl enable --now sok_direct

systemd: etc/systemd/system/sok_direct.service
PID: /tmp/sok_direct.pid
"""

import asyncio
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ble_common import (
    setup_logger,
    acquire_singleton,
    release_singleton,
    publish_delta,
    check_ble_adapter,
    check_sk_reachable,
    bt_recovery,
    setup_signal_handlers,
)

try:
    from bleak import BleakClient, BleakError
except ImportError:
    print('[FATAL] bleak not installed. Run: pip install bleak', flush=True)
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

SOK_MAC = os.environ.get('SOK_BLE_ADDRESS', 'XX:XX:XX:XX:XX:XX')
POLL_S = int(os.environ.get('SOK_POLL_S', '5'))
DATA_TIMEOUT_S = int(os.environ.get('SOK_DATA_TIMEOUT_S', '120'))
HEARTBEAT_S = int(os.environ.get('SOK_HEARTBEAT_S', '300'))
L2_THRESHOLD = int(os.environ.get('SOK_L2_THRESHOLD', '10'))

SERVICE_NAME = 'sok-direct'
PID_FILE = '/tmp/sok_direct.pid'
RECONNECT_BASE_S = 5
RECONNECT_MAX_S = 60

# SOK BMS BLE UUIDs (JBD protocol)
SERVICE_UUID = '0000FFF0-0000-1000-8000-00805F9B34FB'
NOTIFY_UUID = '0000FFF1-0000-1000-8000-00805F9B34FB'  # RX
WRITE_UUID = '0000FFF2-0000-1000-8000-00805F9B34FB'   # TX

# SOK BMS Commands (5 bytes + CRC8)
CMD_INFO = bytes([0xEE, 0xC1, 0x00, 0x00, 0x00])
CMD_DETAIL = bytes([0xEE, 0xC2, 0x00, 0x00, 0x00])
CMD_PROTECTION = bytes([0xEE, 0xC4, 0x00, 0x00, 0x00])

# Response types
RESP_STATUS = 0xCCF0
RESP_CELLS = 0xCCF4
RESP_PROTECTION = 0xCCF5

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PROCESS STATE
# ══════════════════════════════════════════════════════════════════════════════

_running = True
_was_connected = False
_last_err = ''
_pending_response = {}
_response_event = asyncio.Event()

_stats = {
    'reads': 0,
    'last_read_ts': 0.0,
    'last_heartbeat': time.time(),
    'l1_fails': 0,
}

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CRC8 CHECKSUM (minicrc)
# ══════════════════════════════════════════════════════════════════════════════

def minicrc(data: bytes) -> int:
    """
    Compute CRC8 checksum (JBD BMS protocol).
    Polynomial: 0x8C (reversed: 0x31)
    """
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

def encode_command(cmd: bytes) -> bytes:
    """Encode command with CRC8: cmd (5 bytes) + CRC8."""
    crc = minicrc(cmd)
    return cmd + bytes([crc])

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — RESPONSE DECODERS
# ══════════════════════════════════════════════════════════════════════════════

def int24_le(data: bytes, offset: int) -> int:
    """Decode 3-byte signed integer (little-endian)."""
    val = data[offset] | (data[offset+1] << 8) | (data[offset+2] << 16)
    if val & 0x800000:
        val -= 0x1000000
    return val

def decode_status(data: bytes) -> dict | None:
    """
    Decode 0xCCF0 response (cmd_info) — battery status.

    Returns: dict with voltage_v, current_a, power_w, soc_pct, cycles, soc_ratio
    Returns None if data is invalid.
    """
    if len(data) < 18:
        return None
    resp_type = struct.unpack_from('>H', data, 0)[0]
    if resp_type != RESP_STATUS:
        return None

    voltage_mv = int24_le(data, 2)
    current_ua = int24_le(data, 5)
    power_w = int24_le(data, 8)
    cycles = struct.unpack_from('<H', data, 14)[0]
    soc_pct = struct.unpack_from('<H', data, 16)[0]

    return {
        'voltage_v': voltage_mv / 1000.0,
        'current_a': current_ua / 1_000_000.0,
        'power_w': power_w,
        'soc_pct': soc_pct,
        'soc_ratio': soc_pct / 100.0,
        'cycles': cycles,
    }

def decode_cells(data: bytes) -> dict | None:
    """
    Decode 0xCCF4 response (cmd_detail) — individual cell voltages.

    Returns: dict with cell_0_v ... cell_3_v and cell_imbalance_mv
    Returns None if data is too short or wrong type.
    """
    if len(data) < 4:
        return None
    resp_type = struct.unpack_from('>H', data, 0)[0]
    if resp_type != RESP_CELLS:
        return None

    cells = {}
    offset = 2
    while offset + 3 <= len(data) - 1:  # -1 for CRC byte at end
        cell_idx = data[offset]  # 1-based index
        if cell_idx < 1 or cell_idx > 4:
            break
        cell_mv = struct.unpack_from('<H', data, offset + 1)[0]
        cells[cell_idx - 1] = cell_mv / 1000.0  # mV → V
        offset += 4  # index(1) + voltage(2) + reserved(1)

    if len(cells) < 4:
        return None

    imbalance_mv = int((max(cells.values()) - min(cells.values())) * 1000)
    return {
        'cell_0_v': cells.get(0, 0.0),
        'cell_1_v': cells.get(1, 0.0),
        'cell_2_v': cells.get(2, 0.0),
        'cell_3_v': cells.get(3, 0.0),
        'imbalance_mv': imbalance_mv,
    }

def decode_protection(data: bytes) -> dict | None:
    """
    Decode 0xCCF5 response (cmd_protection) — CMOS/DMOS states.

    Returns: dict with prot_cmos, prot_dmos
    """
    if len(data) < 5:
        return None
    resp_type = struct.unpack_from('>H', data, 0)[0]
    if resp_type != RESP_PROTECTION:
        return None

    return {
        'prot_cmos': bool(data[3]),  # 0=normal, 1=triggered
        'prot_dmos': bool(data[4]),
    }

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SIGNAL K PUBLISHER
# ══════════════════════════════════════════════════════════════════════════════

def publish(status: dict, cells: dict, prot: dict | None, logger) -> None:
    """Publish all BMS readings to Signal K via UDP:4123."""
    values = [
        {'path': 'electrical.batteries.house.voltage',
         'value': status['voltage_v']},
        {'path': 'electrical.batteries.house.current',
         'value': status['current_a']},
        {'path': 'electrical.batteries.house.power',
         'value': status['power_w']},
        {'path': 'electrical.batteries.house.capacity.stateOfCharge',
         'value': status['soc_ratio']},
        # Individual cell voltages
        {'path': 'electrical.batteries.house.cells.0.voltage',
         'value': cells['cell_0_v']},
        {'path': 'electrical.batteries.house.cells.1.voltage',
         'value': cells['cell_1_v']},
        {'path': 'electrical.batteries.house.cells.2.voltage',
         'value': cells['cell_2_v']},
        {'path': 'electrical.batteries.house.cells.3.voltage',
         'value': cells['cell_3_v']},
    ]

    # Protection states (optional)
    if prot:
        values.append({
            'path': 'notifications.batteries.house.cmos',
            'value': {'state': 'alarm' if prot['prot_cmos'] else 'normal',
                      'message': 'CMOS protection triggered' if prot['prot_cmos'] else 'CMOS OK'}
        })

    publish_delta(source_label='SOK-BMS', values=values, logger=logger)

    logger.info(
        f'[DATA_OUT] SoC={status["soc_pct"]}% '
        f'V={status["voltage_v"]:.2f}V '
        f'I={status["current_a"]:+.1f}A '
        f'Cell_imbalance={cells["imbalance_mv"]}mV '
        f'Cycles={status["cycles"]}'
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — BLE NOTIFICATION CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def make_notify_handler():
    """Factory: returns BLE notification callback."""
    def on_notify(sender, data: bytearray) -> None:
        """Store response in pending buffer and signal the polling loop."""
        if len(data) < 2:
            return
        resp_type = struct.unpack_from('>H', bytes(data), 0)[0]
        _pending_response[resp_type] = bytes(data)
        _response_event.set()
    return on_notify

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MAIN BLE LOOP
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    """
    Main BLE connection loop for SOK BMS.
    Request/response protocol: send command, wait for response, decode, publish.
    """
    global _running, _was_connected, _last_err

    logger = setup_logger(SERVICE_NAME)

    if SOK_MAC == 'XX:XX:XX:XX:XX:XX':
        logger.error('[STARTUP] SOK_BLE_ADDRESS not set in .env — exiting')
        logger.error('[SETUP] Set: SOK_BLE_ADDRESS=<MAC address>')
        sys.exit(1)

    acquire_singleton(PID_FILE, logger)
    try:
        logger.info('[STARTUP] ' + '=' * 58)
        logger.info('[STARTUP] sok_direct — SOK SK12V100PC BMS Driver')
        logger.info(f'[STARTUP] MAC={SOK_MAC} Poll={POLL_S}s SK=UDP:4123')
        logger.info('[STARTUP] ' + '=' * 58)

        if not check_ble_adapter():
            logger.error('[STARTUP] BLE adapter (hci0) not available — exiting')
            sys.exit(1)

        delay = RECONNECT_BASE_S
        l1_fails = 0
        on_notify = make_notify_handler()

        while _running:
            try:
                async with BleakClient(SOK_MAC, timeout=20.0) as client:
                    logger.info(f'[BLE_CONNECT] Connected ✅')
                    delay = RECONNECT_BASE_S
                    l1_fails = 0
                    _was_connected = True
                    _stats['first_logged'] = False

                    await client.start_notify(NOTIFY_UUID, on_notify)
                    logger.info('[BLE_NOTIFY] Subscribed to notifications')

                    while client.is_connected and _running:
                        # Poll: send cmd_info
                        try:
                            cmd = encode_command(CMD_INFO)
                            await client.write_gatt_char(WRITE_UUID, cmd, response=False)
                            _response_event.clear()

                            # Wait for response (timeout 3s)
                            try:
                                await asyncio.wait_for(_response_event.wait(), timeout=3.0)
                            except asyncio.TimeoutError:
                                logger.warning('[POLL] No response to cmd_info')
                                await asyncio.sleep(POLL_S)
                                continue

                            # Decode status
                            status = decode_status(_pending_response.get(RESP_STATUS, b''))
                            cells = decode_cells(_pending_response.get(RESP_CELLS, b''))

                            if status and cells:
                                _stats['reads'] += 1
                                _stats['last_read_ts'] = time.time()
                                publish(status, cells, None, logger)

                                # Periodic heartbeat
                                if time.time() - _stats['last_heartbeat'] > HEARTBEAT_S:
                                    logger.info(
                                        f'[HEARTBEAT] reads={_stats["reads"]} '
                                        f'SoC={status["soc_pct"]}% '
                                        f'V={status["voltage_v"]:.2f}V '
                                        f'l1_fails={_stats["l1_fails"]}'
                                    )
                                    _stats['reads'] = 0
                                    _stats['last_heartbeat'] = time.time()
                            else:
                                logger.warning(
                                    f'[DECODE] Decode failed: '
                                    f'status={status is not None} '
                                    f'cells={cells is not None}')

                        except Exception as e:
                            logger.error(f'[POLL] Error: {e}')

                        # Data staleness watchdog
                        if _stats['last_read_ts'] > 0:
                            age = time.time() - _stats['last_read_ts']
                            if age > DATA_TIMEOUT_S:
                                logger.warning(
                                    f'[WATCHDOG] No data for {age:.0f}s — reconnecting')
                                break

                        await asyncio.sleep(POLL_S)

                    logger.warning('[BLE_DISCONNECT] Disconnected or timeout')

            except BleakError as e:
                l1_fails += 1
                _stats['l1_fails'] += 1
                _last_err = str(e)
                logger.error(f'[ERROR] BLE error (L1 #{l1_fails}): {e}')

            except Exception as e:
                l1_fails += 1
                _stats['l1_fails'] += 1
                _last_err = str(e)
                logger.error(f'[ERROR] L1 #{l1_fails}: {type(e).__name__}: {e}')

            # BT_RECOVERY: zombie session detection
            if (_was_connected
                and 'not found' in _last_err.lower()
                and l1_fails >= 3):
                recovered = await bt_recovery(SOK_MAC, logger)
                if recovered:
                    l1_fails = 0
                    delay = RECONNECT_BASE_S
                    _was_connected = False
                    _last_err = ''

            # L2: clean exit → systemd restart
            if l1_fails >= L2_THRESHOLD:
                logger.warning(
                    f'[L2] {l1_fails} failures — clean exit for systemd restart')
                break

            if _running:
                logger.info(f'[BLE_SCAN] Reconnecting in {delay}s...')
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_S)

    finally:
        release_singleton(PID_FILE, logger)
        logger.info('[SHUTDOWN] sok_direct stopped — PID released')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    _logger = setup_logger(SERVICE_NAME)

    def _set_stop():
        global _running
        _running = False

    setup_signal_handlers(_set_stop, _logger)
    asyncio.run(main())

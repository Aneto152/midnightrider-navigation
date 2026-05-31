#!/usr/bin/env python3
"""
calypso_direct.py — Calypso UP10 Anemometer Direct BLE Driver
================================================================

ROLE:
 Unified, self-contained BLE daemon for the Calypso UP10.
 Replaces: calypso-anemometer pip package.
 ONE script, ONE service, NO subprocess, NO external watchdog.

DEVICE-SPECIFIC (this file):
 - BLE UUIDs for Calypso UP10
 - Packet decoding (10-byte little-endian struct)
 - Device configuration (mode, rate, compass off)
 - Signal K paths (wind, battery, temperature)

SHARED INFRASTRUCTURE (ble_common.py):
 - Logger setup (RotatingFileHandler)
 - Singleton (PID file)
 - SK UDP publisher (UDP:4123)
 - BLE adapter check
 - BT zombie recovery (bluetoothctl disconnect/remove)
 - Graceful signal handlers (no sys.exit — prevents BLE zombie)

BLE PROTOCOL (Calypso UP10):
 Notify UUID : 00002a39-0000-1000-8000-00805f9b34fb
 Mode UUID : 0000a001-0000-1000-8000-00805f9b34fb
 Rate UUID : 0000a002-0000-1000-8000-00805f9b34fb
 Compass UUID: 0000a003-0000-1000-8000-00805f9b34fb

 Packet: 10 bytes, little-endian <HHBBBBH
 [0-1] wind_speed uint16 ÷ 100 → m/s
 [2-3] wind_dir uint16 → degrees 0-359
 [4] battery uint8 × 10 → %
 [5] temperature uint8 − 100 → °C
 [6-9] compass (disabled at startup → sentinel values)

 Calypso quirk: wind_direction=0 forced when wind_speed=0.
 Compass disabled at startup → no sentinel values (-90/-90/360).

SIGNAL K (UDP:4123):
 environment.wind.speedApparent m/s
 environment.wind.angleApparent rad (-π to +π)
 electrical.batteries.calypso.percent %
 environment.outside.temperature K

RECOVERY:
 L1: BLE reconnect (backoff 5s → 60s)
 BT_RECOVERY: bluetoothctl disconnect+remove (zombie session, own MAC only)
 L2: clean exit → systemd Restart=on-failure
 hci0 NOT reset: would disrupt WIT BLE connection

ENVIRONMENT (.env):
 CALYPSO_BLE_ADDRESS MAC address (default: F8:5F:12:9D:D2:EE)
 CALYPSO_RATE_HZ Data rate 1|4|8 (default: 8) — 10Hz NOT supported by UP10 firmware
 CALYPSO_DATA_TIMEOUT_S Staleness threshold (default: 60)
 CALYPSO_HEARTBEAT_S Heartbeat interval (default: 300)
 CALYPSO_RECONNECT_MAX_S Max backoff (default: 60)
 CALYPSO_L2_THRESHOLD L1 fails before L2 (default: 20)
 SK_UDP_HOST Signal K UDP host (default: 127.0.0.1)
 SK_UDP_PORT Signal K UDP port (default: 4123)

systemd: etc/systemd/system/calypso_direct.service
PID: /tmp/calypso_direct.pid
"""

import asyncio
import math
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
# All parameters via .env — never hardcode values here.
# ══════════════════════════════════════════════════════════════════════════════

CALYPSO_MAC = os.environ.get('CALYPSO_BLE_ADDRESS', 'F8:5F:12:9D:D2:EE')
RATE_HZ = int(os.environ.get('CALYPSO_RATE_HZ', '8'))  # 8Hz = max confirmed rate
DATA_TIMEOUT_S = int(os.environ.get('CALYPSO_DATA_TIMEOUT_S', '60'))
HEARTBEAT_S = int(os.environ.get('CALYPSO_HEARTBEAT_S', '300'))
RECONNECT_MAX_S = int(os.environ.get('CALYPSO_RECONNECT_MAX_S', '60'))
L2_THRESHOLD = int(os.environ.get('CALYPSO_L2_THRESHOLD', '10'))  # Lowered: 20→10 for faster recovery

SERVICE_NAME = 'calypso-direct'
PID_FILE = '/tmp/calypso_direct.pid'
RECONNECT_BASE_S = 5

# Calypso UP10 BLE UUIDs
UUID_DATA = '00002a39-0000-1000-8000-00805f9b34fb'
UUID_MODE = '0000a001-0000-1000-8000-00805f9b34fb'
UUID_RATE = '0000a002-0000-1000-8000-00805f9b34fb'
UUID_COMPASS = '0000a003-0000-1000-8000-00805f9b34fb'

RATE_MAP = {1: 0x01, 4: 0x04, 8: 0x08}  # 10Hz NOT supported — firmware ignores 0x0A

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PROCESS STATE
# Module-level globals for signal handler access.
# ══════════════════════════════════════════════════════════════════════════════

_running = True  # Set to False by SIGTERM/SIGINT for graceful BLE disconnect
_was_connected = False  # BT recovery: did Calypso ever connect this session?
_last_err = ''  # BT recovery: last BLE error string

_stats = {
    'packets': 0,
    'last_data_ts': 0.0,
    'last_heartbeat': time.time(),
    'first_logged': False,
    'l1_fails': 0,
}

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CALYPSO PACKET DECODER
# Ref: github.com/maritime-labs/calypso-anemometer (MIT, 2022)
# ══════════════════════════════════════════════════════════════════════════════

def decode_packet(data: bytes) -> dict | None:
    """
    Decode Calypso UP10 10-byte BLE notification.

    Struct layout <HHBBBBH (little-endian):
    [0-1] wind_speed uint16 ÷ 100 m/s
    [2-3] wind_dir uint16 degrees 0-359 (0=headwind)
    [4] battery uint8 × 10 % (0-100)
    [5] temperature uint8 − 100 °C
    [6] roll/[7]pitch/[8-9]heading IGNORED (compass off → sentinel values)

    Calypso quirk: wind_direction=0 when wind_speed=0 (avoid stale direction).
    Returns None if packet is malformed.
    """
    if len(data) < 10:
        return None
    try:
        fields = struct.unpack_from('<HHBBBBH', data)
        raw_speed, raw_dir, raw_batt, raw_temp = (
            fields[0], fields[1], fields[2], fields[3]
        )
        wind_ms = raw_speed / 100.0
        wind_deg = raw_dir if wind_ms > 0.0 else 0  # Calypso quirk
        batt_pct = raw_batt * 10
        temp_c = raw_temp - 100

        # Convert wind angle: 0-359° → radians (-π to +π)
        # 0° = headwind, positive = starboard, negative = port
        angle_rad = math.radians(wind_deg)
        if angle_rad > math.pi:
            angle_rad -= 2.0 * math.pi

        return {
            'wind_ms': wind_ms,
            'angle_rad': angle_rad,
            'batt_pct': batt_pct,
            'temp_k': temp_c + 273.15,
            # Debug fields
            '_knots': wind_ms * 1.94384,
            '_dir_deg': wind_deg,
        }
    except struct.error as e:
        return None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — SIGNAL K PUBLISHER
# Uses publish_delta() from ble_common (UDP:4123).
# ══════════════════════════════════════════════════════════════════════════════

def publish(data: dict, logger) -> None:
    """Send wind + battery + temperature delta to Signal K via UDP:4123."""
    publish_delta(
        source_label='calypso-direct',
        values=[
            {'path': 'environment.wind.speedApparent', 'value': data['wind_ms']},
            {'path': 'environment.wind.angleApparent', 'value': data['angle_rad']},
            {'path': 'electrical.batteries.calypso.percent', 'value': data['batt_pct']},
            {'path': 'environment.outside.temperature', 'value': data['temp_k']},
        ],
        logger=logger,
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — BLE NOTIFICATION CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def make_notify_handler(logger):
    """Factory: returns a BLE notification callback bound to logger."""
    def on_notify(sender, data: bytearray) -> None:
        if not _stats['first_logged']:
            logger.info(f'[DATA_FIRST] First packet: {list(data[:10])} ({len(data)} bytes)')
            _stats['first_logged'] = True

        reading = decode_packet(bytes(data))
        if reading:
            publish(reading, logger)
            _stats['packets'] += 1
            _stats['last_data_ts'] = time.time()
            logger.debug(
                f'[DATA_IN] AWS={reading["_knots"]:.1f}kt '
                f'AWA={reading["_dir_deg"]}° '
                f'Batt={reading["batt_pct"]}% '
                f'Temp={reading["temp_k"]-273.15:.0f}°C'
            )

        # Periodic heartbeat
        if time.time() - _stats['last_heartbeat'] > HEARTBEAT_S:
            age = (time.time() - _stats['last_data_ts']
                   if _stats['last_data_ts'] else 999)
            logger.info(
                f'[HEARTBEAT] packets={_stats["packets"]} '
                f'last_data={age:.0f}s ago '
                f'l1_fails={_stats["l1_fails"]}'
            )
            _stats['packets'] = 0
            _stats['last_heartbeat'] = time.time()

    return on_notify

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — DEVICE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

async def configure_device(client: BleakClient, logger) -> None:
    """Configure Calypso after connection: normal mode, set rate, disable compass."""
    for uuid, val, label in [
        # UUID_MODE write removed — Calypso firmware always in NORMAL mode, write always fails
        (UUID_RATE, bytes([RATE_MAP.get(RATE_HZ, 0x04)]), f'{RATE_HZ} Hz'),
        (UUID_COMPASS, bytes([0x00]), 'compass OFF (prevents sentinel -90/-90/360)'),
    ]:
        try:
            await client.write_gatt_char(uuid, val, response=True)
            logger.info(f'[CONFIG_WRITE] {label} ✅')
        except Exception as e:
            logger.warning(f'[CONFIG_WRITE] {label} failed: {e}')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MAIN BLE LOOP
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    global _running, _was_connected, _last_err

    logger = setup_logger(SERVICE_NAME)
    acquire_singleton(PID_FILE, logger)

    try:
        logger.info('[STARTUP] ' + '=' * 58)
        logger.info('[STARTUP] calypso_direct — Calypso UP10 BLE Driver')
        logger.info(f'[STARTUP] MAC={CALYPSO_MAC} Rate={RATE_HZ}Hz SK=UDP:4123')
        logger.info(f'[STARTUP] Timeout={DATA_TIMEOUT_S}s L2_threshold={L2_THRESHOLD}')
        logger.info('[STARTUP] ' + '=' * 58)

        if not check_ble_adapter():
            logger.error('[STARTUP] BLE adapter (hci0) not available — exiting')
            sys.exit(1)

        # Initial BlueZ cache clear — startup ONLY (not per-connection!)
    # CRITICAL: calling remove in the retry loop destroys the BLE bond each time
    # → progressive instability: connection gets shorter (18min→12min→6min→1.6min)
    # sleep 2 required: bluetoothctl remove is async, bluetoothd needs ~2s to finish
        try:
            import subprocess as _sp_init
            import time as _t_init
            _sp_init.run(f'bluetoothctl remove {CALYPSO_MAC}',
                         shell=True, capture_output=True, timeout=5)
            logger.info(f'[STARTUP] BlueZ GATT cache cleared for {CALYPSO_MAC}')
            _t_init.sleep(2)  # Wait for bluetoothd async cleanup
        except Exception:
            pass

        delay = RECONNECT_BASE_S
        l1_fails = 0
        on_notify = make_notify_handler(logger)

        while _running:
            try:
                # NOTE: bluetoothctl remove intentionally NOT called per-connection.
                # Calling before every retry destroys the BLE bond, causing progressive
                # instability (18min→12min→6min→1.6min). Bond cleanup happens ONCE
                # at startup (above), and is maintained across retries via BT_RECOVERY.

                logger.info(f'[BLE_SCAN] Connecting to Calypso {CALYPSO_MAC}...')
                async with BleakClient(CALYPSO_MAC, timeout=20.0) as client:
                    logger.info('[BLE_CONNECT] Connected ✅')
                    delay = RECONNECT_BASE_S
                    l1_fails = 0
                    _was_connected = True
                    _stats['first_logged'] = False

                    await configure_device(client, logger)
                    await client.start_notify(UUID_DATA, on_notify)
                    _stats['last_data_ts'] = time.time()  # RESET watchdog — prevents false-positive from stale timestamp
                    logger.info('[DATA_IN] Receiving Calypso wind data...')

                    while client.is_connected and _running:
                        await asyncio.sleep(1.0)
                        # Data staleness watchdog
                        if _stats['last_data_ts'] > 0:
                            age = time.time() - _stats['last_data_ts']
                            if age > DATA_TIMEOUT_S:
                                logger.warning(
                                    f'[WATCHDOG] No data for {age:.0f}s — reconnecting')
                                break

                    logger.warning('[BLE_DISCONNECT] Disconnected or data timeout')

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

            # BT_RECOVERY: zombie session OR le-connection-abort (both resolvable)
            # Targets CALYPSO_MAC only — WIT BLE unaffected
            # 'not found' = device not advertising (classic zombie)
            # 'le-connection-abort-by-local' = BlueZ aborts LE handshake (device not ready)
            # Both trigger: bluetoothctl disconnect + remove (see ble_common.bt_recovery)
            if (_was_connected
                and l1_fails >= 3
                and ('not found' in _last_err.lower()
                     or 'le-connection-abort' in _last_err.lower())):
                recovered = await bt_recovery(CALYPSO_MAC, logger)
                if recovered:
                    l1_fails = 0
                    delay = RECONNECT_BASE_S
                    _was_connected = False
                    _last_err = ''

            # L2: clean exit → systemd restart
            # hci0 NOT reset: would disrupt WIT BLE connection
            if l1_fails >= L2_THRESHOLD:
                logger.warning(
                    f'[L2] {l1_fails} failures — clean exit for systemd restart')
                logger.warning('[L2] hci0 NOT reset: would disrupt WIT BLE')
                break

            if _running:
                logger.info(f'[BLE_SCAN] Reconnecting in {delay}s...')
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_S)

    finally:
        release_singleton(PID_FILE, logger)
        logger.info('[SHUTDOWN] calypso_direct stopped — PID released')

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

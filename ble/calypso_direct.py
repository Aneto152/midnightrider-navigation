#!/usr/bin/env python3
"""
calypso_direct.py — Calypso UP10 Anemometer Direct BLE Driver
=============================================================

ROLE:
 Unified self-contained BLE daemon for the Calypso UP10.
 Replaces: calypso-anemometer pip package + calypso_watchdog.py.
 ONE script, ONE service, NO subprocess, NO external watchdog.

SOURCE:
 Protocol from: github.com/maritime-labs/calypso-anemometer (MIT, 2022)
 Not using the library: no reconnection, unmaintained since 2023.

BLE PROTOCOL (Calypso UP10):
 Notify UUID : 00002a39-0000-1000-8000-00805f9b34fb
 Mode UUID : 0000a001-0000-1000-8000-00805f9b34fb
 Rate UUID : 0000a002-0000-1000-8000-00805f9b34fb
 Compass UUID : 0000a003-0000-1000-8000-00805f9b34fb

 Packet: 10 bytes, little-endian <HHBBBBH
 [0-1] wind_speed uint16 ÷ 100 → m/s
 [2-3] wind_dir uint16 → degrees 0-359
 [4] battery uint8 × 10 → %
 [5] temperature uint8 − 100 → °C
 [6] roll uint8 − 90 → degrees (compass, ignored)
 [7] pitch uint8 − 90 → degrees (compass, ignored)
 [8-9] heading uint16 360−value → degrees (compass, ignored)

 Compass disabled at startup → no sentinel values (-90/-90/360).
 wind_direction=0 forced when wind_speed=0 (Calypso firmware quirk).

SIGNAL K (UDP:4123 — same as wit-ble-direct.py):
 environment.wind.speedApparent m/s
 environment.wind.angleApparent rad (-π to +π)
 electrical.batteries.calypso.percent %
 environment.outside.temperature K

RECOVERY (internal, no external watchdog):
 L1: BLE reconnect (backoff 5s → 60s)
 L2: hci0 reset (coordinates via /tmp/ble-adapter.lock with WIT driver)
 L3: exit → systemd Restart=on-failure

ENVIRONMENT (.env):
 CALYPSO_BLE_ADDRESS MAC address (default: F8:5F:12:9D:D2:EE)
 CALYPSO_RATE_HZ Data rate 1|4|8 (default: 4)
 CALYPSO_DATA_TIMEOUT_S Staleness threshold (default: 60)
 CALYPSO_HEARTBEAT_S Heartbeat interval (default: 300)
 CALYPSO_RECONNECT_MAX_S Max backoff (default: 60)
 CALYPSO_L2_THRESHOLD L1 fails before L2 (default: 5)
 CALYPSO_LOG_LEVEL DEBUG|INFO|WARNING (default: INFO)
 SK_UDP_HOST Signal K UDP host (default: 127.0.0.1)
 SK_UDP_PORT Signal K UDP port (default: 4123)

systemd: etc/systemd/system/calypso_direct.service
PID: /tmp/calypso_direct.pid
"""

import asyncio
import json
import logging
import math
import os
import signal
import struct
import subprocess
import sys
import time
import socket
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
RATE_HZ = int(os.environ.get('CALYPSO_RATE_HZ', '4'))
DATA_TIMEOUT_S = int(os.environ.get('CALYPSO_DATA_TIMEOUT_S', '60'))
HEARTBEAT_S = int(os.environ.get('CALYPSO_HEARTBEAT_S', '300'))
RECONNECT_MAX_S = int(os.environ.get('CALYPSO_RECONNECT_MAX_S', '60'))
L2_THRESHOLD = int(os.environ.get('CALYPSO_L2_THRESHOLD', '20'))
LOG_LEVEL_STR = os.environ.get('CALYPSO_LOG_LEVEL', 'INFO').upper()
SK_UDP_HOST = os.environ.get('SK_UDP_HOST', '127.0.0.1')
SK_UDP_PORT = int(os.environ.get('SK_UDP_PORT', '4123'))

RECONNECT_BASE_S = 5
PID_FILE = '/tmp/calypso_direct.pid'

# Calypso UP10 BLE UUIDs
UUID_DATA = '00002a39-0000-1000-8000-00805f9b34fb'
UUID_MODE = '0000a001-0000-1000-8000-00805f9b34fb'
UUID_RATE = '0000a002-0000-1000-8000-00805f9b34fb'
UUID_COMPASS = '0000a003-0000-1000-8000-00805f9b34fb'

# Rate byte values
RATE_MAP = {1: 0x01, 4: 0x04, 8: 0x08}

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — LOGGING
# ══════════════════════════════════════════════════════════════════════════════

try:
    REPO = subprocess.check_output(
        ['git', '-C', os.path.dirname(os.path.abspath(__file__)),
         'rev-parse', '--show-toplevel'],
        stderr=subprocess.DEVNULL
    ).decode().strip()
except Exception:
    REPO = os.path.expanduser('~/midnightrider-navigation')

LOG_DIR = os.path.join(REPO, 'logs', 'services')
os.makedirs(LOG_DIR, exist_ok=True)

_logger = logging.getLogger('calypso-direct')
_logger.setLevel(getattr(logging, LOG_LEVEL_STR, logging.INFO))
_fh = RotatingFileHandler(
    os.path.join(LOG_DIR, 'calypso-direct.log'),
    maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
)
_fh.setFormatter(logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [calypso-direct] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
))
_logger.addHandler(_fh)
_logger.addHandler(logging.StreamHandler(sys.stdout))

def log(level: str, probe: str, msg: str) -> None:
    getattr(_logger, level.lower(), _logger.info)(f'[{probe}] {msg}')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — SINGLETON
# One BLE connection per peripheral. Second instance = immediate conflict.
# ══════════════════════════════════════════════════════════════════════════════

def acquire_singleton() -> None:
    pid_path = Path(PID_FILE)
    if pid_path.exists():
        try:
            existing = int(pid_path.read_text().strip())
            os.kill(existing, 0)
            log('error', 'STARTUP', f'Another instance running (PID {existing}) — exiting')
            log('error', 'STARTUP', f'Force: rm {PID_FILE} && systemctl restart calypso_direct')
            sys.exit(1)
        except ProcessLookupError:
            log('warning', 'STARTUP', 'Stale PID file — removing')
            pid_path.unlink(missing_ok=True)
        except ValueError:
            pid_path.unlink(missing_ok=True)
    pid_path.write_text(str(os.getpid()))
    log('info', 'STARTUP', f'Singleton acquired (PID {os.getpid()})')

def release_singleton() -> None:
    Path(PID_FILE).unlink(missing_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CALYPSO BLE PACKET DECODER
# Ref: github.com/maritime-labs/calypso-anemometer/blob/main/calypso_anemometer/model.py
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
        log('debug', 'DECODE', f'Short packet: {len(data)} bytes (expected 10)')
        return None
    try:
        fields = struct.unpack_from('<HHBBBBH', data)
        raw_speed, raw_dir, raw_batt, raw_temp = fields[0], fields[1], fields[2], fields[3]

        wind_ms = raw_speed / 100.0
        wind_deg = raw_dir if wind_ms > 0.0 else 0 # Calypso quirk
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
            '_knots': wind_ms * 1.94384,
            '_dir_deg': wind_deg,
        }
    except struct.error as e:
        log('error', 'DECODE', f'Unpack error: {e} | hex: {data.hex()}')
        return None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SIGNAL K PUBLISHER (UDP:4123 — same as wit-ble-direct.py)
# ══════════════════════════════════════════════════════════════════════════════

_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def publish(data: dict) -> None:
    """Send wind + battery + temperature delta to Signal K via UDP:4123."""
    delta = {
        'updates': [{
            'source': {'label': 'calypso-direct', 'type': 'BLE'},
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'values': [
                {'path': 'environment.wind.speedApparent', 'value': data['wind_ms']},
                {'path': 'environment.wind.angleApparent', 'value': data['angle_rad']},
                {'path': 'electrical.batteries.calypso.percent', 'value': data['batt_pct']},
                {'path': 'environment.outside.temperature', 'value': data['temp_k']},
            ],
        }]
    }
    try:
        _udp.sendto(json.dumps(delta).encode(), (SK_UDP_HOST, SK_UDP_PORT))
    except Exception as e:
        log('debug', 'DATA_OUT', f'UDP error: {e}')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — BLE RECOVERY (L1/L2/L3)
# Coordinates hci0 resets with wit-ble-direct.py via /tmp/ble-adapter.lock
# ══════════════════════════════════════════════════════════════════════════════

def _run(cmd: str, timeout: int = 15) -> tuple:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — BLE CONNECTION + MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

_running = True
_was_connected = False
_last_err = ''  # Last BLE error for BT_RECOVERY
_stats = {
    'packets': 0,
    'last_data_ts': 0.0,
    'last_heartbeat': time.time(),
    'first_logged': False,
    'l1_fails': 0,
}

def _stop(sig, frame):
    global _running
    log('info', 'SHUTDOWN', f'Signal {sig} — stopping')
    _running = False

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

def on_notify(sender, data: bytearray) -> None:
    """BLE notification callback — synchronous."""
    if not _stats['first_logged']:
        log('info', 'DATA_FIRST', f'First packet: {list(data[:10])} ({len(data)} bytes)')
        _stats['first_logged'] = True

    reading = decode_packet(bytes(data))
    if reading:
        publish(reading)
        _stats['packets'] += 1
        _stats['last_data_ts'] = time.time()
        log('debug', 'DATA_IN',
            f'AWS={reading["_knots"]:.1f}kt AWA={reading["_dir_deg"]}° '
            f'Batt={reading["batt_pct"]}% Temp={reading["temp_k"]-273.15:.0f}°C')

        # Heartbeat
        if time.time() - _stats['last_heartbeat'] > HEARTBEAT_S:
            age = time.time() - _stats['last_data_ts'] if _stats['last_data_ts'] else 999
            log('info', 'HEARTBEAT',
                f'packets={_stats["packets"]} last_data={age:.0f}s ago')
            _stats['packets'] = 0
            _stats['last_heartbeat'] = time.time()

async def configure_device(client: BleakClient) -> None:
    """Configure Calypso after connection: normal mode, set rate, disable compass."""
    for uuid, val, label in [
        (UUID_MODE, bytes([0x02]), 'NORMAL mode'),
        (UUID_RATE, bytes([RATE_MAP.get(RATE_HZ, 0x04)]), f'{RATE_HZ} Hz'),
        (UUID_COMPASS, bytes([0x00]), 'compass OFF (prevents sentinel -90/-90/360)'),
    ]:
        try:
            await client.write_gatt_char(uuid, val, response=True)
            log('info', 'CONFIG_WRITE', f'{label} ✅')
        except Exception as e:
            log('warning', 'CONFIG_WRITE', f'{label} failed: {e}')

async def main() -> None:
    global _running, _was_connected, _last_err
    acquire_singleton()
    try:
        log('info', 'STARTUP', '=' * 60)
        log('info', 'STARTUP', f'calypso_direct — Calypso UP10 BLE Driver')
        log('info', 'STARTUP', f'MAC={CALYPSO_MAC} Rate={RATE_HZ}Hz SK=UDP:{SK_UDP_PORT}')
        log('info', 'STARTUP', f'Timeout={DATA_TIMEOUT_S}s L2_threshold={L2_THRESHOLD}')
        log('info', 'STARTUP', '=' * 60)

        ok, out = _run('hciconfig hci0')
        log('info', 'DEPENDENCY_CHECK',
            f'hci0: {"RUNNING ✅" if "RUNNING" in out else "⚠️ "+out[:40]}')

        delay = RECONNECT_BASE_S
        l1_fails = 0

        while _running:
            try:
                log('info', 'BLE_SCAN', f'Connecting to Calypso {CALYPSO_MAC}...')
                async with BleakClient(CALYPSO_MAC, timeout=20.0) as client:
                    log('info', 'BLE_CONNECT', 'Connected ✅')
                    delay = RECONNECT_BASE_S
                    l1_fails = 0
                    _was_connected = True
                    _stats['first_logged'] = False

                    await configure_device(client)
                    await client.start_notify(UUID_DATA, on_notify)
                    log('info', 'DATA_IN', 'Receiving Calypso wind data...')

                    while client.is_connected and _running:
                        await asyncio.sleep(1.0)
                        # Data staleness watchdog
                        if _stats['last_data_ts'] > 0:
                            age = time.time() - _stats['last_data_ts']
                            if age > DATA_TIMEOUT_S:
                                log('warning', 'WATCHDOG',
                                    f'No data for {age:.0f}s — reconnecting')
                                break

                    log('warning', 'BLE_DISCONNECT', 'Disconnected or data timeout')

            except BleakError as e:
                l1_fails += 1
                _stats['l1_fails'] += 1
                _last_err = str(e)
                log('error', 'ERROR', f'BLE error (L1 #{l1_fails}): {e}')
            except Exception as e:
                l1_fails += 1
                _stats['l1_fails'] += 1
                _last_err = str(e)
                log('error', 'ERROR', f'Error (L1 #{l1_fails}): {type(e).__name__}: {e}')

            # BT_RECOVERY: Calypso was connected but now invisible = zombie BLE
            # Targets CALYPSO_MAC only — WIT unaffected (validated 2026-05-29)
            if _was_connected and 'not found' in _last_err.lower() and l1_fails >= 3:
                log('warning', 'BT_RECOVERY',
                    f'Zombie BLE after {l1_fails} failures — clearing {CALYPSO_MAC}')
                try:
                    import subprocess as _sp
                    r1 = _sp.run(
                        f'bluetoothctl disconnect {CALYPSO_MAC}',
                        shell=True, capture_output=True, text=True, timeout=10)
                    log('info', 'BT_RECOVERY',
                        f'disconnect: {(r1.stdout+r1.stderr).strip()[:60]}')
                    await asyncio.sleep(2)
                    r2 = _sp.run(
                        f'bluetoothctl remove {CALYPSO_MAC}',
                        shell=True, capture_output=True, text=True, timeout=10)
                    log('info', 'BT_RECOVERY',
                        f'remove: {(r2.stdout+r2.stderr).strip()[:60]}')
                    await asyncio.sleep(3)
                    l1_fails = 0
                    delay = RECONNECT_BASE_S
                    _was_connected = False
                    _last_err = ''
                    log('info', 'BT_RECOVERY', 'Calypso BLE cleared — retrying')
                except Exception as bt_err:
                    log('error', 'BT_RECOVERY', f'Recovery failed: {bt_err}')

            if l1_fails >= L2_THRESHOLD:
                log('warning', 'L2',
                    f'{l1_fails} failures — clean exit for systemd restart')
                log('warning', 'L2',
                    'hci0 NOT reset: would disrupt WIT BLE connection')
                break  # Let systemd Restart=on-failure handle it

            if _running:
                log('info', 'BLE_SCAN', f'Reconnecting in {delay}s...')
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_S)

    finally:
        release_singleton()
        log('info', 'SHUTDOWN', 'calypso_direct stopped — PID released')

if __name__ == '__main__':
    asyncio.run(main())

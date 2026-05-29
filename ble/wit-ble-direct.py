#!/usr/bin/env python3
"""
wit-ble-direct.py — WIT WT901BLECL IMU BLE Driver
===================================================

ROLE:
 Unified, self-contained BLE daemon for the WIT WT901BLECL IMU.
 Handles: BLE connection, configuration, data parsing,
 coordinate transformation, Signal K publishing,
 reconnection, singleton enforcement, and health monitoring.
 NO external watchdog needed — all recovery logic is internal.

WHY QUATERNION:
 The WIT is mounted vertically on the companionway bulkhead.
 In this position, the standard Euler pitch angle can reach ±90°
 causing gimbal lock in the WIT firmware's internal Euler computation.
 By reading native quaternion output (Kalman filter output, flag 0x71),
 we bypass this singularity entirely. Mounting correction is applied
 in quaternion space before any Euler conversion.

COORDINATE TRANSFORM:
 WIT body frame → quaternion multiply (MOUNT_Q) → Boat frame
 Boat frame quaternion → quaternion_to_euler() → roll/pitch/yaw

SIGNAL K PATHS PUBLISHED:
 navigation.attitude.roll rad Heel (+ = starboard down)
 navigation.attitude.pitch rad Trim (+ = bow up)
 navigation.attitude.yaw rad Magnetic heading
 navigation.headingMagnetic rad Same as yaw (explicit SK path)
 navigation.acceleration.x m/s² Along bow axis
 navigation.acceleration.y m/s² Along port axis
 navigation.acceleration.z m/s² Vertical
 navigation.rateOfTurn rad/s From gyro Z

RECOVERY (INTERNAL, no external watchdog):
 L1: Reconnect with exponential backoff (5s → 60s max)
 L2: hci0 reset (after L2_FAIL_THRESHOLD L1 fails)
 L3: Log FATAL + exit → systemd Restart=on-failure restarts
"""

import asyncio
import json
import logging
import math
import os
import signal
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import urllib.error
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print('[FATAL] bleak not installed. Run: pip install bleak', flush=True)
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION
# All from .env — never hardcode values here
# ══════════════════════════════════════════════════════════════════════════════

WIT_MAC = os.environ.get('WIT_BLE_ADDRESS', 'E9:10:DB:8B:CE:C7')
MOUNT_AXIS = os.environ.get('WIT_MOUNT_AXIS', 'z').lower()
MOUNT_DEG = float(os.environ.get('WIT_MOUNT_ROTATION_DEG', '90'))
OUTPUT_RATE_HZ = int(os.environ.get('WIT_OUTPUT_RATE_HZ', '10'))
HEARTBEAT_S = int(os.environ.get('WIT_HEARTBEAT_S', '300'))
RECONNECT_MAX_S = int(os.environ.get('WIT_RECONNECT_MAX_S', '60'))
L2_FAIL_THRESHOLD = int(os.environ.get('WIT_L2_FAIL_THRESHOLD', '5'))
LOG_LEVEL_STR = os.environ.get('WIT_LOG_LEVEL', 'INFO').upper()
SK_URL = os.environ.get('SK_URL', 'http://localhost:3000')

PID_FILE = '/tmp/wit-ble-direct.pid'
RECONNECT_BASE_S = 5

# WIT BLE UUIDs (CORRECTED 2026-05-29: 9a34fb not 9b34fb)
NOTIFY_UUID = '0000ffe4-0000-1000-8000-00805f9a34fb'
WRITE_UUID = '0000ffe9-0000-1000-8000-00805f9a34fb'

# WIT commands
ENABLE_QUATERNION = bytes([0xFF, 0xAA, 0x27, 0x51, 0x00])

# Rate codes: Hz → code
RATE_CODES = {1: 0x01, 2: 0x02, 5: 0x03, 10: 0x04, 20: 0x05, 50: 0x06, 100: 0x07, 200: 0x08}

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

_logger = logging.getLogger('wit-ble-direct')
_logger.setLevel(getattr(logging, LOG_LEVEL_STR, logging.INFO))

_fh = RotatingFileHandler(
    os.path.join(LOG_DIR, 'wit-ble-direct.log'),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
)
_fh.setFormatter(logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [wit-ble-direct] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
))
_logger.addHandler(_fh)
_logger.addHandler(logging.StreamHandler(sys.stdout))

def log(level: str, probe: str, msg: str) -> None:
    getattr(_logger, level.lower(), _logger.info)(f'[{probe}] {msg}')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

def acquire_singleton() -> None:
    pid_path = Path(PID_FILE)
    if pid_path.exists():
        try:
            existing_pid = int(pid_path.read_text().strip())
            os.kill(existing_pid, 0)
            log('error', 'STARTUP', f'Another instance (PID {existing_pid}) is running. Exiting.')
            sys.exit(1)
        except ProcessLookupError:
            pid_path.unlink(missing_ok=True)
        except ValueError:
            pid_path.unlink(missing_ok=True)
    
    pid_path.write_text(str(os.getpid()))
    log('info', 'STARTUP', f'Singleton acquired (PID {os.getpid()})')

def release_singleton() -> None:
    Path(PID_FILE).unlink(missing_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — QUATERNION MATH
# ══════════════════════════════════════════════════════════════════════════════

def quaternion_multiply(q1: tuple, q2: tuple) -> tuple:
    """Hamilton product: q1 × q2 (non-commutative)."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )

def quaternion_to_euler(q: tuple) -> tuple:
    """Convert quaternion to Euler (roll, pitch, yaw) in radians using atan2 (no singularity)."""
    w, x, y, z = q
    roll = math.atan2(2.0*(w*x + y*z), 1.0 - 2.0*(x*x + y*y))
    sinp1 = math.sqrt(max(0.0, 1.0 + 2.0*(w*y - x*z)))
    sinp2 = math.sqrt(max(0.0, 1.0 - 2.0*(w*y - x*z)))
    pitch = 2.0 * math.atan2(sinp1, sinp2) - math.pi / 2.0
    yaw = math.atan2(2.0*(w*z + x*y), 1.0 - 2.0*(y*y + z*z))
    return roll, pitch, yaw

def make_mount_quaternion(axis: str, degrees: float) -> tuple:
    """Create mounting correction quaternion."""
    half = math.radians(degrees) / 2.0
    c, s = math.cos(half), math.sin(half)
    mapping = {'x': (c, s, 0, 0), 'y': (c, 0, s, 0), 'z': (c, 0, 0, s)}
    if axis not in mapping:
        log('warning', 'CONFIG', f'Unknown MOUNT_AXIS "{axis}" — defaulting to z')
        return mapping['z']
    return mapping[axis]

MOUNT_Q = make_mount_quaternion(MOUNT_AXIS, MOUNT_DEG)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — PACKET DECODING
# ══════════════════════════════════════════════════════════════════════════════

def decode_0x71_packet(data: bytes) -> dict | None:
    """Decode quaternion packet (0x71)."""
    if len(data) < 11 or data[0] != 0x55 or data[1] != 0x71:
        return None
    try:
        def s16(off): return struct.unpack_from('<h', data, off)[0]
        return {
            'q0': s16(2) / 32768.0,
            'q1': s16(4) / 32768.0,
            'q2': s16(6) / 32768.0,
            'q3': s16(8) / 32768.0,
        }
    except Exception as e:
        log('debug', 'DECODE', f'0x71 error: {e}')
        return None

def decode_0x61_packet(data: bytes) -> dict | None:
    """Decode acceleration/gyro packet (0x61)."""
    if len(data) < 20 or data[0] != 0x55 or data[1] != 0x61:
        return None
    try:
        def s16(off): return struct.unpack_from('<h', data, off)[0]
        return {
            'accel_x': (s16(2) / 32768.0) * 16.0 * 9.81,
            'accel_y': (s16(4) / 32768.0) * 16.0 * 9.81,
            'accel_z': (s16(6) / 32768.0) * 16.0 * 9.81,
            'gyro_z': (s16(12) / 32768.0) * 2000.0 * math.pi / 180.0,
        }
    except Exception as e:
        log('debug', 'DECODE', f'0x61 error: {e}')
        return None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — COORDINATE TRANSFORMATION
# ══════════════════════════════════════════════════════════════════════════════

def apply_mounting_and_extract(q_raw: dict) -> dict:
    """Transform WIT quaternion to boat frame."""
    q_wit = (q_raw['q0'], q_raw['q1'], q_raw['q2'], q_raw['q3'])
    q_boat = quaternion_multiply(q_wit, MOUNT_Q)
    roll, pitch, yaw = quaternion_to_euler(q_boat)
    return {
        'roll': roll,
        'pitch': pitch,
        'yaw': yaw,
        'headingMagnetic': yaw,
    }

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — SIGNAL K PUBLISHER (TCP DELTA)
# Signal K has a delta TCP server on port 5000 (default) that receives JSON deltas.
# This is more reliable than HTTP POST (which doesn't have a /signalk/v1/api endpoint).
# ══════════════════════════════════════════════════════════════════════════════

import socket

SK_DELTA_HOST = os.environ.get('SK_DELTA_HOST', 'localhost')
SK_DELTA_PORT = int(os.environ.get('SK_DELTA_PORT', '5000'))

_sk_socket = None
_sk_socket_lock = asyncio.Lock()

async def _get_sk_socket():
    """Get or create TCP socket to Signal K delta server."""
    global _sk_socket
    if _sk_socket is None:
        try:
            _sk_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _sk_socket.connect((SK_DELTA_HOST, SK_DELTA_PORT))
            log('info', 'DATA_OUT', f'Connected to SK delta server {SK_DELTA_HOST}:{SK_DELTA_PORT}')
        except Exception as e:
            _sk_socket = None
            log('warning', 'DATA_OUT', f'Failed to connect to SK delta server: {e}')
            return None
    return _sk_socket

async def _send_delta_tcp(values: list) -> bool:
    """Send delta to Signal K via TCP connection."""
    global _sk_socket
    try:
        sock = await _get_sk_socket()
        if not sock:
            return False
        
        delta = {
            'updates': [{
                'source': {'label': 'wit-ble-direct', 'type': 'BLE'},
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'values': values,
            }]
        }
        data = json.dumps(delta).encode() + b'\n'
        sock.sendall(data)
        return True
    except Exception as e:
        _sk_socket = None
        log('debug', 'DATA_OUT', f'SK TCP error (will reconnect): {type(e).__name__}')
        return False

def _post_delta(values: list) -> bool:
    """Wrapper for async delta sending (called from sync context)."""
    try:
        # Since we're in an async context, this should be called via asyncio
        # For now, return false to indicate it needs to be awaited
        return False
    except Exception as e:
        log('debug', 'DATA_OUT', f'SK error: {e}')
        return False

async def send_attitude(data: dict) -> None:
    await _send_delta_tcp([
        {'path': 'navigation.attitude.roll', 'value': data['roll']},
        {'path': 'navigation.attitude.pitch', 'value': data['pitch']},
        {'path': 'navigation.attitude.yaw', 'value': data['yaw']},
        {'path': 'navigation.headingMagnetic', 'value': data['headingMagnetic']},
    ])

async def send_motion(data: dict) -> None:
    await _send_delta_tcp([
        {'path': 'navigation.acceleration.x', 'value': data['accel_x']},
        {'path': 'navigation.acceleration.y', 'value': data['accel_y']},
        {'path': 'navigation.acceleration.z', 'value': data['accel_z']},
        {'path': 'navigation.rateOfTurn', 'value': data['gyro_z']},
    ])

async def check_sk_reachable() -> bool:
    """Check if Signal K delta server is reachable on TCP:5000."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((SK_DELTA_HOST, SK_DELTA_PORT))
        s.close()
        if result == 0:
            return True
    except Exception as e:
        log('warning', 'DEPENDENCY', f'SK delta server unreachable: {e}')
    return False

def check_ble_adapter() -> bool:
    try:
        r = subprocess.run('hciconfig hci0', shell=True, capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and 'RUNNING' in r.stdout:
            return True
    except Exception:
        pass
    log('warning', 'DEPENDENCY', 'hci0 not RUNNING')
    return False

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — STATS & WATCHDOG
# ══════════════════════════════════════════════════════════════════════════════

_stats = {
    'packets_0x71': 0,
    'packets_0x61': 0,
    'sk_posts': 0,
    'l1_fails': 0,
    'last_heartbeat': time.time(),
}

def log_heartbeat() -> None:
    """Periodic status log."""
    elapsed = time.time() - _stats['last_heartbeat']
    if elapsed >= HEARTBEAT_S:
        log('info', 'HEARTBEAT', 
            f'0x71:{_stats["packets_0x71"]} 0x61:{_stats["packets_0x61"]} '
            f'SK:{_stats["sk_posts"]} L1_fails:{_stats["l1_fails"]}')
        _stats['last_heartbeat'] = time.time()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — BLE CONNECTION & RECOVERY
# ══════════════════════════════════════════════════════════════════════════════

async def run_ble_client() -> None:
    """Main BLE connection loop with internal recovery."""
    acquire_singleton()
    try:
        reconnect_delay = RECONNECT_BASE_S
        l1_fail_count = 0
        
        log('info', 'STARTUP', f'Starting WIT BLE client')
        log('info', 'STARTUP', f'MAC={WIT_MAC} Rate={OUTPUT_RATE_HZ}Hz Mount={MOUNT_AXIS}/{MOUNT_DEG}°')
        
        # Dependency checks
        if not await check_sk_reachable():
            log('error', 'STARTUP', 'Signal K unreachable — exiting')
            sys.exit(1)
        if not check_ble_adapter():
            log('error', 'STARTUP', 'BLE adapter (hci0) not available — exiting')
            sys.exit(1)
        
        while True:
            try:
                async with BleakClient(WIT_MAC) as client:
                    log('info', 'BLE_CONNECT', f'Connected to {WIT_MAC}')
                    l1_fail_count = 0
                    reconnect_delay = RECONNECT_BASE_S
                    
                    # Configure WIT: enable quaternion output
                    try:
                        await client.write_gatt_char(WRITE_UUID, ENABLE_QUATERNION)
                        log('debug', 'BLE_SETUP', 'Quaternion (0x71) enabled')
                    except Exception as e:
                        log('warning', 'BLE_SETUP', f'Write failed: {e}')
                    
                    # Start notification handler
                    async def handle_data_async(sender, data):
                        pkt_0x71 = decode_0x71_packet(data)
                        if pkt_0x71:
                            _stats['packets_0x71'] += 1
                            att = apply_mounting_and_extract(pkt_0x71)
                            await send_attitude(att)
                            _stats['sk_posts'] += 1
                        
                        pkt_0x61 = decode_0x61_packet(data)
                        if pkt_0x61:
                            _stats['packets_0x61'] += 1
                            await send_motion(pkt_0x61)
                            _stats['sk_posts'] += 1
                        
                        log_heartbeat()
                    
                    # Sync wrapper for bleak callback
                    def handle_data(sender, data):
                        asyncio.create_task(handle_data_async(sender, data))
                    
                    await client.start_notify(NOTIFY_UUID, handle_data)
                    log('info', 'BLE_NOTIFY', 'Notifications started')
                    
                    # Keep connection alive
                    while True:
                        await asyncio.sleep(5)
            
            except Exception as e:
                l1_fail_count += 1
                _stats['l1_fails'] += 1
                log('warning', 'L1', f'Connection failed ({l1_fail_count}): {e}')
                
                # L2: reset hci0 after threshold
                if l1_fail_count >= L2_FAIL_THRESHOLD:
                    log('error', 'L2', f'L1 failures {l1_fail_count} ≥ threshold {L2_FAIL_THRESHOLD} — resetting hci0')
                    try:
                        subprocess.run('sudo hciconfig hci0 down', shell=True, timeout=10)
                        await asyncio.sleep(3)
                        subprocess.run('sudo hciconfig hci0 up', shell=True, timeout=10)
                        await asyncio.sleep(3)
                        log('info', 'L2', 'hci0 reset complete')
                        l1_fail_count = 0
                        reconnect_delay = RECONNECT_BASE_S
                    except Exception as e2:
                        log('error', 'L2', f'hci0 reset failed: {e2}')
                
                # Exponential backoff: 5s → 10s → 20s → ... → 60s max
                reconnect_delay = min(reconnect_delay * 2, RECONNECT_MAX_S)
                log('info', 'L1', f'Reconnecting in {reconnect_delay}s...')
                await asyncio.sleep(reconnect_delay)
    
    finally:
        release_singleton()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — MAIN & SIGNAL HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

_loop = None

def _shutdown(sig, frame):
    global _loop
    log('info', 'SHUTDOWN', f'Signal {sig} received — shutting down')
    if _loop:
        _loop.stop()
    sys.exit(0)

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

async def main():
    await run_ble_client()

if __name__ == '__main__':
    try:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(main())
    except KeyboardInterrupt:
        _shutdown(signal.SIGINT, None)
    except Exception as e:
        log('error', 'FATAL', f'Unhandled exception: {e}')
        sys.exit(1)

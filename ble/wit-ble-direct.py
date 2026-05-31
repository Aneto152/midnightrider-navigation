#!/usr/bin/env python3
"""
wit-ble-direct.py — WIT WT901BLECL IMU Direct BLE Driver
==========================================================

ROLE:
 Unified, self-contained BLE daemon for the WIT WT901BLECL IMU.
 Handles: BLE connection, data parsing, coordinate transformation,
 Signal K publishing, reconnection, singleton enforcement.
 NO external watchdog needed — all recovery logic is internal.

DEVICE-SPECIFIC (this file):
 - BLE UUIDs for WIT WT901BLECL
 - Quaternion mathematics (Hamilton product, Euler conversion)
 - Mounting correction quaternion (z/90° default)
 - Packet decoders (0x71 quaternion, 0x61 accel/gyro)
 - Signal K paths (attitude, acceleration, rateOfTurn)
 - WIT initialization state machine (ENABLE_QUATERNION protocol)

SHARED INFRASTRUCTURE (ble_common.py):
 - Logger setup (RotatingFileHandler)
 - Singleton (PID file)
 - SK UDP publisher (UDP:4123)
 - BLE adapter check
 - SK reachability check
 - BT zombie recovery (bluetoothctl disconnect/remove)
 - Graceful signal handlers (no sys.exit — prevents BLE zombie)

WHY QUATERNION:
 The WIT is mounted vertically on the companionway bulkhead.
 In this position, the standard Euler pitch angle can reach ±90°
 causing gimbal lock in the WIT firmware's internal Euler computation.
 By reading native quaternion output (Kalman filter output, flag 0x71),
 we bypass this singularity entirely. Mounting correction is applied
 in quaternion space before any Euler conversion.

WIT BLE PROTOCOL (WT901BLECL):
 Notify UUID : 0000ffe4-0000-1000-8000-00805f9a34fb (corrected: 9a not 9b)
 Write UUID : 0000ffe9-0000-1000-8000-00805f9a34fb (corrected: 9a not 9b)

 0x71 packet (quaternion, 20 bytes):
 [0]=0x55 [1]=0x71 [2-3]=Q0 [4-5]=Q1 [6-7]=Q2 [8-9]=Q3 (int16/32768)

 0x61 packet (accel+gyro, 20 bytes):
 [0]=0x55 [1]=0x61 [2-3]=ax [4-5]=ay [6-7]=az [8-9]=gx [10-11]=gy [12-13]=gz

WIT INITIALIZATION PROTOCOL:
 Command FF AA 27 51 00 = one-shot quaternion request (not "enable" mode).
 WIT responds with ONE 0x71 packet per request.

 State machine prevents reset loop:
 UNINITIALIZED: send command once → WIT resets → WAIT_RECONNECT
 WAIT_RECONNECT: reconnect → subscribe (no commands) → STREAMING
 STREAMING: receive data continuously

SIGNAL K PATHS PUBLISHED:
 navigation.attitude.roll rad Heel (+ = starboard down)
 navigation.attitude.pitch rad Trim (+ = bow up)
 navigation.attitude.yaw rad Magnetic heading
 navigation.headingMagnetic rad Same as yaw (explicit SK path)
 navigation.acceleration.x m/s² Along bow axis
 navigation.acceleration.y m/s² Along port axis
 navigation.acceleration.z m/s² Vertical
 navigation.rateOfTurn rad/s From gyro Z

RECOVERY:
 L1: Reconnect with exponential backoff (5s → 60s max)
 BT_RECOVERY: bluetoothctl disconnect+remove (zombie session, own MAC only)
 L2: clean exit → systemd Restart=on-failure (NO hci0 reset)

ENVIRONMENT (.env):
 WIT_BLE_ADDRESS MAC address (default: E9:10:DB:8B:CE:C7)
 WIT_MOUNT_AXIS Mounting axis x|y|z (default: z)
 WIT_MOUNT_ROTATION_DEG Mounting rotation degrees (default: 90)
 WIT_OUTPUT_RATE_HZ Output rate Hz (default: 10)
 WIT_HEARTBEAT_S Heartbeat interval (default: 300)
 WIT_RECONNECT_MAX_S Max backoff (default: 60)
 WIT_L2_FAIL_THRESHOLD L1 fails before L2 (default: 5)
 SK_URL Signal K URL (default: http://localhost:3000)

systemd: etc/systemd/system/wit-ble-direct.service
PID: /tmp/wit-ble-direct.pid
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
    check_sk_reachable,
    bt_recovery,
    setup_signal_handlers,
)

try:
    from bleak import BleakClient
except ImportError:
    print('[FATAL] bleak not installed. Run: pip install bleak', flush=True)
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

WIT_MAC = os.environ.get('WIT_BLE_ADDRESS', 'E9:10:DB:8B:CE:C7')
MOUNT_AXIS = os.environ.get('WIT_MOUNT_AXIS', 'z').lower()
MOUNT_DEG = float(os.environ.get('WIT_MOUNT_ROTATION_DEG', '90'))
OUTPUT_RATE_HZ = int(os.environ.get('WIT_OUTPUT_RATE_HZ', '10'))
HEARTBEAT_S = int(os.environ.get('WIT_HEARTBEAT_S', '300'))
RECONNECT_MAX_S = int(os.environ.get('WIT_RECONNECT_MAX_S', '60'))
L2_FAIL_THRESHOLD = int(os.environ.get('WIT_L2_FAIL_THRESHOLD', '5'))
SK_URL = os.environ.get('SK_URL', 'http://localhost:3000')

SERVICE_NAME = 'wit-ble-direct'
PID_FILE = '/tmp/wit-ble-direct.pid'
RECONNECT_BASE_S = 5

# WIT WT901BLECL BLE UUIDs (CORRECTED 2026-05-29: 9a34fb not 9b34fb)
NOTIFY_UUID = '0000ffe4-0000-1000-8000-00805f9a34fb'
WRITE_UUID = '0000ffe9-0000-1000-8000-00805f9a34fb'

# WIT command: FF AA 27 51 00 = one-shot quaternion request
# WIT responds with ONE 0x71 packet per request.
ENABLE_QUAT_CMD = bytes([0xFF, 0xAA, 0x27, 0x51, 0x00])  # quaternion
CMD_MAG = bytes([0xFF, 0xAA, 0x27, 0x3A, 0x00])  # mag+temp at 1Hz
CMD_PRES = bytes([0xFF, 0xAA, 0x27, 0x45, 0x00])  # pressure at 0.3Hz  # mag+temp at 1Hz

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PROCESS STATE
# ══════════════════════════════════════════════════════════════════════════════

_running = True  # Set to False by SIGTERM/SIGINT — graceful BLE disconnect
_was_connected = False  # BT recovery: did WIT ever connect this session?
_last_err = ''  # BT recovery: last BLE error string

# WIT initialization state machine
# UNINITIALIZED: send ENABLE_QUAT once (WIT resets) → WAIT_RECONNECT
# WAIT_RECONNECT: reconnect → subscribe (no commands) → STREAMING
# STREAMING: receive data continuously
_wit_state = 'UNINITIALIZED'

_stats = {
    'packets_0x71': 0,
    'packets_0x61': 0,
    'sk_posts': 0,
    'l1_fails': 0,
    'last_heartbeat': time.time(),
}

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — QUATERNION MATHEMATICS
# ══════════════════════════════════════════════════════════════════════════════

def quaternion_multiply(q1: tuple, q2: tuple) -> tuple:
    """Hamilton product: q1 ⊗ q2 (non-commutative)."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )

def quaternion_to_euler(q: tuple) -> tuple:
    """
    Convert quaternion to Euler (roll, pitch, yaw) in radians.
    Uses atan2 formulation — no gimbal lock singularity.
    """
    w, x, y, z = q
    roll = math.atan2(2.0*(w*x + y*z), 1.0 - 2.0*(x*x + y*y))
    sinp1 = math.sqrt(max(0.0, 1.0 + 2.0*(w*y - x*z)))
    sinp2 = math.sqrt(max(0.0, 1.0 - 2.0*(w*y - x*z)))
    pitch = 2.0 * math.atan2(sinp1, sinp2) - math.pi / 2.0
    yaw = math.atan2(2.0*(w*z + x*y), 1.0 - 2.0*(y*y + z*z))
    return roll, pitch, yaw

def make_mount_quaternion(axis: str, degrees: float) -> tuple:
    """Create mounting correction quaternion for given axis and rotation."""
    half = math.radians(degrees) / 2.0
    c, s = math.cos(half), math.sin(half)
    mapping = {'x': (c, s, 0, 0), 'y': (c, 0, s, 0), 'z': (c, 0, 0, s)}
    return mapping.get(axis, mapping['z'])

# Pre-compute mounting correction at module load time
# Full quaternion override (w,x,y,z) — takes precedence over MOUNT_AXIS/DEG
# New physical mounting: WIT-X=port, WIT-Y=masthead(up), WIT-Z=bow
# Quaternion (0.5,-0.5,0.5,-0.5) = 120° around (-1,1,-1)/√3 axis
# Verified by Dust 2026-05-31 via rotation matrix: WIT frame → boat frame
# Transform: WIT-Z(bow)→X_boat, -WIT-X(port)→Y_boat(starboard), -WIT-Y(up)→Z_boat(down)
_WIT_MOUNT_Q_STR = os.environ.get('WIT_MOUNT_Q', '0.5,-0.5,0.5,-0.5')
try:
    _mq = [float(v.strip()) for v in _WIT_MOUNT_Q_STR.split(',')]
    if len(_mq) != 4:
        raise ValueError(f'WIT_MOUNT_Q must have 4 values, got {len(_mq)}')
    _norm = sum(v*v for v in _mq) ** 0.5
    if abs(_norm - 1.0) > 0.01:
        raise ValueError(f'WIT_MOUNT_Q norm={_norm:.4f}, must be ~1.0')
    MOUNT_Q = tuple(_mq)  # (w, x, y, z)
except Exception as _e:
    import logging as _lg
    _lg.warning(f'[CONFIG] WIT_MOUNT_Q parse error: {_e} — falling back to axis/angle')
    MOUNT_Q = make_mount_quaternion(MOUNT_AXIS, MOUNT_DEG)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — PACKET DECODERS
# ══════════════════════════════════════════════════════════════════════════════

def decode_0x71_packet(data: bytes) -> dict | None:
    """
    Decode WIT quaternion packet (0x71).

    Layout: 0x55 0x71 [Q0 int16] [Q1 int16] [Q2 int16] [Q3 int16] ...
    Each component: int16 / 32768.0
    Returns None if packet is invalid.
    """
    if len(data) < 12 or data[0] != 0x55 or data[1] != 0x71 or data[2] != 0x51:
        return None
    try:
        def s16(off): return struct.unpack_from('<h', data, off)[0]
        return {
            'q0': s16(4) / 32768.0,  # offset 4 per datasheet (skip REG_L REG_H at 2,3)
                'q1': s16(6) / 32768.0,
                'q2': s16(8) / 32768.0,
                'q3': s16(10) / 32768.0,
        }
    except Exception:
        return None




def decode_0x54_packet(data: bytes) -> dict | None:
    """Decode WIT auto-stream magnetic field packet (0x54) for temperature.
    Layout: 0x55 0x54 HxL HxH HyL HyH HzL HzH TL TH SUM
    Temperature at offset 8: s16(8) / 100.0 °C
    """
    if len(data) < 10 or data[0] != 0x55 or data[1] != 0x54:
        return None
    try:
        def s16(o): return struct.unpack_from('<h', data, o)[0]
        temp_c = s16(8) / 100.0
        if temp_c < -40 or temp_c > 85:
            return None  # sanity check
        return {'temp_c': temp_c}
    except Exception:
        return None

def decode_0x71_pres_packet(data: bytes) -> dict | None:
    """Decode CMD_PRES response (FF AA 27 45 00) — register 0x45.
    Registers 0x45-0x48: PressureL, PressureH (Pa as u32LE)
    Pressure = (PressureH<<16 | PressureL) Pa (sanity: 50000-110000 Pa)
    """
    if len(data) < 12 or data[0] != 0x55 or data[1] != 0x71 or data[2] != 0x45:
        return None
    try:
        def u16(o): return struct.unpack_from('<H', data, o)[0]
        pres_l = u16(4)
        pres_h = u16(6)
        pressure_pa = float((pres_h << 16) | pres_l)
        if pressure_pa < 50000 or pressure_pa > 110000:
            return None  # sanity check
        return {'pressure_pa': pressure_pa}
    except Exception:
        return None

def decode_0x71_mag_packet(data: bytes) -> dict | None:
    """Decode 0x71 response to CMD_MAG — magnetic field + temperature."""
    if len(data) < 10 or data[0] != 0x55 or data[1] != 0x71 or data[2] != 0x3A:
        return None
    try:
        def s16(off): return struct.unpack_from('<h', data, off)[0]
        result = {'hx_ut': s16(4)/10.0, 'hy_ut': s16(6)/10.0, 'hz_ut': s16(8)/10.0}
        if len(data) >= 18:
            result['temp_c'] = s16(16) / 100.0
        return result
    except Exception:
        return None

def decode_0x61_packet(data: bytes) -> dict | None:
    """
    Decode WIT acceleration + gyro packet (0x61).

    Layout: 0x55 0x61 [ax int16] [ay int16] [az int16] [gx int16] [gy int16] [gz int16] ...
    Accel: int16/32768 × 16g × 9.81 m/s²
    Gyro: int16/32768 × 2000°/s → rad/s
    Returns None if packet is invalid.
    """
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
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — COORDINATE TRANSFORMATION
# WIT body frame → quaternion multiply (MOUNT_Q) → Boat frame
# ══════════════════════════════════════════════════════════════════════════════

def apply_mounting_and_extract(q_raw: dict) -> dict:
    """Transform WIT quaternion to boat frame and extract Euler angles.

    WIT WT901BLECL uses Q0=w convention (scalar FIRST) — confirmed 2026-05-31:
    - Q0(offset 4) = w (scalar)
    - Q1(offset 6) = x
    - Q2(offset 8) = y
    - Q3(offset 10) = z

    Euler axis mapping (verified with 7 physical orientations):
    - Euler-X formula → heading (0=N, +π/2=E, normalized [0,2π])
    - Euler-Y formula → heel (+π/2=stbd, -π/2=port)
    - Euler-Z formula → pitch (+π/2=bow up, -π/2=bow down)

    MOUNT_Q=identity works when WIT is correctly calibrated (after heading reset).
    """
    # Q0=w (scalar FIRST) convention — confirmed 2026-05-31
    q_wit = (
        q_raw.get('q0', 0),  # Q0 = w (scalar)
        q_raw.get('q1', 0),  # Q1 = x
        q_raw.get('q2', 0),  # Q2 = y
        q_raw.get('q3', 0),  # Q3 = z
    )
    q_boat = quaternion_multiply(q_wit, MOUNT_Q)
    w, x, y, z = q_boat

    # Euler-X → heading
    euler_heading = math.atan2(2.0*(w*x + y*z), 1.0 - 2.0*(x*x + y*y))
    # Euler-Y → heel (gîte)
    sinp1 = math.sqrt(max(0.0, 1.0 + 2.0*(w*y - x*z)))
    sinp2 = math.sqrt(max(0.0, 1.0 - 2.0*(w*y - x*z)))
    euler_heel = 2.0*math.atan2(sinp1, sinp2) - math.pi/2.0
    # Euler-Z → pitch (assiette)
    euler_pitch = math.atan2(2.0*(w*z + x*y), 1.0 - 2.0*(y*y + z*z))
    # Normalize heading to [0, 2π]
    heading_rad = euler_heading % (2.0 * math.pi)

    return {
        'roll': euler_heel,        # heel (+stbd, -port)
        'pitch': euler_pitch,      # pitch (+bow up)
        'yaw': heading_rad,        # heading [0, 2π]
        'headingMagnetic': heading_rad,  # same (explicit SK path)
        # Raw quaternion (Q0=w convention)
        'qw': q_raw.get('q0', 0),  # Q0 = w (scalar)
        'qx': q_raw.get('q1', 0),  # Q1 = x
        'qy': q_raw.get('q2', 0),  # Q2 = y
        'qz': q_raw.get('q3', 0),  # Q3 = z
    }

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SIGNAL K PUBLISHERS
# Uses publish_delta() from ble_common (UDP:4123).
# ══════════════════════════════════════════════════════════════════════════════

def send_attitude(data: dict, logger) -> None:
    """Publish attitude + headingMagnetic to Signal K via UDP:4123."""
    publish_delta(
        source_label='WIT',
        values=[
            {'path': 'navigation.attitude.roll', 'value': data['roll']},
            {'path': 'navigation.attitude.pitch', 'value': data['pitch']},
            {'path': 'navigation.attitude.yaw', 'value': data['yaw']},
            {'path': 'navigation.headingMagnetic', 'value': data['headingMagnetic']},
            # Raw quaternion (WitMotion convention: Q0=x Q1=y Q2=z Q3=w)
            {'path': 'sensors.wit.quaternion.w', 'value': data.get('qw', 0)},
            {'path': 'sensors.wit.quaternion.x', 'value': data.get('qx', 0)},
            {'path': 'sensors.wit.quaternion.y', 'value': data.get('qy', 0)},
            {'path': 'sensors.wit.quaternion.z', 'value': data.get('qz', 0)},
        ],
        logger=logger,
    )
    logger.info(
        f'[DATA_OUT] Roll={math.degrees(data["roll"]):.1f}° '
        f'Pitch={math.degrees(data["pitch"]):.1f}° '
        f'Hdg={math.degrees(data["headingMagnetic"]):.1f}°'
    )



def send_temperature(temp_c: float, logger) -> None:
    """Publish boat interior temperature (WIT mounted inside cabin).
    Uses environment.inside.temperature (Kelvin per Signal K spec).
    """
    publish_delta(source_label='WIT',
        values=[{'path': 'environment.inside.temperature', 'value': temp_c + 273.15}],
        logger=logger)

def send_pressure(pressure_pa: float, logger) -> None:
    """Publish barometric pressure from WIT BMP280.
    Uses environment.outside.pressure (Pa per Signal K spec).
    """
    publish_delta(source_label='WIT',
        values=[{'path': 'environment.outside.pressure', 'value': pressure_pa}],
        logger=logger)

def send_mag(data: dict, logger) -> None:
    """Publish magnetic field + temperature to SK."""
    values = [
        {'path': 'sensors.wit.magneticField.x', 'value': data['hx_ut']},
        {'path': 'sensors.wit.magneticField.y', 'value': data['hy_ut']},
        {'path': 'sensors.wit.magneticField.z', 'value': data['hz_ut']},
    ]
    if 'temp_c' in data:
        values.append({'path': 'sensors.wit.temperature', 'value': data['temp_c'] + 273.15})
    publish_delta(source_label='WIT', values=values, logger=logger)

def send_motion(data: dict, logger) -> None:
    """Publish acceleration + rateOfTurn to Signal K via UDP:4123."""
    publish_delta(
        source_label='WIT',
        values=[
            {'path': 'navigation.acceleration.x', 'value': data['accel_x']},
            {'path': 'navigation.acceleration.y', 'value': data['accel_y']},
            {'path': 'navigation.acceleration.z', 'value': data['accel_z']},
            {'path': 'navigation.rateOfTurn', 'value': data['gyro_z']},
        ],
        logger=logger,
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — HEARTBEAT
# ══════════════════════════════════════════════════════════════════════════════

def log_heartbeat(logger) -> None:
    """Periodic status log every HEARTBEAT_S seconds."""
    global _wit_state
    if time.time() - _stats['last_heartbeat'] >= HEARTBEAT_S:
        if _stats['packets_0x71'] > 0 or _stats['packets_0x61'] > 0:
            _wit_state = 'STREAMING'
        logger.info(
            f'[HEARTBEAT] state={_wit_state} '
            f'0x71={_stats["packets_0x71"]} '
            f'0x61={_stats["packets_0x61"]} '
            f'SK={_stats["sk_posts"]} '
            f'l1_fails={_stats["l1_fails"]}'
        )
        _stats['packets_0x71'] = 0
        _stats['packets_0x61'] = 0
        _stats['sk_posts'] = 0
        _stats['last_heartbeat'] = time.time()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — BLE NOTIFICATION CALLBACK (FACTORY)
# ══════════════════════════════════════════════════════════════════════════════

def make_data_handler(logger):
    """Factory: returns a BLE notification callback bound to logger."""
    def handle_data(sender, data):
        """BLE notification callback — synchronous, no async issues."""
        pkt_0x71 = decode_0x71_packet(bytes(data))
        if pkt_0x71:
            _stats['packets_0x71'] += 1
            att = apply_mounting_and_extract(pkt_0x71)
            send_attitude(att, logger)
            _stats['sk_posts'] += 1

        # Magnetic field + temperature (CMD_MAG response)
        mag = decode_0x71_mag_packet(bytes(data))
        if mag and (mag.get('hx_ut', 0) != 0.0 or 'temp_c' in mag):
            send_mag(mag, logger)
            _stats['sk_posts'] += 1

        # Pressure from CMD_PRES
        pres = decode_0x71_pres_packet(bytes(data))
        if pres:
            send_pressure(pres['pressure_pa'], logger)

        # Temperature from 0x54 auto-stream
        t54 = decode_0x54_packet(bytes(data))
        if t54:
            send_temperature(t54['temp_c'], logger)

        pkt_0x61 = decode_0x61_packet(bytes(data))
        if pkt_0x61:
            _stats['packets_0x61'] += 1
            send_motion(pkt_0x61, logger)
            _stats['sk_posts'] += 1

        log_heartbeat(logger)
    return handle_data

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — MAIN BLE LOOP
# ══════════════════════════════════════════════════════════════════════════════

async def run_ble_client(logger) -> None:
    """
    Main BLE connection loop with internal recovery.

    WIT initialization state machine:
    - UNINITIALIZED: first connect → send ENABLE_QUAT_CMD once
      The WIT responds with 1 packet then resets. State → WAIT_RECONNECT.
    - WAIT_RECONNECT: reconnect → subscribe only, NO commands
      WIT streams continuously (NVRAM config retained).
    - STREAMING: confirmed by heartbeat (packets_0x71 > 0)
    """
    global _running, _was_connected, _last_err, _wit_state

    acquire_singleton(PID_FILE, logger)
    try:
        logger.info('[STARTUP] ' + '=' * 58)
        logger.info('[STARTUP] wit-ble-direct — WIT WT901BLECL IMU Driver')
        logger.info(f'[STARTUP] MAC={WIT_MAC} Rate={OUTPUT_RATE_HZ}Hz Mount={MOUNT_AXIS}/{MOUNT_DEG}°')
        logger.info(f'[STARTUP] L2_threshold={L2_FAIL_THRESHOLD}')
        logger.info('[STARTUP] ' + '=' * 58)

        if not check_sk_reachable():
            logger.warning(
                '[DEPENDENCY_CHECK] Signal K not ready at startup — will retry when publishing')
        if not check_ble_adapter():
            logger.error('[STARTUP] BLE adapter (hci0) not available — exiting')
            sys.exit(1)

        # Clear BlueZ GATT cache for WIT — prevents stale characteristic discovery
        try:
            import subprocess as _sp
            _sp.run(f'bluetoothctl remove {WIT_MAC}',
                    shell=True, capture_output=True, timeout=5)
            logger.info(f'[STARTUP] BlueZ GATT cache cleared for {WIT_MAC}')
        except Exception:
            pass  # Non-fatal

        reconnect_delay = RECONNECT_BASE_S
        l1_fail_count = 0
        handle_data = make_data_handler(logger)

        while _running:
            try:
                async with BleakClient(WIT_MAC) as client:
                    logger.info(f'[BLE_CONNECT] Connected to {WIT_MAC}')
                    l1_fail_count = 0
                    reconnect_delay = RECONNECT_BASE_S
                    _was_connected = True

                    # Use WRITE_UUID directly (ffe9-9a34fb)
                    # DO NOT use dynamic discovery — BlueZ GATT cache returns
                    # 0x2a00 (Device Name) as first write-capable char, causing
                    # NotAuthorized error when we try to send ENABLE_QUAT.
                    # ffe9-9a34fb is confirmed present on WIT WT901BLECL (2026-05-29).
                    write_uuid = WRITE_UUID
                    logger.debug(f'[BLE_SETUP] Using hardcoded write char: {write_uuid}')

                    # State machine
                    if _wit_state == 'UNINITIALIZED':
                        # First connection: send ENABLE_QUAT_CMD once
                        # WIT responds with 1 packet then resets → reconnect
                        cmd_uuid = write_uuid or NOTIFY_UUID
                        logger.info(
                            f'[BLE_SETUP] State=UNINITIALIZED: sending ENABLE_QUAT to {cmd_uuid}')
                        try:
                            await client.write_gatt_char(
                                cmd_uuid, ENABLE_QUAT_CMD, response=False)
                            logger.info('[BLE_SETUP] ENABLE_QUAT sent — WIT will reset')
                            _wit_state = 'WAIT_RECONNECT'
                            await asyncio.sleep(8)  # WIT resets during this
                            await asyncio.sleep(3)  # Extra: let WIT resume advertising
                            logger.info('[BLE_SETUP] State→WAIT_RECONNECT — reconnecting')
                        except Exception as e:
                            logger.warning(f'[BLE_SETUP] ENABLE_QUAT failed: {e}')
                            _wit_state = 'WAIT_RECONNECT'
                        # Connection dead after WIT reset — exit to trigger reconnect
                        continue

                    else:
                        # WAIT_RECONNECT or STREAMING: subscribe without commands
                        logger.info(
                            f'[BLE_SETUP] State={_wit_state}: subscribing without commands')

                    # Subscribe to BLE notifications
                    await client.start_notify(NOTIFY_UUID, handle_data)
                    logger.info('[BLE_NOTIFY] Subscribed — waiting for WIT data')

                    # Poll for quaternion at 10Hz
                    # 0x71 is a ONE-SHOT response (not auto-streamed)
                    # FF AA 27 51 00 triggers ONE 0x71 packet from WIT
                    # Must send at desired rate to get continuous data
                    poll_interval = 1.0 / OUTPUT_RATE_HZ  # 0.1s at 10Hz
                    poll_errors = 0
                    poll_cycle = 0

                    while client.is_connected and _running:
                        try:
                            await client.write_gatt_char(
                                WRITE_UUID, ENABLE_QUAT_CMD, response=False)
                            if poll_cycle % 10 == 0:  # CMD_MAG ~1Hz
                                await asyncio.sleep(0.015)
                                await client.write_gatt_char(
                                    WRITE_UUID, CMD_MAG, response=False)
                            if poll_cycle % 30 == 0:  # CMD_PRES ~0.3Hz
                                await asyncio.sleep(0.015)
                                await client.write_gatt_char(
                                    WRITE_UUID, CMD_PRES, response=False)
                            poll_cycle += 1
                            poll_errors = 0
                        except Exception as poll_e:
                            poll_errors += 1
                            logger.debug(f'[POLL] Error #{poll_errors}: {poll_e}')
                            if poll_errors >= 10:
                                logger.warning('[POLL] 10 errors — reconnecting')
                                break
                        await asyncio.sleep(poll_interval)

                    logger.warning('[BLE_DISCONNECT] WIT disconnected — will reconnect')

            except Exception as e:
                l1_fail_count += 1
                _stats['l1_fails'] += 1
                _last_err = str(e)
                logger.warning(f'[L1] Connection failed ({l1_fail_count}): {e}')

                # BT_RECOVERY: zombie session detection (validated 2026-05-29)
                # Targets WIT_MAC only — Calypso BLE unaffected
                if (_was_connected
                    and 'not found' in _last_err.lower()
                    and l1_fail_count >= 3):
                    recovered = await bt_recovery(WIT_MAC, logger)
                    if recovered:
                        l1_fail_count = 0
                        reconnect_delay = RECONNECT_BASE_S
                        _was_connected = False
                        _last_err = ''

                # L2: clean exit → systemd restart
                # hci0 NOT reset: would disrupt Calypso BLE connection
                if l1_fail_count >= L2_FAIL_THRESHOLD:
                    logger.warning(
                        f'[L2] {l1_fail_count} failures — clean exit for systemd restart')
                    logger.warning('[L2] hci0 NOT reset: would disrupt Calypso BLE')
                    break

                reconnect_delay = min(reconnect_delay * 2, RECONNECT_MAX_S)
                logger.info(f'[L1] Reconnecting in {reconnect_delay}s...')
                await asyncio.sleep(reconnect_delay)

    finally:
        release_singleton(PID_FILE, logger)
        logger.info('[SHUTDOWN] wit-ble-direct stopped — PID released')

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    _logger = setup_logger(SERVICE_NAME)

    def _set_stop():
        global _running
        _running = False

    setup_signal_handlers(_set_stop, _logger)
    asyncio.run(run_ble_client(_logger))

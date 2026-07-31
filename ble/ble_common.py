"""
ble_common.py — Shared BLE infrastructure for Midnight Rider drivers.

Used by:
 - calypso_direct.py (Calypso UP10 wind sensor)
 - wit-ble-direct.py (WIT WT901BLECL IMU)

Provides:
 - Structured logging (RotatingFileHandler)
 - SK UDP delta publishing
 - Singleton (one instance per service)
 - BLE adapter + SK connectivity checks
 - BT zombie recovery (bluetoothctl disconnect/remove)
 - Signal handler setup

All device-specific logic (UUIDs, packet decoding, SK paths)
stays in the individual driver files.
"""

import asyncio
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ── Logging ───────────────────────────────────────────────────

LOG_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'logs', 'services'
)

def setup_logger(service_name: str) -> logging.Logger:
    """Standard structured logger for Midnight Rider BLE drivers."""
    os.makedirs(LOG_BASE, exist_ok=True)
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = RotatingFileHandler(
            os.path.join(LOG_BASE, f'{service_name}.log'),
            maxBytes=5 * 1024 * 1024,  # 5MB — MR logging standard
            backupCount=3
        )
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        ))
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


# ── Singleton ─────────────────────────────────────────────────

def acquire_singleton(pid_file: str, logger: logging.Logger) -> None:
    """Ensure only one instance runs. Exit if duplicate."""
    p = Path(pid_file)
    if p.exists():
        old_pid = p.read_text().strip()
        try:
            os.kill(int(old_pid), 0)
            logger.error(f'Already running (PID {old_pid}) — exiting')
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            pass
    p.write_text(str(os.getpid()))
    logger.info(f'Singleton acquired (PID {os.getpid()})')


def release_singleton(pid_file: str, logger: logging.Logger) -> None:
    """Remove PID file on clean exit."""
    try:
        Path(pid_file).unlink(missing_ok=True)
        logger.info('Singleton released')
    except Exception as e:
        logger.warning(f'Could not release singleton: {e}')


# ── SK UDP Publisher ───────────────────────────────────────────

SK_HOST = os.environ.get('SK_UDP_HOST', '127.0.0.1')
SK_PORT = int(os.environ.get('SK_UDP_PORT', '4123'))
_sk_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def publish_delta(source_label: str, values: list, logger: logging.Logger) -> bool:
    """
    Publish a Signal K delta via UDP.

    Args:
        source_label: SK source identifier (e.g. 'WIT', 'calypso-direct')
        values: list of {'path': str, 'value': float/dict}
        logger: service logger

    Returns:
        True on success, False on error
    """
    delta = {
        'updates': [{
            'source': {'label': source_label, 'type': 'BLE'},
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'values': values
        }]
    }
    try:
        msg = json.dumps(delta).encode()
        _sk_sock.sendto(msg, (SK_HOST, SK_PORT))
        return True
    except Exception as e:
        logger.error(f'SK publish failed: {e}')
        return False


# ── Health Checks ─────────────────────────────────────────────

def check_sk_reachable(host: str = '127.0.0.1', port: int = SK_PORT) -> bool:
    """Check if Signal K UDP receiver is listening."""
    try:
        test = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test.settimeout(1)
        test.sendto(b'{}', (host, port))
        return True
    except Exception:
        return False
    finally:
        test.close()


def check_ble_adapter(adapter: str = 'hci0') -> bool:
    """Check if BLE adapter is UP and running."""
    try:
        r = subprocess.run(
            f'hciconfig {adapter}', shell=True,
            capture_output=True, text=True, timeout=5)
        return 'UP RUNNING' in r.stdout
    except Exception:
        return False


# ── BT Zombie Recovery ────────────────────────────────────────

async def bt_recovery(mac: str, logger: logging.Logger) -> bool:
    """
    Clear a zombie BLE session for a specific device MAC.

    Sends bluetoothctl disconnect + remove to the target MAC only.
    Does NOT affect other BLE devices (e.g. other driver's device).

    Validated 2026-05-29: manual test confirmed WIT visibility restored.

    Returns:
        True if recovery was attempted, False on error
    """
    logger.warning(f'BT_RECOVERY: clearing zombie session for {mac}')
    try:
        r1 = subprocess.run(
            f'bluetoothctl disconnect {mac}',
            shell=True, capture_output=True, text=True, timeout=10)
        logger.info(f'BT_RECOVERY: disconnect: {(r1.stdout+r1.stderr).strip()[:80]}')
        await asyncio.sleep(2)

        r2 = subprocess.run(
            f'bluetoothctl remove {mac}',
            shell=True, capture_output=True, text=True, timeout=10)
        logger.info(f'BT_RECOVERY: remove: {(r2.stdout+r2.stderr).strip()[:80]}')
        await asyncio.sleep(3)

        logger.info(f'BT_RECOVERY: {mac} cleared — retrying connection')
        return True
    except Exception as e:
        logger.error(f'BT_RECOVERY: failed: {e}')
        return False


# ── Signal Handlers ───────────────────────────────────────────

def setup_signal_handlers(running_flag_setter, logger: logging.Logger) -> None:
    """
    Register SIGTERM/SIGINT handlers for graceful BLE shutdown.

    IMPORTANT: Does NOT call sys.exit() — lets BleakClient.__aexit__
    send a proper BLE DISCONNECT to the device. Without clean disconnect,
    the device enters zombie state and becomes invisible to BLE scans.

    Args:
        running_flag_setter: callable that sets _running = False
        logger: service logger
    """
    def _stop(sig, frame):
        logger.info(f'Signal {sig} — stopping cleanly (BLE disconnect will follow)')
        running_flag_setter()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

#!/usr/bin/env python3
"""
calypso_watchdog.py — Calypso UP10 BLE Watchdog

Monitors calypso_anemometer service health via Signal K data freshness.
Triggers escalating recovery when wind data goes stale.

DESIGN RULES (from BLE conflict incidents):
 1. SINGLETON — PID file: only ONE watchdog allowed
 2. ZOMBIE KILL — pkill -f calypso-anemometer BEFORE every restart
 3. VERIFY STOP — confirm process count=0 before starting
 4. COOLDOWN — mandatory wait between actions
 5. CORRECT SVC — calypso_anemometer (underscore, not hyphen)
 6. CONFLICT — detect >1 process running and fix immediately

Recovery escalation:
 L1: restart service (SIGTERM → SIGKILL → start)
 L2: reset hci0 adapter + restart
 L3: full bluetooth daemon reset + re-trust + restart

Environment:
 CALYPSO_BLE_ADDRESS MAC address of Calypso UP10
 CALYPSO_SERVICE Systemd service name (default: calypso_anemometer)

Logs: logs/services/calypso-watchdog.log
PID: /tmp/calypso_watchdog.pid
"""

import datetime
import json
import logging
import os
import signal
import subprocess
import sys
import time
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
CALYPSO_MAC = os.environ.get('CALYPSO_BLE_ADDRESS', 'F8:5F:12:9D:D2:EE')
CALYPSO_SERVICE = os.environ.get('CALYPSO_SERVICE', 'calypso_anemometer')
SK_URL = 'http://localhost:3000/signalk/v1/api/vessels/self/environment/wind'
PID_FILE = '/tmp/calypso_watchdog.pid'
DATA_TIMEOUT_S = 120
CHECK_INTERVAL_S = 30
COOLDOWN_S = 60
KILL_GRACE_S = 5

# ── Logging ───────────────────────────────────────────────────────────────────
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

logger = logging.getLogger('calypso-watchdog')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'calypso-watchdog.log'),
    maxBytes=5*1024*1024, backupCount=3
)
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [calypso-watchdog] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
))
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler(sys.stdout))

def log(msg, level='INFO'):
    getattr(logger, level.lower(), logger.info)(msg)

# ── Singleton ─────────────────────────────────────────────────────────────────
def acquire_singleton():
    if os.path.exists(PID_FILE):
        try:
            pid = int(Path(PID_FILE).read_text().strip())
            os.kill(pid, 0)
            log(f'FATAL: Another watchdog running (PID {pid}) — exiting', 'error')
            log('To force restart: rm /tmp/calypso_watchdog.pid', 'error')
            sys.exit(1)
        except ProcessLookupError:
            log(f'Stale PID file — removing', 'warning')
        except (ValueError, PermissionError):
            pass
    Path(PID_FILE).write_text(str(os.getpid()))
    log(f'Singleton acquired (PID {os.getpid()})')

def release_singleton():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass

# ── Shutdown ──────────────────────────────────────────────────────────────────
running = True

def _stop(sig, frame):
    global running
    log(f'Signal {sig} — shutting down')
    running = False

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

# ── System commands ───────────────────────────────────────────────────────────
def run_cmd(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout+r.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, f'TIMEOUT {timeout}s'
    except Exception as e:
        return False, str(e)

def process_count():
    """Return number of calypso-anemometer processes currently running."""
    ok, out = run_cmd('pgrep -c -f calypso-anemometer')
    try:
        return int(out.strip()) if ok else 0
    except ValueError:
        return 0

def kill_all_calypso():
    """
    Kill ALL calypso-anemometer processes.
    MUST be called before any restart to prevent BLE conflicts.
    Returns: number of processes that were killed.
    """
    ok, out = run_cmd('pgrep -f calypso-anemometer')
    if not ok or not out.strip():
        log('No calypso-anemometer processes — clean state ✅')
        return 0

    pids = [p.strip() for p in out.strip().splitlines() if p.strip()]
    log(f'Killing {len(pids)} calypso-anemometer process(es): {pids}', 'warning')

    run_cmd('pkill -SIGTERM -f calypso-anemometer')
    time.sleep(KILL_GRACE_S)

    ok, out = run_cmd('pgrep -f calypso-anemometer')
    if ok and out.strip():
        log('Processes survived SIGTERM — sending SIGKILL', 'warning')
        run_cmd('pkill -SIGKILL -f calypso-anemometer')
        time.sleep(2)

    remaining = process_count()
    if remaining > 0:
        log(f'WARNING: {remaining} process(es) still alive after SIGKILL!', 'error')
    else:
        log('All calypso-anemometer processes terminated ✅')
    return len(pids)

# ── Signal K health ───────────────────────────────────────────────────────────
def get_wind_age_seconds():
    """Return seconds since last wind update, or 999 if unavailable."""
    try:
        with urllib.request.urlopen(SK_URL, timeout=5) as r:
            data = json.loads(r.read())
            sa = data.get('speedApparent')
            if not sa:
                return 999.0
            value = sa.get('value')
            ts_str = sa.get('timestamp')
            if not ts_str:
                return 0.0 if value is not None else 999.0
            from datetime import timezone
            ts = ts_str.strip().rstrip('Z')
            if '.' in ts:
                ts = ts.split('.')[0]
            ts += '+00:00'
            try:
                dt = datetime.datetime.fromisoformat(ts)
            except ValueError:
                log(f"Cannot parse timestamp '{ts_str}' — assuming fresh", 'warning')
                return 0.0 if value is not None else 999.0
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.datetime.now(timezone.utc)-dt).total_seconds())
    except urllib.error.URLError as e:
        log(f'SK unreachable: {e}', 'warning')
        return 999.0
    except Exception as e:
        log(f'Wind check error: {e}', 'warning')
        return 999.0

# ── Recovery actions ──────────────────────────────────────────────────────────
def action_L1():
    log('L1: Service restart (kill zombies first)', 'warning')
    kill_all_calypso()
    ok, out = run_cmd(f'sudo systemctl restart {CALYPSO_SERVICE}')
    log(f'L1: restart → {"OK ✅" if ok else "FAILED ❌"}: {out[:100]}')
    time.sleep(5)
    n = process_count()
    log(f'L1: post-restart process count = {n} (expected: 1){"✅" if n==1 else " ⚠️"}')
    log(f'L1 done — cooldown {COOLDOWN_S}s')
    time.sleep(COOLDOWN_S)

def action_L2():
    log('L2: BLE adapter (hci0) reset + restart', 'warning')
    run_cmd(f'sudo systemctl stop {CALYPSO_SERVICE}')
    time.sleep(2)
    kill_all_calypso()
    log('L2: resetting hci0...')
    run_cmd('sudo hciconfig hci0 down')
    time.sleep(3)
    run_cmd('sudo hciconfig hci0 up')
    time.sleep(3)
    if process_count() > 0:
        log('L2: zombie still alive before start — killing again', 'error')
        kill_all_calypso()
    ok, out = run_cmd(f'sudo systemctl start {CALYPSO_SERVICE}')
    log(f'L2: start → {"OK ✅" if ok else "FAILED ❌"}: {out[:100]}')
    time.sleep(5)
    log(f'L2 done — process count={process_count()} — cooldown {COOLDOWN_S}s')
    time.sleep(COOLDOWN_S)

def action_L3():
    log('L3: FULL BLE reset (bluetooth daemon re-pair)', 'error')
    run_cmd(f'sudo systemctl stop {CALYPSO_SERVICE}')
    time.sleep(2)
    kill_all_calypso()
    log('L3: stopping bluetooth...')
    run_cmd('sudo systemctl stop bluetooth')
    time.sleep(3)
    run_cmd('sudo hciconfig hci0 reset')
    time.sleep(2)
    run_cmd('sudo systemctl start bluetooth')
    time.sleep(4)
    run_cmd('sudo hciconfig hci0 up')
    time.sleep(2)
    log(f'L3: re-trusting {CALYPSO_MAC}...')
    run_cmd(f'bluetoothctl remove {CALYPSO_MAC}')
    time.sleep(1)
    run_cmd('bluetoothctl power on')
    time.sleep(1)
    run_cmd(f'bluetoothctl trust {CALYPSO_MAC}')
    time.sleep(2)
    if process_count() > 0:
        log('L3: zombie alive before start — killing', 'error')
        kill_all_calypso()
    ok, out = run_cmd(f'sudo systemctl start {CALYPSO_SERVICE}')
    log(f'L3: start → {"OK ✅" if ok else "FAILED ❌"}: {out[:100]}')
    time.sleep(5)
    log(f'L3 done — process count={process_count()} — cooldown {COOLDOWN_S*2}s')
    time.sleep(COOLDOWN_S * 2)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    acquire_singleton()
    try:
        log(f'STARTUP: service={CALYPSO_SERVICE} mac={CALYPSO_MAC}')
        log(f'STARTUP: timeout={DATA_TIMEOUT_S}s check={CHECK_INTERVAL_S}s cooldown={COOLDOWN_S}s')

        # Startup sanity
        n = process_count()
        if n > 1:
            log(f'STARTUP: {n} instances detected — cleaning up', 'error')
            kill_all_calypso()
            run_cmd(f'sudo systemctl start {CALYPSO_SERVICE}')
            time.sleep(10)
        elif n == 0:
            log('STARTUP: no process running — starting service')
            run_cmd(f'sudo systemctl start {CALYPSO_SERVICE}')
            time.sleep(10)
        else:
            log(f'STARTUP: 1 process running ✅')

        consecutive_fails = 0

        while running:
            # Health check 1: BLE process count (conflict detection)
            n = process_count()
            if n > 1:
                log(f'CONFLICT: {n} calypso-anemometer processes detected!', 'error')
                log('Performing emergency clean restart...', 'error')
                kill_all_calypso()
                run_cmd(f'sudo systemctl start {CALYPSO_SERVICE}')
                consecutive_fails = 0
                time.sleep(COOLDOWN_S)
                continue

            # Health check 2: data freshness
            age = get_wind_age_seconds()

            if age < DATA_TIMEOUT_S:
                if consecutive_fails > 0:
                    log(f'✅ Data OK (age={age:.0f}s) — counter reset')
                    consecutive_fails = 0
            else:
                consecutive_fails += 1
                log(f'⚠️ Stale data: {age:.0f}s (fail #{consecutive_fails})', 'warning')
                if consecutive_fails == 1:
                    action_L1()
                elif consecutive_fails == 2:
                    action_L2()
                elif consecutive_fails >= 3:
                    action_L3()
                    consecutive_fails = 0

            time.sleep(CHECK_INTERVAL_S)

    finally:
        release_singleton()
        log('SHUTDOWN complete — PID file released')

if __name__ == '__main__':
    main()

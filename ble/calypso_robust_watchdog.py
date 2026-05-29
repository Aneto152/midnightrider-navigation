#!/usr/bin/env python3
"""Calypso Watchdog v3 — Fixed 2026-05-21
Root cause fix: fromisoformat crash on SK timestamp format + cooldown anti-death-spiral"""
import subprocess, time, datetime, json, os, urllib.request

CALYPSO_SERVICE = "calypso-anemometer"
MAC = "F8:5F:12:9D:D2:EE"
SK_URL = "http://localhost:3000/signalk/v1/api/vessels/self/environment/wind"
LOG_FILE = "/tmp/calypso_watchdog.log"
DATA_TIMEOUT_S = 120  # Was 60 — too aggressive
CHECK_INTERVAL_S = 30  # Was 15 — too frequent
COOLDOWN_S = 60  # New: wait after each action before checking again

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout + r.stderr
    except Exception as e:
        return False, str(e)

def get_wind_age_seconds():
    """Fixed: robust SK timestamp parsing. Falls back to value check if parse fails."""
    try:
        with urllib.request.urlopen(SK_URL, timeout=5) as r:
            data = json.loads(r.read())
        sa = data.get("speedApparent")
        if not sa:
            return 999
        value = sa.get("value")
        ts_str = sa.get("timestamp")
        if not ts_str:
            # Has value but no timestamp — data is fresh
            return 0 if value is not None else 999
        from datetime import timezone
        # Fix: strip Z, then strip microseconds before parsing
        ts = ts_str.strip()
        if ts.endswith("Z"):
            ts = ts[:-1]
        # Remove microseconds: "2026-05-21T17:01:46.123" → "2026-05-21T17:01:46"
        if "." in ts:
            ts = ts.split(".")[0]
        # Add UTC timezone
        ts += "+00:00"
        try:
            dt = datetime.datetime.fromisoformat(ts)
        except ValueError:
            # Cannot parse — if we have a value, assume fresh
            log(f"Cannot parse timestamp '{ts_str}' — using value fallback")
            return 0 if value is not None else 999
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.datetime.now(timezone.utc) - dt).total_seconds())
    except urllib.error.URLError as e:
        log(f"SK unreachable: {e}")
        return 999
    except Exception as e:
        log(f"Wind check error: {e}")
        return 999

def action_L1():
    log(f"L1: Restart {CALYPSO_SERVICE}")
    run(f"sudo systemctl restart {CALYPSO_SERVICE}")
    log(f"L1 done — cooldown {COOLDOWN_S}s")
    time.sleep(COOLDOWN_S)

def action_L2():
    log("L2: Reset hci0")
    run(f"sudo systemctl stop {CALYPSO_SERVICE}")
    run("sudo hciconfig hci0 down")
    time.sleep(3)
    run("sudo hciconfig hci0 up")
    time.sleep(3)
    run(f"sudo systemctl start {CALYPSO_SERVICE}")
    log(f"L2 done — cooldown {COOLDOWN_S}s")
    time.sleep(COOLDOWN_S)

def action_L3():
    log("L3: Full BLE reset")
    run(f"sudo systemctl stop {CALYPSO_SERVICE}")
    run("sudo systemctl stop bluetooth")
    time.sleep(3)
    run("sudo hciconfig hci0 reset")
    run("sudo systemctl start bluetooth")
    time.sleep(4)
    run("sudo hciconfig hci0 up")
    time.sleep(2)
    run(f"bluetoothctl remove {MAC}")
    run("bluetoothctl power on")
    run(f"bluetoothctl trust {MAC}")
    run(f"sudo systemctl start {CALYPSO_SERVICE}")
    log(f"L3 done — cooldown {COOLDOWN_S * 2}s")
    time.sleep(COOLDOWN_S * 2)

log(f"Watchdog v3 started — timeout={DATA_TIMEOUT_S}s check={CHECK_INTERVAL_S}s cooldown={COOLDOWN_S}s")
consecutive_fails = 0

while True:
    age = get_wind_age_seconds()
    if age < DATA_TIMEOUT_S:
        if consecutive_fails > 0:
            log(f"✅ Data OK (age={age:.0f}s) — reset counter")
            consecutive_fails = 0
    else:
        consecutive_fails += 1
        log(f"⚠️ No data {age:.0f}s (fail #{consecutive_fails})")
        if consecutive_fails == 1:
            action_L1()
        elif consecutive_fails == 2:
            action_L2()
        elif consecutive_fails >= 3:
            action_L3()
            consecutive_fails = 0
    time.sleep(CHECK_INTERVAL_S)

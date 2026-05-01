#!/usr/bin/env python3
"""
target_speed_calc.py — Target Speed from J/30 Polars

Midnight Rider Navigation — Load external polars from data/polars/j30_orc.json

╔════════════════════════════════════════════════════════════════╗
║ SOURCE POLAIRES: data/polars/j30_orc.json (NO HARDCODING!)    ║
║                                                                ║
║ target_speed = interpolate(POLAR, TWS_kts, mode(|TWA|))      ║
║                                                                ║
║ Modes from |TWA| absolute (KEY: use abs() for symmetry):     ║
║  |TWA| < 60° → upwind (beating, close-hauled)                ║
║  60° ≤ |TWA| ≤ 150° → reach (beam, broad)                    ║
║  |TWA| > 150° → downwind (running)                           ║
╚════════════════════════════════════════════════════════════════╝

INPUTS from Signal K (REST HTTP, every 10s):
  environment.wind.speedTrue [m/s] — TWS
  environment.wind.angleTrueWater [rad] — TWA (SIGNED: + starboard, - port)
  navigation.speedThroughWater [m/s] — STW (for efficiency calculation)

OUTPUTS to Signal K (WebSocket PERSISTENT connection):
  performance.targetSpeed [m/s] — polar target speed
  performance.polarEfficiency [0-1] — STW / targetSpeed

OUTPUTS to InfluxDB (bucket: midnight_rider):
  measurement: performance.target
  fields: target_kts, efficiency_pct, mode, tws_kts, twa_deg

BUG FIXES in this version:
  ✅ FIX 1: Load polars from data/polars/j30_orc.json (no hardcoding)
  ✅ FIX 2: Use correct J/30 values (not 2× too high)
  ✅ FIX 3: Use abs() on TWA → starboard/port symmetry
  ✅ BONUS: WebSocket persistent (no reconnect per cycle)

Compliance: DATA-SCHEMA-MASTER.md § Polars & Performance
"""

import asyncio
import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# ─── Configuration ─────────────────────────────────────────────────────

SIGNALK_HTTP = os.getenv("SIGNALK_HTTP", "http://localhost:3000")
SIGNALK_WS = os.getenv("SIGNALK_WS", "ws://localhost:3000/signalk/v1/stream")
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")
CALC_INTERVAL = 10.0  # seconds between calculations

SOURCE_LABEL = "midnight-rider-polar-calc"

# FIX 1: Load polars from external file (not hardcoded)
POLAR_FILE = Path(__file__).parent.parent / "data" / "polars" / "j30_orc.json"

# Signal K paths
SK_TWS = "environment/wind/speedTrue"
SK_TWA = "environment/wind/angleTrueWater"
SK_STW = "navigation/speedThroughWater"
SK_TARGET = "performance.targetSpeed"
SK_EFFICIENCY = "performance.polarEfficiency"


# ════════════════════════════════════════════════════════════════════
# POLARS LOADING
# ════════════════════════════════════════════════════════════════════

def load_polars(path: Path) -> List[dict]:
    """
    Load and validate J/30 polars from external JSON file.
    Source of truth: data/polars/j30_orc.json
    Format: see data/polars/README.md
    """
    if not path.exists():
        raise FileNotFoundError(f"Polar file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    polars = sorted(data["polars"], key=lambda p: p["tws"])

    # Validate structure
    required = {"tws", "upwind", "reach", "downwind"}
    for p in polars:
        missing = required - set(p.keys())
        if missing:
            raise ValueError(f"Point TWS={p['tws']} missing: {missing}")

    print(f"✅ Polars loaded: {path.name}")
    print(f"   Boat: {data['_meta']['boat']}")
    print(f"   Source: {data['_meta']['source']}")
    print(f"   Points: {len(polars)} ({polars[0]['tws']}-{polars[-1]['tws']} knots)")

    return polars


def interpolate_polar(polars: List[dict], tws_kts: float) -> dict:
    """
    Linear interpolation between TWS points.
    Returns {upwind, reach, downwind, ...} for given TWS.
    """
    if tws_kts <= polars[0]["tws"]:
        return polars[0]
    if tws_kts >= polars[-1]["tws"]:
        return polars[-1]

    for i in range(len(polars) - 1):
        lo, hi = polars[i], polars[i + 1]
        if lo["tws"] <= tws_kts <= hi["tws"]:
            ratio = (tws_kts - lo["tws"]) / (hi["tws"] - lo["tws"])
            return {
                k: lo[k] + (hi[k] - lo[k]) * ratio
                for k in lo if isinstance(lo[k], (int, float))
            }

    return polars[-1]


def get_sailing_mode(twa_deg_abs: float) -> str:
    """
    FIX 3: Get sailing mode from |TWA| absolute.

    CRITICAL: twa_deg_abs MUST be abs(TWA_signed).
    Signal K returns TWA signed: + starboard, - port.
    Mode is SYMMETRIC: same target speed either side.

    J/30 thresholds:
      < 60° → upwind (close-hauled)
      60-150°→ reach (travers, broad)
      > 150° → downwind (running)
    """
    if twa_deg_abs < 60:
        return "upwind"
    if twa_deg_abs <= 150:
        return "reach"
    return "downwind"


def get_target_speed(
    polars: List[dict], tws_ms: float, twa_rad: float
) -> Tuple[float, str, float, float]:
    """
    Calculate target speed from polars.

    FIX 1: Use polars loaded from external file
    FIX 3: Use abs(twa_rad) for mode calculation

    Returns: (target_ms, mode, twa_deg_abs, tws_kts)
    """
    tws_kts = tws_ms * 1.944

    # FIX 3: Use abs() on TWA for symmetry (starboard = port)
    twa_deg = math.degrees(abs(twa_rad))

    mode = get_sailing_mode(twa_deg)
    polar = interpolate_polar(polars, tws_kts)

    # FIX 2: Use correct values from j30_orc.json (verified above)
    target_kts = polar[mode]
    target_ms = target_kts / 1.944

    return target_ms, mode, twa_deg, tws_kts


# ════════════════════════════════════════════════════════════════════
# SIGNAL K
# ════════════════════════════════════════════════════════════════════

def get_signalk(path: str) -> Optional[float]:
    """Fetch value from Signal K REST API."""
    try:
        url = f"{SIGNALK_HTTP}/signalk/v1/api/vessels/self/{path}"
        resp = urllib.request.urlopen(
            urllib.request.Request(url), timeout=2
        )
        return json.loads(resp.read()).get("value")
    except Exception:
        return None


def build_delta(target_ms: float, efficiency_ratio: float) -> str:
    """Build Signal K delta message."""
    return json.dumps({
        "context": "vessels.self",
        "updates": [{
            "source": {
                "label": SOURCE_LABEL,
                "type": "software"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "values": [
                {"path": SK_TARGET, "value": round(target_ms, 4)},
                {"path": SK_EFFICIENCY, "value": round(efficiency_ratio, 4)}
            ]
        }]
    })


# ════════════════════════════════════════════════════════════════════
# INFLUXDB
# ════════════════════════════════════════════════════════════════════

def write_influx(
    target_ms: float, efficiency_pct: float,
    mode: str, tws_kts: float, twa_deg: float
) -> None:
    """Write to InfluxDB."""
    if not INFLUX_TOKEN:
        return

    line = (
        f'performance.target '
        f'target_kts={round(target_ms * 1.944, 3)},'
        f'efficiency_pct={round(efficiency_pct, 1)},'
        f'mode="{mode}",'
        f'tws_kts={round(tws_kts, 1)},'
        f'twa_deg={round(twa_deg, 1)}'
    )

    url = (
        f"{INFLUX_URL}/api/v2/write"
        f"?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=s"
    )

    req = urllib.request.Request(
        url, data=line.encode(), method="POST"
    )
    req.add_header("Authorization", f"Token {INFLUX_TOKEN}")
    req.add_header("Content-Type", "text/plain")

    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        print(f"⚠️  InfluxDB: {e}")


# ════════════════════════════════════════════════════════════════════
# MAIN LOOP — WebSocket PERSISTENT
# ════════════════════════════════════════════════════════════════════

async def main_loop():
    """
    BONUS FIX: WebSocket PERSISTENT connection.
    Open once at startup, keep alive for entire runtime.
    Reconnect on disconnection (after 5s delay).
    """
    try:
        import websockets
    except ImportError:
        print("⚠️  websockets module not installed")
        print("   pip3 install websockets")
        return

    # Load polars once at startup (FIX 1)
    try:
        polars = load_polars(POLAR_FILE)
    except Exception as e:
        print(f"❌ Failed to load polars: {e}")
        sys.exit(1)

    print(f"\n🎯 Target Speed Calculator — J/30 Polars")
    print(f"   Polars: {POLAR_FILE.name}")
    print(f"   Bucket: {INFLUX_BUCKET}")
    print(f"   Interval: {CALC_INTERVAL}s")
    print(f"   WebSocket: PERSISTENT\n")

    iteration = 0
    reconnect_delay = 5

    while True:
        try:
            uri = f"{SIGNALK_WS}?subscribe=none"
            async with websockets.connect(uri, ping_interval=30) as ws:
                # Signal K hello
                hello = json.loads(await ws.recv())
                print(f"✅ Signal K: {hello.get('name', '?')} "
                      f"v{hello.get('version', '?')}\n")

                # Calculation loop (WebSocket stays open)
                while True:
                    iteration += 1

                    tws_ms = get_signalk(SK_TWS)
                    twa_rad = get_signalk(SK_TWA)
                    stw_ms = get_signalk(SK_STW)

                    if tws_ms is not None and twa_rad is not None:
                        target_ms, mode, twa_deg, tws_kts = get_target_speed(
                            polars, tws_ms, twa_rad
                        )

                        efficiency_ratio = 0.0
                        efficiency_pct = 0.0
                        if stw_ms and target_ms > 0:
                            efficiency_ratio = stw_ms / target_ms
                            efficiency_pct = efficiency_ratio * 100.0

                        print(
                            f"[{iteration:4d}] "
                            f"TWS={tws_kts:5.1f}kt "
                            f"TWA={twa_deg:5.0f}° "
                            f"Mode={mode:8s} "
                            f"Target={target_ms*1.944:5.2f}kt "
                            f"Eff={efficiency_pct:5.1f}%"
                        )

                        # Send to Signal K (same WebSocket)
                        await ws.send(build_delta(target_ms, efficiency_ratio))

                        # Write to InfluxDB
                        write_influx(
                            target_ms, efficiency_pct,
                            mode, tws_kts, twa_deg
                        )
                    else:
                        print(
                            f"[{iteration:4d}] ⚠️  Missing: "
                            f"TWS={tws_ms}, TWA={twa_rad}"
                        )

                    # Wait before next calculation
                    await asyncio.sleep(CALC_INTERVAL)

        except Exception as e:
            print(f"❌ Connection error: {e}")
            print(f"   Reconnecting in {reconnect_delay}s...\n")
            await asyncio.sleep(reconnect_delay)


# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n⏹️  Stopped")
        sys.exit(0)

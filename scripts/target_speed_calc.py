#!/usr/bin/env python3
"""
target_speed_calc.py — Target Speed Calculation from Polars

Midnight Rider Navigation — J/30 Polar Performance

Formula:
  Target Speed = Polar(TWS, TWA)
  
  Where:
    TWS = True Wind Speed (m/s) from environment.wind.speedTrue
    TWA = True Wind Angle (rad) from environment.wind.angleTrueWater
    
  Polars are J/30-specific boat coefficients.

Inputs from Signal K:
  - environment.wind.speedTrue (m/s)
  - environment.wind.angleTrueWater (rad)

Outputs to Signal K:
  - performance.targetSpeed (m/s)

Also writes to InfluxDB bucket 'midnight_rider'.

J/30 Polars (knots, interpolated):
  TWS=4kts:   0°:2.0  30°:4.5  60°:5.5  90°:5.8  120°:5.2  150°:3.5  180°:0
  TWS=6kts:   0°:3.0  30°:6.5  60°:8.0  90°:8.5  120°:7.5  150°:5.0  180°:0
  TWS=8kts:   0°:4.0  30°:8.5  60°:10.5 90°:11.0 120°:10.0 150°:6.5  180°:0
  TWS=10kts:  0°:5.0  30°:10.0 60°:12.5 90°:13.0 120°:12.0 150°:8.0  180°:0
  TWS=12kts:  0°:5.8  30°:11.5 60°:14.0 90°:14.5 120°:13.5 150°:9.0  180°:0
  TWS=15kts:  0°:6.5  30°:13.0 60°:15.5 90°:16.0 120°:15.0 150°:10.0 180°:0
  TWS=20kts:  0°:7.5  30°:15.0 60°:17.0 90°:17.5 120°:16.5 150°:11.5 180°:0

Author: OC (Open Claw) — Midnight Rider Navigation
License: MIT
"""

import asyncio
import json
import math
import time
import os
import sys
from datetime import datetime
from typing import Optional, List, Tuple

import urllib.request
import urllib.error


# Configuration
SIGNALK_HTTP = os.getenv("SIGNALK_HTTP", "http://localhost:3000")
SIGNALK_WS = os.getenv("SIGNALK_WS", "ws://localhost:3000/signalk/v1/stream")

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")

# Calculation frequency: every 10 seconds
CALC_INTERVAL = 10.0

# J/30 Polars (knots): {tws: [(angle_deg, speed_kts), ...]}
J30_POLARS = {
    4: [(0, 2.0), (30, 4.5), (60, 5.5), (90, 5.8), (120, 5.2), (150, 3.5), (180, 0)],
    6: [(0, 3.0), (30, 6.5), (60, 8.0), (90, 8.5), (120, 7.5), (150, 5.0), (180, 0)],
    8: [(0, 4.0), (30, 8.5), (60, 10.5), (90, 11.0), (120, 10.0), (150, 6.5), (180, 0)],
    10: [(0, 5.0), (30, 10.0), (60, 12.5), (90, 13.0), (120, 12.0), (150, 8.0), (180, 0)],
    12: [(0, 5.8), (30, 11.5), (60, 14.0), (90, 14.5), (120, 13.5), (150, 9.0), (180, 0)],
    15: [(0, 6.5), (30, 13.0), (60, 15.5), (90, 16.0), (120, 15.0), (150, 10.0), (180, 0)],
    20: [(0, 7.5), (30, 15.0), (60, 17.0), (90, 17.5), (120, 16.5), (150, 11.5), (180, 0)],
}


# ─── Signal K API calls ───────────────────────────────────────────────────────

def get_signalk_value(path: str) -> Optional[float]:
    """Fetch a single value from Signal K REST API."""
    try:
        url = f"{SIGNALK_HTTP}/signalk/v1/api/vessels/self/{path}"
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('value')
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def get_wind_inputs() -> Tuple[Optional[float], Optional[float]]:
    """Fetch wind inputs from Signal K."""
    tws = get_signalk_value("environment/wind/speedTrue")
    twa = get_signalk_value("environment/wind/angleTrueWater")
    return tws, twa


# ─── Polar interpolation ──────────────────────────────────────────────────────

def interpolate_polar(tws_kts: float, twa_deg: float) -> Optional[float]:
    """
    Interpolate target speed from J/30 polars.
    
    Args:
        tws_kts: True Wind Speed (knots)
        twa_deg: True Wind Angle (degrees, 0-180)
    
    Returns:
        Target speed (knots), or None if out of range
    """
    # Find surrounding TWS values in polars
    tws_values = sorted(J30_POLARS.keys())
    
    if tws_kts < tws_values[0]:
        # Below minimum TWS
        tws_low = tws_low_idx = None
        tws_high = tws_values[0]
        tws_high_idx = 0
        alpha = 0.0
    elif tws_kts > tws_values[-1]:
        # Above maximum TWS
        tws_low = tws_values[-1]
        tws_low_idx = len(tws_values) - 1
        tws_high = tws_high_idx = None
        alpha = 1.0
    else:
        # Within range: find bracketing values
        for i in range(len(tws_values) - 1):
            if tws_values[i] <= tws_kts <= tws_values[i+1]:
                tws_low = tws_values[i]
                tws_low_idx = i
                tws_high = tws_values[i+1]
                tws_high_idx = i + 1
                alpha = (tws_kts - tws_low) / (tws_high - tws_low) if tws_high > tws_low else 0
                break
    
    # Clamp TWA to 0-180
    twa_norm = min(180, max(0, twa_deg))
    
    # Get speeds from low and high TWS rows
    speed_low = None
    speed_high = None
    
    if tws_low_idx is not None:
        polar_row = J30_POLARS[tws_low]
        # Interpolate within this row
        for i in range(len(polar_row) - 1):
            angle_low, speed_low_lo = polar_row[i]
            angle_high, speed_low_hi = polar_row[i+1]
            if angle_low <= twa_norm <= angle_high:
                beta = (twa_norm - angle_low) / (angle_high - angle_low) if angle_high > angle_low else 0
                speed_low = speed_low_lo + beta * (speed_low_hi - speed_low_lo)
                break
        else:
            # Use last value if beyond range
            speed_low = polar_row[-1][1]
    
    if tws_high_idx is not None:
        polar_row = J30_POLARS[tws_high]
        for i in range(len(polar_row) - 1):
            angle_low, speed_high_lo = polar_row[i]
            angle_high, speed_high_hi = polar_row[i+1]
            if angle_low <= twa_norm <= angle_high:
                beta = (twa_norm - angle_low) / (angle_high - angle_low) if angle_high > angle_low else 0
                speed_high = speed_high_lo + beta * (speed_high_hi - speed_high_lo)
                break
        else:
            speed_high = polar_row[-1][1]
    
    # Interpolate between TWS rows
    if speed_low is not None and speed_high is not None:
        return speed_low + alpha * (speed_high - speed_low)
    elif speed_low is not None:
        return speed_low
    elif speed_high is not None:
        return speed_high
    else:
        return None


# ─── InfluxDB ─────────────────────────────────────────────────────────────────

def write_to_influxdb(measurement: str, fields: dict, tags: dict = None) -> bool:
    """Write measurement to InfluxDB using line protocol."""
    if not INFLUX_TOKEN:
        print("⚠️  INFLUX_TOKEN not set, skipping InfluxDB write")
        return False
    
    if tags is None:
        tags = {}
    
    # Build line protocol
    line = measurement
    
    if tags:
        tag_str = ",".join(f"{k}={v}" for k, v in tags.items())
        line += f",{tag_str}"
    
    field_parts = []
    for k, v in fields.items():
        if isinstance(v, str):
            field_parts.append(f'{k}="{v}"')
        elif isinstance(v, bool):
            field_parts.append(f"{k}={str(v).lower()}")
        else:
            field_parts.append(f"{k}={v}")
    
    line += " " + ",".join(field_parts)
    
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=s"
    data = line.encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Token {INFLUX_TOKEN}")
    req.add_header("Content-Type", "text/plain")
    
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 204
    except urllib.error.URLError as e:
        print(f"⚠️  InfluxDB error: {e}")
        return False


# ─── Signal K Delta ───────────────────────────────────────────────────────────

async def send_signalk_delta(target_speed_kts: float) -> bool:
    """Inject target speed into Signal K via delta."""
    try:
        import websockets
    except ImportError:
        return False
    
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        target_speed_ms = target_speed_kts / 1.944  # Convert knots to m/s
        
        delta = {
            "context": "vessels.self",
            "updates": [{
                "source": {
                    "label": "midnight-rider-polars",
                    "type": "software"
                },
                "timestamp": timestamp,
                "values": [
                    {"path": "performance.targetSpeed", "value": target_speed_ms}
                ]
            }]
        }
        
        uri = f"{SIGNALK_WS}?subscribe=none"
        async with websockets.connect(uri, timeout=5) as websocket:
            await websocket.send(json.dumps(delta))
            print(f"  ↔️  Signal K: targetSpeed={target_speed_kts:.1f}kts ({target_speed_ms:.2f}m/s)")
            return True
    except Exception as e:
        print(f"⚠️  Signal K delta failed: {e}")
        return False


# ─── Main loop ────────────────────────────────────────────────────────────────

async def main():
    """Main calculation loop."""
    print("🎯 Target Speed Calculator — J/30 Polars")
    print(f"   Signal K: {SIGNALK_HTTP}")
    print(f"   InfluxDB: {INFLUX_URL} (bucket: {INFLUX_BUCKET})")
    print()
    
    iteration = 0
    
    while True:
        iteration += 1
        
        # Fetch wind inputs
        tws, twa_rad = get_wind_inputs()
        
        if tws is None or twa_rad is None:
            print(f"[{iteration}] ⚠️  Missing wind data: TWS={tws}, TWA={twa_rad}")
            await asyncio.sleep(CALC_INTERVAL)
            continue
        
        # Convert to knots and degrees
        tws_kts = tws * 1.944
        twa_deg = math.degrees(twa_rad)
        
        # Lookup target speed from polars
        target_speed_kts = interpolate_polar(tws_kts, twa_deg)
        
        if target_speed_kts is None:
            print(f"[{iteration}] ⚠️  Polar lookup failed: TWS={tws_kts:.1f}kts, TWA={twa_deg:.1f}°")
            await asyncio.sleep(CALC_INTERVAL)
            continue
        
        target_speed_ms = target_speed_kts / 1.944
        
        # Log
        print(f"[{iteration}] TWS={tws_kts:.1f}kts TWA={twa_deg:.1f}° → TargetSpeed={target_speed_kts:.1f}kts ({target_speed_ms:.2f}m/s)")
        
        # Write to InfluxDB
        write_to_influxdb(
            "performance.targetSpeed",
            {
                "value": target_speed_ms,
                "kts": target_speed_kts
            },
            {"source": "midnight-rider-polars", "boat": "J30"}
        )
        
        # Send to Signal K
        await send_signalk_delta(target_speed_kts)
        
        # Wait before next iteration
        await asyncio.sleep(CALC_INTERVAL)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Stopped")
        sys.exit(0)

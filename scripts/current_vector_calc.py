#!/usr/bin/env python3
"""
current_vector_calc.py — Current Vector Calculation

Midnight Rider Navigation — Signal K calculation → InfluxDB

Formula:
  Current = SOG_vector − STW_vector
  
  SOG_vector = (SOG × sin(COG), SOG × cos(COG))
  STW_vector = (STW × sin(HDG), STW × cos(HDG))
  
  Current_E = SOG_E − STW_E
  Current_N = SOG_N − STW_N
  
  drift [m/s] = √(Current_E² + Current_N²)
  set [rad] = atan2(Current_E, Current_N) % 2π

Inputs from Signal K:
  - navigation.speedOverGround (m/s)
  - navigation.courseOverGroundTrue (rad)
  - navigation.speedThroughWater (m/s)
  - navigation.headingTrue (rad)

Outputs to Signal K:
  - environment.current.drift (m/s)
  - environment.current.setTrue (rad)

Also writes to InfluxDB bucket 'midnight_rider'.

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
from typing import Optional, Tuple

import urllib.request
import urllib.error


# Configuration
SIGNALK_HTTP = os.getenv("SIGNALK_HTTP", "http://localhost:3000")
SIGNALK_WS = os.getenv("SIGNALK_WS", "ws://localhost:3000/signalk/v1/stream")

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")

# Calculation frequency: every 5 seconds
CALC_INTERVAL = 5.0


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


def get_all_inputs() -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Fetch all required inputs from Signal K."""
    sog = get_signalk_value("navigation/speedOverGround")
    cog = get_signalk_value("navigation/courseOverGroundTrue")
    stw = get_signalk_value("navigation/speedThroughWater")
    hdg = get_signalk_value("navigation/headingTrue")
    return sog, cog, stw, hdg


# ─── Calculation ──────────────────────────────────────────────────────────────

def compute_current_vector(sog: float, cog_rad: float, stw: float, hdg_rad: float) -> Tuple[float, float]:
    """
    Compute current drift and set from vectors.
    
    Args:
        sog: Speed Over Ground (m/s)
        cog_rad: Course Over Ground (radians)
        stw: Speed Through Water (m/s)
        hdg_rad: Heading True (radians)
    
    Returns:
        (drift [m/s], set [radians])
    """
    # Convert to east/north components
    sog_e = sog * math.sin(cog_rad)
    sog_n = sog * math.cos(cog_rad)
    
    stw_e = stw * math.sin(hdg_rad)
    stw_n = stw * math.cos(hdg_rad)
    
    # Current = SOG - STW
    cur_e = sog_e - stw_e
    cur_n = sog_n - stw_n
    
    # Drift magnitude
    drift = math.sqrt(cur_e**2 + cur_n**2)
    
    # Set direction (where current is going)
    set_rad = math.atan2(cur_e, cur_n) % (2 * math.pi)
    
    return drift, set_rad


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
    
    # Add tags
    if tags:
        tag_str = ",".join(f"{k}={v}" for k, v in tags.items())
        line += f",{tag_str}"
    
    # Add fields
    field_parts = []
    for k, v in fields.items():
        if isinstance(v, str):
            field_parts.append(f'{k}="{v}"')
        elif isinstance(v, bool):
            field_parts.append(f"{k}={str(v).lower()}")
        else:
            field_parts.append(f"{k}={v}")
    
    line += " " + ",".join(field_parts)
    
    # Send to InfluxDB
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


# ─── Signal K Delta (WebSocket injection) ──────────────────────────────────────

async def send_signalk_delta(drift: float, set_rad: float) -> bool:
    """
    Inject calculated current into Signal K via delta message.
    
    Delta format:
    {
      "context": "vessels.self",
      "updates": [{
        "source": {...},
        "timestamp": "...",
        "values": [
          {"path": "environment.current.drift", "value": ...},
          {"path": "environment.current.setTrue", "value": ...}
        ]
      }]
    }
    """
    try:
        import websockets
    except ImportError:
        print("⚠️  websockets module not installed, skipping Signal K delta")
        return False
    
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        delta = {
            "context": "vessels.self",
            "updates": [{
                "source": {
                    "label": "midnight-rider-current",
                    "type": "software"
                },
                "timestamp": timestamp,
                "values": [
                    {"path": "environment.current.drift", "value": drift},
                    {"path": "environment.current.setTrue", "value": set_rad}
                ]
            }]
        }
        
        uri = f"{SIGNALK_WS}?subscribe=none"
        async with websockets.connect(uri, timeout=5) as websocket:
            await websocket.send(json.dumps(delta))
            print(f"  ↔️  Signal K: current.drift={drift:.3f}m/s, current.set={math.degrees(set_rad):.1f}°")
            return True
    except Exception as e:
        print(f"⚠️  Signal K delta failed: {e}")
        return False


# ─── Main loop ────────────────────────────────────────────────────────────────

async def main():
    """Main calculation loop."""
    print("🌊 Current Vector Calculator — Midnight Rider")
    print(f"   Signal K: {SIGNALK_HTTP}")
    print(f"   InfluxDB: {INFLUX_URL} (bucket: {INFLUX_BUCKET})")
    print()
    
    iteration = 0
    
    while True:
        iteration += 1
        
        # Fetch inputs
        sog, cog, stw, hdg = get_all_inputs()
        
        # Check if all inputs available
        if None in (sog, cog, stw, hdg):
            print(f"[{iteration}] ⚠️  Missing inputs: SOG={sog}, COG={cog}, STW={stw}, HDG={hdg}")
            await asyncio.sleep(CALC_INTERVAL)
            continue
        
        # Compute current vector
        drift, set_rad = compute_current_vector(sog, cog, stw, hdg)
        set_deg = math.degrees(set_rad)
        
        # Log
        print(f"[{iteration}] SOG={sog:.2f}m/s({sog*1.944:.1f}kts) COG={math.degrees(cog):.1f}° " +
              f"STW={stw:.2f}m/s HDG={math.degrees(hdg):.1f}° " +
              f"→ DRIFT={drift:.3f}m/s({drift*1.944:.2f}kts) SET={set_deg:.1f}°")
        
        # Write to InfluxDB
        write_to_influxdb(
            "environment.current",
            {
                "drift": drift,
                "setTrue": set_rad,
                "setDeg": set_deg
            },
            {"source": "midnight-rider-calc"}
        )
        
        # Send to Signal K (async)
        await send_signalk_delta(drift, set_rad)
        
        # Wait before next iteration
        await asyncio.sleep(CALC_INTERVAL)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Stopped")
        sys.exit(0)

#!/usr/bin/env python3
"""
Midnight Rider — Start Line Geometry Worker
Reads pin/RC GPS from InfluxDB, boat GPS from Signal K.
Computes 8 geometry fields and writes back to InfluxDB @ 1Hz.
Run independently — does NOT require server.py modification.
"""
import os, sys, math, time
import json

try:
    import requests
except ImportError:
    print("ERROR: requests module required. Install: pip3 install requests")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")
SIGNALK_URL = os.getenv("SIGNALK_URL", "http://localhost:3000")
INTERVAL = float(os.getenv("WORKER_INTERVAL", "1.0"))

HEADERS_Q = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "application/vnd.flux"
}
HEADERS_W = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}

# ── Geometry functions ────────────────────────────────────────
def haversine_m(lat1, lon1, lat2, lon2):
    """Distance in meters (Haversine formula)."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(max(0.0, min(1.0, a))))

def bearing_deg(lat1, lon1, lat2, lon2):
    """Bearing in degrees from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1)*math.sin(p2) - math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def signed_distance_to_line(boat_lat, boat_lon, pin_lat, pin_lon, rc_lat, rc_lon):
    """Perpendicular signed distance from boat to start line (pin→RC)."""
    R = 6371000.0
    cos_lat = math.cos(math.radians(pin_lat))
    bx = R * math.radians(boat_lon - pin_lon) * cos_lat
    by = R * math.radians(boat_lat - pin_lat)
    rx = R * math.radians(rc_lon - pin_lon) * cos_lat
    ry = R * math.radians(rc_lat - pin_lat)
    line_len = math.sqrt(rx**2 + ry**2)
    if line_len < 0.5:
        return 0.0
    return (rx * by - ry * bx) / line_len

def compute_geometry(boat_lat, boat_lon, pin_lat, pin_lon, rc_lat, rc_lon, twd_deg=None):
    """Compute all 8 start line geometry fields."""
    pin_dist = haversine_m(boat_lat, boat_lon, pin_lat, pin_lon)
    rc_dist = haversine_m(boat_lat, boat_lon, rc_lat, rc_lon)
    line_len = haversine_m(pin_lat, pin_lon, rc_lat, rc_lon)
    pin_brg = bearing_deg(boat_lat, boat_lon, pin_lat, pin_lon)
    rc_brg = bearing_deg(boat_lat, boat_lon, rc_lat, rc_lon)
    
    sd = signed_distance_to_line(boat_lat, boat_lon, pin_lat, pin_lon, rc_lat, rc_lon)
    dist = abs(sd)
    
    if sd > 15:
        side = "CLEAR"
    elif sd >= -5:
        side = "CLOSE"
    else:
        side = "OCS"
    
    bias = None
    if twd_deg is not None and line_len > 0.5:
        R = 6371000.0
        cos_lat = math.cos(math.radians(pin_lat))
        rx = R * math.radians(rc_lon - pin_lon) * cos_lat
        ry = R * math.radians(rc_lat - pin_lat)
        line_dir = (math.degrees(math.atan2(rx, ry)) + 360) % 360
        perp = (line_dir + 90) % 360
        bias = round(((perp - twd_deg + 180) % 360) - 180, 1)
    
    return {
        "distance_to_line_m": round(dist, 1),
        "line_side": side,
        "pin_buoy_bearing_deg": round(pin_brg, 1),
        "pin_buoy_dist_m": round(pin_dist, 1),
        "pin_rc_bearing_deg": round(rc_brg, 1),
        "pin_rc_dist_m": round(rc_dist, 1),
        "start_line_length_m": round(line_len, 1),
        "line_bias_deg": bias,
    }

# ── InfluxDB helpers ──────────────────────────────────────────
def influx_query(flux):
    """Execute Flux query, return list of {_field, _value} dicts."""
    try:
        r = requests.post(
            f"{INFLUX_URL}/api/v2/query?org={INFLUX_ORG}",
            headers=HEADERS_Q, data=flux, timeout=3
        )
        if r.status_code == 200:
            rows = []
            for line in r.text.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) >= 7:
                    rows.append({
                        "_field": parts[5].strip('"'),
                        "_value": parts[6].strip('"')
                    })
            return rows
    except Exception as e:
        pass
    return []

def influx_write(fields):
    """Write computed fields as line protocol to regatta.start_line."""
    parts = []
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, str):
            parts.append(f'{k}="{v}"')
        else:
            parts.append(f'{k}={v}')
    
    if not parts:
        return False
    
    line = "regatta.start_line " + ",".join(parts)
    try:
        r = requests.post(
            f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns",
            headers=HEADERS_W, data=line.encode(), timeout=3
        )
        return r.status_code in (200, 204)
    except Exception as e:
        return False

# ── Signal K helpers ──────────────────────────────────────────
def sk_get(path):
    """Read value from Signal K REST API."""
    try:
        r = requests.get(
            f"{SIGNALK_URL}/signalk/v1/api/vessels/self/{path}/value",
            timeout=2
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def get_boat_position():
    """Read boat GPS from Signal K."""
    pos = sk_get("navigation/position")
    if pos and isinstance(pos, dict):
        lat = pos.get("latitude") or pos.get("lat")
        lon = pos.get("longitude") or pos.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    return None, None

def get_twd_deg():
    """Read true wind direction from Signal K (convert radians to degrees)."""
    val = sk_get("environment/wind/directionTrue")
    if val is not None:
        try:
            return (math.degrees(float(val)) + 360) % 360
        except Exception:
            pass
    return None

# ── Read pin/RC from InfluxDB ─────────────────────────────────
PIN_RC_STATE = {"pin_lat": None, "pin_lon": None, "rc_lat": None, "rc_lon": None}
DISCOVERY_DONE = False

def discover_and_read_pin_rc():
    """Query InfluxDB for latest pin/RC coords using mark tag."""
    global PIN_RC_STATE, DISCOVERY_DONE
    
    # Query pin marker (mark=pin tag)
    flux_pin = (
        'from(bucket:"midnight_rider")\n'
        ' |> range(start: -24h)\n'
        ' |> filter(fn: (r) => r._measurement == "regatta.start_line" and r.mark == "pin")\n'
        ' |> filter(fn: (r) => r._field == "lat" or r._field == "lon")\n'
        ' |> last()'
    )
    
    # Query rc marker (mark=rc tag)
    flux_rc = (
        'from(bucket:"midnight_rider")\n'
        ' |> range(start: -24h)\n'
        ' |> filter(fn: (r) => r._measurement == "regatta.start_line" and r.mark == "boat")\n'
        ' |> filter(fn: (r) => r._field == "lat" or r._field == "lon")\n'
        ' |> last()'
    )
    
    pin_rows = influx_query(flux_pin)
    rc_rows = influx_query(flux_rc)
    
    if not DISCOVERY_DONE:
        if pin_rows:
            print("[worker] ✅ Found PIN marker in InfluxDB")
        if rc_rows:
            print("[worker] ✅ Found RC marker in InfluxDB")
        DISCOVERY_DONE = True
    
    # Parse pin coordinates
    for row in pin_rows:
        try:
            if row["_field"] == "lat":
                PIN_RC_STATE["pin_lat"] = float(row["_value"])
            elif row["_field"] == "lon":
                PIN_RC_STATE["pin_lon"] = float(row["_value"])
        except Exception:
            pass
    
    # Parse rc/boat coordinates (server uses mark=boat for committee boat)
    for row in rc_rows:
        try:
            if row["_field"] == "lat":
                PIN_RC_STATE["rc_lat"] = float(row["_value"])
            elif row["_field"] == "lon":
                PIN_RC_STATE["rc_lon"] = float(row["_value"])
        except Exception:
            pass
    
    return PIN_RC_STATE["pin_lat"], PIN_RC_STATE["pin_lon"], PIN_RC_STATE["rc_lat"], PIN_RC_STATE["rc_lon"]

# ── Main loop ─────────────────────────────────────────────────
def main():
    print(f"[worker] Midnight Rider — Start Line Geometry Worker")
    print(f"[worker] InfluxDB: {INFLUX_URL} | Signal K: {SIGNALK_URL}")
    print(f"[worker] Update rate: {INTERVAL}s")
    print(f"[worker] Waiting for pin/RC markers and boat GPS...")
    print(f"[worker] (Mark pin + RC in regatta UI at http://localhost:5000/)")
    
    iteration = 0
    last_print = 0
    
    while True:
        try:
            pin_lat, pin_lon, rc_lat, rc_lon = discover_and_read_pin_rc()
            
            if all(v is not None for v in [pin_lat, pin_lon, rc_lat, rc_lon]):
                boat_lat, boat_lon = get_boat_position()
                if boat_lat is not None and boat_lon is not None:
                    twd = get_twd_deg()
                    fields = compute_geometry(
                        boat_lat, boat_lon,
                        pin_lat, pin_lon,
                        rc_lat, rc_lon,
                        twd_deg=twd
                    )
                    
                    if influx_write(fields):
                        now = time.time()
                        if now - last_print > 10:  # Log every 10s
                            print(
                                f"[worker] ✅ {fields['line_side']:5s} | "
                                f"dist={fields['distance_to_line_m']:6.1f}m | "
                                f"pin={fields['pin_buoy_dist_m']:6.1f}m | "
                                f"rc={fields['pin_rc_dist_m']:6.1f}m | "
                                f"bias={fields['line_bias_deg'] if fields['line_bias_deg'] else '-':>5}°"
                            )
                            last_print = now
                    else:
                        if iteration % 30 == 0:
                            print("[worker] ⚠️ InfluxDB write failed")
                else:
                    if iteration % 30 == 0:
                        print("[worker] ⏳ Waiting for boat GPS from Signal K...")
            else:
                if iteration % 30 == 0:
                    print("[worker] ⏳ Waiting for pin/RC markers to be set (or no GPS yet)...")
        
        except Exception as e:
            print(f"[worker] Error: {e}")
        
        iteration += 1
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()

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
    """
    Perpendicular signed distance from boat to start line (pin→RC).
    Positive = boat is behind line (safe/CLEAR side).
    Negative = boat is over line (OCS).
    """
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
PIN_RC_FIELD_MAP = {}  # populated at startup

def discover_pin_rc_fields():
    """Query InfluxDB to find which field names store pin/RC coordinates."""
    global PIN_RC_FIELD_MAP
    
    # Query all field names in regatta.start_line
    rows = influx_query(
        'from(bucket:"midnight_rider")\n'
        ' |> range(start: -24h)\n'
        ' |> filter(fn: (r) => r._measurement == "regatta.start_line")\n'
        ' |> keep(columns: ["_field"])\n'
        ' |> distinct(column: "_field")'
    )
    
    fields = [r["_field"] for r in rows]
    print(f"[worker] regatta.start_line fields: {fields}")
    
    # Try common naming patterns
    patterns = {
        "pin_lat": ["pin_lat", "pin_latitude", "lat_pin", "pinLat"],
        "pin_lon": ["pin_lon", "pin_longitude", "lon_pin", "pinLon"],
        "rc_lat": ["rc_lat", "rc_latitude", "lat_rc", "rcLat", "committee_lat", "boat_lat"],
        "rc_lon": ["rc_lon", "rc_longitude", "lon_rc", "rcLon", "committee_lon", "boat_lon"],
    }
    
    for key, candidates in patterns.items():
        for c in candidates:
            if c in fields:
                PIN_RC_FIELD_MAP[key] = c
                print(f"[worker]   {key} → {c}")
                break
    
    return len(PIN_RC_FIELD_MAP) == 4

def get_start_line_coords():
    """Read latest pin/RC coords from InfluxDB."""
    if not PIN_RC_FIELD_MAP or len(PIN_RC_FIELD_MAP) < 4:
        return None, None, None, None
    
    flux = (
        'from(bucket:"midnight_rider")\n'
        ' |> range(start: -24h)\n'
        ' |> filter(fn: (r) => r._measurement == "regatta.start_line")\n'
        ' |> filter(fn: (r) => '
        f'r._field == "{PIN_RC_FIELD_MAP.get("pin_lat", "")}" or '
        f'r._field == "{PIN_RC_FIELD_MAP.get("pin_lon", "")}" or '
        f'r._field == "{PIN_RC_FIELD_MAP.get("rc_lat", "")}" or '
        f'r._field == "{PIN_RC_FIELD_MAP.get("rc_lon", "")}")\n'
        ' |> last()'
    )
    
    rows = influx_query(flux)
    vals = {}
    for row in rows:
        field = row["_field"]
        try:
            vals[field] = float(row["_value"])
        except Exception:
            pass
    
    pin_lat = vals.get(PIN_RC_FIELD_MAP.get("pin_lat"))
    pin_lon = vals.get(PIN_RC_FIELD_MAP.get("pin_lon"))
    rc_lat = vals.get(PIN_RC_FIELD_MAP.get("rc_lat"))
    rc_lon = vals.get(PIN_RC_FIELD_MAP.get("rc_lon"))
    
    return pin_lat, pin_lon, rc_lat, rc_lon

# ── Main loop ─────────────────────────────────────────────────
def main():
    print(f"[worker] Midnight Rider — Start Line Geometry Worker")
    print(f"[worker] InfluxDB: {INFLUX_URL} | Signal K: {SIGNALK_URL}")
    print(f"[worker] Update rate: {INTERVAL}s")
    print(f"[worker] Discovering pin/RC coordinate field names...")
    
    # Discover coordinate field names
    for attempt in range(10):
        if discover_pin_rc_fields():
            print(f"[worker] ✅ Field mapping complete")
            break
        print(f"[worker] Retry {attempt+1}/10 in 5s...")
        time.sleep(5)
    
    if not PIN_RC_FIELD_MAP or len(PIN_RC_FIELD_MAP) < 4:
        print("[worker] ⚠️ Could not auto-discover all coordinate fields")
        print("[worker] Mark pin and RC boat positions in regatta interface first")
        print("[worker] Then restart this worker")
    
    iteration = 0
    while True:
        try:
            pin_lat, pin_lon, rc_lat, rc_lon = get_start_line_coords()
            
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
                        if iteration % 10 == 0:  # log every 10s
                            print(
                                f"[worker] ✅ {fields['line_side']:5s} | "
                                f"dist={fields['distance_to_line_m']:6.1f}m | "
                                f"pin={fields['pin_buoy_dist_m']:6.1f}m | "
                                f"rc={fields['pin_rc_dist_m']:6.1f}m | "
                                f"bias={fields['line_bias_deg'] if fields['line_bias_deg'] else '-':>5}°"
                            )
                else:
                    if iteration % 30 == 0:
                        print("[worker] ⚠️ No boat GPS from Signal K")
            else:
                if iteration % 30 == 0:
                    print("[worker] ⏳ Waiting for pin/RC positions to be marked")
                # Retry field discovery if not found
                if len(PIN_RC_FIELD_MAP) < 4:
                    discover_pin_rc_fields()
        
        except Exception as e:
            print(f"[worker] Error: {e}")
        
        iteration += 1
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()

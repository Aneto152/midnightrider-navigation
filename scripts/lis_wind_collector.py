#!/usr/bin/env python3
"""
lis_wind_collector.py — LIS Wind Stations → InfluxDB
Fetches ASOS + NOAA buoy data every 15 min, stores in knots to InfluxDB.
All sources converted to knots for unified analysis.

Sources:
  • ASOS (api.weather.gov): wind in m/s → convert ×1.94384 to knots
  • NOAA buoys (tidesandcurrents): units=english → knots (native)
  • NDBC buoys (ndbc.noaa.gov): wind in knots (native)
"""

import json
import urllib.request
import datetime
import os
import time
import sys

# Configuration
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")

# All LIS wind stations (9 total: 5 ASOS + 4 NOAA/NDBC)
STATIONS = [
    # ASOS (api.weather.gov) — wind in m/s, convert ×1.94384 to knots
    {"id": "KBDR", "name": "Bridgeport CT", "lat": 41.163, "lon": -73.126, "type": "ASOS", "zone": "CT-Nord"},
    {"id": "KHVN", "name": "New Haven CT", "lat": 41.264, "lon": -72.887, "type": "ASOS", "zone": "CT-Nord"},
    {"id": "KGON", "name": "New London CT", "lat": 41.330, "lon": -72.045, "type": "ASOS", "zone": "CT-NordEst"},
    {"id": "KOXC", "name": "Oxford CT", "lat": 41.479, "lon": -73.135, "type": "ASOS", "zone": "CT-Intérieur"},
    {"id": "KPVD", "name": "Providence RI", "lat": 41.723, "lon": -71.433, "type": "ASOS", "zone": "RI"},
    
    # NOAA buoys (tidesandcurrents API) — units=english → knots native
    {"id": "NWPR1", "name": "Newport RI", "lat": 41.504, "lon": -71.326, "type": "NOAA", "zone": "RI"},
    {"id": "PTCR1", "name": "Pt Judith RI", "lat": 41.364, "lon": -71.483, "type": "NOAA", "zone": "RI"},
    
    # NDBC buoys (ndbc.noaa.gov realtime) — knots native
    {"id": "44017", "name": "Montauk NY", "lat": 40.693, "lon": -72.048, "type": "NDBC", "zone": "LI-Est"},
    {"id": "44022", "name": "Long Island", "lat": 40.727, "lon": -72.649, "type": "NDBC", "zone": "LI-Centre"},
]

def write_influxdb(measurement, tags, fields, timestamp_ns=None):
    """Write data to InfluxDB using line protocol."""
    if not INFLUX_TOKEN:
        print(f"⚠️  No INFLUX_TOKEN — skipping write")
        return False
    
    tag_str = ",".join(f"{k}={v.replace(' ', '_')}" for k, v in tags.items())
    field_parts = []
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, str):
            field_parts.append(f'{k}="{v}"')
        else:
            field_parts.append(f'{k}={v}')
    
    if not field_parts:
        return False
    
    field_str = ",".join(field_parts)
    line = f"{measurement},{tag_str} {field_str}"
    if timestamp_ns:
        line += f" {timestamp_ns}"
    
    data = line.encode()
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
    
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Token {INFLUX_TOKEN}")
        req.add_header("Content-Type", "text/plain")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"❌ InfluxDB error: {e}")
        return False

def fetch_asos(station_id):
    """Fetch ASOS via api.weather.gov — wind in m/s, convert to knots."""
    url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "midnight-rider/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
            props = d.get("properties", {})
            
            # Extract values
            wspd_ms = props.get("windSpeed", {}).get("value")
            wdir = props.get("windDirection", {}).get("value")
            gust_ms = props.get("windGust", {}).get("value")
            
            return {
                "speed_kts": round(wspd_ms * 1.94384, 1) if wspd_ms is not None else None,
                "dir_deg": round(wdir, 0) if wdir is not None else None,
                "gust_kts": round(gust_ms * 1.94384, 1) if gust_ms is not None else None,
            }
    except Exception as e:
        print(f"  ASOS {station_id} error: {e}")
        return None

def fetch_noaa_buoy(station_id):
    """Fetch NOAA tide/current station — use units=english → knots."""
    url = (f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
           f"?station={station_id}&product=wind&time_zone=gmt"
           f"&units=english&format=json&date=latest")
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.loads(r.read())
            data = (d.get("data") or [{}])[-1]
            
            return {
                "speed_kts": float(data.get("s", 0)) if data.get("s") else None,
                "dir_deg": float(data.get("d", 0)) if data.get("d") else None,
                "gust_kts": float(data.get("g", 0)) if data.get("g") else None,
            }
    except Exception as e:
        print(f"  NOAA {station_id} error: {e}")
        return None

def fetch_ndbc(station_id):
    """Fetch NDBC buoy realtime data — wind already in knots."""
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            lines = r.read().decode().splitlines()
            if len(lines) < 3:
                return None
            
            # Parse header and data
            headers = lines[0].split()
            values = lines[2].split()  # most recent observation
            data = dict(zip(headers, values))
            
            # Extract fields (handling MM = missing)
            def val(v):
                return None if v == "MM" else float(v)
            
            wspd = val(data.get("WSPD"))  # Wind speed in knots
            wdir = val(data.get("WDIR"))   # Wind direction in degrees
            gust = val(data.get("GST"))    # Gust in knots
            
            return {
                "speed_kts": wspd,
                "dir_deg": wdir,
                "gust_kts": gust,
            }
    except Exception as e:
        print(f"  NDBC {station_id} error: {e}")
        return None

def collect_once():
    """Fetch all stations once, write to InfluxDB."""
    ts = int(datetime.datetime.utcnow().timestamp() * 1e9)
    collected = 0
    
    for stn in STATIONS:
        # Fetch data based on type
        if stn["type"] == "ASOS":
            data = fetch_asos(stn["id"])
        elif stn["type"] == "NOAA":
            data = fetch_noaa_buoy(stn["id"])
        else:  # NDBC
            data = fetch_ndbc(stn["id"])
        
        if not data or data.get("speed_kts") is None:
            print(f"⚠️  {stn['id']:8} — no data")
            continue
        
        # Prepare tags and fields
        tags = {
            "station_id": stn["id"],
            "station_name": stn["name"],
            "type": stn["type"],
            "zone": stn["zone"],
        }
        
        fields = {
            "speed_kts": data["speed_kts"],
            "dir_deg": data.get("dir_deg"),
            "gust_kts": data.get("gust_kts"),
            "lat": stn["lat"],
            "lon": stn["lon"],
        }
        
        # Write to InfluxDB
        if write_influxdb("lis_wind", tags, fields, ts):
            print(f"✅ {stn['id']:8} {data['speed_kts']:5.1f}kts @ {data.get('dir_deg', '?'):>3.0f}°")
            collected += 1
        else:
            print(f"❌ {stn['id']:8} — write failed")
    
    return collected

def main():
    """Main entry point."""
    print(f"[LIS Wind] Collector started — {len(STATIONS)} stations")
    
    while True:
        try:
            count = collect_once()
            print(f"[LIS Wind] Collected {count}/{len(STATIONS)} stations ✅\n")
        except KeyboardInterrupt:
            print("[LIS Wind] Stopped")
            sys.exit(0)
        except Exception as e:
            print(f"[LIS Wind] Error: {e}\n")
        
        # Wait 15 minutes before next collection
        time.sleep(900)

if __name__ == "__main__":
    main()

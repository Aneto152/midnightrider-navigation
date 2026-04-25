#!/usr/bin/env python3
"""
MidnightRider — Collecteur météo LIS
Collecte les données NDBC + ASOS toutes les 5 min
Stockage dans InfluxDB bucket "weather_lis"
Démarrage/arrêt via API REST : POST /api/weather/start|stop
"""

import threading
import time
import urllib.request
import json
import os
import sys

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN', '')
INFLUX_ORG = "MidnightRider"
BUCKET = "weather_lis"
INTERVAL = 300  # 5 minutes

# Stations à surveiller
STATIONS = [
    # Bouées marines NDBC
    {"id": "NWPR1",  "name": "Newport RI",          "type": "ndbc", "zone": "EST"},
    {"id": "PTCR1",  "name": "Pt Judith RI",         "type": "ndbc", "zone": "EST"},
    {"id": "44025",  "name": "Offshore SE LI",        "type": "ndbc", "zone": "SUD"},
    {"id": "44017",  "name": "Montauk",               "type": "ndbc", "zone": "EST_LI"},
    {"id": "44022",  "name": "Block Island",          "type": "ndbc", "zone": "EST"},
    # Stations ASOS côté CT
    {"id": "KBDR",   "name": "Bridgeport CT",         "type": "asos", "zone": "CT"},
    {"id": "KHVN",   "name": "New Haven CT",          "type": "asos", "zone": "CT"},
    {"id": "KGON",   "name": "New London CT",         "type": "asos", "zone": "CT_EST"},
    # Stations ASOS côté LI
    {"id": "KISP",   "name": "Islip LI",              "type": "asos", "zone": "LI"},
    {"id": "KFOK",   "name": "Westhampton LI",        "type": "asos", "zone": "LI_EST"},
    {"id": "KJFK",   "name": "JFK NY",                "type": "asos", "zone": "LI_OUEST"},
    {"id": "KLGA",   "name": "LaGuardia NY",          "type": "asos", "zone": "LI_OUEST"},
    # Rhode Island
    {"id": "KPVD",   "name": "Providence RI",         "type": "asos", "zone": "EST"},
]

running = False
collector_thread = None

def write_influx(measurement, tags, fields, timestamp_ns=None):
    tag_str = ",".join(f"{k}={v.replace(' ','_')}" for k, v in tags.items())
    field_parts = []
    for k, v in fields.items():
        if v is None: continue
        if isinstance(v, str):
            field_parts.append(f'{k}="{v}"')
        else:
            field_parts.append(f'{k}={v}')
    if not field_parts: return False
    field_str = ",".join(field_parts)
    line = f"{measurement},{tag_str} {field_str}"
    if timestamp_ns:
        line += f" {timestamp_ns}"
    data = line.encode()
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={BUCKET}&precision=ns"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Token {INFLUX_TOKEN}")
    req.add_header("Content-Type", "text/plain")
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"[InfluxDB error] {e}", flush=True)
        return False

def fetch_ndbc(station_id):
    try:
        url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
        req = urllib.request.Request(url, headers={"User-Agent": "MidnightRider/1.0"})
        res = urllib.request.urlopen(req, timeout=10)
        lines = [l for l in res.read().decode().splitlines() if not l.startswith('#') and l.strip()]
        if not lines: return None
        p = lines[0].split()
        def val(v): return None if v == 'MM' else float(v)
        return {
            "wind_dir": val(p[5]),
            "wind_speed": val(p[6]),
            "wind_gust": val(p[7]),
            "wave_height": val(p[8]),   # WVHT m
            "wave_period": val(p[9]),   # DPD sec
            "wave_dir": val(p[11]) if len(p) > 11 else None,  # MWD deg
            "pressure": val(p[12]),
            "air_temp": val(p[13]),
            "water_temp": val(p[14]) if len(p) > 14 else None,
        }
    except Exception as e:
        print(f"[NDBC {station_id}] {e}", flush=True)
        return None

def fetch_asos(station_id):
    try:
        url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
        req = urllib.request.Request(url, headers={
            "User-Agent": "MidnightRider/1.0 (nav@midnightrider.net)",
            "Accept": "application/geo+json"
        })
        res = urllib.request.urlopen(req, timeout=10)
        raw = json.loads(res.read())
        p = raw.get("properties", {})
        def gv(field):
            v = p.get(field, {})
            return v.get("value") if isinstance(v, dict) else None
        pres = gv("barometricPressure")
        return {
            "wind_dir": gv("windDirection"),
            "wind_speed": gv("windSpeed"),
            "wind_gust": gv("windGust"),
            "pressure": pres / 100 if pres else None,  # Pa → hPa
            "air_temp": gv("temperature"),
            "water_temp": None,
        }
    except Exception as e:
        print(f"[ASOS {station_id}] {e}", flush=True)
        return None

def ensure_bucket():
    """Créer le bucket weather_lis s'il n'existe pas"""
    try:
        # Vérifier si le bucket existe
        req = urllib.request.Request(
            f"{INFLUX_URL}/api/v2/buckets?org={INFLUX_ORG}",
            headers={"Authorization": f"Token {INFLUX_TOKEN}"}
        )
        res = urllib.request.urlopen(req, timeout=5)
        buckets = json.loads(res.read())
        existing = [b["name"] for b in buckets.get("buckets", [])]
        if BUCKET in existing:
            return True
        # Créer le bucket
        org_req = urllib.request.Request(
            f"{INFLUX_URL}/api/v2/orgs",
            headers={"Authorization": f"Token {INFLUX_TOKEN}"}
        )
        org_res = urllib.request.urlopen(org_req, timeout=5)
        orgs = json.loads(org_res.read())
        org_id = orgs["orgs"][0]["id"]
        payload = json.dumps({
            "name": BUCKET,
            "orgID": org_id,
            "retentionRules": [{"type": "expire", "everySeconds": 0}]  # rétention illimitée
        }).encode()
        create_req = urllib.request.Request(
            f"{INFLUX_URL}/api/v2/buckets",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Token {INFLUX_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        urllib.request.urlopen(create_req, timeout=5)
        print(f"[Weather] Bucket '{BUCKET}' créé", flush=True)
        return True
    except Exception as e:
        print(f"[Weather] Bucket error: {e}", flush=True)
        return False

def collect_once():
    ts = time.time_ns()
    collected = 0
    for stn in STATIONS:
        if stn["type"] == "ndbc":
            data = fetch_ndbc(stn["id"])
        else:
            data = fetch_asos(stn["id"])
        if not data: continue
        tags = {
            "station_id": stn["id"],
            "station_name": stn["name"],
            "type": stn["type"],
            "zone": stn["zone"]
        }
        fields = {}
        if data["wind_dir"] is not None:
            fields["wind_dir"] = data["wind_dir"]
        if data["wind_speed"] is not None:
            fields["wind_speed_ms"] = data["wind_speed"]
            fields["wind_speed_kts"] = round(data["wind_speed"] * 1.94384, 2)
        if data["wind_gust"] is not None:
            fields["wind_gust_ms"] = data["wind_gust"]
            fields["wind_gust_kts"] = round(data["wind_gust"] * 1.94384, 2)
        if data["pressure"] is not None:
            fields["pressure_hpa"] = data["pressure"]
        if data["air_temp"] is not None:
            fields["air_temp_c"] = data["air_temp"]
        if data["water_temp"] is not None:
            fields["water_temp_c"] = data["water_temp"]
        if data.get("wave_height") is not None:
            fields["wave_height_m"] = data["wave_height"]
        if data.get("wave_period") is not None:
            fields["wave_period_s"] = data["wave_period"]
        if data.get("wave_dir") is not None:
            fields["wave_dir"] = data["wave_dir"]
        if write_influx("weather.station", tags, fields, ts):
            collected += 1
        time.sleep(0.5)  # éviter de spammer les APIs
    print(f"[Weather] Collecte: {collected}/{len(STATIONS)} stations OK", flush=True)
    return collected

def collector_loop():
    global running
    print("[Weather] Collecteur démarré", flush=True)
    ensure_bucket()
    while running:
        collect_once()
        # Attendre INTERVAL secondes en vérifiant l'arrêt
        for _ in range(INTERVAL):
            if not running: break
            time.sleep(1)
    print("[Weather] Collecteur arrêté", flush=True)

def start():
    global running, collector_thread
    if running:
        return {"ok": False, "msg": "déjà en cours"}
    running = True
    collector_thread = threading.Thread(target=collector_loop, daemon=True)
    collector_thread.start()
    return {"ok": True, "msg": "collecteur démarré"}

def stop():
    global running
    running = False
    return {"ok": True, "msg": "collecteur arrêté"}

def status():
    return {"running": running, "stations": len(STATIONS), "interval_s": INTERVAL, "bucket": BUCKET}

# Mode standalone
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        ensure_bucket()
        collect_once()
    else:
        running = True
        collector_loop()

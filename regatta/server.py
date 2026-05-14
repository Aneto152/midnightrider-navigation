#!/usr/bin/env python3
"""Regatta interface server — MidnightRider"""

from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import json, time, urllib.parse, urllib.request, os, math
import weather_collector

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN') or os.getenv('INFLUXDB_TOKEN', '')
INFLUX_ORG = "MidnightRider"
INFLUX_BUCKET = "midnight_rider"
SIGNALK_URL = "http://localhost:3000"

# Cache vent (TTL 5 min)
wind_cache = {}
WIND_TTL = 300

# Start line cache (pin and boat coordinates)
start_line_cache = {"pin": None, "boat": None}

def write_influx(measurement, fields, tags={}):
    tag_str = ",".join(f"{k}={v}" for k,v in tags.items())
    field_str = ",".join(f'{k}="{v}"' if isinstance(v,str) else f"{k}={v}" for k,v in fields.items())
    line = f"{measurement}"
    if tag_str: line += f",{tag_str}"
    line += f" {field_str}"
    data = line.encode()
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=s"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Token {INFLUX_TOKEN}")
    req.add_header("Content-Type", "text/plain")
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception as e:
        print(f"InfluxDB error: {e}")
        return False

def get_signalk(path):
    try:
        url = f"{SIGNALK_URL}/signalk/v1/api/{path}"
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req, timeout=2)
        return json.loads(res.read())
    except:
        return {}


def put_signalk(path, value):
    """Write a value to Signal K via REST PUT."""
    try:
        url = f"{SIGNALK_URL}/signalk/v1/api/vessels/self/{path.replace('.', '/')}"
        data = json.dumps({"value": value}).encode()
        req = urllib.request.Request(url, data=data, method="PUT")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception as e:
        print(f"Signal K PUT {path}: {e}")
        return False

def load_start_line_from_signalk():
    """On startup: restore start line from Signal K datastore."""
    global start_line_cache
    for point, sk_path in [("pin", "racing/startLinePrt"),
                           ("boat", "racing/startLineStb")]:
        try:
            data = get_signalk(f"vessels/self/{sk_path}")
            if data and data.get("value"):
                v = data["value"]
                if v.get("latitude") and v.get("longitude"):
                    start_line_cache[point] = {
                        "lat": v["latitude"], "lon": v["longitude"]}
                    print(f"Restored {point} from Signal K: {v}")
        except Exception as e:
            print(f"Could not restore {point} from Signal K: {e}")

def get_navigation():
    sog_data = get_signalk("vessels/self/navigation/speedOverGround")
    cog_data = get_signalk("vessels/self/navigation/courseOverGroundTrue")
    return {
        "sog": sog_data.get("value", 0) * 1.94384 if sog_data.get("value") else 0,
        "cog": round((cog_data.get("value", 0) or 0) * 57.2958, 1)
    }

def get_ais_targets(radius_nm=10):
    try:
        # Fetch boat position
        race_data = get_race_data()
        boat_lat = race_data.get('gps_lat')
        boat_lon = race_data.get('gps_lon')
        
        data = get_signalk("vessels")
        targets = []
        self_id = None
        # Trouver l'ID de MidnightRider
        for k in data.keys():
            v = data[k]
            if isinstance(v, dict) and v.get("self"):
                self_id = k
                break
        for mmsi, vessel in data.items():
            if not isinstance(vessel, dict): continue
            if mmsi == self_id or mmsi == "self": continue
            nav = vessel.get("navigation", {})
            pos = nav.get("position", {}).get("value", {})
            if not pos or not pos.get("latitude"): continue
            # Filtrer voiliers uniquement
            vessel_type = vessel.get("design", {}).get("aisShipType", {}).get("value", {}).get("id", 0)
            if vessel_type and (vessel_type < 36 or vessel_type > 39) and vessel_type != 0:
                continue  # pas un voilier
            name = vessel.get("name", mmsi)
            if isinstance(name, dict): name = name.get("value", mmsi)
            sog = nav.get("speedOverGround", {}).get("value", 0) or 0
            cog = nav.get("courseOverGroundTrue", {}).get("value", 0) or 0
            targets.append({
                "mmsi": mmsi,
                "name": str(name)[:20],
                "lat": pos["latitude"],
                "lon": pos["longitude"],
                "sog": round(sog * 1.94384, 2),
                "cog": round(cog * 57.2958, 1)
            })
        
        # Apply radius filter
        if boat_lat and boat_lon:
            targets = [t for t in targets
                      if haversine_m({"lat": boat_lat, "lon": boat_lon}, {"lat": t['lat'], "lon": t['lon']}) <= radius_nm * 1852]
        
        return targets
    except Exception as e:
        print(f"AIS error: {e}")
        return []

def get_gps_position():
    try:
        url = f"{SIGNALK_URL}/signalk/v1/api/vessels/self/navigation/position"
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req, timeout=2)
        data = json.loads(res.read())
        return data.get("value", {})
    except:
        return {}

def fetch_ndbc(station_id):
    """Fetch NDBC buoy data from realtime2 text file"""
    key = f"ndbc_{station_id}"
    if key in wind_cache and time.time() - wind_cache[key]['ts'] < WIND_TTL:
        return wind_cache[key]['data']
    try:
        url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
        req = urllib.request.Request(url, headers={"User-Agent": "MidnightRider/1.0"})
        res = urllib.request.urlopen(req, timeout=10)
        lines = res.read().decode().splitlines()
        # Skip header lines (start with #)
        data_lines = [l for l in lines if not l.startswith('#') and l.strip()]
        if not data_lines:
            return {"error": "no data"}
        parts = data_lines[0].split()
        # Format: YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
        def val(v):
            return None if v == 'MM' else float(v)
        result = {
            "windDir": val(parts[5]),
            "windSpeed": val(parts[6]),   # m/s
            "windGust": val(parts[7]),    # m/s
            "pressure": val(parts[12]),
            "pressureTendency": None,
            "airTemp": val(parts[13]),
            "waterTemp": val(parts[14]),
            "time": f"{parts[2]}/{parts[1]} {parts[3]}:{parts[4]}Z"
        }
        # Historique: 6 dernières mesures
        hist = []
        for l in data_lines[:6]:
            p = l.split()
            hist.append({
                "time": f"{p[3]}:{p[4]}",
                "windDir": val(p[5]),
                "windSpeed": val(p[6]),
                "windGust": val(p[7])
            })
        result["history"] = hist
        wind_cache[key] = {"ts": time.time(), "data": result}
        return result
    except Exception as e:
        return {"error": str(e)}

def fetch_asos(station_id):
    """Fetch ASOS station data from NOAA weather.gov API"""
    key = f"asos_{station_id}"
    if key in wind_cache and time.time() - wind_cache[key]['ts'] < WIND_TTL:
        return wind_cache[key]['data']
    try:
        url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
        req = urllib.request.Request(url, headers={
            "User-Agent": "MidnightRider/1.0 (navigation@midnightrider.net)",
            "Accept": "application/geo+json"
        })
        res = urllib.request.urlopen(req, timeout=10)
        raw = json.loads(res.read())
        p = raw.get("properties", {})
        def gv(field):
            v = p.get(field, {})
            return v.get("value") if isinstance(v, dict) else None
        result = {
            "windDir": gv("windDirection"),
            "windSpeed": gv("windSpeed"),    # m/s
            "windGust": gv("windGust"),      # m/s
            "pressure": gv("barometricPressure"),  # Pa → hPa
            "pressureTendency": None,
            "airTemp": gv("temperature"),
            "time": p.get("timestamp", "")[:16].replace("T", " ") + "Z"
        }
        # Convertir Pa → hPa
        if result["pressure"]:
            result["pressure"] = result["pressure"] / 100
        # Fetch historical observations
        try:
            url2 = f"https://api.weather.gov/stations/{station_id}/observations?limit=6"
            req2 = urllib.request.Request(url2, headers={
                "User-Agent": "MidnightRider/1.0",
                "Accept": "application/geo+json"
            })
            res2 = urllib.request.urlopen(req2, timeout=10)
            raw2 = json.loads(res2.read())
            hist = []
            for feat in raw2.get("features", [])[:6]:
                pp = feat.get("properties", {})
                def gv2(field):
                    v = pp.get(field, {})
                    return v.get("value") if isinstance(v, dict) else None
                t = pp.get("timestamp", "")
                hist.append({
                    "time": t[11:16] + "Z" if len(t) > 16 else t,
                    "windDir": gv2("windDirection"),
                    "windSpeed": gv2("windSpeed"),
                    "windGust": gv2("windGust")
                })
            result["history"] = hist
        except:
            result["history"] = []
        wind_cache[key] = {"ts": time.time(), "data": result}
        return result
    except Exception as e:
        return {"error": str(e)}

def haversine_m(a, b):
    """Distance in meters between two {lat, lon} points."""
    R = 6371000
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(x), math.sqrt(1-x))

def bearing_deg(a, b):
    """Bearing in degrees from point a to point b (0-360)."""
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def signed_dist_m(pin, rc, pos):
    """Signed perpendicular distance from boat to start line (m)."""
    lm = 111319.9
    lo = lm * math.cos(math.radians((pin["lat"] + rc["lat"]) / 2))
    bx = (rc["lon"] - pin["lon"]) * lo
    by = (rc["lat"] - pin["lat"]) * lm
    px = (pos["lon"] - pin["lon"]) * lo
    py = (pos["lat"] - pin["lat"]) * lm
    l = math.sqrt(bx*bx + by*by)
    return 0 if l == 0 else (bx*py - by*px) / l

def get_race_data():
    """Return real-time race line geometry data."""
    pin = start_line_cache.get("pin")
    rc = start_line_cache.get("boat")
    raw = get_gps_position()
    
    r = {
        "ok": False,
        "pin_set": pin is not None,
        "rc_set": rc is not None,
        "gps_ok": bool(raw.get("latitude")),
        "ts": time.time()
    }
    
    if raw.get("latitude"):
        r["gps_lat"] = round(raw["latitude"], 5)
        r["gps_lon"] = round(raw["longitude"], 5)
    
    if not pin or not rc or not raw.get("latitude"):
        return r
    
    pos = {"lat": raw["latitude"], "lon": raw["longitude"]}
    d = signed_dist_m(pin, rc, pos)
    ab = abs(d)
    
    side = "OCS" if ab < 15 else ("CLEAR" if d > 0 else "BEHIND")
    lb = bearing_deg(pin, rc)
    bias = None
    
    try:
        tw = get_signalk("vessels/self/environment/wind/directionTrue")
        if tw.get("value"):
            b = lb - (math.degrees(tw["value"]) + 90) % 360
            if b > 180: b -= 360
            if b < -180: b += 360
            bias = round(b, 1)
    except:
        pass
    
    r.update({
        "ok": True,
        "distance_to_line_m": round(ab, 1),
        "line_side": side,
        "line_bias_deg": bias,
        "line_heading_deg": round(lb, 1),
        "start_line_length_m": round(haversine_m(pin, rc), 1),
        "pin_bearing_deg": round(bearing_deg(pos, pin), 1),
        "pin_dist_m": round(haversine_m(pos, pin), 1),
        "rc_bearing_deg": round(bearing_deg(pos, rc), 1),
        "rc_dist_m": round(haversine_m(pos, rc), 1)
    })
    
    return r

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self.serve_file("index.html")
        elif self.path == "/wind":
            self.serve_file("wind.html")
        elif self.path == "/fleet":
            self.serve_file("fleet.html")
        elif self.path == "/api/position":
            pos = get_gps_position()
            self.send_json(pos)
        elif self.path == "/api/navigation":
            self.send_json(get_navigation())
        elif self.path.startswith("/api/ais"):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            radius = float(params.get('radius', ['10'])[0])
            self.send_json(get_ais_targets(radius))
        elif self.path == "/api/weather/status":
            self.send_json(weather_collector.status())
        elif self.path.startswith("/api/ndbc/"):
            station_id = self.path.split("/")[-1].upper()
            self.send_json(fetch_ndbc(station_id))
        elif self.path.startswith("/api/asos/"):
            station_id = self.path.split("/")[-1].upper()
            self.send_json(fetch_asos(station_id))
        elif self.path == "/equipage":
            self.serve_file("crew.html")
        elif self.path == "/voiles":
            self.serve_file("voiles.html")
        elif self.path == "/api/race_data":
            self.send_json(get_race_data())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON body"}')
            return

        if self.path == "/api/sail":
            ok = write_influx("regatta.sails",
                {"sail": body.get("sail","unknown"), "change": 1},
                {"type": body.get("type", "sail")})
            self.send_json({"ok": ok})
        elif self.path == "/api/helmsman":
            ok = write_influx("regatta.helmsman",
                {"name": body.get("name","unknown"), "active": 1},
                {"type": "helmsman"})
            self.send_json({"ok": ok})
        elif self.path == "/api/start_line":
            pos = get_gps_position()
            point = body.get("point", "pin")
            lat = pos.get("latitude")
            lon = pos.get("longitude")
            # Validate GPS before storing pin
            if not lat or not lon or (abs(lat) < 0.001 and abs(lon) < 0.001):
                self.send_json({"ok": False, "error": "GPS unavailable — cannot pin location", "lat": None, "lon": None})
                return
            # Signal K path: pin=startLinePrt, boat=startLineStb
            sk_path = "racing/startLinePrt" if point == "pin" else "racing/startLineStb"
            ok = put_signalk(sk_path, {"latitude": lat, "longitude": lon})
            if ok:
                start_line_cache[point] = {"lat": lat, "lon": lon}
            self.send_json({"ok": ok, "lat": round(lat, 5), "lon": round(lon, 5), "signalk_path": sk_path})
        elif self.path == "/api/weather/start":
            self.send_json(weather_collector.start())
        elif self.path == "/api/weather/stop":
            self.send_json(weather_collector.stop())
        elif self.path == "/api/event":
            ok = write_influx("regatta.events",
                {"note": body.get("note",""), "value": 1},
                {"type": body.get("type","note")})
            self.send_json({"ok": ok})
        elif self.path == "/api/timer":
            seconds = body.get("seconds_to_start", 0)
            label = body.get("label", "")  # "J-5min", "J-3min", etc
            active = body.get("active", True)
            ok = write_influx(
                "regatta.timer",
                {
                    "seconds_to_start": int(seconds),
                    "active": 1 if active else 0,
                    "label": label
                },
                {"type": "start_timer"}
            )
            self.send_json({"ok": ok})
        else:
            self.send_response(404)
            self.end_headers()

    def serve_file(self, filename):
        file_path = os.path.join(os.path.dirname(__file__), filename)
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
        except:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    load_start_line_from_signalk()
    server = ThreadingHTTPServer(("0.0.0.0", 5000), Handler)
    print("Regatta server on :5000")
    server.serve_forever()

#!/usr/bin/env python3
"""Regatta interface server — MidnightRider"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json, time, urllib.parse, urllib.request, os

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA=="
INFLUX_ORG = "MidnightRider"
INFLUX_BUCKET = "signalk"

SIGNALK_URL = "http://localhost:3000"

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

def get_gps_position():
    try:
        url = f"{SIGNALK_URL}/signalk/v1/api/vessels/self/navigation/position"
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req, timeout=2)
        data = json.loads(res.read())
        return data.get("value", {})
    except:
        return {}

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
            self.serve_html()
        elif self.path == "/api/position":
            pos = get_gps_position()
            self.send_json(pos)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

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
            point = body.get("point", "pin")  # pin ou boat
            lat = pos.get("latitude", 0)
            lon = pos.get("longitude", 0)
            ok = write_influx("regatta.start_line",
                {"lat": lat, "lon": lon, "point": point},
                {"mark": point})
            self.send_json({"ok": ok, "lat": lat, "lon": lon})

        elif self.path == "/api/event":
            ok = write_influx("regatta.events",
                {"note": body.get("note",""), "value": 1},
                {"type": body.get("type","note")})
            self.send_json({"ok": ok})
        else:
            self.send_response(404)
            self.end_headers()

    def serve_html(self):
        html_path = os.path.join(os.path.dirname(__file__), "index.html")
        with open(html_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5000), Handler)
    print("Regatta server on :5000")
    server.serve_forever()

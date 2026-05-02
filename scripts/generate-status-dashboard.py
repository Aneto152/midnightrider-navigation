#!/usr/bin/env python3
"""
generate-status-dashboard.py — Midnight Rider
Generates the DATA-MODEL-STATUS Grafana dashboard JSON.
Lists all measurements and sensors with operational status.

Run: python3 scripts/generate-status-dashboard.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
import base64

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3001")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "")
DATASOURCE_UID = os.environ.get("INFLUXDB_DATASOURCE_UID", "efifgp8jvgj5sf")
INFLUX_BUCKET = "midnight_rider"

def flux_last_seen(measurement, field, stale_seconds=30):
    """Returns 1.0 if data received in last N seconds, else 0.0"""
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f' |> range(start: -{stale_seconds}s)\n'
        f' |> filter(fn: (r) => r._measurement == "{measurement}" and r._field == "{field}")\n'
        f' |> count()\n'
        f' |> map(fn: (r) => ({{r with _value: if r._value > 0 then 1.0 else 0.0}}))'
    )

def flux_last_value(measurement, field):
    """Returns last value of a field"""
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f' |> range(start: -5m)\n'
        f' |> filter(fn: (r) => r._measurement == "{measurement}" and r._field == "{field}")\n'
        f' |> last()'
    )

def stat_panel(pid, title, measurement, field, unit="", stale_sec=30, 
               x=0, y=0, w=6, h=4, description=""):
    """Green=active, red=no data stat panel"""
    return {
        "id": pid,
        "type": "stat",
        "title": title,
        "description": description,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"]},
            "orientation": "auto",
            "textMode": "value_and_name",
            "colorMode": "background",
            "graphMode": "none",
            "justifyMode": "center"
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "orange", "value": 0.1},
                        {"color": "green", "value": 1.0}
                    ]
                },
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "0": {"text": "NO DATA", "color": "red"},
                            "1": {"text": "ACTIVE", "color": "green"}
                        }
                    }
                ],
                "color": {"mode": "thresholds"}
            }
        },
        "datasource": {"type": "influxdb", "uid": DATASOURCE_UID},
        "targets": [{
            "refId": "A",
            "datasource": {"type": "influxdb", "uid": DATASOURCE_UID},
            "query": flux_last_seen(measurement, field, stale_sec)
        }]
    }

def value_panel(pid, title, measurement, field, unit="", decimals=1, 
                x=0, y=0, w=4, h=3):
    """Shows last real value"""
    return {
        "id": pid,
        "type": "stat",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"]},
            "colorMode": "value",
            "graphMode": "area",
            "textMode": "value_and_name"
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": decimals,
                "noValue": "—",
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "blue", "value": None}]
                }
            }
        },
        "datasource": {"type": "influxdb", "uid": DATASOURCE_UID},
        "targets": [{
            "refId": "A",
            "datasource": {"type": "influxdb", "uid": DATASOURCE_UID},
            "query": flux_last_value(measurement, field)
        }]
    }

def row_panel(pid, title, y=0):
    """Row separator"""
    return {
        "id": pid,
        "type": "row",
        "title": title,
        "collapsed": False,
        "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}
    }

def text_panel(pid, content, x=0, y=0, w=24, h=2):
    """Markdown text panel"""
    return {
        "id": pid,
        "type": "text",
        "title": "",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"mode": "markdown", "content": content}
    }

def build_dashboard():
    panels = []
    pid = 1

    panels.append(text_panel(pid,
        "# ⚓ Midnight Rider — Data Model Status\n"
        "_Real-time operational status of all measurements and sensors. "
        "**Green** = active data in last 30s. "
        "**Orange** = stale (30s-5min). "
        "**Red** = no data._",
        y=0, h=2))
    pid += 1

    panels.append(row_panel(pid, "🔌 SENSORS — Hardware Status", y=2))
    pid += 1

    sensors = [
        ("Signal K", "navigation", "sog_kts", "", 30, "Signal K server → NMEA 2000"),
        ("GPS/GNSS", "navigation", "latitude", "", 30, "NANO-HED10L dual antenna"),
        ("Wind B&G", "environment", "tws_kts", "", 30, "WS320 mechanical sensor"),
        ("IMU (Roll)", "navigation", "heel_deg", "", 30, "BNO085 IMU attitude"),
        ("Depth", "navigation", "depth_m", "", 60, "NMEA 2000 sounder"),
        ("NOAA Buoy", "environment", "buoy_wvht", "", 300, "NDBC nearest station"),
    ]

    x, y = 0, 3
    for title, meas, field, unit, stale, desc in sensors:
        panels.append(stat_panel(pid, title, meas, field, unit, stale,
                                x=x, y=y, w=6, h=4, description=desc))
        pid += 1
        x += 6
        if x >= 24:
            x = 0
            y += 4

    y = 11

    panels.append(row_panel(pid, "🧭 NAVIGATION", y=y))
    pid += 1
    y += 1

    nav_values = [
        ("Latitude", "navigation", "latitude", "", 6, 5),
        ("Longitude", "navigation", "longitude", "", 6, 5),
        ("SOG", "navigation", "sog_kts", "velocityKn", 1, 5),
        ("COG", "navigation", "cog_deg", "degree", 0, 5),
        ("Heading", "navigation", "heading_mag_deg", "degree", 0, 5),
        ("STW", "navigation", "stw_kts", "velocityKn", 1, 5),
        ("Heel", "navigation", "heel_deg", "degree", 1, 5),
        ("Pitch", "navigation", "pitch_deg", "degree", 1, 5),
        ("Depth", "navigation", "depth_m", "lengthm", 1, 60),
        ("Satellites", "navigation", "satellites", "", 0, 30),
    ]

    x = 0
    for title, meas, field, unit, dec, stale in nav_values:
        panels.append(value_panel(pid, title, meas, field, unit, dec, x=x, y=y, w=4, h=3))
        pid += 1
        x += 4
        if x >= 24:
            x = 0
            y += 3

    y += 3

    panels.append(row_panel(pid, "💨 WIND & ENVIRONMENT", y=y))
    pid += 1
    y += 1

    env_values = [
        ("TWS", "environment", "tws_kts", "velocityKn", 1, 5),
        ("TWA", "environment", "twa_deg", "degree", 0, 5),
        ("AWA", "environment", "awa_deg", "degree", 0, 5),
        ("AWS", "environment", "aws_kts", "velocityKn", 1, 5),
        ("TWD", "environment", "twd_deg", "degree", 0, 5),
        ("Air Temp", "environment", "air_temp_c", "celsius", 1, 60),
        ("Water Temp", "environment", "water_temp_c", "celsius", 1, 60),
        ("Pressure", "environment", "pressure_hpa", "pressurehpa", 1, 60),
    ]

    x = 0
    for title, meas, field, unit, dec, stale in env_values:
        panels.append(value_panel(pid, title, meas, field, unit, dec, x=x, y=y, w=4, h=3))
        pid += 1
        x += 4
        if x >= 24:
            x = 0
            y += 3

    y += 3

    panels.append(row_panel(pid, "⚡ PERFORMANCE", y=y))
    pid += 1
    y += 1

    perf_values = [
        ("VMG", "performance", "vmg_kts", "velocityKn", 2, 5),
        ("Target Speed", "performance", "target_speed_kts", "velocityKn", 2, 5),
        ("Polar Ratio", "performance", "polar_ratio", "percentunit", 1, 5),
        ("Leeway", "performance", "leeway_deg", "degree", 1, 5),
    ]

    x = 0
    for title, meas, field, unit, dec, stale in perf_values:
        panels.append(value_panel(pid, title, meas, field, unit, dec, x=x, y=y, w=6, h=3))
        pid += 1
        x += 6

    y += 3

    panels.append(row_panel(pid, "🖥️ SYSTEM — Raspberry Pi", y=y))
    pid += 1
    y += 1

    sys_values = [
        ("CPU Temp", "system", "cpu_temp_celsius", "celsius", 1, 60),
        ("CPU Load", "system", "cpu_percent", "percent", 0, 60),
        ("RAM Usage", "system", "memory_percent", "percent", 0, 60),
        ("Disk Usage", "system", "disk_percent", "percent", 0, 60),
    ]

    x = 0
    for title, meas, field, unit, dec, stale in sys_values:
        panels.append(value_panel(pid, title, meas, field, unit, dec, x=x, y=y, w=6, h=3))
        pid += 1
        x += 6

    return {
        "uid": "data-model-status",
        "title": "DATA MODEL STATUS",
        "tags": ["midnight-rider", "status", "monitoring"],
        "timezone": "browser",
        "refresh": "10s",
        "version": 1,
        "schemaVersion": 39,
        "time": {"from": "now-1h", "to": "now"},
        "panels": panels
    }

def push_dashboard(dashboard):
    """Deploy to Grafana"""
    token = base64.b64encode(f"admin:{GRAFANA_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "dashboard": dashboard,
        "overwrite": True,
        "message": "Initial: Data Model Status dashboard"
    }).encode()

    req = urllib.request.Request(
        f"{GRAFANA_URL}/api/dashboards/db",
        data=payload,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            print(f"✅ Dashboard deployed → {GRAFANA_URL}{resp.get('url')}")
            return resp
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()}")
        return None

if __name__ == "__main__":
    dashboard = build_dashboard()

    out_file = "grafana-dashboards/data-model-status.json"
    with open(out_file, "w") as f:
        json.dump(dashboard, f, indent=2)
        f.write("\n")

    print(f"✅ JSON saved: {out_file}")
    print(f"   Panels: {len(dashboard['panels'])}")

    try:
        with open(out_file) as f:
            json.load(f)
        print("✅ JSON valid")
    except Exception as e:
        print(f"❌ JSON invalid: {e}")
        sys.exit(1)

    if GRAFANA_PASSWORD:
        push_dashboard(dashboard)
    else:
        print("⚠️ GRAFANA_PASSWORD not set — deploy manually")

    print(f"\n📊 Dashboard created with {len(dashboard['panels'])} panels")

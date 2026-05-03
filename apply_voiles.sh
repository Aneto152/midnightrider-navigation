#!/bin/bash
cd /home/aneto/.openclaw/workspace

# TÂCHE 1 — Appliquer voiles
python3 << 'PYEOF'
import json
from pathlib import Path

DS = {"type": "influxdb", "uid": "efifgp8jvgj5sf"}
BKT = "midnight_rider"

def flux(field):
    return (f'from(bucket: "{BKT}")\n |> range(start: -6h)\n'
            f' |> filter(fn: (r) => r._measurement == "regatta.sails")\n'
            f' |> filter(fn: (r) => r._field == "{field}")\n |> last()')

def stat(pid, title, field, mappings, w=6, h=5, x=0, y=1):
    return {"type": "stat", "id": pid, "title": title, "datasource": DS,
     "gridPos": {"h": h, "w": w, "x": x, "y": y},
     "targets": [{"refId": "A", "datasource": DS, "query": flux(field)}],
     "fieldConfig": {"defaults": {
         "color": {"mode": "thresholds"},
         "mappings": [{"type": "value", "options": mappings}],
         "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]}},
         "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
         "colorMode": "background", "graphMode": "none", "textMode": "auto", "orientation": "auto"}}

SAIL_PANELS = [
    {"type": "row", "id": 200, "title": "VOILES", "collapsed": False,
     "datasource": DS, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []}},
    stat(201, "GV", "mainsail_config",
         {"FULL": {"text": "Pleine", "color": "green"},
          "R1": {"text": "Ris 1", "color": "yellow"},
          "R2": {"text": "Ris 2", "color": "orange"},
          "R3": {"text": "Ris 3", "color": "red"},
          "FURLED": {"text": "Affalee", "color": "gray"}}, x=0),
    stat(202, "Foc Genois", "headsail_config",
         {"GENOA": {"text": "Genois", "color": "green"},
          "JIB": {"text": "Foc", "color": "blue"},
          "STORM": {"text": "Foc tempete", "color": "red"},
          "NONE": {"text": "Aucun", "color": "gray"}}, x=6),
    stat(203, "Spi Asym", "downwind_sail",
         {"SPI": {"text": "Spi sym", "color": "purple"},
          "ASYM": {"text": "Asym", "color": "cyan"},
          "NONE": {"text": "Aucun", "color": "gray"}}, x=12),
    {"type": "stat", "id": 204, "title": "Note voilure", "datasource": DS,
     "gridPos": {"h": 5, "w": 6, "x": 18, "y": 1},
     "targets": [{"refId": "A", "datasource": DS, "query": flux("sail_note")}],
     "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "gray"},
         "thresholds": {"mode": "absolute", "steps": [{"color": "gray", "value": None}]}},
         "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
         "colorMode": "value", "graphMode": "none", "textMode": "auto", "orientation": "auto"}},
    {"type": "text", "id": 205, "title": "Interface",
     "gridPos": {"h": 3, "w": 24, "x": 0, "y": 6},
     "options": {"content": "Regatta: http://midnightrider.local:8888/regatta/", "mode": "markdown"},
     "datasource": DS, "targets": [], "fieldConfig": {"defaults": {}, "overrides": []}},
]

f = Path("grafana-dashboards/03-performance.json")
d = json.loads(f.read_text())
root = d.get("dashboard", d)
if any(p.get("id") == 200 for p in root.get("panels", [])):
    print("Skip: panels already present")
else:
    for p in root.get("panels", []):
        if "gridPos" in p:
            p["gridPos"]["y"] = p["gridPos"].get("y", 0) + 10
    root["panels"] = SAIL_PANELS + root.get("panels", [])
    root["version"] = root.get("version", 1) + 1
    if "dashboard" in d:
        d["dashboard"] = root
    f.write_text(json.dumps(d, indent=2))
    print(f"OK 03-performance: {len(SAIL_PANELS)} panels")
PYEOF

python3 -c "import json; d=json.load(open('grafana-dashboards/03-performance.json')); print(f'Total: {len(d[\"panels\"])} panels')"

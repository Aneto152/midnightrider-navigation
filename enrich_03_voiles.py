import json
from pathlib import Path

DS = {"type": "influxdb", "uid": "efifgp8jvgj5sf"}
BKT = "midnight_rider"

def flux(field):
    return f'from(bucket: "{BKT}")\n |> range(start: -6h)\n |> filter(fn: (r) => r._measurement == "regatta.sails")\n |> filter(fn: (r) => r._field == "{field}")\n |> last()'

SAIL_PANELS = [
    {"type": "row", "id": 200, "title": "🪁 GESTION DES VOILES", "collapsed": False,
     "datasource": DS, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []}},
    
    {"type": "stat", "id": 201, "title": "🪁 Grand-voile", "datasource": DS,
     "gridPos": {"h": 5, "w": 6, "x": 0, "y": 1},
     "targets": [{"refId": "A", "datasource": DS, "query": flux("mainsail_config")}],
     "fieldConfig": {"defaults": {"color": {"mode": "thresholds"},
         "mappings": [{"type": "value", "options": {
             "FULL": {"text": "OK Pleine", "color": "green"},
             "R1": {"text": "Ris 1", "color": "yellow"},
             "R2": {"text": "Ris 2", "color": "orange"},
             "R3": {"text": "Ris 3", "color": "red"},
             "FURLED": {"text": "Affalee", "color": "gray"}
         }},
         "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]}},
         "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
         "colorMode": "background", "graphMode": "none", "textMode": "auto", "orientation": "auto"}},
    
    {"type": "stat", "id": 202, "title": "Foc Genois", "datasource": DS,
     "gridPos": {"h": 5, "w": 6, "x": 6, "y": 1},
     "targets": [{"refId": "A", "datasource": DS, "query": flux("headsail_config")}],
     "fieldConfig": {"defaults": {"color": {"mode": "thresholds"},
         "mappings": [{"type": "value", "options": {
             "GENOA": {"text": "OK Genois", "color": "green"},
             "JIB": {"text": "Foc", "color": "blue"},
             "STORM": {"text": "Foc tempete", "color": "red"},
             "NONE": {"text": "Aucun", "color": "gray"}
         }},
         "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]}},
         "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
         "colorMode": "background", "graphMode": "none", "textMode": "auto", "orientation": "auto"}},
    
    {"type": "stat", "id": 203, "title": "Spi Asymetrique", "datasource": DS,
     "gridPos": {"h": 5, "w": 6, "x": 12, "y": 1},
     "targets": [{"refId": "A", "datasource": DS, "query": flux("downwind_sail")}],
     "fieldConfig": {"defaults": {"color": {"mode": "thresholds"},
         "mappings": [{"type": "value", "options": {
             "SPI": {"text": "Spi sym", "color": "purple"},
             "ASYM": {"text": "Asymetrique", "color": "cyan"},
             "NONE": {"text": "Aucun", "color": "gray"}
         }},
         "thresholds": {"mode": "absolute", "steps": [{"color": "gray", "value": None}]}},
         "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
         "colorMode": "background", "graphMode": "none", "textMode": "auto", "orientation": "auto"}},
    
    {"type": "stat", "id": 204, "title": "Note voilure", "datasource": DS,
     "gridPos": {"h": 5, "w": 6, "x": 18, "y": 1},
     "targets": [{"refId": "A", "datasource": DS, "query": flux("sail_note")}],
     "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "gray"},
         "thresholds": {"mode": "absolute", "steps": [{"color": "gray", "value": None}]}},
         "overrides": []},
     "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
         "colorMode": "value", "graphMode": "none", "textMode": "auto", "orientation": "auto"}},
    
    {"type": "text", "id": 205, "title": "Modifier voilure", "datasource": DS,
     "gridPos": {"h": 3, "w": 24, "x": 0, "y": 6},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []},
     "options": {"content": "Changer voilure: Ouvrir interface regatta :8888/regatta/ - Onglet Voiles",
         "mode": "markdown"}},
]

f = Path("grafana-dashboards/03-performance.json")
data = json.loads(f.read_text())
root = data.get("dashboard", data)
for p in root.get("panels", []):
    if "gridPos" in p:
        p["gridPos"]["y"] = p["gridPos"].get("y", 0) + 10
root["panels"] = SAIL_PANELS + root.get("panels", [])
root["version"] = root.get("version", 1) + 1
if "dashboard" in data:
    data["dashboard"] = root
else:
    data = root
f.write_text(json.dumps(data, indent=2))
print(f"OK 03-performance.json: {len(SAIL_PANELS)} voiles panels added")

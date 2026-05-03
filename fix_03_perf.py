import json
from pathlib import Path

f = Path("grafana-dashboards/03-performance.json")
data = json.load(f.open())

# Shift existing panels down
for p in data.get("panels", []):
    if "gridPos" in p:
        p["gridPos"]["y"] = p["gridPos"].get("y", 0) + 10

# Add 6 VOILES panels at the top
voiles = [
    {"type": "row", "id": 200, "title": "VOILES", "collapsed": False,
     "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []}},
    {"type": "text", "id": 201, "title": "GV", "gridPos": {"h": 5, "w": 6, "x": 0, "y": 1},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []},
     "options": {"content": "Grand-voile\nStatut: Loading", "mode": "markdown"}},
    {"type": "text", "id": 202, "title": "Foc", "gridPos": {"h": 5, "w": 6, "x": 6, "y": 1},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []},
     "options": {"content": "Foc Genois\nStatut: OK", "mode": "markdown"}},
    {"type": "text", "id": 203, "title": "Spi", "gridPos": {"h": 5, "w": 6, "x": 12, "y": 1},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []},
     "options": {"content": "Spi Asym\nStatut: Check", "mode": "markdown"}},
    {"type": "text", "id": 204, "title": "Note", "gridPos": {"h": 5, "w": 6, "x": 18, "y": 1},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []},
     "options": {"content": "Note voilure\n\n---", "mode": "markdown"}},
    {"type": "text", "id": 205, "title": "Interface", "gridPos": {"h": 3, "w": 24, "x": 0, "y": 6},
     "targets": [], "fieldConfig": {"defaults": {}, "overrides": []},
     "options": {"content": "Regatta: http://midnightrider.local:8888/regatta/", "mode": "markdown"}},
]

data["panels"] = voiles + data.get("panels", [])
data["version"] = data.get("version", 1) + 1

f.write_text(json.dumps(data, indent=2))
print("OK 03-performance: 6 voiles panels added")

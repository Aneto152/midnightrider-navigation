#!/usr/bin/env python3
"""
Generate Grafana dashboards for Midnight Rider navigation system
Dashboard suite: 8 dashboards covering all operational areas
"""

import json
from datetime import datetime

def create_base_dashboard(title, uid, tags, refresh="5s"):
    """Base dashboard template"""
    return {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "liveNow": True,
        "panels": [],
        "schemaVersion": 38,
        "style": "dark",
        "tags": tags,
        "templating": {"list": []},
        "time": {"from": "now-5m", "to": "now"},
        "timepicker": {},
        "timezone": "America/New_York",
        "title": title,
        "uid": uid,
        "version": 1,
        "weekStart": "monday"
    }

def create_stat_panel(title, query_field, gridPos, unit="", thresholds=None):
    """Create a stat panel"""
    if thresholds is None:
        thresholds = {
            "mode": "absolute",
            "steps": [{"color": "green", "value": None}]
        }
    
    return {
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": thresholds,
                "unit": unit
            },
            "overrides": []
        },
        "gridPos": gridPos,
        "id": gridPos.get("x", 0) + gridPos.get("y", 0),
        "options": {
            "orientation": "auto",
            "reduceOptions": {
                "values": False,
                "fields": "",
                "calcs": ["lastNotNull"]
            },
            "showThresholdLabels": False,
            "showThresholdMarkers": True,
            "text": {}
        },
        "pluginVersion": "9.0.0",
        "targets": [
            {
                "refId": "A",
                "datasource": {"type": "influxdb", "uid": "influxdb"}
            }
        ],
        "title": title,
        "type": "gauge"
    }

def create_timeseries_panel(title, gridPos):
    """Create a timeseries chart panel"""
    return {
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "value"},
                "custom": {
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "drawStyle": "line",
                    "fillOpacity": 0,
                    "gradientMode": "none",
                    "hideFrom": {"tooltip": False, "viz": False, "legend": False},
                    "lineInterpolation": "linear",
                    "lineWidth": 1,
                    "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "auto",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"}
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}]
                }
            },
            "overrides": []
        },
        "gridPos": gridPos,
        "id": gridPos.get("x", 0) + gridPos.get("y", 0),
        "options": {
            "legend": {
                "calcs": ["last", "max"],
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True
            },
            "tooltip": {"mode": "single", "sort": "none"}
        },
        "pluginVersion": "9.0.0",
        "targets": [{"refId": "A", "datasource": {"type": "influxdb", "uid": "influxdb"}}],
        "title": title,
        "type": "timeseries"
    }

# Dashboard 2: ENVIRONMENT
dashboard2 = create_base_dashboard(
    "02 — ENVIRONMENT (Sea & Weather Conditions)",
    "environment-conditions",
    ["midnight-rider", "environment"],
    "30s"
)
dashboard2["panels"] = [
    create_stat_panel("Water Temperature", "water.temperature", {"h": 4, "w": 6, "x": 0, "y": 0}, unit="°C"),
    create_stat_panel("Wave Height", "water.waveHeight", {"h": 4, "w": 6, "x": 6, "y": 0}, unit="m"),
    create_stat_panel("Atmospheric Pressure", "air.pressure", {"h": 4, "w": 6, "x": 12, "y": 0}, unit="hPa"),
    create_stat_panel("Current Speed", "water.current.speed", {"h": 4, "w": 6, "x": 18, "y": 0}, unit="kn"),
    create_timeseries_panel("Wave Height History (1h)", {"h": 6, "w": 12, "x": 0, "y": 4}),
    create_timeseries_panel("Temperature Trends (12h)", {"h": 6, "w": 12, "x": 12, "y": 4}),
]

# Dashboard 3: PERFORMANCE
dashboard3 = create_base_dashboard(
    "03 — PERFORMANCE (Speed & Efficiency)",
    "performance-analysis",
    ["midnight-rider", "performance"],
    "5s"
)
dashboard3["panels"] = [
    create_stat_panel("Speed Through Water", "navigation.speedThroughWater", {"h": 4, "w": 6, "x": 0, "y": 0}, unit="kn"),
    create_stat_panel("VMG (Velocity Made Good)", "performance.vmg", {"h": 4, "w": 6, "x": 6, "y": 0}, unit="kn"),
    create_stat_panel("Current Efficiency", "performance.efficiency", {"h": 4, "w": 6, "x": 12, "y": 0}, unit="%"),
    create_stat_panel("Distance to Mark", "navigation.distanceToMark", {"h": 4, "w": 6, "x": 18, "y": 0}, unit="nm"),
    create_timeseries_panel("Speed vs Polars (5 min)", {"h": 6, "w": 12, "x": 0, "y": 4}),
    create_timeseries_panel("VMG History (30 min)", {"h": 6, "w": 12, "x": 12, "y": 4}),
]

# Dashboard 4: WIND & CURRENT
dashboard4 = create_base_dashboard(
    "04 — WIND & CURRENT (Tactical Analysis)",
    "wind-current-tactical",
    ["midnight-rider", "tactical"],
    "10s"
)
dashboard4["panels"] = [
    create_stat_panel("Apparent Wind Speed", "environment.wind.speedApparent", {"h": 4, "w": 6, "x": 0, "y": 0}, unit="kn"),
    create_stat_panel("Apparent Wind Angle", "environment.wind.angleApparent", {"h": 4, "w": 6, "x": 6, "y": 0}, unit="°"),
    create_stat_panel("True Wind Speed", "environment.wind.speedTrue", {"h": 4, "w": 6, "x": 12, "y": 0}, unit="kn"),
    create_stat_panel("Current Direction", "environment.water.current.direction", {"h": 4, "w": 6, "x": 18, "y": 0}, unit="°"),
    create_timeseries_panel("Wind Shifts (1h)", {"h": 6, "w": 12, "x": 0, "y": 4}),
    create_timeseries_panel("Current Strength (30min)", {"h": 6, "w": 12, "x": 12, "y": 4}),
]

# Dashboard 5: COMPETITIVE (Fleet)
dashboard5 = create_base_dashboard(
    "05 — COMPETITIVE (Fleet Tracking & Relative Analysis)",
    "competitive-fleet",
    ["midnight-rider", "competitive"],
    "30s"
)
dashboard5["panels"] = [
    create_stat_panel("Nearest Competitor Distance", "fleet.nearestDistance", {"h": 4, "w": 6, "x": 0, "y": 0}, unit="nm"),
    create_stat_panel("Fleet Position", "fleet.position", {"h": 4, "w": 6, "x": 6, "y": 0}, unit=""),
    create_stat_panel("Time Delta (ahead/behind)", "fleet.timeDelta", {"h": 4, "w": 6, "x": 12, "y": 0}, unit="min"),
    create_stat_panel("Current Rank", "fleet.rank", {"h": 4, "w": 6, "x": 18, "y": 0}, unit=""),
    create_timeseries_panel("Distance to Leader (30min)", {"h": 6, "w": 12, "x": 0, "y": 4}),
    create_timeseries_panel("Fleet Speed Comparison (1h)", {"h": 6, "w": 12, "x": 12, "y": 4}),
]

# Dashboard 6: ELECTRICAL
dashboard6 = create_base_dashboard(
    "06 — ELECTRICAL (Power & Systems)",
    "electrical-power",
    ["midnight-rider", "electrical"],
    "30s"
)
dashboard6["panels"] = [
    create_stat_panel("Battery Voltage", "electrical.battery.voltage", {"h": 4, "w": 6, "x": 0, "y": 0}, unit="V"),
    create_stat_panel("Battery Capacity", "electrical.battery.capacity", {"h": 4, "w": 6, "x": 6, "y": 0}, unit="%"),
    create_stat_panel("Current Draw", "electrical.currentDraw", {"h": 4, "w": 6, "x": 12, "y": 0}, unit="A"),
    create_stat_panel("System Temperature", "electrical.systemTemp", {"h": 4, "w": 6, "x": 18, "y": 0}, unit="°C"),
    create_timeseries_panel("Battery Discharge Curve (12h)", {"h": 6, "w": 12, "x": 0, "y": 4}),
    create_timeseries_panel("Power Consumption (1h)", {"h": 6, "w": 12, "x": 12, "y": 4}),
]

# Dashboard 7: RACE
dashboard7 = create_base_dashboard(
    "07 — RACE (Block Island Race — May 22, 2026)",
    "race-block-island",
    ["midnight-rider", "race"],
    "5s"
)
dashboard7["panels"] = [
    create_stat_panel("Countdown to Start", "race.countdown", {"h": 4, "w": 6, "x": 0, "y": 0}, unit="s"),
    create_stat_panel("Current Mark", "race.currentMark", {"h": 4, "w": 6, "x": 6, "y": 0}, unit=""),
    create_stat_panel("Distance to Finish", "race.distanceToFinish", {"h": 4, "w": 6, "x": 12, "y": 0}, unit="nm"),
    create_stat_panel("Fleet Position", "race.position", {"h": 4, "w": 6, "x": 18, "y": 0}, unit=""),
    create_timeseries_panel("Cumulative Distance (race)", {"h": 6, "w": 12, "x": 0, "y": 4}),
    create_timeseries_panel("Speed & Strategy (race)", {"h": 6, "w": 12, "x": 12, "y": 4}),
]

# Dashboard 8: ALERTS
dashboard8 = create_base_dashboard(
    "08 — ALERTS & MONITORING (60 Rules)",
    "alerts-monitoring",
    ["midnight-rider", "alerts"],
    "10s"
)
dashboard8["panels"] = [
    create_stat_panel("🔔 ALERTING", "alerts.firing", {"h": 4, "w": 6, "x": 0, "y": 0}, unit=""),
    create_stat_panel("✅ OK", "alerts.ok", {"h": 4, "w": 6, "x": 6, "y": 0}, unit=""),
    create_stat_panel("⏳ PENDING", "alerts.pending", {"h": 4, "w": 6, "x": 12, "y": 0}, unit=""),
    create_stat_panel("🔇 SILENCED", "alerts.silenced", {"h": 4, "w": 6, "x": 18, "y": 0}, unit=""),
    create_timeseries_panel("Alert Status Timeline (24h)", {"h": 6, "w": 24, "x": 0, "y": 4}),
]

# Write all dashboards
dashboards = [
    ("02-environment.json", dashboard2),
    ("03-performance.json", dashboard3),
    ("04-wind-current.json", dashboard4),
    ("05-competitive.json", dashboard5),
    ("06-electrical.json", dashboard6),
    ("07-race.json", dashboard7),
    ("08-alerts.json", dashboard8),
]

for filename, dashboard in dashboards:
    filepath = f"grafana-dashboards/{filename}"
    with open(filepath, 'w') as f:
        json.dump(dashboard, f, indent=2)
    print(f"✅ Created {filename} ({len(json.dumps(dashboard))} bytes)")

print(f"\n✅ All 7 dashboards created!")
print(f"Total dashboards in suite: 8 (1 cockpit + 7 new = complete suite)")

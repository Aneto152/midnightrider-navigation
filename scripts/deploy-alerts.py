#!/usr/bin/env python3
"""
Midnight Rider — Deploy Alert Rules to Grafana

Real Grafana Alerting API using /api/ruler/grafana/rules (Grafana 9+).
Creates 14 core alert rules with Flux queries.

Usage:
  python3 scripts/deploy-alerts.py --dry-run     
  python3 scripts/deploy-alerts.py                
  python3 scripts/deploy-alerts.py --delete-all   
"""

import json
import os
import sys
import argparse
import urllib.request
import urllib.error
import base64

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "")
DATASOURCE_UID = os.environ.get("INFLUXDB_DATASOURCE_UID", "efifgp8jvgj5sf")
INFLUX_BUCKET = "midnight_rider"

def auth_header():
    token = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }

def grafana_get(path):
    req = urllib.request.Request(
        f"{GRAFANA_URL}{path}",
        headers=auth_header()
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def grafana_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{GRAFANA_URL}{path}",
        data=body,
        headers=auth_header(),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read()), e.code
        except:
            return {"error": e.read().decode()[:200]}, e.code

def grafana_delete(path):
    req = urllib.request.Request(
        f"{GRAFANA_URL}{path}",
        headers=auth_header(),
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

def flux_threshold(measurement, field, operator, threshold, window="1m"):
    op = ">" if operator == "gt" else "<" if operator == "lt" else "!="
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f' |> range(start: -{window})\n'
        f' |> filter(fn: (r) => r._measurement == "{measurement}")\n'
        f' |> filter(fn: (r) => r._field == "{field}")\n'
        f' |> last()\n'
        f' |> map(fn: (r) => ({{r with _value: if r._value {op} {threshold} then 1.0 else 0.0}}))'
    )

def flux_absence(measurement, field, window="1m"):
    return (
        f'from(bucket: "{INFLUX_BUCKET}")\n'
        f' |> range(start: -{window})\n'
        f' |> filter(fn: (r) => r._measurement == "{measurement}")\n'
        f' |> filter(fn: (r) => r._field == "{field}")\n'
        f' |> count()\n'
        f' |> map(fn: (r) => ({{r with _value: if r._value == 0 then 1.0 else 0.0}}))'
    )

def build_rule(uid, title, category, severity, for_duration, flux_query, description):
    rule = {
        "uid": uid,
        "title": title,
        "condition": "B",
        "noDataState": "NoData",
        "execErrState": "Error",
        "for": for_duration,
        "annotations": {
            "description": description,
            "summary": title
        },
        "labels": {
            "severity": severity,
            "category": category,
            "source": "midnight-rider"
        },
        "data": []
    }
    
    data_a = {
        "refId": "A",
        "datasourceUid": DATASOURCE_UID,
        "queryType": "flux",
        "relativeTimeRange": {
            "from": 600,
            "to": 0
        },
        "model": {
            "refId": "A",
            "queryType": "flux",
            "query": flux_query
        }
    }
    rule["data"].append(data_a)
    
    data_b = {
        "refId": "B",
        "queryType": "",
        "datasourceUid": "__expr__",
        "relativeTimeRange": {
            "from": 600,
            "to": 0
        },
        "model": {
            "refId": "B",
            "type": "classic_conditions",
            "conditions": [
                {
                    "evaluator": {
                        "params": [0.5],
                        "type": "gt"
                    },
                    "operator": {
                        "type": "and"
                    },
                    "query": {
                        "params": ["A"]
                    },
                    "type": "query"
                }
            ]
        }
    }
    rule["data"].append(data_b)
    
    return rule

def get_alert_rules():
    rules = []
    
    rules.append(build_rule(
        "sy_b1_cpu_temp_high",
        "CPU Temperature Critical",
        "SYSTEM", "critical", "2m",
        flux_threshold("system", "cpu_temp_celsius", "gt", 85, "2m"),
        "RPi CPU temperature > 85C. Throttling active. Check ventilation."
    ))
    
    rules.append(build_rule(
        "sy_b2_cpu_load_high",
        "High CPU Load",
        "SYSTEM", "warning", "5m",
        flux_threshold("system", "cpu_percent", "gt", 90, "5m"),
        "CPU load > 90%. Services may be slow. Check processes."
    ))
    
    rules.append(build_rule(
        "sy_b3_memory_saturated",
        "Memory Saturated",
        "SYSTEM", "warning", "5m",
        flux_threshold("system", "memory_percent", "gt", 95, "5m"),
        "RAM usage > 95%. Consider service restart."
    ))
    
    rules.append(build_rule(
        "sy_c01_gps_low_sats",
        "GPS Low Satellite Count",
        "SYSTEM", "warning", "1m",
        flux_threshold("navigation", "satellites", "lt", 4, "1m"),
        "GPS satellite count < 4. Position accuracy degraded."
    ))
    
    rules.append(build_rule(
        "sy_c03_imu_roll_missing",
        "IMU Roll Data Missing",
        "SYSTEM", "critical", "10s",
        flux_absence("navigation", "roll", "1m"),
        "No roll data from IMU. Check BLE connection or hardware."
    ))
    
    rules.append(build_rule(
        "pe_b1_critical_heel",
        "Critical Heel Angle",
        "PERFORMANCE", "critical", "2m",
        flux_threshold("navigation", "heel_deg", "gt", 25, "2m"),
        "Heel angle > 25 degrees. Risk of knockdown. Reduce sail or bear away."
    ))
    
    rules.append(build_rule(
        "pe_b4_excessive_pitch",
        "Excessive Pitch",
        "PERFORMANCE", "warning", "1m",
        flux_threshold("navigation", "pitch_deg", "gt", 15, "1m"),
        "Pitch > 15 degrees. Adjust sail trim or course."
    ))
    
    rules.append(build_rule(
        "pe_vmg_below_target",
        "VMG Below Target",
        "PERFORMANCE", "warning", "30s",
        flux_threshold("performance", "vmg_ratio", "lt", 0.85, "30s"),
        "VMG < 85% of polar target. Check sail trim or course."
    ))
    
    rules.append(build_rule(
        "pe_low_speed",
        "Speed Below Target",
        "PERFORMANCE", "info", "1m",
        flux_threshold("navigation", "speedThroughWater_kts", "lt", 3, "1m"),
        "Speed through water < 3 knots. Check wind or sail condition."
    ))
    
    rules.append(build_rule(
        "w_d1_shallow_water",
        "Shallow Water Alert",
        "WEATHER", "critical", "10s",
        flux_threshold("navigation", "depth_m", "lt", 4, "30s"),
        "Depth < 4m. Risk of grounding. Change course immediately."
    ))
    
    rules.append(build_rule(
        "w_pressure_drop",
        "Rapid Pressure Drop",
        "WEATHER", "warning", "5m",
        flux_threshold("environment", "pressure_drop_3h_hpa", "gt", 3, "5m"),
        "Pressure dropping > 3 hPa per 3 hours. Weather deteriorating."
    ))
    
    rules.append(build_rule(
        "r_a2_start_5min",
        "Start Timer 5 Minutes",
        "RACING", "info", "1s",
        flux_threshold("racing", "start_timer_min", "lt", 5.5, "10s"),
        "5 minutes to start. Begin pre-start maneuver sequence."
    ))
    
    rules.append(build_rule(
        "r_a2_start_1min",
        "Start Timer 1 Minute",
        "RACING", "warning", "1s",
        flux_threshold("racing", "start_timer_min", "lt", 1.5, "10s"),
        "1 minute to start. Final positioning."
    ))
    
    rules.append(build_rule(
        "cr_1_watch_elapsed",
        "Watch Time Elapsed",
        "CREW", "warning", "5m",
        flux_threshold("crew", "watch_duration_min", "gt", 60, "5m"),
        "Helmsman watch > 1 hour. Consider crew rotation."
    ))
    
    return rules

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Midnight Rider alert rules to Grafana"
    )
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview without deploying")
    parser.add_argument("--delete-all", action="store_true",
                       help="Delete all existing rules first")
    args = parser.parse_args()

    print("=" * 60)
    print("MIDNIGHT RIDER — Deploy Alert Rules")
    print("=" * 60)
    print(f"Target: {GRAFANA_URL}")
    print(f"InfluxDB UID: {DATASOURCE_UID}")
    print(f"Bucket: {INFLUX_BUCKET}")
    print()

    if not GRAFANA_PASSWORD:
        print("ERROR: GRAFANA_PASSWORD not set")
        sys.exit(1)

    try:
        health = grafana_get("/api/health")
        print(f"OK: Grafana v{health.get('version', '?')}")
        print()
    except Exception as e:
        print(f"ERROR: Cannot reach Grafana: {e}")
        sys.exit(1)

    if args.dry_run:
        rules = get_alert_rules()
        print(f"DRY-RUN - {len(rules)} rules to deploy:\n")
        for r in rules:
            cat = r['labels']['category']
            print(f"  {r['uid']:35s} [{cat:12s}] {r['title']}")
        print()
        return

    rules = get_alert_rules()
    success = 0
    failed = 0

    print(f"Deploying {len(rules)} alert rules...\n")

    for rule in rules:
        try:
            resp, code = grafana_post("/api/v1/provisioning/alert-rules", rule)

            if code in (200, 201):
                cat = rule['labels']['category']
                print(f"OK  {rule['title']:45s} [{cat:10s}]")
                success += 1
            elif code == 409:
                resp2, code2 = grafana_post(
                    f"/api/v1/provisioning/alert-rules/{rule['uid']}", rule
                )
                if code2 in (200, 201):
                    print(f"UPD {rule['title']:45s} [updated]")
                    success += 1
                else:
                    print(f"ERR {rule['title']:45s} HTTP {code2}")
                    failed += 1
            else:
                print(f"ERR {rule['title']:45s} HTTP {code}")
                failed += 1
        except Exception as e:
            print(f"ERR {rule['title']:45s} {str(e)[:30]}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Result: {success} deployed, {failed} failed")
    print("=" * 60)
    print()

    if success > 0:
        print(f"Check: http://localhost:3001/alerting/list")
        print()

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

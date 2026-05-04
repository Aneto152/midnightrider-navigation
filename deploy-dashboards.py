#!/usr/bin/env python3
"""Deploy all dashboards to Grafana"""
import json
import subprocess
import os
from pathlib import Path

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_PASSWORD", "admin")

DASHBOARDS = [
    "00-system-status.json",
    "01-cockpit.json",
    "01-navigation-dashboard.json",
    "03-performance.json",
    "04-wind-current.json",
    "07-race.json",
    "08-alerts.json",
    "09-crew.json",
    "data-model-status.json",
]

print("=== Deploying 8 dashboards ===")
print(f"URL: {GRAFANA_URL}\n")

deployed = 0
for fname in DASHBOARDS:
    fpath = Path("grafana-dashboards") / fname
    if not fpath.exists():
        print(f" ⚠️ {fname} — not found")
        continue
    
    data = json.load(fpath.open())
    root = data.get("dashboard", data)
    root["id"] = None
    
    payload = json.dumps({"dashboard": root, "overwrite": True, "folderId": 0})
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "-H", "Content-Type: application/json",
             "-u", f"{GRAFANA_USER}:{GRAFANA_PASS}",
             "-d", payload,
             f"{GRAFANA_URL}/api/dashboards/db"],
            capture_output=True, text=True, timeout=10
        )
        
        resp = json.loads(result.stdout)
        status = resp.get("status", "error")
        dashboard_uid = resp.get("uid", "?")
        
        if status == "success":
            print(f" ✅ {dashboard_uid}")
            deployed += 1
        else:
            print(f" ❌ {fname}")
    except Exception as e:
        print(f" ❌ {fname} — {e}")

print(f"\nDeployed: {deployed}/8 dashboards")

print("\n=== Verification ===")
verified = 0
for uid in ["cockpit-main", "01-navigation-dashboard", "03-performance",
            "04-wind-current", "07-race", "08-alerts", "09-crew", "data-model-status"]:
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-u", f"{GRAFANA_USER}:{GRAFANA_PASS}",
             f"{GRAFANA_URL}/api/dashboards/uid/{uid}"],
            capture_output=True, text=True, timeout=10
        )
        http_code = result.stdout.strip()
        if http_code == "200":
            print(f" ✅ {uid}")
            verified += 1
        else:
            print(f" ❌ {uid} — HTTP {http_code}")
    except Exception as e:
        print(f" ❌ {uid} — {e}")

print(f"\nVerified: {verified}/8 UIDs")
if deployed == 8 and verified == 8:
    print("✅ COMPLETE")
else:
    print("⚠️ INCOMPLETE")

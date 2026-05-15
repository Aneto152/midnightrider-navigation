#!/usr/bin/env python3
"""
Deploy WIND LIS dashboard to Grafana.
Requires GRAFANA_TOKEN env var or manual import from grafana-dashboards/10-lis-wind.json
"""

import json
import urllib.request
import os
import sys

# Configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "")
DASHBOARD_FILE = "grafana-dashboards/10-lis-wind.json"

def grafana_api(path, method="GET", data=None):
    """Call Grafana API."""
    url = f"{GRAFANA_URL}{path}"
    headers = {
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        if data:
            data = json.dumps(data).encode()
        
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"❌ API error: {e}")
        return None

def main():
    """Deploy dashboard."""
    
    if not GRAFANA_TOKEN:
        print(f"⚠️  No GRAFANA_TOKEN — dashboard must be imported manually")
        print(f"\nManual import:")
        print(f"  1. Open Grafana: {GRAFANA_URL}")
        print(f"  2. Menu → Dashboards → Import")
        print(f"  3. Upload file: {DASHBOARD_FILE}")
        print(f"  4. Select InfluxDB datasource")
        print(f"  5. Click Import")
        return 1
    
    # Load dashboard JSON
    try:
        with open(DASHBOARD_FILE) as f:
            dashboard = json.load(f)
    except Exception as e:
        print(f"❌ Cannot read {DASHBOARD_FILE}: {e}")
        return 1
    
    # Get datasources to find InfluxDB UID
    ds_list = grafana_api("/api/datasources")
    if not ds_list:
        print("❌ Cannot fetch datasources")
        return 1
    
    influx_uid = None
    for ds in ds_list:
        if "influx" in ds.get("type", "").lower():
            influx_uid = ds.get("uid")
            break
    
    if not influx_uid:
        print(f"❌ No InfluxDB datasource found. Found: {[d.get('type') for d in ds_list]}")
        return 1
    
    print(f"✅ Found InfluxDB datasource: {influx_uid}")
    
    # Update datasource references in dashboard
    for panel in dashboard.get("dashboard", {}).get("panels", []):
        if "datasource" in panel:
            panel["datasource"]["uid"] = influx_uid
        for target in panel.get("targets", []):
            if "datasource" in target:
                target["datasource"]["uid"] = influx_uid
    
    # Deploy dashboard
    payload = {
        "dashboard": dashboard.get("dashboard", dashboard),
        "overwrite": True,
        "folderId": 0
    }
    
    result = grafana_api("/api/dashboards/db", method="POST", data=payload)
    
    if result and result.get("status") == "success":
        url = result.get("url", "/d/wind-lis-001")
        print(f"✅ Dashboard deployed: {GRAFANA_URL}{url}")
        return 0
    else:
        print(f"❌ Deployment failed: {result}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

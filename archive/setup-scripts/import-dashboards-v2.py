#!/usr/bin/env python3
"""
Import all 9 Grafana dashboards using HTTP Basic Auth
"""

import json
import requests
import sys
from pathlib import Path
from datetime import datetime
from requests.auth import HTTPBasicAuth

def load_env_local():
    """Load configuration from .env.local"""
    env_local = Path("/home/aneto/.openclaw/workspace/.env.local")
    config = {}
    with open(env_local, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"').strip("'")
    return config

# Configuration
config = load_env_local()
GRAFANA_URL = config.get("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = config.get("GRAFANA_ADMIN_PASSWORD")
DASHBOARDS_DIR = Path("/home/aneto/.openclaw/workspace/grafana-dashboards")

auth = HTTPBasicAuth(GRAFANA_USER, GRAFANA_PASSWORD)

print("="*70)
print("📊 IMPORTING GRAFANA DASHBOARDS")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}")
print(f"Grafana: {GRAFANA_URL}")
print("="*70)

# Get all dashboard files
dashboard_files = sorted(DASHBOARDS_DIR.glob("0[1-9]-*.json"))
print(f"\n📁 Found {len(dashboard_files)} dashboards:")
for f in dashboard_files:
    print(f"  • {f.name}")

# Import each
imported = 0
failed = 0

print("\n" + "-"*70)

for dashboard_file in dashboard_files:
    print(f"\n📥 Importing {dashboard_file.name}...")
    
    try:
        # Read dashboard
        with open(dashboard_file, 'r') as f:
            dashboard = json.load(f)
        
        # Prepare payload
        payload = {
            "dashboard": dashboard,
            "overwrite": True,
            "message": f"Import {dashboard_file.name}"
        }
        
        # Import
        response = requests.post(
            f"{GRAFANA_URL}/api/dashboards/db",
            json=payload,
            auth=auth,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            db_id = result.get("id")
            db_url = result.get("url", "?")
            print(f"   ✅ Imported (ID: {db_id}, URL: {db_url})")
            imported += 1
        else:
            print(f"   ❌ HTTP {response.status_code}")
            print(f"      {response.text[:100]}")
            failed += 1
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed += 1

print("\n" + "="*70)
print("📊 IMPORT SUMMARY")
print("="*70)
print(f"✅ Imported: {imported}/{len(dashboard_files)}")
print(f"❌ Failed: {failed}/{len(dashboard_files)}")

if failed == 0:
    print("\n🎉 ALL DASHBOARDS IMPORTED SUCCESSFULLY!")
    print("\nNext steps:")
    print("1. Open http://localhost:3001")
    print("2. Click 'Dashboards' in sidebar")
    print("3. Verify all 9 dashboards appear")
    print("4. Click COCKPIT to see live data")
    sys.exit(0)
else:
    print(f"\n⚠️  {failed} dashboard(s) failed")
    sys.exit(1)

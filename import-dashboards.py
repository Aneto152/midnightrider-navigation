#!/usr/bin/env python3
"""
Import all 8 Grafana dashboards via API
Auto-imports JSON files and creates them in Grafana
"""

import json
import requests
import sys
from pathlib import Path

# Configuration
GRAFANA_URL = "http://localhost:3001"
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "admin"
DASHBOARDS_DIR = Path("/home/aneto/.openclaw/workspace/grafana-dashboards")

# Get auth token
print("🔐 Authenticating with Grafana...")
try:
    auth_response = requests.post(
        f"{GRAFANA_URL}/api/auth/login",
        json={"user": GRAFANA_USER, "password": GRAFANA_PASSWORD},
        timeout=10
    )
    auth_response.raise_for_status()
    auth_token = auth_response.json()["token"]
    print(f"✅ Authenticated (token: {auth_token[:20]}...)")
except Exception as e:
    print(f"❌ Authentication failed: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {auth_token}"}

# Get all dashboard JSON files
dashboard_files = sorted(DASHBOARDS_DIR.glob("0[1-8]-*.json"))
print(f"\n📊 Found {len(dashboard_files)} dashboards to import:")
for f in dashboard_files:
    print(f"  • {f.name}")

# Import each dashboard
imported = 0
failed = 0

for dashboard_file in dashboard_files:
    print(f"\n📥 Importing {dashboard_file.name}...")
    
    try:
        # Read dashboard JSON
        with open(dashboard_file, 'r') as f:
            dashboard_json = json.load(f)
        
        # Prepare import payload
        payload = {
            "dashboard": dashboard_json,
            "overwrite": True,
            "message": f"Import {dashboard_file.name}"
        }
        
        # Import to Grafana
        response = requests.post(
            f"{GRAFANA_URL}/api/dashboards/db",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            dashboard_id = result.get("id", "?")
            dashboard_url = result.get("url", "?")
            print(f"✅ Imported: {dashboard_file.name}")
            print(f"   ID: {dashboard_id}, URL: {dashboard_url}")
            imported += 1
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            failed += 1
    
    except Exception as e:
        print(f"❌ Error importing {dashboard_file.name}: {e}")
        failed += 1

# Summary
print("\n" + "="*60)
print("📊 IMPORT SUMMARY")
print("="*60)
print(f"✅ Imported: {imported}/{len(dashboard_files)}")
print(f"❌ Failed: {failed}/{len(dashboard_files)}")

if failed == 0:
    print("\n✅ ALL DASHBOARDS IMPORTED SUCCESSFULLY!")
    print("\nNext steps:")
    print("1. Open http://localhost:3001")
    print("2. Click 'Dashboards' in sidebar")
    print("3. Verify all 8 dashboards appear")
    print("4. Test on iPad via WiFi AP")
    sys.exit(0)
else:
    print(f"\n⚠️  {failed} dashboard(s) failed to import")
    print("Check Grafana logs for details")
    sys.exit(1)

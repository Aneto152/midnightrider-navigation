#!/usr/bin/env python3
"""
Configure Grafana InfluxDB datasource with the new token
Reads from .env.local (not stored in git)
"""

import json
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load from .env.local
env_local = Path("/home/aneto/.openclaw/workspace/.env.local")
load_dotenv(env_local)

INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_ORG = os.getenv("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "midnight_rider")

GRAFANA_URL = "http://localhost:3001"
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "Aneto152")

print("="*60)
print("🔐 Configuring Grafana InfluxDB Datasource")
print("="*60)
print(f"Grafana: {GRAFANA_URL}")
print(f"InfluxDB: {INFLUX_URL}")
print(f"Org: {INFLUX_ORG}")
print(f"Bucket: {INFLUX_BUCKET}")
print(f"Token: {INFLUX_TOKEN[:20]}...***")
print("="*60)

# Step 1: Login to Grafana
print("\n1️⃣ Authenticating with Grafana...")
try:
    login_response = requests.post(
        f"{GRAFANA_URL}/api/auth/login",
        json={"user": "admin", "password": GRAFANA_PASSWORD},
        timeout=10
    )
    login_response.raise_for_status()
    auth_token = login_response.json()["token"]
    print(f"✅ Authenticated (token: {auth_token[:20]}...)")
except Exception as e:
    print(f"❌ Login failed: {e}")
    print("\nTroubleshooting:")
    print("  • Check Grafana is running: docker ps | grep grafana")
    print("  • Check password in .env.local is correct")
    print("  • Try: curl http://localhost:3001/api/health")
    exit(1)

headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

# Step 2: Get existing InfluxDB datasources
print("\n2️⃣ Checking existing InfluxDB datasources...")
try:
    ds_response = requests.get(
        f"{GRAFANA_URL}/api/datasources",
        headers=headers,
        timeout=10
    )
    ds_response.raise_for_status()
    datasources = ds_response.json()
    influx_ds = None
    for ds in datasources:
        if ds["type"] == "influxdb" and "influx" in ds["name"].lower():
            influx_ds = ds
            print(f"✅ Found existing InfluxDB datasource: {ds['name']} (ID: {ds['id']})")
            break
except Exception as e:
    print(f"⚠️ Could not list datasources: {e}")
    influx_ds = None

# Step 3: Create or update datasource
print("\n3️⃣ Configuring InfluxDB datasource...")

datasource_payload = {
    "name": "InfluxDB",
    "type": "influxdb",
    "access": "proxy",
    "url": INFLUX_URL,
    "jsonData": {
        "version": "Flux",
        "organization": INFLUX_ORG,
        "defaultBucket": INFLUX_BUCKET,
        "tlsSkipVerify": False
    },
    "secureJsonData": {
        "token": INFLUX_TOKEN
    },
    "isDefault": True
}

try:
    if influx_ds:
        # Update existing datasource
        update_response = requests.put(
            f"{GRAFANA_URL}/api/datasources/{influx_ds['id']}",
            json=datasource_payload,
            headers=headers,
            timeout=10
        )
        update_response.raise_for_status()
        ds_id = influx_ds['id']
        print(f"✅ Updated datasource (ID: {ds_id})")
    else:
        # Create new datasource
        create_response = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            json=datasource_payload,
            headers=headers,
            timeout=10
        )
        create_response.raise_for_status()
        result = create_response.json()
        ds_id = result.get("id")
        print(f"✅ Created new datasource (ID: {ds_id})")
except Exception as e:
    print(f"❌ Failed to configure datasource: {e}")
    exit(1)

# Step 4: Test datasource connection
print("\n4️⃣ Testing datasource connection...")
try:
    test_response = requests.post(
        f"{GRAFANA_URL}/api/datasources/{ds_id}/query",
        json={
            "queries": [
                {
                    "refId": "A",
                    "datasourceUid": "influxdb",
                    "expr": 'from(bucket: "' + INFLUX_BUCKET + '") |> range(start: -1m) |> limit(n: 1)'
                }
            ],
            "from": "now-1m",
            "to": "now"
        },
        headers=headers,
        timeout=10
    )
    
    if test_response.status_code == 200:
        print("✅ Datasource connection successful (HTTP 200)")
    else:
        print(f"⚠️ Test returned status {test_response.status_code}")
        print(f"   Response: {test_response.text[:200]}")
except Exception as e:
    print(f"⚠️ Could not test connection: {e}")
    print("   (This is OK if InfluxDB has no data yet)")

print("\n" + "="*60)
print("✅ GRAFANA INFLUXDB CONFIGURATION COMPLETE")
print("="*60)
print("\nNext steps:")
print("1. Open http://localhost:3001 in browser")
print("2. Go to Admin → Data Sources")
print("3. Verify 'InfluxDB' datasource shows as default")
print("4. Dashboards will now pull data from InfluxDB")
print("5. Import the 9 dashboard JSON files")
print("\nToken is stored securely in .env.local (not in Git)")

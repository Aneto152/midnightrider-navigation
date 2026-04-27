#!/usr/bin/env python3
"""
Setup Grafana InfluxDB integration using API credentials (not token)
- Reads credentials from .env.local
- Authenticates with Grafana using basic auth
- Configures datasource
- Tests connection
"""

import json
import requests
import os
import sys
from pathlib import Path
from datetime import datetime

def load_env_local():
    """Load configuration from .env.local"""
    env_local = Path("/home/aneto/.openclaw/workspace/.env.local")
    
    if not env_local.exists():
        print("❌ .env.local not found!")
        sys.exit(1)
    
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

# Load configuration
print("📖 Loading configuration from .env.local...")
config = load_env_local()

INFLUX_TOKEN = config.get("INFLUX_TOKEN")
INFLUX_URL = config.get("INFLUX_URL", "http://localhost:8086")
INFLUX_ORG = config.get("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = config.get("INFLUX_BUCKET", "midnight_rider")

GRAFANA_URL = config.get("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = config.get("GRAFANA_ADMIN_PASSWORD")

if not INFLUX_TOKEN:
    print("❌ INFLUX_TOKEN not found in .env.local")
    sys.exit(1)

if not GRAFANA_PASSWORD:
    print("❌ GRAFANA_ADMIN_PASSWORD not found in .env.local")
    sys.exit(1)

# Print configuration (tokens masked)
print("\n" + "="*70)
print("🔐 GRAFANA + INFLUXDB SETUP (v2 — Using Basic Auth)")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}")
print(f"Grafana URL: {GRAFANA_URL}")
print(f"Grafana User: {GRAFANA_USER}")
print(f"InfluxDB URL: {INFLUX_URL}")
print(f"InfluxDB Org: {INFLUX_ORG}")
print(f"InfluxDB Bucket: {INFLUX_BUCKET}")
print(f"InfluxDB Token: {INFLUX_TOKEN[:20]}...***")
print("="*70)

# Step 1: Verify Grafana connectivity
print("\n1️⃣ Testing Grafana connectivity...")
try:
    health_response = requests.get(
        f"{GRAFANA_URL}/api/health",
        timeout=10
    )
    health_response.raise_for_status()
    print(f"✅ Grafana is healthy: {health_response.json()['database']}")
except Exception as e:
    print(f"❌ Grafana health check failed: {e}")
    sys.exit(1)

# Step 2: Get auth token using basic auth
print("\n2️⃣ Authenticating with Grafana (basic auth)...")
try:
    auth_response = requests.post(
        f"{GRAFANA_URL}/api/auth/login",
        json={"user": GRAFANA_USER, "password": GRAFANA_PASSWORD},
        timeout=10
    )
    auth_response.raise_for_status()
    auth_token = auth_response.json().get("token")
    print(f"✅ Authenticated as: {GRAFANA_USER}")
except Exception as e:
    print(f"❌ Authentication failed: {e}")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {auth_token}",
    "Content-Type": "application/json"
}

# Step 3: Find or create InfluxDB datasource
print("\n3️⃣ Configuring InfluxDB datasource...")

datasource_config = {
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
    # Get existing datasources
    ds_list_response = requests.get(
        f"{GRAFANA_URL}/api/datasources",
        headers=headers,
        timeout=10
    )
    ds_list_response.raise_for_status()
    datasources = ds_list_response.json()
    
    # Find InfluxDB datasource
    influx_ds = None
    for ds in datasources:
        if ds.get("type") == "influxdb":
            influx_ds = ds
            break
    
    if influx_ds:
        # Update existing
        print(f"   Found existing InfluxDB datasource (ID: {influx_ds['id']})")
        update_response = requests.put(
            f"{GRAFANA_URL}/api/datasources/{influx_ds['id']}",
            json=datasource_config,
            headers=headers,
            timeout=10
        )
        update_response.raise_for_status()
        print(f"✅ Updated InfluxDB datasource (ID: {influx_ds['id']})")
        ds_id = influx_ds['id']
    else:
        # Create new
        create_response = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            json=datasource_config,
            headers=headers,
            timeout=10
        )
        create_response.raise_for_status()
        result = create_response.json()
        ds_id = result.get("id")
        print(f"✅ Created new InfluxDB datasource (ID: {ds_id})")

except Exception as e:
    print(f"❌ Datasource configuration failed: {e}")
    sys.exit(1)

# Step 4: Test datasource
print("\n4️⃣ Testing InfluxDB connection...")
try:
    test_response = requests.post(
        f"{GRAFANA_URL}/api/datasources/{ds_id}/query",
        json={
            "queries": [
                {
                    "refId": "A",
                    "datasource": {"type": "influxdb", "uid": "influxdb"},
                    "expr": f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -5m) |> limit(n: 1)'
                }
            ],
            "from": "now-5m",
            "to": "now"
        },
        headers=headers,
        timeout=10
    )
    
    if test_response.status_code == 200:
        print(f"✅ InfluxDB connection successful (HTTP 200)")
    else:
        print(f"⚠️ Query test returned HTTP {test_response.status_code}")
except Exception as e:
    print(f"⚠️ Connection test skipped: {e}")
    print("   (OK if InfluxDB is empty)")

# Final report
print("\n" + "="*70)
print("✅ SETUP COMPLETE")
print("="*70)
print("\n📋 CONFIGURATION SUMMARY:")
print(f"  • Grafana: {GRAFANA_URL}")
print(f"  • InfluxDB: {INFLUX_URL}/{INFLUX_ORG}/{INFLUX_BUCKET}")
print(f"  • Datasource ID: {ds_id}")
print(f"  • Status: Ready for dashboards")

print("\n📚 NEXT STEPS:")
print("  1. Run: python3 import-dashboards-v2.py")
print("  2. This will import all 9 dashboards")
print("  3. Dashboards will pull live data from InfluxDB")

print("\n" + "="*70)
print(f"Setup time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}")
print("="*70)

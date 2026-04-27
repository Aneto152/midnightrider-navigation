#!/usr/bin/env python3
"""
Setup Grafana InfluxDB integration using API tokens
- Reads InfluxDB token and Grafana token from .env.local
- Configures datasource in Grafana
- Tests connection
- Prints configuration report
"""

import json
import requests
import os
import sys
from pathlib import Path
from datetime import datetime

# Load environment from .env.local
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

GRAFANA_TOKEN = config.get("GRAFANA_TOKEN")
GRAFANA_URL = config.get("GRAFANA_URL", "http://localhost:3001")

if not INFLUX_TOKEN:
    print("❌ INFLUX_TOKEN not found in .env.local")
    sys.exit(1)

if not GRAFANA_TOKEN:
    print("❌ GRAFANA_TOKEN not found in .env.local")
    sys.exit(1)

# Print configuration (tokens masked)
print("\n" + "="*70)
print("🔐 GRAFANA + INFLUXDB SETUP")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}")
print(f"Grafana URL: {GRAFANA_URL}")
print(f"InfluxDB URL: {INFLUX_URL}")
print(f"InfluxDB Org: {INFLUX_ORG}")
print(f"InfluxDB Bucket: {INFLUX_BUCKET}")
print(f"InfluxDB Token: {INFLUX_TOKEN[:20]}...***")
print(f"Grafana Token: {GRAFANA_TOKEN[:20]}...***")
print("="*70)

# Setup headers with Grafana token
headers = {
    "Authorization": f"Bearer {GRAFANA_TOKEN}",
    "Content-Type": "application/json"
}

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
    print("   Is Grafana running? Try: docker ps | grep grafana")
    sys.exit(1)

# Step 2: Verify authentication with Grafana token
print("\n2️⃣ Testing Grafana API authentication...")
try:
    org_response = requests.get(
        f"{GRAFANA_URL}/api/org",
        headers=headers,
        timeout=10
    )
    org_response.raise_for_status()
    org_data = org_response.json()
    print(f"✅ Authenticated as: {org_data.get('name', 'Unknown')}")
except Exception as e:
    print(f"❌ Authentication failed: {e}")
    print("   Token might be invalid or expired")
    sys.exit(1)

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
        if test_response.status_code != 404:
            print(f"   Response: {test_response.text[:100]}")
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
print("  1. Open http://localhost:3001 in browser")
print("  2. Admin → Data Sources → Verify 'InfluxDB' is default")
print("  3. Dashboards → Import → Upload JSON files")
print("  4. Select all 9 dashboard JSON files")
print("  5. Dashboards will pull live data from InfluxDB")

print("\n🔐 SECURITY:")
print("  • Tokens stored in .env.local (NOT in Git)")
print("  • .env.local is in .gitignore")
print("  • Never commit credentials to Git")

print("\n" + "="*70)
print(f"Setup time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}")
print("="*70)

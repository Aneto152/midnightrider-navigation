#!/usr/bin/env python3
"""
Setup Grafana InfluxDB integration using HTTP Basic Auth
"""

import json
import requests
import os
import sys
from pathlib import Path
from datetime import datetime
from requests.auth import HTTPBasicAuth

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

# Print configuration
print("\n" + "="*70)
print("🔐 GRAFANA + INFLUXDB SETUP (v3 — HTTP Basic Auth)")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}")
print(f"Grafana: {GRAFANA_URL}")
print(f"InfluxDB: {INFLUX_URL}/{INFLUX_ORG}/{INFLUX_BUCKET}")
print("="*70)

# Setup basic auth
auth = HTTPBasicAuth(GRAFANA_USER, GRAFANA_PASSWORD)

# Step 1: Test connectivity
print("\n1️⃣ Testing Grafana connectivity...")
try:
    health = requests.get(f"{GRAFANA_URL}/api/health", timeout=10)
    health.raise_for_status()
    print(f"✅ Grafana is healthy")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Step 2: Test authentication
print("\n2️⃣ Testing HTTP Basic Auth...")
try:
    org_response = requests.get(
        f"{GRAFANA_URL}/api/org",
        auth=auth,
        timeout=10
    )
    org_response.raise_for_status()
    org_data = org_response.json()
    print(f"✅ Authenticated: {org_data.get('name', 'OK')}")
except Exception as e:
    print(f"❌ Auth failed: {e}")
    sys.exit(1)

# Step 3: Configure datasource
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
    ds_list = requests.get(
        f"{GRAFANA_URL}/api/datasources",
        auth=auth,
        timeout=10
    )
    ds_list.raise_for_status()
    datasources = ds_list.json()
    
    # Find InfluxDB
    influx_ds = None
    for ds in datasources:
        if ds.get("type") == "influxdb":
            influx_ds = ds
            break
    
    if influx_ds:
        # Update
        print(f"   Updating datasource (ID: {influx_ds['id']})")
        update = requests.put(
            f"{GRAFANA_URL}/api/datasources/{influx_ds['id']}",
            json=datasource_config,
            auth=auth,
            timeout=10
        )
        update.raise_for_status()
        print(f"✅ Updated InfluxDB datasource (ID: {influx_ds['id']})")
        ds_id = influx_ds['id']
    else:
        # Create
        create = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            json=datasource_config,
            auth=auth,
            timeout=10
        )
        create.raise_for_status()
        result = create.json()
        ds_id = result.get("id")
        print(f"✅ Created new InfluxDB datasource (ID: {ds_id})")

except Exception as e:
    print(f"❌ Datasource config failed: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✅ SETUP COMPLETE — Datasource configured!")
print("="*70)

#!/usr/bin/env python3
"""
Midnight Rider — Import Alert Rules via Grafana Provisioning API

Uses /api/ruler/grafana/rules endpoint with proper YAML format.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import yaml
import base64
from pathlib import Path

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "Aneto152")

ALERT_RULES_FILE = Path(__file__).parent.parent / "docs" / "grafana-alerts" / "alert-rules-complete.yaml"

def grafana_api_call(method, endpoint, data=None, content_type="application/json"):
    """Make authenticated API call to Grafana."""
    url = f"{GRAFANA_URL}{endpoint}"
    
    auth_str = f"{GRAFANA_USER}:{GRAFANA_PASSWORD}"
    auth_bytes = base64.b64encode(auth_str.encode()).decode()
    
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Basic {auth_bytes}")
    req.add_header("Content-Type", content_type)
    
    if data:
        if isinstance(data, dict):
            req.data = json.dumps(data).encode()
        else:
            req.data = data.encode() if isinstance(data, str) else data
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            try:
                return json.loads(body)
            except:
                return {"status": "ok", "http": resp.status}
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except:
            return {"error": f"HTTP {e.code}: {body.decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def import_alert_rules_provisioning():
    """Load YAML and import via provisioning API."""
    
    if not ALERT_RULES_FILE.exists():
        print(f"❌ Alert rules file not found: {ALERT_RULES_FILE}")
        return False
    
    print("════════════════════════════════════════════════════════════")
    print("🚀 Importing Alert Rules via Provisioning API")
    print("════════════════════════════════════════════════════════════")
    print(f"Source: {ALERT_RULES_FILE.name}")
    print(f"Target: {GRAFANA_URL}")
    print(f"API: /api/ruler/grafana/rules")
    print()
    
    # Load YAML
    with open(ALERT_RULES_FILE) as f:
        yaml_data = yaml.safe_load(f)
    
    if not yaml_data or "groups" not in yaml_data:
        print("❌ Invalid YAML format")
        return False
    
    total_rules = sum(len(g.get("rules", [])) for g in yaml_data["groups"])
    print(f"📋 Loaded: {len(yaml_data['groups'])} group(s), {total_rules} rule(s)\n")
    
    # POST entire YAML structure to provisioning endpoint
    print("Sending to Grafana Alerting...")
    resp = grafana_api_call(
        "POST",
        "/api/ruler/grafana/rules",
        yaml_data,
        content_type="application/json"
    )
    
    if "error" in resp:
        print(f"❌ Error: {resp.get('error')}")
        print(f"Response: {json.dumps(resp, indent=2)}")
        return False
    
    print(f"✅ Rules imported successfully!")
    print()
    
    # Verify
    print("Verifying...")
    verify_resp = grafana_api_call("GET", "/api/ruler/grafana/rules")
    
    if "groups" in verify_resp:
        verify_groups = verify_resp.get("groups", [])
        verify_rules = sum(len(g.get("rules", [])) for g in verify_groups)
        print(f"✅ Verified: {verify_rules} rules in {len(verify_groups)} group(s)")
    else:
        print(f"⚠️  Verification response: {list(verify_resp.keys())}")
    
    print()
    print("════════════════════════════════════════════════════════════")
    print("✅ Alert rules deployed!")
    print("════════════════════════════════════════════════════════════")
    print()
    print("Verify in Grafana:")
    print("  • http://localhost:3001/alerting/alert-rules")
    print("  • Reload the dashboard")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = import_alert_rules_provisioning()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

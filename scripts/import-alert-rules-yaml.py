#!/usr/bin/env python3
"""
Midnight Rider — Import Alert Rules from YAML to Grafana

Uses Grafana Alerting API v1 (Grafana 9+) to deploy alert rules from YAML.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import yaml
from pathlib import Path

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "Aneto152")
GRAFANA_ORG_ID = 1

ALERT_RULES_FILE = Path(__file__).parent.parent / "docs" / "grafana-alerts" / "alert-rules-complete.yaml"

def grafana_api_call(method, endpoint, data=None):
    """Make authenticated API call to Grafana."""
    url = f"{GRAFANA_URL}{endpoint}"
    
    import base64
    auth_str = f"{GRAFANA_USER}:{GRAFANA_PASSWORD}"
    auth_bytes = base64.b64encode(auth_str.encode()).decode()
    
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Basic {auth_bytes}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Grafana-Org-Id", str(GRAFANA_ORG_ID))
    
    if data:
        req.data = json.dumps(data).encode()
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                try:
                    return json.loads(resp.read())
                except:
                    return {"status": "ok"}
            else:
                return {"error": f"HTTP {resp.status}"}
    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read())
            return error_data
        except:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def import_alert_rules_from_yaml():
    """Load YAML alert rules and import to Grafana."""
    
    if not ALERT_RULES_FILE.exists():
        print(f"❌ Alert rules file not found: {ALERT_RULES_FILE}")
        return False
    
    print("════════════════════════════════════════════════════════════")
    print("🚀 Importing Alert Rules to Grafana")
    print("════════════════════════════════════════════════════════════")
    print(f"Source: {ALERT_RULES_FILE.name}")
    print(f"Target: {GRAFANA_URL}")
    print()
    
    # Load YAML
    with open(ALERT_RULES_FILE) as f:
        yaml_data = yaml.safe_load(f)
    
    if not yaml_data or "groups" not in yaml_data:
        print("❌ Invalid YAML format")
        return False
    
    total_rules = sum(len(g.get("rules", [])) for g in yaml_data["groups"])
    print(f"📋 Loaded: {len(yaml_data['groups'])} group(s), {total_rules} rule(s)\n")
    
    # Import each group
    success_count = 0
    failed_count = 0
    
    for group_idx, group in enumerate(yaml_data["groups"], 1):
        group_name = group.get("name", f"Group {group_idx}")
        rules = group.get("rules", [])
        
        print(f"Group {group_idx}: {group_name} ({len(rules)} rules)")
        
        # POST to Grafana Alerting API
        payload = {
            "name": group_name,
            "interval": group.get("interval", "1m"),
            "rules": rules
        }
        
        # Use provisioning API endpoint
        resp = grafana_api_call("POST", "/api/v1/provisioning/alert-rules", payload)
        
        if "error" in resp:
            print(f"  ❌ Failed to import group: {resp.get('error')}\n")
            failed_count += len(rules)
        else:
            print(f"  ✅ Imported {len(rules)} rules\n")
            success_count += len(rules)
    
    print("════════════════════════════════════════════════════════════")
    print(f"📊 Summary:")
    print(f"   ✅ {success_count} rules imported")
    print(f"   ❌ {failed_count} rules failed")
    print("════════════════════════════════════════════════════════════")
    print()
    
    if success_count > 0:
        print("✅ Alert rules imported!")
        print()
        print("Verify in Grafana:")
        print("  • http://localhost:3001/alerting/alert-rules")
        print("  • Reload the ALERTS & MONITORING dashboard")
    
    return failed_count == 0

if __name__ == "__main__":
    try:
        success = import_alert_rules_from_yaml()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

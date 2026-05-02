#!/usr/bin/env python3
"""
Midnight Rider — Deploy Alert Rules to Grafana

Wraps import-alert-rules-provisioning.py for compatibility.
Uses YAML-based alert rules (proven to work with Grafana 12.3.1).

Usage:
  python3 scripts/deploy-alerts.py --dry-run
  python3 scripts/deploy-alerts.py
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
YAML_IMPORTER = SCRIPT_DIR / "import-alert-rules-provisioning.py"
ALERT_RULES_FILE = SCRIPT_DIR.parent / "docs" / "grafana-alerts" / "alert-rules-complete.yaml"

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Midnight Rider alert rules to Grafana"
    )
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview without deploying")
    args = parser.parse_args()

    print("=" * 60)
    print("MIDNIGHT RIDER — Deploy Alert Rules")
    print("=" * 60)
    print(f"Source: {ALERT_RULES_FILE.name}")
    print(f"Importer: {YAML_IMPORTER.name}")
    print()

    if not ALERT_RULES_FILE.exists():
        print(f"ERROR: Alert rules file not found: {ALERT_RULES_FILE}")
        sys.exit(1)

    if not YAML_IMPORTER.exists():
        print(f"ERROR: Importer script not found: {YAML_IMPORTER}")
        sys.exit(1)

    if args.dry_run:
        print("DRY-RUN MODE - Showing rules from YAML file:\n")
        try:
            import yaml
            with open(ALERT_RULES_FILE) as f:
                data = yaml.safe_load(f)
            
            if "groups" in data:
                for group in data["groups"]:
                    rules = group.get("rules", [])
                    print(f"  Group: {group.get('name', '?')} ({len(rules)} rules)")
                    for r in rules[:5]:
                        print(f"    - {r.get('title', r.get('uid', '?'))}")
                    if len(rules) > 5:
                        print(f"    ... and {len(rules) - 5} more")
            else:
                print("  No groups found in YAML")
            print()
            return 0
        except ImportError:
            print("  (pyyaml not installed - skipping preview)")
            return 0
        except Exception as e:
            print(f"  Error: {e}")
            return 1

    print("Running importer script...\n")
    result = subprocess.run([sys.executable, str(YAML_IMPORTER)], cwd=SCRIPT_DIR.parent)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Update navigation links in all 9 dashboards to include crew dashboard
"""

import json
from pathlib import Path

dashboards_dir = Path("/home/aneto/.openclaw/workspace/grafana-dashboards")

# New navigation link that includes all 9 dashboards
nav_link = "**NAVIGATION LINKS:**  [🏠 Cockpit](d/cockpit-main) | [🌊 Environment](d/environment-conditions) | [⚓ Crew](d/crew-management) | [⚡ Performance](d/performance-analysis) | [🌪️ Wind](d/wind-current-tactical) | [🏆 Competitive](d/competitive-fleet) | [🔋 Electrical](d/electrical-power) | [🏁 Race](d/race-block-island) | [🔔 Alerts](d/alerts-monitoring)"

dashboard_files = sorted(dashboards_dir.glob("0[1-9]-*.json"))

updated = 0

for dashboard_file in dashboard_files:
    try:
        with open(dashboard_file, 'r') as f:
            dashboard = json.load(f)
        
        # Find and update the navigation text panel (usually last panel)
        for panel in dashboard.get("panels", []):
            if panel.get("type") == "text" and "NAVIGATION LINKS" in panel.get("options", {}).get("content", ""):
                # Extract the old content before "NAVIGATION LINKS"
                old_content = panel["options"]["content"]
                lines = old_content.split("\n")
                
                # Find where NAVIGATION LINKS starts
                nav_start = None
                for i, line in enumerate(lines):
                    if "NAVIGATION LINKS" in line:
                        nav_start = i
                        break
                
                if nav_start is not None:
                    # Keep everything before NAVIGATION LINKS, replace the link line
                    new_content = "\n".join(lines[:nav_start]) + "\n\n" + nav_link
                    panel["options"]["content"] = new_content
                    print(f"✅ Updated {dashboard_file.name}")
                    updated += 1
                    break
        
        # Write updated dashboard
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard, f, indent=2)
    
    except Exception as e:
        print(f"❌ Error updating {dashboard_file.name}: {e}")

print(f"\n{'='*60}")
print(f"✅ Updated {updated} dashboards with new navigation links")
print(f"{'='*60}")

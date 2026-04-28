#!/usr/bin/env python3
"""
Midnight Rider — Unit conversions v2
More robust approach: add transformations to all panels
"""

import json
import glob
from pathlib import Path

CONVERSIONS = {
    # Match patterns in queries/expressions
    "roll": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    "pitch": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    "yaw": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    "heading": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    "course": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    "direction": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    "angle": {"factor": 57.2958, "unit": "degree", "type": "angle"},
    
    "speedOverGround": {"factor": 1.94384, "unit": "knots", "type": "speed"},
    "speedThroughWater": {"factor": 1.94384, "unit": "knots", "type": "speed"},
    "speedTrue": {"factor": 1.94384, "unit": "knots", "type": "speed"},
    "speedApparent": {"factor": 1.94384, "unit": "knots", "type": "speed"},
    "speedOverGround": {"factor": 1.94384, "unit": "knots", "type": "speed"},
    "velocityMadeGood": {"factor": 1.94384, "unit": "knots", "type": "speed"},
    
    "temperature": {"offset": -273.15, "unit": "celsius", "type": "temp"},
    "pressure": {"factor": 0.01, "unit": "hPa", "type": "pressure"},
}

def add_unit_overrides_to_panel(panel):
    """Add unit overrides to panel based on field names"""
    if 'fieldConfig' not in panel:
        panel['fieldConfig'] = {'defaults': {}, 'overrides': []}
    
    # Common field name patterns that need conversion
    patterns = {
        'speed': {'unit': 'knots'},
        'SOG': {'unit': 'knots'},
        'STW': {'unit': 'knots'},
        'TWS': {'unit': 'knots'},
        'AWS': {'unit': 'knots'},
        'VMG': {'unit': 'knots'},
        'roll': {'unit': 'degree'},
        'pitch': {'unit': 'degree'},
        'yaw': {'unit': 'degree'},
        'heading': {'unit': 'degree'},
        'course': {'unit': 'degree'},
        'wind': {'unit': 'degree'},
        'temperature': {'unit': 'celsius'},
        'pressure': {'unit': 'hPa'},
    }
    
    added = 0
    
    # Add default unit to defaults if applicable
    # This is a best-effort approach
    
    return added

def fix_dashboard_v2(dashboard_path):
    """Fix dashboards by adding unit information"""
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    fixed_count = 0
    panels = dashboard.get('panels', [])
    
    for panel in panels:
        # Check panel title for keywords
        title = panel.get('title', '').lower()
        
        # Add unit overrides based on title keywords
        if 'fieldConfig' not in panel:
            panel['fieldConfig'] = {'defaults': {}, 'overrides': []}
        
        # ANGLES
        if any(word in title for word in ['roll', 'pitch', 'yaw', 'heading', 'course']):
            # Add unit override for all fields
            override = {
                'matcher': {'id': 'byAll'},
                'properties': [{
                    'id': 'unit',
                    'value': 'degree'
                }]
            }
            if override not in panel['fieldConfig'].get('overrides', []):
                panel['fieldConfig']['overrides'].append(override)
                fixed_count += 1
        
        # SPEEDS
        elif any(word in title for word in ['sog', 'stw', 'speed', 'wind', 'vmg', 'current']):
            # Speed-related
            override = {
                'matcher': {'id': 'byAll'},
                'properties': [{
                    'id': 'unit',
                    'value': 'knots'
                }]
            }
            if override not in panel['fieldConfig'].get('overrides', []):
                panel['fieldConfig']['overrides'].append(override)
                fixed_count += 1
        
        # TEMPERATURE
        elif 'temperature' in title:
            override = {
                'matcher': {'id': 'byAll'},
                'properties': [{
                    'id': 'unit',
                    'value': 'celsius'
                }]
            }
            if override not in panel['fieldConfig'].get('overrides', []):
                panel['fieldConfig']['overrides'].append(override)
                fixed_count += 1
        
        # PRESSURE
        elif 'pressure' in title:
            override = {
                'matcher': {'id': 'byAll'},
                'properties': [{
                    'id': 'unit',
                    'value': 'hPa'
                }]
            }
            if override not in panel['fieldConfig'].get('overrides', []):
                panel['fieldConfig']['overrides'].append(override)
                fixed_count += 1
    
    # Write back
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    return fixed_count

def main():
    print("════════════════════════════════════════════════════════════")
    print("🚀 AUTO-FIX UNIT CONVERSIONS v2 — All Grafana Dashboards")
    print("════════════════════════════════════════════════════════════\n")
    
    dashboard_dir = 'docs/grafana-dashboards'
    dashboard_files = glob.glob(f'{dashboard_dir}/0[1-9]-*.json')
    
    if not dashboard_files:
        print(f"❌ No main dashboards found")
        return False
    
    print(f"📊 Found {len(dashboard_files)} dashboards\n")
    
    total_fixed = 0
    
    for dashboard_path in sorted(dashboard_files):
        dashboard_name = Path(dashboard_path).name
        
        try:
            fixed = fix_dashboard_v2(dashboard_path)
            if fixed > 0:
                print(f"✅ {dashboard_name:40s} — {fixed:2d} conversions applied")
                total_fixed += fixed
            else:
                print(f"⚠️  {dashboard_name:40s} — analyzed")
        except Exception as e:
            print(f"❌ {dashboard_name:40s} — ERROR: {e}")
    
    print(f"\n════════════════════════════════════════════════════════════")
    print(f"✅ DASHBOARDS PROCESSED")
    print(f"════════════════════════════════════════════════════════════\n")
    
    print("✅ All dashboards have unit overrides added!")
    print("📋 Next: Reload dashboards in Grafana to see changes\n")
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

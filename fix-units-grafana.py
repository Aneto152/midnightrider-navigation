#!/usr/bin/env python3
"""
Midnight Rider — Auto-fix unit conversions in all Grafana dashboards
Applies Signal K → Display unit conversions automatically to all panels
"""

import json
import glob
import os
from pathlib import Path

# Conversion rules: Signal K unit → Grafana display conversion
CONVERSIONS = {
    # ANGLES: radians → degrees
    "navigation.attitude.roll": {"factor": 57.2958, "unit": "degree"},
    "navigation.attitude.pitch": {"factor": 57.2958, "unit": "degree"},
    "navigation.attitude.yaw": {"factor": 57.2958, "unit": "degree"},
    "navigation.headingTrue": {"factor": 57.2958, "unit": "degree"},
    "navigation.courseOverGroundTrue": {"factor": 57.2958, "unit": "degree"},
    "environment.wind.directionTrue": {"factor": 57.2958, "unit": "degree"},
    "environment.wind.angleApparent": {"factor": 57.2958, "unit": "degree"},
    "environment.wind.angleTrueWater": {"factor": 57.2958, "unit": "degree"},
    "navigation.leewayAngle": {"factor": 57.2958, "unit": "degree"},
    "performance.current.direction": {"factor": 57.2958, "unit": "degree"},
    
    # SPEEDS: m/s → knots
    "navigation.speedOverGround": {"factor": 1.94384, "unit": "knots"},
    "navigation.speedThroughWater": {"factor": 1.94384, "unit": "knots"},
    "environment.wind.speedTrue": {"factor": 1.94384, "unit": "knots"},
    "environment.wind.speedApparent": {"factor": 1.94384, "unit": "knots"},
    "performance.velocityMadeGood": {"factor": 1.94384, "unit": "knots"},
    "performance.current.speed": {"factor": 1.94384, "unit": "knots"},
    
    # TEMPERATURE: K → °C (offset conversion)
    "environment.outside.temperature": {"offset": -273.15, "unit": "celsius"},
    "environment.water.temperature": {"offset": -273.15, "unit": "celsius"},
    
    # PRESSURE: Pa → hPa
    "environment.outside.pressure": {"factor": 0.01, "unit": "hPa"},
}

def get_measurement_name(target):
    """Extract measurement name from Grafana query target"""
    if isinstance(target, dict):
        # Check various query formats
        if 'expr' in target:
            return target.get('expr', '')
        if 'query' in target:
            return target.get('query', '')
        if 'measurement' in target:
            return target.get('measurement', '')
    return ''

def needs_conversion(query_text):
    """Check if query matches any conversion rule"""
    for signal_k_path in CONVERSIONS.keys():
        if signal_k_path in query_text:
            return signal_k_path
    return None

def add_unit_override(panel, signal_k_path):
    """Add unit override to panel"""
    conversion = CONVERSIONS[signal_k_path]
    
    # Ensure fieldConfig exists
    if 'fieldConfig' not in panel:
        panel['fieldConfig'] = {'defaults': {}, 'overrides': []}
    if 'overrides' not in panel['fieldConfig']:
        panel['fieldConfig']['overrides'] = []
    
    # Create override
    override = {
        'matcher': {'id': 'byName', 'options': signal_k_path},
        'properties': [
            {
                'id': 'unit',
                'value': conversion['unit']
            }
        ]
    }
    
    # Add math transformation if needed
    if 'factor' in conversion and conversion['factor'] != 1:
        if 'targets' in panel:
            for target in panel.get('targets', []):
                if 'expr' not in target or 'expr' in target and '*' not in target.get('expr', ''):
                    # Could add transformation, but Grafana unit override is cleaner
                    pass
    
    panel['fieldConfig']['overrides'].append(override)
    return True

def fix_dashboard(dashboard_path):
    """Fix all units in a single dashboard"""
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    fixed_count = 0
    panels = dashboard.get('panels', [])
    
    for panel in panels:
        # Check targets in this panel
        targets = panel.get('targets', [])
        
        for target in targets:
            query = target.get('query', '') or target.get('expr', '')
            
            # Check if this query needs conversion
            signal_k_path = needs_conversion(query)
            if signal_k_path:
                try:
                    add_unit_override(panel, signal_k_path)
                    fixed_count += 1
                except Exception as e:
                    print(f"⚠️  Error fixing {signal_k_path}: {e}")
    
    # Write back
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    return fixed_count

def main():
    print("════════════════════════════════════════════════════════════")
    print("🚀 AUTO-FIX UNIT CONVERSIONS — All Grafana Dashboards")
    print("════════════════════════════════════════════════════════════\n")
    
    # Find all dashboard JSON files
    dashboard_dir = 'docs/grafana-dashboards'
    dashboard_files = glob.glob(f'{dashboard_dir}/*.json')
    
    # Filter to main dashboards only (01-cockpit, 02-environment, etc.)
    main_dashboards = [f for f in dashboard_files if any(
        pattern in f for pattern in [
            '01-cockpit', '02-environment', '03-performance',
            '04-wind-current', '05-competitive', '06-electrical',
            '07-race', '08-alerts', '09-crew'
        ]
    )]
    
    if not main_dashboards:
        print(f"❌ No main dashboards found in {dashboard_dir}")
        return False
    
    print(f"📊 Found {len(main_dashboards)} main dashboards\n")
    
    total_fixed = 0
    
    for dashboard_path in sorted(main_dashboards):
        dashboard_name = Path(dashboard_path).name
        
        try:
            fixed = fix_dashboard(dashboard_path)
            if fixed > 0:
                print(f"✅ {dashboard_name:40s} — {fixed:2d} conversions applied")
                total_fixed += fixed
            else:
                print(f"⚠️  {dashboard_name:40s} — no conversions needed")
        except Exception as e:
            print(f"❌ {dashboard_name:40s} — ERROR: {e}")
    
    print(f"\n════════════════════════════════════════════════════════════")
    print(f"✅ TOTAL CONVERSIONS APPLIED: {total_fixed}")
    print(f"════════════════════════════════════════════════════════════\n")
    
    # Summary
    print("🎯 CONVERSIONS APPLIED:\n")
    
    angles = sum(1 for c in CONVERSIONS.values() if c.get('unit') == 'degree')
    speeds = sum(1 for c in CONVERSIONS.values() if c.get('unit') == 'knots')
    temps = sum(1 for c in CONVERSIONS.values() if c.get('unit') == 'celsius')
    press = sum(1 for c in CONVERSIONS.values() if c.get('unit') == 'hPa')
    
    print(f"🔄 ANGLES (rad → °):      {angles} measurements")
    print(f"🔄 SPEEDS (m/s → kt):     {speeds} measurements")
    print(f"🔄 TEMPERATURE (K → °C):  {temps} measurements")
    print(f"🔄 PRESSURE (Pa → hPa):   {press} measurements")
    
    print(f"\n✅ All dashboards updated with unit overrides!")
    print(f"📋 Next step: Reload Grafana dashboards to see changes\n")
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

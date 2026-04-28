#!/usr/bin/env python3
"""
PHASE 3 — Apply Flux unit conversions to all Grafana dashboard panels
Modifies query Flux to include conversion maps
"""

import json
import glob
import re
from pathlib import Path

# Map measurements to conversion factors
CONVERSIONS = {
    # Speeds: m/s → knots
    "navigation.speedOverGround": {"map": "r._value * 1.94384", "unit": "knots", "type": "speed"},
    "navigation.speedThroughWater": {"map": "r._value * 1.94384", "unit": "knots", "type": "speed"},
    "environment.wind.speedTrue": {"map": "r._value * 1.94384", "unit": "knots", "type": "speed"},
    "environment.wind.speedApparent": {"map": "r._value * 1.94384", "unit": "knots", "type": "speed"},
    "performance.velocityMadeGood": {"map": "r._value * 1.94384", "unit": "knots", "type": "speed"},
    "performance.current.speed": {"map": "r._value * 1.94384", "unit": "knots", "type": "speed"},
    
    # Angles: rad → degrees
    "navigation.attitude.roll": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "navigation.attitude.pitch": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "navigation.attitude.yaw": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "navigation.headingTrue": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "navigation.headingMagnetic": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "navigation.courseOverGroundTrue": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "environment.wind.directionTrue": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "environment.wind.directionMagnetic": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "environment.wind.angleApparent": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    "environment.wind.angleTrueWater": {"map": "r._value * 57.2958", "unit": "degree", "type": "angle"},
    
    # Temperature: K → °C
    "environment.water.temperature": {"map": "r._value - 273.15", "unit": "celsius", "type": "temp"},
    "environment.outside.temperature": {"map": "r._value - 273.15", "unit": "celsius", "type": "temp"},
    
    # Pressure: Pa → hPa
    "environment.outside.pressure": {"map": "r._value / 100.0", "unit": "hPa", "type": "pressure"},
}

def needs_conversion(query_text):
    """Check if query contains any measurement needing conversion"""
    for measurement in CONVERSIONS.keys():
        if measurement in query_text:
            return measurement
    return None

def add_conversion_to_query(query_text, measurement):
    """Add conversion map to Flux query"""
    conversion = CONVERSIONS[measurement]
    
    # Build the conversion line
    conversion_line = f"|> map(fn: (r) => ({{r with _value: {conversion['map']}}})"
    
    # Find the last |> before drop() or end of query
    # Pattern: we want to insert BEFORE any terminal operations
    lines = query_text.split('\n')
    
    insert_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not line.startswith('//') and line != '':
            # Found last non-comment, non-empty line
            if '|> drop' not in line and 'keep(' not in line:
                insert_idx = i
                break
    
    if insert_idx >= 0:
        # Insert conversion line after the last filter/operation
        lines.insert(insert_idx + 1, conversion_line)
        return '\n'.join(lines), True
    
    return query_text, False

def process_panel(panel, dashboard_name):
    """Process a single panel: check queries and apply conversions"""
    conversions_applied = []
    
    targets = panel.get('targets', [])
    
    for target_idx, target in enumerate(targets):
        if 'expr' in target:
            # Prometheus format (not Flux)
            continue
        
        if 'query' not in target:
            continue
        
        query = target['query']
        
        # Check if needs conversion
        measurement = needs_conversion(query)
        
        if measurement:
            new_query, applied = add_conversion_to_query(query, measurement)
            
            if applied:
                target['query'] = new_query
                
                # Also set unit in field config if possible
                if 'fieldConfig' not in panel:
                    panel['fieldConfig'] = {'defaults': {}, 'overrides': []}
                
                # Add unit override
                unit = CONVERSIONS[measurement]['unit']
                conv_type = CONVERSIONS[measurement]['type']
                
                if 'overrides' not in panel['fieldConfig']:
                    panel['fieldConfig']['overrides'] = []
                
                override = {
                    'matcher': {'id': 'byName'},
                    'properties': [
                        {'id': 'unit', 'value': unit},
                        {'id': 'custom.hideFrom', 'value': {'legend': False, 'tooltip': False, 'viz': False}}
                    ]
                }
                
                panel['fieldConfig']['overrides'].append(override)
                
                conversions_applied.append({
                    'measurement': measurement,
                    'type': conv_type,
                    'unit': unit,
                    'target_idx': target_idx,
                    'panel_title': panel.get('title', 'Unknown')
                })
    
    return conversions_applied

def process_dashboard(dashboard_path):
    """Process all panels in a dashboard"""
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    all_conversions = []
    dashboard_name = Path(dashboard_path).name
    
    panels = dashboard.get('panels', [])
    
    for panel in panels:
        conversions = process_panel(panel, dashboard_name)
        all_conversions.extend(conversions)
    
    # Write back
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    return all_conversions

def main():
    print("════════════════════════════════════════════════════════════")
    print("🚀 PHASE 3 — Apply Flux Unit Conversions to All Dashboards")
    print("════════════════════════════════════════════════════════════\n")
    
    dashboard_dir = 'docs/grafana-dashboards'
    dashboard_files = glob.glob(f'{dashboard_dir}/0[1-9]-*.json')
    
    if not dashboard_files:
        print(f"❌ No dashboards found in {dashboard_dir}")
        return False
    
    print(f"📊 Found {len(dashboard_files)} dashboards\n")
    
    total_conversions = 0
    results_by_dashboard = {}
    
    for dashboard_path in sorted(dashboard_files):
        dashboard_name = Path(dashboard_path).name
        
        try:
            conversions = process_dashboard(dashboard_path)
            results_by_dashboard[dashboard_name] = conversions
            
            if conversions:
                print(f"✅ {dashboard_name:40s} — {len(conversions):2d} conversions applied")
                total_conversions += len(conversions)
                
                # Print details
                for conv in conversions:
                    print(f"    • {conv['panel_title']:30s} {conv['measurement']:40s} → {conv['unit']}")
            else:
                print(f"⚠️  {dashboard_name:40s} — no conversions needed")
        except Exception as e:
            print(f"❌ {dashboard_name:40s} — ERROR: {e}")
    
    print(f"\n════════════════════════════════════════════════════════════")
    print(f"✅ TOTAL CONVERSIONS APPLIED: {total_conversions}")
    print(f"════════════════════════════════════════════════════════════\n")
    
    # Summary by type
    by_type = {}
    for dashboard, conversions in results_by_dashboard.items():
        for conv in conversions:
            conv_type = conv['type']
            if conv_type not in by_type:
                by_type[conv_type] = 0
            by_type[conv_type] += 1
    
    if by_type:
        print("📊 CONVERSIONS BY TYPE:\n")
        for conv_type, count in sorted(by_type.items()):
            print(f"  • {conv_type.upper():15s} {count:2d}")
    
    print(f"\n✅ All dashboards updated with Flux conversions!")
    print(f"📋 Next step: Reload dashboards in Grafana to see changes\n")
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

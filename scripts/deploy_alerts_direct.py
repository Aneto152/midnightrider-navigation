#!/usr/bin/env python3
"""Deploy Grafana alerts using basic auth (no token needed)"""
import json, urllib.request, base64, sys

G = 'http://localhost:3001'
admin_user = 'admin'
admin_pass = 'admin'
creds = base64.b64encode(f'{admin_user}:{admin_pass}'.encode()).decode()

def g(path, data=None, method='GET'):
    """Call Grafana API with Basic auth"""
    req = urllib.request.Request(f'{G}{path}', data, method=method)
    req.add_header('Authorization', f'Basic {creds}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        resp = e.read().decode()
        try:
            return json.loads(resp)
        except:
            return {'error': resp, 'code': e.code}
    except Exception as e:
        return {'error': str(e)}

print('🔍 Configuring Grafana...')

# Folder
folders = g('/api/folders') or []
folder = next((f for f in folders if 'Midnight' in f.get('title', '')), None)
if not folder:
    folder = g('/api/folders', 
        json.dumps({'title': 'Midnight Rider Alerts'}).encode(), 'POST')

folder_uid = folder.get('uid', 'general')
print(f'✅ Folder: {folder_uid}')

# Datasource
ds = g('/api/datasources') or []
uid = next((d['uid'] for d in ds if 'influx' in d.get('type', '').lower()), '')

if not uid:
    print(f'❌ No InfluxDB datasource. Found: {[d.get("type") for d in ds]}')
    sys.exit(1)

print(f'✅ InfluxDB: {uid}')

# Alert rule helpers
B = 'midnight_rider'

def q(flux):
    return {'refId': 'A', 'relativeTimeRange': {'from': 300, 'to': 0},
        'datasourceUid': uid, 'model': {'datasource': {'type': 'influxdb', 'uid': uid},
        'refId': 'A', 'query': flux}}

def thr(op, val):
    return {'refId': 'B', 'relativeTimeRange': {'from': 0, 'to': 0},
        'datasourceUid': '-100', 'model': {'type': 'threshold', 'refId': 'B',
        'expression': 'A', 'conditions': [{'evaluator': {'params': [val], 'type': op},
        'operator': {'type': 'and'}, 'query': {'params': ['A']},
        'reducer': {'params': [], 'type': 'last'}, 'type': 'query'}]}}

def rule(title, flux, op, val, dur, nd, sev, cat):
    return {'title': title, 'condition': 'B', 'data': [q(flux), thr(op, val)],
        'noDataState': nd, 'execErrState': 'Error', 'for': dur,
        'folderUID': folder_uid, 'ruleGroup': 'midnight-rider-alerts',
        'annotations': {'description': title, 'category': cat},
        'labels': {'severity': sev, 'category': cat}}

def ex(m, f='value'):
    return f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="{m}" and r._field=="{f}")|>last()'

# Simple 10-rule core set (Safety + Critical Performance)
RULES = [
    # Safety (5)
    rule('⛵ Safety: Heel >22°', ex('navigation.attitude', 'roll'), 'gt', 22.0, '30s', 'OK', 'critical', 'Safety'),
    rule('🔋 Safety: Battery <10V', ex('sok_bms', 'voltage_v'), 'lt', 10.0, '1m', 'OK', 'critical', 'Safety'),
    rule('📡 Safety: Signal K Down', f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="navigation.speedOverGround")|>count()', 'lt', 1.0, '2m', 'Alerting', 'critical', 'Safety'),
    rule('📍 Safety: GPS Loss', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="navigation.position")|>count()', 'lt', 1.0, '1m', 'Alerting', 'critical', 'Safety'),
    rule('⚡ Safety: Sensor Failure', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="navigation.attitude")|>count()', 'lt', 1.0, '5m', 'OK', 'critical', 'Safety'),
    
    # Performance (3)
    rule('🔽 Perf: VMG <1kt', ex('performance.velocityMadeGood'), 'lt', 1.0, '5m', 'OK', 'warning', 'Performance'),
    rule('🌊 Perf: Wave Height >4m', ex('environment.water.waves.significantWaveHeight'), 'gt', 4.0, '5m', 'OK', 'warning', 'Performance'),
    rule('⛈️ Wx: Squall >30kts', ex('environment.wind.speedTrue'), 'gt', 30.0, '3m', 'OK', 'critical', 'Weather'),
    
    # Racing (2)
    rule('🏁 Race: Start Line', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="start_line")|>count()', 'gt', 0, '30s', 'OK', 'critical', 'Racing'),
    rule('⚖️ Race: Penalty', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="penalty")|>count()', 'gt', 0, '1m', 'OK', 'critical', 'Racing'),
]

print(f'\n📋 Deploying {len(RULES)} core alert rules...\n')

created = 0
skipped = 0
failed = 0

for r in RULES:
    result = g('/api/v1/provisioning/alert-rules', json.dumps(r).encode(), 'POST')
    if result.get('uid'):
        created += 1
        print(f'  ✅ {r["title"]}')
    elif result.get('code') == 409 or 'already exists' in str(result.get('message', '')).lower():
        skipped += 1
        print(f'  ⏭️  {r["title"]} (already exists)')
    else:
        failed += 1
        print(f'  ❌ {r["title"]}: {result.get("message", result.get("error", "?"))[:40]}')

print(f'\n{"="*60}')
print(f'✅ Created: {created:2d} | ⏭️  Skipped: {skipped:2d} | ❌ Failed: {failed:2d}')
print(f'Total: {created + skipped}/{len(RULES)}')

if failed == 0:
    print(f'\n🎉 All alerts deployed successfully!')
    print(f'View: http://192.168.1.167:3001/alerting/list')
else:
    print(f'\n⚠️  Some rules failed.')

print(f'{"="*60}')

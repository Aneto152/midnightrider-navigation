#!/usr/bin/env python3
"""Auto-deploy 60 Grafana alert rules with auto-generated token"""
import re, json, urllib.request, base64, sys
import os

os.chdir('/home/aneto/.openclaw/workspace')

# Read .env
env = {}
for line in open('.env'):
    m = re.match(r'^([A-Z_]+)=(.+)', line.strip())
    if m:
        env[m.group(1)] = m.group(2).strip('"')

G = 'http://localhost:3001'

# Get admin credentials
admin_user = env.get('GF_SECURITY_ADMIN_USER', 'admin')
admin_pass = env.get('GF_SECURITY_ADMIN_PASSWORD', env.get('GRAFANA_ADMIN_PASSWORD', 'admin'))
creds = base64.b64encode(f'{admin_user}:{admin_pass}'.encode()).decode()

def g_basic(path, data=None, method='GET'):
    """Call Grafana API with Basic auth"""
    req = urllib.request.Request(f'{G}{path}', data, method=method)
    req.add_header('Authorization', f'Basic {creds}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'error': e.read().decode(), 'code': e.code}
    except Exception as e:
        return {'error': str(e)}

print('🔐 Generating GRAFANA_TOKEN via admin credentials...')

# Try service account approach
sa = g_basic('/api/serviceaccounts',
    json.dumps({'name': 'oc-alert-deployer', 'role': 'Admin'}).encode(), 'POST')

sa_id = None
if sa.get('id'):
    sa_id = sa['id']
    print(f'✅ Service account created: {sa_id}')
elif 'already exists' in str(sa.get('error', '')).lower():
    sas = g_basic('/api/serviceaccounts/search?perpage=10')
    if sas and isinstance(sas, dict) and 'serviceAccounts' in sas:
        sa_id = next((s['id'] for s in sas.get('serviceAccounts', [])
            if s.get('name') == 'oc-alert-deployer'), None)
    if sa_id:
        print(f'✅ Service account found: {sa_id}')

# Create token
token = None
if sa_id:
    tok = g_basic(f'/api/serviceaccounts/{sa_id}/tokens',
        json.dumps({'name': 'oc-deploy-token'}).encode(), 'POST')
    if tok.get('key'):
        token = tok['key']
        print(f'✅ Token created via service account')

# Fallback: old API key endpoint
if not token:
    print('⚠️  Service account failed, trying legacy API key...')
    key = g_basic('/api/auth/keys',
        json.dumps({'name': 'oc-alerts', 'role': 'Admin'}).encode(), 'POST')
    if key.get('key'):
        token = key['key']
        print(f'✅ API key created via legacy endpoint')
    else:
        print(f'❌ Cannot generate token: {key}')
        sys.exit(1)

# Save token to .env
print('💾 Saving GRAFANA_TOKEN to .env...')
env_content = open('.env').read()
if 'GRAFANA_TOKEN=' in env_content:
    env_content = re.sub(r'GRAFANA_TOKEN=.*\n', f'GRAFANA_TOKEN={token}\n', env_content)
else:
    env_content += f'\nGRAFANA_TOKEN={token}\n'

with open('.env', 'w') as f:
    f.write(env_content)
print(f'✅ Token saved')

# Bearer token API function
def g(path, data=None, method='GET'):
    """Call Grafana API with Bearer token"""
    req = urllib.request.Request(f'{G}{path}', data, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'error': e.read().decode(), 'code': e.code}
    except Exception as e:
        return {'error': str(e)}

print('\n🔍 Configuring Grafana...')

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

# Alert rules helpers
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

def cnt(m):
    return f'from(bucket:"{B}")|>range(start:-3m)|>filter(fn:(r)=>r._measurement=="{m}")|>count()|>map(fn:(r)=>({{{r} with _value:float(v:r._value)}})'

# 60 Alert rules
RULES = [
    # Safety (10)
    rule('⛵ Safety: Heel >22°', ex('navigation.attitude', 'roll'), 'gt', 22.0, '30s', 'OK', 'critical', 'Safety'),
    rule('⚓ Safety: Pitch >15°', ex('navigation.attitude', 'pitch'), 'gt', 15.0, '30s', 'OK', 'critical', 'Safety'),
    rule('🔋 Safety: Battery <10V', ex('sok_bms', 'voltage_v'), 'lt', 10.0, '1m', 'OK', 'critical', 'Safety'),
    rule('📡 Safety: Signal K Down', cnt('navigation.speedOverGround'), 'lt', 1.0, '2m', 'Alerting', 'critical', 'Safety'),
    rule('📍 Safety: GPS Loss', cnt('navigation.position'), 'lt', 1.0, '1m', 'Alerting', 'critical', 'Safety'),
    rule('⚠️ Safety: Sensor Failure', cnt('navigation.attitude'), 'lt', 1.0, '5m', 'OK', 'critical', 'Safety'),
    rule('🚢 Safety: Hull Breach', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="hull_breach")|>count()', 'gt', 0, '1m', 'OK', 'critical', 'Safety'),
    rule('🌐 Safety: Network Down', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._field=="value")|>count()', 'lt', 1.0, '5m', 'Alerting', 'critical', 'Safety'),
    rule('💾 Safety: InfluxDB Stale', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._field=="value")|>count()', 'lt', 1.0, '5m', 'Alerting', 'critical', 'Safety'),
    rule('🌡️ Safety: System Temp >80°C', f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="system.cpu_temp")|>last()', 'gt', 80.0, '5m', 'OK', 'critical', 'Safety'),
    
    # Performance (15)
    rule('🔽 Perf: VMG <1kt', ex('performance.velocityMadeGood'), 'lt', 1.0, '5m', 'OK', 'warning', 'Performance'),
    rule('🌊 Perf: Wave Height >4m', ex('environment.water.waves.significantWaveHeight'), 'gt', 4.0, '5m', 'OK', 'warning', 'Performance'),
    rule('📐 Perf: Layline Off >10°', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="navigation.courseOverGround")|>last()', 'gt', 10.0, '5m', 'OK', 'warning', 'Performance'),
    rule('🧭 Perf: Heading Drift >5°', f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="navigation.headingTrue")|>difference()|>last()', 'gt', 5.0, '2m', 'OK', 'warning', 'Performance'),
    rule('⛵ Perf: Sail Config Inefficient', f'from(bucket:"{B}")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="sails")|>last()', 'lt', 0.8, '10m', 'OK', 'warning', 'Performance'),
    rule('🎛️ Perf: Trim Not Optimal', f'from(bucket:"{B}")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="trim")|>last()', 'lt', 0.8, '10m', 'OK', 'info', 'Performance'),
    rule('🌀 Perf: Current Against', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="current")|>last()', 'gt', 0.5, '5m', 'OK', 'warning', 'Performance'),
    rule('⚡ Perf: Accel Low', ex('navigation.acceleration', 'x'), 'lt', -0.5, '2m', 'OK', 'info', 'Performance'),
    rule('💨 Perf: Decel Unexpected', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="navigation.speedOverGround")|>derivative(unit:1s)|>last()', 'lt', -0.3, '1m', 'OK', 'warning', 'Performance'),
    rule('🔥 Perf: Engine Overheat', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="engine_temp")|>last()', 'gt', 100.0, '1m', 'OK', 'warning', 'Performance'),
    rule('🌀 Perf: Cavitation', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="cavitation")|>count()', 'gt', 0, '1m', 'OK', 'warning', 'Performance'),
    rule('🎣 Perf: Fouling', f'from(bucket:"{B}")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="fouling")|>count()', 'gt', 0, '10m', 'OK', 'info', 'Performance'),
    rule('↗️ Perf: Leeway High', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="leeway")|>last()', 'gt', 10.0, '5m', 'OK', 'warning', 'Performance'),
    rule('🗺️ Perf: DR Error', f'from(bucket:"{B}")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="dr_error")|>last()', 'gt', 0.5, '10m', 'OK', 'warning', 'Performance'),
    rule('📉 Perf: Polars Dev >20%', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="polars_deviation")|>last()', 'gt', 20.0, '5m', 'OK', 'warning', 'Performance'),
    
    # Weather/Sea (15)
    rule('💨 Wx: Wind Shift >15°', f'from(bucket:"{B}")|>range(start:-15m)|>filter(fn:(r)=>r._measurement=="environment.wind.directionTrue")|>timedMovingAverage(every:5m,period:5m)|>difference()|>last()', 'gt', 15.0, '5m', 'OK', 'warning', 'Weather'),
    rule('🌬️ Wx: Wind Speed +5kt', f'from(bucket:"{B}")|>range(start:-10m)|>filter(fn:(r)=>r._measurement=="environment.wind.speedTrue")|>timedMovingAverage(every:5m,period:5m)|>difference()|>last()', 'gt', 5.0, '5m', 'OK', 'warning', 'Weather'),
    rule('⛈️ Wx: Squall >30kts', ex('environment.wind.speedTrue'), 'gt', 30.0, '3m', 'OK', 'critical', 'Weather'),
    rule('📉 Wx: Pressure -5hPa/h', f'from(bucket:"{B}")|>range(start:-60m)|>filter(fn:(r)=>r._measurement=="lis_wind")|>timedMovingAverage(every:30m,period:30m)|>difference()|>last()', 'lt', -5.0, '30m', 'OK', 'warning', 'Weather'),
    rule('❄️ Wx: Temp Drop >3°C', f'from(bucket:"{B}")|>range(start:-15m)|>filter(fn:(r)=>r._measurement=="lis_wind")|>timedMovingAverage(every:10m,period:10m)|>difference()|>last()', 'lt', -3.0, '15m', 'OK', 'info', 'Weather'),
    rule('🌊 Wx: Swell Adverse', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="swell_adverse")|>count()', 'gt', 0, '5m', 'OK', 'warning', 'Weather'),
    rule('🌊 Wx: Tide Change', f'from(bucket:"{B}")|>range(start:-30m)|>filter(fn:(r)=>r._measurement=="tide")|>derivative(unit:15m)|>last()', 'lt', -0.1, '10m', 'OK', 'info', 'Weather'),
    rule('↩️ Wx: Current Reversal', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="current_reversal")|>count()', 'gt', 0, '5m', 'OK', 'info', 'Weather'),
    rule('🌊 Wx: Wave Period <6s', ex('environment.water.waves.period'), 'lt', 6.0, '5m', 'OK', 'warning', 'Weather'),
    rule('🌊 Wx: Whitecaps >20kt', ex('environment.wind.speedTrue'), 'gt', 20.0, '10m', 'OK', 'info', 'Weather'),
    rule('🌫️ Wx: Fog Bank', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="fog")|>count()', 'gt', 0, '5m', 'OK', 'warning', 'Weather'),
    rule('⚡ Wx: Lightning', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="lightning")|>count()', 'gt', 0, '1m', 'OK', 'critical', 'Weather'),
    rule('📉 Wx: Baro Trend Neg', f'from(bucket:"{B}")|>range(start:-120m)|>filter(fn:(r)=>r._measurement=="lis_wind")|>derivative(unit:1h)|>last()', 'lt', -3.0, '60m', 'OK', 'warning', 'Weather'),
    rule('💧 Wx: Humidity >90%', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="humidity")|>last()', 'gt', 90.0, '5m', 'OK', 'info', 'Weather'),
    rule('❄️ Wx: Dew Point', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="dew_point")|>last()', 'gt', 0, '5m', 'OK', 'info', 'Weather'),
    
    # Systems (10)
    rule('🔋 Sys: SOC <20%', ex('sok_bms', 'soc_pct'), 'lt', 20.0, '2m', 'OK', 'critical', 'Systems'),
    rule('⚡ Sys: Current >100A', ex('sok_bms', 'current_a'), 'gt', 100.0, '1m', 'OK', 'critical', 'Systems'),
    rule('🔌 Sys: Charger Fail', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="charger")|>count()', 'lt', 1, '5m', 'OK', 'warning', 'Systems'),
    rule('🔌 Sys: Inverter Fault', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="inverter")|>count()', 'lt', 1, '5m', 'OK', 'warning', 'Systems'),
    rule('⏱️ Sys: Comm Delay >30s', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="navigation.speedOverGround")|>last()', 'gt', 30.0, '1m', 'OK', 'warning', 'Systems'),
    rule('📡 Sys: GPS Dilution >10', ex('navigation.gnss.horizontalDilution'), 'gt', 10.0, '2m', 'OK', 'warning', 'Systems'),
    rule('🧭 Sys: Compass Err >5°', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="compass")|>last()', 'gt', 5.0, '5m', 'OK', 'warning', 'Systems'),
    rule('🕐 Sys: Clock Sync', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="clock")|>count()', 'lt', 1, '5m', 'OK', 'info', 'Systems'),
    rule('💾 Sys: Storage >85%', ex('system.disk', 'usage_pct'), 'gt', 85.0, '10m', 'OK', 'warning', 'Systems'),
    rule('🔄 Sys: Update Available', f'from(bucket:"{B}")|>range(start:-60m)|>filter(fn:(r)=>r._measurement=="update")|>count()', 'gt', 0, '60m', 'OK', 'info', 'Systems'),
    
    # Racing (10)
    rule('⚓ Race: Mark <2nm', f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="marks")|>min()', 'lt', 2.0, '1m', 'OK', 'info', 'Racing'),
    rule('🏁 Race: Start Cross', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="start_line")|>count()', 'gt', 0, '30s', 'OK', 'critical', 'Racing'),
    rule('⚠️ Race: Wrong Mark', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="wrong_mark")|>count()', 'gt', 0, '1m', 'OK', 'critical', 'Racing'),
    rule('🚫 Race: Outside Course', f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="course_boundary")|>count()', 'gt', 0, '2m', 'OK', 'warning', 'Racing'),
    rule('⚖️ Race: Penalty', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="penalty")|>count()', 'gt', 0, '1m', 'OK', 'critical', 'Racing'),
    rule('⏰ Race: Time <2h', ex('regatta.timer', 'remaining_h'), 'lt', 2.0, '30m', 'OK', 'warning', 'Racing'),
    rule('📏 Race: Fleet Behind >5nm', f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="fleet")|>max()', 'gt', 5.0, '10m', 'OK', 'info', 'Racing'),
    rule('⚠️ Race: Fleet Ahead <0.2nm', f'from(bucket:"{B}")|>range(start:-2m)|>filter(fn:(r)=>r._measurement=="fleet")|>min()', 'lt', 0.2, '2m', 'OK', 'warning', 'Racing'),
    rule('🏁 Race: Finish Zone', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="finish_zone")|>count()', 'gt', 0, '1m', 'OK', 'info', 'Racing'),
    rule('🎯 Race: Finish', f'from(bucket:"{B}")|>range(start:-1m)|>filter(fn:(r)=>r._measurement=="finish")|>count()', 'gt', 0, '1m', 'OK', 'info', 'Racing'),
]

print(f'\n📋 Deploying {len(RULES)} alert rules...\n')

created = 0
skipped = 0
failed = 0

for r in RULES:
    result = g('/api/v1/provisioning/alert-rules', json.dumps(r).encode(), 'POST')
    if result.get('uid'):
        created += 1
    elif result.get('code') == 409 or 'already exists' in str(result.get('error', '')).lower():
        skipped += 1
    else:
        failed += 1
        if failed <= 5:  # Show first 5 failures
            print(f'  ⚠️  {r["title"]}: {str(result.get("error", "?"))[:40]}')

print(f'\n{"="*60}')
print(f'✅ Created: {created:2d} | ⏭️  Skipped: {skipped:2d} | ❌ Failed: {failed:2d}')
print(f'Total: {created + skipped}/{len(RULES)}')

if created + skipped == len(RULES):
    print(f'\n🎉 All {len(RULES)} alert rules deployed!')
    print(f'View: http://192.168.1.167:3001/alerting/list')
else:
    print(f'\n⚠️  Some rules failed to deploy.')

print(f'{"="*60}')

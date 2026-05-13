# Grafana COMPETITION Dashboard — Deployment Guide

## Prerequisites

**GRAFANA_TOKEN** must be set in `.env` before dashboard deployment.

---

## Step 1: Generate Grafana API Token

### Option A: Web UI (Recommended)

1. Open http://192.168.1.167:3001 (or http://localhost:3001)
2. Click **Admin** (top menu) → **Service Accounts**
3. Click **Create Service Account**
   - Name: `ais-watch-api`
   - Role: **Admin** (required for dashboard creation)
4. Click **Create**
5. Click **Add Service Account Token**
6. Copy the token (shown once only!)

### Option B: API (requires current token)

```bash
curl -X POST http://localhost:3001/api/v1/serviceaccounts \
  -H "Authorization: Bearer $EXISTING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "ais-watch-api", "role": "Admin"}'
```

---

## Step 2: Add Token to .env

Edit `/home/aneto/.openclaw/workspace/.env`:

```bash
# Add this line (replace xxx with your actual token):
GRAFANA_TOKEN=glsa_xxxxxxxxxxxxxxxxxxxx
```

Then verify:

```bash
grep GRAFANA_TOKEN .env
```

---

## Step 3: Deploy Dashboard

Run the deployment script:

```bash
cd /home/aneto/.openclaw/workspace
python3 << 'PYEOF'
import json,urllib.request,os,re

env={}
for l in open('.env'):
    m=re.match(r'^([A-Z_]+)=(.+)',l.strip())
    if m: env[m.group(1)]=m.group(2).strip('"')

G='http://localhost:3001'; T=env.get('GRAFANA_TOKEN','')
if not T: print('ERR: GRAFANA_TOKEN missing'); exit(1)

def g(path,data=None,m='GET'):
    r=urllib.request.Request(f'{G}{path}',data,method=m)
    r.add_header('Authorization',f'Bearer {T}')
    r.add_header('Content-Type','application/json')
    try:
        with urllib.request.urlopen(r,timeout=10) as x: return json.loads(x.read())
    except Exception as e: print(f'{path}: {e}'); return None

# Find InfluxDB datasource
ds=g('/api/datasources') or []
uid=next((d['uid'] for d in ds if 'influx' in d.get('type','')),'')
if not uid: print(f'ERR: no InfluxDB datasource'); exit(1)
print(f'InfluxDB UID: {uid}')

B='midnight_rider'; C='competitor_tracking'

def tgt(q): return [{'refId':'A','query':q,'datasource':{'type':'influxdb','uid':uid}}]

def p(i,t,ty,x,y,w,h,q):
    return {
        'id':i,'title':t,'type':ty,
        'gridPos':{'h':h,'w':w,'x':x,'y':y},
        'targets':tgt(q),
        'datasource':{'type':'influxdb','uid':uid}
    }

# Flux queries (5 min and 2 hour windows)
b5=f'from(bucket:"{B}")|>range(start:-5m)|>filter(fn:(r)=>r._measurement=="{C}")'
b2h=f'from(bucket:"{B}")|>range(start:-2h)|>filter(fn:(r)=>r._measurement=="{C}")'
nm='/1852.0'  # Conversion: meters to nautical miles

# Dashboard panels (6 total)
panels=[
    p(1,'Fleet Status — Distance · Bearing · SOG','table',0,0,24,8,
        b5+'|>filter(fn:(r)=>r._field=="distance_m" or r._field=="bearing_true" or r._field=="sog_ms" or r._field=="ais_age_s")|>last()|>pivot(rowKey:["boat_name","priority"],columnKey:["_field"],valueColumn:"_value")|>sort(columns:["distance_m"])'),
    p(2,'Distance Trend — High Priority (NM)','timeseries',0,8,16,8,
        b2h+'|>filter(fn:(r)=>r._field=="distance_m" and r.priority=="high")|>aggregateWindow(every:2m,fn:last,createEmpty:false)|>map(fn:(r)=>({r with _value:r._value'+nm+'}))'),
    p(3,'Closest Competitor (NM)','stat',16,8,8,4,
        b5+'|>filter(fn:(r)=>r._field=="distance_m")|>last()|>min()|>map(fn:(r)=>({r with _value:r._value'+nm+'}))'),
    p(4,'AIS Signal Age (seconds)','table',16,12,8,4,
        b5+'|>filter(fn:(r)=>r._field=="ais_age_s")|>last()|>sort(columns:["_value"],desc:true)|>limit(n:20)'),
    p(5,'Competitors — Distance Ranking (NM)','bargauge',0,16,12,6,
        b5+'|>filter(fn:(r)=>r._field=="distance_m")|>last()|>map(fn:(r)=>({r with _value:r._value'+nm+'}))|>sort(columns:["_value"])'),
    p(6,'Competitor Positions Map','geomap',12,16,12,6,
        b5+'|>filter(fn:(r)=>r._field=="lat" or r._field=="lon")|>last()|>pivot(rowKey:["boat_name","mmsi"],columnKey:["_field"],valueColumn:"_value")')
]

# Create dashboard
dash={
    'dashboard':{
        'id':None,
        'title':'COMPETITION — Block Island 2026',
        'tags':['competition','ais','birw2026'],
        'timezone':'browser',
        'schemaVersion':38,
        'refresh':'30s',
        'panels':panels
    },
    'overwrite':True,
    'folderId':0
}

result=g('/api/dashboards/db',json.dumps(dash).encode(),m='POST')
if result and result.get('status')=='success':
    print(f"✅ Dashboard created: http://localhost:3001{result.get('url','')}")
else: 
    print(f"Error: {result}")
PYEOF
```

---

## Step 4: Verify Dashboard

1. Open http://192.168.1.167:3001/d/COMPETITION-Block-Island-2026
2. Check all 6 panels load
3. If no data: ais-watch service not running yet (start on May 19)

---

## Dashboard Panels

| # | Name | Type | Data | Refresh |
|---|------|------|------|---------|
| 1 | Fleet Status | Table | Last 5m snapshot | 30s |
| 2 | Distance Trend (High Priority) | Time Series | 2h history, high-priority boats | 30s |
| 3 | Closest Competitor | Stat | Minimum distance (NM) | 30s |
| 4 | AIS Signal Age | Table | Top 20 by age (seconds) | 30s |
| 5 | Distance Ranking | Bar Gauge | All competitors, NM | 30s |
| 6 | Positions Map | Geomap | Lat/lon scatter | 30s |

---

## InfluxDB Measurement Schema

```
measurement: competitor_tracking
timestamp: Unix seconds
tags: competitor_id, boat_name, mmsi, priority
fields: distance_m, bearing_true, lat, lon, sog_ms, cog_true, phrf_lis, irc_tcc, ais_age_s
```

---

## Troubleshooting

### "ERR: no InfluxDB datasource"

Check datasource exists:

```bash
curl -s http://localhost:3001/api/datasources \
  -H "Authorization: Bearer $GRAFANA_TOKEN" | jq '.[] | select(.type=="influxdb")'
```

### "ERR: GRAFANA_TOKEN missing"

Add token to .env:

```bash
echo 'GRAFANA_TOKEN=glsa_xxxx' >> .env
```

### Panels show "No data"

ais_watch service not running yet. Start after field test:

```bash
sudo systemctl start ais-watch
journalctl -u ais-watch -f  # Watch logs
```

---

## Next Steps

1. **May 18**: Generate token + deploy dashboard
2. **May 19**: Field test → start ais-watch service
3. **May 22**: Monitor dashboard during Block Island Race

---

**Dashboard ready for race data! 🎯**

# InfluxDB Configuration — Local + Cloud Support

## Overview

**Supports BOTH local and cloud InfluxDB.**

- **Local:** Always active (localhost:8086)
- **Cloud:** Optional (activate when token available)

## Architecture

```
Data Sources
├─ GPS/NMEA (UM982) → Signal K
├─ Attitude (roll/pitch/yaw) → Signal K Plugin
└─ Astronomical Data → Cron Script

Signal K + Plugins
├─ signalk-to-influxdb2 (local)
└─ Can add cloud replication later

Storage Options:
├─ LOCAL: InfluxDB (localhost:8086) — ALWAYS ON ✅
├─ CLOUD: InfluxDB Cloud — WHEN TOKEN PROVIDED ⏳
└─ HYBRID: Both simultaneously (replication)
```

## Local InfluxDB (Always Active)

```yaml
# docker-compose.yml
influxdb:
  image: influxdb:2.8
  ports:
    - "8086:8086"
  environment:
    - INFLUX_DB_BUCKET=signalk
    - INFLUX_DB_ORG=MidnightRider
    - INFLUX_DOCKER_INIT_MODE=setup
    - INFLUX_ORG=MidnightRider
    - INFLUX_BUCKET=signalk
    - INFLUX_ADMIN_USER=admin
    - INFLUX_ADMIN_PASSWORD=password
    - INFLUX_ADMIN_TOKEN=[MASKED_INFLUX_TOKEN]
  volumes:
    - influxdb-data:/var/lib/influxdb2
```

## Cloud InfluxDB (Optional)

When you renew the cloud token:

```bash
# Export token
export INFLUX_CLOUD_URL="https://us-east-1-1.aws.cloud2.influxdata.com"
export INFLUX_CLOUD_TOKEN="your-new-cloud-token-here"
export INFLUX_CLOUD_ORG="48a34d6463cef7c9"
export INFLUX_CLOUD_BUCKET="signalk-cloud"
```

Add to `docker-compose.yml`:

```yaml
astronomical:
  environment:
    # Local (always)
    - INFLUX_URL=http://localhost:8086
    - INFLUX_TOKEN=[MASKED_INFLUX_TOKEN]
    - INFLUX_ORG=MidnightRider
    - INFLUX_BUCKET=signalk
    
    # Cloud (when available)
    - INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
    - INFLUX_CLOUD_TOKEN=your-cloud-token
    - INFLUX_CLOUD_ORG=48a34d6463cef7c9
    - INFLUX_CLOUD_BUCKET=signalk-cloud
```

## Hybrid Replication Script

When both local and cloud are active:

```bash
#!/bin/bash
# scripts/replicate-to-cloud.sh

# Query local
influx query 'from(bucket:"signalk") |> range(start: -24h)' \
  --org MidnightRider > /tmp/data.csv

# Write to cloud (if token available)
if [ -n "$INFLUX_CLOUD_TOKEN" ]; then
  influx write \
    --url "$INFLUX_CLOUD_URL" \
    --token "$INFLUX_CLOUD_TOKEN" \
    --org "$INFLUX_CLOUD_ORG" \
    --bucket "$INFLUX_CLOUD_BUCKET" \
    /tmp/data.csv
fi
```

Add to crontab:

```bash
# Replicate to cloud daily (if token set)
0 3 * * * /home/aneto/docker/signalk/scripts/replicate-to-cloud.sh
```

## Current Status

### Local (✅ ACTIVE)

```
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=[MASKED_INFLUX_TOKEN]
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk
```

**Status:** ✅ All services writing to local InfluxDB

### Cloud (⏳ INACTIVE)

```
INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
INFLUX_CLOUD_TOKEN=<EXPIRED>
INFLUX_CLOUD_ORG=48a34d6463cef7c9
INFLUX_CLOUD_BUCKET=signalk-cloud
```

**Status:** ⏳ Token expired, not syncing to cloud

## How to Activate Cloud

### Step 1: Renew Cloud Token

1. Go to: https://cloud2.influxdata.com
2. Log in with your InfluxDB Cloud account
3. Navigate: Settings → API Tokens
4. Create new token with:
   - Permissions: Read + Write on `signalk-cloud` bucket
   - Copy token

### Step 2: Update Environment

Option A: Update docker-compose.yml

```yaml
astronomical:
  environment:
    - INFLUX_CLOUD_TOKEN=<paste-new-token-here>
```

Option B: Create .env file

```bash
# /home/aneto/docker/signalk/.env
INFLUX_CLOUD_TOKEN=<new-token>
INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
INFLUX_CLOUD_ORG=48a34d6463cef7c9
INFLUX_CLOUD_BUCKET=signalk-cloud
```

Then update docker-compose.yml:

```yaml
astronomical:
  env_file: .env
```

### Step 3: Update Scripts

Edit `scripts/astronomical-data.sh`:

```bash
# Add after sending to local
if [ -n "$INFLUX_CLOUD_TOKEN" ]; then
  echo "Sending to cloud..."
  curl -X POST \
    "$INFLUX_CLOUD_URL/api/v2/write?org=$INFLUX_CLOUD_ORG&bucket=$INFLUX_CLOUD_BUCKET&precision=ns" \
    -H "Authorization: Token $INFLUX_CLOUD_TOKEN" \
    -H "Content-Type: text/plain" \
    -d "$DATA"
fi
```

### Step 4: Restart Services

```bash
docker compose restart astronomical
```

### Step 5: Verify

```bash
# Check cloud connection
curl -H "Authorization: Token $INFLUX_CLOUD_TOKEN" \
  $INFLUX_CLOUD_URL/health

# Query cloud data
influx query \
  --url $INFLUX_CLOUD_URL \
  --token $INFLUX_CLOUD_TOKEN \
  --org $INFLUX_CLOUD_ORG \
  'from(bucket:"signalk-cloud") |> range(start: -24h)'
```

## Data Flow with Both Active

```
GPS/NMEA Instruments
        ↓
Signal K Server
        ├─ → InfluxDB Local (localhost:8086) ✅
        └─ → InfluxDB Cloud (cloud URL) [if token set]
        
Astronomical Data Script
        ├─ → InfluxDB Local (localhost:8086) ✅
        └─ → InfluxDB Cloud (cloud URL) [if token set]
        
Grafana
        ├─ Sources from Local (primary)
        └─ Can also query Cloud (backup)
        
Backup Strategy
        ├─ Local: Always stored on Pi
        └─ Cloud: Optional backup copy
```

## Advantages of Hybrid

| Scenario | Local Only | Cloud Only | Hybrid (Both) |
|----------|-----------|-----------|--------------|
| On-boat access | ✅ Yes | ❌ Need internet | ✅ Yes (local) |
| Remote access | ❌ No | ✅ Yes (cloud) | ✅ Yes (cloud) |
| Data backup | ⚠️ Manual | ✅ Auto | ✅ Auto redundancy |
| Cost | Free | $$ | $$ (minimal) |
| Reliability | Single point | Single point | Redundant |
| Internet required | ❌ No | ✅ Yes | Partial (cloud only) |

**Recommendation:** Hybrid = Best of both worlds

## .gitignore

**Important:** Don't commit tokens to git!

```bash
# /home/aneto/docker/signalk/.gitignore
.env
.env.local
*.secret
**/config/*.json
**/plugin-config-data/
```

Then use environment variables:

```bash
export INFLUX_CLOUD_TOKEN="..."
docker compose up
```

## Troubleshooting

### Cloud write fails (401)

```
Error: 401 Unauthorized
```

**Solution:** Token expired or invalid

```bash
# Check token
echo $INFLUX_CLOUD_TOKEN

# Renew at: https://cloud2.influxdata.com
# → Settings → API Tokens → Create new
```

### Cloud URL not reachable

```
Error: net::ERR_NAME_NOT_RESOLVED
```

**Solution:** Check internet connection

```bash
curl https://us-east-1-1.aws.cloud2.influxdata.com/health
```

### Cloud data not syncing

```bash
# Check if script is sending
docker logs astronomical | grep -i cloud

# Verify environment variables
docker exec astronomical env | grep INFLUX_CLOUD
```

## Fallback Strategy

If cloud goes down:

1. **Local continues working** ✅ (no interruption)
2. **Grafana queries local** ✅ (primary source)
3. **Cloud syncs resume** when cloud recovers
4. **No data loss** (stored locally)

Perfect for on-boat navigation where internet is unreliable!

## Summary

| Component | Status | Action |
|-----------|--------|--------|
| Local InfluxDB | ✅ Active | No action needed |
| Cloud InfluxDB | ⏳ Inactive | Renew token when needed |
| Scripts | ✅ Ready | Will auto-detect cloud token |
| Docker Compose | ✅ Ready | Will auto-detect cloud env vars |
| Replication | ⏳ Optional | Set up when cloud token available |

**You have maximum flexibility:**
- Use local-only for now (works perfectly)
- Activate cloud anytime (no code changes)
- Both simultaneously (automatic redundancy)

---

**Updated:** 2026-04-20 02:32 EDT
**System:** MidnightRider J/30 (Raspberry Pi 4B)

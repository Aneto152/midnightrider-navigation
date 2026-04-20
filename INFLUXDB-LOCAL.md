# InfluxDB Local-Only Configuration

## Overview

**All data is stored locally on the Raspberry Pi.**

No cloud synchronization, no external dependencies beyond the Pi.

## Architecture

```
GPS/NMEA Instruments
        ↓
Signal K Server (port 3000)
        ├─ um982-gps plugin: heading, position
        ├─ um982-proprietary: roll/pitch/yaw
        └─ signalk-to-influxdb2: → InfluxDB
        
Astronomical Data Scripts
        ├─ scripts/astronomical-data.sh
        ├─ Docker: astronomical container
        └─ → InfluxDB (HTTP POST)

Cron Jobs (daily updates)
        ├─ 0 0 * * * astronomical-data.sh
        └─ → InfluxDB

MCP Server (for Claude/Cursor AI)
        ├─ Queries InfluxDB
        └─ Provides tools: get_sun_data, get_moon_data, get_tide_data

All → InfluxDB Local (localhost:8086)
    ↓
Grafana (port 3001)
    ↓
iPad/Browser (WiFi)
```

## Services

### InfluxDB (Port 8086)

```bash
# Status
docker ps | grep influxdb

# Connect
influx --host http://localhost:8086 --token $INFLUX_TOKEN --org MidnightRider

# Query example
influx query 'from(bucket:"signalk") |> range(start: -24h)' --org MidnightRider

# Backup
docker exec influxdb influx backup /tmp/backup
docker cp influxdb:/tmp/backup ./backups/
```

### Grafana (Port 3001)

```bash
# Open
firefox http://localhost:3001
# or
firefox http://192.168.x.x:3001  # From iPad on WiFi

# Data Source
- Type: InfluxDB
- URL: http://localhost:8086
- Org: MidnightRider
- Bucket: signalk
- Token: 4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
```

### Signal K (Port 3000)

```bash
# Admin UI
firefox http://localhost:3000
# or
firefox http://192.168.x.x:3000  # From iPad on WiFi

# API
curl -H "Authorization: Bearer $SIGNAL_K_TOKEN" \
  http://localhost:3000/signalk/v1/api/vessels/self
```

## Data Storage

### Location

```
/var/lib/docker/volumes/influxdb-data/_data/
```

### Size Estimation

- 1 Hz GPS data: ~50 MB/day
- 10 measurements/point: ~500 MB/day total
- 30-day retention: ~15 GB
- Pi storage: 32-64 GB → OK

## Environment Variables

All services use these env vars:

```bash
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk
```

**No cloud URLs, no cloud tokens.**

## Accessing Data

### From Bash

```bash
# List all measurements
influx bucket list --org MidnightRider

# Query all navigation data (last 24h)
influx query 'from(bucket:"signalk") 
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement =~ /^navigation/')

# Export to CSV
influx query 'from(bucket:"signalk") |> range(start: -7d)' \
  --org MidnightRider > export.csv
```

### From Grafana

1. Create dashboard
2. Add panel
3. Query example:
```sql
SELECT value FROM "navigation.headingTrue" 
WHERE time > now() - 24h
```

### From Claude/Cursor (via MCP)

```
Claude: "What's the sunrise time?"
→ MCP Server queries InfluxDB
← Sunrise: 2026-04-19T10:10:06Z
```

## Backup Strategy

### Option 1: Manual Backup (weekly)

```bash
# Backup InfluxDB
docker exec influxdb influx backup /tmp/backup
docker cp influxdb:/tmp/backup ~/backups/influxdb-$(date +%Y%m%d)/

# Backup Grafana config
docker cp grafana:/etc/grafana ~/backups/grafana-$(date +%Y%m%d)/
```

### Option 2: Automated Backup (cron)

```bash
# /home/aneto/backup-influxdb.sh
#!/bin/bash
DATE=$(date +%Y%m%d)
docker exec influxdb influx backup /tmp/backup
docker cp influxdb:/tmp/backup /mnt/nfs/backups/influxdb-$DATE
```

Add to crontab:
```bash
0 2 * * 0 /home/aneto/backup-influxdb.sh
```

### Option 3: Push to Cloud (optional)

If you later want cloud backup:

```bash
# After backup
aws s3 sync ~/backups/influxdb-* s3://my-backup-bucket/

# Or
rsync -av ~/backups/ user@nas:/backups/midnightrider/
```

## Disaster Recovery

### If InfluxDB dies

```bash
# Stop all containers
docker compose down

# Remove corrupted data
docker volume rm signalk_influxdb-data

# Restore from backup
docker cp ~/backups/influxdb-20260419/backup /tmp/
docker volume create influxdb-data
docker cp /tmp/backup/. influxdb-data:/

# Start services
docker compose up -d
```

## Capacity Planning

### Storage

- Bucket size: ~500 MB/day (1 Hz data, 10 measurements)
- 60-day retention: ~30 GB
- Pi total storage: 32-64 GB
- **Status:** Comfortable, no issues

### Memory

- InfluxDB: ~500 MB
- Signal K: ~200 MB
- Grafana: ~100 MB
- **Total:** ~800 MB (Pi has 4-8 GB)
- **Status:** Plenty of headroom

### CPU

- InfluxDB writes: Minimal (<1% Pi CPU)
- Signal K processing: ~5-10% Pi CPU
- Grafana rendering: Minimal
- **Total:** ~10-15% Pi CPU
- **Status:** Comfortable

## Troubleshooting

### InfluxDB not responding

```bash
# Check logs
docker logs influxdb | tail -50

# Verify port
netstat -tlnp | grep 8086

# Test connection
curl http://localhost:8086/health

# Restart
docker restart influxdb
```

### No data in Grafana

```bash
# Check Signal K sending to InfluxDB
docker logs signalk | grep influx

# Verify data in bucket
influx query 'from(bucket:"signalk") |> range(start: -1h)' --org MidnightRider

# Check plugin config
cat /home/aneto/.signalk/plugin-config-data/signalk-to-influxdb2.json
```

### MCP can't reach InfluxDB

```bash
# Test from inside container
docker exec astronomical curl -I http://localhost:8086/health

# Check token
echo $INFLUX_TOKEN

# Verify env vars passed
docker inspect astronomical | grep INFLUX
```

## Future: Cloud Sync (if needed)

If you later want to sync to InfluxDB Cloud:

```yaml
# Add to docker-compose.yml
environment:
  - INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
  - INFLUX_CLOUD_TOKEN=your-cloud-token
  - INFLUX_CLOUD_ORG=your-cloud-org
  - INFLUX_CLOUD_BUCKET=signalk-cloud
```

Then in script:

```bash
# Replicate data to cloud (optional, not configured)
influx remote create \
  --name cloud \
  --remote-url https://us-east-1-1.aws.cloud2.influxdata.com \
  --remote-token $INFLUX_CLOUD_TOKEN \
  --remote-org $INFLUX_CLOUD_ORG
```

**But for now, local-only is simpler and sufficient.** ✅

## Security Notes

### Token Storage

Token is in:
- `docker-compose.yml` (environment)
- `.signalk/plugin-config-data/*.json`
- Scripts and containers

**For production security:**
1. Use Docker secrets: `docker secret create influx_token`
2. Or: `.env` file (not in git)
3. Or: systemd environment files

**For now:** Single-user system on private network → OK

### Network Access

- InfluxDB: localhost:8086 only (no port forward to internet)
- Grafana: localhost:3001 (access via iPad on local WiFi)
- Signal K: localhost:3000 (access via iPad on local WiFi)

**Status:** Secured by network isolation ✅

## Summary

| Aspect | Status |
|--------|--------|
| Data Storage | ✅ Local InfluxDB (Pi) |
| Cloud Sync | ❌ Disabled (no cloud token) |
| Backup | ⚠️ Manual recommended |
| Access | ✅ Local network (WiFi) |
| Capacity | ✅ Plenty (30+ GB available) |
| Security | ✅ Network isolated |

**Everything works locally. No external dependencies.** 🚤⛵

---

**Updated:** 2026-04-20 02:30 EDT
**System:** MidnightRider J/30 (Raspberry Pi 4B)

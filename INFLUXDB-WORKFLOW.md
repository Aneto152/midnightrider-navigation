# InfluxDB Workflow — Live Local + Debrief Cloud

## Strategy

**Perfect for sailing:**

```
RÉGATE (Live)                    APRÈS RÉGATE (Debrief)
└─ Local InfluxDB                └─ Cloud InfluxDB
   ├─ No internet needed            ├─ Upload race data
   ├─ Real-time iPad monitoring     ├─ Detailed analysis
   ├─ Full speed 1 Hz               ├─ Compare tactics
   └─ Data on boat                  ├─ Share results
                                    └─ Long-term storage
```

## Live Race Workflow

### Before Race (Dock)

```bash
# 1. Verify local InfluxDB ready
docker ps | grep influxdb
# Status: Up (port 8086 open)

# 2. Start Signal K + Grafana
docker compose up -d signalk grafana

# 3. Verify data flow
curl http://localhost:8086/health
# {"status":"ok"}

# 4. Open Grafana on iPad
# http://192.168.x.x:3001
# Dashboard: MidnightRider Live (shows heading, speed, wind, etc.)

# 5. Disable cloud sync (to avoid distractions)
# Set INFLUX_CLOUD_TOKEN="" or don't set it
# → Scripts will skip cloud writes
```

### During Race (2-4 hours)

```
Local InfluxDB writes:
├─ GPS heading (1 Hz) ✅
├─ Speed through water ✅
├─ Wind angle/speed ✅
├─ Boat position ✅
└─ Performance data ✅

Grafana displays (iPad):
├─ Real-time heading
├─ VMG (velocity made good)
├─ Performance vs target
├─ Tack angles
└─ Shift detection alerts

Storage:
└─ All data on Pi (local SSD)
   ~30-50 MB for 4-hour race
```

**NO internet = NO latency = PERFECT racing experience**

### After Race (Dock/Marina)

```bash
# 1. Race finished, WiFi at marina available

# 2. Prepare for cloud debrief
export INFLUX_CLOUD_TOKEN="your-renewed-token"
export INFLUX_CLOUD_URL="https://us-east-1-1.aws.cloud2.influxdata.com"
export INFLUX_CLOUD_ORG="48a34d6463cef7c9"
export INFLUX_CLOUD_BUCKET="signalk-cloud"

# 3. Export race data from local
influx query \
  --org MidnightRider \
  'from(bucket:"signalk") 
   |> range(start: 2026-04-20T14:00:00Z, stop: 2026-04-20T18:00:00Z)' \
  > race-2026-04-20.csv

# 4. Upload to cloud
influx write \
  --url $INFLUX_CLOUD_URL \
  --token $INFLUX_CLOUD_TOKEN \
  --org $INFLUX_CLOUD_ORG \
  --bucket $INFLUX_CLOUD_BUCKET \
  race-2026-04-20.csv

# 5. Clear local to free space (optional)
# Keep race data in local backup just in case
docker exec influxdb influx bucket truncate \
  --org MidnightRider \
  --bucket signalk \
  --older-than 7d  # Keep 7 days locally, rest goes to cloud

# 6. Access cloud Grafana for debrief
# https://cloud2.influxdata.com/orgs/48a34d6463cef7c9/dashboards
```

## Configuration

### Environment Setup

Create `.env` file (keep secrets out of git):

```bash
# /home/aneto/docker/signalk/.env

# LOCAL (Always active)
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=[MASKED_INFLUX_TOKEN]
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk

# CLOUD (Empty during race, set after)
INFLUX_CLOUD_URL=
INFLUX_CLOUD_TOKEN=
INFLUX_CLOUD_ORG=
INFLUX_CLOUD_BUCKET=

# WORKFLOW
RACE_MODE=true  # Set to 'true' before race (local only)
```

### Docker Compose Setup

```yaml
# docker-compose.yml
services:
  astronomical:
    env_file: .env
    environment:
      # Overrides for race mode
      - RACE_MODE=${RACE_MODE:-false}
```

### Script: Auto-Sync After Race

```bash
#!/bin/bash
# scripts/race-debrief.sh
# Run this after returning to dock

set -e

RACE_NAME="race-$(date +%Y-%m-%d-%H%M)"
START_TIME="${1:-$(date -d '4 hours ago' +%Y-%m-%dT%H:%M:%SZ)}"
END_TIME="$(date +%Y-%m-%dT%H:%M:%SZ)"

echo "🏁 Preparing race debrief..."

# 1. Export from local
echo "📥 Exporting race data from local InfluxDB..."
influx query \
  --org MidnightRider \
  'from(bucket:"signalk")
   |> range(start: '"$START_TIME"', stop: '"$END_TIME"')' \
  > /tmp/$RACE_NAME.csv

echo "✅ Exported: /tmp/$RACE_NAME.csv ($(wc -l < /tmp/$RACE_NAME.csv) lines)"

# 2. If cloud token available, upload
if [ -n "$INFLUX_CLOUD_TOKEN" ]; then
  echo "☁️  Uploading to cloud InfluxDB..."
  
  influx write \
    --url "$INFLUX_CLOUD_URL" \
    --token "$INFLUX_CLOUD_TOKEN" \
    --org "$INFLUX_CLOUD_ORG" \
    --bucket "$INFLUX_CLOUD_BUCKET" \
    /tmp/$RACE_NAME.csv
  
  echo "✅ Uploaded to cloud!"
  
else
  echo "⚠️  Cloud token not set. Skipping cloud upload."
  echo "   To enable: export INFLUX_CLOUD_TOKEN='...'"
fi

# 3. Archive locally
echo "💾 Archiving locally..."
cp /tmp/$RACE_NAME.csv ~/races/$RACE_NAME.csv
git add ~/races/$RACE_NAME.csv
git commit -m "Race debrief: $RACE_NAME"

echo ""
echo "🏁 Race debrief complete!"
echo "   Local: ~/races/$RACE_NAME.csv"
echo "   Cloud: signalk-cloud bucket"
echo ""
echo "Next: Open cloud Grafana for analysis"
echo "   https://cloud2.influxdata.com"

```

Make executable:
```bash
chmod +x scripts/race-debrief.sh
```

## Race Day Timeline

### T-2 hours (Morning, before race)

```bash
# Ensure local InfluxDB ready
docker compose up -d influxdb signalk grafana astronomical

# Verify no cloud token (local only)
unset INFLUX_CLOUD_TOKEN
docker compose restart astronomical

# Open Grafana dashboard on iPad
# http://192.168.x.x:3001 (local WiFi)

# All data → localhost:8086 only ✅
```

### T=0 (Start line)

```
iPad shows:
├─ Heading (true, 0-360°)
├─ Speed (through water, knots)
├─ Wind angle/speed (relative)
├─ Performance vs target
├─ Position (lat/lon)
└─ Shift detection alerts

All 100% local, zero latency
```

### T+4h (Finish line)

```
Data on Pi:
├─ ~240,000 points (1 Hz × 4h)
├─ ~50-100 MB storage used
└─ ~80% of race logged

WiFi at dock:
└─ Now available ✅
```

### T+4h + 30min (Back to dock, WiFi connected)

```bash
# Run debrief script
./scripts/race-debrief.sh

# Automatically:
# ✅ Exports race data from local
# ✅ Uploads to cloud (if token set)
# ✅ Archives locally
# ✅ Commits to git
```

### T+4h + 1h (Analysis phase)

```
Cloud Grafana shows:
├─ Complete race visualization
├─ Heading evolution
├─ Speed profile
├─ Tactic timeline
├─ Comparison to previous races
└─ Export for report/article
```

## Grafana Dashboards

### Live Dashboard (During Race)

**Name:** "MidnightRider Live"

```
Panels:
├─ Heading (gauge, 0-360°)
├─ Speed Through Water (gauge, 0-12kt)
├─ Wind Angle (gauge, -180 to +180°)
├─ Wind Speed (gauge, 0-25kt)
├─ VMG to Waypoint (graph, last 30 min)
├─ Latitude / Longitude (map)
├─ Performance vs Target (%)
└─ Alerts (shift detected, gust, etc.)

Refresh: 5 seconds (live data)
Source: Local InfluxDB
```

### Debrief Dashboard (After Race)

**Name:** "Race Analysis"

```
Panels:
├─ Complete heading timeline (4h)
├─ Speed profile (4h)
├─ Tactic markers (manual annotations)
├─ Wind evolution (4h)
├─ Position track (map with time animation)
├─ Performance histogram
├─ Downwind vs upwind analysis
├─ Comparison to boat records
└─ Share link for crew debrief

Refresh: Manual
Source: Cloud InfluxDB
Annotations: Manual (add tack/gybe marks)
```

## Storage Management

### Local (Pi)

```
Before race: 5 GB free ✅
After 4h race: 4.9 GB free (100 MB used)
Retention: Keep 7-14 days locally
After 7 days: Archive to cloud/git
```

### Cloud

```
Unlimited storage ✅
Keep all races indefinitely
Search/analyze by date, name, conditions
Share with team
```

## Automation Scripts

### Setup

```bash
# Create race tracking directory
mkdir -p ~/races
git init ~/races

# Make scripts executable
chmod +x scripts/race-debrief.sh
chmod +x scripts/astronomical-data.sh
```

### Race Mode Toggle

```bash
#!/bin/bash
# scripts/race-mode.sh

if [ "$1" = "on" ]; then
  echo "🏁 RACE MODE: ON (local only)"
  unset INFLUX_CLOUD_TOKEN
  docker compose restart astronomical
  echo "✅ Cloud disabled, local only"
  
elif [ "$1" = "off" ]; then
  echo "🏁 RACE MODE: OFF (cloud enabled)"
  export INFLUX_CLOUD_TOKEN="your-token"
  docker compose restart astronomical
  echo "✅ Cloud enabled, hybrid mode"
  
else
  echo "Usage: race-mode.sh [on|off]"
fi
```

Make executable:
```bash
chmod +x scripts/race-mode.sh
```

## Backup Strategy

### After Every Race

```bash
# Local backup (on Pi)
docker exec influxdb influx backup /tmp/race-backup
tar -czf ~/races/backup-$(date +%Y%m%d-%H%M).tar.gz /tmp/race-backup

# Git commit
cd ~/races
git add .
git commit -m "Race $(date +%Y-%m-%d) backup"
git push origin main
```

### Cloud Backup (Optional)

```bash
# S3 or external cloud
aws s3 sync ~/races s3://my-sailing-data/races/
```

## Troubleshooting

### Local InfluxDB stops during race

```bash
# This shouldn't happen, but if it does:

# Check logs
docker logs influxdb | tail -50

# Restart immediately (preserves all data)
docker restart influxdb

# Verify data still there
influx query 'from(bucket:"signalk") |> range(start: -1h)' --org MidnightRider
```

### Cloud token expired after race

```bash
# Renew at https://cloud2.influxdata.com
# Update .env file
# Re-run debrief script
./scripts/race-debrief.sh
```

### Can't upload to cloud (internet issues)

```bash
# Keep local backup, try again later
cp /tmp/race-*.csv ~/races/pending/

# Once internet restored:
./scripts/race-debrief.sh
```

## Summary

| Phase | Data Store | Internet | Latency | Purpose |
|-------|-----------|----------|---------|---------|
| **Live Race** | Local | ❌ None | Minimal | Real-time racing |
| **Post-Race (Dock)** | Local + Cloud | ✅ Yes | Upload | Hybrid backup |
| **Debrief** | Cloud | ✅ Optional | Analysis | Detailed review |
| **Archive** | Local + Cloud + Git | ✅ Optional | Storage | Long-term records |

**Perfect workflow for competitive sailing!** 🏁⛵

---

**Updated:** 2026-04-20 02:35 EDT
**System:** MidnightRider J/30 (Raspberry Pi 4B)

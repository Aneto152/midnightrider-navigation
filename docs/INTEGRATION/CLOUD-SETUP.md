# Cloud Integration Guide — Midnight Rider Navigation

**⚠️ NOTE:** This guide focuses on **InfluxDB Cloud + Grafana Cloud only** (no Google Drive). For Google Drive backup, see separate documentation.

## Overview

**Architecture:** RPi (at sea) → Local InfluxDB → [Back at dock, WiFi] → InfluxDB Cloud → Grafana Cloud

This guide explains how to sync race data to the cloud and access it from anywhere after the race.

## Prerequisites

You will need:
1. **InfluxDB Cloud account** (Free tier = 30 days retention, sufficient for post-race analysis)
2. **Grafana Cloud account** (Free tier = 1 free stack)
3. **WiFi connection at dock** (to upload data)

### Prerequisites Check (run before race day)

```bash
# Check InfluxDB local is accessible
curl http://localhost:8086/health

# Check Grafana local is accessible
curl http://localhost:3001/api/health

# Verify .env contains cloud tokens
grep "INFLUX_CLOUD_TOKEN\|GRAFANA_CLOUD_API_KEY" .env
```

---

## Step 1: Create Cloud Accounts

### InfluxDB Cloud

1. Go to https://cloud2.influxdata.com/signup
2. Sign up with your email
3. Choose **Free tier** (30-day retention is fine)
4. Select region: **us-east-1** (AWS) or closest to you
5. Create organization
6. Create bucket named: `midnight_rider`
7. **Generate token:**
   - Go to **Data** → **API Tokens**
   - Click **Generate API Token**
   - Select **All Buckets** with **Read/Write**
   - Copy the token (looks like: `ABCD1234-1234...`)

**⚠️ Important:** Copy your exact InfluxDB Cloud URL from: **Account** → **Settings** → **Cloud URL**

**Save these values to .env:**
```bash
# Use the EXACT URL from your InfluxDB Cloud account
# Do NOT hardcode — it varies by region and account
INFLUX_CLOUD_URL=https://your-unique-url.aws.cloud2.influxdata.com
INFLUX_CLOUD_TOKEN=your_token_here
INFLUX_CLOUD_ORG=your-org-id-here
INFLUX_CLOUD_BUCKET=midnight_rider
```

### Grafana Cloud

1. Go to https://grafana.com/products/cloud/
2. Sign up (free account)
3. Create a stack (choose a name, e.g., "midnight-rider")
4. Wait for stack creation (2 min)
5. Note your stack URL: `https://yourname.grafana.net`
6. **Generate Service Account Token (NOT API Key):**
   - Go to **Administration** → **Service Accounts**
   - Click **Add service account**
   - Display name: `midnight-rider-sync`
   - Role: **Admin**
   - Click **Create**
   - Click **Add service account token**
   - Display name: `rpi-sync`
   - Click **Generate token**
   - ⚠️ **Copy the token IMMEDIATELY** (displayed only once!)

**Save to .env:**
```bash
GRAFANA_CLOUD_URL=https://yourname.grafana.net
GRAFANA_CLOUD_API_KEY=your_service_account_token_here
```

---

## Step 2: Configure InfluxDB Cloud Replication (Optional)

This step automatically syncs data from local InfluxDB to the cloud.

### Create InfluxDB Cloud Remote

**⚠️ CRITICAL:** Each `influx` command MUST include `--host "http://localhost:8086"` to target the local InfluxDB.

```bash
# First, get your InfluxDB Cloud org ID
# Go to https://cloud2.influxdata.com → Account → Organization ID

influx remote create \
  --name "influxdb-cloud" \
  --remote-url "${INFLUX_CLOUD_URL}" \
  --remote-api-token "${INFLUX_CLOUD_TOKEN}" \
  --remote-org-id "your-cloud-org-id" \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}" \
  --host "http://localhost:8086"
```

### Create Replication

```bash
# Get IDs
REMOTE_ID=$(influx remote list \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}" \
  --host "http://localhost:8086" \
  --json | jq -r '.[0].id')

BUCKET_ID=$(influx bucket list \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}" \
  --host "http://localhost:8086" \
  --json | jq -r '.[] | select(.name=="midnight_rider") | .id')

# Create replication
influx replication create \
  --name "midnight-rider-to-cloud" \
  --remote-id "${REMOTE_ID}" \
  --local-bucket-id "${BUCKET_ID}" \
  --remote-bucket "midnight_rider" \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}" \
  --host "http://localhost:8086"

# Verify
influx replication list \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}" \
  --host "http://localhost:8086"
```

---

## Step 3: Post-Race Workflow

### ⚠️ **DEADLINE CRITICAL**

**InfluxDB Cloud Free Tier = 30-day retention only.**

Block Island Race = **May 22, 2026** → **Data deleted after June 21, 2026**

**You MUST export/archive race data within 48 hours of returning to dock.**

### Run the sync script

```bash
bash scripts/post-race-cloud-sync.sh
```

This will:
1. ✅ Backup last 30 hours to local archive
2. ✅ Flush InfluxDB replication queue to cloud
3. ✅ Export Grafana dashboards

### Import Dashboards to Grafana Cloud

1. Go to your Grafana Cloud: `https://yourname.grafana.net`
2. **+ Create** → **Import dashboard**
3. Upload the dashboard JSON files from `/tmp/grafana-cloud-export-*/`
4. For each dashboard, create/assign a datasource:
   - Click **Create new datasource** → **InfluxDB**
   - **URL:** `${INFLUX_CLOUD_URL}` (use exact URL from Step 1)
   - **Organization:** (your InfluxDB Cloud org name)
   - **Token:** `${INFLUX_CLOUD_TOKEN}`
   - **Bucket:** `midnight_rider`
   - **Query Language:** ⚠️ **SELECT "Flux" (NOT InfluxQL)**
     - Midnight Rider dashboards use Flux language only
     - InfluxQL is not compatible
   - Click **Save & Test**
5. Complete the import and save dashboard

---

## Accessing Data

After sync complete:

### InfluxDB Cloud
- https://cloud2.influxdata.com
- Query race data directly in **Explore**
- Use Flux query language

### Grafana Cloud
- https://yourname.grafana.net
- View dashboards with live data
- All 9 dashboards accessible

---

## Troubleshooting

### "Replication failed"
- Check internet connection
- Verify `INFLUX_CLOUD_TOKEN` is valid (expires after 30 days)
- Verify `INFLUX_CLOUD_BUCKET` exists in cloud

### "Dashboard won't load"
- Verify datasource is set to **Flux** (not InfluxQL)
- Check `INFLUX_CLOUD_TOKEN` has Read access to `midnight_rider` bucket
- Verify bucket name is exactly `midnight_rider`

### "Import fails with JSON error"
- Use `python3 scripts/json_utils.py validate <file>` to check dashboard JSON
- Never use `sed`/`awk` on JSON files — use json_utils.py only

---

## FAQ

**Q: Do I need InfluxDB Cloud?**  
A: No, it's optional. Local backups are sufficient for post-race analysis.

**Q: What if I exceed 30 days?**  
A: Free tier data is deleted automatically. Upgrade to paid tier to extend retention.

**Q: Can I access live data during the race?**  
A: No, replication only works when connected to WiFi. During the race, only local monitoring works.

**Q: Do I need Grafana Cloud if I have local Grafana?**  
A: No, but cloud Grafana is accessible from any device (phone, tablet) after the race.

**Q: Which Grafana region should I choose?**  
A: US region is default. Choose based on your location for lower latency.

---

## More Info

- InfluxDB Cloud docs: https://docs.influxdata.com/influxdb/cloud/
- Grafana Cloud docs: https://grafana.com/docs/grafana-cloud/
- Flux query language: https://docs.influxdata.com/influxdb/cloud/query-data/get-started/

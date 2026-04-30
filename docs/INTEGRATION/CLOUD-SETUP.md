# Cloud Integration Guide — Midnight Rider Navigation

## Overview

**Architecture:** RPi (at sea) → Local InfluxDB → [Back at dock, WiFi] → InfluxDB Cloud → Grafana Cloud

This guide explains how to sync race data to the cloud and access it from anywhere after the race.

## Prerequisites

You will need:
1. **InfluxDB Cloud account** (Free tier = 30 days retention, sufficient for post-race analysis)
2. **Grafana Cloud account** (Free tier = 1 free stack)
3. **Google Drive** (for backup)
4. **rclone** (for Google Drive sync)
5. **WiFi connection at dock** (to upload data)

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

**Save these values to .env:**
```bash
INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
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
6. **Generate API key:**
   - Go to **Configuration** → **API Keys**
   - Click **New API key**
   - Scope: **Admin**
   - Copy the key

**Save to .env:**
```bash
GRAFANA_CLOUD_URL=https://yourname.grafana.net
GRAFANA_CLOUD_API_KEY=your_key_here
```

### Google Drive (for rclone)

1. Already have? Continue to Step 2
2. Don't have? Just use your existing Google account
3. rclone will handle OAuth authentication

## Step 2: Configure rclone

### Install rclone

```bash
curl https://rclone.org/install.sh | sudo bash
```

### Add Google Drive remote

```bash
rclone config

# Follow prompts:
# - Name: gdrive
# - Storage: Google Drive (option 13 or search "drive")
# - Client ID: Leave blank (use built-in)
# - Use advanced config? No
# - Use browser for auth? Yes → Opens browser → Approve → Paste token
# - Confirm config: Yes
```

Test:
```bash
rclone ls gdrive:
```

## Step 3: Configure InfluxDB Cloud Replication (Optional)

This step automatically syncs data from local InfluxDB to the cloud.

### Create InfluxDB Cloud Remote

```bash
# First, get your InfluxDB Cloud org ID
# Go to https://cloud2.influxdata.com → Account → Org ID

influx remote create \
  --name "influxdb-cloud" \
  --remote-url "https://us-east-1-1.aws.cloud2.influxdata.com" \
  --remote-api-token "${INFLUX_CLOUD_TOKEN}" \
  --remote-org-id "your-cloud-org-id" \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}" \
  --host "http://localhost:8086"
```

### Create Replication

```bash
# Get IDs
REMOTE_ID=$(influx remote list --org "${INFLUX_ORG}" --token "${INFLUX_TOKEN}" --json | jq -r '.[0].id')
BUCKET_ID=$(influx bucket list --org "${INFLUX_ORG}" --token "${INFLUX_TOKEN}" --json | jq -r '.[] | select(.name=="midnight_rider") | .id')

# Create replication
influx replication create \
  --name "midnight-rider-to-cloud" \
  --remote-id "${REMOTE_ID}" \
  --local-bucket-id "${BUCKET_ID}" \
  --remote-bucket "midnight_rider" \
  --org "${INFLUX_ORG}" \
  --token "${INFLUX_TOKEN}"

# Verify
influx replication list --org "${INFLUX_ORG}" --token "${INFLUX_TOKEN}"
```

## Step 4: Post-Race Workflow

After the race, when back at dock with WiFi:

### Run the sync script

```bash
bash scripts/post-race-cloud-sync.sh
```

This will:
1. ✅ Backup last 30 hours to Google Drive
2. ✅ Flush InfluxDB replication queue
3. ✅ Export Grafana dashboards

### Import Dashboards to Grafana Cloud

1. Go to your Grafana Cloud: `https://yourname.grafana.net`
2. **+ Create** → **Import dashboard**
3. Upload the dashboard JSON files from `/tmp/grafana-cloud-export-*/`
4. For datasource: **Create new** → **InfluxDB**
   - URL: `https://us-east-1-1.aws.cloud2.influxdata.com`
   - Organization: (your InfluxDB Cloud org)
   - Token: `${INFLUX_CLOUD_TOKEN}`
   - Bucket: `midnight_rider`
5. Save

## Accessing Data

After sync complete:

### InfluxDB Cloud
- https://cloud2.influxdata.com
- Query race data directly in Explore

### Grafana Cloud
- https://yourname.grafana.net
- View dashboards with live data

### Google Drive
- https://drive.google.com
- Folder: **MidnightRider/InfluxDB-backups/**
- Contains tar.gz archives of race data

## Troubleshooting

### "Replication failed"
- Check internet connection
- Verify cloud token is valid
- Check InfluxDB Cloud bucket exists

### "rclone: gdrive remote not found"
- Run `rclone config` and create remote named `gdrive`

### "Grafana auth failed"
- Verify GRAFANA_PASSWORD in .env
- Check admin user still exists

## FAQ

**Q: Do I need to sync to cloud?**  
A: No, it's optional. Local backups to Google Drive are sufficient for post-race analysis.

**Q: What's the retention policy?**  
A: InfluxDB Cloud Free = 30 days. After that, data is deleted unless you upgrade.

**Q: Can I access live data during the race?**  
A: No, replication only works when connected to WiFi. During the race, only local monitoring works.

**Q: Do I need Grafana Cloud if I have local Grafana?**  
A: No, but cloud Grafana is accessible from any device after the race.

## More Info

- InfluxDB Cloud docs: https://docs.influxdata.com/influxdb/cloud/
- Grafana Cloud docs: https://grafana.com/docs/grafana-cloud/
- rclone Google Drive: https://rclone.org/drive/

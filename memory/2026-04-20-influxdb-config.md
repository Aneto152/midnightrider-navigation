# InfluxDB Configuration — Local + Cloud Hybrid (2026-04-20)

## Decision
✅ **KEEP CLOUD OPTION — Hybrid Configuration**

Support both local AND cloud when token is available.

## Current Status

### Local InfluxDB ✅ ACTIVE
```
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk
```

### Cloud InfluxDB ⏳ INACTIVE (Token Expired)
```
INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
INFLUX_CLOUD_TOKEN=<EXPIRED>
INFLUX_CLOUD_ORG=48a34d6463cef7c9
INFLUX_CLOUD_BUCKET=signalk-cloud
```

## How to Activate Cloud

1. Go to https://cloud2.influxdata.com
2. Log in, navigate Settings → API Tokens
3. Create new token (read+write on signalk-cloud bucket)
4. Update `INFLUX_CLOUD_TOKEN` in:
   - docker-compose.yml, OR
   - .env file (recommended for secrets)
5. Restart: `docker compose restart astronomical`

## Architecture

```
Data Sources
└─ Signal K + Scripts
   ├─ → InfluxDB Local (always) ✅
   └─ → InfluxDB Cloud (if token set) ⏳
       ↓
Grafana
├─ Primary source: Local
└─ Backup: Cloud
```

## Advantages

- **Local-only works now** (no cloud needed)
- **Cloud optional** (add anytime)
- **Both simultaneously** (automatic redundancy)
- **Fallback** (if cloud down, local still works)
- **On-boat** (works without internet)
- **Remote access** (when internet available)

## Scripts Support

All scripts auto-detect `INFLUX_CLOUD_TOKEN`:
- If set → sends to both local + cloud
- If not set → sends to local only

No code changes required when activating cloud!

## Security

Use `.env` file for cloud token (not in docker-compose.yml):

```bash
# /home/aneto/docker/signalk/.env
INFLUX_CLOUD_TOKEN=<new-token>
INFLUX_CLOUD_URL=https://us-east-1-1.aws.cloud2.influxdata.com
INFLUX_CLOUD_ORG=48a34d6463cef7c9
INFLUX_CLOUD_BUCKET=signalk-cloud
```

Then in docker-compose.yml:
```yaml
env_file: .env
```

Add `.env` to `.gitignore` (keep secrets out of git)

## Data Replication

Daily sync to cloud (optional cron):
```bash
0 3 * * * /home/aneto/docker/signalk/scripts/replicate-to-cloud.sh
```

Script queries local, writes to cloud if token available.

---
**Updated:** 2026-04-20 02:32 EDT
**Decision:** Hybrid (Local + Cloud optional)
**System:** MidnightRider J/30

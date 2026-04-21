# InfluxDB — LOCAL ONLY (2026-04-20)

## Decision
✅ **InfluxDB Cloud token expired → USE LOCAL ONLY**

## Configuration Summary

### InfluxDB Local
- **Host:** localhost:8086 (or IP:8086 on network)
- **Bucket:** signalk
- **Org:** MidnightRider
- **Token:** `4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==`
- **Cloud:** DISABLED (token expired, no cloud sync)

### Docker Compose Configuration
All services use **localhost:8086** only:

```yaml
environment:
  - INFLUX_URL=http://localhost:8086
  - INFLUX_TOKEN=4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
  - INFLUX_ORG=MidnightRider
  - INFLUX_BUCKET=signalk
```

### Services Using Local InfluxDB

| Service | Config File | Port |
|---------|-------------|------|
| astronomical | docker-compose.yml | 8086 |
| astronomical-cron | docker-compose.yml | 8086 |
| signalk-to-influxdb2 | ~/.signalk/config.json | 8086 |
| Grafana | dashboard queries | 8086 |
| MCP Server | mcp/astronomical-server.js | 8086 |

### Deployment

**All containers use:**
```bash
docker compose up -d influxdb grafana signalk astronomical
```

**No cloud configuration needed.**

## Data Flow

```
GPS/NMEA/Instruments → Signal K → InfluxDB Local → Grafana
Astronomical Data → Script → InfluxDB Local → Grafana
```

## Backup Strategy

Since no cloud, recommend:
1. **Local snapshots:** `influx backup /backup/signalk-$(date +%Y%m%d)`
2. **Git:** Archive InfluxDB config in GitHub
3. **External:** Periodic rsync to NAS/cloud if needed

## Cloud Future

If cloud sync needed later:
1. Renew Cloud token
2. Add cloud config to docker-compose.yml
3. No code changes required (uses same env vars)

## Status

✅ Local InfluxDB working
✅ All services configured for localhost:8086
✅ No external dependencies
✅ Data stored locally on Raspberry Pi
✅ Accessible on-boat via WiFi AP

---
**Updated:** 2026-04-20 02:30 EDT
**System:** MidnightRider J/30 (Raspberry Pi 4B)

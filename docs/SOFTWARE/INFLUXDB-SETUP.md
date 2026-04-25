# INFLUXDB v2 SETUP GUIDE

**Version:** 2.7.x  
**Database:** midnight_rider (bucket: signalk)  
**Port:** 8086  
**Date:** 2026-04-25

---

## SERVICE MANAGEMENT

```bash
# Check status
systemctl status influxdb

# Start/Stop
sudo systemctl start influxdb
sudo systemctl stop influxdb

# Restart
sudo systemctl restart influxdb

# Logs
sudo journalctl -u influxdb -n 50
```

---

## KEY SETTINGS

**Location:** `/etc/influxdb/influxdb.conf`

### Data Storage

```
[data]
  dir = "/var/lib/influxdb/data"
  index-version = "tsi1"           # Compressed index (faster)

[retention]
  enabled = true
  check-interval = "30m"
```

---

## DATA STRUCTURE

### Organization
- **Org:** midnight_rider
- **Bucket:** signalk
- **Retention:** 365 days (1 year)

### Measurement: `signalk`

**Tags (indexed):**
```
measurement=signalk,
  source=um982-gps,           # or: wit-imu, wave-analyzer, etc.
  instance=1
```

**Fields (values):**
```
latitude=41.172,
longitude=-71.550,
headingTrue=3.98,
roll=0.1,
pitch=-0.05,
acceleration_x=0.2,
acceleration_y=-0.1,
acceleration_z=9.7,
waveHeight=1.5,
wavePeriod=8.2,
...
```

---

## API ACCESS

### Query Data

```bash
# Via curl
curl -X POST "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token [TOKEN]" \
  -H "Content-type: application/vnd.flux" \
  -d 'from(bucket:"signalk") |> range(start:-1h)'

# Or use Grafana (easier)
```

### Health Check

```bash
curl http://localhost:8086/api/v2/health

# Expected:
# {
#   "status": "ok",
#   "message": "ready for queries and writes"
# }
```

---

## STORAGE MONITORING

```bash
# Check disk usage
du -sh /var/lib/influxdb/data

# Typical race:
# 5-hour race @ 1 sec resolution = ~18,000 points = ~5-10 MB
```

---

## BACKUP & RESTORE

### Backup

```bash
# Export all data
influx backup /backup/influxdb-2026-05-22 \
  --token [TOKEN] \
  --org midnight_rider
```

### Restore

```bash
influx restore /backup/influxdb-2026-05-22 \
  --token [TOKEN] \
  --org midnight_rider
```

---

## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| Port 8086 not responding | Restart: `systemctl restart influxdb` |
| "permission denied" | Check file permissions: `ls -la /var/lib/influxdb/` |
| High RAM usage | Restart (clears cache) or delete old data if needed |
| Write errors | Check Signal K plugin config (token valid?) |

---

## RACING OPERATION

**Zero manual intervention needed:**
- Signal K plugin auto-writes every 1 sec
- Data persists automatically
- Backups: handled post-race

---

**Status:** ✅ Ready  
**Last Updated:** 2026-04-25

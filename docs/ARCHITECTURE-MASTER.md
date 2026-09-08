# Midnight Rider Architecture Master Document

**Version:** 1.1  
**Last Updated:** 2026-09-08  
**Status:** Production

---

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Midnight Rider System                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐         ┌──────────────────┐            │
│  │  Hardware       │         │  Signal K Hub    │            │
│  │  (Sensors)      │────────▶│  (Port 3000)     │            │
│  │  • GNSS         │         │  • Aggregation   │            │
│  │  • IMU (BLE)    │         │  • Normalization │            │
│  │  • Wind/Speed   │         │  • Distribution  │            │
│  │  • Battery      │         │                  │            │
│  └─────────────────┘         └─────────┬────────┘            │
│                                        │                    │
│                         ┌──────────────▼─────────────┐      │
│                         │  Authentication Chain      │      │
│                         │  1. Docker-internal CLI    │      │
│                         │  2. Token File             │      │
│                         │  3. Environment Variable   │      │
│                         └──────────────┬─────────────┘      │
│                                        │                    │
│  ┌──────────────────────────────────────▼──────────────┐    │
│  │  InfluxDB (Port 8086)                              │    │
│  │  • Time-series storage (midnight_rider bucket)     │    │
│  │  • Retention: 7 days (default)                      │    │
│  │  • Secure auth: Docker exec (no CLI token)          │    │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  Grafana (Port 3001)                                │   │
│  │  • 9 Dashboards (COCKPIT, WIND, PERFORMANCE, etc.)  │   │
│  │  • 65 Alerts                                        │   │
│  │  • Datasource: InfluxDB (uid:efifgp8jvgj5sf)        │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  Portal (Port 8888) + iPad/Browser                  │   │
│  │  • Real-time navigation UI                          │   │
│  │  • Proxy to Regatta (5000)                          │   │
│  │  • Offline support with local cache                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AI Coaching & Reporting                            │   │
│  │  • Media Man (WhatsApp reporting)                    │   │
│  │  • Claude MCP tools (tactics, strategy)              │   │
│  │  • Async message queue for offline mode              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Authentication & Security

### New: Docker-Internal InfluxDB Auth (v1.1)

**Problem Solved:** InfluxDB tokens previously stored in env vars or files, risking exposure via:
- `ps aux` command
- Bash history
- /proc/PID/environ
- Docker logs

**Solution:** Retrieve tokens inside Docker container using `docker exec`:

```
┌─────────────────────────────────────────┐
│  Host (untrusted for token visibility)  │
│                                         │
│  docker exec influxdb \                 │
│    influx auth list --format json       │
│    (only returns inside container)      │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Container (token stays here)   │   │
│  │                                 │   │
│  │  influx auth list json output   │   │
│  │  ────────────────────────────   │   │
│  │  (token bytes returned to host) │   │
│  │  (not exposed to ps/env/etc)    │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Key Security Properties:**
- ✅ Token command not visible in `ps aux`
- ✅ Token not stored in host environment
- ✅ Token not logged to host logs
- ✅ Automatic cache expiration (per session)
- ✅ Graceful fallback if Docker unavailable

### Auth Provider Chain

```python
AuthProviderChain([
    DockerInternalCliAuthProvider(),     # Try first
    SecureTokenFileAuthProvider(),       # Fallback
    EnvironmentTokenAuthProvider(),      # Last resort
]).get_token()
```

| Provider | Method | Security | Availability |
|----------|--------|----------|--------------|
| Docker CLI | `docker exec` + `influx auth list` | ⭐⭐⭐⭐⭐ | Docker, compose file, running container |
| Token File | Read from `~/.influxdb-token` | ⭐⭐⭐ | File on disk, mode 0600 |
| Environment | Read `$INFLUXDB_TOKEN` | ⭐⭐ | Env var set |

---

## Data Flow

### 1. Signal K → InfluxDB

```
Sensor Data
    ↓
Signal K Server (port 3000)
    │
    ├─ Validates & normalizes
    ├─ Converts NMEA to JSON
    ├─ Aggregates multiple sources
    │
    ▼
InfluxDB (port 8086)
    │
    ├─ Signal K plugin writes to midnight_rider bucket
    ├─ Line Protocol format
    ├─ 7-day retention (configurable)
    │
    ▼
Time-Series Database (persisted)
```

### 2. InfluxDB → Grafana

```
Grafana Dashboard
    ↓
Query InfluxDB (Flux language)
    │
    ├─ Authentication: DockerInternalCliAuthProvider
    ├─ Datasource UID: efifgp8jvgj5sf (IMPORTANT)
    ├─ Bucket: midnight_rider
    │
    ▼
InfluxDB Search
    │
    ├─ Scans time-series by measurement/tag
    ├─ Applies time filters (-1h, -7d, etc.)
    ├─ Returns CSV/JSON
    │
    ▼
Grafana Visualization
    ├─ Panels (gauge, graph, table, heatmap)
    ├─ 5-second refresh (COCKPIT dashboard)
    ├─ Real-time alerts on 65 metric thresholds
```

### 3. Portal Access

```
Browser Request (iPad/Desktop)
    ↓
Portal Server (port 8888)
    │
    ├─ Serves /portal directory only
    ├─ Proxies /grafana → Grafana (3001)
    ├─ Proxies /regatta → Regatta (5000)
    │
    ├─ No credential exposure (reverse proxy)
    ├─ Offline cache (localStorage)
    │
    ▼
Live Navigation UI
```

---

## Component Details

### Signal K Configuration

**File:** `config/signalk-plugins/signalk-to-influxdb2.json`

```json
{
  "enabled": true,
  "plugin": "signalk-to-influxdb2",
  "config": {
    "url": "http://localhost:8086",
    "org": "midnight-rider",
    "bucket": "midnight_rider",
    "token": "${INFLUXDB_TOKEN}"
  }
}
```

**Data Written:**
- `measurement`: signalk (or plugin-specific names)
- `tags`: source, vessel, context
- `fields`: numeric values (heading, speed, wind, etc.)
- `timestamp`: UTC

### InfluxDB Configuration

**Bucket:** `midnight_rider`
- **Retention:** 7 days (604,800 seconds)
- **Read/Write:** InfluxDB Service Token
- **Org:** midnight-rider

**Authentication:**
- Token managed via DockerInternalCliAuthProvider
- Docker service: `influxdb`
- Compose file: `docker-compose.yml`

### Grafana Configuration

**Datasource UID:** `efifgp8jvgj5sf`
- **Type:** InfluxDB
- **Query Language:** Flux
- **Authentication:** Token (from docker-internal provider)

**Dashboard IDs:**
1. 1 - COCKPIT (5s refresh)
2. 2 - ENVIRONMENT (30s refresh)
3. 3 - PERFORMANCE (5s refresh)
4. 4 - WIND & CURRENT (10s refresh)
5. 5 - COMPETITIVE (30s refresh)
6. 6 - ELECTRICAL (30s refresh)
7. 7 - RACE (5s refresh)
8. 8 - ALERTS (10s refresh)
9. 9 - CREW (30s refresh)

### Portal Configuration

**Service:** `midnightrider-portal`
- **Port:** 8888
- **Working Directory:** `/home/pi/midnightrider-navigation/portal`
- **Command:** `python3 -m http.server 8888 --directory portal`

**Endpoints:**
- `/` → `portal/index.html` (navigation UI)
- `/grafana/` → Proxied to `http://localhost:3001`
- `/regatta/` → Proxied to `http://localhost:5000`
- `/.env` → ❌ 404 (protected)
- `/viewer.html` → ✅ 200 (public)

---

## Security Model

### Threat Model

| Threat | Impact | Mitigation |
|--------|--------|-----------|
| InfluxDB token exposure via ps/env | Critical | Docker-internal auth (v1.1) |
| Docker socket compromise | High | Restrict docker group membership |
| File token theft | Medium | File mode 0600, encrypted FS |
| Env var exposure in systemd | Medium | Use docker-internal method |
| Portal .env leak | High | HTTP 404 response configured |
| Grafana API token leak | Medium | Rotate token quarterly |
| Signal K auth bypass | Low | Local network only (default) |

### Recommendations

1. **Always use Docker-internal auth** for production
2. **Restrict docker socket access:**
   ```bash
   sudo gpasswd -a $USER docker
   sudo systemctl restart docker
   ```
3. **Use token file only if Docker unavailable**
4. **Rotate InfluxDB tokens quarterly**
5. **Enable Grafana SSO** for multi-user deployments
6. **Monitor /var/log/syslog** for auth attempts

---

## Deployment Checklist

### Pre-Launch

- [ ] Docker Compose volumes created
- [ ] InfluxDB initialized with `midnight_rider` bucket
- [ ] Signal K configured with InfluxDB plugin
- [ ] Grafana provisioned with datasource + 9 dashboards
- [ ] Portal systemd service enabled
- [ ] Authentication provider tested (docker-internal)
- [ ] Firewall rules configured (Signal K 3000, Grafana 3001, Portal 8888)
- [ ] Backup strategy in place (InfluxDB daily backups)

### Post-Launch

- [ ] Health check: `curl http://localhost:3001/api/health`
- [ ] Health check: `curl http://localhost:8086/health`
- [ ] Portal accessible: `http://midnightrider.local:8888`
- [ ] Data flowing: Check InfluxDB bucket size
- [ ] Dashboards populated: At least 1 graph per dashboard
- [ ] Alerts configured: Test alert channel

---

## Monitoring & Observability

### Key Metrics

| Metric | Source | Threshold |
|--------|--------|-----------|
| InfluxDB Health | `/health` endpoint | Should be 200 OK |
| Signal K Uptime | Systemd status | > 99% |
| Grafana Uptime | Docker health check | > 99.9% |
| Portal Uptime | Systemd status | > 99.9% |
| InfluxDB Storage | `du -sh /var/lib/influxdb2` | < 50GB |
| Query Latency | Grafana query time | < 5 seconds |

### Alerting

65 alerts configured in Grafana:
- Wind gust threshold (> 25 kts)
- Battery SOC (< 20%)
- Speed anomalies
- Attitude (roll/pitch) warnings
- Network latency
- Data gap detection

---

## Maintenance

### Daily

- Monitor InfluxDB storage usage
- Check alert notifications

### Weekly

- Review Grafana logs
- Verify data collection quality
- Test Portal offline mode

### Monthly

- Rotate InfluxDB token (via docker-internal)
- Update firmware (if applicable)
- Review security logs

### Quarterly

- Backup InfluxDB data
- Update Docker images
- Security audit (OWASP top 10)

---

## Roadmap

### v1.2 (Q4 2026)

- [ ] Kubernetes deployment support
- [ ] InfluxDB Cloud integration
- [ ] Prometheus exporter

### v2.0 (2027)

- [ ] Time-sync via NTP/GPS
- [ ] Multi-vessel federation
- [ ] Real-time AIS integration
- [ ] Satellite backup (Iridium)

---

## References

- **InfluxDB:** https://docs.influxdata.com/influxdb/v2.0/
- **Signal K:** https://signalk.org/
- **Grafana:** https://grafana.com/docs/
- **Flux Language:** https://docs.influxdata.com/flux/v0.x/
- **Docker:** https://docs.docker.com/

---

**Maintained by:** Denis Lafarge & OpenClaw AI  
**Last Verified:** 2026-09-08  
**Next Review:** 2026-12-08

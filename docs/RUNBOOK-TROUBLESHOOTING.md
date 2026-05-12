# RUNBOOK — Troubleshooting Midnight Rider

**Last Updated:** 2026-05-12  
**Based on:** Real incidents from May 12 session  
**Quick Reference:** 5-minute diagnostics below

---

## 5-Minute Diagnostic

Run this to check all systems:

```bash
#!/bin/bash
echo "=== Signal K ===" && systemctl is-active signalk
echo "=== Docker Services ===" && docker compose ps --format "table {{.Service}}\t{{.Status}}"
echo "=== Grafana Datasource ===" && \
  curl -s http://localhost:3001/api/datasources/uid/efifgp8jvgj5sf/health | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('status')} — {d.get('message','')}\")"
echo "=== InfluxDB Token ===" && \
  source ~/.openclaw/workspace/.env && \
  curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Authorization: Token $INFLUX_TOKEN" http://localhost:8086/health
echo "=== Portal ===" && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost/
echo "=== mDNS Resolution ===" && hostname -I
```

---

## Problem 1: Grafana — All Panels Show "NO DATA" or "unauthorized"

**Symptoms:**
- All dashboard panels: "NO DATA"
- Datasource health: "ERROR — unauthorized: unauthorized access error reading buckets"

**Root Cause (May 12 incident):**
INFLUX_TOKEN not in Grafana container environment → `${INFLUX_TOKEN}` placeholder = empty string → HTTP 401

### Diagnosis

```bash
# Test 1: Does the token work?
source ~/.openclaw/workspace/.env
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Authorization: Token $INFLUX_TOKEN" http://localhost:8086/health

# Test 2: Does Grafana have the token in its environment?
docker exec grafana env | grep INFLUX_TOKEN

# Test 3: Can Grafana reach InfluxDB?
docker exec grafana curl -s -o /dev/null -w "%{http_code}\n" http://influxdb:8086/health
```

### Solution Decision Tree

| Test 1 | Test 2 | Test 3 | Solution |
|--------|--------|--------|----------|
| 200 | INFLUX_TOKEN=xxx | 200 | Datasource config broken in Grafana — see Grafana logs |
| 200 | (empty) | 200 | `docker compose up -d grafana` (token not in container env) |
| 401 | N/A | 200 | Token invalid/revoked — `bash scripts/rotate-token.sh` |
| ANY | ANY | 000 | InfluxDB crashed — `docker compose restart influxdb` |

**Most Common Fix:**
```bash
docker compose up -d grafana
sleep 8
docker exec grafana env | grep INFLUX_TOKEN  # Should show token now
```

---

## Problem 2: Signal K — No NMEA Data

**Symptoms:**
- SOG (Speed Over Ground) = 0 or null
- COG (Course Over Ground) = 0 or null
- Heading = 0 or null
- GPS not updating

### Diagnosis

```bash
# Check Signal K is running
systemctl status signalk

# Check if it has data
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/speedOverGround

# Check actual data stream (should update frequently)
curl -s http://localhost:3000/signalk/v1/stream | head -50
```

### Common Causes

| Cause | Check | Fix |
|-------|-------|-----|
| Signal K crashed | `systemctl status signalk` | `sudo systemctl restart signalk` |
| No NMEA source connected | Check /dev/ttyUSB* devices exist | Connect GPS/compass/loch cables |
| Plugin disabled | http://localhost:3000 → Admin → Plugins | Enable UM982, loch, compass plugins |
| InfluxDB not writing | Query: `from(bucket:"midnight_rider") \| range(start:-5m) \| last()` | Check plugin config in Signal K |

**Standard Recovery:**
```bash
sudo systemctl restart signalk
sleep 5
systemctl is-active signalk
# Then wait 30 seconds for data to flow into InfluxDB
```

---

## Problem 3: Portal Inaccessible (midnightrider.local)

**Symptoms:**
- http://midnightrider.local returns "connection refused"
- http://192.168.1.167:8888 works fine
- http://192.168.1.167 (port 80) shows nginx error

### Diagnosis

```bash
# Check all components
echo "nginx:" && systemctl is-active nginx
echo "portal:" && docker compose ps portal
echo "mDNS:" && systemctl is-active avahi-daemon

# Check mDNS is advertising correct IP
hostname -I  # Should show 192.168.1.167 ONLY

# Test nginx reverse proxy
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/  # Should be 200
curl -s http://localhost/ | head -5
```

### Solution Decision Tree

| nginx | portal | mDNS | Solution |
|-------|--------|------|----------|
| inactive | running | ✓ | `sudo systemctl restart nginx` |
| active | inactive | ✓ | `docker compose up -d portal` |
| active | running | inactive | `sudo systemctl restart avahi-daemon` |
| active | running | wrong IP | Check WiFi config (should be 192.168.1.167 only) |

**Complete Reset:**
```bash
sudo systemctl restart nginx avahi-daemon
docker compose restart portal
sleep 5
# Test direct
curl -s http://localhost:8888/ | head -5
# Test via nginx
curl -s http://localhost/ | head -5
# Test mDNS (may take 10 seconds)
curl -s http://midnightrider.local/ | head -5
```

---

## Problem 4: Grafana Iframes Empty in Portal

**Symptoms:**
- Portal loads fine
- Grafana iframe shows login screen instead of dashboard

**Root Cause:**
GF_AUTH_ANONYMOUS_ENABLED was set to false

### Diagnosis

```bash
# Check Grafana config
docker exec grafana env | grep "GF_AUTH"
# Should show: GF_AUTH_ANONYMOUS_ENABLED=true

# Verify docker-compose.yml
grep "GF_AUTH" docker-compose.yml
```

### Solution

```bash
# Fix docker-compose.yml if needed
grep "GF_AUTH_ANONYMOUS_ENABLED=false" docker-compose.yml && \
  echo "❌ Anonymous auth disabled — fix required"

# Restore it
docker compose up -d grafana
sleep 8

# Verify
docker exec grafana env | grep GF_AUTH_ANONYMOUS_ENABLED
# Should show: true
```

---

## Problem 5: InfluxDB — Missing Data (No points in last hour)

**Symptoms:**
- InfluxDB running, but time range "Last 1 hour" returns no data
- Historical data (last week) is present
- Dashboard shows "No data" for recent panels

### Causes

1. **Signal K crashed** → stopped writing data
2. **Plugin disabled** → signalk-to-influxdb2 not running
3. **No sensor input** → indoors with no GPS/compass

### Diagnosis

```bash
# Check Signal K is writing to InfluxDB
source ~/.openclaw/workspace/.env
curl -s -X POST "http://localhost:8086/api/v2/query?org=MidnightRider" \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"midnight_rider") |> range(start:-5m) |> last()' | head -100

# If empty: Signal K is not writing
# Check Signal K plugin: http://localhost:3000 → Admin → Plugin Config Data
```

### Solution

```bash
# Restart Signal K to force flush
sudo systemctl restart signalk
sleep 5

# Wait for data to appear
sleep 30

# Re-query InfluxDB
source ~/.openclaw/workspace/.env
curl -s -X POST "http://localhost:8086/api/v2/query?org=MidnightRider" \
  -H "Authorization: Token $INFLUX_TOKEN" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"midnight_rider") |> range(start:-5m) |> last()' | head -100
```

---

## Emergency Fallbacks (May 19 / May 22)

If one system is down, others work independently:

| System | URL | What It Shows | Fallback If Down |
|--------|-----|---------------|------------------|
| Portal | http://midnightrider.local | Grafana iframes + night mode | Direct IP: 192.168.1.167:8888 |
| Grafana | http://midnightrider.local/grafana/ | 264 dashboards, live data | Direct: 192.168.1.167:3001 |
| Signal K | http://192.168.1.167:3000 | Raw sensor data + NMEA | None (native systemd) |
| InfluxDB | (HTTP API only) | Data storage | Restart: `docker compose restart influxdb` |

**Tier 1 (Critical):** Signal K (systemd) — if down, nothing works  
**Tier 2 (Important):** InfluxDB (Docker) — if down, no history, but sensors still visible in Signal K  
**Tier 3 (Nice-to-have):** Grafana/Portal — if down, use direct IPs

---

## Survival Rules for Race Day

| Time | Priority | Service | Action | Command |
|------|----------|---------|--------|---------|
| Race start | Check all | All | Run 5-min diagnostic | See top of this runbook |
| Every 4h | Monitor | Grafana | Verify dashboards live | `curl http://localhost:3001/...` |
| If NO DATA | CRITICAL | Signal K | Restart | `sudo systemctl restart signalk` |
| If NO DATA | CRITICAL | InfluxDB | Restart | `docker compose restart influxdb` |
| If inaccessible | HIGH | nginx/mDNS | Restart | `sudo systemctl restart nginx avahi-daemon` |
| If token expires | MEDIUM | Grafana | Rotate | `bash scripts/rotate-token.sh` |

---

## Log Locations

```bash
# Signal K
journalctl -u signalk -n 50 -f

# Docker containers
docker logs grafana -n 50 -f
docker logs influxdb -n 50 -f
docker logs portal -n 50 -f

# nginx
sudo tail -50 /var/log/nginx/error.log
sudo tail -50 /var/log/nginx/access.log

# Avahi (mDNS)
sudo journalctl -u avahi-daemon -n 50 -f

# System
dmesg | tail -20
free -h  # Memory
df -h    # Disk
```

---

## Contact & References

- **GitHub:** https://github.com/Aneto152/midnightrider-navigation
- **Dust MidnightCoordinator:** Message with prompt from MEMORY.md
- **Emergency token rotation:** `bash scripts/rotate-token.sh`
- **Complete guide:** docs/RUNBOOK-TOKEN-ROTATION.md

# Midnight Rider — Alert Rules Deployment Guide

**Status:** Phase 1 — 18 alerts ready for deployment  
**Target Release:** May 19, 2026 (Field Test)  
**Total Planned:** 69 alerts (6 categories)

---

## Phase 1: 18 Deployable Alerts NOW

✅ **Ready to deploy (data available):**
- SYSTEM: 9 alerts (services, hardware, instruments)
- PERFORMANCE: 2 alerts (heel, pitch)
- WEATHER/SEA: 1 alert (shallow water)
- RACING: 4 alerts (start timers)
- CREW: 2 alerts (watch rotation)

⏳ **Pending Phase 2 (hardware integration):**
- 30 alerts (wind, current, waves, electrical, etc.)

---

## Files

| File | Purpose |
|---|---|
| `alert-rules-phase1.yaml` | Grafana Alerting rule definitions (18 alerts) |
| `ALERTS-DEPLOYMENT-GUIDE.md` | This file |
| `ALERTS-CATALOG.md` | Complete specification (69 alerts) |

---

## Deployment Methods

### Option 1: Grafana Web UI (Recommended)

1. Open Grafana: **http://localhost:3001**
2. Navigate: **Alerting → Alert Rules**
3. Click: **+ Create Alert Rule**
4. Configure rule:
   - **Rule name:** (from YAML)
   - **Evaluate every:** 1m
   - **For:** (from YAML, e.g., "30s")
   - **Query:** (Flux query from alert-rules-phase1.yaml)
   - **Condition:** `A` (threshold/comparison)
   - **Annotations:**
     - `description`: (from YAML)
     - `severity`: (from YAML)
   - **Labels:**
     - `category`: (SYSTEM, PERFORMANCE, etc.)
5. Click: **Create**
6. Repeat for all 18 alerts

**Time:** ~30 min for all 18 alerts

---

### Option 2: API Import (Grafana 9+)

```bash
curl -X POST \
  -H "Content-Type: application/yaml" \
  -H "Authorization: Bearer ${GRAFANA_API_TOKEN}" \
  --data-binary @alert-rules-phase1.yaml \
  http://localhost:3001/api/ruler/grafana/rules
```

**Requirements:**
- Grafana API token (Admin role)
- YAML format compatible with Grafana Alerting

---

### Option 3: CLI Provisioning

```bash
# Copy rules to provisioning directory
cp alert-rules-phase1.yaml /etc/grafana/provisioning/rules/

# Restart Grafana
sudo systemctl restart grafana-server
```

---

## Alert Details — Phase 1

### SYSTEM (9 alerts)

| ID | Title | Condition | Duration | Severity |
|---|---|---|---|---|
| sy_a1 | Signal K Down | signalk_up = 0 | 30s | CRITICAL |
| sy_a2 | InfluxDB Down | influxdb_up = 0 | 30s | CRITICAL |
| sy_a3 | Grafana Down | grafana_up = 0 | 30s | WARNING |
| sy_a4 | Internet Lost | internet_up = 0 | 2m | CRITICAL |
| sy_b1 | CPU Temp Critical | cpu.temp > 85°C | 2m | CRITICAL |
| sy_b2 | High CPU Load | cpu.load > 90% | 5m | WARNING |
| sy_b3 | Memory Saturated | memory > 95% | 5m | WARNING |
| sy_c01 | GPS Low Sats | satellites < 4 | 1m | WARNING |
| sy_c03 | IMU Roll Missing | no data for 10s | 10s | CRITICAL |

### PERFORMANCE (2 alerts)

| ID | Title | Condition | Duration | Severity |
|---|---|---|---|---|
| pe_b1 | Critical Heel | roll > 25° | 2m | CRITICAL |
| pe_b4 | Excessive Pitch | pitch > 15° | 1m | WARNING |

### WEATHER/SEA (1 alert)

| ID | Title | Condition | Duration | Severity |
|---|---|---|---|---|
| w_d1 | Shallow Water | depth < 4m | 10s | CRITICAL |

### RACING (4 alerts)

| ID | Title | Condition | Duration | Severity |
|---|---|---|---|---|
| r_a2_5min | Start — 5 min | timer ≤ 300s | 1s | INFO |
| r_a2_1min | Start — 1 min | timer ≤ 60s | 1s | INFO |
| r_a2_30s | Start — 30 sec | timer ≤ 30s | 1s | INFO |
| r_a2_10s | Start — 10 sec | timer ≤ 10s | 1s | INFO |

### CREW (2 alerts)

| ID | Title | Condition | Duration | Severity |
|---|---|---|---|---|
| cr_1 | Watch Elapsed | duration > 1h | 5m | WARNING |
| cr_2 | Watch Excessive | duration > 3h | 3h | CRITICAL |

---

## Datasource Configuration

All alerts reference:
- **Datasource UID:** `efifgp8jvgj5sf` (InfluxDB)
- **Bucket:** `midnight_rider`
- **Organization:** `MidnightRider`
- **Query Language:** Flux

**Verify datasource exists:**
```bash
curl -s -u admin:Aneto152 http://localhost:3001/api/datasources | \
  python3 -c "import json, sys; \
  [print(f\"{d['uid']}: {d['name']}\") for d in json.load(sys.stdin) if 'influx' in d.get('type', '').lower()]"
```

---

## Notification Channels

Alerts need notification channels configured. Examples:

### Email
1. **Admin → Notification Channels → New Channel**
2. **Type:** Email
3. **Email address:** race-alerts@example.com
4. **Test:** Verify receipt

### Slack (Recommended)
1. **Type:** Slack
2. **Webhook URL:** (from Slack workspace)
3. **Channel:** #midnight-rider-alerts
4. **Username:** Grafana Alerting

### Telegram
1. **Type:** Telegram
2. **Bot Token:** (from BotFather)
3. **Chat ID:** (group or personal)

---

## Testing Alerts

### Manual Test

1. Trigger a condition manually:
   ```bash
   # Stop Signal K to trigger sy_a1
   sudo systemctl stop signalk
   
   # Wait 30s for alert to fire
   # Check Grafana: Alerting → Alert Instances
   
   # Restore
   sudo systemctl start signalk
   ```

2. Check alert in Grafana:
   - **Alerting → Alert Instances** (active alerts)
   - **Alerting → Alert Rules** (all rules + their state)

### Query Test (Flux)

Test individual alert queries in Grafana Explore:

```flux
# Test: sy_a1_signalk_down
from(bucket:"midnight_rider")
|> range(start:-5m)
|> filter(fn:(r) => r._measurement == "system_health" and r.signalk_up == "0")
|> last()
```

---

## Checklist Before Race Day (May 22)

- [ ] All 18 Phase 1 alerts deployed
- [ ] Notification channels configured (email/Slack/Telegram)
- [ ] Test alert fired manually
- [ ] Dashboard 08-alerts displays alert status
- [ ] Crew trained on alert acknowledgement
- [ ] Silencing/routing rules configured
- [ ] Alert history reviewed (post-field-test)

---

## Phase 2 Alerts (May 19→22)

After field test, deploy remaining 30 alerts:

| Category | Pending | Blocker |
|---|---|---|
| PERFORMANCE (15) | 13 | Wind data (B&G WS320) |
| WEATHER (14) | 13 | Wind, pressure, waves |
| RACING (10) | 6 | Advanced MCP Race |
| **Total** | **51** | **Hardware integration** |

---

## Troubleshooting

### Alerts not firing

1. Check datasource connection:
   ```bash
   curl -s -u admin:Aneto152 \
     http://localhost:3001/api/datasources/uid/efifgp8jvgj5sf | \
     python3 -m json.tool
   ```

2. Test query in Explore:
   - Go to Grafana → Explore
   - Select InfluxDB datasource
   - Paste Flux query from alert definition
   - Verify results appear

3. Check alert evaluation:
   - **Alerting → Alert Rules** → Click rule → **View instances**

### Duplicate alerts

Each alert UID must be unique. If importing multiple times:
1. Delete old rules via UI or API
2. Verify no conflicts
3. Reimport

### Notification failures

1. Test notification channel:
   - **Admin → Notification Channels** → Click channel → **Test**
2. Check logs:
   ```bash
   docker logs grafana | grep -i alert
   ```

---

## Support

- **Documentation:** docs/ALERTS-CATALOG.md
- **Schema:** docs/DATA-SCHEMA.md
- **Grafana Docs:** https://grafana.com/docs/grafana/latest/alerting/
- **Issues:** GitHub Issues (midnightrider-navigation)

---

**Last Updated:** 2026-04-27 20:00 EDT  
**Next Review:** Pre-field-test (May 18)

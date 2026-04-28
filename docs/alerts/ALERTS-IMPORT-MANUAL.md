# Midnight Rider — Manual Alert Import Guide

**Fastest way to deploy 18 Phase 1 alerts in Grafana UI**

---

## Quick Start (5 minutes)

### Step 1: Open Grafana
```
http://localhost:3001
Username: admin
Password: Aneto152
```

### Step 2: Go to Alerting
Navigate: **Alerting → Alert Rules**

### Step 3: Import from YAML
1. Click: **+ Create Alert Rule**
2. Choose: **Import from YAML**
3. Paste content from: `docs/grafana-alerts/alert-rules-phase1.yaml`
4. Click: **Import**

---

## Detailed Step-by-Step (Copy/Paste Method)

If the YAML importer isn't available, create alerts manually:

### Alert 1: Signal K Down

1. **Click:** + Create Alert Rule
2. **Rule name:** `Signal K Down`
3. **Rule type:** Grafana managed alert
4. **Evaluate every:** 1m
5. **For:** 30s

**Step: Query (A)**
- **Data source:** InfluxDB (midnight_rider)
- **Query editor:** Code
- **Paste:**
```flux
from(bucket:"midnight_rider")
|> range(start:-5m)
|> filter(fn:(r) => r._measurement == "system_health" and r.signalk_up == "0")
|> last()
```

**Conditions**
- Condition: `A` (is not empty)

**Annotations**
- **Description:** Signal K API is not responding. Check systemctl status signalk
- **Runbook URL:** https://docs.openclaw.ai/signalk-troubleshooting

**Labels**
- **severity:** critical
- **category:** SYSTEM

**Click:** Save

---

### Alert 2-18: Same Pattern

Follow the same process for each alert. Use the definitions from:

**File:** `docs/grafana-alerts/alert-rules-phase1.yaml`

Each alert has:
- UID (alert ID)
- Title
- Condition (A)
- For (duration)
- Flux query
- Description
- Labels (severity, category)

---

## 18 Alerts to Create

| # | Title | Severity | Category | For |
|---|---|---|---|---|
| 1 | Signal K Down | critical | SYSTEM | 30s |
| 2 | InfluxDB Down | critical | SYSTEM | 30s |
| 3 | Grafana Down | warning | SYSTEM | 30s |
| 4 | Internet Lost | critical | SYSTEM | 120s |
| 5 | CPU Temperature Critical | critical | SYSTEM | 120s |
| 6 | High CPU Load | warning | SYSTEM | 300s |
| 7 | Memory Saturated | warning | SYSTEM | 300s |
| 8 | GPS Low Satellite Count | warning | SYSTEM | 60s |
| 9 | IMU Roll Data Missing | critical | SYSTEM | 10s |
| 10 | Critical Heel Angle | critical | PERFORMANCE | 120s |
| 11 | Excessive Pitch | warning | PERFORMANCE | 60s |
| 12 | Shallow Water Alert | critical | WEATHER | 10s |
| 13 | Start Timer — 5 Minutes | info | RACING | 1s |
| 14 | Start Timer — 1 Minute | info | RACING | 1s |
| 15 | Start Timer — 30 Seconds | info | RACING | 1s |
| 16 | Start Timer — 10 Seconds | info | RACING | 1s |
| 17 | Watch Time Elapsed | warning | CREW | 300s |
| 18 | Watch Excessive (>3h) | critical | CREW | 10800s |

---

## Notification Channels (Required)

Before alerts can fire, configure where notifications go.

### Setup Email Notifications

1. **Admin → Notification Channels**
2. **+ New Channel**
3. **Type:** Email
4. **Name:** Email (Midnight Rider)
5. **Email address:** race-alerts@example.com
6. **Click:** Test
7. **Click:** Save

### Setup Slack (Optional but Recommended)

1. **Type:** Slack
2. **Name:** Slack (Midnight Rider)
3. **Webhook URL:** (from Slack workspace → Create App → Incoming Webhooks)
4. **Channel:** #midnight-rider-alerts
5. **Username:** Grafana Alerting
6. **Click:** Test
7. **Click:** Save

---

## Configure Alert Routes

After creating alerts, configure where they send notifications:

1. **Alerting → Notification Policies**
2. **Root Policy:**
   - **Group by:** category, severity
   - **Repeat interval:** 5m (for active alerts)
   - **Group wait:** 10s (wait before first notification)
   - **Continue matching subsequent sibling nodes:** ✓

3. **Add Routes:**
   - **Matcher:** `category = "SYSTEM"` → Send to: Email
   - **Matcher:** `severity = "critical"` → Send to: Slack (if available)

---

## Test an Alert

### Manually trigger Signal K Down alert:

```bash
# Stop Signal K
sudo systemctl stop signalk

# Wait 30 seconds for alert to fire

# Check Grafana
# Alerting → Alert Instances → "Signal K Down" should show "FIRING"

# Restore Signal K
sudo systemctl start signalk
```

### Check alert in Grafana:

1. **Alerting → Alert Instances**
2. Look for: **Signal K Down** with status **FIRING**
3. Check notifications (email/Slack)

---

## Verify Alerts Are Working

After importing all 18 alerts:

1. **Go to:** Alerting → Alert Rules
2. **Count:** Should show 18 rules
3. **Status:** Should show "Healthy" (green checkmarks)
4. **Go to:** Alerting → Alert Instances
5. **Current:** Should show 0 (unless services are down)

---

## Troubleshooting

### Alerts not appearing in list

- [ ] Check Grafana is running: `docker ps | grep grafana`
- [ ] Verify login: Try Admin panel
- [ ] Check datasource exists: `Admin → Data Sources → InfluxDB`

### Alerts created but not firing

- [ ] Verify notification channel is configured
- [ ] Check alert evaluation: Alerting → Alert Rules → Click rule → View instances
- [ ] Test Flux query in Explore tab

### Queries fail

- [ ] Verify datasource connection
- [ ] Test query in **Explore** tab
- [ ] Check InfluxDB is running: `docker ps | grep influxdb`

### Dashboard shows 0 rules

- [ ] Rules may be in different folder
- [ ] Check Alerting → Alert Rules (not dashboards)
- [ ] Verify Grafana Alerting is enabled

---

## Files Reference

| File | Purpose |
|---|---|
| `alert-rules-phase1.yaml` | YAML definitions of 18 alerts |
| `ALERTS-DEPLOYMENT-GUIDE.md` | Detailed deployment instructions |
| `ALERTS-CATALOG.md` | Complete specification (69 alerts) |
| `deploy-alerts.py` | Python script (API method) |
| `import-alerts-grafana.py` | Python import helper |

---

## Next Steps

### Before Field Test (May 19)

1. ✅ Import all 18 Phase 1 alerts
2. ✅ Configure notification channels
3. ✅ Test at least 1 alert manually
4. ✅ Train crew on alert acknowledgement
5. ✅ Review alert history

### Before Race Day (May 22)

1. ✅ Verify all 18 alerts still active
2. ✅ Silence any noisy alerts
3. ✅ Pre-race system check
4. ✅ Battery SOC > 95%

### After Race

1. Analyze alert firing patterns
2. Adjust thresholds if needed
3. Prepare Phase 2 alerts (after hardware integration)

---

## Support

- **Grafana Docs:** https://grafana.com/docs/grafana/latest/alerting/
- **InfluxDB Flux:** https://docs.influxdata.com/flux/
- **Project Issues:** GitHub Issues

---

**Last Updated:** 2026-04-27 20:15 EDT  
**Estimated Time:** 5-10 minutes to import all 18 alerts

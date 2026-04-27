# Grafana Dashboards — Midnight Rider

Complete backup of 9 Grafana dashboards for Block Island Race 2026.
Exported from Grafana API on 2026-04-27.

## 🚀 Quick Import

### Automatic (Recommended)
```bash
bash scripts/import-grafana-dashboards.sh
```

### Manual (Via UI)
1. Open http://localhost:3001
2. Dashboards → Import → Upload JSON file
3. Select each dashboard file
4. Configure InfluxDB datasource (http://localhost:8086)
5. Click Save

## 📊 Dashboard Files

| File | Dashboard | Refresh | Purpose |
|------|-----------|---------|---------|
| 01-cockpit.json | 🏠 COCKPIT | 5s | Main navigation view |
| 02-environment.json | 🌊 ENVIRONMENT | 30s | Sea & weather |
| 03-performance.json | ⚡ PERFORMANCE | 5s | Speed analysis |
| 04-wind-current.json | 🌪️ WIND & CURRENT | 10s | Tactical analysis |
| 05-competitive.json | 🏆 COMPETITIVE | 30s | Fleet tracking |
| 06-electrical.json | 🔋 ELECTRICAL | 30s | Power management |
| 07-race.json | 🏁 RACE | 5s | Race metrics |
| 08-alerts.json | 🔔 ALERTS | 10s | System monitoring (60+ alerts) |
| 09-crew.json | ⚓ CREW | 30s | Watch rotation & fatigue |

## 🔐 Credentials

- **InfluxDB Token:** Set in `.env.local` (gitignored)
- **InfluxDB URL:** http://localhost:8086
- **Organization:** MidnightRider
- **Bucket:** midnight_rider

## 📝 Notes

- Dashboard UIDs and IDs reset on import (prevents conflicts)
- Reconfigure InfluxDB datasource after fresh install
- All 9 dashboards contain 60+ alert rules
- Charts auto-refresh at configured intervals

## 🔄 Recovery

If you need to restore from these files:

```bash
# 1. Boot the system (Signal K, InfluxDB, Grafana running)
docker-compose up -d

# 2. Import dashboards
bash scripts/import-grafana-dashboards.sh

# 3. Verify
curl http://localhost:3001/api/dashboards
# Should list all 9 dashboards
```

## 📈 Data Sources

All dashboards use InfluxDB as datasource:
- **Bucket:** midnight_rider
- **Organization:** MidnightRider
- **Refresh interval:** Automatic (5-30s)
- **Retention:** 7-14 days local, unlimited cloud (if configured)

## 🎯 Total Recovery Time

From zero to fully functional:
- System boot: 5 min
- Docker services start: 2 min
- Dashboard import: 1 min
- **Total:** ~8 minutes ⚓

---

**Made with ⛵ for Block Island Race 2026**

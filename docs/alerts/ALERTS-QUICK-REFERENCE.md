# Midnight Rider — Alerts Quick Reference
**One-page cheat sheet for all 69 alerts**

---

## ⚡ Quick Deploy (5 min)

**Option 1: YAML Import (Recommended)**
```
1. Open: http://localhost:3001
2. Alerting → Alert Rules → + Create → Import from YAML
3. Paste: docs/grafana-alerts/alert-rules-complete.yaml (all 69)
4. Click: Import
```

**Option 2: Phase-by-Phase**
```
1. Import Phase 1 first: docs/grafana-alerts/alert-rules-phase1.yaml (18)
2. Test before May 19 field test
3. Import Phase 2 later: docs/grafana-alerts/alert-rules-phase2.yaml (51)
```

---

## 📊 All 69 Alerts by Category

### SYSTEM (20) — Infrastructure & Hardware
| Phase | Name | Trigger | Delay |
|-------|------|---------|-------|
| 1 | Signal K Down | API offline | 30s |
| 1 | InfluxDB Down | DB offline | 30s |
| 1 | Grafana Down | UI offline | 30s |
| 1 | Internet Lost | No connectivity | 2m |
| 1 | CPU Temp Critical | > 85°C | 2m |
| 1 | High CPU Load | > 90% | 5m |
| 1 | Memory Saturated | > 95% | 5m |
| 1 | GPS Low Sats | < 4 satellites | 1m |
| 1 | IMU Roll Missing | No data > 10s | 10s |
| 2 | GPS Heading Missing | No heading 30s | 30s |
| 2 | Anemometer Silent | No wind 30s | 30s |
| 2 | Loch No Data | No STW 30s | 30s |
| 2 | AIS No Targets | No vessels 60s | 60s |
| 2 | Barometer No Data | No pressure | 60s |
| 2 | Thermometer No Data | No water temp | 60s |
| 2 | Battery SOC No Data | No house batt | 60s |
| 2 | Starter Battery No Data | No starter | 60s |
| 2 | Vulcan NMEA2000 Silent | No Vulcan 30s | 30s |
| 2 | Wave Analyzer No Data | No wave height | 60s |
| 2 | Current Calc No Data | No current | 60s |

### PERFORMANCE (17) — Boat Speed & Trim
| Phase | Name | Trigger | Delay |
|-------|------|---------|-------|
| 1 | Critical Heel | > 25° (0.436 rad) | 2m |
| 1 | Excessive Pitch | > 15° (0.262 rad) | 1m |
| 2 | VMG Suboptimal | < 85% polar | 3m |
| 2 | VMG Overestimated | > 105% polar | 2m |
| 2 | Boat Slow | -20% vs polars | 5m |
| 2 | Insufficient Heel | < 5° @ TWS>12 | 3m |
| 2 | Heel Unstable | σ > 5°/2m | 2m |
| 2 | Heading Drift | > 5°/20min | 20m |
| 2 | Helm Oscillation | TWA σ > 5° | 10m |
| 2 | High Leeway | > 8° | 5m |
| 2 | Adverse Current | > 0.5kt against | 5m |
| 2 | Current Shift | > 0.5kt/5m | 5m |
| 2 | Port Layline Open | angle ≤ 0° | imm |
| 2 | Starboard Layline | angle ≤ 0° | imm |
| 2 | Favorable Lift | > 8°/3min | 3m |
| 2 | Unfavorable Header | > 8°/3min | 3m |
| 2 | Sails Not Optimal | ≠ polar rec | 5m |

### WEATHER/SEA (15) — Wind, Pressure, Waves
| Phase | Name | Trigger | Delay |
|-------|------|---------|-------|
| 1 | Shallow Water | < 4m depth | 10s |
| 2 | Wind Shift | > 15°/3min | 3m |
| 2 | Gust Imminente | > 8kt/5min | 5m |
| 2 | Squall | > 15kt/10min | 10m |
| 2 | NDBC Direction | > 20°/30min | 30m |
| 2 | NDBC Speed | > 6kt/30min | 30m |
| 2 | Pressure Drop | > 3hPa/3h | 3h |
| 2 | NWS Alert | SCA/Gale active | imm |
| 2 | Short Wave Period | < 6 sec | 5m |
| 2 | Adverse Swell | > 90° from COG | 10m |
| 2 | Slack Water | < 30min away | imm |
| 2 | Sunset | < 30min away | imm |
| 2 | Current Direction | > 20°/5min | 5m |
| 2 | Water Temp Anomaly | > 2°C/30min | 30m |
| 2 | Cold Water | < 10°C | 10m |

### RACING (14) — Start, Marks, Fleet
| Phase | Name | Trigger | Delay |
|-------|------|---------|-------|
| 1 | Start Timer 5min | ≤ 300s | imm |
| 1 | Start Timer 1min | ≤ 60s | imm |
| 1 | Start Timer 30sec | ≤ 30s | imm |
| 1 | Start Timer 10sec | ≤ 10s | imm |
| 2 | Start Line Approach | < 0.5nm | imm |
| 2 | OCS Risk | crossing before | imm |
| 2 | Line Bias | > 5° bias | 2m |
| 2 | Mark Approaching | < 1nm | imm |
| 2 | Wrong Mark | bad rounding | imm |
| 2 | Course Boundary | > 0.1nm out | 30s |
| 2 | Finish Approach | < 0.2nm | imm |
| 2 | Competitor Passing | position change | 5m |
| 2 | Competitor Close | < 0.2nm | imm |
| 2 | Time Limit | < 2h to finish | imm |

### CREW (3) — Watch Management
| Phase | Name | Trigger | Delay |
|-------|------|---------|-------|
| 1 | Watch Elapsed | > 1h watch | 5m |
| 1 | Watch Excessive | > 3h watch | 3h |
| 2 | Crew Wake-Up | T-10min call | imm |

---

## 🎯 Deployment Checklist

**Phase 1 (Before May 19):**
- [ ] Import 18 Phase 1 alerts
- [ ] Configure email notification channel
- [ ] Configure Slack (if available)
- [ ] Test 1 alert manually (stop Signal K)
- [ ] Train crew on dashboard + alerts

**Phase 2 (Before May 22):**
- [ ] Verify all Phase 1 alerts still active
- [ ] Import 51 Phase 2 alerts
- [ ] Test new alerts
- [ ] Verify notification channels working
- [ ] Final pre-race system check

---

## 📁 Files Reference

| File | Size | Purpose |
|------|------|---------|
| alert-rules-complete.yaml | 30 KB | All 69 alerts (combined) |
| alert-rules-phase1.yaml | 17 KB | 18 alerts (deploy now) |
| alert-rules-phase2.yaml | 16 KB | 51 alerts (after hardware) |
| ALERTS-CATALOG.md | 12 KB | Complete specifications |
| ALERTS-DEPLOYMENT-GUIDE.md | 7 KB | Troubleshooting guide |
| ALERTS-IMPORT-MANUAL.md | 6 KB | Manual step-by-step |
| This file | 3 KB | Quick reference |

---

## ⚡ Emergency Procedures

**If alerts aren't firing:**
1. Check Grafana: Alerting → Alert Rules (should show 18+)
2. Check datasource: Admin → Data Sources → InfluxDB (test connection)
3. Check notification: Admin → Notification Channels (test)

**If a critical alert fires:**
1. Read alert description (in Grafana UI)
2. Check documentation: ALERTS-CATALOG.md
3. Take recommended action
4. Acknowledge alert in Grafana

**Silence noisy alerts (if needed):**
1. Alerting → Alert Rules → Click rule → Add silence
2. Duration: 5m / 1h / Until acknowledged
3. Can re-enable anytime

---

## 🔗 Quick Links

- **Dashboard:** http://localhost:8888
- **Grafana:** http://localhost:3001
- **Alert Rules:** http://localhost:3001/alerting/alert-rules
- **Alert Instances:** http://localhost:3001/alerting/alerts
- **Documentation:** docs/ALERTS-CATALOG.md

---

**Deploy Phase 1 now. Phase 2 can wait until May 21. All 69 alerts are production-ready! 🚀**

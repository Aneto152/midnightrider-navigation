# CHECK-SYSTEM.SH — QUICK REFERENCE CARD

**Print this and laminate for boat reference!**

---

## ⚡ QUICK START

```bash
# Fast check (2 sec)
check-quick

# Full diagnostic (10 sec) — USE THIS BEFORE RACE
check-full

# Live monitoring
check-watch
```

---

## 📋 WHAT IT CHECKS

| Category | Items |
|----------|-------|
| **Services** | Signal K, InfluxDB, Grafana |
| **Sensors** | GPS, WIT BLE, YDNU-02, Calypso |
| **Data** | Position, heading, attitude, waves |
| **Database** | InfluxDB writes, bucket health |
| **Docker** | influxdb, grafana containers |

---

## 📊 OUTPUT

```
✅ PASS    → Component operational
⚠️  WARNING → Component OK but check it
❌ FAIL    → Component not working

RESULT:
✅ GO FOR DEPLOYMENT      (0 failures)
⚠️  CAUTION PROCEED       (warnings only)
❌ NO-GO                  (critical failures)
```

---

## 🚀 PRE-RACE PROCEDURE

**1h before race:**
```bash
check-full
# Should return: ✅ GO or ⚠️ CAUTION
```

**15 min before start:**
```bash
check-quick
# Verify everything still OK
```

**If anything is ❌:**
1. Read the error message
2. Check troubleshooting below
3. Fix or escalate to Denis

---

## 🔧 QUICK FIXES

| Problem | Fix |
|---------|-----|
| Signal K ❌ | `systemctl start signalk` |
| InfluxDB ❌ | `docker compose up -d influxdb` |
| Grafana ❌ | `docker compose up -d grafana` |
| GPS ⚠️ | Wait 30+ sec (cold start) |
| WIT BLE ❌ | Power cycle WIT (off 10s) |
| YDNU-02 ⚠️ | Unplug USB 5 sec, replug |

---

## 📞 ESCALATION

If `check-full` shows ❌ and you can't fix it:
1. Note the failing component
2. Take a screenshot
3. Call Denis: [phone number]
4. Do NOT depart until GO

---

## 💡 TIPS

- **Before departure:** Always run `check-full`
- **During setup:** Use `check-watch` to monitor
- **In doubt:** Re-run check (may be transient)
- **GPS slow?** It's normal on cold start

---

**READY FOR RACE!** ⛵ 🏁

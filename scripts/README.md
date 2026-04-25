# Scripts — Midnight Rider Navigation System

## check-system.sh

**Diagnostic complet du système navigation avant la mise à la mer.**

### Usage

```bash
./check-system.sh [--quick | --full | --watch]
```

### Options

- `--quick` — Test des services de base (signal K, ports)
- `--full` — Diagnostic complet (services, capteurs, données, InfluxDB)
- `--watch` — Monitoring continu (refresh toutes les 10 sec)

### Exemples

**Quick check before departing:**
```bash
./check-system.sh --quick
```

**Full pre-race diagnostic:**
```bash
./check-system.sh --full
```

**Monitor live during setup:**
```bash
./check-system.sh --watch
```

### Output

Script affiche un rapport structuré avec statuts:

```
✅ PASS    — Composant opérationnel
⚠️  WARNING — Composant dégradé (fonctionnel mais vérifier)
❌ FAIL    — Composant critique hors service

RÉSUMÉ:
  Total checks: X
  ✅ Passed: X
  ⚠️ Warnings: X
  ❌ Failed: X

GO / NO-GO:
  ✅ GO FOR DEPLOYMENT       (0 failures, ≤2 warnings)
  ⚠️  CAUTION PROCEED        (0 failures, >2 warnings)
  ❌ NO-GO                   (≥1 failure)
```

### Catégories de Tests

#### 1. Services de Base
- Signal K (systemctl)
- Signal K API (port 3000)
- InfluxDB (port 8086)
- Grafana (port 3001)

#### 2. Capteurs Connectés
- UM982 GNSS (/dev/ttyUSB0)
- WIT IMU BLE (hci0)
- YDNU-02 Gateway (USB)
- Calypso UP10 (optional)

#### 3. Données Signal K
- Position GPS
- Heading True
- Attitude (roll/pitch/yaw)
- Wave Height (Wave Analyzer v1.1)

#### 4. InfluxDB
- Bucket 'midnight_rider'
- Recent writes (last 5 min)
- No error logs

#### 5. Docker Services (Optional)
- influxdb container
- grafana container

### Exit Codes

```
0 = ✅ GO FOR DEPLOYMENT
1 = ⚠️  CAUTION PROCEED (warnings only)
2 = ❌ NO-GO (critical failures)
```

### Pre-Race Procedure

**1h before race start:**
```bash
# Full diagnostic
./check-system.sh --full

# Should return exit code 0 or 1
# If exit code 2, fix issues before deployment
```

**15 min before start:**
```bash
# Quick recheck
./check-system.sh --quick
```

**During race (optional):**
```bash
# Continuous monitoring
./check-system.sh --watch
```

### Integration with Systemd (Optional)

**Auto-run on boot (see /etc/systemd/system/check-system.service):**

```ini
[Unit]
Description=Midnight Rider System Check
After=network.target signalk.service

[Service]
Type=oneshot
ExecStart=/home/aneto/check-system.sh --full
ExecOnFailure=systemctl start emergency-alert.service
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Logs & Debugging

**Signal K logs:**
```bash
journalctl -u signalk -f
```

**InfluxDB write activity:**
```bash
journalctl -u signalk --since "5 min ago" | grep -i influx
```

**All system services:**
```bash
systemctl status signalk
docker compose ps
```

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Signal K API (❌) | `systemctl start signalk` |
| InfluxDB (❌) | `docker compose up -d influxdb` |
| Grafana (❌) | `docker compose up -d grafana` |
| GPS (⚠️) | Wait 30+ sec for cold start |
| WIT BLE (❌) | `systemctl restart signalk` or check power |
| YDNU-02 (⚠️) | Unplug USB 5 sec, replug |
| Containers won't start | `sudo systemctl stop influxdb && docker compose up -d` |

### Version

- **v1.0** — 2026-04-25 — Initial release
  - Complete diagnostics
  - All sensor checks
  - GO/NO-GO decision logic
  - Three execution modes (quick/full/watch)

---

**Status:** ✅ Ready for production deployment

**Last Updated:** 2026-04-25

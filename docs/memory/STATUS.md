# 📊 STATUS — MidnightRider (2026-04-19 15:58)

## Services

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| SignalK | 3000 | ✅ Running | Node.js, 2.8GB RAM |
| InfluxDB | 8086 | ✅ Running | 2.2GB RAM, bucket "signalk" OK |
| Grafana | 3001 | ✅ Running | 3.0GB RAM, admin login OK |
| kflex | 10110 | ✅ Configured | NMEA multiplexer (no data yet) |
| Interface Régate | 5000 | ⏳ Exists | Flask server, not running as service |

## Données GPS

**Dernières mesures (2026-04-19 18:54:52 UTC):**
- Position: 40.7627°N, 73.9881°W (East River, NYC)
- Source: GPS UM982
- Fréquence: ~1 point/sec (logged ~every 2s)
- Bucket: InfluxDB local (`signalk`)

**Requête test:**
```flux
from(bucket:"signalk")
  |> range(start:-1h)
  |> filter(fn:(r) => r._measurement=="navigation.position")
```

✅ **Retourne 3 derniers points OK**

## Connectivité

| Link | Status | Notes |
|------|--------|-------|
| GPS → SignalK | ✅ | /dev/ttyUSB0, 115200 baud |
| SignalK → InfluxDB local | ✅ | Plugin signalk-to-influxdb2 actif |
| Local → Cloud | ❌ | Pas de synchro configurée |
| InfluxDB Cloud | ⚠️ | Token expiré (401 Unauthorized) |
| Grafana Cloud | ⏳ | Account exists, datasource not configured |

## Configurations

```
/home/aneto/docker/signalk/config/
  ├─ signalk-settings.json    — providers GPS, NMEA2000, kflex
  ├─ signalk-to-influxdb2.json — InfluxDB local config ✅
  └─ docker-compose.yml        — SignalK + InfluxDB + Grafana

/home/aneto/.signalk/
  └─ plugin-config-data/
     └─ signalk-to-influxdb2.json — plugin settings (copy of above)
```

## Instruments Status

| Instrument | Type | Status | Notes |
|------------|------|--------|-------|
| GPS UM982 | NMEA0183 | ✅ Active | Dual GNSS, /dev/ttyUSB0 |
| YDWG-02 | NMEA2000 | ✅ Configured | /dev/ttyACM1, no data yet |
| kflex | NMEA mux | ✅ Configured | TCP 10110, for qtVLM |
| Loch/Sondeur | NMEA | ⏳ Pending | Not installed |
| Girouette | NMEA | ⏳ Pending | Not installed |
| Baromètre | NMEA | ⏳ Pending | Not installed |
| AIS | NMEA | ⏳ Pending | Not installed |

## GitHub

**Repo:** https://github.com/Aneto152/midnightrider-navigation

**Latest commits:**
- `6aee3d3` (2026-04-19 15:58) — Sauvegarde vérif GPS/InfluxDB
- `821a8bf` (2026-04-19 02:00) — Auto-backup
- `b9275ba` — Fix permissions GPS ttyUSB0

**Auto-backup:** Every night at 02:00 UTC

## WiFi AP

- SSID: `MidnightRider`
- Password: `Aneto152`
- IP: 192.168.4.1 (RPi)
- Public dashboard: http://192.168.4.1:3001/public-dashboards/d397139a405c4f4eb9f1fdc52f306029

## Memory Files (This Repo)

| File | Purpose | Last Updated |
|------|---------|---------------|
| SYSTEM.md | How assistant memory works | 2026-04-19 |
| ARCHITECTURE.md | System overview & data flow | 2026-04-19 |
| TODO.md | Prioritized task list | 2026-04-19 |
| STATUS.md | This file | 2026-04-19 |
| CREDENTIALS.md | Tokens (in .gitignore) | 2026-04-19 |

---

**What's blocking next steps:**
1. ❌ InfluxDB Cloud token expired — **Need to regenerate**
2. ❌ No sync local → cloud configured
3. ⏳ Instruments not installed yet (girouette, loch, etc.)

**Next session checklist:**
- [ ] Check memory files in this repo
- [ ] Verify GPS is still streaming
- [ ] Confirm no new errors in logs

# 🏗️ Architecture — MidnightRider Navigation

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    BATEAU - MidnightRider (J/30)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Instruments NMEA                                             │
│  ├─ GPS UM982 Dual GNSS (/dev/ttyUSB0, 115200 baud) ✅      │
│  ├─ YDWG-02 NMEA2000 (/dev/ttyACM1) — pas de données        │
│  ├─ kflex (TCP 10110) — multiplexeur NMEA                   │
│  ├─ Loch/Sondeur (NMEA) ⏳                                    │
│  ├─ Girouette anémomètre (NMEA) ⏳                            │
│  └─ AIS receiver ⏳                                           │
│                        │                                      │
│                        ▼                                      │
│  ┌──────────────────────────────────────┐                   │
│  │     SignalK Server (port 3000)       │ ✅ Actif           │
│  │  Docker: signalk-server + plugins    │                   │
│  │  Providers:                          │                   │
│  │  - um982-gps (active)                │                   │
│  │  - kflex (active)                    │                   │
│  │  - NMEA2000 (active)                 │                   │
│  └──────────────────────────────────────┘                   │
│         │                    │                               │
│         ▼                    ▼                               │
│  ┌──────────────────┐  ┌─────────────────────┐              │
│  │  InfluxDB v2     │  │  Grafana Local      │              │
│  │  localhost:8086  │  │  localhost:3001     │              │
│  │  bucket: signalk │  │  admin/MidnightRider│              │
│  │  ✅ Actif        │  │  ✅ Actif           │              │
│  └──────────────────┘  └─────────────────────┘              │
│         │                    │                               │
│         └────────┬───────────┘                              │
│                  ▼                                            │
│         Interface Régate                                     │
│         (http://192.168.4.1:5000)                           │
│         - Timer départ                                       │
│         - Sélection voiles/barreur                          │
│         - Marquage ligne (2 points GPS)                     │
│                  │                                            │
│                  ▼                                            │
│         InfluxDB local (persistance)                        │
│                                                               │
│  Réseau WiFi AP: MidnightRider (192.168.4.1)               │
│  - iPad/Phone peut accéder http://192.168.4.1:3001         │
│  - Dashboard public sans login                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ (Ethernet out)
                          │
        ┌─────────────────▼────────────────┐
        │   CLOUD (À CONFIGURER) ⏳        │
        ├─────────────────────────────────┤
        │  InfluxDB Cloud                  │
        │  https://us-east-1-1.aws.cloud2  │
        │  org: 48a34d6463cef7c9           │
        │  bucket: signalk                 │
        │  Token: EXPIRÉ ❌                 │
        │                                   │
        │  Grafana Cloud                   │
        │  (Denis compte existant)          │
        │  Dashboards post-régate          │
        └─────────────────────────────────┘
```

## Flux de données GPS

### Local (✅ WORKING)
1. GPS UM982 envoie NMEA0183 → /dev/ttyUSB0
2. SignalK reçoit via provider "um982-gps"
3. SignalK parse & dérive données (SOG, COG, position)
4. Plugin "signalk-to-influxdb2" → InfluxDB local
5. **Résolution:** 1 point par seconde (~2s actuellement)
6. **Mesures:**
   - navigation.position (lat/lon)
   - navigation.courseOverGround (COG)
   - navigation.speedOverGround (SOG)
   - navigation.headingTrue (HDG)
   - etc.

### Cloud (❌ TODO)
1. InfluxDB local → InfluxDB Cloud (replication/sync)
   - **Méthode:** À définir
     - Option A: Plugin SignalK "signalk-to-influxdb2-cloud"
     - Option B: Script cron qui replique local → cloud
     - Option C: InfluxDB Telegraf/Replication
   - **Authentification:** Token Cloud à renouveler
2. InfluxDB Cloud → Grafana Cloud (datasource)
3. Denis consulte dashboards cloud depuis PC/tel

## Services systemd

```bash
# À vérifier
systemctl status docker
systemctl status signalk
# Interface régate (À CRÉER)
# systemctl status regatta
```

## Sauvegardes

- **Auto-backup Git:** Chaque nuit à 2h (crontab)
- **Backup InfluxDB:** Répertoire `/home/aneto/docker/signalk/influxdb-backup-20260417`
- **Config Docker:** Versionnées dans GitHub

## Credentials

⚠️ **NE PAS COMMITTER EN CLAIR!**

Voir `docs/memory/CREDENTIALS.md` (`.gitignore`d)

---

**Last updated:** 2026-04-19 15:58

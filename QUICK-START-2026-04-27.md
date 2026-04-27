# Quick Start — Midnight Rider Navigation (2026-04-27)

**Status:** ✅ Opérationnel — données en direct, dashboards actifs

---

## 🚀 Démarrage (2 minutes)

### 1. Boot du système
```bash
# Les services se lancent automatiquement au démarrage
sudo systemctl restart signalk      # (optionnel, si besoin)
docker compose up -d influxdb grafana  # (optionnel, si besoin)
```

### 2. Vérifier que tout tourne
```bash
# Signal K: doit répondre
curl http://localhost:3000/signalk/v1/api/self

# InfluxDB: doit être healthy
curl http://localhost:8086/health

# Grafana: doit répondre
curl http://localhost:3001/api/health
```

### 3. Ouvrir le dashboard
```
Desktop:     http://localhost:3001/d/cockpit-main (F5)
iPad WiFi:   http://MidnightRider.local:8888 (puis cliquer COCKPIT)
Portal:      http://localhost:8888 (9 dashboards)
```

---

## 📊 Ce que tu vas voir

### COCKPIT Dashboard
```
Speed Over Ground (SOG):    0.159 kt (dernière valeur en direct)
Heading True:               243° (cap magnétique)
Roll (Heel):                -0.005 rad (~-0.3°)
Pitch:                      +0.001 rad (~+0.06°)
Speed History:              graphique 5min
Attitude History:           roll/pitch en direct
System Status:              CPU 80°C, sensors OK
```

### Autres Dashboards
```
ENVIRONMENT:  Température eau, vagues, pression
PERFORMANCE:  STW, VMG, polars, efficiency
WIND:         Vent apparent, vrai vent, shifts
RACE:         Countdown, marks, distance
CREW:         Watch management, fatigue
ALERTS:       60 règles de monitoring
```

---

## 🔧 Troubleshooting (30 sec)

### "No data" dans Grafana
```bash
# 1. Vérifier que Signal K envoie des données
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation | jq .speedOverGround

# 2. Vérifier que InfluxDB les reçoit
docker exec influxdb influx query --org MidnightRider \
  'from(bucket:"midnight_rider") |> range(start:-5m) |> limit(n:1)'

# 3. Vérifier le token Grafana
cat .env.local | grep INFLUX_TOKEN

# 4. Actualiser Grafana (F5)
```

### "Datasource not found"
```bash
# Vérifier datasource dans Grafana
curl -s -u "admin:Aneto152" http://localhost:3001/api/datasources | jq .

# Doit avoir un InfluxDB avec uid: "efifgp8jvgj5sf"
```

### Services ne démarrent pas
```bash
# Vérifier InfluxDB (native vs Docker)
sudo systemctl status influxdb   # native
docker ps | grep influxdb        # Docker

# Si conflit de port 8086:
sudo systemctl stop influxdb
docker compose up -d influxdb

# Vérifier les logs
docker logs influxdb | tail -20
journalctl -u signalk -n 20
sudo systemctl status grafana
```

---

## 📡 Données Actuelles

### Volume dans InfluxDB
```
Dernière heure:     35,000+ records
Débit:              600+ records/minute
Sources:
  • WIT IMU (attitude, acceleration)
  • UM982 GPS (speed, heading, position)
  • CPU temp (system monitoring)
```

### Measurements Disponibles
```
✅ navigation.speedOverGround
✅ navigation.courseOverGroundTrue
✅ navigation.attitude.roll
✅ navigation.attitude.pitch
✅ navigation.attitude.yaw
✅ navigation.acceleration.x/y/z
✅ navigation.gnss.* (position, satellites, etc.)
✅ environment.system.cpuTemperature
```

---

## 🎯 Avant la Course (May 22)

### Checklist 1 heure avant
```
☐ Boot RPi (5 min)
☐ Vérifier Signal K actif
☐ Vérifier InfluxDB reçoit des données
☐ Ouvrir Grafana COCKPIT (F5)
☐ Affichage sur iPad en fullscreen (F key)
☐ Tester les 9 dashboards
☐ Vérifier no errors, no crashes
☐ Contrôler batterie SOK si arrivée
```

### Race Mode
```
Primary:   COCKPIT (navigation + attitude)
Tactical:  RACE + WIND + COMPETITIVE dashboards
Monitor:   ALERTS (60 rules active)
```

---

## 🔐 Credentials

```
Grafana:
  URL:      http://localhost:3001
  Login:    admin / Aneto152
  
Signal K:
  URL:      http://localhost:3000
  No auth (local network)
  
InfluxDB:
  URL:      http://localhost:8086
  Org:      MidnightRider
  Bucket:   midnight_rider
  Token:    daEPqojW6k0Bs1VgV6HoRNZQxUyJe2Rj0vjzIzqsejVXX7jeIA4sFqcicamRdddk8Cpf6kfQrFtpxXcko9bQeg==
```

---

## 📞 En Cas de Problème

### Logs Utiles
```bash
# Signal K
journalctl -u signalk -f

# InfluxDB (Docker)
docker logs -f influxdb

# Grafana (Docker)
docker logs -f grafana

# System
dmesg | tail -20
```

### Reset Complet (si tout casse)
```bash
# Arrêter tout
docker compose down
sudo systemctl stop signalk

# Attendre 10 sec

# Redémarrer
docker compose up -d influxdb grafana
sudo systemctl start signalk

# Attendre 30 sec pour InfluxDB ready
curl http://localhost:8086/health
```

---

## 📚 Documentation Complète

- **SESSION-FINAL-2026-04-27.md** — Rapport complet de la session (9.6 KB)
- **README.md** — Architecture du système
- **docs/INDEX.md** — Navigation documentation
- **scripts/INSTALL-README.md** — Installation guide

---

## ✅ Status Actuel

```
Signal K:    ✅ Running (systemd)
InfluxDB:    ✅ Running (Docker)
Grafana:     ✅ Running (Docker)
Portal:      ✅ Running (port 8888)
Dashboards:  ✅ 9/9 opérationnel
Data Flow:   ✅ 600+ records/min
Live Demo:   ✅ http://localhost:3001/d/cockpit-main
```

---

**Midnight Rider Navigation System — Prêt pour la course! 🚀⛵**

Dernière mise à jour: 2026-04-27 16:15 EDT

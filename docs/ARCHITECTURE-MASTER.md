# Midnight Rider Navigation System — Architecture Master Reference
Version: 5.0 (consolidated from previous v4.x documents)
Last Updated: 2026-06-14
Status: ✅ PRODUCTION — Canonical architecture reference
Source: Merged from ARCHITECTURE-REFERENCE-2026-05-20.md

> Note: This document is now the single canonical architecture reference.
> All future updates MUST be made to this file only.

---

## 1. VUE D'ENSEMBLE

Midnight Rider embarque un système de navigation open-source basé sur un Raspberry Pi 4,
collectant les données de tous les instruments via trois réseaux physiques distincts
(NMEA 2000, Bluetooth LE, USB), les centralisant dans Signal K, les persistant dans
InfluxDB et les visualisant dans Grafana.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MIDNIGHT RIDER — STACK                       │
│                                                                 │
│  CAPTEURS ──► COLLECTE ──► TRAITEMENT ──► STOCKAGE ──► VISU   │
│                                                                 │
│  UM982 (USB)  ──────────────────────────► Signal K :3000       │
│  WIT IMU (BLE) ─────────────────────────► │                    │
│  Calypso UP10 (BLE/UDP) ────────────────► │ ──► InfluxDB :8086 │
│  WS320 (N2K/YDNU-02) ───────────────────► │         │          │
│  YDBC-05 (N2K/YDNU-02) ─────────────────► │         │          │
│  AIS700 (N2K/YDNU-02) ──────────────────► │         │          │
│                                           │         │          │
│  SOK BMS (BLE) ─────────────────────────────────────► InfluxDB │
│                                                      │          │
│                                           │         ▼          │
│  Signal K ──► signalk-n2k-bridge (P5) ──────────────► Grafana :3001│
│                    │                                            │
│                    ▼                                            │
│               YDNU-02 (USB/N2K) ──► N2K backbone               │
│                                    ├── Vulcan 7 FS              │
│                                    ├── WS320 base               │
│                                    ├── YDBC-05                  │
│                                    └── AIS700                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. MATÉRIEL EMBARQUÉ

### 2.1 Serveur de navigation

| Composant | Détail |
|-----------|--------|
| **Raspberry Pi 4 Model B** | 4 Go RAM, microSD 64 Go |
| **IP locale fixe** | 192.168.1.131 |
| **OS** | Raspberry Pi OS (Debian 12 Bookworm) |
| **Rôle** | Signal K server, Docker host (InfluxDB, Grafana), gateway BLE, scripts Python |
| **Alimentation** | 12V → 5V USB-C via convertisseur DC/DC |
| **Accès local** | SSH (`aneto@192.168.1.131`) |
| **Accès distant** | Cloudflare Tunnel (voir `CLOUDFLARE-TUNNEL-URL.md`) |

### 2.2 Instruments actifs

| # | Instrument | Modèle | Protocole | Rôle principal |
|---|------------|--------|-----------|---------------|
| 1 | GPS + Cap | Unicore UM982 | USB serial | Position, cap vrai, SOG, COG |
| 2 | IMU | WIT WT901BLECL | Bluetooth LE 5.0 | Gîte, assiette, accélération |
| 3 | Vent masthead | Calypso UP10 | Bluetooth LE | Vent apparent/vrai + temp air |
| 4 | Vent masthead (N2K) | B&G WS320 | NMEA 2000 | Vent apparent → Vulcan 7 direct |
| 5 | Passerelle N2K | Yacht Devices YDNU-02 | USB + NMEA 2000 | Bridge Signal K ↔ N2K |
| 6 | Chartplotter | B&G Vulcan 7 FS | NMEA 2000 | Affichage helm + GPS secondaire |
| 7 | Batterie | SOK SK12V100PC LiFePO4 | Bluetooth LE | Monitoring BMS (direct InfluxDB) |
| 8 | Baromètre | Yacht Devices YDBC-05 | NMEA 2000 | Pression atmosphérique |
| 9 | Transpondeur AIS | B&G AIS700 Class B | NMEA 2000 | AIS TX/RX + sécurité |

### 2.3 Bus NMEA 2000 — Charge réseau

| Appareil | LEN | Rôle sur le bus |
|----------|-----|----------------|
| YDNU-02 Gateway | 1 | Bridge USB ↔ N2K |
| Vulcan 7 FS | 1 | Chartplotter + réception données |
| WS320 Base Station | 2 | Émetteur vent via BLE→N2K |
| YDBC-05 Barometer | 1 | Émetteur pression |
| AIS700 | 1 | Transpondeur AIS |
| **Total** | **6 / 50 LEN max** | ✅ |

---

## 3. RÉSEAUX PHYSIQUES

### 3.1 USB (série)

```
RPi 4 USB-A
  └── /dev/ttyACM0 ──► YDNU-02 (CDC ACM, VID:0483 PID:A217)
                           │
                           └── NMEA 2000 backbone (250 kbps)

RPi 4 USB-A
  └── /dev/ttyUSB0 ──► UM982 GNSS (CH340/CP2102, 115200 baud, 8N1)
```

> ⚠️ YDNU-02 utilise le driver CDC ACM (pas FTDI) → port `/dev/ttyACM*`  
> ⚠️ UM982 utilise un convertisseur USB-série → port `/dev/ttyUSB*`

### 3.2 Bluetooth LE (hci0)

```
RPi 4 BLE adapter (hci0)
  ├── WIT WT901BLECL    ← IMU (BLE 5.0, device: "WT901BLE__")
  ├── Calypso UP10      ← Anémomètre (BLE 4.x, device: "ULTRASONIC")
  └── SOK Battery BMS   ← BMS LiFePO4 (BLE, JBD protocol)
```

**Services systemd associés :**

| Service | Instrument | Rôle |
|---------|-----------|------|
| `signalk.service` | WIT (via plugin) | Lecture IMU, injection SK |
| `calypso_direct` | Calypso UP10 | Lecture vent BLE → UDP 4123 |
| `calypso_watchdog` (obsolète) | Calypso UP10 | Redémarrage auto si déconnexion |
| `sok_direct` | SOK BMS | Lecture BMS → direct InfluxDB |

### 3.3 NMEA 2000 (backbone bateau)

```
YDNU-02 ──T── Vulcan 7 FS
         │
         ├──T── WS320 Base Station
         │
         ├──T── YDBC-05 Barometer
         │
         ├──T── AIS700
         │
         [T] Terminateurs aux deux extrémités
```

### 3.4 Réseau IP (WiFi)

```
RPi 4 (192.168.1.131)
  ├── Point d'accès WiFi (hostapd)
  │     SSID: MidnightRider / password: voir wifi-ap.txt
  │     Connecté: téléphones équipage, tablettes
  │
  └── Cloudflare Tunnel ──► Internet (accès distant sécurisé)
```

---

## 4. STACK LOGICIELLE

### 4.1 Services et ports

| Service | Port | Protocole | Mode de démarrage | Technologie |
|---------|------|-----------|------------------|-------------|
| **Signal K** | 3000 | HTTP/WS | `systemctl` (**JAMAIS docker**) | Node.js |
| **InfluxDB** | 8086 | HTTP | `docker compose` | Docker |
| **Grafana** | 3001 | HTTP | `docker compose` | Docker |
| **OpenClaw Gateway** | 18789 | HTTP | `systemctl` | Local only |
| **Regatta Server** | 5000 | HTTP | `docker compose` | Docker |
| **Signal K UDP RX** | 4123 | UDP | Interne Signal K | Calypso injection |

> ⚠️ **RÈGLE ABSOLUE :**  
> Signal K = `systemctl` UNIQUEMENT  
> InfluxDB + Grafana = `docker compose` UNIQUEMENT  
> Ne jamais inverser ces deux règles.

### 4.2 Signal K — Plugins actifs

| Plugin | Rôle | Source SK |
|--------|------|-----------|
| `signalk-um982-gnss` | Lecture UM982 (NMEA+proprietary) | `signalk-um982-gnss.UM982-HDG` |
| `signalk-wit-imu-ble` | Lecture WIT IMU BLE | `signalk-wit-imu-ble.XX` |
| `signalk-n2k-bridge (P5)` | Émission PGNs → YDNU-02 → N2K | — |
| `signalk-to-influxdb2` | Persistence SK → InfluxDB | — |
| `signalk-performance-polars` | Calcul VMG, efficacité polaire | `performance.*` |
| signalk-heading-true-calculator | Cap vrai (HM + variation mag.) | navigation.headingTrue |
| signalk-j30-leeway | Dérive J/30 = K×|gîte|/STW² | performance.leewayAngle |
| signalk-current-calculator | Courant (set + drift) | environment.current.* |
| signalk-truewind-calculator | Vent vrai (TWD/TWS/TWA) | environment.wind.* |
| `signalk-astronomical` | Données soleil/lune | `environment.sun.*` |
| `signalk-rpi-cpu-temp` | Temp CPU RPi | `environment.rpi.*` |
| `signalk-sails-management-v2` | Gestion voiles | `sails.*` |
| `signalk-app-dock` | Dashboard Signal K webapp | — |
| `signalk-to-nmea0183` | Export NMEA 0183 (WiFi) | — |
| `freeboard-sk` | Carte nautique webapp | — |
| `kip` | Instrument display webapp | — |
| `course-provider` | Calculs de navigation | — |

### 4.3 Docker Compose — Services

```yaml
# docker-compose.yml — résumé
services:
  influxdb:
    image: influxdb:2.x
    ports: ["8086:8086"]
    volumes: [influxdb-data:/var/lib/influxdb2]

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    volumes: [grafana-data:/var/lib/grafana]
    depends_on: [influxdb]

  regatta-server:
    ports: ["5000:5000"]
```

### 4.4 InfluxDB — Organisation des données

| Paramètre | Valeur |
|-----------|--------|
| **Organisation** | MidnightRider |
| **Bucket principal** | `midnight_rider` |
| **Rétention** | Illimitée (racing data) |
| **Token** | Stocké dans `.env` (jamais dans git) |

**Measurements clés :**

| Measurement | Source | Champs principaux |
|-------------|--------|------------------|
| `navigation` | Signal K → signalk-to-influxdb2 | headingTrue, position, SOG, COG |
| `environment` | Signal K → signalk-to-influxdb2 | wind.*, outside.*, water.* |
| `attitude` | Signal K → signalk-to-influxdb2 | roll, pitch, yaw |
| `performance` | Signal K → signalk-to-influxdb2 | targetSpeed, polarEfficiency, VMG |
| `sok_bms` | Python direct | soc_pct, voltage_v, current_a, cell_1_4_mv |
| `astronomical` | signalk-astronomical | sunrise, sunset, moon phase |
| `sails` | signalk-sails-management | active_sail, reef_state |

### 4.5 Grafana — Dashboards

| # | Nom | Contenu |
|---|-----|---------|
| 01 | Cockpit | Cap, position, SOG, COG, gîte |
| 02 | Environment | Vent (AWS/TWS/AWA/TWA), pression baro, temp |
| 03 | Performance | Polaires, VMG, efficacité, target speed |
| 04 | Wind & Current | Vent détaillé, courant estimé |
| 05 | Competitive | Données course, laylines |
| 06 | Electrical | SOK BMS — SoC, tension, cellules, température |
| 07 | Race | Dashboard régate complet |
| 08 | Alerts | Alertes actives et historique |
| 09 | Crew | Dashboard équipage (vue simplifiée) |

---

## 5. FLUX DE DONNÉES DÉTAILLÉS

### 5.1 Cap vrai (headingTrue)

```
UM982 GNSS (ANT1 + ANT2)
  HEADINGOFFSET 90 appliqué (firmware permanent, NVRAM, 2026-05-17)
  ↓ USB /dev/ttyUSB0 (115200 baud)
signalk-um982-gnss plugin
  ↓ Signal K — navigation.headingTrue (radians)
  ├──► InfluxDB → Grafana 01-Cockpit
  └──► signalk-n2k-bridge (P5)
         ↓ PGN 127250 (Vessel Heading)
         YDNU-02 → N2K bus
         └── Vulcan 7 FS (affichage helm)
```

### 5.2 Gîte / Assiette (attitude)

```
WIT WT901BLECL (BLE 5.0, 30 Hz)
  ↓ bleak_wit.py → signalk-wit-imu-ble plugin
  ↓ Signal K — navigation.attitude.{roll, pitch, yaw}
  │              navigation.acceleration.{x, y, z}
  │              navigation.rateOfTurn
  ├──► InfluxDB → Grafana 01-Cockpit
  ├──► Wave Analyzer v1.1 (heel correction)
  │       ↓ environment.water.waves.*
  └──► signalk-n2k-bridge (P5)
         ↓ PGN 127257 (Attitude)    ← attitude.js patché 2026-05-17
         YDNU-02 → N2K bus
         └── Vulcan 7 FS (affichage gîte en temps réel)
```

### 5.3 Vent (priorité sources)

```
Calypso UP10 (BLE → UDP 4123) — PRIORITÉ 1 pour Signal K
  ↓ calypso-anemometer Python (systemd)
  ↓ Signal K Delta UDP port 4123
  ↓ environment.wind.{speedApparent, angleApparent, speedTrue, directionTrue}
  ├──► InfluxDB → Grafana 02-Environment
  └──► signalk-n2k-bridge (P5) → PGN 130306 → Vulcan 7

B&G WS320 (BLE → base station → N2K) — PRIORITÉ 2 pour Signal K
  ↓ NMEA 2000 PGN 130306 (5 Hz) — DIRECT vers Vulcan 7 FS
  └──► YDNU-02 → Signal K (source secondaire)
```

### 5.4 Position GPS

```
UM982 GNSS (Primary — 1.5m accuracy autonomous)
  ↓ PGNs 129025, 129026, 129029 → Signal K → InfluxDB → Grafana

Vulcan 7 FS internal GPS (Fallback — 3m accuracy)
  ↓ PGNs 129025, 129026 sur N2K bus (si UM982 absent)
```

### 5.5 Batterie (SOK BMS)

```
SOK SK12V100PC BMS (BLE — JBD protocol)
  ↓ sok_bms_reader.py (Python, 0.2 Hz)
  ↓ DIRECT → InfluxDB measurement: sok_bms
  [Signal K non impliqué — bypass intentionnel]
  └──► Grafana 06-Electrical
```

### 5.6 Pression atmosphérique

```
YDBC-05 (N2K PGNs 130310/130311/130314 @ 0.5 Hz)
  ↓ N2K bus → YDNU-02 → Signal K
  ↓ environment.outside.pressure (Pascal)
  ├──► InfluxDB → Grafana 02-Environment
  └──► Vulcan 7 FS (page données environnement)
```

### 5.7 AIS

```
AIS700 Class B (N2K PGNs 129038–129810)
  ↓ N2K bus → YDNU-02 → Signal K
  ↓ vessels.<MMSI>.{name, position, SOG, COG, ...}
  ├──► InfluxDB (log trafic AIS)
  └──► Vulcan 7 FS (targets sur carte)
```

---

## 6. PRIORITÉS DES SOURCES SIGNAL K

| Path Signal K | Priorité 1 (haute) | Priorité 2 | Priorité 3 |
|---------------|-------------------|-----------|-----------|
| `navigation.position` | UM982 | Vulcan 7 internal GPS | — |
| `navigation.headingTrue` | UM982 | — | — |
| `navigation.speedOverGround` | UM982 | Vulcan 7 | — |
| `navigation.attitude.*` | **WIT IMU** | Calypso (si --compass=on) | — |
| `navigation.rateOfTurn` | WIT IMU | UM982 dual-antenna | — |
| `environment.wind.*` | **Calypso UP10** | WS320 (via N2K) | — |
| `environment.outside.temperature` | Calypso UP10 | YDBC-05 | — |
| `environment.outside.pressure` | YDBC-05 | — | — |
| `vessels.*` (AIS) | AIS700 | — | — |

---

## 7. UNITÉS SI — RÉFÉRENCE RAPIDE

| Grandeur | Unité Signal K | Affichage Grafana | Conversion |
|----------|---------------|------------------|-----------|
| Vitesse (SOG, vent) | m/s | nœuds | × 1.944 |
| Cap, angle | radians | degrés | × 57.296 |
| Température | Kelvin | °C | − 273.15 |
| Pression | Pascal | hPa | ÷ 100 |
| Taux de giration | rad/s | °/s | × 57.296 |
| État de charge | ratio 0–1 | % | × 100 |
| Position | degrés décimaux | degrés décimaux | — |

---

## 8. RÈGLES ABSOLUES — OPÉRATION OC

> Ces règles s'appliquent à tout prompt généré par Dust/OC.  
> Aucune exception sans validation explicite de Denis.

| # | Règle | Raison |
|---|-------|--------|
| 1 | Signal K = `systemctl` UNIQUEMENT | Port 3000, service natif |
| 2 | InfluxDB = Docker UNIQUEMENT | Port 8086, container |
| 3 | Grafana = Docker UNIQUEMENT | Port 3001, container |
| 4 | Fichiers JSON = `python3` UNIQUEMENT | Jamais `sed` sur du JSON |
| 5 | Aucun token/secret dans `git commit` | Sécurité |
| 6 | Après chaque action : `git add -A && git commit -m '...' && git push` | Traçabilité |
| 7 | Changement structurel = validation Denis avant exécution | Sécurité |
| 8 | `HEADINGOFFSET 90` dans UM982 NVRAM = NE PAS écraser | Permanent, critique |
| 9 | `attitude.js` patché (2026-05-17) = référence actuelle | PGN 127257 actif |
| 10 | SOK BMS → direct InfluxDB (bypass Signal K) | Architecture volontaire |

---

## 9. SÉCURITÉ

### 9.1 Secrets — Emplacement

| Secret | Emplacement | Dans git ? |
|--------|-------------|-----------|
| InfluxDB token | `.env` | ❌ jamais |
| Grafana admin password | `.env` | ❌ jamais |
| OpenClaw token | `.openclaw-token` | ❌ jamais |
| GitHub PAT | Env variable SSH session | ❌ jamais |
| WiFi password | `config/wifi-ap.txt` | ⚠️ git privé seulement |

### 9.2 .gitignore — Fichiers exclus

```
.env
*.env
.openclaw-token
*.secret
*.key
*.pem
```

### 9.3 Firewall UFW — Ports ouverts

| Port | Service | Accès |
|------|---------|-------|
| 3000 | Signal K | LAN + Cloudflare Tunnel |
| 3001 | Grafana | LAN + Cloudflare Tunnel |
| 8086 | InfluxDB | LAN uniquement |
| 22 | SSH | LAN uniquement |
| 18789 | OpenClaw Gateway | localhost uniquement |

### 9.4 YDNU-02 Silent Mode

```bash
# En cas de bug Signal K → protéger le bus N2K
echo YDNU SILENT ON > /dev/ttyACM0
# LED bleue = mode silencieux (lecture seule)
```

---

## 10. PROCÉDURES DE DÉMARRAGE

### 10.1 Démarrage normal (ordre)

```bash
# 1. Signal K (premier — toujours)
sudo systemctl start signalk

# 2. Docker (InfluxDB + Grafana + Regatta)
cd ~/midnightrider-navigation
docker compose up -d

# 3. Services Python BLE
sudo systemctl start calypso_anemometer calypso_watchdog

# 4. Vérification
sudo systemctl status signalk calypso_anemometer
docker compose ps
```

### 10.2 Arrêt propre (ordre inverse)

```bash
sudo systemctl stop calypso_anemometer calypso_watchdog
docker compose down
sudo systemctl stop signalk
```

### 10.3 Vérification rapide pré-régate

```bash
# État des services
sudo systemctl status signalk calypso_anemometer
docker compose ps

# Données live Signal K
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/ | \
  jq '{headingTrue, speedOverGround, position: .position.value}'

# Batterie SOK
curl -s http://localhost:3000/signalk/v1/api/vessels/self/ | \
  jq '.electrical' 2>/dev/null || \
  docker exec influxdb influx query \
  'from(bucket:"midnight_rider") |> range(start: -5m) |> filter(fn:(r) => r._measurement == "sok_bms") |> last()'

# Pression atmosphérique
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/outside/pressure | \
  jq '.value / 100 | tostring + " hPa"'
```

---

## 11. JOURNAL DES CHANGEMENTS MAJEURS

| Date | Changement | Impact |
|------|-----------|--------|
| 2026-04-25 | Déploiement initial RPi 4 | Système opérationnel |
| 2026-04-28 | Audit sécurité + rotation tokens | Sécurité renforcée |
| 2026-05-01 | Polaires J/30 v1 (incorrectes) | — |
| 2026-05-12 | SOK BMS integration complète | Monitoring batterie actif |
| 2026-05-13 | Inventaire instruments v1 | Documentation |
| 2026-05-17 | **HEADINGOFFSET 90 permanent (UM982 NVRAM)** | Cap corrigé ✅ |
| 2026-05-17 | **attitude.js patché (PGN 127257 → Vulcan 7)** | Gîte sur Vulcan ✅ |
| 2026-05-19 | YDBC-05 barometer installé sur N2K | Pression active ✅ |
| 2026-05-19 | AIS700 installé sur N2K | AIS actif ✅ |
| 2026-05-20 | Révision complète documentation hardware | Datasheets à jour |
| 2026-05-20 | Polaires J/30 v3 — données ORC réelles (UK) | Polaires corrigées ✅ |
| 2026-05-20 | **Ce document — Architecture v4.0** | Référence canonique |

---

## 12. FICHIERS DE RÉFÉRENCE CLÉS

| Fichier | Rôle |
|---------|------|
| `docs/ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md` | Ancien doc archi (partiellement obsolète) |
| **`docs/ARCHITECTURE-REFERENCE-2026-05-20.md`** | **CE DOCUMENT — référence canonique** |
| `docs/HARDWARE/INSTRUMENT-INVENTORY.md` | Inventaire instruments à jour |
| `docs/DATA-SCHEMA-MASTER.md` | Schéma complet données Signal K / InfluxDB |
| `docs/GRAFANA-UNIT-CONVERSIONS.md` | Conversions unités pour Grafana |
| `docs/SYSTEM-SUMMARY.md` | Résumé système (référencé par Dust) |
| `docs/DASHBOARDS-README.md` | Guide dashboards Grafana (référencé par Dust) |
| `logs/latest.json` | Journal d'exécution OC |
| `data/polars/j30_orc.json` | Polaires J/30 v3 — données ORC réelles |
| `docker-compose.yml` | Configuration Docker (InfluxDB, Grafana, Regatta) |
| `.env` | Secrets (NON versionné) |

---

**Maintenu par :** Denis LAFARGE + OC (OpenClaw via Dust)  
**Prochain événement :** Block Island Race — 2026-05-22  
**Contact urgence :** `logs/latest.json` → état système en temps réel


---

## REPOSITORY CLEANUP & STRUCTURE — 2026-05-29

### Cleanup Rounds Completed

**Round 1 (commit b3aaacf):** Removed 11 debug/superseded files
- Debug logs (3 files)
- Duplicate documentation (2 files)
- Superseded scripts (5 files)
- Old dashboard version (1 file)

**Round 2 (commit aae1073):** Removed 4 files, moved 3 files
- Debug artifacts: ble_diagnostic.txt, diagnostic_raw.txt
- MCP dedup: mcp/racing-server.js, mcp/racing-package.json
- Root reorganization: 3 docs moved to docs/

**Round 3 (commit a1a279e):** Removed 34 files
- docs/grafana-dashboards/ (complete duplicate)
- docs/archive/ (12 abandoned specs)
- logs/ (12 debug artifacts)
- .gitignore: added *.pyc rule

### Repository Structure (Post-Cleanup)

```
midnightrider-navigation/
├── grafana-dashboards/          # Active Grafana dashboard JSONs (13 dashboards)
├── docs/                        # Documentation (architecture, integration, hardware)
│   ├── OPERATIONS/              # Field test, race day checklists
│   ├── HARDWARE/                # Datasheets (Calypso, UM982, WIT, Vulcan, etc.)
│   ├── INTEGRATION/             # Setup guides for each device
│   ├── SOFTWARE/                # Signal K, Grafana, InfluxDB docs
│   └── index.md                 # Documentation index
├── scripts/                     # Deployment & monitoring scripts
├── logs/                        # Operational logs (latest.json, cleanup logs, oc-actions.log)
├── mcp/                         # Model Context Protocol servers (race, weather, polar, etc.)
├── plugins/                     # Signal K plugins (2 versions of astronomical)
├── portal/                      # Web dashboard (HTTP server)
├── regatta/                     # Race-day reporting system
├── data/                        # Polar curves (J30 ORC)
└── docker-compose.yml           # Container orchestration
```

### Known Plugin Duality

**Astronomical Plugin:** Two versions exist in plugins/
- signalk-astronomical.js (11.4 KB)
- signalk-astronomical-direct.js (10.0 KB)

**Status:** Configuration shows `signalk-astronomical.json` enabled with NOAA station 8518750
**Decision:** Keep both versions; unclear which is active. Recommend consolidation in future refactor.

### Pending Issues

1. **logs/__pycache__/write_log.cpython-313.pyc** — Python bytecode file committed (should be in .gitignore)
2. **Astronomical plugin duplication** — Two working versions, unclear which is "primary"

### Cleanup Summary

| Metric | Value |
|--------|-------|
| Total files deleted | 57 |
| Total files moved | 3 |
| Repository size reduction | ~15 KB |
| Cleanup rounds | 3 |
| Status | ✅ COMPLETE |

---
**Cleaned on:** 2026-05-29 22:35 UTC
**Cleaned by:** OC Agent (automated)


---

## Changelog — 2026-06-15 — WIT Acceleration Corrected

**Commits:** 039581b + e052630 + 9fe25f2d

| Bug | Cause | Fix | Result |
|---|---|---|---|
| rateOfTurn = -769°/s (physically impossible) | CMD_ACCEL read register 0x61 (unknown/garbage data) | CMD_ACCEL → register 0x34 (standard WIT AX register) | rateOfTurn = -0.02 rad/s ✅ |
| acceleration x=0, y=0, z=4.79 (wrong orientation) | Register 0x61 does NOT contain acceleration | Same fix as above | \|A\| = 10.0 m/s² ≈ g ✅ |

**WIT Register Map Verified:**
- AX=0x34, AY=0x35, AZ=0x36 (acceleration)
- GX=0x37, GY=0x38, GZ=0x39 (gyro rate)

**Confirmed Values at Dock (2026-06-15 12:02 EDT):**
- Acceleration magnitude: 10.005 m/s² (expected gravity ≈ 9.81 m/s²) ✅
- Rate of turn: -0.02 rad/s (vessel at rest) ✅
- WIT mounted level on companionway ✅

**Logging:** WIT + Calypso raised to INFO level (2026-06-15) — was DEBUG @ 8 msg/sec, now <2 msg/sec production logging.


## ⚠️ NOTE ARCHITECTURALE — 2026-06-15 AUDIT

### Corrections apportées

| Composant | État documentation | État réel | Action |
|---|---|---|---|
| signalk-performance-polars | "Actif" | Config orpheline, jamais installé | ✅ SUPPRIMÉ |
| signalk-sails-management-v2 | "Actif" | Config orpheline, jamais installé | ✅ SUPPRIMÉ |
| signalk-n2k-bridge (P5) | "Émet PGNs N2K" | 0 mappings configurés | ⚠️ Conservé comme backup |
| Output N2K (SK → Vulcan) | "Actif" | INACTIF — aucun PGN transmis | 🔧 P5 planifié |

### P5 — Plugin N2K Bridge (conception en cours)

Remplacera `signalk-n2k-bridge (P5)` pour l'output N2K avec:
- Conversions standard (leeway PGN 128000, courant PGN 129291)
- Conversions B&G propriétaires (PGN 130824)
- Architecture extensible et modulaire
- `signalk-n2k-bridge (P5)` maintenu comme backup jusqu'à validation P5

# DATA SCHEMA MASTER — Midnight Rider Navigation
**Source de vérité unique pour l'architecture data du projet**
**Généré le:** 2026-04-28
**Dernière mise à jour:** 2026-04-28
**Auteur:** OC (Open Claw) — validé Denis Lafarge

---

## Légende des statuts

| Statut | Signification | Exemple |
|---|---|---|
| ✅ Actif | Opérationnel et confirmé dans InfluxDB | UM982 GNSS, WIT IMU |
| ⏳ Non connecté | Instrument physique non encore branché au réseau | B&G WS320, SOK BMS |
| 🔨 À construire | Intégration software/API non encore développée | NOAA Buoys, NDBC API |
| ❓ À confirmer | Présence dans InfluxDB non encore vérifiée | navigation.headingTrue |
| ❌ Absent | Capteur non disponible à bord | STW (Speed Through Water) |

---

## 1. Architecture globale du flux de données

```
┌─────────────────────────────────────────────────────────────┐
│ RÉSEAU NMEA 2000 (bus CAN)                                  │
│ B&G WS320 · B&G Vulcan GPS · Loch · Baro · AIS             │
└──────────────────────┬──────────────────────────────────────┘
                       │ YDNU-02 (bidirectionnel NMEA 2000 ↔ USB)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ SIGNAL K :3000                                              │
│ + UM982 (USB) · WIT BLE · Calypso BLE · RPi sys            │
│ + Regatta Server :5000 · qtVLM TCP :10111                  │
│ Calibration → réinjection NMEA 2000                         │
│ Fusion multi-sources (tags source InfluxDB)                 │
└────────┬─────────────────┬──────────────┬───────────────────┘
         │                 │              │
         ▼                 ▼              ▼
    InfluxDB :8086     qtVLM :10110  NMEA 2000 (retour)
    midnight_rider     NMEA 0183 TCP données calibrées
         │
         ▼
    Grafana :3001 — 9 dashboards · 65 alertes
         │
         ▼
    MCP (7 serveurs · 37 outils)
         │
         ▼
    OC / Claude → WhatsApp → Denis & Anne-Sophie
```

---

## 2. Catalogue des sources de données

### Architecture des connexions capteurs

**Réseau NMEA 2000 (via Yacht Devices YDNU-02)**
Le YDNU-02 est un gateway bidirectionnel NMEA 2000 ↔ USB.
Tous les instruments ci-dessous transitent par ce bus :

| Instrument | Mesures | PGN NMEA 2000 | Statut |
|---|---|---|---|
| B&G WS320 (anémomètre) | TWS, TWD, AWA, AWS | PGN 130306 | ⏳ Appairage requis |
| Loch (à installer) | STW, distance | PGN 128259 | ⏳ Capteur non installé |
| Baromètre (à définir) | Pression atmosphérique | PGN 130314 | ⏳ Capteur non installé |
| AIS Transponder Class B | Vessels, position, MMSI | PGN 129038/129039 | ⏳ Non installé (obligatoire ORC) |
| B&G Vulcan (écrans) | Position GPS interne, SOG, COG | PGN 129025/129026 | ✅ Actif (source secondaire GPS) |

**Connexions directes Signal K (hors NMEA 2000)**

| Instrument | Protocole | Plugin Signal K | Statut |
|---|---|---|---|
| UM982 NANO-HED10L | NMEA 0183 / USB | signalk-parser-nmea0183 | ✅ Actif |
| WIT WT901BLECL IMU | BLE JSON | bleak_wit.py | ✅ Actif |
| Calypso ULTRASONIC | BLE | signalk-calypso (prévu) | ⏳ Non connecté |
| Système RPi 4 | sysfs / proc | signalk-system-stats | ✅ Actif |
| Regatta Server | HTTP REST :5000 | plugin custom | ✅ Actif |
| qtVLM | NMEA 0183 TCP :10111 | signalk-tcp-server | ✅ Actif (bidirectionnel) |

### Tableau des instruments



| # | Instrument | Type | Protocole | Fréquence | Mesures principales | Statut |
|---|---|---|---|---|---|---|
| 1 | UM982 NANO-HED10L | GNSS dual-antenna | NMEA / USB | 1 Hz | Position, SOG, COG, Heading | ✅ Actif |
| 2 | WIT WT901BLECL IMU | Accéléromètre/gyro | BLE JSON | 30 Hz | Roll, pitch, yaw, accél, temp | ✅ Actif |
| 3 | B&G WS320 | Anémomètre mécanique | NMEA 2000 | 1 Hz | TWS, TWD, AWA, AWS | ⏳ Non connecté |
| 4 | Système RPi 4 | CPU, mémoire, temp | Signal K internal | 5 s | CPU temp, load, storage | ✅ Actif |
| 5 | NOAA NDBC | Météo côtière (buoys LIS) | HTTP API | 30 min | Vent, pression, temp eau | 🔨 À construire |
| 6 | Open-Meteo | Prévisions météo | HTTP API | 6h (scheduler) | Vent prévu, pression, gust | ✅ Actif |
| 7 | Regatta Server | Timer, équipage | HTTP local :5000 | Event-driven | Timer départ, watch crew, scoring | ✅ Actif |
| 8 | SOK BMS LiFePO4 | Batterie maison | BLE (BMS protocol) | 1 Hz | Voltage, current, SOC, temp cell | ⏳ Non connecté (~5 mai) |
| 9 | Yacht Devices YDNU-02 | Gateway NMEA 2000 ↔ USB | NMEA 2000 bidirectionnel | passthrough | Bridge instruments NMEA 2000 → Signal K (et retour) | ✅ Actif |
| 10 | B&G Vulcan (écrans) | Chartplotter avec GPS interne | NMEA 2000 | 1 Hz | Position GPS, SOG, COG (source secondaire) | ✅ Actif |
| 11 | Loch (à installer) | Capteur vitesse dans l'eau | NMEA 2000 (via YDNU-02) | 1 Hz | STW, distance parcourue | ⏳ Non installé |
| 12 | Baromètre (à définir) | Capteur pression | NMEA 2000 (via YDNU-02) | 1/min | Pression atmosphérique | ⏳ Non installé |
| 13 | AIS Transponder Class B | Transpondeur AIS | NMEA 2000 (via YDNU-02) | event | Vessels, position, MMSI | ⏳ Non installé (obligatoire ORC) |

---

---

## 2b. Stratégie multi-sources — Capteurs redondants

Plusieurs capteurs mesurent les mêmes grandeurs physiques (vent, attitude, position GPS).
Principe : chaque source est loggée indépendamment dans InfluxDB avec un tag source.
Aucune donnée n'est perdue. La fusion ou la priorité est appliquée à la couche affichage
(Grafana) ou analyse (OC), pas au niveau du stockage.

### Sources redondantes et stratégie

| Grandeur | Sources | Signal K path | Tag source InfluxDB | Priorité affichage |
|---|---|---|---|---|
| Vent (TWS/TWD) | B&G WS320 (NMEA 2000), Calypso (BLE) | environment.wind.* | nmea2000_ws320, calypso_ble | WS320 prioritaire (mât, plus précis en vitesse) |
| Attitude (roll/pitch/yaw) | WIT WT901BLECL (BLE, hull), Calypso (BLE, masthead) | navigation.attitude.* | wit_hull, calypso_masthead | WIT prioritaire (30 Hz vs 1 Hz Calypso) |
| Heading | UM982 (GNSS dual-ant), Calypso (masthead) | navigation.headingTrue | um982_gnss, calypso_masthead | UM982 prioritaire (RTK Float, précis) |
| Position GPS | UM982 (principal), B&G Vulcan (secondaire) | navigation.position | um982_primary, vulcan_internal | UM982 prioritaire (dual-antenna, RTK) |
| SOG / COG | UM982 (principal), B&G Vulcan (secondaire) | navigation.speedOverGround, navigation.courseOverGroundTrue | um982_primary, vulcan_internal | UM982 prioritaire |
| Température de l'air | Calypso (masthead), NOAA API (externe) | environment.outside.temperature | calypso_masthead, noaa_api | Calypso si connecté, NOAA sinon |

### Configuration Signal K requise

Dans Signal K, activer le logging multi-sources dans le plugin signalk-to-influxdb2 :
```json
{
  "logAllSources": true,
  "tagWithSource": true
}
```

Cela garantit que chaque valeur est stockée avec son tag source dans InfluxDB,
permettant des queries filtrées par source ou comparatives.

### Query Flux exemple — comparer deux sources de vent
```flux
from(bucket: "midnight_rider")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "environment.wind.speedTrue")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
  |> group(columns: ["source"])
  |> aggregateWindow(every: 5s, fn: mean, createEmpty: false)
```

---

## 2c. Calibration Signal K et réinjection NMEA 2000

Signal K peut appliquer des corrections sur les données entrantes et les réinjecter
sur le bus NMEA 2000 via le YDNU-02 (bidirectionnel).
Cela permet à tous les instruments du bord (Vulcan, etc.) d'afficher des données calibrées.

| Mesure | Correction appliquée dans Signal K | Réinjectée NMEA 2000 ? | PGN cible | Statut |
|---|---|---|---|---|
| **Heading (cap compas)** | Déclinaison magnétique (auto via position GPS) | ✅ Prévu | PGN 127250 | ⏳ À configurer |
| **Variation magnétique** | Calculée par Signal K (plugin variation) | ✅ Prévu | PGN 127258 | ⏳ À configurer |
| **Depth (profondeur)** | Offset quille (à définir selon tirant d'eau J/30) | ✅ Prévu | PGN 128267 | ⏳ Loch non installé |
| **STW calibrée** | Coefficient de calibration loch | ✅ Prévu | PGN 128259 | ⏳ Loch non installé |
| **Vent calibré (offset direction)** | Correction d'installation WS320 (upwash) | ✅ Prévu | PGN 130306 | ⏳ WS320 non connecté |

> ⚠️ **Règle anti-conflit :** Ne jamais réinjecter une PGN déjà émise par un instrument actif
> (ex: ne pas réinjecter PGN 130306 si le WS320 émet déjà cette PGN sur le bus).

**Note :** La réinjection nécessite que le YDNU-02 soit configuré en mode bidirectionnel
(paramètre "PGN forwarding" activé dans la config YDNU-02).

---

## 2d. Interface YDNU-02 — Filtrage des données NMEA 2000 ↔ Signal K

Le YDNU-02 est configuré pour contrôler quelles PGNs passent dans chaque direction.
Toutes les PGNs ne doivent pas nécessairement être transmises — certaines sont ignorées
pour éviter les conflits ou la surcharge.

### NMEA 2000 → Signal K (lecture)

| PGN | Données | Source | Transmis ? | Notes |
|---|---|---|---|---|
| 129025 | Position GPS | Vulcan | ✅ Oui | Source secondaire (priorité basse) |
| 129026 | SOG / COG | Vulcan | ✅ Oui | Source secondaire |
| 130306 | Vent (vitesse + direction) | B&G WS320 | ✅ Oui (dès connexion) | |
| 128259 | STW / distance | Loch | ✅ Oui (dès installation) | |
| 130314 | Pression atmosphérique | Baromètre | ✅ Oui (dès installation) | |
| 129038/129039 | AIS vessels | AIS transponder | ✅ Oui (dès installation) | |
| 127250 | Cap compas | Vulcan / compas | ✅ Oui | |
| 127257 | Attitude (roll/pitch) | Vulcan | ⚠️ Optionnel | Redondant avec WIT (priorité WIT) |

### Signal K → NMEA 2000 (réinjection)

| PGN | Données | Condition | Transmis ? | Notes |
|---|---|---|---|---|
| 127250 | Cap vrai calibré | Signal K calcule heading + déclinaison | ✅ Prévu | Affichage Vulcan |
| 127258 | Variation magnétique | Signal K plugin variation | ✅ Prévu | |
| 130306 | Vent calibré (offset corrigé) | WS320 connecté + calibration configurée | ✅ Prévu | |
| 128259 | STW calibrée | Loch installé + coefficient configuré | ✅ Prévu | |
| 128267 | Profondeur calibrée | Loch installé + offset quille | ✅ Prévu | |
| 129025 | Position UM982 (haute précision) | UM982 actif (RTK Float) | ✅ Prévu | Override GPS Vulcan |

⚠️ **Point d'attention :** Éviter de réinjecter une PGN déjà émise par un instrument sur
le bus (risque de conflit). Par exemple, ne pas réinjecter PGN 130306 (vent) si le WS320
émet déjà cette PGN sur le bus.

Cette règle est répétée ici par souci de clarté (voir aussi Section 2c).

## 3. Signal K paths actifs (réalité du terrain)

Basé sur audit direct du 28 avril 2026.

| Path Signal K | Instrument source | Unité SI | Valeur sample (28 avr) | Fréquence | Status |
|---|---|---|---|---|---|
| navigation.speedOverGround | UM982 | m/s | 3.2 | 1 Hz | ✅ |
| navigation.courseOverGroundTrue | UM982 | radians | 2.2096 | 1 Hz | ✅ |
| navigation.headingTrue | UM982 + WIT | radians | 1.741 | 1 Hz | ❓ À confirmer |
| navigation.position.latitude | UM982 | degrés décimaux | 41.5425 | 1 Hz | ✅ |
| navigation.position.longitude | UM982 | degrés décimaux | -71.4132 | 1 Hz | ✅ |

> ⚠️ **Note InfluxDB :** `navigation.position` est stocké comme measurement unique
> avec les fields `lat` et `lon` (voir Section 4). Les paths Signal K `.latitude` et
> `.longitude` sont la vue applicative ; dans InfluxDB ils apparaissent comme fields
> d'un même measurement.

| navigation.attitude.roll | WIT WT901BLECL | radians | -0.00518 | 30 Hz | ✅ |
| navigation.attitude.pitch | WIT WT901BLECL | radians | -0.02291 | 30 Hz | ✅ |
| navigation.attitude.yaw | WIT WT901BLECL | radians | -0.03445 | 30 Hz | ✅ |
| navigation.speedThroughWater | N/A | m/s | N/A | N/A | ❌ Absent |
| navigation.rateOfTurn | WIT calc | rad/s | ~0.01 | 30 Hz | ✅ |
| navigation.gnss.satellites | UM982 | count | 12 | 1 Hz | ✅ |
| navigation.gnss.type | UM982 | string | "RTK Float" | 1 Hz | ✅ |

| navigation.acceleration.x | WIT | m/s² | -0.15 | 30 Hz | ✅ |
| navigation.acceleration.y | WIT | m/s² | 0.22 | 30 Hz | ✅ |
| navigation.acceleration.z | WIT | m/s² | 9.81 | 30 Hz | ✅ |
| environment.wind.speedTrue | B&G WS320 | m/s | N/A | N/A | ⏳ Non connecté (B&G WS320) |
| environment.wind.directionTrue | B&G WS320 | radians | N/A | N/A | ⏳ Non connecté (B&G WS320) |
| environment.wind.speedApparent | B&G WS320 | m/s | N/A | N/A | ⏳ Non connecté (B&G WS320) |
| environment.wind.angleApparent | B&G WS320 | radians | N/A | N/A | ⏳ Non connecté (B&G WS320) |
| environment.system.cpuTemperature | RPi sysfs | Kelvin | 323.15 (50°C) | 5 s | ✅ |
| environment.outside.temperature | NOAA API | Kelvin | N/A | 30 min | 🔨 À construire (NOAA API) |
| environment.water.temperature | NOAA API | Kelvin | N/A | 30 min | 🔨 À construire (NOAA API) |
| environment.outside.pressure | NOAA API | Pa | N/A | 30 min | 🔨 À construire (NOAA API) |
| electrical.batteries.house.voltage | SOK BMS (future) | V | N/A | 1 Hz | ⏳ Non connecté |
| electrical.batteries.house.current | SOK BMS (future) | A | N/A | 1 Hz | ⏳ Non connecté |
| electrical.batteries.house.stateOfCharge | SOK BMS (future) | ratio 0-1 | N/A | 1 Hz | ⏳ Non connecté |
| regatta.timer.startTime | Regatta Server | ISO 8601 | 2026-05-22T14:00:00Z | event | ✅ |
| regatta.crew.watch | Regatta Server | string | "crew-A" | event | ✅ |

**Status récapitulatif:**
- ✅ **Confirmé dans InfluxDB**: 16 measurements
- ❓ **À confirmer**: 1 measurement (heading)
- 🔨 **À construire (software)**: 4 measurements (NOAA)
- ⏳ **Non connecté (hardware)**: 5 measurements (B&G WS320 + SOK BMS)
- ❌ **Absent**: 1 (STW — capteur manquant)

---

## 4. InfluxDB — Structure des measurements

**Bucket:** midnight_rider
**Rétention actuelle:** 30 jours (par défaut)
**Rétention recommandée:** 
  - Brute (1s): 30 jours
  - Downsampled (1h mean): 1 an
  - Archive (24h mean): 7 ans

**Fréquence globale d'écriture:**
  - **Estimated:** ~3,000 points/min (1,800 de WIT à 30 Hz + 1,200 navigation/wind à 1 Hz)
  - **Vérification requise:** Phase 1.3

| Measurement (nom exact InfluxDB) | Field | Unité brute | Valeur sample (28 avr) | Points/min | Conversion requise |
|---|---|---|---|---|---|
| navigation.speedOverGround | _value | m/s | 3.2 | ~60 | × 1.94384 → knots |
| navigation.courseOverGroundTrue | _value | radians | 2.2096 | ~60 | × 57.2958 → ° |
| navigation.attitude.roll | _value | radians | -0.00518 | ~1800 (30 Hz) | × 57.2958 → ° |
| navigation.attitude.pitch | _value | radians | -0.02291 | ~1800 (30 Hz) | × 57.2958 → ° |
| navigation.attitude.yaw | _value | radians | -0.03445 | ~1800 (30 Hz) | × 57.2958 → ° |
| navigation.rateOfTurn | _value | rad/s | ~0.01 | ~1800 (30 Hz) | × 57.2958 → °/s |
| navigation.acceleration.x | _value | m/s² | -0.15 | ~1800 (30 Hz) | N/A (SI unit) |
| navigation.acceleration.y | _value | m/s² | 0.22 | ~1800 (30 Hz) | N/A (SI unit) |
| navigation.acceleration.z | _value | m/s² | 9.81 | ~1800 (30 Hz) | N/A (SI unit) |
| navigation.position | lat, lon | degrés décimaux | 41.5425, -71.4132 | ~60 | N/A (already decimal) |
| navigation.gnss.satellites | _value | count | 12 | ~60 | N/A (count) |
| navigation.gnss.type | _value | string | "RTK Float" | ~60 | N/A (string) |
| environment.system.cpuTemperature | _value | Kelvin | 323.15 | ~12/min (5s) | - 273.15 → °C |
| environment.wind.speedTrue | _value | m/s | N/A | N/A | × 1.94384 → knots |
| environment.wind.directionTrue | _value | radians | N/A | N/A | × 57.2958 → ° |
| environment.wind.speedApparent | _value | m/s | N/A | N/A | × 1.94384 → knots |
| environment.wind.angleApparent | _value | radians | N/A | N/A | × 57.2958 → ° |

---

## 5. Table de conversions — Référence Flux

**Appliqué dans tous les dashboards Grafana via Flux queries.**

| Catégorie | Unité SI | Unité display | Snippet Flux | Measurements concernés |
|---|---|---|---|---|
| **Angles** | radians | degrés (°) | `\|> map(fn: (r) => ({r with _value: r._value * 57.2958}))` | roll, pitch, yaw, heading, course, wind direction, rate of turn |
| **Vitesses** | m/s | nœuds (kt) | `\|> map(fn: (r) => ({r with _value: r._value * 1.94384}))` | SOG, STW, TWS, AWS, VMG, courant |
| **Températures** | Kelvin | °C | `\|> map(fn: (r) => ({r with _value: r._value - 273.15}))` | CPU temp, outside temp, water temp |
| **Pression** | Pascal | hPa/mbar | `\|> map(fn: (r) => ({r with _value: r._value / 100.0}))` | atmospheric pressure |
| **SOC batterie** | ratio 0-1 | % | `\|> map(fn: (r) => ({r with _value: r._value * 100.0}))` | stateOfCharge |

**Template de query Flux complet (exemple SOG avec conversion):**
```flux
from(bucket: "midnight_rider")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> filter(fn: (r) => r._field == "_value")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
  |> aggregateWindow(every: 5s, fn: mean, createEmpty: false)
```

---

## 6. Plages de valeurs et seuils d'alerte

**Ces valeurs définissent ce qui est "normal" pour un J/30 en course. À affiner après field test (19 mai 2026).**

| Mesure | Unité display | Au port | Navigation normale | Course | Seuil WARN | Seuil CRIT | Notes |
|---|---|---|---|---|---|---|---|
| **Roll (gîte)** | ° | ±2° | ±15° | ±25° | ±30° | ±40° | J/30: max théorique ±90°; excès =risk |
| **Pitch (assiette)** | ° | ±1° | ±5° | ±10° | ±15° | ±20° | Trim optimal: 0-2° |
| **SOG** | kt | 0 | 3-6 | 5-8 | <0.5 pendant >30s | N/A | Vitesse nulle brève acceptable en manœuvre |
| **TWS (vent réel)** | kt | — | 8-20 | 10-25 | >30 | >40 | Limite J/30 ~35-40 kt |
| **AWS (vent apparent)** | kt | — | 10-25 | 12-30 | >35 | >45 | |
| **TWD (direction)** | ° | — | variable | variable | shift >20° en 5min | N/A | Mark approach sensible |
| **Heading** | ° | — | stable | variable | dérive >10° | N/A | Vérifier trim + autocap |
| **CPU temp** | °C | 40-50 | 55-65 | 65-75 | >80 | >85 | RPi 4 max 85°C |
| **Voltage maison** | V | 13.2 | 12.8-13.5 | 12.5-13.5 | <12.0 | <11.5 | LiFePO4 nominal 12.8V ⏳ |
| **SOC batterie** | % | 100 | >60 | >40 | <20 | <10 | ⏳ (future) |

---

## 7. Vue par dashboard Grafana

| Dashboard | Measurements consommés | Refresh | Panels | Status |
|---|---|---|---|---|
| 🏠 **COCKPIT** (ID: 8) | navigation.speed*, heading*, attitude.*, course* | 5s | 8 | ✅ Actif |
| 🌊 **ENVIRONMENT** (ID: 10) | environment.wind.*, outside.*, water.*, system.cpu* | 30s | 7 | ⏳ Non connecté (B&G WS320) |
| ⚡ **PERFORMANCE** (ID: 13) | navigation.speed*, polar, VMG | 5s | 7 | ⏳ À vérifier |
| 🌪️ **WIND & CURRENT** (ID: 15) | environment.wind.*, navigation.current* | 10s | 7 | ⏳ À vérifier |
| 🏆 **COMPETITIVE** (ID: 16) | AIS, fleet, distance, performance | 30s | 7 | ⏳ À vérifier |
| 🔋 **ELECTRICAL** (ID: 17) | electrical.batteries.*, solar.* | 30s | 7 | ⏳ Non connecté (SOK BMS) |
| 🏁 **RACE** (ID: 18) | navigation.*, regatta.timer, current* | 5s | 7 | ⏳ À vérifier |
| 🔔 **ALERTS** (ID: 19) | tous (event-based) | 10s | 2 | ⏳ À vérifier |
| ⚓ **CREW** (ID: 20) | regatta.crew, navigation.speed*, timer | 30s | 10 | ⏳ À vérifier |

---

## 8. Vue par serveur MCP

**Audit 2026-05-01:** 7 serveurs implémentés. 🔧 **ISSUE:** Tous utilisent bucket 'signalk', doivent utiliser 'midnight_rider'. Voir `docs/MCP-INTEGRATION-STATUS.md`.

| Serveur MCP | Fichier | Bucket | Statut | Notes |
|---|---|---|---|---|
| **Astronomical** | astronomical-server.js | midnight_rider | ✅ Actif | Calculs locaux |
| **Weather** | weather-server.js | midnight_rider | ✅ Actif | Open-Meteo API |
| **Racing** | racing-server.js | midnight_rider | ✅ Actif | Performance de course |
| **Polar** | polar-server.js | midnight_rider | ✅ Actif | Polars J/30 |
| **Race** | race-server.js | midnight_rider | ✅ Actif | Race management |
| **Buoy** | buoy-server.js | midnight_rider | ⚠️ Partiel | MCP ✅, NOAA data TBD |
| **Crew** | crew-server.js | midnight_rider | ⏳ En attente | Regatta.crew requis |

---

---

## 8.2 Alignement avec DATA-SCHEMA-MASTER

**Bucket InfluxDB utilisé:** `midnight_rider` (27 measurements actifs)  
**Outils MCP exposés:** 37 outils (5 serveurs + 2 partiels)  
**Statut global:** 5/7 serveurs fully operational

---

## 8b. Interface qtVLM — Navigation et routing

qtVLM est le logiciel de routage et navigation utilisé à bord.
Il communique avec Signal K via NMEA 0183 sur TCP, bidirectionnel.

### Architecture de la connexion

```
Signal K :3000
│ NMEA 0183 TCP server
├──► qtVLM port :10110 (Signal K → qtVLM)
│    Données envoyées : position, SOG, COG, heading, vent
│
└◄── qtVLM port :10111 (qtVLM → Signal K)
     Données reçues : waypoints actifs, routing data, AIS décodé
```

### Données Signal K → qtVLM (port 10110, NMEA 0183 TCP)

| Sentence NMEA 0183 | Données | Source Signal K | Fréquence |
|---|---|---|---|
| $GPGGA / $GPRMC | Position, SOG, COG | UM982 (primary) | 1 Hz |
| $HEHDT | Heading true | UM982 | 1 Hz |
| $WIMWV | Vent apparent (AWA, AWS) | B&G WS320 | 1 Hz (dès connexion) |
| $WIMWD | Vent vrai (TWD, TWS) | B&G WS320 | 1 Hz (dès connexion) |
| $VDVHW | STW, cap magnétique | Loch | 1 Hz (dès installation) |

### Données qtVLM → Signal K (port 10111, NMEA 0183 TCP)

| Sentence NMEA 0183 | Données | Utilisation dans Signal K | Status |
|---|---|---|---|
| $GPWPL / $GPBWC | Waypoint actif, bearing, distance | Affichage dans dashboards Grafana | ✅ Actif |
| $VDRMB | Route active, XTE | Alertes déviation de route (OC) | ✅ Actif |
| $AIVDM | AIS vessels (si qtVLM a un décodeur AIS) | Source AIS complémentaire | ⏳ À vérifier |

### Signal K paths alimentés par qtVLM

| Signal K path | Source | Données | Statut |
|---|---|---|---|
| `navigation.courseRhumbline.nextPoint` | qtVLM | Waypoint actif | ✅ Actif |
| `navigation.courseRhumbline.crossTrackError` | qtVLM | XTE | ✅ Actif |
| `navigation.racing.distanceLayline` | qtVLM (calc) | Distance au layline | ⏳ À configurer |

**Note :** Les données qtVLM reçues par Signal K sont également loggées dans InfluxDB
(bucket: midnight_rider) et peuvent alimenter des panels Grafana ou des alertes OC
(ex: alerte XTE > 0.5nm).

## 9. Intégrations API à construire (software uniquement)

**Ces intégrations ne nécessitent pas de hardware — elles sont à coder.**

| Source | Données | Fréquence | Signal K path cible | Priorité | Status |
|---|---|---|---|---|---|
| **NOAA NDBC** | Vent réel, temp eau, pression, houle (buoys LIS) | 30 min | environment.outside.*, environment.water.temperature | 🔴 Avant race | 🔨 À construire |
| **NDBC Station 44017** | Montauk: vent, pression, houle | 30 min | environment.outside.wind.*, outside.pressure | 🔴 Avant race | 🔨 À construire |
| **NDBC Station 44025** | LIS Central: température eau | 30 min | environment.water.temperature | 🔴 Avant race | 🔨 À construire |
| **NDBC Station BLTM3** | Block Island: météo locale (pendant race) | 10 min | environment.outside.wind.*, pressure | 🔴 Pendant race | 🔨 À construire |

**Architecture NOAA à construire:**
```
[NOAA NDBC API]
  ↓ HTTP GET https://www.ndbc.noaa.gov/data/realtime2/{STATION_ID}.txt
  ↓ Parser Python (regatta/weather_collector.py ou nouveau script)
  ↓ Write InfluxDB directement (bucket: midnight_rider)
  ↓ Measurements: environment.outside.*, environment.water.*
  ↓ Fréquence: cron toutes les 30 min (données buoy ~30 min delay)
  ↓ Signal K: push via REST API ou direct InfluxDB write
```

---

## 9b. Intégrations futures — Matériel (pipeline 2026)

| Intégration | ETA | Signal K path | InfluxDB measurement | Dépendance | Priorité |
|---|---|---|---|---|---|
| **SOK BMS LiFePO4** | ~5 mai 2026 | electrical.batteries.house.* | electrical.batteries.* | Hardware attendu + plugin Signal K | 🔴 Critique |
| **Calypso ULTRASONIC** | TBD | environment.wind.*, navigation.attitude.*, environment.outside.temperature | Complément + backup B&G WS320. Fournit aussi pitch/roll/heading (masthead, 1Hz, moins précis que WIT). Seul capteur de température de l'air. | 🟡 Haute |

> **Note Calypso :** Si connecté, `environment.outside.temperature` devient disponible
> localement (masthead) — n'est plus dépendant de NOAA pour la température de l'air.
> Attitude depuis le Calypso = complément du WIT (source "masthead" vs "hull").
| **AIS Transponder** | TBD (regatta) | vessels.* | vessels.* | Maritime AIS | 🟡 Haute |
| **Victron MPPT** | TBD | electrical.solar.* | electrical.solar.* | Solar panel monitoring | 🟢 Moyenne |

---

## 10. Commandes de diagnostic rapide

```bash
# ✅ Lister tous les measurements actifs
influx query 'import "influxdata/influxdb/schema"
schema.measurements(bucket: "midnight_rider")'

# ✅ Vérifier la fréquence d'écriture (points/min)
influx query 'from(bucket:"midnight_rider") 
  |> range(start:-1m) 
  |> count()'

# ✅ Sample d'un measurement spécifique (SOG example)
influx query 'from(bucket:"midnight_rider") 
  |> range(start:-5m)
  |> filter(fn:(r)=>r._measurement=="navigation.speedOverGround") 
  |> last()'

# ✅ Vérifier la connexion Signal K → InfluxDB
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/speedOverGround

# ✅ Vérifier les logs du plugin signalk-to-influxdb2
docker logs signalk 2>&1 | grep influxdb | tail -20

# ✅ Tester une conversion Flux (rad to degrees)
influx query 'from(bucket:"midnight_rider") 
  |> range(start:-1m)
  |> filter(fn:(r)=>r._measurement=="navigation.attitude.roll") 
  |> map(fn:(r)=>({r with _value: r._value * 57.2958}))
  |> last()'
```

---

## 11. Checklist de maintenance

- [ ] **Hebdo:** Vérifier CPU temp trend (Section 6, alerte >80°C)
- [ ] **Hebdo:** Vérifier InfluxDB disk usage (rétention 30j)
- [ ] **Mensuel:** Valider que tous les measurements du Section 4 ont des données fraîches (<1h old)
- [ ] **Avant chaque course:** Confirmer que COCKPIT dashboard affiche des valeurs en live
- [ ] **Après chaque course:** Exporter logs InfluxDB pour analyse post-race
- [ ] **Mai 19 (Field Test):** Affiner seuils d'alerte (Section 6) avec données réelles
- [ ] **Mai 22 (Race):** Activé monitoring complet, alertes Telegram en live
- [ ] **Juin:** Post-mortem: quelle data a manqué ? Quelle alerte a sauvé la course ?

---

## 12. Historique des révisions

| Date | Auteur | Changement | Sections affectées |
|---|---|---|---|
| 2026-04-28 | OC + Denis | Document initial | Toutes |
| 2026-04-28 | OC + Denis | Clarification statuts, NOAA → À construire, corrections audit | 2, 3, 6, 9, 9b |
| 2026-04-28 v2 | OC | Clarifier statuts (⏳/🔨/❓/❌), ajouter NOAA API section | 1-9 |
| 2026-04-28 v3 | OC + Denis | Architecture NMEA 2000, YDNU-02 interface, multi-sources, Vulcan, qtVLM, calibration | 1, 2, 2b, 2c, 2d, 8b, 9b |
| TBD (mai 2026) | OC | Ajout SOK BMS data | 2, 3, 4, 6 |
| TBD (mai 2026) | OC | Affinage seuils post-field-test | Section 6 |
| TBD (juin 2026) | Denis | Post-mortem course | Toutes |

---

**Ce document est vivant. Mise à jour requise à chaque nouveau capteur ou changement d'architecture.**

**Questions ou corrections ? → Denis Lafarge**

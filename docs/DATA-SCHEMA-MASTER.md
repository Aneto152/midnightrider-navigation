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
[Instruments physiques]
│ NMEA 2000 / BLE / USB
▼
[Signal K] :3000 ──── normalisation, routing, unités SI
│ signalk-to-influxdb2 plugin (1s interval)
▼
[InfluxDB] :8086 ──── time-series, bucket: midnight_rider
│ Flux queries + conversions
▼
[Grafana] :3001 ──── dashboards (9), alertes (69)
│ MCP tools (7 serveurs, 37 outils)
▼
[OC / Claude] ──── intelligence, analyse, coaching
│ Twilio WhatsApp / Telegram
▼
[Denis & Anne-Sophie] ──── Helmsman & Navigator
```

---

## 2. Catalogue des sources de données

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

---

## 3. Signal K paths actifs (réalité du terrain)

Basé sur audit direct du 28 avril 2026.

| Path Signal K | Instrument source | Unité SI | Valeur sample (28 avr) | Fréquence | Status |
|---|---|---|---|---|---|
| navigation.speedOverGround | UM982 | m/s | 3.2 | 1 Hz | ✅ |
| navigation.courseOverGroundTrue | UM982 | radians | 2.2096 | 1 Hz | ✅ |
| navigation.headingTrue | UM982 + WIT | radians | 1.741 | 1 Hz | ❓ À confirmer |
| navigation.position.latitude | UM982 | degrés décimaux | 41.5425 | 1 Hz | ✅ |
| navigation.position.longitude | UM982 | degrés décimaux | -71.4132 | 1 Hz | ✅ |
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
- ✅ **Confirmé dans InfluxDB**: 12 measurements
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
| 🏠 **COCKPIT** (ID: 8) | navigation.speed*, heading*, attitude.*, course* | 5s | 6 | ✅ Actif |
| 🌊 **ENVIRONMENT** (ID: 10) | environment.wind.*, outside.*, water.*, system.cpu* | 30s | ⏳ | ⏳ Non connecté (B&G WS320) |
| ⚡ **PERFORMANCE** (ID: 13) | navigation.speed*, polar, VMG | 5s | ⏳ | ⏳ À vérifier |
| 🌪️ **WIND & CURRENT** (ID: 15) | environment.wind.*, navigation.current* | 10s | ⏳ | ⏳ À vérifier |
| 🏆 **COMPETITIVE** (ID: 16) | AIS, fleet, distance, performance | 30s | ⏳ | ⏳ À vérifier |
| 🔋 **ELECTRICAL** (ID: 17) | electrical.batteries.*, solar.* | 30s | ⏳ | ⏳ Non connecté (SOK BMS) |
| 🏁 **RACE** (ID: 18) | navigation.*, regatta.timer, current* | 5s | ⏳ | ⏳ À vérifier |
| 🔔 **ALERTS** (ID: 19) | tous (event-based) | 10s | ⏳ | ⏳ À vérifier |
| ⚓ **CREW** (ID: 20) | regatta.crew, navigation.speed*, timer | 30s | ⏳ | ⏳ À vérifier |

---

## 8. Vue par serveur MCP

| Serveur MCP | Config | Measurements InfluxDB utilisés | Outils exposés | Status |
|---|---|---|---|---|
| **Astronomical** | mcp/astronomical | N/A (calculs locaux) | sun_position, moon_phase, tides, twilight_times | ✅ Actif |
| **Racing** | mcp/racing | navigation.*, environment.wind.* | heading_accuracy, sog_analysis, vmg, wind_optimization | ✅ Actif |
| **Polar** | mcp/polar | navigation.speed*, wind.* | polar_efficiency, target_speed, performance_delta | ✅ Actif |
| **Crew** | mcp/crew | regatta.crew, navigation.* | watch_rotation, helmsman_status, performance_brief | ⏳ À intégrer |
| **Race Management** | mcp/race_management | regatta.timer, navigation.* | start_timer, mark_distance, layline_calc | ⏳ À intégrer |
| **Weather** | mcp/weather | Open-Meteo HTTP API | forecast_summary, wind_trend, gust_warning | ✅ Actif |
| **Buoy** | mcp/buoy | NOAA HTTP API | real_observations, wind_comparison, pressure_trend | ✅ Actif |

---

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
| **Calypso ULTRASONIC** | TBD | environment.wind.* | environment.wind.* | Replaces B&G WS320 | 🟡 Haute |
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
| TBD (mai 2026) | OC | Ajout SOK BMS data | 2, 3, 4, 6 |
| TBD (mai 2026) | OC | Affinage seuils post-field-test | Section 6 |
| TBD (juin 2026) | Denis | Post-mortem course | Toutes |

---

**Ce document est vivant. Mise à jour requise à chaque nouveau capteur ou changement d'architecture.**

**Questions ou corrections ? → Denis Lafarge**

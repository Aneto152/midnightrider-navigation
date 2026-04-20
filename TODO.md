# 📋 TODO MidnightRider — Roadmap Complète

**Status:** 🎯 En construction (multi-phases)  
**Last Updated:** 2026-04-20 19:01 EDT  
**Owner:** Denis Lafarge

---

## 🚀 PHASE 1 — Immédiate (Foundation Ready)

**Status:** ✅ ~70% COMPLÈTE

### ✅ Déjà Fait
- [x] GPS UM982 dual-antenna configuré (heading TRUE)
- [x] Signal K hub opérationnel
- [x] InfluxDB local (bucket "signalk") actif
- [x] Grafana 3 dashboards créés (prêts à importer)
- [x] 7 MCP servers développés et testés (37 tools)
- [x] Data loggers cron (weather, buoys, astronomical)
- [x] Recovery procedures documentées

### 🔄 À Terminer Immédiatement (< 1 jour)
- [ ] **Importer les 3 Grafana dashboards**
  - Navigation (heading, speed, COG, rate of turn)
  - Race Management (helmsman, sails, start line)
  - Astronomical (sunrise, sunset, moon phase)
  - Status: JSON files créés, prêts à importer
  - Priority: HIGH (live visibility on iPad)

- [ ] **Déployer MCP servers sur Claude/Cursor**
  - Ajouter 7 servers à `~/.config/Claude/claude_desktop_config.json`
  - Redémarrer Claude Desktop
  - Tester avec prompt: "Give me the race picture"
  - Status: All servers tested locally
  - Priority: HIGH (enables AI coaching)

- [ ] **Valider InfluxDB data source dans Grafana**
  - Token InfluxDB: `4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==`
  - URL: `http://localhost:8086`
  - Org: `MidnightRider`
  - Bucket: `signalk`
  - Test: Save & Test button should be green
  - Priority: HIGH (prerequisite for dashboards)

- [ ] **Test MCP tools with live data**
  - Start weather-logger.sh (5 min cycle)
  - Start buoy-logger.sh (5 min cycle)
  - Run astronomical cron (daily)
  - Query MCP tools from Claude: check they return recent data
  - Priority: MEDIUM (validate integration)

---

## 🔧 PHASE 2 — Hardware Integration (1-2 semaines)

**Status:** ⏳ En attente d'instruments

### Loch (Speed Through Water)

**Status:** À tester (modèle à confirmer)

- [ ] **Identifier loch**
  - Obtenir modèle exact (électromagnétique / hélice / autre)
  - Type sortie (NMEA0183 / NMEA2000 / analogique)
  - Port série/NMEA2000
  - Specs: vitesse min/max, précision

- [ ] **Configurer Signal K provider**
  - Ajouter source dans signalk-settings.json
  - Port série ou NMEA2000 device
  - Baudrate / PGN mapping

- [ ] **Calibrage Loch**
  - Calibrage statique: offset au repos
  - Calibrage en route: GPS vs Loch (1nm test)
  - Facteur d'échelle (gain)
  - Polynôme (si non-linéaire)

- [ ] **Réinjection NMEA2000**
  - Plugin output Signal K vers NMEA2000
  - Tester réception sur Vulcan
  - Vérifier précision

- [ ] **Données InfluxDB**
  - `navigation.speedThroughWater` (calibré)
  - `navigation.speedThroughWaterRaw` (debug)
  - `environment.water.temperature` (optionnel)

### Anémomètre + Girouette (Wind Data)

**Status:** À installer

- [ ] **Connecter girouette/anémomètre**
  - Type: YDWG-02 NMEA2000 (supposé)
  - Installer sur mât
  - Brancher sur NMEA2000 bus

- [ ] **Configurer Wind Data dans Signal K**
  - Provider NMEA2000
  - Mapping appWind (relative): angle + speed
  - Mapping trueWind (absolu): calcul TWA, TWS, TWD

- [ ] **Calibrage/Offset**
  - Offset mécanique girouette (orientation 0°)
  - Offset électronique si nécessaire
  - Test en bateau

- [ ] **Données InfluxDB**
  - `environment.wind.angleApparent`
  - `environment.wind.speedApparent`
  - `environment.wind.angleTrue`
  - `environment.wind.speedTrue`
  - `environment.wind.directionTrue`

### Baromètre + Thermomètre (Environment)

**Status:** À installer (optionnel)

- [ ] **Connecter capteurs**
  - Baromètre (NMEA2000 ou capteur USB)
  - Thermomètre eau
  - Hygrométrie (optionnel)

- [ ] **Configurer Signal K**
  - Pressions: `environment.outside.pressure`
  - Température: `environment.water.temperature`, `environment.outside.temperature`
  - Humidité (optionnel)

- [ ] **Données InfluxDB**
  - Pressure trend (alerte baromètrique)
  - Temperature pour alertes météo

### Sondeur/Sondeur (Water Depth)

**Status:** À installer (optionnel mais utile)

- [ ] **Connecter sondeur**
  - Type: Sondeur NMEA2000 ou analogique
  - Installer transducteur
  - Brancher sur Signal K

- [ ] **Données InfluxDB**
  - `environment.water.depth`
  - Alerte: profondeur critique < 4m

### Attitude Sensor (Roll/Pitch) — OPTIONNEL

**Status:** À évaluer (UM982 peut fournir via dual-antenna)

**Note:** UM982 propriétaire sentences (#HEADINGA) **contiennent déjà roll/pitch**

- [ ] **Option A: Parser UM982 propriétaire (RECOMMANDÉ)**
  - Décoder champs 12-14 de #HEADINGA
  - Roll, Pitch, Yaw déjà présents
  - No additional hardware needed!
  - Implémentation: custom Signal K plugin

- [ ] **Option B: Ajouter BNO085 IMU (si UM982 insuffisant)**
  - IMU 9-DoF (gyro + accel + compass)
  - NMEA0183 ou USB serial
  - Meilleure résolution, lower latency
  - Backup si UM982 en perte de signal

**Action:** Test avec UM982 propriétaire d'abord (le data est déjà là!)

---

## 📊 PHASE 3 — Advanced Analytics (2-3 semaines)

**Status:** ⏳ Foundation déjà là, besoin de fine-tuning

### Performance Metrics (VMG, Target Speed, Polaires)

**Status:** MCP tools prêts, besoin de données

- [ ] **B&G Performance Plugin (PGN 130824)**
  - Vérifier plugin signalk-bandg-performance-plugin installé
  - Paths: `performance.targetSpeed`, `performance.targetVMG`, `performance.velocityMadeGoodRatio`
  - Configurer sources Signal K (polaires, conditions actuelles)
  - Test transmission au Vulcan

- [ ] **Polaires Boat (Custom)**
  - Intégrer polaires J/30 officielles
  - Ou calculer à partir données historiques
  - Stockage: fichier JSON ou InfluxDB
  - MCP tool: `current_polar()` retourne TWS/TWA → target speed

- [ ] **Targets & Hints**
  - Pour chaque point de voile:
    - Target speed (polaires)
    - Optimal angle (beating angle, running angle)
    - Heel angle (for performance)
    - VMG ratio

- [ ] **Watchdog Alertes**
  - Alerte si speed < 90% target (mauvaise voilure?)
  - Alerte si heel > seuil optimal (gîte excessive?)
  - Alerte si VMG < 80% best (virer ou empanner?)

### Crew & Race Management

**Status:** Interface régate existe (regatta/), besoin d'amélioration

- [ ] **UI Régate Améliorée (Web/iPad-friendly)**
  - Sélection helmsman (Denis, Anne-Sophie, crew...)
  - Sélection voiles (dropdown: Main 1ris/2ris, Jib1/Jib2, etc.)
  - Timer régate (5min, 4min, 1min, 30s, 10s)
  - Marqueurs ligne de départ (2 points GPS: pin + bateau comité)
  - Événements: virement, empannage, marque, arrivée
  - Tout loggé en temps réel dans InfluxDB

- [ ] **Crew Workload Assessment**
  - Nombre tacks par période
  - Durée moyenne tack
  - Transitions voiles (fréquence, durée)
  - Suggestion: rotation helmsman si fatigue

- [ ] **Start Line Analysis**
  - Longueur ligne (GPS distance pin-boat)
  - Angle ligne vs vent réel (geometry)
  - Bias detection (côté avantage?)
  - Distance/Time to line (live countdown)
  - OCS detection (crossed before gun)

### Alertes Intelligentes

**Status:** Liste complète documentée (memory/2026-04-18-alerts-todo.md), besoin implémentation

#### Meteo Alerts
- [ ] NWS Small Craft Advisory (API: api.weather.gov/alerts)
- [ ] Chute pression > 3hPa/3h (NOAA buoys)
- [ ] Wind gust forecast > seuil (Open-Meteo)
- [ ] Fog/visibility < seuil (METAR)

#### Safety Alerts
- [ ] Lever/coucher soleil + crépuscule nautique (calcul + GPS)
- [ ] Nuit = visibilité réduite (alerte avant dark)
- [ ] Profondeur < 4m (sondeur NMEA2000)
- [ ] Batterie faible (voltage sensor)

#### Race Alerts
- [ ] Timer départ (J-5, J-3, J-1, 30s, 10s)
- [ ] Approche ligne < 0.3nm (10 min avant)
- [ ] Franchissement ligne (OCS si avant gun)
- [ ] Approaching mark (1nm countdown)

#### Performance Alerts
- [ ] Speed < 90% target (4s average)
- [ ] Heel > seuil optimal (+ 2-3°)
- [ ] VMG < 80% best (avant la minute)
- [ ] Rate of turn trop élevé (mauvais angle de virement?)

---

## 🔗 PHASE 4 — Cloud & Remote Access (3-4 semaines)

**Status:** ⏳ Infrastructure en place, config en cours

### InfluxDB Cloud (Hybrid Local + Cloud)

**Status:** Compte Cloud existe (Denis), config à compléter

- [ ] **InfluxDB Cloud Setup**
  - Organisation: Denis's account
  - Bucket: signalk-cloud (ou replicated depuis local?)
  - Token: générer
  - Retention: 30 jours (shorter for bandwidth)

- [ ] **Sync Strategy**
  - Local InfluxDB: détail complet (infinite retention)
  - Cloud InfluxDB: résumé + dashboards (via telegraf ou script)
  - Option: Replicate toutes données vers cloud (si bandwidth ok)

- [ ] **Grafana Cloud**
  - Data source: InfluxDB Cloud
  - Mêmes dashboards (navigation, race, astronomical)
  - Accès public (sans login) pour shore team

### AIS Integration (Ship Tracking)

**Status:** À ajouter (optionnel mais cool)

- [ ] **AIS Receiver**
  - RTLSDRµ dongle (cheap USB receiver)
  - Ou AIS transponder avec output NMEA0183/2000
  - Feed vers Signal K

- [ ] **Competitor Tracking**
  - Parser AIS messages (lat/lon/heading/speed)
  - Store in InfluxDB
  - Grafana map: show other boats
  - MCP tool: `competitor_data()` (distance, bearing, speed relative)

### Shore Team Dashboard

**Status:** À concevoir

- [ ] **Public Cloud Dashboard**
  - Real-time position (map)
  - Speed, heading, wind
  - Race state (if applicable)
  - No login required
  - Update frequency: 30-60s (balance bandwidth vs latency)

- [ ] **Extended Analytics**
  - Historical performance trends
  - Polaire comparison vs target
  - Crew statistics
  - Race history & results

---

## 🎯 PHASE 5 — ML & Coaching (4-6 semaines)

**Status:** 🚀 Foundation ready (MCP tools 70% done)

### AI Coaching (Claude/Cursor Integration)

**Status:** MCP servers created, deployment in progress

- [ ] **Deploy 7 MCP Servers to User**
  - Add to `~/.config/Claude/claude_desktop_config.json`
  - All 7 servers: Astronomical, Racing, Polar, Crew, Race Management, Weather, Buoy
  - Test prompts:
    - "Give me the race picture" (synthesizes all data)
    - "What's my VMG performance?" (polaires + current)
    - "Should I tack now?" (tactics)
    - "When's sunset?" (astronomical + safety)

- [ ] **Coaching Prompts**
  - System prompt: "You are a J/30 sailing coach"
  - Context: realtime data from 7 MCP tools
  - Output: Narrative analysis + recommendations
  - Examples:
    - "You're at 6.5 knots. Target is 7.2 knots (polaires TWS 12 kt). Heel is high (18°). Suggest: depower main 1 ris or change jib."
    - "You're approaching mark in 8 minutes. Current heading 045°. Wind from 090°. Recommend starboard approach via layline."

### Personalized Helmsman Profiles

**Status:** Data collection ready (crewing metrics)

- [ ] **Helmsman Stats**
  - Number of tacks/hour
  - Average tack duration
  - Heel stability (std dev)
  - Speed consistency (std dev)
  - Guess: Denis likes aggressive short tacks, Anne-Sophie prefers stable smooth turns

- [ ] **Coaching Recommendations**
  - Suggest helmsman rotation based on conditions (light air = smooth helmsman)
  - Praise good technique or flag issues
  - Learn preferences over time

### ML Models (Optional, Future)

**Status:** ⏳ Data needed to train

- [ ] **Speed Prediction Model**
  - Input: TWS, TWA, heel, sails
  - Output: predicted VMG
  - Compare vs actual → reveals efficiency gaps
  - Retrain weekly with recent data

- [ ] **Tack Decision Model**
  - Input: current heading, wind, target, polaires
  - Output: optimal time to tack
  - Evaluate: did we improve VMG?

- [ ] **Start Predictor**
  - Input: line length, wind, boat position, time to gun
  - Output: optimal start strategy (which end, when to cross)

---

## 🐛 PHASE 6 — Polish & Robustness (Ongoing)

**Status:** Good foundation, incremental improvements

### Monitoring & Alerts

- [ ] **System Health Dashboard**
  - Signal K uptime
  - InfluxDB disk usage
  - Data freshness (latest timestamp)
  - Network connectivity
  - Battery level (if applicable)

- [ ] **Data Quality Checks**
  - Detect missing measurements
  - Outlier detection (unrealistic values)
  - Sensor failure detection
  - Auto-recovery procedures

### Documentation

- [ ] **User Manual (French)**
  - iPad usage guide
  - Dashboard interpretation
  - Emergency procedures
  - Troubleshooting

- [ ] **Technical Docs**
  - System architecture
  - Data schema (Signal K paths)
  - Plugin list & versions
  - Recovery procedures (update existing)

- [ ] **API Reference**
  - MCP tool specification (all 37 tools)
  - Query examples (Flux for InfluxDB)
  - Integration guide (external systems)

### Testing & Validation

- [ ] **On-Water Testing**
  - Test all 7 MCP tools with live data
  - Validate Grafana dashboards (readability, refresh rate)
  - Test alerts (no false positives!)
  - Helmsman feedback & adjustments

- [ ] **Disaster Recovery Drills**
  - Simulate SD card failure → restore from GitHub
  - Simulate InfluxDB data loss → recovery procedure
  - Simulate network loss → offline mode
  - Time to recovery < 1 hour

---

## 📋 By Category

### 🏁 Racing Features

| Feature | Status | Priority | Phase |
|---------|--------|----------|-------|
| Helmsman tracking | ✅ Done | HIGH | 1 |
| Sail tracking | ✅ Done | HIGH | 1 |
| Start line marking | ⏳ UI needs work | HIGH | 2 |
| Timer (5-1-30s-10s) | 🔄 Half done | HIGH | 2 |
| OCS detection | ⏳ Todo | MEDIUM | 3 |
| Mark approach alerts | ⏳ Todo | MEDIUM | 3 |
| Crew workload | ⏳ Todo | MEDIUM | 3 |
| Performance metrics | 🔄 Tools ready | HIGH | 3 |

### 🌬️ Wind & Weather

| Feature | Status | Priority | Phase |
|---------|--------|----------|-------|
| Wind data (appWind) | ⏳ Hardware | HIGH | 2 |
| True wind calc | ⏳ Hardware | HIGH | 2 |
| Weather forecast | ✅ Done (MCP) | MEDIUM | 1 |
| NOAA buoys | ✅ Done (MCP) | MEDIUM | 1 |
| Gale warnings | ⏳ Alerts | MEDIUM | 3 |
| Pressure trend | ⏳ Barometer | LOW | 2 |

### 🚤 Navigation

| Feature | Status | Priority | Phase |
|---------|--------|----------|-------|
| True heading (UM982) | ✅ Done | HIGH | 1 |
| Speed over ground (GPS) | ✅ Done | HIGH | 1 |
| Course over ground | ✅ Done | MEDIUM | 1 |
| Speed through water | ⏳ Loch | HIGH | 2 |
| Water depth | ⏳ Sounder | MEDIUM | 2 |
| Current calculation | 🔄 Formula ready | MEDIUM | 3 |
| Rate of turn | ✅ Done | LOW | 1 |

### 📊 Visualization

| Feature | Status | Priority | Phase |
|---------|--------|----------|-------|
| Navigation dashboard | ✅ Done | HIGH | 1 |
| Race dashboard | ✅ Done | HIGH | 1 |
| Astronomical dashboard | ✅ Done | MEDIUM | 1 |
| Performance dashboard | ⏳ Todo | MEDIUM | 3 |
| GNSS quality dashboard | ⏳ Todo | LOW | 3 |
| Map widget | ✅ Done | HIGH | 1 |
| Real-time updates | ✅ Done (10s) | HIGH | 1 |

### 🤖 AI Coaching

| Feature | Status | Priority | Phase |
|---------|--------|----------|-------|
| 7 MCP servers | ✅ Done | HIGH | 1 |
| Deploy to Claude | 🔄 In progress | HIGH | 1 |
| Race picture synthesis | ✅ Ready | HIGH | 1 |
| VMG coaching | ✅ Tools ready | MEDIUM | 1 |
| Tactic recommendations | ⏳ Prompt design | MEDIUM | 5 |
| Helmsman profiles | ⏳ Data collection | LOW | 5 |
| ML models | ⏳ Future | LOW | 5 |

---

## 🎯 Quick Wins (Next 48h)

Low effort, high impact:

1. ✅ Import 3 Grafana dashboards (~15 min)
2. ✅ Verify InfluxDB data source in Grafana (~10 min)
3. ✅ Deploy MCP servers to Claude config (~20 min)
4. ✅ Test "Give me the race picture" prompt (~5 min)
5. ⏳ Start data loggers (weather, buoys) (~10 min)
6. ⏳ Commit everything to GitHub (~5 min)

**Total time: ~1 hour**

---

## 🚧 Blockers

| Blocker | Impact | Solution |
|---------|--------|----------|
| Loch hardware | No STW speed | Install & calibrate |
| Anémomètre | No wind data | Install YDWG-02 |
| InfluxDB cloud auth | Cloud sync | Complete cloud setup |
| AIS receiver | No competitor tracking | Buy RTLSDRµ |
| BNO085 IMU | Low-res attitude | Try UM982 proprietary first |

---

## 📅 Estimated Timeline

- **Phase 1 (Done):** ✅ ~70% done, ~1-2 days to finish
- **Phase 2 (Hardware):** ⏳ 1-2 weeks (depends on parts arrival)
- **Phase 3 (Analytics):** ⏳ 2-3 weeks (data-dependent)
- **Phase 4 (Cloud):** ⏳ 3-4 weeks (lower priority)
- **Phase 5 (ML):** ⏳ 4-6 weeks (nice to have)
- **Phase 6 (Polish):** 🔄 Ongoing

**Total for full system:** ~8-12 weeks (with hardware delays factored in)

---

## 💾 Success Criteria

- [x] System boots & runs reliably (24h+ uptime)
- [x] All sensors streaming data → InfluxDB
- [x] Grafana dashboards showing live data
- [x] iPad WiFi access working
- [ ] MCP tools deployed & tested with real data
- [ ] All alertes working (no false positives)
- [ ] Recovery < 1 hour (after any failure)
- [ ] Shore team can see boat position + stats
- [ ] Coaching prompts generate useful recommendations

---

## 🎬 Action Items (Immediate)

**Today (2026-04-20):**
1. [ ] Import 3 Grafana dashboards
2. [ ] Deploy MCP servers to Claude
3. [ ] Test Claude prompts with live data
4. [ ] Verify InfluxDB data source

**This Week:**
1. [ ] Test on boat (WiFi connectivity)
2. [ ] Gather feedback (helmsman, crew)
3. [ ] Fine-tune alert thresholds
4. [ ] Document any issues

**Next Week:**
1. [ ] Plan hardware installation (loch, wind)
2. [ ] Order missing parts
3. [ ] Prepare installation guides
4. [ ] Schedule on-water testing

---

**Status Dashboard:**
```
Foundation (Phase 1):     ✅✅✅✅✅ 90%
Hardware (Phase 2):       🔄🔄⏳⏳⏳ 30%
Analytics (Phase 3):      🔄🔄⏳⏳⏳ 30%
Cloud/Remote (Phase 4):   ⏳⏳⏳⏳⏳  0%
ML/Coaching (Phase 5):    ✅⏳⏳⏳⏳ 20%
Polish (Phase 6):         🔄⏳⏳⏳⏳ 20%
```

Overall: **40% Complete**, Momentum: **📈 High** 🚀

# 🚨 Alertes MidnightRider — Spécification Complète (2026-04-18)

## Statut

**EN ATTENTE:** Instruments (YDWG-02 + girouette + loch + BNO085)

Actuellement possible:
- ✅ Alertes Niveau 1 (sources publiques: NOAA, NWS, calculs astro)
- ⏳ Alertes Niveau 2 (quand SignalK TWS/TWA/gîte disponibles)
- ⏳ Alertes Niveau 3 (nécessite développement spécifique + AIS)

---

## Niveau 1 — Faisable maintenant (sources publiques)

| ID | Nom | Source | Status |
|---|---|---|---|
| METEO-02 | Alerte NWS (SCA/Gale) | api.weather.gov/alerts | ⏳ |
| METEO-03 | Chute pression > 3hPa/3h | NOAA buoys (déjà collecté) | ⏳ |
| CURR-08 | Profondeur critique < 4m | Sondeur NMEA2000 | ⏳ Sondeur manquant |
| RACE-01 | Timer départ (J-5/3/1/30s/10s) | Timer manuel (interface régate) | ⏳ |
| RACE-02 | Approche ligne < 0.3nm / < 5min | GPS + ligne marquée | ⏳ |
| RACE-03 | Franchissement ligne / OCS | GPS + ligne marquée | ⏳ |
| ENV-01 | Lever soleil + crépuscule nautique | Calcul astro + GPS | ⏳ |
| ENV-02 | Coucher soleil + activation feux | Calcul astro + GPS | ⏳ |
| ENV-03 | Lever lune (phase + luminosité) | Calcul astro + GPS | ⏳ |
| ENV-04 | Coucher lune (obscurité totale) | Calcul astro + GPS | ⏳ |
| ENV-07 | Pleine mer / basse mer | NOAA tidal predictions | ⏳ |
| ENV-08 | Étale points clés (30 min avant) | NOAA tidal predictions | ⏳ |

---

## Niveau 2 — Quand instruments connectés

**Dépend de:** SignalK TWS/TWA/STW/gîte (girouette, anémomètre, BNO085)

### Perf

| ID | Nom | Trigger | Source |
|---|---|---|---|
| PERF-01 | VMG < 85% polaire | SignalK vs ORC polaire | ⏳ |
| PERF-02 | VMG > 105% polaire | SignalK vs ORC polaire | ⏳ |
| PERF-03 | Angle au vent sous-optimal ±5° | SignalK TWA + polaire | ⏳ |
| PERF-04 | Sur-gîte > 25° pendant 2min | BNO085 roll | ⏳ |
| PERF-05 | Sous-gîte < 8° au près > 12kt | BNO085 + SignalK | ⏳ |
| PERF-06 | Gîte oscillante std > 5°/2min | BNO085 roll variance | ⏳ |
| PERF-07 | Variation courant force > 0.5kt/5min | SOG + STW vecteur | ⏳ |
| PERF-08 | Variation courant direction > 20°/5min | SOG + STW vecteur | ⏳ |
| PERF-09 | Instabilité barreur TWA std > 5°/10min | SignalK TWA variance | ⏳ |
| PERF-10 | Dérive cap moyen > 5°/20min | SignalK TWA glissante | ⏳ |
| PERF-11 | Dégradation progressive barre | InfluxDB historique PERF-09 | ⏳ |
| PERF-12 | Changement barreur recommandé | Timer quart + PERF-09/10 | ⏳ |

### Wind Shifts

| ID | Nom | Trigger | Source |
|---|---|---|---|
| SHIFT-01 | Lift — bascule favorable > 8°/3min | SignalK TWD dérivée | ⏳ |
| SHIFT-02 | Header — bascule défavorable > 8°/3min | SignalK TWD dérivée | ⏳ |
| SHIFT-03 | Bascule persistante > 20°/30min | SignalK TWD glissante | ⏳ |
| SHIFT-05 | Bascule géographique bouée vs bord | NOAA buoy + SignalK | ⏳ |

### Sail Management

| ID | Nom | Trigger | Source |
|---|---|---|---|
| SAIL-01 | Changement config recommandé | SignalK TWS+TWA+polaire | ⏳ |
| SAIL-02 | Réduction préventive (vent monte) | SignalK TWS dérivée + HRRR | ⏳ |
| SAIL-03 | Opportunité augmenter toile | SignalK TWS dérivée + BNO085 | ⏳ |
| SAIL-04 | Spi possible (TWA > 120°, TWS < 18kt) | SignalK TWA+TWS+BNO085 | ⏳ |
| SAIL-05 | Affaler spi préventif rafale imminente | SignalK TWS + HRRR | ⏳ |
| SAIL-06 | Correction mer agitée — réduire | BNO085 pitch/roll | ⏳ |
| SAIL-07 | Config optimale confirmée > 95% polaire | SignalK + BNO085 + polaire | ⏳ |

### Racing

| ID | Nom | Trigger | Source |
|---|---|---|---|
| RACE-04 | Layline tribord atteinte | SignalK + TWA + courant + marque | ⏳ |
| RACE-05 | Layline bâbord atteinte | SignalK + TWA + courant + marque | ⏳ |

### Currents

| ID | Nom | Trigger | Source |
|---|---|---|---|
| CURR-07 | Changement profondeur > 3m/5min | Sondeur NMEA2000 | ⏳ |

---

## Niveau 3 — Développement spécifique + AIS

| ID | Nom | Complexité | Status |
|---|---|---|---|
| METEO-01 | Divergence modèles météo | Open-Meteo multi-modèles | ⏳ |
| METEO-05 | Risque brouillard | NWS marine forecast parsing | ⏳ |
| METEO-06 | Cisaillement géographique vent | Réseau bouées NOAA | ⏳ |
| METEO-07 | Rafale imminente HRRR < 15min | HRRR nowcast API | ⏳ |
| AIS-01 | Concurrent corrigé ORC nous dépasse | AIS + YachtScoring ratings | ⏳ |
| AIS-02 | Divergence tactique concurrent proche | AIS cap + position | ⏳ |
| AIS-03 | Classement corrigé toute flotte | AIS + ratings ORC | ⏳ |
| AIS-04 | Concurrent franchit waypoint clé | AIS + géofencing | ⏳ |
| AIS-06 | Concurrent surperforme + position rel. | AIS + ratings ORC | ⏳ |
| AIS-07 | Groupement flotte sur un bord | AIS clustering | ⏳ |
| AIS-08 | Changement d'armure concurrent | COG change > 45°/3min | ⏳ |
| AIS-09 | Accélération soudaine concurrent | SOG +0.8kt/5min dans vent stable | ⏳ |
| AIS-10 | Décélération soudaine concurrent | SOG -0.8kt/5min | ⏳ |
| AIS-11 | Concurrent change de bord | Passage CT↔LI détecté | ⏳ |
| SHIFT-04 | Schéma oscillant (FFT sur TWD 2h) | InfluxDB FFT | ⏳ |
| SHIFT-06 | Bascule prévue HRRR dans 30-60min | HRRR grille temporelle | ⏳ |
| CURR-03 | Timing Plum Gut (étale 60/30/15min) | NOAA tidal predictions | ⏳ |
| CURR-06 | Courant NYOFS adverse > 1kt | NYOFS NetCDF | ⏳ |
| ENV-05 | Passage nuageux (perte brise thermique) | HRRR cloud cover | ⏳ |
| ENV-06 | Ciel dégagé nuit (brise de terre) | HRRR cloud cover | ⏳ |
| ENV-10 | Crépuscule nautique (première lumière) | Calcul astro + GPS | ⏳ |
| RACE-06 | Approche marque 1nm/0.5nm/0.2nm | GPS + waypoints BIR | ⏳ |
| RACE-07 | Gain place classement corrigé | AIS + ratings + calcul | ⏳ |
| RACE-08 | Perte place classement corrigé | AIS + ratings + calcul | ⏳ |
| RACE-09 | Dépassement physique par concurrent | AIS positions séquentielles | ⏳ |

---

## Architecture MCP (Mode de Communication)

### Outils envisagés
```python
influxdb_query(measurement, range, filters)  # Requête temps réel
fleet_status(radius_nm)                       # État flotte AIS + VMG corrigé
weather_lis_now()                             # Relevés bouées + résumé CT/LI
alerts_active()                               # Liste alertes firing
boat_performance(minutes)                     # VMG, gîte, TWA vs polaire
tidal_windows(hours_ahead)                    # Étales et courants prévus
race_context()                                # Timer, distance, marques, classement
```

**Usage:** Agent de décision contextualise les alertes et formule recommandations tactiques en temps réel sur Telegram.

---

## Paramètres Technique AIS

### Dérivées robustes
- Agréger AIS sur fenêtres **2min** (lisse bruit)
- Dérivée robuste sur **5min** (évite pics)
- **COG:** différence angulaire circulaire (évite saut 359→1°)

### Seuils de détection

| Alerte | Signal | Fenêtre | Seuil |
|---|---|---|---|
| AIS-08 armure | ΔCOGcirculaire | 3 min | > 45° |
| AIS-09 accélération | ΔSOG moyenne glissante | 5 min | > 0.8 kt |
| AIS-10 décélération | ΔSOG moyenne glissante | 5 min | < -0.8 kt |
| AIS-11 changement bord | Position vs axe parcours | 10 min | > 0.2nm latéral |

### Filtre contextuel pour AIS-09/10

Croiser avec vent local (bouée plus proche):
- **Accélération + rafale simultanée** → pas d'alerte (normal, tout le monde accélère)
- **Accélération + vent stable** → alerte tactique (significatif, concurrent tactique)
- **Décélération + bon vent** → alerte (problème concurrent ou manœuvre)

---

## Next Steps

### Avant prochaine régate
1. [ ] Instruments branchés (girouette, loch, BNO085)
2. [ ] SignalK configure avec tous les providers
3. [ ] Niveau 1 + Niveau 2 alertes codées + testées
4. [ ] AIS integré
5. [ ] Interface Grafana avec alarmes

### Post-régate
- [ ] Analyser alertes firing réelles
- [ ] Affiner seuils
- [ ] Ajouter Niveau 3 progressivement

---

**Last updated:** 2026-04-18 (Denis)  
**Maintained in:** `/home/aneto/docker/signalk/docs/memory/ALERTES.md`

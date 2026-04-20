# 📋 LISTE COMPLÈTE DES 60+ ALERTES MIDNIGHTRIDER

**Status:** Spécifications documentées | Phase 1-3  
**Date:** 2026-04-18 / 2026-04-20  
**Owner:** Denis Lafarge

---

## 📊 RÉSUMÉ STATISTIQUE

```
TOTAL: 60+ alertes
├─ NIVEAU 1 (Faisable maintenant): 12 alertes
├─ NIVEAU 2 (Instruments connectés): 16 alertes  
└─ NIVEAU 3 (Développement spécifique): 21 + 4 alertes AIS

Par Catégorie:
├─ METEO:  7 alertes
├─ PERF:  12 alertes
├─ SHIFT:  4 alertes
├─ SAIL:   7 alertes
├─ RACE:   6 alertes
├─ CURR:   3 alertes
├─ ENV:    5 alertes
└─ AIS:   11 alertes + 4 veille concurrentielle
```

---

## NIVEAU 1 — FAISABLE MAINTENANT ✅ (12 alertes)

**Sources publiques, aucun hardware supplémentaire requis**

### METEO (1)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| METEO-02 | Alerte NWS (SCA/Gale) | SCA/Gale bulletin | api.weather.gov/alerts | ⚠️ WARNING |
| METEO-03 | Chute pression > 3hPa/3h | Δ pression > 3 hPa en 3h | NOAA buoys (collecté) | ⚠️ WARNING |

### ENV (5)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| ENV-01 | Lever soleil + crépuscule nautique | Time = sunrise/twilight | Calcul astro + GPS | ℹ️ INFO |
| ENV-02 | Coucher soleil + activation feux | Time = sunset | Calcul astro + GPS | 🔴 CRITICAL |
| ENV-03 | Lever lune (phase + luminosité) | Time = moonrise | Calcul astro + GPS | ℹ️ INFO |
| ENV-04 | Coucher lune (obscurité totale) | Time = moonset | Calcul astro + GPS | ℹ️ INFO |
| ENV-07 | Pleine mer / basse mer | Time = slack water | NOAA tidal API | ℹ️ INFO |
| ENV-08 | Étale points clés (30 min avant) | Δ time = 30 min before slack | NOAA tidal API | ℹ️ INFO |

### RACE (3)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| RACE-01 | Timer départ (J-5/3/1/30s/10s) | Time countdown | Manuel (interface régate) | 🔴 CRITICAL |
| RACE-02 | Approche ligne < 0.3nm / < 5min | Distance < 0.3nm | GPS + start_line | ⚠️ WARNING |
| RACE-03 | Franchissement ligne / OCS | Position crosses line avant gun | GPS + line vector | 🔴 CRITICAL |

### CURR (1)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| CURR-08 | Profondeur critique < 4m | Depth < 4m | Sondeur NMEA2000 | 🔴 CRITICAL |

---

## NIVEAU 2 — QUAND INSTRUMENTS CONNECTÉS ⏳ (16 alertes)

**SignalK TWS/TWA/STW + BNO085 + Sondeur NMEA2000**

### METEO (1)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| METEO-04 | Vent mesuré ≠ prévu | |TWS - forecast| > 3 kt | NOAA buoy + HRRR | ⚠️ WARNING |

### PERF (12)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| PERF-01 | VMG < 85% polaire | VMG_actual / VMG_target < 0.85 | SignalK + polaire | ⚠️ WARNING |
| PERF-02 | VMG > 105% polaire | VMG_actual / VMG_target > 1.05 | SignalK + polaire | ℹ️ INFO |
| PERF-03 | Angle au vent sous-optimal ±5° | \|TWA - optimal_TWA\| > 5° | SignalK TWA + polaire | ⚠️ WARNING |
| PERF-04 | Sur-gîte > 25° pendant 2min | Heel > 25° pour > 2min | BNO085 | ⚠️ WARNING |
| PERF-05 | Sous-gîte < 8° au près > 12kt | Heel < 8° && TWS > 12 && TWA < 60° | BNO085 + SignalK | ⚠️ WARNING |
| PERF-06 | Gîte oscillante std > 5°/2min | StdDev(Heel) > 5° en 2min | BNO085 | ⚠️ WARNING |
| PERF-07 | Variation courant force > 0.5kt/5min | \|Current_magnitude\| change > 0.5kt | SOG + STW vecteur | ⚠️ WARNING |
| PERF-08 | Variation courant direction > 20°/5min | \|Current_direction\| change > 20° | SOG + STW vecteur | ⚠️ WARNING |
| PERF-09 | Instabilité barreur (TWA std > 5°/10min) | StdDev(TWA) > 5° en 10min | SignalK TWA | ⚠️ WARNING |
| PERF-10 | Dérive cap moyen > 5°/20min | \|mean_TWA - target_TWA\| > 5° | SignalK TWA glissante | ⚠️ WARNING |
| PERF-11 | Dégradation progressive barre | Trend(PERF-09) > 2°/10min | InfluxDB historique | ⚠️ WARNING |
| PERF-12 | Changement barreur recommandé | PERF-09 > 7° && Duration > 5min | Timer quart + PERF-09/10 | ℹ️ INFO |

### SHIFT (3)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| SHIFT-01 | Lift — bascule favorable > 8°/3min | TWD > 8° en 3min && helping tack | SignalK TWD dérivée | ℹ️ INFO |
| SHIFT-02 | Header — bascule défavorable > 8°/3min | TWD < -8° en 3min && hurting tack | SignalK TWD dérivée | ⚠️ WARNING |
| SHIFT-03 | Bascule persistante > 20°/30min | Persistent direction > 20° | SignalK TWD glissante | ℹ️ INFO |
| SHIFT-05 | Bascule géographique bouée vs bord | TWD(buoy) - TWD(boat) > 15° | NOAA buoy + SignalK | ℹ️ INFO |

### SAIL (7)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| SAIL-01 | Changement config recommandé | Optimal_sails ≠ current_sails | SignalK TWS+TWA+polaire | ⚠️ WARNING |
| SAIL-02 | Réduction préventive (vent monte) | TWS trend > 1 kt/min && > threshold | SignalK TWS dérivée + HRRR | ⚠️ WARNING |
| SAIL-03 | Opportunité augmenter toile | TWS trend < -0.5 kt/min && stable | SignalK TWS dérivée + BNO085 | ℹ️ INFO |
| SAIL-04 | Spi possible | TWA > 120° && TWS < 18kt && Heel < 15° | SignalK TWA+TWS+BNO085 | ℹ️ INFO |
| SAIL-05 | Affaler spi préventif (rafale) | Gust forecast > 18kt dans < 10min | SignalK TWS + HRRR | ⚠️ WARNING |
| SAIL-06 | Correction mer agitée — réduire | Pitch > 10° || Roll > 25° persistant | BNO085 pitch/roll | ⚠️ WARNING |
| SAIL-07 | Config optimale confirmée > 95% polaire | VMG_ratio > 0.95 pour > 5min | SignalK + BNO085 + polaire | ℹ️ INFO |

### RACE (1)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| RACE-04 | Layline tribord atteinte | Position on layline || perpendicular | SignalK + TWA + courant + marque | ℹ️ INFO |
| RACE-05 | Layline bâbord atteinte | Position on layline || perpendicular | SignalK + TWA + courant + marque | ℹ️ INFO |

### CURR (1)
| ID | Nom | Trigger | Source | Sévérité |
|----|-----|---------|--------|----------|
| CURR-07 | Changement profondeur > 3m/5min | \|Depth_change\| > 3m en 5min | Sondeur NMEA2000 | ⚠️ WARNING |

---

## NIVEAU 3 — DÉVELOPPEMENT SPÉCIFIQUE REQUIS 🚀 (25 alertes)

**Nécessite intégration API avancée ou ML**

### METEO (4)
| ID | Nom | Complexité | Source |
|----|-----|-----------|--------|
| METEO-01 | Divergence modèles météo | ⭐⭐⭐ | Open-Meteo multi-modèles |
| METEO-05 | Risque brouillard | ⭐⭐⭐ | NWS marine forecast parsing |
| METEO-06 | Cisaillement géographique vent | ⭐⭐⭐ | Réseau bouées NOAA |
| METEO-07 | Rafale imminente HRRR < 15min | ⭐⭐⭐ | HRRR nowcast API |

### SHIFT (2)
| ID | Nom | Complexité | Source |
|----|-----|-----------|--------|
| SHIFT-04 | Schéma oscillant (FFT sur TWD 2h) | ⭐⭐⭐⭐ | InfluxDB FFT |
| SHIFT-06 | Bascule prévue HRRR dans 30-60min | ⭐⭐⭐ | HRRR grille temporelle |

### CURR (2)
| ID | Nom | Complexité | Source |
|----|-----|-----------|--------|
| CURR-03 | Timing Plum Gut (étale 60/30/15min) | ⭐⭐⭐ | NOAA tidal predictions |
| CURR-06 | Courant NYOFS adverse > 1kt | ⭐⭐⭐⭐ | NYOFS NetCDF |

### ENV (2)
| ID | Nom | Complexité | Source |
|----|-----|-----------|--------|
| ENV-05 | Passage nuageux (perte brise thermique) | ⭐⭐⭐ | HRRR cloud cover |
| ENV-06 | Ciel dégagé nuit (brise de terre) | ⭐⭐⭐ | HRRR cloud cover |
| ENV-10 | Crépuscule nautique (première lumière) | ⭐⭐ | Calcul astro + GPS |

### RACE (3)
| ID | Nom | Complexité | Source |
|----|-----|-----------|--------|
| RACE-06 | Approche marque 1nm/0.5nm/0.2nm | ⭐⭐ | GPS + waypoints BIR |
| RACE-07 | Gain place classement corrigé | ⭐⭐⭐ | AIS + ratings + calcul |
| RACE-08 | Perte place classement corrigé | ⭐⭐⭐ | AIS + ratings + calcul |
| RACE-09 | Dépassement physique par concurrent | ⭐⭐ | AIS positions séquentielles |

### AIS (11)
| ID | Nom | Complexité | Source |
|----|-----|-----------|--------|
| AIS-01 | Concurrent corrigé ORC nous dépasse | ⭐⭐⭐ | AIS + YachtScoring ratings |
| AIS-02 | Divergence tactique concurrent proche | ⭐⭐⭐ | AIS cap + position |
| AIS-03 | Classement corrigé toute flotte | ⭐⭐⭐ | AIS + ratings ORC |
| AIS-04 | Concurrent franchit waypoint clé | ⭐⭐ | AIS + géofencing |
| AIS-06 | Concurrent surperforme + position rel. | ⭐⭐⭐ | AIS + ratings ORC |
| AIS-07 | Groupement flotte sur un bord | ⭐⭐ | AIS clustering |
| AIS-08 | Changement d'armure concurrent | ⭐⭐ | AIS COG change > 45° en 3min |
| AIS-09 | Accélération soudaine concurrent | ⭐⭐ | AIS SOG +0.8kt en 5min |
| AIS-10 | Décélération soudaine concurrent | ⭐⭐ | AIS SOG -0.8kt en 5min |
| AIS-11 | Concurrent change de bord | ⭐⭐ | AIS position vs axis |

---

## 📈 IMPLÉMENTATION PAR PHASE

### ✅ PHASE 1 (Immédiate — 12 alertes)

```
METEO:    2 alertes
├─ NWS SCA/Gale
└─ Pressure drop > 3 hPa/3h

ENV:      6 alertes
├─ Sunrise/sunset/twilight times
├─ Moonrise/moonset times
├─ Slack water times
└─ 30 min avant slack water

RACE:     3 alertes
├─ Start timer (countdown)
├─ Distance to line < 0.3nm
└─ OCS detection

CURR:     1 alerte
└─ Depth critical < 4m
```

**Timeline:** Cette semaine (15 min setup)  
**Dépendances:** Aucune  
**Status:** ✅ Prêt

---

### ⏳ PHASE 2 (Quand hardware — 16 alertes)

```
Dépend de:
├─ YDWG-02 (Wind data: TWS, TWA, TWD)
├─ BNO085 (Heel, pitch, roll) ou UM982 propriétaire
└─ Sondeur (Depth)

Alertes possibles:
├─ METEO: 1 (wind mismatch)
├─ PERF: 12 (VMG, heel, angle, stability)
├─ SHIFT: 4 (wind shifts)
├─ SAIL: 7 (sail config changes)
└─ RACE: 2 (laylines)
```

**Timeline:** 2-3 semaines (après hardware install)  
**Dépendances:** YDWG-02, BNO085/UM982 propriétaire, sondeur  
**Complexité:** Moyenne (implémentation Signal K + Grafana)

---

### 🚀 PHASE 3 (Avancé — 25 alertes)

```
Dépend de:
├─ HRRR API (weather nowcasting)
├─ NYOFS NetCDF (current forecasting)
├─ AIS integration (fleet tracking)
├─ ML models (pattern recognition)
└─ Advanced FFT analysis

Alertes possibles:
├─ METEO: 4 (divergence, fog, shear, gust)
├─ SHIFT: 2 (oscillation patterns, forecast)
├─ CURR: 2 (Plum Gut timing, NYOFS)
├─ ENV: 3 (cloud passage, clear sky, twilight)
├─ RACE: 4 (mark approach, classement, overtake)
└─ AIS: 10 (fleet tracking, tactics)
```

**Timeline:** 4-8 semaines (après Phase 1+2)  
**Dépendances:** APIs externes, AIS, ML  
**Complexité:** Haute (développement custom)

---

## 🔑 CLÉS POUR CHAQUE ALERTE

### Sources de Données Requises

```
PublicAPIs:
├─ NOAA (pressure, tidal, buoys)
├─ NWS (alerts, forecasts)
├─ Open-Meteo (weather)
└─ HRRR (nowcast, advanced)

SignalK (onboard):
├─ GPS (position, SOG, COG)
├─ Wind (TWS, TWA, TWD) [YDWG-02 needed]
├─ Attitude (heel, pitch, roll) [BNO085/UM982]
├─ Depth (sondeur) [NMEA2000]
└─ Calculated (VMG, current, etc.)

AIS:
├─ Competitor positions
├─ COG/SOG
└─ Calculated metrics (distance, relative speed)

Calculations:
├─ Polaire matching (TWS/TWA → target speed)
├─ Layline geometry (position, target, wind)
├─ Current vectors (SOG - STW)
└─ Trend analysis (derivatives, FFT)
```

---

## 🎯 RÉSUMÉ POUR TABLEAU DE BORD

```
ACTUELLEMENT DISPONIBLES (Phase 1): 12 alertes
├─ 2 METEO
├─ 6 ENV
├─ 3 RACE
└─ 1 CURR

À AJOUTER (Phase 2): 16 alertes
├─ 1 METEO
├─ 12 PERF
├─ 3 SHIFT
├─ 7 SAIL
├─ 1 RACE
└─ 1 CURR

FUTURE (Phase 3): 25+ alertes
├─ 4 METEO
├─ 2 SHIFT
├─ 2 CURR
├─ 3 ENV
├─ 4 RACE
└─ 10 AIS
```

---

**Status:** ✅ Documentation complète  
**Déployé:** ✅ Phase 1 (8 alertes Grafana sélectionnées)  
**Prêt Phase 2:** ⏳ En attente hardware (YDWG-02, BNO085)  
**Prêt Phase 3:** 🚀 Planifié (4-8 semaines)

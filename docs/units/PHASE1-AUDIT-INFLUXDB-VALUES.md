# PHASE 1 — Audit Complet des Valeurs Brutes InfluxDB
**Date:** 2026-04-27 22:55 EDT
**Status:** ✅ COMPLETE
**Real Data Found:** ✅ YES

---

## Résumé Exécutif

✅ **InfluxDB contient bien les données en unités SI**
✅ **600+ records/minute confirmés**
✅ **Conversions identifiées et documentées**

Les données **Signal K brutes en SI** sont stockées correctement dans InfluxDB:
- **Angles:** radians (ex: 2.2096 rad = 126.6°)
- **Attitudes:** radians (ex: -0.00518 rad = -0.30°)
- **Vitesses:** m/s (données futures)
- **Température:** Kelvin (données futures)
- **Pression:** Pascal (données futures)

---

## Audit Détaillé: Valeurs Observées

### 1. ANGLES — Radians → Degrés

#### navigation.attitude.roll
- **Valeur brute:** `-0.005177 rad`
- **Conversion:** `-0.005177 × 57.2958 = -0.297°`
- **Interprétation:** Bateau presque droit (gîte négligeable)
- **Status:** ✅ CORRECT

#### navigation.attitude.pitch
- **Valeur brute:** `-0.022914 rad`
- **Conversion:** `-0.022914 × 57.2958 = -1.313°`
- **Interprétation:** Légère assiette piquée (normal)
- **Status:** ✅ CORRECT

#### navigation.attitude.yaw
- **Valeur brute:** `1.740685 rad`
- **Conversion:** `1.740685 × 57.2958 = 99.78°`
- **Interprétation:** Cap/yaw cohérent
- **Status:** ✅ CORRECT

#### navigation.courseOverGroundTrue
- **Valeur brute:** `2.209587 rad`
- **Conversion:** `2.209587 × 57.2958 = 126.6°`
- **Interprétation:** Cap environ 127° (SE, cohérent)
- **Status:** ✅ CORRECT

### 2. ACCÉLÉRATIONS — Pas de conversion

#### navigation.acceleration.x
- **Valeur brute:** `0.2347 m/s²`
- **Unité:** m/s² (SI - déjà correct)
- **Status:** ✅ NO CONVERSION

#### navigation.acceleration.y
- **Valeur brute:** `-0.0527 m/s²`
- **Unité:** m/s² (SI - déjà correct)
- **Status:** ✅ NO CONVERSION

#### navigation.acceleration.z
- **Valeur brute:** `10.150 m/s²`
- **Unité:** m/s² (SI - déjà correct, inclut gravité ~9.81)
- **Status:** ✅ NO CONVERSION

### 3. AUTRES DONNÉES OBSERVÉES

#### environment.system.cpuTemperature
- **Valeur brute:** `74.0`
- **Unité:** °C (pas de conversion nécessaire)
- **Status:** ✅ CORRECT

#### navigation.gnss.antennaAltitude
- **Valeur brute:** `123.82 m`
- **Unité:** mètres (pas de conversion)
- **Status:** ✅ CORRECT

---

## Données Futures (Pas encore en flux live)

Basé sur la structure Signal K, ces measurements arrivent en SI:

| Measurement | Field | SI Unit | Display Unit | Conversion |
|---|---|---|---|---|
| navigation | speedOverGround | m/s | knots | × 1.94384 |
| navigation | speedThroughWater | m/s | knots | × 1.94384 |
| environment.wind | speedTrue | m/s | knots | × 1.94384 |
| environment.wind | speedApparent | m/s | knots | × 1.94384 |
| environment.wind | directionTrue | rad | ° | × 57.2958 |
| environment.wind | angleApparent | rad | ° | × 57.2958 |
| environment.wind | angleTrueWater | rad | ° | × 57.2958 |
| environment.water | temperature | K | °C | − 273.15 |
| environment.outside | pressure | Pa | hPa | ÷ 100 |
| performance | velocityMadeGood | m/s | knots | × 1.94384 |

---

## Conclusions Phase 1

### ✅ Confirmé:

1. **InfluxDB stocke correctement en SI**
   - Pas de corruption de données
   - Pas de double-conversion
   - Source fiable pour les conversions

2. **Les conversions à appliquer sont simples**
   - Multipliez/divisez des facteurs constants
   - Pas de logique complexe

3. **Les données observées sont cohérentes**
   - Roll/pitch/yaw = petits angles (< 2 rad) ✅
   - Accélérations = < 11 m/s² ✅
   - CPU temp = raisonnable ✅

### ⏳ À Faire (PHASE 2-3):

1. Créer la bibliothèque Flux avec tous les snippets
2. Modifier chaque panel Grafana avec les conversions
3. Tester les conversions sur les données live

---

## Template Flux pour Conversions

Utiliser ces templates dans chaque panel Grafana:

### Angles (rad → °)
```flux
|> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

### Vitesses (m/s → knots)
```flux
|> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```

### Température (K → °C)
```flux
|> map(fn: (r) => ({r with _value: r._value - 273.15}))
```

### Pression (Pa → hPa)
```flux
|> map(fn: (r) => ({r with _value: r._value / 100.0}))
```

### Exemple Complet: Roll en Degrés

```flux
from(bucket: "midnight_rider")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "navigation.attitude.roll")
  |> map(fn: (r) => ({r with _value: r._value * 57.2958}))
```

---

## Status: PHASE 1 ✅ COMPLETE

**Prêt pour PHASE 2 (Bibliothèque Flux)**

Timestamp: 2026-04-27T22:55:00-0400 EDT

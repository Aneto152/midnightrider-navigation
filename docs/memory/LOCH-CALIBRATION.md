# Loch à Hélice/Roue — Calibrage & Intégration Signal K

## Overview

- **Type:** Loch à hélice/roue (vitesse par rotation)
- **Modèle:** À déterminer (Denis)
- **Flux:** BIDIRECTIONNEL (Loch → Signal K → NMEA2000 réinjection)
- **Calibrage:** Offset + facteur d'échelle (+ polynôme si nécessaire)

## Architecture

```
Loch physique (hélice/roue)
    ↓ (NMEA0183 ou NMEA2000)
Signal K Provider (reçoit brut)
    ↓ (calibrage appliqué)
navigation.speedThroughWater (STW calibré)
    ↓ (plugin output NMEA2000)
NMEA2000 Bus (réinjection)
    ↓
Vulcan + autres afficheurs
```

## Problèmes Typiques des Lochs Hélice

| Problème | Cause | Impact |
|----------|-------|--------|
| **Offset** | Frottements, alignement | Lit 0.2-0.5kt au repos |
| **Usure hélice** | Encrassement, corrosion | Facteur d'échelle dérive |
| **Non-linéarité** | Performance basse vitesse | Imprécis < 2 knots |
| **Température** | Eau froide/chaude | Viscosité → biais vitesse |

## Méthodes de Calibrage

### 1️⃣ Calibrage Statique (simple)

**Procédure:**
1. Bateau immobile (quai ou mouillage)
2. Lire la valeur brute du loch
3. Doit afficher 0 knot (ou proche)
4. Si lit 0.3kt → offset = -0.3

**Configuration Signal K:**
```json
{
  "offset": -0.3,
  "comment": "Lecture au repos"
}
```

### 2️⃣ Calibrage en Route (recommandé ✅)

**Meilleure méthode — calibrage GPS vs loch**

**Procédure:**
1. Parcourir distance connue (ex: 1nm entre deux points)
2. Temps stable, vent faible, mer calme
3. Calculer moyenne GPS SOG sur la distance
4. Calculer moyenne Loch STW sur même temps
5. Facteur = GPS SOG / Loch STW brut

**Exemple concret:**

```
Trajet: 1 nautical mile
Temps: 10 minutes
GPS moyen: 6.5 knots
Loch brut moyen: 6.8 knots

Facteur = 6.5 / 6.8 = 0.956
→ Loch lit ~4.4% trop rapide

Configuration Signal K:
{
  "offset": 0,
  "factor": 0.956
}
```

**Formule appliquée dans Signal K:**
```
STW_calibré = (STW_brut + offset) × factor
STW_calibré = (6.8 + 0) × 0.956 = 6.49 knots ✅
```

### 3️⃣ Calibrage Avancé — Polynômiale

**Si loch très nonlinéaire (rarement nécessaire)**

**Procédure:**
1. Collecter paires (Loch_brut, GPS_moyen) à différentes vitesses
   - 2-3 knots
   - 4-5 knots
   - 6-7 knots
   - 8+ knots
2. Fitter polynôme ordre 2 ou 3
3. Utiliser coefficients dans Signal K

**Exemple:**

```
Données collectées:
  Loch brut: 2.0 → GPS: 1.95
  Loch brut: 5.0 → GPS: 4.82
  Loch brut: 7.0 → GPS: 6.75
  Loch brut: 8.5 → GPS: 8.15

Polynôme: y = 0.05 + 0.95*x + 0.002*x²

Configuration Signal K:
{
  "calibration": {
    "type": "polynomial",
    "coefficients": [0.05, 0.95, 0.002],
    "unit": "knots"
  }
}
```

## Signal K Paths

Après calibrage, les données seront disponibles à:

```
navigation.speedThroughWater       # STW calibré (utilisé par perf calcs)
navigation.speedThroughWaterRaw    # STW brut (avant calibrage, debug)
environment.water.temperature      # Si capteur intégré
```

## NMEA2000 Output

Pour réinjecter le STW calibré sur le bus NMEA2000:

**PGN standard:** 128259 (Water speed - knots)

**Configuration plugin (à déterminer):**
```json
{
  "inputPath": "navigation.speedThroughWater",
  "outputPGN": 128259,
  "interval": 1000,  // 1 sec
  "sourceInstance": 0
}
```

## Workflow — Prochaines Étapes

### Phase 1: Préparation
- [ ] Obtenir modèle exact du loch
- [ ] Identifier sortie (NMEA0183 ou NMEA2000?)
- [ ] Connecter à Signal K (provider config)
- [ ] Tester réception des données brutes

### Phase 2: Calibrage
- [ ] Calibrage statique (offset)
- [ ] Calibrage en route (facteur)
- [ ] Valider sur 3-4 passages
- [ ] Déterminer si polynôme nécessaire

### Phase 3: Intégration
- [ ] Configurer plugin NMEA2000 output
- [ ] Réinjection sur le bus
- [ ] Tester affichage Vulcan
- [ ] Valider calculs perf (VMG, etc.)

### Phase 4: Validation
- [ ] Test en bateau (plusieurs allures)
- [ ] Comparaison GPS long-court terme
- [ ] Affinage si nécessaire
- [ ] Documentation finale

## Related

- **Performance Alerts:** PERF-01 à PERF-12 utilisent STW
- **Flux courant:** Calcul SOG - STW pour direction courant
- **InfluxDB:** Stocker STW_brut + STW_calibré pour analyse
- **PGN 130824:** Performance data peut inclure VMG (basé sur STW)

---

**Last updated:** 2026-04-19  
**Status:** À faire calibrage  
**Owner:** Denis Lafarge

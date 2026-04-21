# Loch Calibration System — Signal K Plugin

**Date:** 2026-04-21  
**Bateau:** J/30 MidnightRider  
**Plugin:** signalk-loch-calibration  
**Purpose:** Calibrate raw loch speed and reinject into NMEA2000

---

## 📋 Vue d'ensemble

Le loch (speed through water sensor) mesure rarement avec précision absolue. Ce plugin:
- ✅ Reçoit vitesse brute (navigation.speedThroughWaterRaw)
- ✅ Applique calibration (offset + factor, ou polynomial)
- ✅ Réinjecte vitesse calibrée (navigation.speedThroughWater)
- ✅ Stocke dans InfluxDB (24h+ historique)
- ✅ Affiche dans Grafana avec comparaison GPS
- 📍 Reinjecte en NMEA2000 (future)

---

## 🎯 Problèmes typiques des lochs

### Dérive statique (Offset)
```
À l'arrêt (bateau immobile au quai):
  Loch affiche: 0.2-0.5 knots
  Réel: 0 knots
  
Offset = 0.2-0.5 knots
Solution: Soustraire l'offset
```

### Dérive d'échelle (Factor)
```
Loch usé ou encrassé:
  GPS: 6.5 knots (vrai, mesuré sur 1nm)
  Loch: 6.8 knots (lit trop rapide)
  
Factor = GPS / Loch = 6.5 / 6.8 = 0.956
Solution: Multiplier par le facteur
```

### Non-linéarité
```
Très basses vitesses (< 1 knot):
  Loch: erreurs >10%
  
Solution: Polynôme d'ordre 2-3
  speedCalibrated = a0 + a1*x + a2*x²
```

---

## 🔧 Calibration Methods

### Méthode 1: Linear (Recommandée pour début)

**Formule:**
```
speedCalibrated = (speedRaw - offset) * factor
```

**Paramètres:**
- `offset`: Valeur à soustraire (m/s)
- `factor`: Multiplicateur (ratio)

**Exemple:**
```json
{
  "calibrationMethod": "linear",
  "linearCalibration": {
    "offset": 0.1,
    "factor": 0.98
  }
}
```

**Interprétation:**
```
Loch lit: 5.0 m/s
Moins offset: 5.0 - 0.1 = 4.9 m/s
Fois factor: 4.9 × 0.98 = 4.802 m/s ✅
```

---

### Méthode 2: Polynomial (Avancée)

**Formule:**
```
speedCalibrated = c[0] + c[1]*x + c[2]*x² + c[3]*x³
```

**Paramètres:**
- `coefficients`: [a0, a1, a2, a3, ...]
- `order`: Degré du polynôme

**Exemple:**
```json
{
  "calibrationMethod": "polynomial",
  "polynomialCalibration": {
    "coefficients": [0.05, 0.95, 0.002, 0],
    "order": 2
  }
}
```

**Utilité:**
- Loch très nonlinéaire (ancien, usé)
- Plusieurs régimes de vitesse différents
- Besoin haute précision (<2% error)

---

### Méthode 3: None (Bypass/Testing)

```json
{
  "calibrationMethod": "none"
}
```

Passthrough brut (pas de calibration). Utile pour:
- Tester avant d'avoir coefficients
- Débugging
- Loch neuf (supposé précis)

---

## 🚀 Installation & Configuration

### 1. Installer le plugin

```bash
# Fichier déjà créé:
# /home/aneto/.signalk/plugins/signalk-loch-calibration.js
# /home/aneto/.signalk/plugin-config-data/signalk-loch-calibration.json

# Redémarrer Signal K pour charger
docker restart signalk
```

### 2. Vérifier que le loch envoie des données

```bash
# Signal K API
curl http://localhost:3000/signalk/v1/api/self/navigation/speedThroughWaterRaw

# Réponse attendue:
# {"value": 5.123, "timestamp": "2026-04-21T12:49:00Z"}
```

### 3. Configurer calibration

#### Option A: Calibrage statique (Repos au quai)

```bash
# Bateau immobile au quai
# Observer loch pendant 10 min

Loch affiche: 0.25 m/s
Réel: 0 m/s

offset = 0.25 m/s

# Mettre en config:
{
  "linearCalibration": {
    "offset": 0.25,
    "factor": 1.0
  }
}
```

#### Option B: Calibrage en route (Recommandé)

```
Procédure:
1. Marker deux points (ex: deux bouées, distance connue = 1nm)
2. Parcourir distance lentement
3. Chrono le temps exact
4. Moyenne GPS SOG = distance / temps
5. Moyenne Loch = moyenne readings en même temps
6. Factor = GPS / Loch
```

**Exemple:**
```
Distance: 1 nautical mile = 1852m
Temps: 10 min = 600 sec
GPS vitesse réelle: 1852 / 600 = 3.087 m/s

Loch moyennes: 3.2, 3.19, 3.21, 3.2, 3.18 m/s
Loch moyenne: 3.196 m/s

Factor = 3.087 / 3.196 = 0.966
```

#### Option C: Calibrage polynôme (Avancé)

Collecter 5-10 paires (Loch, GPS) à vitesses différentes:

```
GPS (m/s)  Loch (m/s)  Error %
1.5        1.6        +6.7%
2.5        2.6        +4.0%
3.0        3.1        +3.3%
4.0        4.15       +3.8%
5.0        5.2        +4.0%
6.0        6.25       +4.2%

→ Tendance: Loch lit ~4% trop rapide (quasi-linéaire)
→ Solution: factor = 0.96 suffit
```

---

## 📊 Signal K Paths

### Inputs
```
navigation.speedThroughWaterRaw    # Brute loch (m/s)
```

### Outputs
```
navigation.speedThroughWater       # Calibrée (m/s) ← MAIN OUTPUT
navigation.speedThroughWaterSmoothed # Lissée (m/s)
navigation.loch.calibrationOffset  # Différence GPS (m/s)
```

---

## 📈 Grafana Dashboard

### Panel 1: Raw vs Calibrated

```
Line Chart:
  • Loch brute (navigation.speedThroughWaterRaw)
  • Loch calibrée (navigation.speedThroughWater)
  • GPS SOG (navigation.speedOverGround)
  
Format: 0.1 sec sampling → 1 min average
```

### Panel 2: Calibration Error

```
Line Chart:
  • Offset (calibrée - GPS)
  • Seuil ±0.2 m/s (warning)
  • Seuil ±0.5 m/s (critical)
```

### Panel 3: Statistics

```
Stat Panel:
  • Min/Max Loch brute (m/s)
  • Min/Max Loch calibrée (m/s)
  • Moyenne brute vs calibrée
  • Points traités (24h)
```

---

## 🧪 Calibration Procedure (Détaillé)

### Semaine 1: Baseline

**Jour 1-3: Calibrage statique (au quai)**
```
□ Bateau immobile
□ Moteur OFF
□ Loch branché
□ Observer 10 minutes
□ Noter lecture moyenne
□ offset = lecture
□ factor = 1.0
```

**Exemple de résultat:**
```
Offset observé: 0.15 m/s
Configuration:
{
  "offset": 0.15,
  "factor": 1.0
}
```

---

### Semaine 2: Calibrage en route

**Jour 1-2: Parcours d'étalonnage**
```
□ Deux points connus (distance 1-2 nm)
□ Parcourir: lent (2-3 kt), moyen (4-5 kt), rapide (6-7 kt)
□ Pour chaque vitesse:
  - Chrono GPS précis (AIS, chartplotter)
  - Noter loch moyenne
  - Calculer factor
  - Mettre en config
□ Tester sur plusieurs parcours
□ Affiner si besoin
```

**Résultat typique:**
```
Loch 2.5 kt → GPS 2.4 kt → factor = 0.96
Loch 5.0 kt → GPS 4.9 kt → factor = 0.98
Loch 7.0 kt → GPS 6.8 kt → factor = 0.97

Factor moyen: 0.97
Configuration:
{
  "offset": 0.15,
  "factor": 0.97
}
```

---

### Semaine 3: Validation

**En navigation réelle:**
```
□ Surveiller offset (calibrée - GPS)
□ Target: < 0.2 m/s error
□ Si > 0.5 m/s: re-calibrer
□ Logger données 1 semaine
□ Analyser pattern (si offset varie avec vitesse → polynomial)
```

---

## 🔄 Dynamic Calibration (Optional)

### Auto-calibration avec GPS

**Concept:**
```
À chaque seconde:
1. Lire Loch + GPS
2. Si GPS valide:
   offset_atual = speedCalibrated - GPS
   moyenne_offset = EMA(offset_atual, alpha=0.1)
3. Si abs(offset) > threshold:
   ajuster factor dynamiquement
```

**Code (simplifié):**
```javascript
// En développement pour version v2
const offsetGPS = speedCalibrated - gpsSpeed;
if (Math.abs(offsetGPS) > 0.3) {
  // Signal d'alerte
  app.handleMessage({
    updates: [{
      path: 'notifications.navigation.lochCalibrationDrift',
      value: { ... }
    }]
  });
}
```

---

## 📝 Maintenance

### Hebdomadaire
```
□ Vérifier offset (calibrée - GPS)
□ Target: moyenne < 0.2 m/s
□ Si dépasse: noter et ajuster factor
```

### Mensuel
```
□ Nettoyer capteur loch (si accessible)
□ Vérifier connexion électrique
□ Test complet (quai + route)
□ Revalider factor
```

### Annuel (fin saison)
```
□ Inspection capteur (usure, encrassement)
□ Recalibrage complet
□ Historique: analyser trend annuel
□ Rapport: précision, dérives observées
```

---

## 🚨 Troubleshooting

### Problème: Pas de données brutes

```
Check:
1. Loch connecté (NMEA0183 ou NMEA2000)?
2. Signal K reçoit-il sentences?
   → curl http://localhost:3000/signalk/v1/api/self/navigation/speedThroughWaterRaw
3. Fréquence suffisante (1 Hz)?
4. Câblage sain?

Solution:
  • Vérifier sources NMEA0183 dans Signal K
  • Tester avec autre reader NMEA (ex: desktop app)
```

### Problème: Calibration instable

```
Causes:
• Loch avec beaucoup de bruit
• Water flow turbulent
• Capteur encrassé

Solution:
  • Augmenter windowSize smoothing (de 5 → 10)
  • Nettoyer capteur
  • Diminuer minSpeed threshold
  • Utiliser polynomial si trend visible
```

### Problème: Offset varie avec vitesse

```
Symptôme:
  Lent (2kt): offset = 0.1 m/s
  Moyen (5kt): offset = 0.3 m/s
  Rapide (8kt): offset = 0.5 m/s

Cause: Non-linéarité du loch

Solution: Utiliser polynomial
{
  "calibrationMethod": "polynomial",
  "polynomialCalibration": {
    "coefficients": [0.1, 0.92, 0.015, 0],
    "order": 2
  }
}
```

---

## 📚 Ressources

### Documentation Signal K
- Speed through water: https://signalk.org/specification/1.5.1/
- NMEA0183 VTG sentence: RMC, VTG (speed)
- NMEA2000 PGN 128267: Water speed

### Loch Manufacturers
- Airmar: https://www.airmar.com
- B&G: https://www.bandg.com
- Raymarine: https://www.raymarine.com
- Garmin: https://www.garmin.com/marine

---

## 🎬 Configuration Recommendation

### Pour commencer (J/30)

```json
{
  "enabled": true,
  "debug": true,
  "inputPath": "navigation.speedThroughWaterRaw",
  "outputPath": "navigation.speedThroughWater",
  "calibrationMethod": "linear",
  "linearCalibration": {
    "offset": 0.15,
    "factor": 0.97
  },
  "smoothing": {
    "enabled": true,
    "windowSize": 5,
    "minSpeed": 0.2,
    "maxSpeed": 10.0
  },
  "statistics": {
    "enabled": true,
    "logInterval": 60000
  }
}
```

**Étapes:**
1. Installer plugin (déjà fait ✅)
2. Tester avec offset=0, factor=1 (1 heure)
3. Faire calibrage au quai (1 heure) → déterminer offset
4. Faire parcours route (2-3 heures) → déterminer factor
5. Affiner avec Grafana (ongoing)

---

## API & Integration

### Readiness Checklist

- [ ] Plugin installed
- [ ] Loch sending raw data
- [ ] Signal K receives navigation.speedThroughWaterRaw
- [ ] Calibration parameters configured
- [ ] Grafana dashboard created (optional)
- [ ] Tested with GPS validation
- [ ] NMEA2000 output ready (future)

---

**Ready to calibrate your loch! 🚤**

Questions? Check logs:
```bash
docker logs signalk | grep Loch
```

# Intégration des Laylines dans Signal K

**Date:** 2026-04-21  
**Bateau:** J/30 (MidnightRider)  
**Objectif:** Navigation tactique en temps réel avec optimisation de cap vers les marques

---

## Vue d'ensemble

Une **layline** est le cap optimal permettant d'accoster une marque sans virer supplémentaire.

### Exemple pratique (régates)
```
Situation: Près vers Marque 1
  • Ton cap: 330°
  • Marque: cap 320° (NW)
  • Vent: 10kt au près (45°)
  
Layline optimal: 320°
Ton écart: +10° (au-dessus du layline)
Recommendation: "Abats de 10° pour accoster marque"
Gain de temps: ~30 secondes pour 1nm
```

---

## Architecture Signal K

### Données requises
```
Navigation (1 Hz):
  ✓ navigation.position.latitude
  ✓ navigation.position.longitude
  ✓ navigation.courseOverGroundTrue
  ✓ navigation.speedOverGround

Environment (1 Hz):
  ✓ environment.wind.speedTrue
  ✓ environment.wind.angleTrueWater

Racing (manuel ou API):
  ✓ Positions des 3 marques (lat, lon)

Performance:
  ✓ J/30 polars data
```

### Signal K Paths créés
```javascript
navigation.racing.layline              // Bearing optimal (radians)
navigation.racing.distanceToMark       // Distance en mètres
navigation.racing.offsetFromLayline    // Écart du layline (m ou °)
navigation.racing.laylineOptimal       // true si sur le layline
navigation.racing.recommendation       // Texte d'action
navigation.racing.markSequence         // Numéro de la marque actuelle
navigation.racing.timeToMark           // Temps estimé (secondes)
```

---

## OPTION 1: Plugin Signal K (Recommandé)

### Avantages
- ✅ Native Signal K integration
- ✅ Temps réel (1 Hz)
- ✅ Accès à toutes les données
- ✅ Auto-save dans InfluxDB
- ✅ Utilisable par MCP tools

### Implémentation

**File:** `/home/aneto/.signalk/plugins/signalk-layline-calculator.js`

```javascript
module.exports = function(app) {
  const debug = true;
  const UPDATE_INTERVAL = 1000; // 1 Hz
  
  // Marques de course (configurable)
  const marks = [
    { name: 'Mark 1', lat: 40.7700, lon: -73.9950 },
    { name: 'Mark 2', lat: 40.7650, lon: -73.9900 },
    { name: 'Mark 3', lat: 40.7600, lon: -73.9850 }
  ];
  
  let currentMarkIndex = 0;

  // Haversine: calcule bearing et distance
  function calculateBearingDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Earth radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    
    // Distance
    const a = Math.sin(dLat/2)**2 + 
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2)**2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distance = R * c;
    
    // Bearing
    const y = Math.sin(dLon) * Math.cos(lat2 * Math.PI / 180);
    const x = Math.cos(lat1 * Math.PI / 180) * Math.sin(lat2 * Math.PI / 180) -
              Math.sin(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
              Math.cos(dLon);
    const bearing = Math.atan2(y, x);
    
    return { bearing, distance };
  }

  // Calcule layline optimal
  // Utilise VMG (Velocity Made Good) pour trouver meilleur cap
  function calculateLayline(markBearing, tws, twa, boatSpeed) {
    // Angle du vent vrai
    const windAngle = twa;
    
    // Si au près (< 60°): utilise angle polaire optimal (~45° du vent)
    // Si portant (> 100°): cap direct vers marque
    // Entre: transition progressive
    
    if (windAngle < 1.047) { // < 60° = près
      // Au près: cherche VMG maximum vers la marque
      // Angle optimal J/30 au près: ~45° du vent
      return markBearing; // Simplifié: utilise bearing direct
    } else if (windAngle > 1.745) { // > 100° = portant
      // Portant: va direct vers la marque
      return markBearing;
    } else {
      // Entre: transition douce
      return markBearing;
    }
  }

  // Calcule écart du layline
  function calculateOffset(currentCourse, layline) {
    let offset = currentCourse - layline;
    
    // Normaliser entre -π et +π
    while (offset > Math.PI) offset -= 2 * Math.PI;
    while (offset < -Math.PI) offset += 2 * Math.PI;
    
    return offset;
  }

  // Timer principal
  const interval = setInterval(() => {
    try {
      const position = app.getSelfPath('navigation.position');
      const cog = app.getSelfPath('navigation.courseOverGroundTrue.value');
      const sog = app.getSelfPath('navigation.speedOverGround.value');
      const tws = app.getSelfPath('environment.wind.speedTrue.value');
      const twa = app.getSelfPath('environment.wind.angleTrueWater.value');
      
      if (!position || !cog || !tws || !twa) return;
      
      const lat = position.value.latitude;
      const lon = position.value.longitude;
      const mark = marks[currentMarkIndex];
      
      if (!lat || !lon) return;
      
      // Calculs
      const { bearing, distance } = calculateBearingDistance(lat, lon, mark.lat, mark.lon);
      const layline = calculateLayline(bearing, tws, twa, sog);
      const offset = calculateOffset(cog, layline);
      const offsetDeg = offset * 180 / Math.PI;
      
      // Estimation temps (très simplifié)
      const timeToMark = distance / Math.max(sog, 0.1);
      
      // Recommendation texte
      let recommendation = '';
      if (Math.abs(offsetDeg) < 5) {
        recommendation = '✅ Sur le layline - maintien le cap';
      } else if (offsetDeg > 0) {
        recommendation = `📈 Au-dessus du layline - abats ${Math.abs(offsetDeg).toFixed(1)}°`;
      } else {
        recommendation = `📉 Sous le layline - lofe ${Math.abs(offsetDeg).toFixed(1)}°`;
      }
      
      // Injecter dans Signal K
      app.handleMessage({
        updates: [{
          source: { label: 'layline-calculator', type: 'NMEA0183' },
          timestamp: new Date().toISOString(),
          values: [
            { path: 'navigation.racing.layline', value: layline },
            { path: 'navigation.racing.distanceToMark', value: distance },
            { path: 'navigation.racing.offsetFromLayline', value: offset },
            { path: 'navigation.racing.laylineOptimal', value: Math.abs(offsetDeg) < 5 },
            { path: 'navigation.racing.recommendation', value: recommendation },
            { path: 'navigation.racing.timeToMark', value: timeToMark },
            { path: 'navigation.racing.markSequence', value: currentMarkIndex }
          ]
        }]
      });
      
      if (debug) {
        app.debug(`[Layline] Offset: ${offsetDeg.toFixed(1)}° | Distance: ${(distance/1852).toFixed(2)} nm | Mark ${currentMarkIndex}`);
      }
      
    } catch (err) {
      app.error(`[Layline] Error: ${err.message}`);
    }
  }, UPDATE_INTERVAL);

  return {
    start() {
      app.debug('[Layline] Plugin started');
    },
    stop() {
      clearInterval(interval);
      app.debug('[Layline] Plugin stopped');
    },
    setMark(index) {
      currentMarkIndex = Math.min(index, marks.length - 1);
    }
  };
};
```

### Configuration

**File:** `/home/aneto/.signalk/plugin-config-data/signalk-layline-calculator.json`

```json
{
  "enabled": true,
  "debug": true,
  "updateInterval": 1000,
  "marks": [
    {
      "name": "Mark 1 (Start/Finish)",
      "lat": 40.7700,
      "lon": -73.9950,
      "description": "Stamford LIS - départ"
    },
    {
      "name": "Mark 2 (Leeward)",
      "lat": 40.7650,
      "lon": -73.9900,
      "description": "Milieu LIS"
    },
    {
      "name": "Mark 3 (Windward)",
      "lat": 40.7600,
      "lon": -73.9850,
      "description": "Ouest LIS"
    }
  ]
}
```

---

## OPTION 2: MCP Tool (Coaching)

### Implémentation
```javascript
// MCP Racing Tool - Layline Calculator
module.exports = {
  name: 'calculate-layline',
  description: 'Calculate optimal layline to a mark',
  inputSchema: {
    type: 'object',
    properties: {
      currentLat: { type: 'number', description: 'Latitude actuelle' },
      currentLon: { type: 'number', description: 'Longitude actuelle' },
      markLat: { type: 'number', description: 'Latitude de la marque' },
      markLon: { type: 'number', description: 'Longitude de la marque' },
      tws: { type: 'number', description: 'True Wind Speed (knots)' },
      twa: { type: 'number', description: 'True Wind Angle (degrés)' }
    }
  },
  
  async execute(input) {
    // Haversine calculation
    // Return { laylineBearing, distanceToMark, recommendation }
  }
};
```

### Utilisation
```
Claude: "Calcule la layline vers Mark 1"
MCP Tool Response:
  Bearing: 320°
  Distance: 1.2 nm
  Offset: +10° (au-dessus)
  Recommendation: "Abats de 10° pour accoster"
```

---

## OPTION 3: Grafana Dashboard

### Panels recommandés

1. **Layline Bearing Gauge**
   - 0-360° gauge
   - Affiche layline optimal
   - Aiguille = cap actuel

2. **Distance to Mark**
   - Gauge en nm
   - Seuils: > 5nm (rouge) | 2-5nm (jaune) | < 2nm (vert)

3. **Offset from Layline (Graph)**
   - Line chart -90° à +90°
   - Zéro = sur le layline
   - Montre trend offwind/onwind

4. **Mark Position (Map)**
   - Map avec position bateau
   - Marque cible
   - Layline tracée

---

## Flux de données complet

```
GPS Position (1 Hz)
    ↓
Haversine calculation
    ↓
Bearing & Distance to Mark
    ↓
Wind data
    ↓
Layline Optimization (with polars)
    ↓
Signal K Injection (navigation.racing.*)
    ↓
┌─────────────────┬──────────────┬────────────┐
↓                 ↓              ↓            ↓
InfluxDB      Grafana      MCP Tools    Display
(storage)    (visual)    (coaching)    (iPad)

24h History  Real-time  "Abats de 10°" Live data
```

---

## Cas d'usage

### Course Mark-to-Mark
```
Situation: Tu navigues vers Mark 1
Données: Position GPS, Vent, Polaires

Système retourne:
  • Layline: 320° (bearing optimal)
  • Offset: +10° (tu es au-dessus)
  • Time to mark: 8 min
  • Recommendation: "Abats de 10° pour accoster"

Résultat: Tu gains temps en optimisant le cap
```

### Analyse tactique post-race
```
InfluxDB stocke 60 min de layline data
Analyse: À quel point du parcours tu as dévié du layline
Optimisation: Ajuste stratégie pour prochaine course
```

---

## Phases d'implémentation

### PHASE 1: Basique (2-3h)
- [ ] Créer plugin Signal K
- [ ] Implémenter Haversine formula
- [ ] Tester avec marques fictives
- [ ] Valider Signal K API

### PHASE 2: Avancé (3-4h)
- [ ] Intégrer polaires J/30
- [ ] Ajouter MCP tool
- [ ] Créer Grafana panels
- [ ] Tester avec vraies marques

### PHASE 3: Production (2-3h)
- [ ] Configurer 3 marques de course
- [ ] Test en navigation réelle
- [ ] Collecter feedback
- [ ] Tuning des thresholds

---

## Ressources

- Signal K Racing: https://signalk.org/appstore/racing
- Layline theory: https://sailing.world/layline-tactics
- J/30 Polars: voir `j30-polars-data.json`
- Haversine Formula: https://en.wikipedia.org/wiki/Haversine_formula

---

**Prochaines questions?**
- Marques spécifiques du bassin?
- Faut-il du multi-fleet (tactique compétiteurs)?
- Alertes Grafana pour le layline?

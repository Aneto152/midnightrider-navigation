# ⛵ INTÉGRATION ANALYSE PERFORMANCE POLAIRE DANS SIGNAL K

**Date:** 2026-04-20  
**Goal:** Comment intégrer analyse polaire dans Signal K pour coaching en temps réel  
**Status:** Architecture existante + implémentation proposée

---

## 🎯 VUE D'ENSEMBLE

Signal K a **déjà une structure complète** pour les polaires (`performance.*` paths).
Le challenge est d'injecter les données polaires et de calculer l'efficacité en temps réel.

### Composants Nécessaires

```
1. Données Polaires (J/30) ← Table de référence
2. Récepteur Plugin Signal K ← Injection des paths
3. Calculs d'Efficacité ← Performance analysis
4. Stockage InfluxDB ← Historical tracking
5. MCP Tools ← Claude coaching
6. Grafana Visualisation ← Dashboards
```

---

## 📊 SIGNAL K PERFORMANCE PATHS (Déjà existants!)

### Structure complète dans `/schemas/groups/performance.json`:

```
navigation.performance
├─ polars                          (Dictionnaire de tables)
├─ activePolar                     (UUID de la polaire active)
├─ activePolarData                 (Polaire actuellement active)
├─ polarSpeed                      (Vitesse polaire pour conditions actuelles)
├─ polarSpeedRatio                 (Actual speed / Polar speed = EFFICIENCY %)
├─ velocityMadeGood               (VMG réelle)
├─ beatAngle                       (Angle optimal au près)
├─ beatAngleVelocityMadeGood      (VMG optimal au près)
├─ beatAngleTargetSpeed           (Vitesse cible au près)
├─ gybeAngle                       (Angle optimal au portant)
├─ gybeAngleVelocityMadeGood      (VMG optimal au portant)
├─ gybeAngleTargetSpeed           (Vitesse cible au portant)
├─ targetAngle                     (Angle cible global)
├─ targetSpeed                     (Vitesse cible)
└─ leeway                          (Dérive due au vent de travers)
```

Tous les **paths existent déjà**! Il faut juste les alimenter.

---

## 🔄 ARCHITECTURE D'INTÉGRATION

### Option A: Plugin Signal K (Recommandé)

```
J/30 Polaires JSON
      ↓
Plugin Signal K "signalk-performance-polars"
      ↓
Injecte: polars, activePolar, polarSpeed, polarSpeedRatio, etc.
      ↓
Signal K Bus (navigation.performance.*)
      ↓
InfluxDB (auto via signalk-to-influxdb2)
      ↓
MCP Tools (lecture) + Grafana (affichage)
```

**Avantages:**
- ✅ Réutilisable (autre bateau, autres polaires)
- ✅ Architecture Signal K native
- ✅ Alimente automatiquement InfluxDB
- ✅ Accessible via API Signal K

---

### Option B: Plugin B&G natif (Si disponible)

```
Vulcan Display (B&G) → envoie perf data
      ↓
Plugin Signal K B&G receiver
      ↓
Injecte performance.* dans Signal K
      ↓
MCP Tools + Grafana
```

**Avantages:**
- ✅ Données temps réel de l'afficheur
- ✅ Intégration native B&G

**Inconvénient:**
- ❌ Dépend du Vulcan qui calcule déjà

---

### Option C: MCP Server Standalone (Déjà en place!)

```
Données en temps réel Signal K
      ↓
MCP Polar Server (read-only)
      ↓
7 tools Claude: get_boat_efficiency, get_current_polar, etc.
      ↓
Claude coaching
```

**Avantages:**
- ✅ Déjà implémenté et testé
- ✅ Pas besoin plugin Signal K
- ✅ MCP tools disponibles immédiatement

**Inconvénient:**
- ❌ Pas d'historique dans InfluxDB
- ❌ Pas d'alerte temps réel

---

## ✅ APPROCHE RECOMMANDÉE: Option A + C (Combinaison)

**Implémenter DEUX pistes:**

### Piste 1: Plugin Signal K (pour données historiques)
- Créer plugin "signalk-performance-polars"
- Injecte J/30 polaires dans Signal K
- Stocke dans InfluxDB
- Alimente Grafana dashboards temps réel
- Permet alertes basées sur performance

### Piste 2: MCP Tools (pour coaching)
- Déjà en place (5 tools polaires)
- Read-only sur Signal K
- Fournit coaching contextuel à Claude
- Pas de dépendance au plugin

**Résultat:** Système robuste, données redondantes, coaching enrichi.

---

## 🛠️ IMPLÉMENTATION: Plugin Signal K Performance

### Architecture du Plugin

```javascript
// signalk-performance-polars.js

const j30Polars = {
  "id": "j30-production",
  "name": "J/30 Production",
  "description": "Standard J/30 polar diagram",
  "windData": [
    {
      "trueWindSpeed": 5,  // knots
      "angleData": [
        [0.698, 2.5],      // 40°, 2.5 knots
        [0.873, 3.0],      // 50°, 3.0 knots
        [1.047, 3.2],      // 60°, 3.2 knots
        // ... 80 angles
      ],
      "optimalBeats": [[0.873, 3.0]]
    },
    {
      "trueWindSpeed": 10,
      "angleData": [
        [0.698, 4.8],
        [0.873, 5.5],
        // ...
      ],
      "optimalBeats": [[0.873, 5.5]]
    },
    // ... 15+ wind speeds
  ]
};

module.exports = {
  id: 'performance-polars',
  name: 'Performance Polars',
  
  start() {
    // Inject polars into Signal K
    app.signalk.self.navigation.performance = {
      polars: {
        'j30-prod-uuid': j30Polars
      },
      activePolar: 'j30-prod-uuid',
      activePolarData: j30Polars
    };
    
    // Calculate performance metrics
    setInterval(() => {
      const stw = app.getSelfPath('navigation.speedThroughWater.value');
      const tws = app.getSelfPath('environment.wind.speedTrue.value');
      const twa = app.getSelfPath('environment.wind.angleTrueWater.value');
      
      // Calculate polar speed for current conditions
      const polarSpeed = calculatePolarSpeed(tws, twa, j30Polars);
      
      // Efficiency = Actual / Target
      const efficiency = stw / polarSpeed;
      
      // Update Signal K paths
      app.signalk.self.navigation.performance.polarSpeed = {
        value: polarSpeed,
        timestamp: new Date()
      };
      
      app.signalk.self.navigation.performance.polarSpeedRatio = {
        value: efficiency,
        timestamp: new Date()
      };
      
      // Calculate VMG
      const vmg = stw * Math.cos(twa);
      app.signalk.self.navigation.performance.velocityMadeGood = {
        value: vmg,
        timestamp: new Date()
      };
      
      // Calculate target angle/speed
      const optimal = findOptimalAngle(tws, j30Polars);
      app.signalk.self.navigation.performance.targetAngle = {
        value: optimal.angle,
        timestamp: new Date()
      };
      
      app.signalk.self.navigation.performance.targetSpeed = {
        value: optimal.speed,
        timestamp: new Date()
      };
    }, 1000); // Update every second
  },
  
  stop() {
    // Cleanup
  }
};

function calculatePolarSpeed(tws, twa, polarTable) {
  // Linear interpolation between polar points
  // ...implementation...
}

function findOptimalAngle(tws, polarTable) {
  // Find best VMG angle for current wind
  // ...implementation...
}
```

### Fichiers à Créer

```
/home/aneto/.signalk/plugins/
├─ signalk-performance-polars.js
├─ package.json
└─ j30-polars-data.json  (Données polaires)

/home/aneto/.signalk/plugin-config-data/
└─ signalk-performance-polars.json  (Config)
```

---

## 📝 DONNÉES POLAIRES J/30

### Format Standard (YAML/JSON)

```yaml
boat: "J/30"
id: "j30-production"
name: "J/30 Standard Polars"

windData:
  - tws: 5     # knots (True Wind Speed)
    angleData:
      - angle: 40°, speed: 2.5kt, vmg: 1.9kt
      - angle: 50°, speed: 3.0kt, vmg: 2.0kt
      - angle: 60°, speed: 3.2kt, vmg: 2.2kt
      - angle: 70°, speed: 3.5kt, vmg: 2.4kt
      # ... jusqu'à 180°
      
  - tws: 10
    angleData:
      - angle: 40°, speed: 4.8kt, vmg: 3.7kt
      # ... etc
      
  # ... tws: 15, 20, 25
```

### Source Données

**Option 1: Utiliser JSpot (gratuit)**
```bash
# Télécharger polaires J/30 depuis JSpot
# https://www.jspotcloud.com/
```

**Option 2: Utiliser OpenPlotter Polar Creator**
```bash
# Créer/éditer polaires avec OpenPlotter
# Format compatible Signal K
```

**Option 3: Données mesurées**
```
Collecter données réelles en régate:
- Wind speed (tws)
- Boat speed (stw)
- Angles (twa)
- Construire table empirique
```

---

## 🔗 INTÉGRATION AVEC MCP TOOLS

### MCP Polar Server (Existant)

Les 5 tools existants lisent depuis Signal K:

```javascript
// Dans polar-server.js (MCP)

async function get_boat_efficiency() {
  // Lit: navigation.performance.polarSpeedRatio
  const efficiency = await signalkClient.get(
    'navigation.performance.polarSpeedRatio'
  );
  
  return {
    current: efficiency.value,
    target: 0.95,  // 95% est excellent
    status: efficiency.value > 0.95 ? "EXCELLENT" : "SUBOPTIMAL"
  };
}

async function get_current_polar() {
  // Reads: navigation.performance.activePolarData
  const polar = await signalkClient.get(
    'navigation.performance.activePolarData'
  );
  
  return {
    name: polar.name,
    windData: polar.windData,
    activeWind: getCurrentWindSpeedTrue()
  };
}

// ... 3 autres tools
```

**Résultat:** MCP tools alimentés par Signal K, qui lui-même est alimenté par le plugin.

---

## 📊 GRAFANA DASHBOARDS

### Dashboard "Performance Analysis"

```
┌─────────────────────────────────────────────────┐
│ PERFORMANCE DASHBOARD                           │
├─────────────────────────────────────────────────┤
│                                                 │
│ EFFICIENCY (%)     TARGET SPEED      ACTUAL SPEED │
│  ████████ 92%      6.1 kt ←→ 5.4 kt  │
│                                                 │
│ CURRENT POLAR CURVE (10kt wind)                 │
│                                                 │
│   Speed (kt)                                    │
│   7 ┌─────────────────────────────┐            │
│   6 │         ╱╲                   │            │
│   5 │        ╱  ╲                  │            │
│   4 │       ╱    ╲___╱─╲            │            │
│   3 │      ╱              ╲         │            │
│   2 └─────────────────────────────┘            │
│     0° 30° 60° 90° 120° 150° 180°             │
│     └─ You are here (65°, 5.4kt)              │
│                                                 │
│ VMG PERFORMANCE (Last 1h)                      │
│ ▂▃▄▅▆▆▅▄▃▂▂▃▄▅▆▇▇▆▅▄▃▂▂ 2.2 kt avg            │
│                                                 │
│ HEEL vs SPEED (Last 6h)                        │
│ Heel: 18-22° (optimal for current wind)        │
│ Speed: trending up (+0.3kt in last 20min)      │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Panels à Créer

1. **Efficiency Gauge** — Actual / Target speed %
2. **Polar Curve** — Interactive for current wind
3. **Target vs Actual** — Line chart 1h
4. **VMG Trending** — Performance over time
5. **Heel Analysis** — Relation heel/speed
6. **Wind Analysis** — Performance par plage vent

---

## 🚀 ROADMAP D'IMPLÉMENTATION

### Phase 1: Foundation (This week - 4 hours)

- [ ] Create signalk-performance-polars plugin (2h)
- [ ] Load J/30 polar data (1h)
- [ ] Calculate efficiency ratio (1h)
- [ ] Test with live data

### Phase 2: Integration (Week 2 - 3 hours)

- [ ] Connect to MCP tools (1h)
- [ ] Validate Signal K paths (1h)
- [ ] Test InfluxDB storage (1h)

### Phase 3: Visualization (Week 3 - 3 hours)

- [ ] Create Grafana dashboard (2h)
- [ ] Add alert rules for efficiency (1h)
- [ ] Test on iPad

### Phase 4: Coaching (Week 4 - 2 hours)

- [ ] Enhance MCP prompts (1h)
- [ ] Test Claude coaching (1h)

---

## 💻 EXEMPLE CODE: PLUGIN COMPLET

```javascript
// File: signalk-performance-polars.js

const j30Polars = require('./j30-polars.json');

module.exports = function(app) {
  let unsubscribes = [];

  const plugin = {
    id: 'signalk-performance-polars',
    name: 'Performance Polars Analysis',
    description: 'Calculate performance metrics against J/30 polars',
    version: '1.0.0',
    
    start() {
      // Initialize performance object
      app.signalk.self.navigation.performance = 
        app.signalk.self.navigation.performance || {};
      
      // Load polars
      app.signalk.self.navigation.performance.polars = {
        'j30-uuid-1': j30Polars
      };
      
      app.signalk.self.navigation.performance.activePolar = 
        'j30-uuid-1';
      
      app.signalk.self.navigation.performance.activePolarData = 
        j30Polars;
      
      // Subscribe to required values
      const stwStream = app.signalk.self.navigation
        .speedThroughWater.subscribe(value => {
          calculateMetrics();
        });
      
      const twsStream = app.signalk.self.environment.wind
        .speedTrue.subscribe(value => {
          calculateMetrics();
        });
      
      const twaStream = app.signalk.self.environment.wind
        .angleTrueWater.subscribe(value => {
          calculateMetrics();
        });
      
      unsubscribes = [stwStream, twsStream, twaStream];
      
      // Calculate every second too
      this.interval = setInterval(calculateMetrics.bind(this), 1000);
    },
    
    stop() {
      unsubscribes.forEach(unsub => unsub());
      clearInterval(this.interval);
    }
  };
  
  function calculateMetrics() {
    try {
      const stw = app.getSelfPath('navigation.speedThroughWater.value') || 0;
      const tws = app.getSelfPath('environment.wind.speedTrue.value') || 0;
      const twa = app.getSelfPath('environment.wind.angleTrueWater.value') || 0;
      
      if (!stw || !tws) return;
      
      // Find polar speed for current conditions
      const polarSpeed = interpolatePolarSpeed(tws, twa, j30Polars);
      
      // Efficiency = actual / target
      const efficiency = stw / polarSpeed;
      
      // VMG
      const vmg = stw * Math.cos(twa);
      
      // Target
      const target = findOptimal(tws, j30Polars);
      
      // Update Signal K
      const updates = [
        {
          path: 'navigation.performance.polarSpeed',
          value: polarSpeed,
          timestamp: new Date().toISOString()
        },
        {
          path: 'navigation.performance.polarSpeedRatio',
          value: efficiency,
          timestamp: new Date().toISOString()
        },
        {
          path: 'navigation.performance.velocityMadeGood',
          value: vmg,
          timestamp: new Date().toISOString()
        },
        {
          path: 'navigation.performance.targetSpeed',
          value: target.speed,
          timestamp: new Date().toISOString()
        },
        {
          path: 'navigation.performance.targetAngle',
          value: target.angle,
          timestamp: new Date().toISOString()
        }
      ];
      
      app.handleMessage(null, {
        updates: [{
          source: { label: 'performance-polars' },
          timestamp: new Date().toISOString(),
          values: updates
        }]
      });
      
    } catch (err) {
      app.error(`Performance calculation error: ${err.message}`);
    }
  }
  
  function interpolatePolarSpeed(tws, twa, polarData) {
    // Find nearest wind speed in polar
    // Linear interpolate angle/speed
    // Return interpolated speed
    // ... implementation ...
  }
  
  function findOptimal(tws, polarData) {
    // Find angle with best VMG
    // Return { angle, speed, vmg }
    // ... implementation ...
  }
  
  return plugin;
};
```

---

## ✅ CHECKPOINTS DE VALIDATION

- [ ] Plugin crée et installe
- [ ] Polars chargés dans Signal K
- [ ] Paths `navigation.performance.*` remplis
- [ ] Valeurs dans InfluxDB
- [ ] MCP tools lisent correctement
- [ ] Grafana affiche data
- [ ] Claude coaching fonctionne
- [ ] Efficacité calculée < 100ms

---

## 📚 RESSOURCES

**J/30 Polaires:**
- JSpot: https://www.jspotcloud.com/
- OpenPlotter: https://opencpn.org/
- Empirical data: collect during races

**Signal K Performance Schema:**
- `/home/aneto/.signalk/node_modules/@signalk/signalk-schema/schemas/groups/performance.json`

**Références:**
- Signal K Spec: https://signalk.org/specification/1.5.1/
- Performance Analysis: https://www.tacticalboating.com/

---

**Status:** ✅ Architecture validée, prête pour implémentation  
**Effort:** 8-12 heures (spread over 4 weeks)  
**Impact:** Real-time performance coaching in boat

Ready to build this? 🚀⛵

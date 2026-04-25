# ⛵ SYSTÈME DE GESTION DES VOILES — J/30

**Date:** 2026-04-20  
**Goal:** Plugin Signal K pour recommandations de configuration voiles en temps réel  
**Status:** Architecture + implémentation proposée

---

## 🎯 VUE D'ENSEMBLE

Système intelligent qui recommande la meilleure configuration de voiles basée sur:
- **Force du vent** (TWS)
- **Allure** (angle par rapport au vent — TWA)
- **État de la mer** (hauteur vagues, pitch/roll du bateau)
- **Performance** (efficacité vs polaires)

---

## 📊 CONFIGURATIONS VOILES J/30

### Tableau Décisionnel

```
┌──────────────┬──────────────────────────────────────────────────────────┐
│ CONDITION    │ CONFIGURATION RECOMMANDÉE                               │
├──────────────┼──────────────────────────────────────────────────────────┤
│ < 4kt light  │ • Mainsail full + Jib full (ou Génois)                 │
│              │ • TWA 35-45° optimal                                    │
│              │ • Avoid: trop de toile = gîte excessive                │
├──────────────┼──────────────────────────────────────────────────────────┤
│ 4-7kt        │ • Mainsail full + Jib full/genoa optimal               │
│ light air    │ • TWA 40-50° meilleur VMG                              │
│              │ • Heel < 15° = bon                                     │
├──────────────┼──────────────────────────────────────────────────────────┤
│ 7-12kt       │ • Mainsail full + Working Jib                          │
│ medium       │ • Optimal heel 15-18°                                  │
│ breeze       │ • TWA 45-55° upwind                                    │
│              │ • Reef main si rafales récurrentes > 15kt              │
├──────────────┼──────────────────────────────────────────────────────────┤
│ 12-16kt      │ • Mainsail 1 reef + Working Jib                        │
│ fresh        │ • Heel target 18-20°                                   │
│ breeze       │ • Reduce canvas if TWS > 14kt sustained                │
├──────────────┼──────────────────────────────────────────────────────────┤
│ 16-20kt      │ • Mainsail 2 reefs + Working Jib (ou Storm Jib)        │
│ strong       │ • Heel < 22° (security limit)                          │
│              │ • Consider storm jib if TWS > 18kt                     │
├──────────────┼──────────────────────────────────────────────────────────┤
│ > 20kt gale  │ • Mainsail 2 reefs + Storm Jib                         │
│              │ • Heel target 20-22°                                   │
│              │ • Prepare to drop main if gusts > 25kt                 │
│              │ • Run storm trysail if too rough                       │
├──────────────┼──────────────────────────────────────────────────────────┤
│ Downwind     │ • TWA > 120°:                                          │
│ 5-12kt       │   - Jib out + Mainsail full (broad reach)             │
│              │ • TWA > 160°:                                          │
│              │   - Spinnaker (if TWS < 18kt) or jib+main poled       │
│              │ • Very broad: Spinnaker or drogue jib                  │
├──────────────┼──────────────────────────────────────────────────────────┤
│ Downwind     │ • Jib poled out (not spinnaker — too risky alone)       │
│ 12-18kt      │ • Mainsail at safest angle (avoid jibe)                │
│              │ • Heel < 15° (stability)                               │
├──────────────┼──────────────────────────────────────────────────────────┤
│ Sea state    │ • Pitch > 20° (rough):                                 │
│ rough        │   - Reduce mainsail (easier handling)                  │
│              │ • Roll > 25° (heavy roll):                             │
│              │   - Reduce jib size                                    │
│              │ • Reduce heel target by 2-3°                           │
└──────────────┴──────────────────────────────────────────────────────────┘
```

---

## 🔧 PLUGIN SIGNAL K: signalk-sails-management

### Données Entrée

```javascript
{
  tws: 12,              // True Wind Speed (knots)
  twa: 65,              // True Wind Angle (degrees)
  heel: 18,             // Heel angle (degrees)
  pitch: 12,            // Pitch angle (degrees)
  roll: 8,              // Roll angle (degrees)
  waveHeight: 1.2,      // Wave height (meters)
  efficiency: 0.92      // Polaire efficiency (ratio)
}
```

### Données Sortie

```javascript
{
  sailConfig: {
    main: "full",         // full, 1reef, 2reef, trysail, down
    jib: "working",       // full/genoa, working, storm, out/poled, down
    spinnaker: "down",    // up, ready, down
    recommendation: "Sailing optimally",
    confidence: 0.95
  },
  
  alerts: [
    {
      type: "SAIL_REDUCTION",
      severity: "warning",
      message: "Consider reducing main (heel 22°, target 20°)",
      action: "REEF_MAIN"
    }
  ],
  
  targets: {
    optimalHeel: 18,      // degrés
    optimalTWA: 50,       // degrés
    optimalTWS: 12        // knots (dans cette plage)
  }
}
```

---

## 💡 LOGIQUE DE DÉCISION

### Step 1: Classer le vent

```javascript
function classifyWind(tws) {
  if (tws < 4) return 'LIGHT';
  if (tws < 7) return 'LIGHT_AIR';
  if (tws < 12) return 'MEDIUM';
  if (tws < 16) return 'FRESH';
  if (tws < 20) return 'STRONG';
  return 'GALE';
}
```

### Step 2: Analyser l'allure

```javascript
function classifyTack(twa) {
  if (twa < 45) return 'BEATING';        // Au près
  if (twa < 90) return 'CLOSE_REACH';    // Petit largue
  if (twa < 120) return 'BEAM_REACH';    // Largue
  if (twa < 160) return 'BROAD_REACH';   // Grand largue
  return 'RUNNING';                      // Vent arrière
}
```

### Step 3: Évaluer l'état de la mer

```javascript
function evaluateSeaState(pitch, roll, waveHeight) {
  let roughness = 0;
  
  if (pitch > 20) roughness += 3;         // Pitch élevé
  if (roll > 25) roughness += 3;          // Roll élevé
  if (waveHeight > 1.5) roughness += 2;   // Vagues
  
  if (roughness < 3) return 'CALM';
  if (roughness < 6) return 'MODERATE';
  return 'ROUGH';
}
```

### Step 4: Recommander configuration

```javascript
function recommendSails(wind, tack, seaState, heel, efficiency) {
  // Base recommendation from wind class
  const config = SAIL_MATRIX[wind][tack] || DEFAULT;
  
  // Adjust for heel
  if (heel > 22) {
    config.action = 'REDUCE_SAIL';  // Too much heel
  }
  
  // Adjust for rough sea
  if (seaState === 'ROUGH') {
    config.main = reduceMain(config.main);
  }
  
  // Adjust for efficiency loss
  if (efficiency < 0.85) {
    config.suggestion = 'Check configuration vs polars';
  }
  
  return config;
}
```

---

## 📈 MATRICE DE DÉCISION COMPLÈTE

### BEATING (TWA < 45°)

| Wind | Light | Light Air | Medium | Fresh | Strong | Gale |
|------|-------|-----------|--------|-------|--------|------|
| Main | Full | Full | Full | 1 Reef | 2 Reef | 2 Reef |
| Jib | Genoa | Full | Working | Working | Working | Storm |
| Heel Target | 12° | 14° | 16° | 18° | 20° | 22° |
| VMG Focus | High | High | High | Stable | Stable | Safety |

### REACHING (45° < TWA < 120°)

| Wind | Light | Light Air | Medium | Fresh | Strong | Gale |
|------|-------|-----------|--------|-------|--------|------|
| Main | Full | Full | Full | Full | 1 Reef | 2 Reef |
| Jib | Genoa | Genoa | Working | Working | Working | Working |
| Heel Target | 15° | 16° | 18° | 20° | 22° | 20° |
| Power | Medium | Medium | High | High | Reduced | Reduced |

### RUNNING (TWA > 160°)

| Wind | Light | Light Air | Medium | Fresh | Strong | Gale |
|------|-------|-----------|--------|-------|--------|------|
| Main | Full | Full | Full | Full | 1 Reef | Down |
| Jib | Out | Out | Out | Out | Poled | Poled |
| Spinnaker | Up | Up | Ready | Down | Down | Down |
| Safety | Low | Low | Medium | High | High | Very High |

---

## 🚀 IMPLÉMENTATION PLUGIN

### Architecture

```javascript
module.exports = function(app) {
  return {
    id: 'signalk-sails-management',
    name: 'Sails Management System',
    
    start() {
      // Subscribe to required inputs
      subscribeToInputs();
      
      // Calculate every 2 seconds
      setInterval(calculateSailRecommendation, 2000);
    },
    
    calculateSailRecommendation() {
      const tws = getTrueWindSpeed();
      const twa = getTrueWindAngle();
      const heel = getHeel();
      const pitch = getPitch();
      const roll = getRoll();
      const efficiency = getEfficiency();
      
      // Classify conditions
      const windClass = classifyWind(tws);
      const tack = classifyTack(twa);
      const seaState = evaluateSeaState(pitch, roll);
      
      // Get recommendation
      const config = recommendSails(
        windClass, tack, seaState, heel, efficiency
      );
      
      // Inject into Signal K
      injectSailConfig(config);
      
      // Generate alerts if needed
      generateAlerts(config, heel, efficiency);
    }
  };
};
```

---

## 📊 SIGNAL K PATHS INJECTÉS

```
navigation.sailing
├─ currentSails
│  ├─ mainsail: "full" | "1reef" | "2reef" | "trysail" | "down"
│  ├─ jib: "full" | "working" | "storm" | "out" | "down"
│  ├─ spinnaker: "up" | "ready" | "down"
│  └─ configuration: "beating" | "reaching" | "running"
│
├─ recommendedSails
│  ├─ mainsail: "recommended config"
│  ├─ jib: "recommended config"
│  ├─ spinnaker: "recommended config"
│  └─ reason: "text explanation"
│
├─ sailMetrics
│  ├─ optimalHeel: 18 (degrees)
│  ├─ heelGap: 2 (actual - optimal)
│  ├─ sailEfficiency: 0.92
│  └─ lastChangeTime: "timestamp"
│
└─ sailAlerts
   ├─ type: "REDUCTION_NEEDED" | "FULL_CANVAS" | "CHANGE_TACK" | "SPINNAKER_UP"
   ├─ severity: "info" | "caution" | "warning" | "critical"
   ├─ message: "text"
   └─ action: "what crew should do"
```

---

## 🎯 CAS D'USAGE

### Cas 1: Crise de vent

```
Conditions:
  TWS: 18kt (gust from 22kt)
  TWA: 60° (beating)
  Heel: 24° (trop!)
  Pitch: 18°

Plugin recommande:
  ❌ Current: Main full + Working Jib
  ✅ Recommended: Main 2 reefs + Working Jib
  
  Alert: "SAIL_REDUCTION (warning)"
  Message: "Heel 24° exceeds safety. Reef main immediately."
  Action: "REEF_MAIN_2X"
```

### Cas 2: Opportunité VMG

```
Conditions:
  TWS: 6kt (light air)
  TWA: 45° (beating)
  Heel: 10° (trop léger!)
  Efficiency: 0.82 (sous-performant)

Plugin recommande:
  ❌ Current: Main full + Working Jib (trop conservateur)
  ✅ Recommended: Main full + Genoa
  
  Alert: "INCREASE_SAIL (info)"
  Message: "Light conditions. Genoa up = better VMG."
  Action: "RAISE_GENOA"
```

### Cas 3: Changement allure

```
Conditions:
  TWA changes: 45° → 140° (beating → broad reach)
  TWS: 10kt (stable)
  
Plugin détecte:
  ❌ Current: Main + Working Jib (beating config)
  ✅ Recommended: Main + Jib out (reaching config)
  
  Alert: "CONFIG_CHANGE"
  Message: "Now on broad reach. Ease main, jib out."
  Action: "ADJUST_REACH"
```

---

## ⚙️ PARAMÈTRES CONFIGURABLES

```json
{
  "heelSafetyLimit": 22,           // Max heel avant alerte
  "heelOptimalTarget": 18,         // Target heel (moyen)
  "efficencyThreshold": 0.85,      // Alert si < this
  "roughSeaPitchLimit": 20,        // Degrees
  "roughSeaRollLimit": 25,         // Degrees
  "windChangeThreshold": 2,        // kt avant reconfig
  "updateInterval": 2000,          // ms
  "debug": false
}
```

---

## 📚 DONNÉES J/30

### Voiles Disponibles

| Voile | Taille | Usage |
|-------|--------|-------|
| Mainsail | 200 sq ft | All conditions |
| Genoa | 180 sq ft | Light air (< 12kt) |
| Working Jib | 120 sq ft | Medium-fresh (7-18kt) |
| Storm Jib | 60 sq ft | Strong-gale (16-25kt) |
| Spinnaker | 250 sq ft | Downwind light-medium (< 18kt) |

### Réductions de Voile (Mainsail)

| Config | Size | Usage |
|--------|------|-------|
| Full | 200 sq ft | < 16kt |
| 1 Reef | 160 sq ft | 12-20kt |
| 2 Reefs | 120 sq ft | 16-25kt |
| Trysail | 80 sq ft | Gale (> 25kt) |

---

## 🧪 TESTS

### Test 1: Condition légère

```bash
# Input
tws=5, twa=45, heel=10, pitch=5, roll=3, efficiency=0.85

# Expected output
Main: Full, Jib: Genoa
Alert: none (optimal light air)
```

### Test 2: Crise vent

```bash
# Input
tws=20, twa=60, heel=25, pitch=18, roll=12, efficiency=0.88

# Expected output
Main: 2 Reefs, Jib: Working
Alert: SAIL_REDUCTION (warning)
Action: REEF_MAIN
```

### Test 3: Downwind

```bash
# Input
tws=8, twa=170, heel=12, pitch=6, roll=8, efficiency=0.90

# Expected output
Main: Full, Jib: Out, Spinnaker: Up
Alert: none (optimal downwind)
```

---

## 📝 PROCHAINES ÉTAPES

### Phase 1 (Cette semaine): Plugin Core
- [ ] Créer plugin JavaScript
- [ ] Implémenter logique décision
- [ ] Tester avec cas de base
- [ ] Injecter dans Signal K

### Phase 2 (Semaine 2): Intégration
- [ ] Connecter aux MCP tools
- [ ] Créer alertes Grafana
- [ ] Tester en bateau condition légère

### Phase 3 (Semaine 3-4): Affinage
- [ ] Collecter feedback équipage
- [ ] Ajuster seuils
- [ ] Tester conditions diverses
- [ ] Production deployment

---

## 📊 GRAFANA INTEGRATION

### Dashboard "Sail Management"

```
┌─────────────────────────────────────────────┐
│ CURRENT CONFIGURATION vs RECOMMENDED        │
├─────────────────────────────────────────────┤
│                                             │
│ ✓ Main: Full              Main: Full        │
│ ✓ Jib: Working           Jib: Working      │
│ ○ Spi: Down              Spi: Down         │
│                           Heel Target: 18° │
│                                             │
├─────────────────────────────────────────────┤
│ SAIL EFFICIENCY METRICS                     │
│                                             │
│ Heel: 17° (target 18°) ✓                   │
│ Performance: 92% of polar ✓                 │
│ Last change: 15 minutes ago                │
│                                             │
├─────────────────────────────────────────────┤
│ ALERTS & RECOMMENDATIONS                    │
│                                             │
│ • Light air: Consider genoa (VMG +0.3kt)  │
│ • Wind shift: Trim main, adjust heel      │
│                                             │
└─────────────────────────────────────────────┘
```

---

## ✅ CHECKPOINTS

- [ ] Plugin créé et syntaxe valide
- [ ] Tous les paths Signal K injectés
- [ ] Données polaires chargées
- [ ] Alertes générées correctement
- [ ] MCP tools lisent les données
- [ ] Grafana affiche recommandations
- [ ] Test en bateau condition légère
- [ ] Test en bateau condition fraîche
- [ ] Production ready

---

**Status:** ✅ Architecture validée  
**Effort:** 8-12 heures (2-3 semaines spread)  
**Impact:** Intelligent sail management system  
**Ready for:** Development start

---

**Ready to build?** 🚀⛵

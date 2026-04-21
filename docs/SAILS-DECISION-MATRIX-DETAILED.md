# ⛵ MATRICE DE DÉCISION VOILES — DÉTAIL COMPLET

**Date:** 2026-04-20  
**Purpose:** Guide complet pour le système de gestion des voiles  
**Format:** Détail ligne par ligne + logique JavaScript

---

## 🎯 STRUCTURE GÉNÉRALE

```
           WIND CLASS (force)
           ↓
[Light | Light Air | Medium | Fresh | Strong | Gale]
           ↓
     + TACK CLASS (allure)
           ↓
[Beating | Close Reach | Beam Reach | Broad Reach | Running]
           ↓
     + SEA STATE (état mer)
           ↓
[Calm | Moderate | Rough]
           ↓
     = SAIL CONFIGURATION
           ↓
[Main Sail | Jib | Spinnaker | Heel Target]
```

---

## 📊 CLASSIFICATION PAR VENT (TWS — True Wind Speed)

### Définitions

```javascript
function classifyWind(tws) {
  if (tws < 4) return 'LIGHT';           // < 4kt
  if (tws < 7) return 'LIGHT_AIR';       // 4-6kt
  if (tws < 12) return 'MEDIUM';         // 7-11kt
  if (tws < 16) return 'FRESH';          // 12-15kt
  if (tws < 20) return 'STRONG';         // 16-19kt
  return 'GALE';                         // >= 20kt
}
```

### Tableau des Forces

| Wind Class | TWS Range | Beaufort | Conditions | Typical |
|------------|-----------|----------|-----------|---------|
| LIGHT | < 4kt | 0-1 | Très peu de vent, très difficile | Rare en régate |
| LIGHT_AIR | 4-6kt | 2 | Vent léger, bonne portance | Été après pluie |
| MEDIUM | 7-11kt | 3-4 | Vent agréable, conditions normales | Idéal pour course |
| FRESH | 12-15kt | 5 | Vent frais, bonne puissance | Après-midi normal |
| STRONG | 16-19kt | 6 | Vent fort, demande du travail | Été orageux |
| GALE | >= 20kt | 7-8 | Grand frais, très demandant | Tempête légère |

---

## 🧭 CLASSIFICATION PAR ALLURE (TWA — True Wind Angle)

### Définitions

```javascript
function classifyTack(twa) {
  if (twa < 45) return 'BEATING';         // 0-44° (près)
  if (twa < 90) return 'CLOSE_REACH';     // 45-89° (petit largue)
  if (twa < 120) return 'BEAM_REACH';     // 90-119° (largue)
  if (twa < 160) return 'BROAD_REACH';    // 120-159° (grand largue)
  return 'RUNNING';                       // 160-180° (vent arrière)
}
```

### Tableau des Allures

| Tack | TWA Range | Sailing Description | Characteristics |
|------|-----------|-------------------|-----------------|
| BEATING | 0-44° | Au près | Maximum upwind, best VMG angle, heel oriented |
| CLOSE_REACH | 45-89° | Petit largue | Still upwind, good performance, heel key |
| BEAM_REACH | 90-119° | Largue | Perpendicular to wind, high speed possible, power-oriented |
| BROAD_REACH | 120-159° | Grand largue | Downwind start, can hoist spinnaker if light, power/stability balance |
| RUNNING | 160-180° | Vent arrière | Pure downwind, spinnaker optimal if conditions allow, wing-on-wing alternative |

---

## 🌊 CLASSIFICATION PAR ÉTAT DE MER (SEA STATE)

### Définitions

```javascript
function evaluateSeaState(pitch, roll, waveHeight) {
  let roughness = 0;
  
  // Pitch contribution
  if (pitch < 10) roughness += 0;      // Calm
  if (pitch < 15) roughness += 1;      // Light
  if (pitch < 20) roughness += 2;      // Moderate
  if (pitch >= 20) roughness += 3;     // Rough
  
  // Roll contribution
  if (roll < 8) roughness += 0;        // Calm
  if (roll < 15) roughness += 1;       // Light
  if (roll < 25) roughness += 2;       // Moderate
  if (roll >= 25) roughness += 3;      // Rough
  
  // Wave height contribution
  if (waveHeight < 0.5) roughness += 0;   // Calm
  if (waveHeight < 1.0) roughness += 1;   // Light
  if (waveHeight < 1.5) roughness += 1;   // Moderate
  if (waveHeight >= 1.5) roughness += 2;  // Rough
  
  if (roughness <= 2) return 'CALM';
  if (roughness <= 4) return 'MODERATE';
  return 'ROUGH';
}
```

### Tableau des États Mer

| Sea State | Pitch | Roll | Wave Ht | Effect on Sails |
|-----------|-------|------|---------|-----------------|
| CALM | < 10° | < 8° | < 0.5m | Ideal, full canvas |
| MODERATE | 10-20° | 8-25° | 0.5-1.5m | Manageable, normal config |
| ROUGH | > 20° | > 25° | > 1.5m | Reduce sail, stability crucial |

---

## 📋 MATRICE COMPLÈTE: BEATING (Au Près — TWA < 45°)

### Définition
Au près = angle optimal pour remonter le vent
- Focus: Meilleur VMG (Velocity Made Good)
- Heel: 15-20° optimal, > 22° problématique
- Safety: Grande voile réductible immédiatement

### La Matrice

```
BEATING (TWA < 45°)
════════════════════════════════════════════════════════════════════════════

                LIGHT    LIGHT_AIR  MEDIUM    FRESH     STRONG    GALE
                <4kt     4-6kt      7-11kt    12-15kt   16-19kt   >=20kt
────────────────────────────────────────────────────────────────────────────
MAIN            Full     Full       Full      1 Reef    2 Reefs   2 Reefs
────────────────────────────────────────────────────────────────────────────
JIB             Genoa    Full       Working   Working   Working   Storm
────────────────────────────────────────────────────────────────────────────
SPINNAKER       Down     Down       Down      Down      Down      Down
────────────────────────────────────────────────────────────────────────────
HEEL TARGET     12°      14°        16°       18°       20°       22°
────────────────────────────────────────────────────────────────────────────
FOCUS           VMG      VMG        VMG       Stable    Stable    Safety
────────────────────────────────────────────────────────────────────────────
COMMENTS        Rare     Light air  Ideal     Adjust    Demands   Extreme
                          - needs   - balance  power     crew work
                          full sail  heel
────────────────────────────────────────────────────────────────────────────
```

### Détail Ligne par Ligne

#### MAIN (Grande Voile)

| Wind | Config | Why | Handling | Notes |
|------|--------|-----|----------|-------|
| LIGHT | Full | Need max area | Easy | Rare, need full genoa too |
| LIGHT_AIR | Full | VMG priority | Easy | Good conditions |
| MEDIUM | Full | Ideal power | Normal | Standard beating |
| FRESH | 1 Reef | Heel control | Moderate | Heel approaching 18° |
| STRONG | 2 Reefs | Safety | Harder | Heel > 20°, needs crew |
| GALE | 2 Reefs | Survival | Hard | Extreme conditions |

**Logique de Décision:**
```javascript
if (tws < 12 && heel < 16) {
  main = 'FULL';           // Light conditions
} else if (tws < 16 && heel < 18) {
  main = 'FULL';           // Medium, well-controlled
} else if (tws < 16 && heel > 18) {
  main = '1_REEF';         // Heel building, reduce early
} else if (tws < 20) {
  main = '2_REEFS';        // Fresh, strong conditions
} else {
  main = '2_REEFS';        // Gale = minimal sail
}
```

#### JIB (Petit Voile)

| Wind | Config | Why | VMG Gain | Notes |
|------|--------|-----|----------|-------|
| LIGHT | Genoa | Max area (180 sq ft) | +0.3kt | Best upwind |
| LIGHT_AIR | Full | Good balance | +0.2kt | Almost genoa |
| MEDIUM | Working | Good control | 0kt baseline | Standard |
| FRESH | Working | Manageable heel | 0kt | Stable setup |
| STRONG | Working | Control crucial | 0kt | No change needed |
| GALE | Storm | Minimal & safe | 0kt | Last resort |

**Logique de Décision:**
```javascript
if (tws < 7 && efficiency < 0.90) {
  jib = 'GENOA';           // Light air = bigger jib needed
} else if (tws < 12 && efficiency < 0.90) {
  jib = 'FULL_JIB';        // Marginal gain but light enough
} else if (tws < 16) {
  jib = 'WORKING_JIB';     // Medium+ = working jib standard
} else if (tws < 20) {
  jib = 'WORKING_JIB';     // Strong = no change
} else {
  jib = 'STORM_JIB';       // Gale = minimal sail
}
```

#### HEEL TARGET (Angle de Gîte Cible)

| Wind | Target | Why | Safety Margin | Notes |
|------|--------|-----|----------------|-------|
| LIGHT | 12° | Need lateral stability | 10° margin | Light air instability |
| LIGHT_AIR | 14° | VMG optimization | 8° margin | Balance power/stability |
| MEDIUM | 16° | Optimal performance | 6° margin | Sweet spot |
| FRESH | 18° | Power + control | 4° margin | Getting critical |
| STRONG | 20° | Limit approaches | 2° margin | Conservative |
| GALE | 22° | Absolute safety | 0° margin | Hard limit |

**Logique de Décision:**
```javascript
const heelTargets = {
  'LIGHT': 12,
  'LIGHT_AIR': 14,
  'MEDIUM': 16,
  'FRESH': 18,
  'STRONG': 20,
  'GALE': 22
};

let target = heelTargets[windClass];

// Adjust for sea state
if (seaState === 'ROUGH') {
  target -= 2;              // Conservative in rough seas
}

// Alert if approaching safety
if (actualHeel > target + 2) {
  alert('HEEL_HIGH', 'approaching target limit');
}
if (actualHeel > 24) {
  alert('HEEL_CRITICAL', 'safety exceeded, action needed NOW');
}
```

#### FOCUS (Priorité Système)

| Wind | Focus | Means | Example |
|------|-------|-------|---------|
| LIGHT | VMG | Maximize speed upwind | Genoa for +0.3kt |
| LIGHT_AIR | VMG | Same | Need full sail area |
| MEDIUM | VMG | Balanced sailing | Good efficiency |
| FRESH | Stability | Control heel | Reef if heel > 18° |
| STRONG | Stability | Same | Heel < 20° priority |
| GALE | Safety | Survival mode | Minimize heel at all costs |

---

## 📋 MATRICE COMPLÈTE: REACHING (Largue — 45° < TWA < 120°)

### Définition
Largue = angle perpendiculaire au vent (ou près)
- Focus: Meilleur VMG (varie avec angle)
- Heel: 16-20° optimal, > 22° problématique
- Spinnaker: Possible en largue par vent faible

### La Matrice

```
REACHING (45° < TWA < 120°)
════════════════════════════════════════════════════════════════════════════

                LIGHT    LIGHT_AIR  MEDIUM    FRESH     STRONG    GALE
                <4kt     4-6kt      7-11kt    12-15kt   16-19kt   >=20kt
────────────────────────────────────────────────────────────────────────────
MAIN            Full     Full       Full      Full      1 Reef    2 Reefs
────────────────────────────────────────────────────────────────────────────
JIB             Genoa    Genoa      Working   Working   Working   Working
────────────────────────────────────────────────────────────────────────────
SPINNAKER       Ready    Up         Ready     Down      Down      Down
────────────────────────────────────────────────────────────────────────────
HEEL TARGET     15°      16°        18°       20°       22°       20°
────────────────────────────────────────────────────────────────────────────
FOCUS           Power    Power      Power     Balance   Reduce    Safety
────────────────────────────────────────────────────────────────────────────
COMMENTS        Rare     Good reach Ideal     Normal    Conservative Extreme
────────────────────────────────────────────────────────────────────────────
```

### Détail Key Changes from Beating

#### MAIN: Differences from Beating

| Wind | Beating | Reaching | Why |
|------|---------|----------|-----|
| LIGHT | Full | Full | Same (good power either way) |
| LIGHT_AIR | Full | Full | Same |
| MEDIUM | Full | Full | Reaching needs more power, easier to control heel |
| FRESH | 1 Reef | Full | Can sail full main on reach (different angle) |
| STRONG | 2 Reefs | 1 Reef | More forgiving angle on reach |
| GALE | 2 Reefs | 2 Reefs | Same safety requirement |

**Logique:**
```javascript
// Reaching is more forgiving (wind at 90°, not 45°)
// So can often carry more sail than beating

if (tws < 16) {
  main = 'FULL';           // Can usually do full on reach
} else if (tws < 20) {
  main = '1_REEF';         // One reef for control
} else {
  main = '2_REEFS';        // Gale = reduced anyway
}
```

#### JIB: Differences from Beating

| Wind | Beating | Reaching | Why |
|------|---------|----------|-----|
| LIGHT | Genoa | Genoa | Same (power needed) |
| LIGHT_AIR | Full | Genoa | Reaching even more power-hungry |
| MEDIUM | Working | Working | Same balanced approach |
| FRESH | Working | Working | Same |
| STRONG | Working | Working | Same |
| GALE | Storm | Working | Reaching = slightly better control |

**Logique:**
```javascript
// Reaching needs power (less efficient angle than beating)
// So bigger jib on reach vs beating for same heel

if (tws < 12) {
  jib = 'GENOA';           // Light reach = power needed
} else {
  jib = 'WORKING_JIB';     // Fresh+ = control
}
```

#### SPINNAKER: New Decision Factor!

| Wind | Status | Why | Safety |
|------|--------|-----|--------|
| LIGHT | Ready | Can hoist (but rare) | Very low risk |
| LIGHT_AIR | Up | Good reaching with spi | Safe, light wind |
| MEDIUM | Ready | Possible but optional | Moderate wind okay |
| FRESH | Down | Too much power | Risk of gybe/broach |
| STRONG | Down | Absolutely not | Dangerous |
| GALE | Down | Never | Survival mode |

**Logique:**
```javascript
function shouldHoistSpinnaker(tws, twa, heel, stability) {
  // Spinnaker only on reach/broad reach
  if (twa < 90 || twa > 160) return false;
  
  // Only in light conditions
  if (tws > 16) return false;
  
  // Must be stable
  if (stability === 'UNSTABLE') return false;
  
  // Must not exceed power
  if (heel > 20) return false;
  
  return true;  // Conditions optimal for spinnaker
}
```

---

## 📋 MATRICE COMPLÈTE: RUNNING (Vent Arrière — TWA > 160°)

### Définition
Vent arrière = course quasi directement sous le vent
- Focus: Spinnaker optimal si conditions permettent, sinon jib out
- Heel: 12-18° pour stabilité, > 22° danger de gybe involontaire
- Spinnaker: Maximum power upside, HIGH risk (accidental jibe)

### La Matrice

```
RUNNING (TWA > 160°)
════════════════════════════════════════════════════════════════════════════

                LIGHT    LIGHT_AIR  MEDIUM    FRESH     STRONG    GALE
                <4kt     4-6kt      7-11kt    12-15kt   16-19kt   >=20kt
────────────────────────────────────────────────────────────────────────────
MAIN            Full     Full       Full      Full      1 Reef    Down
────────────────────────────────────────────────────────────────────────────
JIB             Out      Out        Out       Out       Poled     Poled
────────────────────────────────────────────────────────────────────────────
SPINNAKER       Up       Up         Ready     Down      Down      Down
────────────────────────────────────────────────────────────────────────────
HEEL TARGET     12°      13°        15°       16°       18°       14°
────────────────────────────────────────────────────────────────────────────
FOCUS           VMG      VMG        Power     Control   Control   Safety
────────────────────────────────────────────────────────────────────────────
RIGGING         Wing-on  Wing-on    Spi       Spi pole  Spi/pole  Poled
────────────────────────────────────────────────────────────────────────────
COMMENTS        Speed    Speed      Optimal   Spicy     Demanding Bare poles
────────────────────────────────────────────────────────────────────────────
```

### Détail Key Differences from Beating/Reaching

#### MAIN: Completely Different

| Wind | Beating | Reaching | Running | Comment |
|------|---------|----------|---------|---------|
| LIGHT | Full | Full | Full | Same sail, different angle |
| LIGHT_AIR | Full | Full | Full | Maximum power |
| MEDIUM | Full | Full | Full | Full power downwind |
| FRESH | 1 Reef | Full | Full | Running less demanding? No! |
| STRONG | 2 Reefs | 1 Reef | 1 Reef | Downwind still powerful |
| GALE | 2 Reefs | 2 Reefs | Down | Extreme = furl main completely |

**Why Running is Actually Harder:**
```javascript
// Running looks easier (downwind) but ISN'T
// Reasons:
// 1. Accidental jibe = catastrophic (boom crosses violently)
// 2. Broad-reaching means 180° swing if wind shifts
// 3. Spinnaker more powerful on reach than beat
// 4. Loss of aerodynamic lift (dead air)
// 5. Rolling motion more pronounced

// So we often REDUCE more on running than other points!
```

#### JIB: Strategic Placement

| Wind | Config | Placement | Why |
|------|--------|-----------|-----|
| LIGHT | Out | Opposite main | Wing-on-wing, balance |
| LIGHT_AIR | Out | Opposite main | Same, smooth running |
| MEDIUM | Out | Opposite main | Still wing-on-wing (if no spi) |
| FRESH | Out | Poled out (if spi) | Stabilize if spinnaker up |
| STRONG | Poled | Pole rigger's job | Control rolling |
| GALE | Poled | Poled small | Stability critical |

**Logique:**
```javascript
if (hasSpiUp === true) {
  jib = 'POLED_OUT';       // Stabilizes spi rolling
} else {
  jib = 'WING_ON_WING';    // Opposite to main
}
```

#### SPINNAKER: Maximum Decision Point!

| Wind | Status | Why | Risk Level | Crew Needed |
|------|--------|-----|------------|------------|
| LIGHT | Up | Perfect conditions | Very Low | 1-2 trained |
| LIGHT_AIR | Up | Ideal, stable | Low | 1-2 trained |
| MEDIUM | Ready | Can hoist if experienced | Medium | 2-3 trained |
| FRESH | Down | Too powerful + gybe risk | High | 3+ crew needed |
| STRONG | Down | Absolute not | Very High | Danger zone |
| GALE | Down | Never ever | Extreme | Bare poles only |

**Logique Détaillée:**
```javascript
function shouldHoistSpinnaker(tws, twa, heel, gust, crew_experience) {
  // Must be running
  if (twa < 160) return false;
  
  // Wind limits
  if (tws > 16) return false;              // Too much power
  if (gusts > 18) return false;            // Gust risk
  
  // Heel limits
  if (heel > 20) return false;             // Already heeled
  
  // Crew skill
  if (crew_experience < 'INTERMEDIATE') {
    if (tws > 10) return false;            // Need skill for med+ wind
  }
  
  // Stability check
  if (roll > 25) return false;             // Too much motion
  
  return true;  // Safe to hoist
}

// Douse criteria (even tighter!)
function shouldDoueSpinnaker(tws, twa, heel, gust, stability) {
  // ANY of these = DOUSE NOW
  if (gusts > 18) return true;             // Gust spike
  if (heel > 22) return true;              // Excessive heel
  if (stability === 'UNSTABLE') return true; // Rolling too much
  if (twa < 150) return true;              // Jibing risk
  
  // Lower threshold = douse sooner than hoist
  return false;
}
```

---

## 🎓 LOGIQUE IMPLÉMENTATION (Pseudocode Complet)

```javascript
function recommendSailConfig(tws, twa, heel, pitch, roll, waveHeight, efficiency) {
  
  // Step 1: Classify conditions
  const windClass = classifyWind(tws);
  const tackClass = classifyTack(twa);
  const seaState = evaluateSeaState(pitch, roll, waveHeight);
  
  // Step 2: Get base config from matrix
  const config = SAIL_MATRIX[tackClass][windClass];
  
  // Step 3: Adjust for sea state
  if (seaState === 'ROUGH') {
    if (config.main === 'FULL') config.main = '1_REEF';      // Reduce 1 point
    if (config.main === '1_REEF') config.main = '2_REEFS';   // Reduce another
    config.heelTarget -= 2;                                   // Conservative
  }
  
  // Step 4: Override for heel
  if (heel > config.heelTarget + 2) {
    // Heel is high - reduce sail
    config.alerts.push({
      type: 'SAIL_REDUCTION',
      severity: heel > 24 ? 'CRITICAL' : 'WARNING',
      action: reduceSail(config)
    });
  }
  
  // Step 5: Check efficiency
  if (efficiency < 0.85 && tws < 16 && seaState !== 'ROUGH') {
    config.alerts.push({
      type: 'SAIL_INCREASE',
      severity: 'INFO',
      suggestion: increaseSail(config)
    });
  }
  
  // Step 6: Spinnaker decision (if applicable)
  if (tackClass === 'BROAD_REACH' || tackClass === 'RUNNING') {
    if (shouldHoistSpinnaker(tws, twa, heel, stability)) {
      config.spinnaker = 'UP';
      config.alerts.push({
        type: 'SPINNAKER_UP',
        severity: 'INFO',
        message: 'Conditions optimal for spinnaker'
      });
    } else if (config.spinnaker === 'UP' && shouldDoueSpinnaker(...)) {
      config.spinnaker = 'DOWN';
      config.alerts.push({
        type: 'SPINNAKER_DOWN',
        severity: 'WARNING',
        action: 'Douse spinnaker immediately'
      });
    }
  }
  
  return {
    sailConfig: config,
    alerts: config.alerts,
    confidence: calculateConfidence(...)
  };
}
```

---

## 🧮 EXEMPLE EXÉCUTION PAS À PAS

### Scénario: "12 knots, beating 55°, heel 18°, pitch 12°, roll 10°, waves 0.8m"

```
Input:
  tws = 12kt
  twa = 55°
  heel = 18°
  pitch = 12°
  roll = 10°
  waveHeight = 0.8m
  efficiency = 0.89

Step 1: Classify
  windClass = MEDIUM (7-11kt? NO → 12-15kt = FRESH? NO)
  Actually TWS 12 → falls in MEDIUM boundary...
  Let's say: windClass = MEDIUM (11.99kt rounds down)
  tackClass = CLOSE_REACH (45-89°, we're at 55°)
  seaState = MODERATE (pitch 12 + roll 10 = moderate)

Step 2: Matrix Lookup [CLOSE_REACH][MEDIUM]
  main = FULL
  jib = WORKING
  heel_target = 16°
  focus = VMG

Step 3: Adjust for Sea State
  seaState = MODERATE (not rough)
  → No adjustment needed

Step 4: Override for Heel
  actual_heel (18°) > target (16°) + buffer (1°)
  → heel is slightly high
  → Alert: "HEEL_SLIGHTLY_HIGH"
  → Consider reducing if sustained

Step 5: Check Efficiency
  efficiency = 0.89 → acceptable (>0.85)
  → No alarm

Step 6: Spinnaker
  tactClass = CLOSE_REACH (not broad/running)
  → Spinnaker not applicable
  → Stay DOWN

RESULT:
  Main: FULL ✓
  Jib: WORKING ✓
  Heel Target: 16°
  Actual Heel: 18° (within 2°, acceptable)
  Alerts: None (slight heel monitoring)
  Message: "Good sailing, monitor heel if wind increases"
```

---

## 📊 TRANSITION EXAMPLES

### Transition 1: Vent Augmente (7kt → 14kt)

```
BEFORE:
  Wind: 7kt (LIGHT_AIR)
  Tack: BEATING
  Config: Full main + Genoa, heel target 14°

CHANGE:
  Wind: 14kt (FRESH)
  Tack: BEATING (same direction)

AFTER:
  Config: Full main + Working jib, heel target 18°
  Alert: "Wind increasing. Switch Genoa to Working jib"
  Crew Action: Drop genoa, raise working jib (practiced maneuver ~2 min)
```

### Transition 2: Changement d'Allure (Beating → Running)

```
BEFORE:
  Tack: BEATING (55°)
  Config: Full main + Working jib, heel 16°

CHANGE:
  Tack: RUNNING (170°)
  Wind: 10kt (stable)

AFTER:
  Config: Full main + Jib out + Spinnaker UP, heel target 13°
  Alert: "Tack change to running. Prepare for spinnaker"
  Crew Action: 
    1. Release jib sheet
    2. Pole out jib
    3. Hoist spinnaker (if confident)
    4. Wing-on-wing configuration
```

### Transition 3: Crise Vent (14kt → 20kt gust)

```
BEFORE:
  Wind: 14kt (FRESH)
  Config: Full main + Working jib, heel 18°

SUDDEN GUST:
  Wind: 22kt for 30 seconds

DURING GUST:
  Heel: 24° (exceeds safety!)
  Alert (CRITICAL): "Heel 24°. Reef main NOW!"

CREW RESPONSE:
  1. Helmsman pinches up (reduces heel)
  2. Trim main (tighten outhaul, vang)
  3. Sheet in jib (if not already)
  4. Reef main (point of ris) — 2 minutes
  → Heel drops to 19° ✓

AFTER GUST:
  Wind: 16kt (STRONG)
  Config: Now 1 Reef + Working jib, heel 19°
  System says: "REEF_MAIN done correctly"
```

---

## 🚨 ALERT RULES DÉFINIES

### Alert Triggers (JavaScript)

```javascript
const ALERT_RULES = {
  HEEL_HIGH: {
    trigger: () => heel > heelTarget + 2,
    severity: 'WARNING',
    message: `Heel ${heel.toFixed(0)}° exceeds target ${heelTarget}°`
  },
  
  HEEL_CRITICAL: {
    trigger: () => heel > 24,
    severity: 'CRITICAL',
    message: `Heel ${heel.toFixed(0)}° CRITICAL! Reduce sail NOW!`,
    action: 'REDUCE_SAIL_IMMEDIATELY'
  },
  
  EFFICIENCY_LOW: {
    trigger: () => efficiency < 0.85 && tws < 16 && seaState !== 'ROUGH',
    severity: 'INFO',
    message: 'Efficiency low. Consider different sail config',
    suggestion: 'Raise Genoa (light air)' or 'Check trim'
  },
  
  SPINNAKER_UP: {
    trigger: () => shouldHoistSpinnaker(...),
    severity: 'INFO',
    message: 'Conditions optimal for spinnaker',
    action: 'HOIST_SPINNAKER'
  },
  
  SPINNAKER_DOWN: {
    trigger: () => shouldDouseSpinnaker(...),
    severity: 'WARNING',
    message: 'Spinnaker conditions degrading. Douse soon',
    action: 'DOUSE_SPINNAKER'
  },
  
  REEF_MAIN: {
    trigger: () => tws > 14 && main === 'FULL',
    severity: 'CAUTION',
    message: `Wind ${tws}kt sustained. Consider reef`,
    action: 'REEF_MAIN_1'
  },
  
  UNREEF: {
    trigger: () => tws < 10 && main !== 'FULL',
    severity: 'INFO',
    message: `Wind dropped to ${tws}kt. Can unreef`,
    action: 'UNREEF_MAIN'
  }
};
```

---

## 📈 CONFIDENCE SCORING

```javascript
function calculateConfidence(windClass, seaState, heel_error, efficiency_match) {
  let confidence = 1.0;  // Start at 100%
  
  // Reduce confidence if conditions are chaotic
  if (windClass === 'GALE') confidence *= 0.9;  // Gale = less predictable
  if (seaState === 'ROUGH') confidence *= 0.9;  // Rough sea = harder to control
  
  // Reduce if heel error is large
  const heelError = Math.abs(actualHeel - heelTarget);
  if (heelError > 5) confidence *= 0.95;
  if (heelError > 10) confidence *= 0.85;
  
  // Reduce if efficiency mismatch
  if (Math.abs(efficiency - 0.92) > 0.1) confidence *= 0.9;
  
  return Math.max(confidence, 0.65);  // Never below 65%
}
```

---

## 🎓 CHEAT SHEET RAPIDE

### Light Air (< 7kt)
```
→ Max sail (Genoa, Full main)
→ Focus: VMG
→ Heel target: 12-14°
→ Watch: Under-powered, heel too light
```

### Medium (7-12kt)
```
→ Balanced sail (Working jib, Full main)
→ Focus: VMG
→ Heel target: 16-18°
→ Watch: Efficiency vs polars
```

### Fresh (12-16kt)
```
→ Reduce slightly (Working jib, Full main sometimes)
→ Focus: Stable heel
→ Heel target: 18°
→ Watch: Heel creeping up
```

### Strong (16-20kt)
```
→ Reef main, standard jib
→ Focus: Heel control
→ Heel target: 20°
→ Watch: Gusts, safety limit
```

### Gale (> 20kt)
```
→ Minimal sail (2 reefs, storm jib)
→ Focus: SAFETY
→ Heel target: 22° (absolute max!)
→ Watch: Anything above 22° = critical
```

---

## ✅ CHECKLIST POUR IMPLÉMENTATION

- [ ] Code classifyWind()
- [ ] Code classifyTack()
- [ ] Code evaluateSeaState()
- [ ] Build SAIL_MATRIX[tack][wind]
- [ ] Implement heel override logic
- [ ] Implement efficiency check
- [ ] Implement spinnaker logic
- [ ] Add alert rules
- [ ] Calculate confidence score
- [ ] Test with 10+ scenarios
- [ ] Deploy to Signal K

---

**Ready to code the system?** 🚀⛵


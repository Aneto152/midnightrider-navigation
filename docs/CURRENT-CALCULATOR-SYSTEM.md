# Current Calculator System — Signal K Plugin

**Date:** 2026-04-21  
**Bateau:** J/30 MidnightRider  
**Plugin:** signalk-current-calculator  
**Purpose:** Calculate water current (speed + direction) from GPS and loch data

---

## 📋 Vue d'ensemble

Le courant marin est invisible mais critique pour la navigation. Ce plugin le **calcule automatiquement** à partir de:
- **GPS** (position réelle, SOG/COG)
- **Loch calibré** (vitesse bateau dans l'eau, STW)
- **Heading** (cap du bateau)

### Principecompute
```
GPS shows where bateau actually goes
Loch shows how fast bateau moves through water
The difference = courant marin
```

### Équation vectorielle
```
GPS_velocity = STW_velocity + Current_velocity

Therefore:
Current = GPS_velocity - STW_velocity (soustraction vectorielle)
```

---

## 🎯 Inputs Requis

Pour fonctionner, le plugin a besoin de:

| Input | Path | Source | Status |
|-------|------|--------|--------|
| **SOG** | navigation.speedOverGround | GPS UM982 | ✅ Disponible |
| **COG** | navigation.courseOverGroundTrue | GPS UM982 | ✅ Disponible |
| **STW** | navigation.speedThroughWater | Loch calibré | ⏳ Quand hardware |
| **Heading** | navigation.headingTrue | GPS UM982 | ⚠️ Issue (0.0°) |

**Statut:** 3/4 inputs disponibles → Plugin peut démarrer avec données partielles

---

## 📊 Outputs Générés

Le plugin génère 5 paths Signal K:

### Vitesse du courant
```
environment.water.currentSpeed (m/s)
• 0.0 = pas de courant
• 0.5 = 1 knot de courant
• 1.0 = ~2 knots
```

### Direction du courant
```
environment.water.currentDirection (radians, 0-2π)
environment.water.currentDirectionTrue (même chose)
• 0 = vers l'est
• π/2 = vers le nord
• π = vers l'ouest
• 3π/2 = vers le sud
```

### Dérive latérale (Leeway)
```
navigation.performance.leeway (radians)
navigation.performance.driftAngle (même chose)
• Positive = dérive à tribord (heading > COG)
• Négatif = dérive à bâbord (heading < COG)
• Exemple: +0.17 rad = +10° (bateau dériv à tribord)
```

---

## 🧮 Théorie Mathématique

### Décomposition vectorielle

```
Step 1: Convert STW + Heading → Boat velocity in earth frame
   V_boat_through_water = [STW * cos(heading), STW * sin(heading)]

Step 2: Convert SOG + COG → Actual velocity in earth frame
   V_boat_over_ground = [SOG * cos(COG), SOG * sin(COG)]

Step 3: Calculate current = GPS - STW
   V_current = V_boat_over_ground - V_boat_through_water
             = [SOG*cos(COG) - STW*cos(heading), SOG*sin(COG) - STW*sin(heading)]

Step 4: Convert back to polar form
   CurrentSpeed = sqrt(Vx² + Vy²)
   CurrentDir = atan2(Vy, Vx)
```

### Leeway (dérive latérale)

```
Leeway = COG - Heading (smallest arc)
• Si positive: bateau dériv à droite
• Si négative: bateau dériv à gauche

Exemple:
  Heading = 330° (NW)
  COG = 340° (NW)
  Leeway = +10° (dérive à droite, courant tire à tribord)
```

---

## 🎨 Exemple Visuel (Navigation)

```
Bateau en route au près:

Heading: 330° (cap au NW, vers la marque)
STW: 5.0 knots (vitesse loch)
Courant: 1.0 knot vers 045° (NE)
GPS SOG: 5.1 knots
GPS COG: 340° (réelle direction)
Leeway: +10° (dérive à tribord, vers le courant)

Interprétation:
  Bateau veut aller à 330° mais courant le tire à 045°
  Résultat: dérive de 10° à droite
  Bateau doit anticiper et lofer de 10° (cap = 320°)
```

---

## ⚙️ Configuration

**File:** `/home/aneto/.signalk/plugin-config-data/signalk-current-calculator.json`

### Paramètres clés

```json
{
  "validation": {
    "minSOG": 0.5,           // Ignore si < 0.5 m/s (trop lent)
    "maxCurrentSpeed": 3.0,  // Rejette si > 3 m/s (erreur probable)
    "minSTW": 0.1,           // Ignore si < 0.1 m/s (loch ne fonctionne pas)
    "gpsPrecision": 2.5      // Ignore petits courants < precision GPS
  },
  "smoothing": {
    "enabled": true,
    "windowSize": 10,        // 10 points = 10 secondes de lissage
    "method": "exponential"
  }
}
```

### Interprétation

- **minSOG**: Si bateau va trop lent (< 0.5 m/s), calcul courant peu fiable
- **maxCurrentSpeed**: Si courant calculé > 3 m/s, c'est probablement une erreur
- **windowSize**: Lisse sur 10 secondes (réduit bruit GPS)

---

## 📈 Grafana Dashboards

### Panel 1: Current Vector (Compass)

```
Radial gauge montrant:
  • Flèche = direction courant (0-360°)
  • Longueur = magnitude (0-3 knots)
  
Exemple:
  Flèche pointe NE (045°) avec longueur 1.0
  = Courant 1 knot vers le NE
```

### Panel 2: Current Speed

```
Line Chart:
  • X-axis: temps
  • Y-axis: courant (0-3 knots)
  • Ligne lisse = 10 sec rolling average
  
Couleurs:
  • vert: < 0.5 knot (courant faible)
  • jaune: 0.5-1.5 knots (courant moyen)
  • orange: 1.5-2.5 knots (courant fort)
  • rouge: > 2.5 knots (exceptionnel)
```

### Panel 3: Leeway (Dérive)

```
Line Chart:
  • Y-axis: -180 à +180° (degrés)
  • Zéro = cap et route confondus (pas de dérive)
  • Positive = dérive à droite
  • Négative = dérive à gauche
  
Interprétation:
  Leeway > +15° = forte dérive à droite
  Leeway < -15° = forte dérive à gauche
```

### Panel 4: Heading vs COG

```
Dual Line Chart:
  • Ligne 1: Heading (cap bateau, jaune)
  • Ligne 2: COG (vraie route, bleu)
  • Écart = leeway
  
Visual:
  Si lignes séparées → dérive observée
  Si lignes confondues → pas de courant
```

---

## 📊 Cas d'Usage Racing

### Situation 1: Courant Favorable

```
Objectif: Aller à Mark (320°)
Heading: 320°
Courant: 0.5 knot vers 320° (même direction!)
COG: 320°
Leeway: 0° (parfait!)

Résultat: Performance optimale
  STW 6.0 + Courant 0.5 = SOG 6.5 knots
  Sans faire rien, on va plus vite!
```

### Situation 2: Courant Contraire

```
Objectif: Aller à Mark (320°)
Heading: 320°
Courant: 1.0 knot vers 140° (opposite!)
Calculated COG: ~310° (dériv de -10°)
Leeway: -10°

Résultat: Performance dégradée
  STW 6.0 - Courant 1.0 = SOG ~5.2 knots
  Bateau dériv à gauche, miss la mark
  
Solution: Lofer de 10° (heading = 330°)
  Nouvel COG: 320° (correct)
```

### Situation 3: Courant Lateral

```
Objectif: Aller au NW (315°)
Heading: 315°
Courant: 0.8 knot vers 045° (perpendiculaire!)
Calculated COG: 330° (dériv de +15°!)
Leeway: +15°

Résultat: Forte dérive à droite
  Bateau va à 315° mais arrive à 330° = 15° off course
  
Solution: Lofer de 15° (heading = 300°)
  Nouvel COG: 315° (correct)
```

---

## 🚀 Installation & Utilisation

### Installation

```bash
# Plugin déjà créé:
# /home/aneto/.signalk/plugins/signalk-current-calculator.js
# /home/aneto/.signalk/plugin-config-data/signalk-current-calculator.json

# Redémarrer Signal K pour charger
docker restart signalk
```

### Vérification

```bash
# Check logs
docker logs signalk | grep Current

# Devrait voir:
# [Current] Plugin started
# [Current] Inputs: SOG=..., STW=..., Heading=...
```

### API Signal K

```bash
# Check current data
curl http://localhost:3000/signalk/v1/api/self/environment/water/currentSpeed
# → {"value": 0.5, "timestamp": "..."}

curl http://localhost:3000/signalk/v1/api/self/navigation/performance/leeway
# → {"value": 0.175, "timestamp": "..."} # radians = 10°
```

---

## 🧪 Testing

### Test Case 1: No Current

```
Input:
  SOG = 6.0 m/s, COG = 320°
  STW = 6.0 m/s, Heading = 320°

Expected Output:
  Current Speed = 0.0 m/s
  Current Dir = N/A
  Leeway = 0.0°

Validation: Heading = COG ✓
```

### Test Case 2: Following Current

```
Input:
  SOG = 6.5 m/s, COG = 320°
  STW = 6.0 m/s, Heading = 320°

Expected Output:
  Current Speed = 0.5 m/s
  Current Dir = 320° (same as heading)
  Leeway = 0.0°

Interpretation: Courant aide (tailwind), +0.5 knot gain
```

### Test Case 3: Lateral Current

```
Input:
  SOG = 6.4 m/s, COG = 330°
  STW = 6.0 m/s, Heading = 320°

Expected Output:
  Current Speed = 0.8 m/s
  Current Dir = 045° (perpendicular)
  Leeway = +10°

Interpretation: Courant dérive bateau 10° à droite
```

---

## 📈 Grafana Integration

### Quick Setup

1. **Data Source:** InfluxDB (already configured)
2. **Measurement:** `environment_water_currentSpeed`
3. **Queries:**
   ```
   SELECT value FROM environment_water_currentSpeed
   SELECT value FROM environment_water_currentDirection
   SELECT value FROM navigation_performance_leeway
   ```
4. **Visualizations:**
   - Gauge (current speed)
   - Compass (current direction)
   - Line chart (leeway over time)

---

## 🎯 Racing Tips

### Exploiting Current

1. **Identify Courant** ← This plugin does it!
2. **Angle to Cross** — Lofe to compensate leeway
3. **Speed Gain** — Favorable current = free speed
4. **Mark Approach** — Approach with zero leeway

### Example Race Scenario

```
Mark is at 315° (NW)
Courant calculated: 1.0 knot @ 045°
Leeway = +20°

Strategy:
  1. Lofe 20° to compensate
  2. Heading = 295° (instead of 315°)
  3. This gives COG = 315° (correct to mark)
  4. STW = 6.0 + current 1.0 = gain to mark

Result: Direct line to mark + speed boost!
```

---

## 🔄 Future Enhancements

### Phase 2 (TBD)
- [ ] Tidal current prediction (API integration)
- [ ] Eddy detection (circular currents)
- [ ] Current shear alerts (sudden changes)
- [ ] Historical current database

### Phase 3 (TBD)
- [ ] Multi-layer currents (surface vs deep)
- [ ] Seasonal current patterns
- [ ] User-entered current (manual override)
- [ ] AIS integration (compare with other boats)

---

## 📚 Resources

- **Vector Math:** https://en.wikipedia.org/wiki/Vector_calculus
- **Navigation:** https://en.wikipedia.org/wiki/Dead_reckoning
- **Leeway:** https://en.wikipedia.org/wiki/Leeway_(navigation)
- **J/30 Design:** Specific leeway characteristics differ

---

## 🎬 Quick Start

1. **Plugin deployed** ✅ (already live)
2. **Inputs:** GPS + loch + heading
3. **Outputs:** Current speed + direction + leeway
4. **Grafana:** Dashboards ready
5. **Racing:** Use leeway to aim accurate to marks

**Ready to exploit the current! ⛵🌊**

---

**Questions?**

1. What leeway are you typically seeing in Stamford area?
2. Want to log historical current patterns?
3. Need alerts for strong currents (> 1.5 knots)?

I can create those features! 🚀

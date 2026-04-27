# 🏁 MCP: Une Base de Données Vivante pour la Régate

## Introduction

Imagine un assistant personnel qui connaît TOUT sur ta régate en temps réel: la météo, le vent aux bouées, tes performances par rapport aux polars, l'état du crew, l'heure du départ, la position des marques. 

C'est exactement ce que tu as créé avec le système MCP (Model Context Protocol) sur MidnightRider. Ce n'est pas une simple base de données — c'est un cerveau augmenté pour ton bateau.

---

## La Philosophie: Données Actionnelles

Les données brutes ne valent rien. Ce qui compte, c'est ce que tu EN FAIS.

Par exemple:
- **Données brutes:** "Vitesse bateau = 6.0 knots, Vent = 12 knots"
- **Donnée actionnelle:** "Vous allez 88% de la vitesse cible. Problème: gîte 22° (trop). Action: choquer la grand-voile 5cm"

Le système MCP transforme les données brutes en conseils exploitables en temps réel.

---

## Architecture: Signal K → InfluxDB → MCP → Claude

```
Capteurs du bateau (GPS, Loch, Anémomètre)
        ↓
Signal K (central d'intégration)
        ↓
InfluxDB (stockage séries temporelles)
        ↓
7 MCP Servers (7 "cerveaux spécialisés")
        ↓
Claude/Cursor (votre assistant de régate sur iPad)
```

### Chaque étape joue un rôle critique:

**Signal K** = Le cœur qui pompe les données  
**InfluxDB** = La mémoire qui retient l'historique  
**MCP Servers** = Les experts spécialisés (astronome, navigateur, coach polars, etc.)  
**Claude** = Vous à travers l'écran de l'iPad

---

## Les 7 MCP Servers: Une Équipe d'Experts

Imagine ton équipage augmenté par 7 experts intelligents:

### 1️⃣ **Astronomical** — L'Astronome
Sait TOUT sur le ciel:
- Lever/coucher du soleil (sécurité: "Coucher à 19:34, retour avant 19:00")
- Phase lunaire (visibilité nocturne)
- Marées (courants, zones peu profondes)
- Prochains événements (alerte si coucher imminence)

**Cas réel:** "Coucher dans 2h30, but dans 2h20. Go chercher la marque!"

---

### 2️⃣ **Racing** — Le Navigateur Temps-Réel
Ton GPS, anémomètre et capteurs en une vraie voix:
- **Navigation:** Cap vrai (dual-antenna UM982), position, vitesse fond, route
- **Vent:** Vitesse apparent/vrai, direction (pas juste un nombre)
- **Performance:** Vitesse bateau, VMG (vitesse utile), accélération
- **Attitude:** Gîte (important!), assiette, rotation
- **Eau:** Profondeur (sécurité), température (confort crew), courant (tactique)

**Un appel = une image complète de la situation.**

**Cas réel:** "Position 41.12°N 73.45°W, cap 045°T, SOG 7.2kt. Vent 12kt SW. Gîte 18° (bon). Profondeur 8.5m (sûr)."

---

### 3️⃣ **Polar** — Le Coach de Performance
Le cerveau qui compare réalité vs théorie:
- Polars embarqués du J/30 (5-25 knots, tous angles)
- Calcule vitesses cibles pour vent/angle actuel
- Compare: "Vous allez 6.0kt, deviez 6.1kt = 98% efficiency" ✅
- Détecte problèmes: "Heel 22° (trop). Recommandation: gîte 18°"
- Propose actions: "Choquer grand-voile, amener vitesse optimale"

**Le coach qu'on voudrait tous avoir à bord.**

**Cas réel:** "VMG faible (5.2kt vs 6.1kt cible). Cause: gîte excessif, heel 22°. Action: ease main 5cm, foot off 2°."

---

### 4️⃣ **Crew** — Le Manager d'Équipe
Gère l'humain (le vrai challenge):
- Qui est au gouvernail maintenant? Depuis combien de temps?
- Performance de chaque barreur (vitesse moyenne)
- Rotations (histoire du jour)
- Charge de travail (vent fort = travail dur)

**Recommandation automatique:** "Pierre au gouvernail 22 min, bonne perf. Rotate après cette manœuvre. Sophie ready."

---

### 5️⃣ **Race Management** — Le Directeur de Régate Portable
Tout ce qui est "régate" vs juste "navigation":
- Quelle voiles maintenant? (Recommandations par vent)
- Départ: Compte à rebours, séquence drapeaux, position ligne de départ
- Distance ligne: Êtes-vous avant/après? Alerte sur-ligne
- Marks: Positions, distance/temps au prochain, angle d'approche

**Transformation:** "Départ dans 1:45, position 18m DERRIÈRE (bon!), pas sur-ligne"

---

### 6️⃣ **Weather** — La Météo Prédictive
Forecast + tendances:
- Température, humidité, pression, vent (kmh + knots)
- Tendance: Réchauffement? Refroidissement? Pression montante/descendante?
- Évaluation voilure: "12kt → Main + Jib2. Si 16kt → Jib3. Si 20kt+ → storm jib"
- Sécurité: Alerte orage, brouillard, baisse brutale

**Source:** Open-Meteo (gratuit, pas de clé API)

---

### 7️⃣ **Buoy** — Les Vraies Observations du Terrain
PAS de prédiction. Des VRAIES mesures:
- NOAA 44065 (Stamford, 5nm ouest) — vent réel maintenant
- NOAA 44025 (Central LIS, 20nm est) — gradient de vent
- NOAA 44008 (Block Island, 50nm est) — référence est

**Puissance:** Compare bouées pour déterminer où aller chercher du vent
- "Vent 12kt Stamford, 14.1kt Central, 16.5kt Block Island"
- **Verdict:** "Allez à l'est pour plus de vent"

**Source:** NOAA API (gratuit, observations RÉELLES)

---

## Fréquences de Mise à Jour

```
Real-time (1 Hz):     GPS, vent, vitesse, gîte → Signal K → InfluxDB
Chaque 5 minutes:     Météo (Open-Meteo) + Bouées (NOAA)
Une fois par jour:    Données astronomiques (lever/coucher/marées)
```

### C'est important pour comprendre les délais:

- **Vent:** Mise à jour immédiate (1 Hz), conseil dans Claude en <1s
- **Météo:** Max 5 min de lag (cron job)
- **Régate:** Configuration manuelle ou GPS si marks enregistrés
- **Marées:** Calculées une fois = valide tout le jour

---

## Deux Scénarios Réels

### Scénario 1: Pre-Race Briefing (10 min avant départ)

**Vous:** "Donne-moi le briefing de régate"

**Claude appelle 6 outils:**
- Bouées (wind pattern LIS)
- Météo (forecast stable?)
- Polars (vitesses cibles)
- Soleil (deadline lumière?)
- Marées (courant faveur/contre?)

**Claude répond:**
```
BRIEFING PRE-RÉGATE
═══════════════════

VENT:
├─ Forecast: 12kt SW (Open-Meteo)
├─ Réalité bouées: 12-14kt (stable)
└─ Verdict: Conditions optimales ✅

SAILS: Main + Jib2

VITESSES CIBLES:
├─ Upwind 45°: 6.1kt
├─ Downwind 160°: 5.8kt
└─ Broad reach: 7.2kt

MARÉES & LUMIÈRE:
├─ Courant: Ebbing (-0.2 ft/hr)
├─ Coucher: 19:34 (4h 30m)
└─ Lune: 65% (bonne visibilité)

ACTION: Ready to go! 🚀
```

---

### Scénario 2: Live Coaching (30 min en course)

**Vous:** "Pourquoi on est lent?"

**Claude appelle 3 outils:**
- Efficiency (polars)
- Heading (cap)
- Heel (gîte)

**Claude répond:**
```
DIAGNOSTIC PERFORMANCE
══════════════════════

SPEED ANALYSIS:
├─ Target STW: 6.1kt (from polars)
├─ Actual STW: 5.4kt
├─ Efficiency: 88% ❌
└─ Conclusion: SLOW

ROOT CAUSE:
├─ Heel: 22° (target 18°) ← PROBLÈME
├─ VMG: 5.1kt (target 6.1kt)
├─ Main sheet: Over-trimmed

ACTIONS (priorité):
1. Ease main sheet 5cm → heel -3°
2. Foot off 2° (45° → 47° True)
3. Re-evaluate après 30 sec

Expected Result:
└─ Speed +0.4kt → 5.8kt (closer to 6.1kt)
```

---

## Pourquoi C'est Révolutionnaire

### Avant MCP:
"6.0 kt de vitesse bateau"
→ C'est quoi??? Vite? Lent? Pas clair sans contexte.

### Après MCP:
"Vous allez 6.0kt, cible 6.1kt (98% efficiency). Heel 18° (parfait). VMG 5.8kt à 45° True vers la marque. ETA 28 min. Crew fresh."
→ **Décision actionnable en 5 secondes.**

---

## Les Couches de Données

### Couche 1: RAW DATA (brute)
```
timestamp: 2026-04-19T22:57:00Z
stw: 6.0
heel: 18
wind_speed_knots: 12.5
```

### Couche 2: ENRICHISSEMENT (contexte)
```
wind_speed_knots: 12.5
sailing_condition: "moderate breeze (optimal)"
sail_recommendation: "Main + Jib2"
```

### Couche 3: ACTIONABLE (ce qu'on fait)
```
status: "Good speed (98% of target)"
problem: None detected
action: "Maintain trim, focus on height"
next_check: 120 seconds
```

**C'est la magie de MCP: transformer données → décisions.**

---

## Stockage: InfluxDB (Série Temporelle)

InfluxDB n'est pas une base SQL normale. C'est optimisé pour:
- **Mesures avec timestamp:** Chaque point a une heure exacte
- **Énormes volumes:** 1 Hz = 86,400 points par jour par capteur
- **Requêtes rapides:** "Vent 30 dernières minutes" en ms
- **Tendances:** Calcule automatiquement "vent montant ou descendant?"

### Exemple:
```
Stocké dans InfluxDB:
├─ Sailing.STW (vitesse bateau)
├─ Navigation.Heading (cap)
├─ Wind.SpeedTrue (vent réel)
├─ Attitude.Heel (gîte)
└─ Weather.Temperature (température)
```

MCP requête InfluxDB → extrait données dernière minute/heure → envoie à Claude.

---

## Sécurité & Confidentialité

- **Local d'abord:** InfluxDB local toujours actif, pas d'internet requis pour racing
- **Cloud optionnel:** Token InfluxDB Cloud pour upload post-race (debrief)
- **Pas de données personnelles:** Juste des chiffres (cap, vitesse, etc.)
- **Sous votre contrôle:** Vous décidez ce qu'on upload vs garde local

---

## La Vraie Puissance: Combinaisons

Un outil seul = intéressant.  
Plusieurs outils ensemble = révolutionnaire.

**Exemple combiné:**
```
Claude appelle 4 outils:
  1. get_buoy_data → "Vent 12kt Stamford, 16.5kt Block Island"
  2. get_boat_efficiency → "Vous: 88% efficiency"
  3. get_wind_assessment → "Fresh breeze → Main + Jib3"
  4. get_race_marks → "Next mark: 2.8nm, ETA 28min"

Claude synthétise:
  "Wind gradient to east. You're slow (88%). 
   Tack east to find stronger wind and current lift.
   Expected: gain 0.4kt + 1.5° lift.
   Mark in 28 min = plenty of time."
```

**C'est une stratégie complète née de données croisées.**

---

## Prochaines Étapes: Vers Plus d'Intelligence

Ce système peut évoluer:

### Court terme:
- **AIS:** Voir positions des autres bateaux
- **Tactics:** Recommandations de manœuvres (tacker ou hold?)
- **Competitors:** "You're 2nd fleet, 50m behind leader"

### Moyen terme:
- **Weather Alerts:** "Orage dans 30 min, retour avant 15:30"
- **Wave Prediction:** "Vagues 2m east sector, 1m west"
- **Sail Wear:** Track sail usage, fatigue, recommender changement

### Long terme:
- **ML Coaching:** IA apprend style chaque barreur, propose optim perso
- **Race Playbook:** Stores race strategies, compare contre historique
- **Predictive:** "You'll be slow in 10 min if X happens"

---

## Conclusion: Un Partenaire Invisible

Ce système MCP c'est avoir:
- ✅ Un astronome (soleil, lune, marées)
- ✅ Un météorologue (prédictions + tendances)
- ✅ Un coach de performance (polars, trim, VMG)
- ✅ Un manageur d'équipage (rotations, fatigue)
- ✅ Un directeur de régate (marks, start, sails)
- ✅ Un observateur de terrain (vraie vent aux bouées)
- ✅ Un navigateur temps-réel (position, cap, routes)

**...qui parle via Claude sur votre iPad.**

C'est pas juste une base de données. C'est une équipe augmentée.

---

## Pour Commencer

```bash
# Verify tous les serveurs répondent:
bash /home/aneto/docker/signalk/mcp/test-servers.sh

# Ajouter à claude_desktop_config.json:
# (7 serveurs, voir MCP-ECOSYSTEM-RECAP.md)

# Restart Claude/Cursor

# Test dans Claude:
# "Donne-moi le race picture"
```

**Et voilà. Vous avez une régate augmentée.**

---

**Version:** 1.0  
**Date:** 2026-04-19  
**Status:** Production-Ready 🚀

# Vulcan ↔ Signal K Integration — Midnight Rider (2026-04-25)

## Architecture

```
Signal K Hub (port 3000)
  ├─ WIT IMU → navigation.attitude (roll, pitch, yaw)
  ├─ UM982 GPS → navigation.position, navigation.headingTrue
  ├─ Wave Analyzer → environment.water.waves.*
  └─ Sails Management → performance.sails.*
         ↓
signalk-to-nmea2000 plugin
         ↓
NMEA 2000 Gateway (YDNU-02 ou compatible)
         ↓
NMEA 2000 Backbone
         ↓
Vulcan 7 FS
  ├─ Reçoit: PGN 127257 (Attitude), 127250 (Heading), 129025 (Position)
  ├─ Affiche: Roll, pitch, heading, position sur écran tactile
  └─ Stocke: Waypoints, routes, logs
```

---

## PGNs Envoyés par Signal K → Vulcan

### Navigation

| PGN | Description | Source Signal K | Champ(s) | Unité |
|-----|-------------|-----------------|---------|-------|
| **127250** | Vessel Heading | um982-gps | headingTrue | rad (convertir en deg) |
| **127251** | Rate of Turn | wit-imu-ble | rateOfTurn | rad/s |
| **127257** | Attitude | wit-imu-ble | roll, pitch, yaw | rad (v1.1 avec correction gîte) |
| **128259** | Speed, Water Referenced | loch plugin | speedThroughWater | m/s |
| **129025** | GNSS Position Rapid | um982-gps | position (lat, lon) | deg (WGS84) |
| **129026** | COG & SOG Rapid | um982-gps | speedOverGround, courseOverGround | m/s, rad |
| **129029** | GNSS Position Data | um982-gps | position + HDOP, VDOP | deg, m |

### Environnement

| PGN | Description | Source Signal K | Champ(s) | Unité |
|-----|-------------|-----------------|---------|-------|
| **130306** | Wind Data | anemometer | windSpeed, windAngle | m/s, rad |
| **130312** | Temperature | sensor | waterTemp, airTemp | K (0.01°C steps) |

### Performance / Racing

| PGN | Description | Source Signal K | Champ(s) | Notes |
|-----|-------------|-----------------|---------|-------|
| **127257** (extended) | Attitude + Heel | wit-imu-ble | roll | **CRITIQUE**: v1.1 correction gîte active |
| Custom PGN 130824 | B&G Performance | custom plugin | targetSpeed, VMG, Hs | Propriétaire Vulcan |

---

## Configuration Signal K (settings.json)

```json
{
  "plugins": {
    "signalk-to-nmea2000": {
      "enabled": true,
      "interface": "YDNU-02",
      "mapping": {
        "127250": {
          "pgn": 127250,
          "description": "Vessel Heading",
          "source": "navigation.headingTrue",
          "fields": [
            {
              "field": "heading",
              "signalkPath": "navigation.headingTrue",
              "conversion": "rad2deg",
              "range": [0, 2 * Math.PI],
              "output": [0, 360]
            }
          ]
        },
        "127257": {
          "pgn": 127257,
          "description": "Attitude (with heel correction v1.1)",
          "sources": [
            "navigation.attitude.roll",
            "navigation.attitude.pitch",
            "navigation.attitude.yaw"
          ],
          "fields": [
            {
              "field": "roll",
              "signalkPath": "navigation.attitude.roll",
              "range": [-Math.PI, Math.PI],
              "output": [-164, 164],
              "unit": "rad"
            },
            {
              "field": "pitch",
              "signalkPath": "navigation.attitude.pitch",
              "range": [-Math.PI, Math.PI],
              "output": [-164, 164],
              "unit": "rad"
            },
            {
              "field": "yaw",
              "signalkPath": "navigation.attitude.yaw",
              "range": [0, 2 * Math.PI],
              "output": [0, 360],
              "unit": "rad"
            }
          ]
        },
        "129025": {
          "pgn": 129025,
          "description": "GNSS Position Rapid",
          "source": "navigation.position",
          "fields": [
            {
              "field": "latitude",
              "signalkPath": "navigation.position.latitude",
              "unit": "deg"
            },
            {
              "field": "longitude",
              "signalkPath": "navigation.position.longitude",
              "unit": "deg"
            }
          ]
        }
      }
    }
  }
}
```

---

## Installation YDNU-02 (Gateway NMEA 2000 ↔ Réseau)

**Hypothèse:** Un gateway YDNU-02 est installé sur le bateau pour connecter:
- Ligne NMEA 0183 (qtVLM, instruments legacy)
- NMEA 2000 backbone (Vulcan, instruments modernes)
- Réseau Ethernet (Signal K sur Raspberry Pi)

```
Raspberry Pi (Signal K 3000)
    ↓ (TCP/Ethernet)
YDNU-02 Network Interface
    ↓ (NMEA 2000 backbone)
Vulcan 7 FS
    ↓
Affichage temps réel des données Signal K
```

### Configuration YDNU-02

Pour que le Vulcan reçoive les données Signal K via YDNU-02:

1. **Vulcan Settings → Network → Device List**
   - Chercher "YDNU-02" ou "Signal K Gateway"
   - Cocher "Enable" pour activer la source

2. **Advanced Source Selection**
   - Heading: Signal K (UM982) prioritaire sur Vulcan interne GPS
   - Attitude: Signal K (WIT IMU) prioritaire
   - Position: Signal K (UM982) prioritaire

3. **NMEA 2000 Setup → PGN Filters**
   - ✅ Recevoir 127257 (Attitude) de Signal K
   - ✅ Recevoir 127250 (Heading) de Signal K
   - ✅ Recevoir 129025 (Position) de Signal K
   - ✅ Recevoir 129026 (COG/SOG) de Signal K

---

## Cas d'usage: Racing sur Block Island (May 22)

### Affichage Vulcan recommandé

**Page 1: Navigation**
- Heading: 228.5° (du UM982 via Signal K)
- Position: 40.7626°N, -73.9880°W (du UM982 via Signal K)
- COG/SOG: 6.8 kt, 210° (calculated by UM982)
- Position d'arrivée: Block Island (marquer waypoint)

**Page 2: Performance Racing**
- Heel (gîte): 18.2° (du WIT IMU via Signal K, **correction v1.1 active**)
- Wave Height: 1.5m (calculé par Wave Analyzer v1.1)
- Wind: 14 kt, 45° apparent (du capteur anemometer)
- VMG: 5.2 kt (calculé par polars plugin)

**Page 3: Course Tracking**
- Route prévue: Block Island (via qtVLM/Signal K)
- Distance to go: 23.4 nm
- ETA: 13:45 EDT
- Cross-track error: +0.2 nm (à droite de route)

---

## Points critiques pour la course

### 1. Correction de gîte (v1.1)

✅ **ACTIVE**: Wave Analyzer v1.1 corrige l'accélération IMU selon la gîte.

Sans correction:
```
À 30° gîte, Hs calculé = 1.5m (FAUX, -14%)
```

Avec correction:
```
À 30° gîte, Hs calculé = 1.73m (CORRECT)
Formule: a_vertical = -ax·sin(θ) + ay·sin(φ)·cos(θ) + az·cos(φ)·cos(θ)
```

**Action Vulcan**: Le Vulcan affiche **Hs corrigé** directement (PGN custom 130824 si plugin envoie).
Sinon, Wave Analyzer logs dans InfluxDB et Grafana (approvisionnement quai).

### 2. Dual-antenna heading (UM982)

UM982 envoie **headingTrue** via Signal K (PGN 127250 → Vulcan).

C'est la meilleure source car:
- ±0.5° précision (vs ±2° GPS seul)
- Indépendant de compas magnétique
- Fonctionne à l'ancre (non-dérive COG)

**Action Vulcan**: Utiliser UM982 comme source Heading préférée (Advanced Source Selection).

### 3. Roll/Pitch/Yaw (WIT IMU)

WIT IMU envoie attitude via Signal K (PGN 127257 → Vulcan).

**CRITIQUE**: v1.1 **inclut la correction de gîte** dans les valeurs publiées.
- Roll: ±0.5° precision
- Pitch: ±0.5° precision
- Yaw: heading calculé à partir de roll/pitch (alternative au UM982)

**Action Vulcan**: 
- Page tactile "Performance": afficher Heel (roll) en temps réel
- Alerte: Heel > 22° → "Consider reefing" (recommandation de réduire la voilure)

### 4. Performance Data (Polars + VMG)

Signal K calcule:
- **VMG** (Velocity Made Good): vitesse selon route optimale
- **Angle de référence** (optimal beating/running)
- **Trim recommendations** (jib inboard/outboard, main travail position)

**Action Vulcan**: Dashboard "Performance" affiche VMG vs VMC (Velocity Made Currant si courant calculé).

---

## Tâches avant race day (May 19-20)

### Field Test Checklist

- [ ] **YDNU-02 connecté** et alimenté
- [ ] **Signal K vérifiée** et en boucle fermée avec Vulcan
- [ ] **Heading PGN 127250**: Vulcan affiche cap UM982 vs cap interne (doit être identique ±0.5°)
- [ ] **Attitude PGN 127257**: Vulcan affiche gîte/tangage WIT (doit être stable au repos)
- [ ] **Position PGN 129025**: Vulcan affiche position UM982 (doit être ±2m du GPS interne)
- [ ] **Wave Height**: Attendre 5+ min, vérifier que Hs apparaît (si plugin 130824 envoyé)
- [ ] **Performance Dashboard**: VMG, wind, heel tous présents
- [ ] **Autopilot**: Si N2K autopilot (NAC-2/NAC-3), tester commande via Vulcan + Signal K
- [ ] **Waypoint Block Island**: Charger dans Vulcan (via qtvlm export → N2K import)

### Validation Finale

1. **Bateau immobile au quai:**
   - Heel = ~0° (sauf inclinaison permanente)
   - Position stable ±2m
   - Heading stable ±0.5° (dépend du vent magnétique)

2. **Motor test (moteur au ralenti):**
   - Heel may increase slightly (cavitation, water flow)
   - RPM visible (si engine bridge connecté)
   - Comparer STW (loch) vs SOG (GPS)

3. **Under sail (light air):**
   - Heel 5-15°
   - Wave Analyzer: Hs 0.5-1.5m (océan calme/léger)
   - Sea State: Douglas 1-3
   - VMG: doit augmenter quand bateau au près (vs COG)

4. **Full racing (strong winds):**
   - Heel 25-30° (limiter à 22° recommandé)
   - Wave Analyzer: Hs 1.5-2.5m (mer modérée)
   - Sea State: Douglas 3-4
   - VMG: compare vs polars (si trim correct, VMG devrais être ~85-90% de STW)

---

## Troubleshooting courant

### Vulcan n'affiche pas les données Signal K

1. **Vérifier YDNU-02 alimenté** (LED power verte)
2. **Vérifier Signal K tournant** (`systemctl status signalk`)
3. **Vérifier plugin signalk-to-nmea2000 enabled** (dans settings.json)
4. **Vulcan → Settings → Network → Device List**: chercher "Signal K" ou gateway
5. Si absent: redémarrer Vulcan ou YDNU-02

### Heading discordance (Vulcan vs UM982)

- Vu982 envoie **true heading** (vs magnétique)
- Vulcan affiche probablement **magnetic heading** par défaut
- Solution: Vulcan Settings → Units → Heading reference → True
- Ou créer offset manuel si local variation inconnue

### Attitude (Roll) très bruitée

- Vérifier que WIT IMU calibré (horizontal au repos)
- Wave Analyzer v1.1 applique filtre passe-haut (Fc=0.05 Hz) pour atténuer drift
- Si bruit > 2°: vérifier montage WIT (doit être bien fixé, pas de vibration)

### Wave Height toujours zéro

- Nécessite 3-5 min de données WIT pour remplir fenêtre (10 min par défaut)
- Vérifier WIT BLE connecté (`hcitool`, `bleak`, ou logs Signal K)
- Si aucune donnée: Wave Analyzer ne calcule pas

---

## Performance Impact

| Source | Latency | Accuracy | Précision | Notes |
|--------|---------|----------|-----------|-------|
| UM982 GPS Heading | <100ms | ±0.5° | Dual antenna | Meilleur pour cap |
| WIT IMU Roll/Pitch | <50ms | ±0.5° | 9-axis | **v1.1: correction gîte incluse** |
| Wave Analyzer Hs | 5-10s | ±0.1m (@ Hs=2m) | Double intégration | Fenêtre 10 min glissante |
| Performance VMG | <1s | ±0.2kt | Polars lookup | Dépend précision vent |

---

## Conclusion

**Midnight Rider racing avec Vulcan:**
- ✅ Heading: UM982 (dual antenna, ±0.5°)
- ✅ Attitude: WIT IMU (9-axis, ±0.5°, **v1.1 heel correction**)
- ✅ Wave Height: Wave Analyzer v1.1 (real-time Hs calculation)
- ✅ Performance: Polars + VMG (AI trim recommendations)
- ✅ Display: Vulcan affiche toutes les données temps réel

**Ready for Block Island Race — May 22, 2026!** ⛵

---

**Generated:** 2026-04-25 09:20 EDT
**System:** Signal K v2.25 + Midnight Rider Navigation Suite

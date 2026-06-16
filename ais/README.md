# AIS Competitor Tracker — `ais/`

> **Module de suivi des concurrents en course** | Midnight Rider (J/30) | Phase J-1/J-2 | v1.1

Intégration du flux AIS reçu par Signal K avec la base de données des concurrents inscrits,
pour afficher en temps réel qui est autour de vous, à quelle distance, et si vous gagnez ou perdez du terrain.

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Modules](#modules)
4. [API Reference](#api-reference)
5. [Base de données des concurrents](#base-de-données-des-concurrents)
6. [Logique couleur VMG](#logique-couleur-vmg)
7. [Daemon AIS Watch](#daemon-ais-watch)
8. [Tests](#tests)
9. [Déploiement Docker](#déploiement-docker)
10. [Utilisation en course](#utilisation-en-course)
11. [Historique des versions](#historique-des-versions)

---

## Vue d'ensemble

### Fonctionnalité principale

Le module AIS répond à une question simple en course :

> **"Parmi les bateaux inscrits que je vois sur AIS, lesquels gagnent du terrain sur moi ?"**

Il croise deux sources de données :
- **Signal K** : flux AIS en temps réel (position, cap, vitesse de tous les bateaux à portée VHF)
- **`regatta/competitors.json`** : base de données des 68 concurrents inscrits (MMSI, PHRF, équipage)

Le résultat : un tableau de concurrents avec leur VMG calculé, codé **GREEN** (vous gagnez)
ou **RED** (ils gagnent), mis à jour toutes les 30 secondes.

### Ce que le module fait

- Récupère la position, cap et vitesse de Midnight Rider depuis Signal K
- Récupère le vent vrai (TWD/TWS) depuis Signal K
- Récupère la marque suivante depuis Signal K (si waypoint actif dans Vulcan 7)
- Parcourt tous les `vessels/` dans Signal K, filtre les AIS dans un rayon configurable
- Croise les MMSI AIS avec la base de données des concurrents inscrits
- Calcule TWA, VMG vent et VMG marque pour chaque concurrent ET pour Midnight Rider
- Compare les VMG et produit la couleur GREEN/RED/NEUTRAL
- Conserve un historique de 30 minutes pour calculer les deltas (qui se rapproche / s'éloigne)
- Expose deux endpoints HTTP REST consommés par les frontends HTML (Phase J-3)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                           │
├─────────────────────────────────────────────────────────────────┤
│  Signal K (port 3000)          regatta/competitors.json         │
│  ├── vessels/self/...          ├── 68 bateaux inscrits          │
│  │   ├── navigation.position  ├── MMSI par bateau              │
│  │   ├── navigation.SOG/COG   ├── PHRF LIS + IRC TCC           │
│  │   └── environment.wind.*   └── skipper, classe              │
│  └── vessels/<mmsi>/...                                         │
│      ├── navigation.position  ← flux AIS décodé par SK         │
│      ├── navigation.SOG/COG                                     │
│      └── name                                                   │
└──────────────┬────────────────────────┬────────────────────┘
               │                        │
               ▼                        ▼
┌──────────────────────┐     ┌──────────────────────────┐
│  server_handlers.py  │     │   competitors_db.py       │
│  api_competitors()   │◄────│   CompetitorDB            │
│  api_fleet_db()      │     │   TTL cache: 5 min        │
└──────────┬───────────┘     └──────────────────────────┘
           │                            ▲
           │ calcule via                │ enrich()
           ▼                            │
┌──────────────────────┐     ┌──────────────────────────┐
│    ais_lib.py        │     │   ais_watch.py (optionnel)│
│  Pure math functions │     │   Daemon: SK → InfluxDB   │
│  haversine, TWA, VMG │     │   toutes les 30s          │
│  delta, color logic  │     │   logs/services/          │
└──────────┬───────────┘     └──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│            regatta/server.py (Docker port 5000)              │
│  GET /api/competitors?radius_nm=15&vmg_mode=wind             │
│  GET /api/fleet_db                                           │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│          portal/server.py (port interne)                     │
│  GET /ais/           → tracker.html  (Phase J-3)             │
│  GET /ais/fleet_db   → fleet_db.html (Phase J-3)            │
└──────────────────────────────────────────────────────────────┘
```

### Flux de données en course

```
Bus NMEA 2000
    └── YDNU-02 USB (/dev/ttyACM0)
        └── Signal K (canboatjs decoder)
            ├── AIS Class A/B (PGN 129038/129039)
            │   → vessels/<mmsi>/navigation.position, SOG, COG
            └── GPS/vent propre → vessels/self/navigation.*, environment.*
                    │
                    ▼
        server_handlers.py (à chaque requête HTTP)
                    │
                    ├── vessels/self → position MR, SOG, COG, TWD, TWS, marque
                    ├── vessels/*   → filtre dans radius_nm
                    ├── MMSI        → CompetitorDB.get_by_mmsi()
                    ├── compute_twa(COG, TWD)
                    ├── compute_vmg_wind(SOG, TWA)
                    ├── is_gaining_ground(VMG_MR, VMG_comp) → color
                    └── JSON response avec couleur par concurrent
```

---

## Modules

### `ais_lib.py` — Bibliothèque mathématique pure

**Rôle** : 9 fonctions stateless, sans I/O, sans état global. Aucune dépendance externe.
Testées unitairement à 100% (34 tests).

| Fonction | Description | Entrées | Sortie |
|----------|-------------|---------|--------|
| `haversine_ll(lat1,lon1,lat2,lon2)` | Distance great-circle | degrés décimaux | **mètres** |
| `bearing_ll(lat1,lon1,lat2,lon2)` | Relèvement vrai | degrés décimaux | **degrés 0–360** |
| `compute_twa(cog_deg, twd_deg)` | True Wind Angle ±180 | degrés | **degrés ±180** (+ = tribord) |
| `compute_vmg_wind(sog_kts, twa_deg)` | VMG vers le vent | kts, degrés | **kts** (+ = au vent) |
| `compute_vmg_mark(sog_kts, cog_deg, brg_mark_deg)` | VMG vers la marque | kts, degrés | **kts** (+ = vers marque) |
| `make_history_store()` | Créer store historique 30 min | — | `defaultdict(deque(maxlen=80))` |
| `record_position(store, mmsi, dist_m, brg_deg)` | Enregistrer une position | — | — |
| `compute_delta(store, mmsi, window_s=1800)` | Delta vs ~30 min | — | `(Δdist_m, Δbrg_deg, age_min)` |
| `is_gaining_ground(vmg_mr, vmg_comp)` | Logique couleur | kts, kts | `'green'` / `'red'` / `'neutral'` |

```python
# Exemples
from ais_lib import haversine_ll, compute_twa, compute_vmg_wind, is_gaining_ground

dist_nm = haversine_ll(40.921, -73.751, 41.167, -71.583) / 1852  # → 101 nm (Larchmont→Block Island)
twa     = compute_twa(cog_deg=45.0, twd_deg=0.0)                  # → +45° (tribord amures)
vmg     = compute_vmg_wind(sog_kts=6.5, twa_deg=45.0)             # → 4.60 kts
color   = is_gaining_ground(vmg_mr=5.1, vmg_comp=4.8)             # → 'green'
```

---

### `competitors_db.py` — Gestionnaire de la base de données

**Rôle** : Charge `regatta/competitors.json`, le met en cache (TTL 5 min),
et fournit les méthodes de lookup utilisées par `server_handlers.py`.

```python
from competitors_db import CompetitorDB

db = CompetitorDB('/repo/regatta/competitors.json')

# Lookup par MMSI (accepte int ou str, supporte ais.mmsi et mmsi direct)
boat = db.get_by_mmsi('338123456')   # → dict brut ou None
boat = db.get_by_mmsi(338123456)     # → même résultat (int accepté)

# Normaliser les données (retourne un dict uniforme)
e = db.enrich(boat)
# {'id': 'boat-01', 'name': 'Wind Hunter', 'sail_num': 'USA 1234',
#  'skipper': 'John Doe', 'boat_class': 'J/Boats J/30',
#  'mmsi': '338123456', 'phrf_lis': 171, 'irc_tcc': 1.012,
#  'priority': 'high', 'events': ['BIR2026']}

# Listes
db.get_all()                # 68 bateaux (actifs + inactifs)
db.get_all_active()         # 56 bateaux actifs (active: true)
db.get_all_active_mmsis()   # set de strings MMSI des actifs

# Recherche texte (nom, sail number, MMSI, classe)
db.search('Wind')           # → liste de correspondances
db.search('USA 1234')       # → lookup par sail number
db.search('338123456')      # → lookup par MMSI

# Métadonnées du fichier
db.get_meta()               # → {'version': '...', 'event': 'BIR2026', ...}
```

---

### `server_handlers.py` — Handlers API HTTP

**Rôle** : Deux fonctions importées par `regatta/server.py` via `sys.path.insert(0, '/repo/ais')`.
Chaque appel HTTP lit Signal K en temps réel — pas de cache Signal K côté handler.

#### `api_competitors(sk_fn, gps_fn, radius=10.0, min_sog=0.0, inc_unk=False, vmode='wind')`

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `sk_fn` | callable | — | `sk_fn(path) → dict` — accès Signal K |
| `gps_fn` | callable | — | `gps_fn() → {'lat': float, 'lon': float}` |
| `radius` | float | 10.0 | Rayon de recherche en milles nautiques |
| `min_sog` | float | 0.0 | SOG minimale (filtre les bateaux mouillés) |
| `inc_unk` | bool | False | Inclure les AIS hors base de données |
| `vmode` | str | `'wind'` | Mode VMG : `'wind'` ou `'mark'` |

**Réponse JSON :**
```json
{
  "ts": 1718485200,
  "self": {
    "lat": 40.921, "lon": -73.751,
    "sog_kts": 6.1, "cog": 45.0, "twa": 32.5,
    "vmg_wind_kts": 5.15, "vmg_mark_kts": 4.80
  },
  "wind":  { "twd": 12.5, "tws_kts": 14.2, "available": true },
  "mark":  { "lat": 41.167, "lon": -71.583, "brg": 87.3, "dist_nm": 101.2, "available": true },
  "competitors": [
    {
      "mmsi": "338123456", "name": "Wind Hunter", "sail_num": "USA 1234",
      "skipper": "John Doe", "boat_class": "J/Boats J/30", "phrf_lis": 171,
      "in_comp_db": true,
      "dist_nm": 1.24, "bearing": 47.3, "sog_kts": 5.9, "cog": 38.0,
      "twa": 25.5, "vmg_wind_kts": 5.33, "vmg_mark_kts": 4.91,
      "delta_dist_m": -340.0, "delta_brg_deg": 2.1, "delta_window_min": 31.2,
      "color": "red"
    }
  ],
  "matched": 1
}
```

**Erreur (GPS inactif) :**
```json
{"error": "no_position", "competitors": []}
```
Comportement **normal au quai**. Disparaît dès que Signal K publie `navigation.position`.

#### `api_fleet_db(sk_fn)`

Vue statique de tous les concurrents avec leur statut AIS courant.

```json
{
  "total": 68, "active": 56,
  "competitors": [
    { "id": "boat-01", "name": "Wind Hunter", "mmsi": "338123456",
      "ais_status": "live", "phrf_lis": 171, "irc_tcc": 1.012, ... }
  ]
}
```

**Statuts AIS :**

| Statut | Condition | Interprétation |
|--------|-----------|----------------|
| `live` | Vu par Signal K < 2 min | Transponder actif, signal reçu |
| `stale` | Vu il y a 2–10 min | Signal intermittent / limite de portée |
| `old` | Vu il y a 10–60 min | Probablement hors de portée VHF |
| `absent` | Non vu dans Signal K | Pas de transponder AIS, ou hors portée |

---

### `ais_watch.py` — Daemon InfluxDB (optionnel)

**Rôle** : Daemon standalone qui poll Signal K toutes les 30 secondes et écrit
les données de tracking dans InfluxDB pour analyse post-course dans Grafana.

```bash
# Variables d'environnement (valeurs par défaut)
export SIGNALK_HTTP=http://localhost:3000
export INFLUX_URL=http://localhost:8086
export INFLUX_ORG=MidnightRider
export INFLUX_BUCKET=midnight_rider
export AIS_POLL_S=30
export AIS_RADIUS_NM=20

python3 /home/aneto/midnightrider-navigation/ais/ais_watch.py
```

**Measurement InfluxDB :** `competitor_tracking`
Tags : `mmsi`, `name`, `sail`
Fields : `dist_nm`, `bearing`, `sog_kts`, `cog`, `twa`, `vmg_wind`, `vmg_mark`, `color`, `phrf_lis`

**Logs :** `logs/services/ais-watch.log` (RotatingFileHandler 5 MB × 3)

---

## API Reference

```bash
# Concurrents dans un rayon de 15 nm, VMG vent
curl "http://midnightrider.local:5000/api/competitors?radius_nm=15"

# VMG vers la marque, exclure les mouillés (SOG < 0.5 kts)
curl "http://midnightrider.local:5000/api/competitors?radius_nm=10&vmg_mode=mark&min_sog_kts=0.5"

# Inclure les AIS hors base de données
curl "http://midnightrider.local:5000/api/competitors?radius_nm=20&include_unknown=true"

# Base de données complète (ne nécessite pas de GPS actif)
curl "http://midnightrider.local:5000/api/fleet_db"
```

| Paramètre `api/competitors` | Valeurs | Défaut |
|-----------------------------|---------|--------|
| `radius_nm` | 1–50 | 10 |
| `vmg_mode` | `wind`, `mark` | `wind` |
| `min_sog_kts` | 0–20 | 0 |
| `include_unknown` | `true`/`false` | `false` |

---

## Base de données des concurrents

### Fichier source

```
regatta/competitors.json
```

Source de vérité unique. Rechargé automatiquement toutes les 5 minutes (cache TTL).
**Ne jamais éditer en cours de course** — utiliser `git pull` pour mettre à jour.

### Format complet

```json
{
  "_meta": {
    "version": "2026-BIR-v1.0",
    "event": "Block Island Race 2026",
    "fleet": "J/30 One-Design",
    "last_updated": "2026-06-15",
    "total_boats": 68,
    "active_boats": 56
  },
  "competitors": [
    {
      "id": "boat-01",
      "boat_name": "Wind Hunter",
      "sail_number": "USA 1234",
      "skipper": "John Doe",
      "active": true,
      "ais": { "mmsi": 338123456 },
      "vessel": { "make": "J/Boats", "model": "J/30" },
      "ratings": {
        "PHRF_LIS": { "value": 171 },
        "IRC": { "TCC": 1.012 }
      },
      "priority": "high",
      "events": ["BIR2026"]
    }
  ]
}
```

### Champs

| Champ | Obligatoire | Type | Description |
|-------|-------------|------|-------------|
| `id` | ✅ | string | Identifiant unique stable (`boat-01`) |
| `boat_name` | ✅ | string | Nom du bateau |
| `sail_number` | ✅ | string | Numéro de voile (`USA 1234`) |
| `active` | ✅ | bool | `true` = apparaît dans le tracker |
| `ais.mmsi` | ⭐ | int | **Requis pour le tracking AIS** — 9 chiffres |
| `mmsi` | ⭐ | int | Alternative à `ais.mmsi` (les deux formats acceptés) |
| `ratings.PHRF_LIS.value` | — | int | Handicap PHRF (entier) |
| `ratings.PHRF_LIS` | — | int | Raccourci direct (int au lieu de dict) |
| `ratings.IRC.TCC` | — | float | Coefficient IRC (ex : `1.012`) |
| `vessel.make` + `vessel.model` | — | string | Classe du bateau |
| `priority` | — | string | `high`/`medium`/`low` — tri d'affichage |
| `events` | — | list | Régates (`["BIR2026"]`) |

### Ajouter un concurrent

```bash
# 1. Éditer le fichier
nano /home/aneto/midnightrider-navigation/regatta/competitors.json

# 2. Ajouter l'entrée dans le tableau "competitors" :
# {
#   "id": "boat-69",
#   "boat_name": "New Challenger",
#   "sail_number": "USA 9876",
#   "skipper": "Jane Doe",
#   "active": true,
#   "ais": { "mmsi": 338001234 },
#   "vessel": { "make": "J/Boats", "model": "J/30" },
#   "ratings": { "PHRF_LIS": { "value": 165 } },
#   "priority": "medium",
#   "events": ["BIR2026"]
# }

# 3. Mettre à jour _meta.total_boats et _meta.last_updated

# 4. Valider le JSON
python3 -c "import json; json.load(open('regatta/competitors.json')); print('JSON valid')"

# 5. Committer
git add regatta/competitors.json
git commit -m "data: add New Challenger USA 9876 (MMSI 338001234)"
git push origin main
```

Le cache se rechargera **automatiquement dans les 5 minutes** sans redémarrer le container.

### Désactiver un concurrent

Passer `"active": false`. Le bateau apparaît toujours dans `/api/fleet_db`
(avec `ais_status: "absent"`) mais est exclu de `/api/competitors`.

### Trouver le MMSI d'un bateau

```bash
# Option 1 : MarineTraffic (navigateur)
# https://www.marinetraffic.com/en/ais/details/ships/name:WIND+HUNTER

# Option 2 : VesselFinder
# https://www.vesselfinder.com/?name=WIND+HUNTER

# Option 3 : depuis Signal K en mer (bateau visible à portée AIS)
curl -s http://localhost:3000/signalk/v1/api/vessels/ | python3 -c "
import sys, json
for k, v in json.load(sys.stdin).items():
    name = (v.get('name') or {}).get('value', '')
    if name: print(k.split(':')[-1], name)
" | grep -i "wind hunter"
```

---

## Logique couleur VMG

```
VMG_MR   = SOG_MR   × cos(TWA_MR)    ← Midnight Rider
VMG_comp = SOG_comp × cos(TWA_comp)   ← Concurrent

VMG_MR - VMG_comp > +0.05 kts  →  GREEN  (vous gagnez du terrain)
VMG_comp - VMG_MR > +0.05 kts  →  RED    (le concurrent gagne)
Différence ≤ 0.05 kts           →  NEUTRAL
```

**Seuil 0.05 kts** = 90 m/heure — évite le clignotement sur les micro-variations.

**Mode `vmg_mode=mark`** : remplace `cos(TWA)` par `cos(angle_vers_marque)`.
Plus pertinent sur les bords de reaching ou lors de l'approche d'une marque.

**Cas particuliers :**

| Situation | Comportement |
|-----------|-------------|
| Vent non disponible dans SK | Tous NEUTRAL (TWD manquant → TWA incalculable) |
| Marque non disponible | Mode mark impossible → fallback mode wind |
| VMG_MR ou VMG_comp = None | NEUTRAL |
| SOG = 0 (bateau mouillé) | VMG = 0 → utiliser `min_sog_kts=0.5` pour exclure |

---

## Tests

```bash
cd /home/aneto/midnightrider-navigation

# Suite complète — 75 tests, ~0.04s
python3 -m unittest discover -s tests/ -p 'test_*.py' -v

# Par module
python3 -m unittest tests.test_ais_lib -v           # 34 tests (maths pures)
python3 -m unittest tests.test_competitors_db -v    # 23 tests (base de données)
python3 -m unittest tests.test_server_handlers -v   # 18 tests (API handlers)
```

| Fichier test | N | Couverture |
|---|---|---|
| `test_ais_lib.py` | 34 | haversine, bearing, TWA wrap-around, VMG vent/marque, delta 30min, couleur threshold, history store |
| `test_competitors_db.py` | 23 | CRUD, MMSI nested/direct, search, enrich PHRF dict+int, IRC TCC, boat_class, meta |
| `test_server_handlers.py` | 18 | no_position, SOG m/s→kts, COG rad→deg, wind/mark available, fleet_db structure, cache isolation |

---

## Déploiement Docker

```yaml
# docker-compose.yml (extrait)
regatta:
  build: ./regatta
  ports:
    - "5000:5000"
  volumes:
    - /home/aneto/midnightrider-navigation:/repo
  environment:
    SIGNALK_HTTP: http://signalk:3000
    INFLUX_URL: http://influxdb:8086
```

**Point de montage** : `/repo/ais` accessible en Python via `sys.path`.

**Redémarrage du container** : Requiert `/repo` à l'exécution (pas de copie lors du build).

---

## Utilisation en course

### Vérifier le module avant de partir

```bash
# 1. Vérifier que Signal K reçoit du vert AIS
curl -s http://localhost:3000/signalk/v1/api/vessels/ | python3 -m json.tool | head -20

# 2. Tester les API
curl "http://localhost:5000/api/fleet_db" | python3 -m json.tool
curl "http://localhost:5000/api/competitors?radius_nm=15" | python3 -m json.tool

# 3. Vérifier les logs
tail -20 logs/latest.json
```

### En mer

L'endpoint `/api/competitors` affiche en **temps réel** (pas de cache) :
- Concurrents dans le rayon spécifié
- Couleur GREEN/RED/NEUTRAL basée sur le VMG
- Historique 30 min pour voir les **tendances** (delta distance + bearing)

**À ignorer :**
- AIS non dans la base de données (`in_comp_db: false`) — sauf si vous pourchassez un invité
- Bateaux avec `ais_status: "old"` ou `"absent"` → probablement hors portée

### Post-course (optionnel)

```bash
# Récupérer la séquence InfluxDB du daemon ais_watch
influx query --org MidnightRider \
  'from(bucket:"midnight_rider") 
   |> range(start: 2026-05-22T08:00:00Z, stop: 2026-05-22T20:00:00Z)
   |> filter(fn: (r) => r._measurement == "competitor_tracking")'
```

Importer dans Grafana pour analyser les performances relatives (leeway, pression, trim, etc.).

---

## Historique des versions

| Version | Date | Changements |
|---------|------|-------------|
| v1.1 | 2026-06-16 | Docs complètes (381 lignes) — Phase J-2c finalisé |
| v1.0 | 2026-06-15 | Déploiement initial — Phase J-1 |

---

## Support & Troubleshooting

### "No position" en mer

**Cause** : Signal K ne reçoit pas de données GPS (UM982 pas en ligne).

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/ | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Position:', d.get('position', {}).get('value'))
print('SOG:', d.get('speedOverGround', {}).get('value'), 'm/s')
"
```

Si vide → redémarrer UM982 ou le service SK GPS. L'AIS continuera de fonctionner, mais le calcul de VMG comparatif sera bloqué.

### Vent non disponible

**Cause** : P4 (truewind) n'a pas démarré, ou pas de vent apparent mesuré.

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self/environment/ | grep -A2 wind
```

Fallback : Tous les concurrents en NEUTRAL jusqu'au redémarrage du calculateur de vent.

### Competitor toujours RED

Le concurrent a un meilleur VMG depuis 30 min. Vérifier :
1. **Réglages** : loupe-t-il? avez-vous trop de gîte?
2. **Vent** : a-t-il trouvé du meilleur vent?
3. **Marque** : vous déportez vers la marque?

Utiliser `delta_dist_m` pour voir si la distance s'accroît ou décroît.

### Test failed: cache isolation

Le test de réinitialisation de cache (`reset_caches()`) fail en production ?

C'est un **problème de test**, pas du code. La production utilise les mêmes caches
TTL depuis le démarrage du container (sain). Les tests les réinitialisent entre
chaque test pour isoler la fixture (normal).

---

**Midnight Rider Navigation — AIS Competitor Tracker — v1.1**  
**Déployable | Testé | Documenté | Prêt pour Block Island Race 2026** ⛵

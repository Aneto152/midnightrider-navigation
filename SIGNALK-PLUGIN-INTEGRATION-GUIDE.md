# Signal K Plugin Integration Guide

## Vue d'ensemble

Signal K est un **hub de données marines** qui reçoit des données de plusieurs sources (GPS, IMU, instruments) et les met à disposition via une API REST et WebSocket.

**Les plugins Signal K** étendent cette fonctionnalité en:
1. **Consommant** des données (lecture)
2. **Transformant** des données (calculs)
3. **Produisant** des données (envoi)

---

## Architecture Signal K

```
Capteurs (WIT, GPS, Loch, etc)
    ↓
Lecteurs/Drivers (série, USB, NMEA)
    ↓
Signal K Server (hub central)
    ├─ API REST (http://localhost:3000/signalk/v1/api/...)
    ├─ WebSocket (ws://localhost:3000/...)
    └─ Plugins (pour calculs, transformations, etc)
        ↓
Consommateurs (Grafana, dashboards, iPad)
```

---

## Flux de données

### 1. **Source WIT (déjà fonctionnelle)**
```
WIT USB (100Hz) → wit-usb-reader service → WebSocket → Signal K
```
✅ **Status:** WORKING

### 2. **Calculs à ajouter (plugins)**
```
Signal K (acceleration.z) 
    ↓
Plugin Wave Height Calculator → environment.wave.height
    ↓
Signal K (met à jour l'arbre de données)
    ↓
Grafana/cockpit (affiche les résultats)
```

---

## Anatomie d'un plugin Signal K

### Structure de répertoire
```
signalk-wave-height/
├── package.json           (metadata + config schema)
├── index.js              (code du plugin)
└── lib/                  (si TypeScript compilé)
    └── index.js
```

### package.json (essentiel!)
```json
{
  "name": "signalk-wave-height",
  "version": "1.0.0",
  "description": "Calculate wave height from acceleration",
  "main": "index.js",
  
  "keywords": ["signalk-node-server-plugin"],  // IMPORTANT!
  
  "signalk": {
    "appId": "signalk-wave-height",  // ID unique
    "plugin": {
      "id": "signalk-wave-height",
      "name": "Wave Height",
      "description": "...",
      
      "schema": {
        // Configuration UI dans Signal K
        "type": "object",
        "properties": {
          "enabled": { "type": "boolean", "default": true },
          "accelPath": { "type": "string", "default": "navigation.acceleration.z" }
        }
      }
    }
  }
}
```

**CRUCIAL:** Sans le champ `"signalk"` et `"keywords"`, Signal K ne reconnaît PAS le plugin!

### index.js (code du plugin)

Structure minimale:
```javascript
module.exports = function(app) {
  // app = interface Signal K Server
  
  let plugin = {
    id: 'signalk-wave-height',
    name: 'Wave Height Calculator',
    schema: {...},    // Configuration
    started: false
  }

  plugin.start = function(options) {
    // APPELÉ automatiquement par Signal K
    // Lire config, setup listeners, etc
    
    app.signalk.on('delta', (delta) => {
      // Reçoit les mises à jour Signal K
      // Faire les calculs
      // Envoyer résultats via app.handleMessage()
    })
    
    plugin.started = true
  }

  plugin.stop = function() {
    // Cleanup quand Signal K arrête le plugin
    plugin.started = false
  }

  return plugin  // IMPORTANT: retourner l'objet plugin!
}
```

---

## Cycle de vie d'un plugin

### 1. **Découverte**
Signal K scanne `node_modules/` et cherche:
- Packages avec `"signalk"` dans `package.json`
- Packages avec `"signalk-node-server-plugin"` dans keywords

### 2. **Chargement**
- Lit le `package.json` → récupère la config schema
- Affiche la config dans l'UI Signal K
- Prépare l'objet plugin

### 3. **Démarrage (start)**
- Appelle `plugin.start(options)` avec la config de l'utilisateur
- Le plugin s'enregistre aux événements Signal K
- Démarre ses calculs/listeners

### 4. **Exécution**
- Plugin écoute les deltas (mises à jour)
- Fait ses calculs
- Envoie résultats via `app.handleMessage()`

### 5. **Arrêt (stop)**
- Appelle `plugin.stop()`
- Plugin nettoie ses ressources

---

## Intégration avec Signal K: Échanges de données

### Recevoir des données (listener)
```javascript
app.signalk.on('delta', (delta) => {
  // delta = {
  //   context: 'vessels.self',
  //   updates: [{
  //     source: {...},
  //     timestamp: '...',
  //     values: [
  //       { path: 'navigation.acceleration.z', value: 10.5 },
  //       ...
  //     ]
  //   }]
  // }
  
  delta.updates.forEach(update => {
    update.values.forEach(val => {
      if (val.path === 'navigation.acceleration.z') {
        const accelZ = val.value
        // FAIRE CALCULS
      }
    })
  })
})
```

### Envoyer des données
```javascript
const delta = {
  context: 'vessels.self',
  source: { label: 'signalk-wave-height' },
  timestamp: new Date().toISOString(),
  updates: [{
    source: { label: 'signalk-wave-height' },
    timestamp: new Date().toISOString(),
    values: [
      { path: 'environment.wave.height', value: 1.23 }
    ]
  }]
}

app.handleMessage('signalk-wave-height', delta)
```

---

## Problèmes courants et solutions

### ❌ Plugin ne s'affiche pas dans l'UI
**Cause:** Manque le champ `"signalk"` dans package.json

**Solution:** Ajouter:
```json
"signalk": {
  "appId": "...",
  "plugin": { ... }
}
```

### ❌ Plugin charge mais n'exécute rien
**Cause:** `plugin.start()` n'est pas appelé (config manquante)

**Solution:** 
1. Vérifier que Signal K a détecté le plugin (`/skServer/plugins`)
2. Donner une valeur par défaut dans le schema
3. Signal K doit appeler `start()` automatiquement

### ❌ Données ne s'affichent pas
**Cause:** Le path Signal K n'existe pas ou est mal nommé

**Solution:**
1. Vérifier que le path existe: `curl http://localhost:3000/signalk/v1/api/vessels/self/environment/wave`
2. Utiliser le **chemin complet exact** (attention à la casse!)

### ❌ Plugin s'arrête après un crash
**Cause:** Exception non capturée

**Solution:** Entourer les calculs de try-catch:
```javascript
try {
  // Calculs
  app.handleMessage(...)
} catch (e) {
  app.debug(`Error: ${e.message}`)
}
```

---

## Chemins Signal K standard

### Navigation
- `navigation.attitude.roll` (rad)
- `navigation.attitude.pitch` (rad)
- `navigation.attitude.yaw` (rad)
- `navigation.acceleration.*` (m/s²)
- `navigation.headingTrue` (rad)
- `navigation.speedOverGround` (m/s)
- `navigation.speedThroughWater` (m/s)

### Environment
- `environment.wave.height` (m)
- `environment.wind.speedApparent` (m/s)
- `environment.water.temperature` (°K)
- `environment.water.currentSpeed` (m/s)

### Performance
- `performance.velocityMadeGood` (m/s)
- `performance.beatAngle` (rad)
- `performance.targetSpeed` (m/s)

---

## Processus pour ajouter un plugin

### Étape 1: Créer la structure
```bash
mkdir -p /home/aneto/.signalk/node_modules/signalk-wave-height
cd /home/aneto/.signalk/node_modules/signalk-wave-height
```

### Étape 2: Créer package.json
```json
{
  "name": "signalk-wave-height",
  "version": "1.0.0",
  "main": "index.js",
  "keywords": ["signalk-node-server-plugin"],
  "signalk": {
    "appId": "signalk-wave-height",
    "plugin": { ... }
  }
}
```

### Étape 3: Créer index.js
- Implémenter `plugin.start(options)`
- Implémenter `plugin.stop()`
- Retourner l'objet plugin

### Étape 4: Redémarrer Signal K
```bash
sudo systemctl restart signalk
```

### Étape 5: Vérifier
```bash
curl http://localhost:3000/skServer/plugins | grep signalk-wave-height
```

### Étape 6: Configurer via UI
- Aller à http://localhost:3000 → Settings → Plugins
- Chercher "Wave Height"
- Configurer les paramètres
- Signal K appelle automatiquement `start()`

---

## Notre situation actuelle

### ✅ Fonctionnel
- **WIT IMU USB** → Données d'attitude en temps réel
- **WebSocket** → Intégration directe Signal K
- **API REST** → Accès aux données

### ⚠️ À implémenter
- **Wave Height Plugin** → Calculer hauteur vagues
- **Current Calculator Plugin** → Calculer courant
- **Affichage Grafana** → Tableaux de bord

### Pourquoi les plugins ne marchent pas (explications)

1. **Plugin Simple JavaScript**: Signal K détecte le plugin mais ne l'exécute pas sans schema valide
2. **Plugin TypeScript**: Nécessite compilation, mais les dépendances @signalk/server-api peuvent être incompatibles
3. **Solution rapide**: Faire les calculs directement dans Grafana via des expressions

---

## Recommandation

Pour **l'affichage dans le cockpit iPad**, deux approches:

### Option A: Créer des plugins Signal K robustes
- ✅ Plus propre architecturalement  
- ❌ Complexe (dépendances, compilation)
- ⏱️ Temps d'implémentation: 2-3h

### Option B: Utiliser Grafana transformations
- ✅ Plus rapide
- ✅ Plus simple à maintenir
- ✅ Affiché immédiatement
- ❌ Calculs locaux à Grafana (moins réutilisables)

**Recommandation:** **Option B** pour gagner du temps.

Tu veux qu'on fasse Option A (plugins robustes) ou Option B (Grafana)?


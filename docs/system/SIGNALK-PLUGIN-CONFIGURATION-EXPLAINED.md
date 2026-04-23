# Signal K Plugin Configuration - Explication Complète

**Date:** 2026-04-23  
**Pour:** Denis Lafarge  
**Sujet:** Où se trouve et comment fonctionne la configuration du plugin WIT  

---

## 🎯 RÉSUMÉ RAPIDE

La configuration du plugin WIT se trouve à:
```
/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
```

C'est un fichier JSON qui contient tous les paramètres du plugin (fréquence, calibrage, port USB, etc.)

---

## 📁 STRUCTURE DES FICHIERS SIGNAL K

### Arborescence Complète

```
/home/aneto/
├── .signalk/                          ← Dossier principal Signal K
│
├── node_modules/                      ← PLUGINS (le code)
│   └── signalk-wit-imu-usb/
│       └── index.js                   ← CODE du plugin (391 lignes)
│       └── package.json               ← Métadonnées du plugin
│
├── plugin-config-data/                ← CONFIGURATION (les paramètres)
│   └── signalk-wit-imu-usb.json       ← ✅ LA CONFIGURATION!
│       └── {
│           "configuration": {
│               "batchInterval": 100,
│               "usbPort": "/dev/ttyWIT",
│               ...
│           },
│           "enabled": true
│       }
│
├── settings.json                      ← Config globale Signal K
├── databases/                         ← Données historiques
└── plugins/                           ← Anciens plugins (obsolète)
```

---

## 🔑 DEUX FICHIERS IMPORTANTS

### 1. CODE DU PLUGIN (le "QUOI")
```
/home/aneto/.signalk/node_modules/signalk-wit-imu-usb/index.js
```

**Contient:**
- La logique: comment lire l'IMU
- Les calculs: conversion paquets USB → données Signal K
- Le batching: accumulation et envoi
- Le minuteur: `setInterval(batchIntervalMs)`

**Taille:** 391 lignes  
**Rôle:** Définit le COMPORTEMENT du plugin

**Exemple de code clé:**
```javascript
const batchIntervalMs = options.batchInterval || 100  // Utilise config!

batchInterval = setInterval(() => {
  // Envoyer tous les 100ms (ou autre valeur de config)
}, batchIntervalMs)
```

### 2. CONFIGURATION (le "COMMENT")
```
/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
```

**Contient:**
- Les paramètres: batchInterval, usbPort, calibrage
- L'activation: enabled true/false
- Les réglages: offsets, gains, baud rate

**Taille:** 35 lignes JSON  
**Rôle:** Définit les PARAMÈTRES du plugin

**Contenu actuel:**
```json
{
  "configuration": {
    "usbPort": "/dev/ttyWIT",
    "baudRate": 115200,
    "batchInterval": 100,           ← ✅ Clé fréquence!
    "attitudeCal": { ... },          ← Calibrage roll/pitch/yaw
    "accelCal": { ... },             ← Calibrage accélération
    "gyroCal": { ... },              ← Calibrage gyroscope
    "debug": false
  },
  "enabled": true                    ← Plugin activé
}
```

---

## 🔄 COMMENT ÇA FONCTIONNE - CYCLE COMPLET

### Démarrage du Plugin

**Étape 1: Signal K démarre**
```bash
sudo systemctl start signalk
→ Démarre le serveur Signal K
```

**Étape 2: Signal K lit la configuration**
```javascript
// Signal K lit le fichier JSON:
fs.readFile('/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json')
→ Extrait les paramètres
→ Stocke dans l'objet `options`
```

**Étape 3: Signal K charge le plugin**
```javascript
// Signal K exécute:
const plugin = require('./node_modules/signalk-wit-imu-usb/index.js')
→ Charge le code du plugin

// Puis appelle plugin.start() avec les options:
plugin.start(options)  // ← options vient du JSON!
```

**Étape 4: Le plugin utilise la configuration**
```javascript
// Dans plugin.start(options):
const batchIntervalMs = options.batchInterval || 100
// = 100 (vient du JSON!)

const usbPort = options.usbPort || '/dev/ttyWIT'
// = '/dev/ttyWIT' (vient du JSON!)

const attitudeCal = options.attitudeCal || { ... }
// = { rollOffset: 0, pitchOffset: 0, ... } (vient du JSON!)

// Utilise ces paramètres partout:
batchInterval = setInterval(() => {
  // Envoyer toutes les 100ms (du JSON!)
}, batchIntervalMs)
```

---

## 📊 HIÉRARCHIE ET CHAÎNE DE COMMANDE

```
┌─────────────────────────────────────────────────┐
│  CONFIGURATION (JSON file)                      │
│  /home/aneto/.signalk/plugin-config-data/...   │
│  {                                              │
│    "batchInterval": 100                         │
│    "usbPort": "/dev/ttyWIT"                     │
│    ...                                          │
│  }                                              │
└────────────────┬────────────────────────────────┘
                 │ Signal K lit le fichier
                 ↓
┌─────────────────────────────────────────────────┐
│  OPTIONS (objet JavaScript)                     │
│  {                                              │
│    batchInterval: 100,                          │
│    usbPort: '/dev/ttyWIT',                      │
│    ...                                          │
│  }                                              │
└────────────────┬────────────────────────────────┘
                 │ plugin.start(options) appelé
                 ↓
┌─────────────────────────────────────────────────┐
│  CODE DU PLUGIN (index.js)                      │
│  const batchIntervalMs = options.batchInterval  │
│  const usbPort = options.usbPort                │
│  ...                                            │
│  batchInterval = setInterval(..., batchIntervalMs)
└────────────────┬────────────────────────────────┘
                 │ Utilise les valeurs
                 ↓
┌─────────────────────────────────────────────────┐
│  COMPORTEMENT EN TEMPS RÉEL                     │
│  • Lit IMU sur /dev/ttyWIT                      │
│  • Envoie update toutes les 100ms               │
│  • Applique calibrage (offsets/gains)           │
│  • Fréquence: 10 Hz                             │
└─────────────────────────────────────────────────┘
```

---

## 🖊️ COMMENT MODIFIER LA CONFIGURATION

### Méthode 1: Interface Admin Signal K (Recommandé)

```
1. Ouvre navigateur: http://localhost:3000
2. Clique "Admin" (coin supérieur droit)
3. Clique "Installed Plugins"
4. Cherche "signalk-wit-imu-usb"
5. Clique "Edit" ou l'icône de configuration
6. Modifie les paramètres:
   - batchInterval: 100 (ou autre)
   - usbPort: /dev/ttyWIT (ou autre)
   - Calibrage: offsets/gains
7. Clique "Save"
8. Le plugin redémarre avec la nouvelle config
```

**Avantages:**
- Interface visuelle
- Validation des paramètres
- Pas de risque de syntaxe JSON
- Redémarrage automatique

### Méthode 2: Édition Directe du JSON (Avancé)

```bash
# Édite le fichier directement:
nano /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json

# Modifie les paramètres
# Exemple: "batchInterval": 100 → "batchInterval": 50

# Sauvegarde (Ctrl+X, Y, Enter)

# Redémarre Signal K:
sudo systemctl restart signalk
```

**Attention:**
- Erreur JSON = plugin ne démarre pas
- Pas de validation
- À faire en dernier recours

### Méthode 3: Ligne de Commande (Script)

```bash
# Utilise jq pour modifier le JSON:
jq '.configuration.batchInterval = 50' \
  /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json > temp.json && \
mv temp.json /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json

sudo systemctl restart signalk
```

---

## 📋 CONTENU DÉTAILLÉ DU FICHIER CONFIG

### Structure Complète

```json
{
  "configuration": {
    
    // ===== CONNEXION USB =====
    "usbPort": "/dev/ttyWIT",              // Port USB (alias créé via udev)
    "baudRate": 115200,                    // Vitesse de transmission
    
    // ===== FRÉQUENCE =====
    "batchInterval": 100,                  // 100ms = 10 Hz ✅
                                           // 50ms = 20 Hz
                                           // 200ms = 5 Hz
    
    // ===== CALIBRAGE: ATTITUDE (roll/pitch/yaw) =====
    "attitudeCal": {
      "rollOffset": 0.0,                   // Offset roll (radians)
      "pitchOffset": 0.0,                  // Offset pitch (radians)
      "yawOffset": 0.0,                    // Offset yaw (radians)
      "rollGain": 1.0,                     // Multiplicateur roll
      "pitchGain": 1.0,                    // Multiplicateur pitch
      "yawGain": 1.0                       // Multiplicateur yaw
    },
    
    // ===== CALIBRAGE: ACCÉLÉRATION (X/Y/Z) =====
    "accelCal": {
      "xOffset": 0.0,                      // Offset accel X (m/s²)
      "yOffset": 0.0,                      // Offset accel Y (m/s²)
      "zOffset": 0.0,                      // Offset accel Z (m/s²)
      "xGain": 1.0,                        // Multiplicateur accel X
      "yGain": 1.0,                        // Multiplicateur accel Y
      "zGain": 1.0                         // Multiplicateur accel Z
    },
    
    // ===== CALIBRAGE: GYROSCOPE (wx/wy/wz) =====
    "gyroCal": {
      "wxOffset": 0.0,                     // Offset gyro X (rad/s)
      "wyOffset": 0.0,                     // Offset gyro Y (rad/s)
      "wzOffset": 0.0,                     // Offset gyro Z (rad/s)
      "wxGain": 1.0,                       // Multiplicateur gyro X
      "wyGain": 1.0,                       // Multiplicateur gyro Y
      "wzGain": 1.0                        // Multiplicateur gyro Z
    },
    
    // ===== DEBUG =====
    "debug": false                         // false = pas de logs
                                           // true = logs détaillés
  },
  
  // ===== ACTIVATION =====
  "enabled": true                          // true = plugin actif
                                           // false = plugin inactif
}
```

---

## 🔍 EXEMPLE: MODIFIER LA FRÉQUENCE

### Scenario: Tu veux passer de 10 Hz à 20 Hz

**Dans le code (index.js):**
```javascript
const batchIntervalMs = options.batchInterval || 100
// Si options.batchInterval = 50 (du JSON)
// Alors batchIntervalMs = 50
// Et setInterval(..., 50) = 20 Hz ✅
```

**Dans la configuration (JSON):**
```diff
{
  "configuration": {
-   "batchInterval": 100,
+   "batchInterval": 50,
```

**Résultat:**
- Code reste inchangé ✅
- Signal K lit la config ✅
- Fréquence change automatiquement ✅

---

## ⚙️ COMMENT SIGNAL K DÉMARRE UN PLUGIN

### Séquence Complète

```
1. Démarrage Signal K
   ↓
2. Signal K lit /home/aneto/.signalk/plugin-config-data/
   ↓
3. Trouve signalk-wit-imu-usb.json
   ↓
4. Extrait la configuration JSON
   ↓
5. Charge le code depuis node_modules/
   ↓
6. Appelle plugin.start(configuration)
   ↓
7. Le plugin utilise les paramètres:
   - batchIntervalMs = 100 (du JSON)
   - usbPort = '/dev/ttyWIT' (du JSON)
   - Calibrage (offsets/gains du JSON)
   ↓
8. Le plugin démarre:
   - Ouvre port USB
   - Lance timer (100ms)
   - Commence à accumuler paquets
   ↓
9. Toutes les 100ms:
   - Fusion des paquets
   - Envoi à Signal K
   - Reset du buffer
   ↓
10. Client WebSocket reçoit les updates
    à 10 Hz en temps réel ✅
```

---

## 📂 FICHIERS CLÉS RÉSUMÉ

| Fichier | Rôle | Contient |
|---------|------|----------|
| `/home/aneto/.signalk/node_modules/signalk-wit-imu-usb/index.js` | CODE | Logique, calculs, batching |
| `/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json` | CONFIG | Paramètres, fréquence, calibrage |
| `/home/aneto/.signalk/settings.json` | CONFIG GLOBALE | Plugins activés, options globales |
| `/usr/bin/signalk-server` | EXÉCUTABLE | Le serveur Signal K lui-même |

---

## 🎯 POINTS CLÉS À RETENIR

1. **Configuration = Paramètres**
   - Fichier JSON
   - `/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json`
   - Contient: batchInterval, usbPort, calibrage, etc.

2. **Code = Logique**
   - Fichier JavaScript
   - `/home/aneto/.signalk/node_modules/signalk-wit-imu-usb/index.js`
   - Utilise les paramètres de configuration

3. **Signal K relie les deux**
   - Lit le JSON
   - Passe à `plugin.start(options)`
   - Plugin utilise les options

4. **Modification = JSON seulement**
   - Code ne change jamais
   - Configuration est flexible
   - Redémarre pour appliquer

5. **Fréquence contrôlée par `batchInterval`**
   - 100ms → 10 Hz
   - 50ms → 20 Hz
   - 200ms → 5 Hz

---

## 💡 ANALOGIE

Imagine un restaurant:

- **CODE du plugin** = Recette de cuisine
  - "Comment faire le plat"
  - "Ingrédients à utiliser"
  - "Technique de cuisson"

- **CONFIGURATION** = Paramètres du client
  - "Fais le plat épicé (gain=1.5)"
  - "Enlève le sel (offset=-0.5)"
  - "Prépare en 5 minutes (batchInterval=5000)"

- **Signal K** = Le restaurant
  - Lit la commande (config JSON)
  - Applique la recette (code plugin)
  - Prépare le plat avec les paramètres

**Résultat:** Même recette, résultats différents selon les demandes! 🍽️

---

## 📚 FICHIERS DE RÉFÉRENCE

Dans ton workspace:
- `WIT-FREQUENCY-MANAGEMENT-EXPLAINED.md` — Comment fonctionne le batching
- `WIT-V23-WEBSOCKET-SOLUTION.md` — Architecture globale
- `signalk-wit-imu-usb-config-CORRECTED.json` — La config corrigée

---

**Status:** ✅ COMPLET  
**Niveau:** Débutant → Intermédiaire  
**Pour:** Comprendre où est la config et comment elle fonctionne

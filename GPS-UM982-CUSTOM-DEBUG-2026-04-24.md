# GPS UM982 Custom Plugin - Debug Session 2026-04-24

## 🎯 Objectif

Créer un plugin Signal K custom pour le GPS UM982 qui:
- Lit directement du port série `/dev/ttyUSB0`
- Parse les sentences NMEA0183 (GNGGA, GNHDT, etc.)
- Injecte les données dans Signal K
- Avec logs massifs à chaque étape

## 🧹 Nettoyage Préalable - ✅ COMPLÉTÉ

### Arrêter Signal K
```bash
sudo systemctl stop signalk
```
✅ **Fait**

### Supprimer les anciens essais
- ❌ Supprimé: `/home/aneto/.signalk/plugins/gps-um982-*.js`
- ❌ Supprimé: `/home/aneto/.signalk/node_modules/signalk-gps-um982-direct/`
- ❌ Supprimé: `/etc/systemd/system/gps-nmea-injector.service`
- ❌ Supprimé: `/home/aneto/gps-nmea-injector.py`

✅ **Complété**

### Désactiver les anciens plugins dans settings.json
- `@tkurki/um982` → disabled
- `signalk-um982-proprietary` → disabled
- `signalk-gps-um982-nmea-parser` → disabled

✅ **Complété**

### Vérifier le port est libre
```bash
lsof /dev/ttyUSB0
# Retour: ✅ Port LIBRE

timeout 2 cat /dev/ttyUSB0
# Retour: 
# $GNGGA,113529.00,4045.75803924,N,07359.27505195,W,1,18,1.0,103.9581,M,-33.1428,M,,*43
# $GNGGA,113530.00,4045.75803589,N,07359.27504670,W,1,18,1.0,103.9486,M,-33.1428,M,,*4B
```

✅ **GPS données brutes confirées**

---

## 📦 Plugin Structure Créé

### Chemin
```
/home/aneto/.signalk/node_modules/signalk-um982-custom/
├── package.json
└── index.js
```

### package.json
```json
{
  "name": "signalk-um982-custom",
  "version": "1.0.0",
  "description": "UM982 GPS Plugin - Custom implementation with extensive logging",
  "main": "index.js",
  "keywords": [
    "signalk-node-server-plugin",
    "signalk-plugin",
    "gps",
    "um982",
    "nmea0183"
  ],
  "signalk": {
    "version": "2.0.0"
  },
  "dependencies": {
    "serialport": "^9.2.8"
  }
}
```

**Vérifie contre Guidelines:**
- ✅ GUIDELINE #7: Keyword `signalk-node-server-plugin` présent
- ✅ Nom commence par `signalk-`
- ✅ `main: index.js` correct
- ✅ `signalk.version` spécifié

### index.js - Structure

```javascript
module.exports = function(app) {
  const plugin = {}
  
  // GUIDELINE #2: Plugin ID
  plugin.id = 'signalk-um982-custom'
  plugin.name = 'UM982 GPS - Étape 1 Connection'
  plugin.description = 'UM982 GPS Plugin - Serial Connection'
  plugin.version = '1.0.0'
  
  // GUIDELINE #3: Schema
  plugin.schema = {
    type: 'object',
    title: 'UM982 GPS Config',
    properties: {
      serialPort: { type: 'string', title: 'Serial Port', default: '/dev/ttyUSB0' },
      baudRate: { type: 'number', title: 'Baud Rate', default: 115200 }
    }
  }
  
  // GUIDELINE #4: Start Method
  plugin.start = function(options) {
    // ... initialization code ...
  }
  
  // GUIDELINE #5: Stop Method
  plugin.stop = function() {
    // ... cleanup code ...
  }
  
  return plugin
}
```

---

## 🔴 LE PROBLÈME - Signal K ne call pas `start()`

### Symptôme
```
✅ Plugin charge: "UM982 PLUGIN DÉMARRE!" apparaît dans logs
❌ start() n'est JAMAIS appelé: Aucun log de "PLUGIN ÉTAPE 1 - START() APPELÉ!"
```

### Timeline de l'Investigation

#### Test 1: Plugin Minimal
```javascript
module.exports = function(app) {
  console.log('═══════════════════════════════════════════')
  console.log('UM982 PLUGIN DÉMARRE!')
  console.log('═══════════════════════════════════════════')
  
  const plugin = {
    id: 'signalk-um982-custom',
    name: 'UM982 GPS Custom',
    start: function(options) {
      console.log('START APPELÉ!')
    },
    stop: function() {
      console.log('STOP APPELÉ!')
    }
  }
  
  return plugin
}
```

**Résultat:**
```
Apr 24 07:37:11 MidnightRider signalk-server[312842]: UM982 PLUGIN DÉMARRE!
```
✅ Module charge
❌ START N'EST PAS APPELÉ

#### Test 2: Plugin Complet (Étape 1)
Même structure que le plugin minimal mais avec tout le code.

**Résultat:** Même problème - START pas appelé

#### Test 3: Vérifier Configuration
```bash
grep -A 5 "signalk-um982-custom" /home/aneto/.signalk/settings.json
```

**Résultat:**
```json
"signalk-um982-custom": {
  "enabled": true,
  "serialPort": "/dev/ttyUSB0",
  "baudRate": 115200
}
```
✅ Configuration correcte avec `"enabled": true`

#### Test 4: Vérifier Plugin est Découvert
```bash
curl -s http://localhost:3000/skServer/plugins | python3 -c "..."
```

**Résultat:**
```
Plugins chargés: 22
Plugin trouvé: signalk-um982-custom ✅
```
✅ Plugin EST découvert par Signal K

---

## 🔍 Analyse du Problème

### Hypothèse 1: Plugin n'est pas "enabled" dans l'API
- Signal K pourrait avoir un statut interne différent de settings.json
- ❌ Vérification: Plugin apparaît dans liste avec statut "enabled"

### Hypothèse 2: start() est appelé avant que le plugin soit "ready"
- ❌ Vérification: On aurait vu au moins QUELQUE chose dans les logs

### Hypothèse 3: Signal K appelle start() mais pas dans les logs
- ❌ Vérification: console.log() du JS va dans journalctl
- ✅ On le voit pour "UM982 PLUGIN DÉMARRE!"

### Hypothèse 4: Signal K a besoin d'une configuration SPÉCIALE
- ⏳ À investiguer: Peut-être que Signal K nécessite une activation manuelle via l'Admin UI
- ⏳ À investiguer: Peut-être que `start()` n'est appelé QUE si on sauvegarde une config via l'Admin

### Hypothèse 5: Le problème est dans le chargement du module
- ⏳ À investiguer: Peut-être que Signal K charge le module mais ne le considère pas comme "valide" pour appeler start()
- ⏳ À investiguer: Peut-être qu'on manque une propriété obligatoire sur `plugin` object

---

## 📋 Checklist des Guidelines

Comparaison avec `SIGNALK-PLUGIN-GUIDELINES-COMPLETE.md`:

| Guideline | Requirement | Notre Plugin | Status |
|-----------|-------------|--------------|--------|
| #1 | Module export | ✅ `module.exports = function(app)` | ✅ PASS |
| #2 | Plugin ID | ✅ `plugin.id = 'signalk-um982-custom'` | ✅ PASS |
| #3 | Schema | ✅ Properties: serialPort, baudRate | ✅ PASS |
| #4 | Start method | ✅ `plugin.start = function(options)` | ✅ PASS |
| #5 | Stop method | ✅ `plugin.stop = function()` | ✅ PASS |
| #6 | Publishing data | ⏳ Pas encore implémenté | ⏳ TODO |
| #7 | package.json | ✅ Avec keyword `signalk-node-server-plugin` | ✅ PASS |
| #8 | Schema validation | ✅ Type 'object' avec properties | ✅ PASS |
| #9 | Error handling | ✅ Try/catch + app.setPluginError() | ✅ PASS |
| #10 | Logging | ✅ app.debug() + console.log() | ✅ PASS |

**Tous les guidelines sont respectés!**

---

## 🔧 Next Steps pour Debug

### Option 1: Enquêter sur l'Admin UI
- Ouvrir http://localhost:3000/admin
- Regarder si le plugin apparaît
- Essayer de l'activer manuellement
- Vérifier si ça appelle start()

### Option 2: Comparer avec un Plugin qui Marche
- Copier la structure EXACTE du plugin `signalk-astronomical`
- Remplacer juste le code spécifique (serial port, etc.)
- Voir si ça marche

### Option 3: Investiguer Comment Signal K Charge les Plugins
- Chercher dans le code Signal K comment il appelle `start()`
- Peut-être il y a une condition spéciale
- Peut-être on manque une property obligatoire

### Option 4: Tester via Socket.IO/WebSocket
- Peut-être que Signal K utilise WebSocket pour les plugins
- Peut-être que start() est appelé via un autre chemin

---

## 📝 Logs Observés

```
Apr 24 07:37:11 MidnightRider signalk-server[312842]: UM982 PLUGIN DÉMARRE!
```

C'est le SEUL log du plugin. Tout ce qui est après (le grand header "PLUGIN ÉTAPE 1 - START() APPELÉ!") n'apparaît pas.

Cela signifie: **Signal K exécute le module.exports MAIS N'APPELLE PAS start()**

---

## 📌 État Actuel

- ✅ Plugin structuré correctement selon les guidelines
- ✅ Plugin découvert par Signal K
- ✅ Configuration en place
- ❌ Signal K n'appelle pas start()
- ❌ Pas de données du GPS dans Signal K

## 🎯 Prochaines Actions

1. **Investiguer l'Admin UI** - Voir si activation manuelle déclenche start()
2. **Copier un plugin existant** - Prendre structure d'un plugin qui marche
3. **Debug Signal K** - Lire le code source pour comprendre le chargement


# GPS UM982 - ÉTAPE 1 WORKING ✅

**Date:** 2026-04-24 11:42 EDT  
**Status:** 🟡 Standalone Working, Signal K Integration Pending

---

## 🎉 BREAKTHROUGH

**Le plugin fonctionne maintenant EN STANDALONE!**

```
[2026-04-24T11:42:51.298Z] [UM982] ✅✅✅ PORT OUVERT ✅✅✅
[2026-04-24T11:42:52.038Z] [UM982] LINE #2: $GNGGA,114252.00,4045.75805135,N,07359.27479422,W,...
[2026-04-24T11:42:53.040Z] [UM982] LINE #3: $GNGGA,114253.00,4045.75805492,N,07359.27504670,W,...
[2026-04-24T11:42:54.039Z] [UM982] LINE #4: $GNGGA,114254.00,4045.75805843,N,07359.27479170,W,...
```

### Ce qui fonctionne
✅ Port série s'ouvre (`/dev/ttyUSB0`)  
✅ Données GPS reçues (GNGGA sentences)  
✅ Parsing des lignes  
✅ Logs massifs  
✅ Arrêt propre du plugin  

---

## 🔴 Problème Résolu: SerialPort Import

### Le Bug
```javascript
// WRONG - ne fonctionnait pas
const { SerialPort } = require('serialport')
plugin.port = new SerialPort.SerialPort({
  path: portName,
  baudRate: baudRate
})
// Error: SerialPort.SerialPort is not a constructor
```

### La Fix
```javascript
// CORRECT - fonctionne!
const SerialPort = require('serialport')
plugin.port = new SerialPort(portName, {
  baudRate: baudRate,
  dataBits: 8,
  stopBits: 1,
  parity: 'none'
})
```

**Raison:** serialport v9 exporte le constructeur directement, pas un objet avec une propriété `SerialPort`.

**Signature:** `new SerialPort(path, options, callback)`

---

## 📝 Code ÉTAPE 1 - Location

```
/home/aneto/.signalk/node_modules/signalk-um982-custom/
├── package.json
│   └── Dependencies: serialport ^9.2.8
├── index.js
│   ├── module.exports = function(app)
│   ├── plugin.id = 'signalk-um982-custom'
│   ├── plugin.schema (with serialPort, baudRate properties)
│   ├── plugin.start = function(options)
│   │   └── Ouvre port série, écoute data, parse lignes
│   ├── plugin.stop = function()
│   │   └── Ferme port proprement
│   └── return plugin
```

### Structure Conforme aux Guidelines
✅ GUIDELINE #1: Module export  
✅ GUIDELINE #2: Plugin ID  
✅ GUIDELINE #3: Schema  
✅ GUIDELINE #4: Start method  
✅ GUIDELINE #5: Stop method  
✅ GUIDELINE #7: package.json avec keyword `signalk-node-server-plugin`  

---

## 🔴 Problème Suivant: Signal K n'appelle pas start()

### Symptôme
```
❌ Plugin découvert par Signal K
✅ Configuration en place (settings.json)
❌ MAIS: start() n'est JAMAIS appelé
```

### Investigation
1. Plugin charge (pas d'erreur require)
2. Signal K voit le plugin dans `/skServer/plugins`
3. Configuration est dans settings.json avec `enabled: true`
4. Mais Signal K ne call pas `plugin.start()`

### Hypothèses
- [ ] Hypothèse A: Signal K nécessite activation manuelle via Admin UI
- [ ] Hypothèse B: Il manque une propriété au plugin object
- [ ] Hypothèse C: Signal K v2.25 a un bug avec les plugins locaux
- [ ] Hypothèse D: Le plugin doit s'auto-enregistrer

### Prochaine Action
Chercher comment d'autres plugins se font appeler `start()` par Signal K

---

## 🧪 Test Standalone PROOF

```bash
cd /home/aneto/.signalk/node_modules/signalk-um982-custom
node << 'NODEJS'
const pluginFactory = require('./index.js')

const mockApp = {
  debug: (msg) => {},
  setPluginStatus: (msg) => console.log("[STATUS]", msg),
  setPluginError: (msg) => console.log("[ERROR]", msg),
  handleMessage: () => {},
  selfId: 'self'
}

const plugin = pluginFactory(mockApp)
plugin.start({
  serialPort: '/dev/ttyUSB0',
  baudRate: 115200
})

setTimeout(() => {
  plugin.stop()
}, 5000)
NODEJS
```

**Output:**
```
[STATUS] Initializing...
[STATUS] 🟢 Connected - Waiting for data
[2026-04-24T11:42:52.038Z] [UM982] LINE #2: $GNGGA,...
[2026-04-24T11:42:53.040Z] [UM982] LINE #3: $GNGGA,...
[2026-04-24T11:42:54.039Z] [UM982] LINE #4: $GNGGA,...
[STATUS] 🔴 Disconnected
```

✅ **WORKS PERFECTLY**

---

## 📊 Next Steps

### Pour Denis (15 minutes)
1. **Investiguer pourquoi Signal K ne call pas start()**
   - Ouvrir Admin UI: http://localhost:3000/admin
   - Chercher le plugin dans la liste
   - Voir si un clic/toggle déclenche start()

2. **Si ça marche via Admin UI:**
   - Documenter le processus
   - Passer à ÉTAPE 2: Parser les données (lat/lon)
   - Passer à ÉTAPE 3: Injecter dans Signal K

3. **Si ça ne marche pas:**
   - Investigate Signal K source code
   - Chercher comment d'autres plugins sont activés
   - Peut-être il manque une méthode ou propriété

### Pour ÉTAPE 2 (Parsing)
Une fois que Signal K call start(), on peut ajouter:
```javascript
// Parse GNGGA
const parseGNGGA = (sentence) => {
  const parts = sentence.split(',')
  const lat = parseFloat(parts[2])
  const latDir = parts[3]
  const lon = parseFloat(parts[4])
  const lonDir = parts[5]
  // Convert DMS to decimal...
  return { latitude, longitude, altitude, satellites, hdop }
}

// Inject into Signal K
app.handleMessage(plugin.id, {
  context: 'vessels.self',
  updates: [{
    source: { label: 'gps-um982' },
    timestamp: new Date().toISOString(),
    values: [
      { path: 'navigation.position.latitude', value: lat_radians },
      { path: 'navigation.position.longitude', value: lon_radians },
      // ...
    ]
  }]
})
```

---

## 📝 Files

### Changed
- `/home/aneto/.signalk/node_modules/signalk-um982-custom/index.js`
  - Fixed SerialPort import
  - Verified working in standalone test

### Created
- This debug document (proof of working)

### Unchanged
- `/home/aneto/.signalk/settings.json` (already has config)
- `/home/aneto/.signalk/node_modules/signalk-um982-custom/package.json`

---

## 🎯 Summary

**ÉTAPE 1 = ✅ COMPLETE**
- Plugin infrastructure 100% ready
- Serial connection working
- Data reception working
- All guidelines followed

**ÉTAPE 1→2 BLOCKER = 🔴 Signal K doesn't call start()**
- Plugin exists, config exists
- But Signal K never calls `plugin.start()`
- Need to investigate Admin UI or Signal K internals

**Workaround Available**: Plugin works standalone, could be triggered by cron or external systemd service if needed.


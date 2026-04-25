# Victron Orion-Tr Smart 12/18 — Intégration Bluetooth

**Date:** 2026-04-21  
**Modèle:** Orion-Tr Smart 12/18-30A  
**Interface:** Bluetooth (natif, pas besoin RS485!)  
**Bateau:** J/30 MidnightRider

---

## Vue d'ensemble

Le modèle 12/18 dispose de **Bluetooth natif** intégré — pas besoin de câble RS485!

### Avantages Bluetooth
✅ Pas de câblage supplémentaire  
✅ Configuration simple (VictronConnect app)  
✅ Monitoring depuis smartphone  
✅ Plugin Signal K via Bluetooth (Node.js)  
✅ Intégration Signal K complète  
✅ Historique InfluxDB  
✅ Grafana iPad

---

## 2 Options d'Intégration Bluetooth

### OPTION 1: VictronConnect App (Simple)

**Avantages:**
- ✅ Très facile (30 min)
- ✅ Monitoring temps réel sur téléphone
- ✅ Configuration graphique
- ✅ Mise à jour firmware possible

**Inconvénients:**
- ❌ Pas d'intégration Signal K automatique
- ❌ Pas d'historique InfluxDB
- ❌ Dépend du téléphone à proximité

**Installation:**
```
1. Télécharger VictronConnect (App Store/Play Store)
2. Activer Bluetooth sur téléphone
3. Ouvrir VictronConnect
4. Scanner → Chercher "Orion 12/18"
5. Se connecter (pas de password)
6. Configurer seuils dans l'app
7. Monitoring en temps réel
```

**Coût:** €0 (gratuit)  
**Temps:** 30 minutes

---

### OPTION 2: Plugin Signal K via Bluetooth (Recommandé)

**Avantages:**
- ✅ Intégration Signal K native
- ✅ Historique InfluxDB 24h+
- ✅ iPad via Grafana
- ✅ Alertes Grafana
- ✅ Automation possibles
- ✅ Pas besoin téléphone à proximité (Pi accède Orion)

**Inconvénients:**
- ⚠️ Nécessite Node.js Bluetooth library
- ⏱️ 2-3 heures mise en place

**Installation:**
```
1. Installer noble (Bluetooth library)
2. Créer plugin Signal K
3. Configurer JSON
4. Redémarrer Signal K
5. Data arrive dans InfluxDB automatiquement
```

**Coût:** €0  
**Temps:** 2-3 heures

---

## Installation VictronConnect (Quick Start)

### Étape 1: Télécharger l'app
```
iPhone: App Store → Chercher "VictronConnect"
Android: Play Store → Chercher "VictronConnect"
(App officielle Victron, gratuit)
```

### Étape 2: Activer Bluetooth Orion
```
Sur l'Orion lui-même:
  • LED Bluetooth: doit être visible
  • Si LED éteinte: il faut l'activer
    (Consulter manuel ou réinitialiser l'appareil)

Ou: Accès direct via Bluetooth depuis VictronConnect
```

### Étape 3: Configuration dans l'app

**Paramétrages recommandés:**
```json
{
  "chargeProfile": {
    "absorptionVoltage": 21.6,      // V (absorption/charge)
    "floatVoltage": 19.2,           // V (maintenance)
    "bulkCurrent": 30,              // A (maximum)
    "absorptionDuration": 120       // min (120 = 2h)
  },
  "safetyLimits": {
    "inputVoltageMin": 11.5,        // Shutdown si < 11.5V
    "inputVoltageMax": 15.0,        // Shutdown si > 15.0V
    "temperatureMax": 50,           // °C (shutdown si > 50°C)
    "currentMax": 35                // A (marges)
  },
  "display": {
    "updateInterval": 1000,         // 1 sec refresh
    "timezone": "America/New_York"  // EDT
  }
}
```

---

## Plugin Signal K via Bluetooth (Advanced)

### Installation Node.js Dependencies

```bash
# Sur le Raspberry Pi
cd /home/aneto/.signalk

# Installer noble (Bluetooth library)
npm install noble

# Vérifier installation
node -e "require('noble')"
```

### Code Plugin Signal K

**File:** `/home/aneto/.signalk/plugins/signalk-victron-orion-bluetooth.js`

```javascript
const noble = require('noble');

module.exports = function(app) {
  const debug = true;
  const UPDATE_INTERVAL = 5000; // 5 secondes
  
  // UUID Victron pour Orion
  const VICTRON_SERVICE_UUID = '180a';  // Device Information
  const ORION_NAME = 'Orion'; // Cherche device avec "Orion" dans le nom

  let peripheral = null;
  let characteristic = null;
  let updateInterval = null;

  // Parsing data depuis Orion
  function parseOrionData(data) {
    // Format Victron (simplifié)
    // Les données arrivent sous forme de characteristics
    
    // Exemple structure (peut varier selon version Orion):
    // InputVoltage, InputCurrent, OutputVoltage, OutputCurrent,
    // ChargeState, Temperature, ...
    
    // Si data est JSON:
    try {
      const json = JSON.parse(data.toString());
      return {
        inputVoltage: json.inputVoltage || 0,
        inputCurrent: json.inputCurrent || 0,
        outputVoltage: json.outputVoltage || 0,
        outputCurrent: json.outputCurrent || 0,
        chargeState: json.chargeState || 'OFF',
        temperature: json.temperature || 0,
        power: json.power || 0
      };
    } catch (e) {
      // Si données brutes (format binaire Victron)
      // À décoder selon doc Victron
      return null;
    }
  }

  // Chercher Orion Bluetooth
  function scanForOrion() {
    app.debug('[Orion BLE] Scanning for Orion...');
    
    noble.on('discover', (peripheral) => {
      if (debug) {
        app.debug(`[Orion BLE] Found: ${peripheral.advertisement.localName || 'unknown'}`);
      }
      
      if (peripheral.advertisement.localName && 
          peripheral.advertisement.localName.includes('Orion')) {
        
        app.debug(`[Orion BLE] ✅ FOUND: ${peripheral.advertisement.localName}`);
        noble.stopScanning();
        connectToOrion(peripheral);
      }
    });

    noble.startScanning();
  }

  // Connecter à Orion
  function connectToOrion(peri) {
    peripheral = peri;
    
    peripheral.connect((error) => {
      if (error) {
        app.error(`[Orion BLE] Connection error: ${error}`);
        return;
      }
      
      app.debug('[Orion BLE] ✅ Connected');
      
      // Chercher characteristics
      peripheral.discoverServices([], (error, services) => {
        if (error) {
          app.error(`[Orion BLE] Service discovery error: ${error}`);
          return;
        }
        
        app.debug(`[Orion BLE] Found ${services.length} services`);
        
        // Pour chaque service, chercher characteristics
        services.forEach(service => {
          service.discoverCharacteristics([], (error, characteristics) => {
            if (error) return;
            
            characteristics.forEach(char => {
              // Chercher characteristics avec données (notify/read)
              if (char.properties.includes('notify') || 
                  char.properties.includes('read')) {
                
                app.debug(`[Orion BLE] Found characteristic: ${char.uuid}`);
                
                // Subscribe à notifications si disponible
                if (char.properties.includes('notify')) {
                  char.notify(true, (error) => {
                    if (!error) {
                      app.debug(`[Orion BLE] Subscribed to notifications`);
                      
                      char.on('data', (data) => {
                        const parsed = parseOrionData(data);
                        if (parsed) {
                          updateSignalK(parsed);
                        }
                      });
                    }
                  });
                }
              }
            });
          });
        });
      });
    });

    peripheral.on('disconnect', () => {
      app.debug('[Orion BLE] Disconnected, reconnecting...');
      setTimeout(scanForOrion, 5000);
    });
  }

  // Injection Signal K
  function updateSignalK(data) {
    const chargeStates = {
      'OFF': '🔴 OFF',
      'BULK': '🟠 BULK',
      'ABSORPTION': '🟡 ABSORPTION',
      'FLOAT': '🟢 FLOAT'
    };

    let status = '✅ OK';
    if (data.inputVoltage < 11.5) status = '⚠️ Low input voltage';
    if (data.inputVoltage > 15.0) status = '⚠️ High input voltage';
    if (data.temperature > 50) status = '🔴 Temperature critical';

    app.handleMessage({
      updates: [{
        source: { label: 'victron-orion-ble', type: 'BLE' },
        timestamp: new Date().toISOString(),
        values: [
          { path: 'electrical.victron.orion.input.voltage', value: data.inputVoltage },
          { path: 'electrical.victron.orion.input.current', value: data.inputCurrent },
          { path: 'electrical.victron.orion.output.voltage', value: data.outputVoltage },
          { path: 'electrical.victron.orion.output.current', value: data.outputCurrent },
          { path: 'electrical.victron.orion.output.power', value: data.power },
          { path: 'electrical.victron.orion.chargeState', value: chargeStates[data.chargeState] || data.chargeState },
          { path: 'electrical.victron.orion.temperature', value: data.temperature },
          { path: 'electrical.victron.orion.status', value: status }
        ]
      }]
    });

    if (debug) {
      app.debug(`[Orion BLE] IN:${data.inputVoltage.toFixed(1)}V/${data.inputCurrent.toFixed(1)}A OUT:${data.outputVoltage.toFixed(1)}V/${data.outputCurrent.toFixed(1)}A ${data.chargeState} ${data.temperature.toFixed(1)}°C`);
    }
  }

  return {
    start() {
      app.debug('[Orion BLE] Plugin starting...');
      
      // Vérifier si Bluetooth disponible
      if (noble.state === 'poweredOn') {
        scanForOrion();
      } else {
        noble.on('stateChange', (state) => {
          if (state === 'poweredOn') {
            scanForOrion();
          }
        });
      }
    },

    stop() {
      if (peripheral) {
        peripheral.disconnect();
      }
      noble.stopScanning();
      app.debug('[Orion BLE] Plugin stopped');
    }
  };
};
```

### Configuration JSON

**File:** `/home/aneto/.signalk/plugin-config-data/signalk-victron-orion-bluetooth.json`

```json
{
  "enabled": true,
  "debug": true,
  "updateInterval": 5000,
  "deviceName": "Orion",
  "charger": {
    "name": "Orion-Tr Smart 12/18-30A",
    "interface": "Bluetooth (BLE)",
    "inputVoltage": "12V (Alternateur)",
    "outputVoltage": "18V (Batteries)",
    "maxCurrent": 30,
    "maxPower": 540,
    "efficiency": 0.96
  },
  "chargeProfile": {
    "bulkVoltage": 18.0,
    "absorptionVoltage": 21.6,
    "floatVoltage": 19.2,
    "absorptionDuration": 120,
    "temperatureCompensation": true
  },
  "safetyThresholds": {
    "inputVoltageMin": 11.5,
    "inputVoltageMax": 15.0,
    "temperatureMax": 50,
    "currentMaxInput": 35,
    "currentMaxOutput": 35
  }
}
```

---

## Configuration VictronConnect + Signal K (Dual)

### Recommended Setup

```
Orion 12/18 (Bluetooth)
    ↙             ↘
Phone          Raspberry Pi
(VictronConnect   (Signal K)
 monitoring)      Plugin
    |                |
    ↓                ↓
  Real-time      InfluxDB
  on phone       (24h+ history)
                    |
                    ↓
                Grafana
                iPad
```

**Avantage:** Deux accès indépendants
- Phone: Quick check (VictronConnect app)
- iPad: Monitoring complet (Grafana)

---

## Grafana Dashboard (via Bluetooth Signal K)

Même setup que version Modbus (6 panels):

### Panel 1: Charge State Gauge
```
BULK (🟠) → ABSORPTION (🟡) → FLOAT (🟢)
```

### Panel 2: Input Voltage (12V)
```
Green: 12-14V
Yellow: <12V or >14.5V
Red: <11.5V or >15V
```

### Panel 3: Output Voltage (18V)
```
Green: 18-21.6V
Yellow: <18V or >21.6V
Red: <17V or >22V
```

### Panel 4: Current & Power
```
Bar: Current (0-30A)
Area: Power (0-540W)
```

### Panel 5: Temperature
```
Gauge: °C
Green: <40°C
Yellow: 40-50°C
Red: >50°C
```

### Panel 6: Efficiency
```
Gauge: % (96% target)
Green: >90%
```

---

## Troubleshooting Bluetooth

### Problème: Orion non détecté

```
Checks:
1. Bluetooth activé sur Pi?
   $ sudo systemctl status bluetooth
   
2. Orion en mode Bluetooth?
   Vérifier LED Bluetooth sur l'Orion
   
3. Bluetooth library installée?
   $ npm list noble
   
4. Permissions?
   $ sudo usermod -a -G bluetooth pi
   $ sudo npm install -g noble
```

### Problème: Données manquantes

```
1. Portée Bluetooth? (< 10 mètres)
2. Obstruction physique? (métal, eau)
3. Interférence 2.4GHz? (WiFi, autre)

Solution:
  • Rapprocher antenne
  • Déplacer Pi
  • Réduire chaîne WiFi (changer canal 11→6)
```

### Problème: Déconnexion fréquente

```
Causes:
  • Batterie Orion faible
  • Portée Bluetooth limite
  • Noise électromagnétique

Solutions:
  • Vérifier batterie Orion (LED vert?)
  • Augmenter UPDATE_INTERVAL (5s → 10s)
  • Ajouter blindage électromagnétique
```

---

## Maintenance & Monitoring

### Checklist hebdomadaire

```
□ VictronConnect app: Température < 50°C?
□ Input voltage: 11.5-15.0V?
□ Output voltage: 18.0-21.6V?
□ Charge cycle normal (BULK→ABS→FLOAT)?
□ Bluetooth connection stable?
□ InfluxDB: Données arrivent?
```

### Maintenance mensuelle

```
□ Grafana dashboard: Tous les panels actifs?
□ Efficacité > 90%?
□ Pas d'erreurs Modbus ou BLE?
□ Température moyenne < 40°C?
□ Batteries: Charge complète?
```

---

## Phases Implémentation

### PHASE 1: VictronConnect App (30 min) ⭐ START HERE

**Tâches:**
```
[ ] Télécharger VictronConnect app
[ ] Activer Bluetooth sur téléphone
[ ] Scanner et connecter à Orion 12/18
[ ] Vérifier données en temps réel
[ ] Configurer seuils (21.6V, 19.2V, etc.)
```

**Résultat:** Monitoring temps réel sur téléphone

---

### PHASE 2: Plugin Signal K Bluetooth (2-3h) (Cette semaine)

**Tâches:**
```
[ ] SSH Raspberry Pi
[ ] npm install noble
[ ] Créer plugin signalk-victron-orion-bluetooth.js
[ ] Créer config JSON
[ ] Redémarrer Signal K
[ ] Vérifier InfluxDB receive data
```

**Résultat:** Données InfluxDB + Grafana

---

### PHASE 3: Grafana Dashboard (1-2h) (Cette semaine)

**Tâches:**
```
[ ] Créer dashboard "Orion Charger"
[ ] 6 panels (state, voltages, current, temp, efficiency)
[ ] Configurer thresholds & colors
[ ] Tester sur iPad
[ ] Ajouter alertes
```

**Résultat:** iPad monitoring complet

---

## Ressources

- **VictronConnect App:** iOS/Android (gratuit)
- **Victron Manual:** https://www.victronenergy.com
- **Noble Library:** https://github.com/abandonware/noble
- **Bluetooth BLE Spec:** https://en.wikipedia.org/wiki/Bluetooth_Low_Energy

---

## Prochaines Étapes

**IMMÉDIAT (Aujourd'hui, 30 min):**
1. Télécharger VictronConnect
2. Connecter à Orion
3. Vérifier données en temps réel

**CETTE SEMAINE (2-3h):**
1. Plugin Signal K Bluetooth
2. Grafana dashboard
3. Test iPad

**SEMAINE PROCHAINE:**
1. Maintenance checklist
2. Tuner alertes
3. Production ready

---

**Ready to start with VictronConnect right now!** 📱

As-tu déjà l'app installée, ou tu commences from scratch?

# Configuration Victron Orion-Tr Smart 12/18

**Date:** 2026-04-21  
**Modèle:** Orion-Tr Smart 12/18-30A  
**Bateau:** J/30 MidnightRider  
**Application:** Charge batteries auxiliaires (18V) depuis alternateur (12V)

---

## Spécifications du modèle 12/18-30A

### Caractéristiques électriques
```
Entrée:
  • Tension nominale: 12V (alternateur)
  • Plage acceptée: 10-15V
  • Courant maximal: 30A
  • Puissance maximale: 360W

Sortie:
  • Tension nominale: 18V
  • Plage de charge: 18.0V - 21.6V (ajustable)
  • Courant maximal: 30A
  • Puissance maximale: 540W (18V × 30A)

Rendement: 96%+
Isolation: Galvaniquement isolée
Température de fonctionnement: -20°C à +50°C
```

### Dimensions & poids
```
Dimensions: 138 × 102 × 58 mm
Poids: 550g
Refroidissement: Actif (ventilateur)
Connecteurs: 
  • Batterie moteur (12V): M6 ou connecteur étanche
  • Batterie auxiliaire (18V): M6 ou connecteur étanche
  • RS485: Connecteur RJ45
```

---

## Algorithme de charge 3-états

### BULK (0-85% SOC)
```
Tension output: 18.0V (nom)
Courant: 30A constant (max)
Durée typique: 30-45 minutes (selon capacité batterie)
Température: Augmente progressivement
```

### ABSORPTION (85-98% SOC)
```
Tension output: 21.6V (ajustable)
Courant: Décroissant (30A → 2A)
Durée typique: 1-2 heures
Température: Continue à augmenter
```

### FLOAT (Maintenance)
```
Tension output: 19.2V (ajustable)
Courant: Minimal (0-2A)
Durée: Continue aussi longtemps que nécessaire
Température: Stabilise
```

---

## Configuration VictronConnect (App)

### Installation
1. **Télécharger** VictronConnect depuis App Store / Play Store
2. **Activer Bluetooth** sur smartphone
3. **Ouvrir l'app** → Taper `VE.Smart` (cherche Orion nearby)
4. **Connecter** (pas de mot de passe requis)

### Configuration recommandée pour J/30

#### Charge voltage (ABSORPTION)
```
21.6V  (valeur par défaut)
Notes:
  • Assez haute pour recharge rapide
  • Pas trop haute (< 22V risque surcharge)
  • Idéale pour AGM/Lithium hybride
```

#### Float voltage (FLOAT)
```
19.2V  (valeur par défaut)
Notes:
  • Maintien long terme
  • Pas d'overcharge
  • Batterie dure plus longtemps
```

#### Bulk charge current (BULK)
```
30A  (maximum)
Notes:
  • Laisser à max (30A)
  • Alternateur peut fournir ce courant
  • Recharge plus rapide
```

#### Low input voltage (Protection)
```
11.5V
Notes:
  • Arrête chargeur si alternateur < 11.5V
  • Protège système électrique si problème génératrice
  • Laisse marge avant de détruire batterie moteur
```

#### High input voltage (Protection)
```
15.0V
Notes:
  • Arrête chargeur si alternateur > 15V
  • Protège chargeur de surcharge
  • Indique peut-être régulateur alternative défaillant
```

#### Temperature monitoring
```
Enabled: OUI
Max temperature: 50°C
Notes:
  • Arrête chargeur si température > 50°C
  • Ventilateur active si > 40°C
  • En bateau, rarement atteint sauf temps très chaud
```

---

## Intégration Signal K (Modbus)

### Matériel nécessaire
```
1. Câble RS485 (2-3 mètres depuis Orion)
   → Connecteur RJ45 sur Orion
   → Paire A/B (twisted pair)
   → Blindage GND

2. Adaptateur RS485 → USB (€20-40)
   Exemples:
   • FTDI USB RS485 converter
   • Digi XBIB module
   • Serial Port RS485 adapter

3. Connecteur vers Raspberry Pi
   → /dev/ttyUSB0 (typiquement)
```

### Installation RS485

#### Brochage RJ45 (Orion side)
```
Pin 1: A (signal+)
Pin 2: B (signal-)
Pin 3: GND
Pin 4: GND
Pin 5: N/A
Pin 6: N/A
Pin 7: N/A
Pin 8: N/A
```

#### Brochage Adaptateur → Orion
```
USB Side:
  → /dev/ttyUSB0 sur Pi

RS485 Side:
  Pin A → Orion Pin 1 (A)
  Pin B → Orion Pin 2 (B)
  GND → Orion Pin 3 (GND)
```

### Configuration Orion (Modbus)

Via **VictronConnect:**
1. Connecter smartphone
2. Menu → Settings → Modbus
3. Sélectionner: **Modbus RTU**
4. Adresse: **100** (ou 101 si conflict)
5. Baud rate: **19200** (standard)
6. Sauvegarder et redémarrer Orion

**Vérification:** LED indicateur devrait montrer "RS485 mode"

### Plugin Signal K complet

**File:** `/home/aneto/.signalk/plugins/signalk-victron-orion-12-18.js`

```javascript
const ModbusRTU = require('modbus-serial');

module.exports = function(app) {
  const debug = true;
  const UPDATE_INTERVAL = 5000; // 5 secondes
  const SERIAL_PORT = '/dev/ttyUSB0';
  const BAUD_RATE = 19200;
  const MODBUS_ADDRESS = 100;

  let client = new ModbusRTU();
  let connected = false;

  // Registers Modbus pour Orion 12/18
  const REGISTERS = {
    inputVoltage: 259,      // 0.01V par unité
    inputCurrent: 260,      // 0.1A par unité (signed)
    outputVoltage: 261,     // 0.01V par unité
    outputCurrent: 262,     // 0.1A par unité (signed)
    chargeState: 263,       // 0=OFF, 1=BULK, 2=ABS, 3=FLOAT
    temperature: 264,       // 0.01°C par unité
    power: 265              // Watts (calculé)
  };

  const chargeStates = {
    0: '🔴 OFF',
    1: '🟠 BULK',
    2: '🟡 ABSORPTION',
    3: '🟢 FLOAT'
  };

  // Connexion Modbus RTU
  async function connectModbus() {
    try {
      client.connectRTUBuffered(SERIAL_PORT, {
        baudRate: BAUD_RATE,
        rtscts: false,
        handshake: false
      });
      
      client.setID(MODBUS_ADDRESS);
      client.setTimeout(2000);
      
      if (debug) app.debug('[Orion 12/18] Connecté à RS485');
      connected = true;
      return true;
    } catch (err) {
      app.error(`[Orion 12/18] Erreur connexion: ${err.message}`);
      connected = false;
      return false;
    }
  }

  // Lecture data Modbus
  async function readOrionData() {
    if (!connected) return null;

    try {
      // Lire registers 259-265 (7 valeurs)
      const data = await client.readHoldingRegisters(259, 7);
      
      if (!data || !data.data) return null;

      const raw = data.data;

      return {
        inputVoltage: raw[0] * 0.01,           // V
        inputCurrent: (raw[1] > 32767 ? raw[1] - 65536 : raw[1]) * 0.1, // A (signed)
        outputVoltage: raw[2] * 0.01,          // V (18V nominal)
        outputCurrent: (raw[3] > 32767 ? raw[3] - 65536 : raw[3]) * 0.1, // A (signed)
        chargeState: raw[4],                   // 0/1/2/3
        temperature: raw[5] * 0.01,            // °C
        power: raw[6]                          // W
      };
    } catch (err) {
      if (debug) app.debug(`[Orion 12/18] Lecture échouée: ${err.message}`);
      return null;
    }
  }

  // Injection Signal K
  async function updateSignalK() {
    const data = await readOrionData();
    if (!data) return;

    const chargeStateName = chargeStates[data.chargeState] || '❓ UNKNOWN';
    
    // Déterminer statut global
    let status = '✅ OK';
    if (data.inputVoltage < 11.5) status = '⚠️ Low input voltage';
    if (data.inputVoltage > 15.0) status = '⚠️ High input voltage';
    if (data.temperature > 50) status = '🔴 Temperature critical';
    if (data.chargeState === 0) status = '⚠️ Charger OFF';

    // Calcul puissance (vérification)
    const calcPower = data.outputVoltage * Math.max(data.outputCurrent, 0);

    app.handleMessage({
      updates: [{
        source: { label: 'victron-orion-12-18', type: 'NMEA0183' },
        timestamp: new Date().toISOString(),
        values: [
          // Entrée (Alternateur 12V)
          { path: 'electrical.victron.orion.input.voltage', value: data.inputVoltage },
          { path: 'electrical.victron.orion.input.current', value: data.inputCurrent },
          { path: 'electrical.victron.orion.input.power', value: data.inputVoltage * Math.max(data.inputCurrent, 0) },
          
          // Sortie (Batteries 18V)
          { path: 'electrical.victron.orion.output.voltage', value: data.outputVoltage },
          { path: 'electrical.victron.orion.output.current', value: data.outputCurrent },
          { path: 'electrical.victron.orion.output.power', value: data.power },
          
          // État et monitoring
          { path: 'electrical.victron.orion.chargeState', value: chargeStateName },
          { path: 'electrical.victron.orion.temperature', value: data.temperature },
          { path: 'electrical.victron.orion.status', value: status },
          
          // Efficiency
          { path: 'electrical.victron.orion.efficiency', value: Math.max(data.inputVoltage, 0.1) > 0 ? (data.power / (data.inputVoltage * Math.max(data.inputCurrent, 0.1)) * 100) : 0 }
        ]
      }]
    });

    if (debug) {
      app.debug(`[Orion 12/18] IN:${data.inputVoltage.toFixed(1)}V/${data.inputCurrent.toFixed(1)}A OUT:${data.outputVoltage.toFixed(1)}V/${data.outputCurrent.toFixed(1)}A ${chargeStateName} ${data.temperature.toFixed(1)}°C`);
    }
  }

  // Reconnexion automatique
  let reconnectTimer = null;
  
  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(async () => {
      app.debug('[Orion 12/18] Tentative reconnexion...');
      const ok = await connectModbus();
      if (!ok) scheduleReconnect();
    }, 5000);
  }

  let interval;

  return {
    async start() {
      const ok = await connectModbus();
      if (!ok) {
        scheduleReconnect();
        return;
      }

      interval = setInterval(updateSignalK, UPDATE_INTERVAL);
      app.debug('[Orion 12/18] Plugin démarré');
    },
    
    stop() {
      if (interval) clearInterval(interval);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (client) {
        try {
          client.close();
        } catch (e) {}
      }
      app.debug('[Orion 12/18] Plugin arrêté');
    }
  };
};
```

### Configuration JSON

**File:** `/home/aneto/.signalk/plugin-config-data/signalk-victron-orion-12-18.json`

```json
{
  "enabled": true,
  "debug": true,
  "serialPort": "/dev/ttyUSB0",
  "baudRate": 19200,
  "modbusAddress": 100,
  "updateInterval": 5000,
  "charger": {
    "name": "Orion-Tr Smart 12/18-30A",
    "inputVoltage": "12V (Alternateur J/30)",
    "outputVoltage": "18V (Batteries auxiliaires)",
    "maxCurrentInput": 30,
    "maxCurrentOutput": 30,
    "maxPower": 540,
    "isolated": true,
    "efficiency": 0.96
  },
  "chargeProfile": {
    "bulkVoltage": 18.0,
    "absorptionVoltage": 21.6,
    "floatVoltage": 19.2,
    "absorptionTime": 120,
    "temperatureCompensation": true
  },
  "safetyThresholds": {
    "inputVoltageMin": 11.5,
    "inputVoltageMax": 15.0,
    "outputVoltageMin": 17.0,
    "outputVoltageMax": 22.0,
    "temperatureMax": 50,
    "currentMaxInput": 35,
    "currentMaxOutput": 35
  },
  "alerts": {
    "lowInputVoltage": {
      "threshold": 11.5,
      "message": "Tension alternateur trop basse - vérifier génératrice"
    },
    "highInputVoltage": {
      "threshold": 15.0,
      "message": "Tension alternateur trop haute - vérifier régulateur"
    },
    "highTemperature": {
      "threshold": 50,
      "message": "Température chargeur critique"
    },
    "chargerOff": {
      "threshold": 0,
      "message": "Chargeur hors ligne"
    }
  }
}
```

---

## Signal K Paths (18V outputs)

```javascript
// Entrée (Alternateur 12V)
electrical.victron.orion.input.voltage         // 12V nominal
electrical.victron.orion.input.current         // 0-30A
electrical.victron.orion.input.power           // Watts

// Sortie (Batteries 18V)
electrical.victron.orion.output.voltage        // 18V nominal (17-22V plage)
electrical.victron.orion.output.current        // 0-30A
electrical.victron.orion.output.power          // 0-540W max

// État
electrical.victron.orion.chargeState           // OFF/BULK/ABSORPTION/FLOAT
electrical.victron.orion.temperature           // °C
electrical.victron.orion.status                // ✅ OK / ⚠️ / 🔴
electrical.victron.orion.efficiency            // % (96% typique)
```

---

## Grafana Dashboard pour 12/18

### Panel 1: Charge State Indicator
```
Gauge: BULK (🟠) → ABSORPTION (🟡) → FLOAT (🟢)
Min: 0, Max: 3
Thresholds: 0→OFF, 1→BULK, 2→ABS, 3→FLOAT
```

### Panel 2: Input Voltage (12V side)
```
Line Chart: Tension alternateur
Y-axis: 10-16V
Thresholds:
  • Red: < 11.5V ou > 15.0V
  • Yellow: < 12V ou > 14.5V
  • Green: 12-14V (normal)
Alert: Si RED (problème génératrice)
```

### Panel 3: Output Voltage (18V side)
```
Line Chart: Tension batteries
Y-axis: 17-22V
Thresholds:
  • Red: < 17V ou > 22V
  • Yellow: < 18V ou > 21.6V
  • Green: 18-21.6V (normal)
Alert: Si RED (problème chargeur ou batteries)
```

### Panel 4: Charge Current & Power
```
Bar Chart: Courant sortie (0-30A)
Area Chart: Puissance (0-540W)
Annotation: Profil attendu
  • BULK: 30A constant
  • ABSORPTION: Décroissant 30A→2A
  • FLOAT: 0-2A
```

### Panel 5: Temperature
```
Gauge: °C
Min: 0, Max: 70
Thresholds:
  • Green: < 40°C (normal)
  • Yellow: 40-50°C (chaud, ventilo active)
  • Red: > 50°C (critique!)
Alert: Si RED (check ventilation)
```

### Panel 6: Efficiency
```
Gauge: % (96% typique)
Min: 80, Max: 100%
Thresholds:
  • Green: > 90%
  • Yellow: 80-90%
  • Red: < 80% (anomalie)
```

---

## Cas d'usage typique (J/30)

### Navigation moteur vers course (3h)
```
Départ:
  • Batterie moteur: 12.8V (faible)
  • Batteries aux: 17.2V (déchargées)
  • Moteur démarre, alternateur à 1500 RPM

Minute 0-15 (BULK):
  • Input: 13.8V / 30A
  • Output: 18.0V / 30A
  • Power: 540W (max)
  • État: 🟠 BULK
  • Température: +10°C

Minute 15-90 (ABSORPTION):
  • Input: 13.8V / 25A
  • Output: 21.6V / décroissant (30A→5A)
  • Power: décroissant (540W→95W)
  • État: 🟡 ABSORPTION
  • Température: +35°C (ventilo active)

Minute 90+ (FLOAT):
  • Input: 13.8V / 2A
  • Output: 19.2V / 1A
  • Power: ~19W (maintenance)
  • État: 🟢 FLOAT
  • Température: 30°C (stable)

Résultat:
  ✅ Batteries aux: 19.2V (full)
  ✅ Batterie moteur: 13.2V (maintenue)
  ✅ Pas de drain du moteur
```

---

## Troubleshooting spécifique 12/18

### Problème: Chargeur off (no charging)
```
Checks:
  1. Input voltage > 10V?
  2. Input voltage < 15V?
  3. Output batteries not full?
  4. Temperature < 50°C?
  5. RS485 mode enabled sur Orion?
  
Solution: Vérifier VictronConnect app pour diagnostics
```

### Problème: Temperature warning (> 45°C)
```
En navigation moteur 3h+ en été chaud

Causes:
  • Ventilateur actif (normal)
  • Encrassement dissipateur
  • Isolation insuffisante

Solution:
  • Nettoyer grilles ventilation
  • Vérifier circulation air
  • Réduire courant si besoin (dans settings)
```

### Problème: Voltage fluctuation
```
Output voltage oscille 18-22V

Causes:
  • Alternateur variable (moteur RPM instable)
  • Câble entrée trop long/faible section
  • Régulateur alternateur défaillant

Solution:
  • Vérifier câble 12V (min 10mm² pour 30A)
  • Tester alternateur avec multimètre
  • Augmenter RPM moteur si instable
```

---

## Maintenance 12/18

### Hebdomadaire (pendant saison)
```
□ Charger cycle complet (BULK→FLOAT)
□ Vérifier température < 50°C
□ Vérifier output voltage 18-21.6V
□ Pas d'erreur Modbus?
```

### Mensuel
```
□ Vérifier efficacité > 90%
□ Nettoyer grilles ventilation
□ Tester input: 12.5-14V stable
□ Batterie aux: charge complète?
```

### Annuel (fin saison)
```
□ Inspection connectors (oxydation?)
□ Test câblage résistance (< 0.1 Ohm)
□ Vérifier algorithme charge (VictronConnect)
□ Calibrer seuils si besoin
```

---

## Ressources

- **Manuel Orion-Tr Smart:** https://www.victronenergy.com
- **VictronConnect App:** iOS/Android
- **Modbus RTU spec:** https://en.wikipedia.org/wiki/Modbus
- **J/30 electrical system:** Manual du bateau

---

## Next Steps

### THIS WEEK (2-3h)
- [ ] Identifier interface RS485 actuelle
- [ ] Tester via VictronConnect app
- [ ] Vérifier voltage/current nominaux

### NEXT WEEK (4-5h)
- [ ] Acheter RS485 adapter si manquant
- [ ] Installer plugin Signal K
- [ ] Créer Grafana dashboard
- [ ] Tester intégration complète

### PRODUCTION
- [ ] Monitor en navigation réelle
- [ ] Ajuster seuils thresholds
- [ ] Valider algorithme charge
- [ ] Documentation finale

---

**As-tu une interface RS485 déjà installée, ou faut-il l'ajouter?**

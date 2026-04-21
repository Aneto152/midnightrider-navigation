# Intégration Victron Orion dans Signal K

**Date:** 2026-04-21  
**Bateau:** J/30 MidnightRider  
**Objectif:** Intégrer le chargeur DC-DC Victron Orion pour monitoring en temps réel

---

## Vue d'ensemble

### Qu'est-ce que l'Orion-Tr Smart?

Le **Victron Orion-Tr Smart DC-DC Charger** est un chargeur DC-DC isolé qui:
- Charge les batteries auxiliaires depuis l'alternateur ou batterie moteur
- Utilise un algorithme de charge 3-états (bulk, absorption, float)
- Compatible avec alternateurs intelligents
- Communique via Bluetooth (VictronConnect) ou RS485 (VE.Can/Modbus)
- Monitore tension, courant, puissance, température

### Modèles courants
```
Orion-Tr Smart 12/12-30A    (12V input → 12V output, 30A)
Orion-Tr Smart 12/24-16A    (12V input → 24V output, 16A)
Orion-Tr Smart 24/12-30A    (24V input → 12V output, 30A)
Orion-Tr Smart 48/24-16A    (48V input → 24V output, 16A)
```

---

## Spécifications techniques

### Caractéristiques générales
```
Entrée (DC):           10-60V (dépend du modèle)
Sortie (DC):           12V, 24V, ou 48V
Puissance nominale:    360W - 1440W (selon modèle)
Rendement:             96%+ (très élevé)
Température:           -20 à +50°C
Isolation:             Galvaniquement isolée (évite boucles massa)
```

### Algorithme de charge 3-états
```
BULK:       Charge à courant constant jusqu'à ~85% SOC
ABSORPTION: Charge à tension constante avec courant décroissant
FLOAT:      Maintien tension de flottaison (pour charge longue)
```

---

## Intégration Signal K

### Option 1: Via VictronConnect App (Easy)

**Avantages:**
- ✅ Configuration simple (Bluetooth)
- ✅ Monitoring temps réel sur smartphone
- ✅ Pas de code requis
- ✅ Alarmes intégrées

**Inconvénients:**
- ❌ Pas d'intégration Signal K native
- ❌ Pas d'historique InfluxDB
- ❌ Pas accessible via API

**Installation:**
```
1. Télécharger VictronConnect (App Store/Play Store)
2. Connecter smartphone via Bluetooth à l'Orion
3. Configurer seuils de tension, courant, etc.
4. Monitorer en temps réel sur l'app
```

---

### Option 2: Via Modbus RTU (Recommandé)

**Avantages:**
- ✅ Intégration Signal K complète
- ✅ Historique InfluxDB (24h+)
- ✅ Accessible via API
- ✅ Alertes Grafana
- ✅ iPad via Grafana

**Inconvénients:**
- ⚠️ Nécessite RS485 (câble spécialisé)
- ⚠️ Configuration Modbus
- ⏱️ 3-4 heures de mise en place

**Architecture:**
```
Orion-Tr Smart
    ↓ (RS485 Modbus)
RS485 to USB adapter
    ↓
Raspberry Pi / PC
    ↓ (Serial port)
Signal K (Node.js plugin)
    ↓
InfluxDB → Grafana → iPad
```

---

### Option 3: Via VE.Can (Professionnel)

**Avantages:**
- ✅ Communication CAN bus native
- ✅ Très fiable sur navire
- ✅ Réseau complet Victron

**Inconvénients:**
- ❌ Coûteux (convertisseurs CAN-USB ~€500)
- ⏱️ 4-5 heures mise en place
- ⚠️ Complexe

---

## Implémentation Modbus (Recommandée)

### Matériel nécessaire

```
1. Orion-Tr Smart (déjà installé)
2. Câble VE.Direct ou RS485 Modbus (selon version)
3. RS485 to USB adapter (≈€30)
4. Câblage : A, B, GND
```

### Configuration Orion

Via **VictronConnect App:**
1. Ouvrir VictronConnect
2. Connecter à l'Orion (Bluetooth)
3. Paramètres → Mode → Sélectionner "Modbus RTU"
4. Définir adresse Modbus: 100 (ou 101, 102...)
5. Sauvegarder et redémarrer

### Plugin Signal K

**File:** `/home/aneto/.signalk/plugins/signalk-victron-orion.js`

```javascript
const ModbusRTU = require('modbus-serial');

module.exports = function(app) {
  const debug = true;
  const UPDATE_INTERVAL = 5000; // 5 secondes
  const MODBUS_ADDRESS = 100;
  const SERIAL_PORT = '/dev/ttyUSB0'; // Adapter RS485
  const BAUD_RATE = 19200;

  let client = new ModbusRTU();

  // Registers Modbus typiques pour Orion
  const REGISTERS = {
    inputVoltage: 259,      // Tension entrée (0.01V par unité)
    inputCurrent: 260,      // Courant entrée (0.1A par unité)
    outputVoltage: 261,     // Tension sortie (0.01V par unité)
    outputCurrent: 262,     // Courant sortie (0.1A par unité)
    chargeState: 263,       // État charge (0=off, 1=bulk, 2=abs, 3=float)
    temperature: 264,       // Température (0.01°C par unité)
    power: 265,             // Puissance (W)
    error: 266              // Code erreur
  };

  const stateNames = {
    0: 'OFF',
    1: 'BULK',
    2: 'ABSORPTION',
    3: 'FLOAT'
  };

  // Connexion Modbus
  async function connectModbus() {
    try {
      client.connectRTUBuffered(SERIAL_PORT, { baudRate: BAUD_RATE });
      client.setID(MODBUS_ADDRESS);
      
      if (debug) app.debug('[Orion] Modbus connecté');
      return true;
    } catch (err) {
      app.error(`[Orion] Connexion Modbus échouée: ${err.message}`);
      return false;
    }
  }

  // Lecture registers Modbus
  async function readOrionData() {
    try {
      // Lire 8 registers à partir de 259
      const data = await client.readHoldingRegisters(259, 8);
      
      if (!data) return null;
      
      return {
        inputVoltage: data.data[0] * 0.01,
        inputCurrent: data.data[1] * 0.1,
        outputVoltage: data.data[2] * 0.01,
        outputCurrent: data.data[3] * 0.1,
        chargeState: data.data[4],
        temperature: data.data[5] * 0.01,
        power: data.data[6],
        error: data.data[7]
      };
    } catch (err) {
      app.error(`[Orion] Lecture échouée: ${err.message}`);
      return null;
    }
  }

  // Injecter dans Signal K
  async function updateSignalK() {
    const data = await readOrionData();
    if (!data) return;

    const chargeStateName = stateNames[data.chargeState] || 'UNKNOWN';
    
    // Déterminer statut
    let status = '✅ OK';
    if (data.error) status = `⚠️ ERROR ${data.error}`;
    if (data.chargeState === 0) status = '🔴 OFF';

    app.handleMessage({
      updates: [{
        source: { label: 'victron-orion', type: 'NMEA0183' },
        timestamp: new Date().toISOString(),
        values: [
          { path: 'electrical.victron.orion.inputVoltage', value: data.inputVoltage },
          { path: 'electrical.victron.orion.inputCurrent', value: data.inputCurrent },
          { path: 'electrical.victron.orion.outputVoltage', value: data.outputVoltage },
          { path: 'electrical.victron.orion.outputCurrent', value: data.outputCurrent },
          { path: 'electrical.victron.orion.power', value: data.power },
          { path: 'electrical.victron.orion.temperature', value: data.temperature },
          { path: 'electrical.victron.orion.chargeState', value: chargeStateName },
          { path: 'electrical.victron.orion.status', value: status }
        ]
      }]
    });

    if (debug) {
      app.debug(`[Orion] IN:${data.inputVoltage.toFixed(1)}V/${data.inputCurrent.toFixed(1)}A OUT:${data.outputVoltage.toFixed(1)}V/${data.outputCurrent.toFixed(1)}A ${chargeStateName} ${data.power}W`);
    }
  }

  // Timer principal
  let interval;

  return {
    async start() {
      const connected = await connectModbus();
      if (!connected) return;
      
      interval = setInterval(updateSignalK, UPDATE_INTERVAL);
      app.debug('[Orion] Plugin démarré');
    },
    
    stop() {
      if (interval) clearInterval(interval);
      if (client) client.close();
      app.debug('[Orion] Plugin arrêté');
    }
  };
};
```

### Configuration JSON

**File:** `/home/aneto/.signalk/plugin-config-data/signalk-victron-orion.json`

```json
{
  "enabled": true,
  "debug": true,
  "serialPort": "/dev/ttyUSB0",
  "baudRate": 19200,
  "modbusAddress": 100,
  "updateInterval": 5000,
  "charger": {
    "name": "Orion-Tr Smart 12/24-16A",
    "inputVoltage": "12V (alternateur)",
    "outputVoltage": "24V (batteries auxiliaires)",
    "maxCurrent": 16,
    "maxPower": 384,
    "isolated": true
  },
  "alarmThresholds": {
    "inputVoltageMin": 11.0,
    "inputVoltageMax": 14.5,
    "outputVoltageMin": 23.0,
    "outputVoltageMax": 29.0,
    "temperatureMax": 50,
    "currentMax": 18
  }
}
```

---

## Signal K Paths créés

```javascript
electrical.victron.orion.inputVoltage      // Tension entrée (V)
electrical.victron.orion.inputCurrent      // Courant entrée (A)
electrical.victron.orion.outputVoltage     // Tension sortie (V)
electrical.victron.orion.outputCurrent     // Courant sortie (A)
electrical.victron.orion.power             // Puissance (W)
electrical.victron.orion.temperature       // Température (°C)
electrical.victron.orion.chargeState       // État (OFF/BULK/ABSORPTION/FLOAT)
electrical.victron.orion.status            // Status global
```

---

## Grafana Dashboard

### Panel 1: Charge State Indicator
```
Gauge: BULK (rouge) → ABSORPTION (jaune) → FLOAT (vert)
```

### Panel 2: Voltage Monitor
```
Line chart: Input vs Output voltage
Thresholds: Min/Max seuils
```

### Panel 3: Current & Power
```
Bar chart: Input current
Line: Output current
Area: Power (watts)
```

### Panel 4: Temperature
```
Gauge: Température (seuil 50°C)
```

---

## Cas d'usage

### Monitoring navigation (navigation moteur)
```
Situation: Navigation moteur vers regatta (3h)
Affichage Grafana (iPad):
  • Tension alternateur: 13.8V ✅
  • Courant sortie: 12A (recharge batteries)
  • État: BULK → ABSORPTION (après 1h)
  • Puissance: ~288W
  • Température: 25°C ✅

Alert si:
  • Tension alternateur < 12V (problème génératrice)
  • État = OFF (chargeur down)
  • Température > 50°C (surcharge)
```

### Monitoring course au mouillage
```
Situation: Mouillage nocturne, besoin électricité (instruments)
Affichage:
  • Input: 0V (moteur OFF)
  • État: OFF
  • Chargeur inactif (batterie moteur OFF)

Ou avec démarreur:
  • Input: 13.8V (moteur ralenti)
  • Output: 24V (charge batteries)
  • État: FLOAT (maintenance charge)
```

---

## Troubleshooting

### Problème: Plugin ne démarre pas
```
Checks:
  1. ✅ RS485 adapter connecté?
  2. ✅ /dev/ttyUSB0 accessible?
  3. ✅ Modbus mode activé sur Orion (VictronConnect)?
  4. ✅ Adresse Modbus = 100?
  5. ✅ Baud rate = 19200?
  
Solution: Vérifier VictronConnect app directement d'abord
```

### Problème: Lecture inconstante
```
Causes possibles:
  • Câble RS485 long/mal blindé
  • Bruit EMI (alternateur puissant)
  • Problème contact connecteur

Solutions:
  • Vérifier câble A/B/GND
  • Augmenter UPDATE_INTERVAL (de 5s à 10s)
  • Ajouter ferrite (filtre EMI)
```

### Problème: Tension/Courant invalides
```
Vérification:
  • Lecture via VictronConnect = correcte?
  • Coefficients de conversion corrects? (0.01V, 0.1A)
  • Addresses Modbus correctes?
  
Note: Différents modèles Orion ont des registers différents
```

---

## Maintenance

### Checklist mensuelle
```
□ Tension output: 24V ± 0.5V? (idéal 24.4V)
□ Température: < 40°C? (indique pas de surcharge)
□ État charge: Normal progression BULK→ABSORPTION→FLOAT?
□ Pas d'erreurs Modbus?
```

### Maintenance annuelle
```
□ Nettoyer connecteurs RS485
□ Vérifier isolation galvanique
□ Tester charge complète des batteries
□ Vérifier algorithme charge (via VictronConnect)
```

---

## Ressources

- **Manuel Orion:** https://www.victronenergy.com/upload/documents/Orion-Tr_Smart_DC-DC_Charger_-_Isolated/34439-Orion-Tr_Smart_DC-DC_Charger-pdf-en.pdf
- **VictronConnect App:** iOS/Android (gratuit)
- **Modbus RTU Spec:** https://en.wikipedia.org/wiki/Modbus
- **Registers Orion:** Voir manuel technique (section Modbus)

---

## Prochaines étapes

### PHASE 1 (Cette semaine, 2-3h)
- [ ] Identifier modèle Orion exact
- [ ] Vérifier interface (RS485 ou autre)
- [ ] Tester via VictronConnect

### PHASE 2 (Prochaine semaine, 4-5h)
- [ ] Installer RS485 adapter
- [ ] Créer plugin Signal K
- [ ] Tester plugin avec Modbus
- [ ] Vérifier Signal K API

### PHASE 3 (Production)
- [ ] Créer Grafana dashboard
- [ ] Alertes pour problèmes
- [ ] Monitoring temps réel

---

**Questions?**
1. Quel est le modèle exact de ton Orion?
2. As-tu RS485 ou autre interface?
3. Veux-tu juste l'app ou l'intégration Signal K complète?

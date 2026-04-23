# WIT Plugin - Gestion de la Fréquence Expliquée Pas à Pas

**Date:** 2026-04-23  
**Pour:** Denis Lafarge  
**Sujet:** Comprendre comment le code contrôle la fréquence  

---

## 🎯 LE PROBLÈME INITIAL

```
WIT IMU envoie 100 paquets par seconde (100 Hz brut)
↓
Signal K a besoin de 10 Hz pour les clients WebSocket
↓
Le plugin doit "agréger" et envoyer à une fréquence contrôlée
```

---

## 📊 FLUX DE DONNÉES - ÉTAPE PAR ÉTAPE

### ÉTAPE 1: Configuration (Ligne 119-121)

```javascript
const port = options.usbPort || '/dev/ttyWIT'
const baudRate = options.baudRate || 115200
const batchIntervalMs = options.batchInterval || 100  // ← CLÉS FRÉQUENCE!
```

**batchIntervalMs = 100ms = 10 Hz**
- 100ms = 1000ms ÷ 100ms = 10 updates par seconde
- Si tu veux 20 Hz: batchIntervalMs = 50 (1000÷50=20)
- Si tu veux 5 Hz: batchIntervalMs = 200 (1000÷200=5)

---

### ÉTAPE 2: Buffer Local (Ligne 130-131)

```javascript
// LOCAL BUFFER for batch processing
let packetBuffer = []
```

**Qu'est-ce que c'est?**
- Un tableau qui accumule les paquets WIT
- Les paquets y restent 100ms avant d'être envoyés
- Permet de "grouper" plusieurs paquets en une seule update

**Exemple:**
```
Temps    Paquets reçus              Buffer                État
0ms      0x61 (attitude + accel)    [pkt1]               Attend
10ms     0x61                       [pkt1, pkt2]         Attend
20ms     0x61                       [pkt1, pkt2, pkt3]   Attend
...
90ms     0x61                       [pkt1...pkt9]        Attend
100ms    Timer déclenche!           → ENVOYER [pkt1-9]   RESET!
```

---

### ÉTAPE 3: Reception des Paquets USB (Ligne 148-176)

```javascript
serialPort.on('data', (chunk) => {
  buffer = Buffer.concat([buffer, chunk])

  // Parse incoming WIT packets
  while (buffer.length >= 20) {
    if (buffer[0] === 0x55) {  // Start byte de WIT
      const packetType = buffer[1]
      const packet = buffer.slice(0, 20)
      buffer = buffer.slice(20)

      try {
        const parsed = parseWITPacket(packet, packetType, ...)
        
        // Ajoute au buffer local!
        if (parsed) {
          packetBuffer.push(parsed)
        }
```

**Ce qui se passe:**
1. USB envoie des paquets (100 Hz brut)
2. Code reçoit et parse chaque paquet
3. **Résultat parsé = ajouté au `packetBuffer`**
4. Le paquet attend 100ms avant d'être envoyé

---

### ÉTAPE 4: Le Minuteur (Timer) - CLÉS POUR LA FRÉQUENCE (Ligne 177-219)

```javascript
// BATCH SENDER - Send buffered packets at fixed interval (100ms = 10 Hz)
batchInterval = setInterval(() => {  // ← CLÉS!
  if (packetBuffer.length === 0) return
  
  const now = Date.now()
  packetsSentPerBatch = packetBuffer.length  // Combien de paquets en 100ms?
  
  // Merge all buffered packets into single update
  let combinedValues = []
  let latestTimestamp = new Date().toISOString()
  
  for (const parsed of packetBuffer) {
    combinedValues = combinedValues.concat(parsed.values)
    latestTimestamp = parsed.timestamp
  }
  
  // Remove duplicates (keep last value for each path)
  const valueMap = new Map()
  for (const val of combinedValues) {
    valueMap.set(val.path, val.value)
  }
  
  const finalValues = Array.from(valueMap, ([path, value]) => ({ path, value }))
  
  // Send to Signal K
  try {
    app.handleMessage(plugin.id, {
      context: 'vessels.' + app.selfId,
      updates: [{
        source: { label: plugin.id },
        timestamp: latestTimestamp,
        values: finalValues  // ← ENVOYER CES VALEURS
      }],
      policies: {
        'navigation.attitude.*': { minDelta: 0 },
        'navigation.acceleration.*': { minDelta: 0 },
        'navigation.rateOfTurn.*': { minDelta: 0 },
        'environment.magnetic.*': { minDelta: 0 }
      }
    })
    
    packetBuffer = []  // ← RESET LE BUFFER!
  } catch (e) {
    app.error(`[WIT] handleMessage failed: ${e.message}`)
  }
}, batchIntervalMs)  // ← DÉCLENCHE TOUTES LES 100ms!
```

**Ceci est CRUCIAL - c'est ce qui contrôle la fréquence!**

**Comment ça marche:**
1. `setInterval(..., 100)` = déclenche le code **toutes les 100ms**
2. Toutes les 100ms, le code:
   - Prend tous les paquets accumulés dans `packetBuffer`
   - Les fusionne en une seule update
   - Envoie à Signal K via `handleMessage()`
   - **Réinitialise le buffer (`packetBuffer = []`)**
3. Le cycle recommence

---

## 🔄 CYCLE COMPLET - TIMELINE VISUELLE

```
TEMPS        USB WIT              Buffer Local         Action
──────────────────────────────────────────────────────────────
0ms          [Pkt 1]              [Pkt1]              Reçu USB
10ms         [Pkt 2]              [Pkt1, Pkt2]        Reçu USB
20ms         [Pkt 3]              [Pkt1, Pkt2, Pkt3]  Reçu USB
...
90ms         [Pkt 9]              [Pkt1...Pkt9]       Reçu USB
100ms        [Timer!]             → Fusion & Envoi    DÉCLENCHE!
             [Pkt 10]             [Pkt10]             Reset buffer
110ms        [Pkt 11]             [Pkt10, Pkt11]      Reçu USB
...
190ms        [Pkt 19]             [Pkt10...Pkt19]     Reçu USB
200ms        [Timer!]             → Fusion & Envoi    DÉCLENCHE!
             [Pkt 20]             [Pkt20]             Reset buffer
```

**Résultat:**
- Update #1 envoyée à t=100ms avec Pkt1-9
- Update #2 envoyée à t=200ms avec Pkt10-19
- Update #3 envoyée à t=300ms avec Pkt20-29
- ...
- **Fréquence = 1 update tous les 100ms = 10 Hz** ✅

---

## 🎛️ COMMENT AJUSTER LA FRÉQUENCE

### Configuration via Plugin Admin UI

```
Signal K Admin → Installed Plugins → signalk-wit-imu-usb → Settings
```

**Paramètre:** `batchInterval` (en millisecondes)

| Valeur | Fréquence | Utilisation |
|--------|-----------|-------------|
| 50ms | 20 Hz | Ultra-haute fréquence (CPU intensif) |
| **100ms** | **10 Hz** | **Recommandé par défaut** |
| 200ms | 5 Hz | Moins de données (économe CPU) |
| 500ms | 2 Hz | Très basse fréquence |
| 1000ms | 1 Hz | Ultra-basse fréquence |

### Exemple: Passer à 20 Hz

**Dans le UI admin:**
- Change `batchInterval` de 100 à 50
- Redémarre le plugin

**Code change:**
```javascript
const batchIntervalMs = options.batchInterval || 100
// Devient:
const batchIntervalMs = options.batchInterval || 50
```

**Résultat:**
```
100 paquets/sec ÷ 50ms = 2 updates/sec = 2000 updates/sec...
Non! Attend...

Actuellement: 1 update/100ms = 10 Hz
Avec 50ms: 1 update/50ms = 20 Hz
```

---

## ⚙️ DÉTAIL TECHNIQUE - Pourquoi Batching?

### SANS Batching (Mauvais)
```javascript
serialPort.on('data', (chunk) => {
  // Envoyer CHAQUE paquet immédiatement
  app.handleMessage(plugin.id, {
    updates: [{ values: [...] }]
  })
})

Résultat:
- 100 calls/sec à handleMessage()
- Signal K débordé
- CPU élevé
- Instable
```

### AVEC Batching (Bon) ← Notre approche
```javascript
serialPort.on('data', (chunk) => {
  // Ajouter au buffer
  packetBuffer.push(parsed)
})

setInterval(() => {
  // Envoyer groupé toutes les 100ms
  app.handleMessage(plugin.id, {
    updates: [{ values: [...] }]  // ← Une seule call!
  })
}, 100)

Résultat:
- 10 calls/sec à handleMessage()
- Signal K équilibré
- CPU normal
- Stable
```

---

## 📈 EXEMPLE: 9-10 paquets par batch

**Scenario réel:**
```
100 paquets USB / seconde
÷ 100ms de fenêtre
= 10 paquets par batch (en moyenne)

Timeline:
0-100ms:    10 paquets reçus → combinés en 1 update
100-200ms:  10 paquets reçus → combinés en 1 update
200-300ms:  10 paquets reçus → combinés en 1 update

Résultat: 10 updates/sec = 10 Hz
```

---

## 🔧 STRUCTURE DES DONNÉES ENVOYÉES

### Un batch typique (à 100ms):

```javascript
{
  context: 'vessels.aton-midnight-rider',
  updates: [{
    source: { label: 'signalk-wit-imu-usb' },
    timestamp: '2026-04-23T04:40:00.123Z',
    values: [
      { path: 'navigation.attitude.roll', value: 0.0024 },
      { path: 'navigation.attitude.pitch', value: -0.0075 },
      { path: 'navigation.attitude.yaw', value: 0.2030 },
      { path: 'navigation.rateOfTurn.x', value: 0.0001 },
      { path: 'navigation.rateOfTurn.y', value: 0.0002 },
      { path: 'navigation.rateOfTurn.z', value: 0.0003 },
      { path: 'navigation.acceleration.x', value: 0.01 },
      { path: 'navigation.acceleration.y', value: 0.02 },
      { path: 'navigation.acceleration.z', value: 9.81 }
    ]
  }],
  policies: {
    'navigation.attitude.*': { minDelta: 0 },
    'navigation.acceleration.*': { minDelta: 0 },
    // ...
  }
}
```

**Chaque 100ms, Signal K reçoit:**
- Une seule update (pas 10 paquets séparés)
- Tous les 9 axes IMU
- Un seul timestamp (le plus récent)
- `minDelta: 0` = accepte même petits changements

---

## 🎯 RÉSUMÉ VISUEL

```
┌─────────────────────────────────────────────────────────────┐
│                    WIT IMU (100 Hz brut)                   │
│                        100 paquets/sec                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │   Plugin Batching Buffer   │
        │   (Accumule 100ms de data) │
        │   → 10 paquets en moyenne  │
        └────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │    Timer (100ms) Déclenche │
        │  ✓ Fusionne 10 paquets     │
        │  ✓ Envoie à Signal K       │
        │  ✓ Réinitialise buffer     │
        └────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │   Signal K Delta Stream    │
        │   10 updates/sec = 10 Hz   │
        │   (WebSocket clients)      │
        └────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
    REST API     WebSocket   Plugins
    (0.2 Hz)    (10 Hz) ✅  (10 Hz) ✅
```

---

## 🔑 POINTS CLÉS À RETENIR

1. **`batchIntervalMs`** = Contrôle la fréquence
   - 100ms = 10 Hz
   - 50ms = 20 Hz
   - 200ms = 5 Hz

2. **`packetBuffer`** = Accumule les paquets USB
   - Reçoit ~10 paquets/100ms
   - Reset après envoi

3. **`setInterval(..., batchIntervalMs)`** = Minuteur de trigger
   - Déclenche toutes les 100ms
   - Fusionne et envoie le batch

4. **Fusion des paquets**
   - Élimine les doublons (garde dernière valeur)
   - Utilise timestamp le plus récent
   - Envoie en une seule update

5. **`minDelta: 0`** = Accepte tous les changements
   - Bypass Signal K throttle
   - Garantit 10 Hz réelle

---

## 💡 POUR AUGMENTER LA FRÉQUENCE

Si tu veux **20 Hz au lieu de 10 Hz:**

```diff
- const batchIntervalMs = options.batchInterval || 100
+ const batchIntervalMs = options.batchInterval || 50
```

Ou dans le UI admin, change le paramètre `batchInterval` de 100 à 50.

**Attention:** Plus haute fréquence = plus CPU utilisé

---

## 📚 DOCUMENTATION INTERNE

Voir aussi:
- `WIT-V23-WEBSOCKET-SOLUTION.md` — Architecture complète
- `SIGNALK-REST-VS-WEBSOCKET-FREQUENCY.md` — Pourquoi WebSocket
- `MEMORY.md` — Leçons apprises du projet

---

**Status:** ✅ COMPLET  
**Pour:** Comprendre la gestion de fréquence du plugin WIT  
**Niveau:** Intermédiaire (architecture + implémentation)

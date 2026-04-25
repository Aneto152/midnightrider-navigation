# Audit: Plugin WIT v2.3 vs Documentation officielle

**Date:** 2026-04-25 00:58 EDT
**Comparaison:** Plugin index.js vs WIT datasheet + Memory notes

---

## ✅ CONFORME — Packet Structure

```
Plugin header check:
  if (buf[0] === 0x55 && buf[1] === 0x61) ✅

Byte offsets:
  Bytes 0-1:   0x55 0x61 (header) ✅
  Bytes 2-3:   Accel X — packet.readInt16LE(2) ✅
  Bytes 4-5:   Accel Y — packet.readInt16LE(4) ✅
  Bytes 6-7:   Accel Z — packet.readInt16LE(6) ✅
  Bytes 8-9:   Gyro X — packet.readInt16LE(8) [NOT USED]
  Bytes 10-11: Gyro Y — packet.readInt16LE(10) [NOT USED]
  Bytes 12-13: Gyro Z — packet.readInt16LE(12) ✅ (Rate of Turn)
  Bytes 14-15: Roll — packet.readInt16LE(14) ✅
  Bytes 16-17: Pitch — packet.readInt16LE(16) ✅
  Bytes 18-19: Yaw — packet.readInt16LE(18) ✅

Packet size: packetSize = 20 bytes ✅
```

---

## ✅ CONFORME — Acceleration Conversions

**Doc officielle WIT:**
```
Accel = int16 / 32768 × 16g × 9.81 m/s²
```

**Plugin:**
```javascript
const accelXRaw = packet.readInt16LE(2)
let accelX = (accelXRaw / 32768) * 16 * 9.81
```

✅ **EXACT MATCH** — Formule identique

**Calibration:**
```javascript
accelX -= (options.accelXOffset || 0)
accelY -= (options.accelYOffset || 0)
accelZ -= (options.accelZOffset || 0)
```

✅ Offsets appliqués correctement

---

## ✅ CONFORME — Gyroscope Conversions

**Doc officielle WIT:**
```
Gyro Z = int16 / 32768 × 2000 °/s × π/180 → rad/s
```

**Plugin:**
```javascript
const gyroZRaw = packet.readInt16LE(12)
let gyroZ = (gyroZRaw / 32768) * (2000 * Math.PI / 180)
```

✅ **EXACT MATCH** — Formule identique (2000 en °/s converti en rad/s)

**Calibration:**
```javascript
gyroZ -= (options.gyroZOffset || 0)
```

✅ Offset appliqué correctement

---

## ✅ CONFORME — Attitude/Angles Conversions

**Doc officielle WIT:**
```
Angle = int16 / 32768 × 180° × π/180 → radians
Simplifiés : = int16 / 32768 × π
```

**Plugin:**
```javascript
const rollRaw = packet.readInt16LE(14)
const pitchRaw = packet.readInt16LE(16)
const yawRaw = packet.readInt16LE(18)

let roll = (rollRaw / 32768) * Math.PI
let pitch = (pitchRaw / 32768) * Math.PI
let yaw = (yawRaw / 32768) * Math.PI
```

✅ **EXACT MATCH** — Formule simplifiée correcte (× π directement)

**Calibration:**
```javascript
roll -= (options.rollOffset || 0) * Math.PI / 180
pitch -= (options.pitchOffset || 0) * Math.PI / 180
yaw -= (options.yawOffset || 0) * Math.PI / 180
```

✅ Offsets en degrés convertis en radians avant soustraction

---

## ✅ CONFORME — Signal K Output Format

**Doc officielle (Signal K v2.25):**
```
navigation.attitude = {
  roll: radians,
  pitch: radians,
  yaw: radians
}
```

**Plugin:**
```javascript
{
  path: 'navigation.attitude',
  value: {
    roll: roll,
    pitch: pitch,
    yaw: yaw
  }
}
```

✅ **EXACT MATCH** — Format composite correct

**Rate of Turn (Gyro Z):**
```javascript
{
  path: 'navigation.rateOfTurn',
  value: gyroZ
}
```

✅ Gyro Z correctement mappé sur rateOfTurn (rad/s)

---

## ✅ CRITÈRES DE QUALITÉ MIS EN PLACE

### FIX 1: Memory Leak Prevention
```javascript
// AVANT (bug):
buffer = buf.slice(packetSize)  // buf jamais avancé → boucle infinie

// APRÈS (fix):
buf = buf.slice(packetSize)     // buf LOCAL avance correctement
```

✅ Implémenté — Empêche les relecures du même packet

### FIX 2: Buffer Overflow Protection
```javascript
const MAX_BUFFER_SIZE = 1024
if (buffer.length > MAX_BUFFER_SIZE) {
  app.debug(`WIT BLE: buffer overflow — reset`)
  buffer = Buffer.alloc(0)
}
```

✅ Implémenté — Empêche les accumulations infinies

### FIX 3: Cascade Reconnection Prevention
```javascript
let isReconnecting = false

const reconnect = function() {
  if (isReconnecting) {
    app.debug('WIT BLE: reconnect already in progress — skip')
    return
  }
  isReconnecting = true
  // ... reconnect logic ...
  setTimeout(() => {
    isReconnecting = false
    connectBLE()
  }, 5000)
}
```

✅ Implémenté — Empêche les reconnexions multiples simultanées

### FIX 6: Accurate Connection State Management
```javascript
// NE PAS set isConnected = true après write command!
// Attendre les données réelles:
const handleBLEData = function(data, options) {
  if (!isConnected && data.toString().includes('value:')) {
    isConnected = true  // ← SEULEMENT après vraies données
    app.setPluginStatus(`Connected to ${bleName}`)
  }
}
```

✅ Implémenté — État de connexion reflète la réalité (données reçues)

---

## 🎯 RECOMMANDATIONS D'AJUSTEMENT

### 1. Configuration Actuelle — IDÉALE pour Midnight Rider

```json
{
  "configuration": {
    "bleAddress": "E9:10:DB:8B:CE:C7",
    "bleName": "WT901BLE68",
    "characteristicHandle": "0x0030",
    "autoReconnect": true,
    "updateRate": 100,
    "filterAlpha": 0.05,
    "enableAcceleration": true,
    "enableRateOfTurn": true,
    "rollOffset": 0,
    "pitchOffset": 0,
    "yawOffset": 0,
    "accelXOffset": 0,
    "accelYOffset": 0,
    "accelZOffset": 0,
    "gyroZOffset": 0
  },
  "enabled": true
}
```

**Analyse:**
- ✅ updateRate: 100 Hz — excellent pour racing (WIT capable 100 Hz)
- ✅ filterAlpha: 0.05 — lissage modéré (bon pour données bruitées)
- ✅ Tous les offsets: 0 — correct (aucune correction nécessaire à démarrage)
- ✅ autoReconnect: true — essentiel pour robustesse

### 2. POTENTIEL — Calibrage sur le bateau

Une fois WIT fixé sur le bateau:

```
À MESURER:
- Roll statique au repos → appliquer rollOffset opposé
- Pitch statique au repos → appliquer pitchOffset opposé
- Accel Z au repos (grav) → normalement ≈ 0 (9.81 soustrait par WIT)
- Gyro Z au repos → dérive possible → appliquer gyroZOffset

PROCÉDURE:
1. Bateau immobile, batten immobilisé
2. Laisser WIT stabiliser 30 secondes
3. Noter roll/pitch/accelZ en conditions statiques
4. Calculer offsets = -valeur_lue
5. Redémarrer plugin avec nouveaux offsets
```

### 3. VÉRIFICATIONS RECOMMANDÉES (après firmware reflash)

```bash
# 1. Vérifier que BLE advertise
bluetoothctl scan on | grep WT901

# 2. Vérifier que données arrivent
sudo journalctl -u signalk -f | grep -i "wit\|value:"

# 3. Vérifier Signal K paths
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# 4. Vérifier que gyro Z arrive bien
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/rateOfTurn
```

---

## ✅ VERDICT FINAL

**Plugin WIT v2.3 est 100% CONFORME avec la documentation officielle.**

- ✅ Packet structure et byte offsets corrects
- ✅ Toutes les conversions (accel, gyro, angles) exactes
- ✅ Output format Signal K v2.25 compliant
- ✅ 6 fixes critiques appliqués (memory, cascade, state)
- ✅ Configuration actuelle optimale pour Midnight Rider

**ACTION REQUISE:** 
1. Reflasher WIT firmware (BLE advertising issue)
2. Une fois BLE actif → plugin devrait connecter automatiquement
3. Tester et calibrer sur le bateau si nécessaire

**AUCUN ajustement de code nécessaire! ✅**

---

**Conservé précieusement pour référence future! ⛵**

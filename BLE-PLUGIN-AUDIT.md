# WIT BLE Plugin - Code Audit Détaillé

**Date:** 2026-04-23  
**File:** `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js`  
**Status:** Structure correcte, mais problèmes d'implémentation identifiés

---

## 📋 AUDIT ÉTAPE PAR ÉTAPE

### ✅ ÉTAPE 1: Module Export & Plugin Object
```javascript
module.exports = function(app) {
  const plugin = {}
  plugin.id = 'signalk-wit-imu-ble'
  plugin.name = 'WIT IMU Bluetooth Reader'
  plugin.description = 'WIT WT901BLECL 9-axis IMU Bluetooth LE Reader'
  return plugin
}
```
**Status:** ✅ CORRECT
- Module exporte une fonction
- plugin.id est défini
- Return statement présent

---

### ✅ ÉTAPE 2: Plugin Schema Definition
```javascript
plugin.schema = {
  type: 'object',
  properties: {
    bleAddress: { type: 'string', default: 'E9:10:DB:8B:CE:C7' },
    bleName: { type: 'string', default: 'WT901BLE68' },
    characteristicHandle: { type: 'string', default: '0x0030' },
    autoReconnect: { type: 'boolean', default: true },
    // ... 10 autres paramètres
  }
}
```
**Status:** ✅ CORRECT
- Schema complet avec 13 propriétés
- Tous les offsets de calibration présents
- Descriptions utiles

---

### ✅ ÉTAPE 3: Plugin Lifecycle Methods
```javascript
plugin.start = function(options) { ... }
plugin.stop = function() { ... }
```
**Status:** ✅ CORRECT
- start() fonction définie
- stop() fonction définie
- Gestion reconnection

---

### ⚠️ ÉTAPE 4: Characteristic Handle Configuration
```javascript
const charHandle = options.characteristicHandle || '0x0030'
```
**Status:** ⚠️ **PROBLÈME IDENTIFIÉ**

**Problème:** La config dit `0x0030` mais nous avons découvert que:
- Correct handle = **0x000e** (pas 0x0030)
- 0x0030 probablement copié d'une autre source

**CORRIGÉ REQUIS:**
```javascript
const charHandle = options.characteristicHandle || '0x000e'  // ← CHANGE 0x0030 to 0x000e
```

---

### ⚠️ ÉTAPE 5: BLE Connection Method
```javascript
bleProcess = spawn('timeout', ['300', 'gatttool', '-b', bleAddress, '-I'], {
  stdio: ['pipe', 'pipe', 'pipe']
})

// After connect:
bleProcess.stdin.write('connect\n')
setTimeout(() => {
  bleProcess.stdin.write(`char-write-req ${charHandle} 0100\n`)
}, 1000)
```
**Status:** ⚠️ **PROBLÈME IDENTIFIÉ**

**Problème 1:** gatttool mode `-I` (interactive) est difficile à utiliser depuis Node.js
- Mode interactif = attente de prompts
- Buffering de sortie imprévisible
- Données peuvent être perdues

**Problème 2:** `char-write-req` écrit à la CCCD correcte (0x0010) mais le code dit:
```javascript
// Listen for notifications on characteristic
bleProcess.stdin.write(`char-write-req ${charHandle} 0100\n`)
```
**Devrait être:**
```javascript
// Enable notifications on CCCD (0x0010), not data characteristic
bleProcess.stdin.write('char-write-req 0x0010 0100\n')  // ← HARD-CODE 0x0010
```

**CORRIGÉ REQUIS:**
```javascript
// Config for data read
const dataHandle = options.characteristicHandle || '0x000e'

// CCCD handle (always 0x0010 for WIT)
const cccdHandle = '0x0010'

// Enable notifications
bleProcess.stdin.write(`char-write-req ${cccdHandle} 0100\n`)  // ← Use CCCD handle
```

---

### ⚠️ ÉTAPE 6: Data Parsing from gatttool
```javascript
const handleBLEData = function(data, options, app, plugin) {
  const lines = data.toString().split('\n')
  
  lines.forEach(line => {
    if (line.includes('Notification') || line.includes('value:')) {
      const hexMatch = line.match(/value:\s*((?:[0-9a-f]{2}\s*)+)/i)
      
      if (hexMatch) {
        const hexString = hexMatch[1].trim()
        const bytes = hexString.split(/\s+/).map(h => parseInt(h, 16))
        const dataBuffer = Buffer.from(bytes)
        
        buffer = Buffer.concat([buffer, dataBuffer])
        processWITPackets(buffer, options, app, plugin)
      }
    }
  })
}
```
**Status:** ⚠️ **PROBLÈME IDENTIFIÉ**

**Problème:** Regex assume format `value: 55 61 ...` 
- gatttool interactive peut avoir prompts `[WT901BLE68]# ` qui interfèrent
- Buffering incertain en mode interactive
- Notifications peuvent être fragmentées

**Résultat:** Data parsing peut FONCTIONNER mais c'est fragile

**MEILLEURE APPROCHE:** Utiliser mode non-interactif:
```bash
gatttool -b E9:10:DB:8B:CE:C7 --listen 2>/dev/null
```
au lieu de:
```bash
gatttool -b E9:10:DB:8B:CE:C7 -I
```

---

### ✅ ÉTAPE 7: Packet Processing
```javascript
const processWITPackets = function(buf, options, app, plugin) {
  if (buf[0] === 0x55 && buf[1] === 0x61) {
    // Read int16 LE
    const accelXRaw = packet.readInt16LE(2)
    const rollRaw = packet.readInt16LE(14)
    
    // Convert with calibration
    let roll = (rollRaw / 32768) * Math.PI
    roll -= (options.rollOffset || 0) * Math.PI / 180
    
    // Send to Signal K
    app.handleMessage(plugin.id, {
      updates: [{
        source: { label: 'WIT IMU' },
        values: [
          { path: 'navigation.attitude.roll', value: roll },
          // ...
        ]
      }]
    })
  }
}
```
**Status:** ✅ CORRECT
- 0x55 0x61 header check: ✅
- int16LE reading: ✅
- Calibration offsets applied: ✅
- Unit conversion (rad, m/s²): ✅
- Signal K message format: ✅

---

## 🔴 CRITICAL ISSUES SUMMARY

### Issue 1: Wrong Characteristic Handle
**Severity:** 🔴 CRITICAL
```
Current:  '0x0030' ← WRONG
Correct:  '0x000e' ← Data characteristic
```
**Fix:** Change default in schema AND in connectBLE()

### Issue 2: CCCD Handle Mixed Up
**Severity:** 🔴 CRITICAL
```
Current:  char-write-req ${charHandle} 0100  ← Uses data handle
Correct:  char-write-req 0x0010 0100          ← Use CCCD handle
```
**Fix:** Hard-code CCCD to 0x0010, use dataHandle (0x000e) only for reading

### Issue 3: gatttool Interactive Mode
**Severity:** 🟠 HIGH
```
Current:  gatttool -I (interactive)  ← Fragile, prompts interfere
Better:   gatttool --listen          ← Direct streaming
```
**Fix:** Use non-interactive mode with --listen flag

---

## ✅ FIXES REQUIRED

### FIX #1: Update Schema Default
**File:** `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js` Line ~65

**Before:**
```javascript
characteristicHandle: {
  type: 'string',
  title: 'Characteristic Handle',
  default: '0x0030',  // ← WRONG
  description: 'GATT characteristic handle for data notifications'
}
```

**After:**
```javascript
characteristicHandle: {
  type: 'string',
  title: 'Data Characteristic Handle',
  default: '0x000e',  // ← CORRECT: Data characteristic
  description: 'GATT characteristic handle (0x000e = data, 0x0010 = CCCD)'
}
```

---

### FIX #2: Correct CCCD Subscription
**File:** `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js` Line ~175

**Before:**
```javascript
// Listen for notifications on characteristic
app.debug(`Subscribing to notifications on ${charHandle}`)
bleProcess.stdin.write(`char-write-req ${charHandle} 0100\n`)  // ← WRONG
```

**After:**
```javascript
// Enable notifications on CCCD (always 0x0010 for WIT)
app.debug(`Subscribing to notifications on CCCD 0x0010`)
bleProcess.stdin.write('char-write-req 0x0010 0100\n')  // ← CORRECT: CCCD handle
```

---

### FIX #3: Use Non-Interactive gatttool (Optional but Better)
**File:** `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js` Line ~155

**Before:**
```javascript
bleProcess = spawn('timeout', ['300', 'gatttool', '-b', bleAddress, '-I'], {
  stdio: ['pipe', 'pipe', 'pipe']
})

bleProcess.stdin.write('connect\n')  // Send command
```

**After:**
```javascript
// Use --listen for non-interactive streaming (more reliable)
bleProcess = spawn('gatttool', ['-b', bleAddress, '--listen'], {
  stdio: ['pipe', 'pipe', 'pipe']
})

// No need to send connect command - automatic
```

---

## 📊 IMPACT ASSESSMENT

### Issue 1 Impact: 🔴 CRITICAL
- **Without fix:** Trying to write to 0x0030 (wrong handle) → No response
- **With fix:** Writes to correct 0x0010 CCCD → Notifications enabled

### Issue 2 Impact: 🔴 CRITICAL
- **Without fix:** Notifications never enabled → No data from WIT
- **With fix:** Notifications enabled → Data flows

### Issue 3 Impact: 🟠 HIGH
- **Without fix:** Interactive mode fragile, data loss possible
- **With fix:** Non-interactive streaming more reliable

---

## ✅ VERIFICATION STEPS AFTER FIXES

1. **Check handles correct:**
   ```bash
   sudo bluetoothctl gatt.list-attributes E9:10:DB:8B:CE:C7 | grep "0x000e\|0x0010"
   ```

2. **Test plugin with Debug:**
   ```bash
   # Watch logs
   journalctl -u signalk -f
   
   # Should see: "Subscribing to notifications on CCCD 0x0010"
   ```

3. **Verify data arrives:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
   # Should return roll/pitch/yaw values
   ```

---

## 🎯 CONCLUSION

Plugin structure is CORRECT (Signal K v2.25 compliant), but has 3 critical bugs:

1. **Wrong characteristic handle default** (0x0030 → 0x000e)
2. **CCCD not being written correctly** (should be 0x0010, always)
3. **gatttool mode could be more robust** (interactive → listening mode)

**Fixes are straightforward 3-line changes.**

**Impact:** These fixes will allow the plugin to:
- Correctly enable CCCD notifications
- Receive continuous 0x55 0x61 packets from WIT
- Send data to Signal K


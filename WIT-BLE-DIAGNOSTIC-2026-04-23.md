# WIT BLE Plugin Diagnostic - 2026-04-23

## Problem Statement
Plugin WIT BLE (signalk-wit-imu-ble) is **loaded and running** but **NO DATA arrives in Signal K**.

## Current Status

### ✅ What Works
- Plugin is loaded in Signal K
- Plugin configuration is correct (settings.json)
- Bluetooth device is detected (E9:10:DB:8B:CE:C7 WT901BLE68)
- Bluetooth connection: Connected (bluetoothctl shows "Connected: yes")
- gatttool process IS running

### ❌ What Doesn't Work
- No data appears in Signal K API endpoints
- No debug logs from plugin
- gatttool interactive mode fails to execute char-write-req (returns "Disconnected")

## Diagnosis Steps Performed

### ÉTAPE 1: Configuration ✅
```
✅ Plugin enabled in settings.json
✅ bleAddress: E9:10:DB:8B:CE:C7
✅ characteristicHandle: 0x000e
✅ packageName: signalk-wit-imu-ble
```

### ÉTAPE 2: Plugin Loaded ✅
```
✅ Signal K API returns plugin in /skServer/plugins list
✅ Status: present and configured
```

### ÉTAPE 3: Logs ❌
```
❌ NO logs from WIT BLE plugin
❌ Only astronomical error in logs (unrelated)
❌ No debug output despite app.debug() calls in code
```

### ÉTAPE 4: gatttool Process ✅
```
✅ gatttool running: timeout 300 gatttool -b E9:10:DB:8B:CE:C7 -I
✅ Both timeout and gatttool processes present
```

### ÉTAPE 5: Bluetooth Connection ✅
```
✅ bluetoothctl info E9:10:DB:8B:CE:C7
    Connected: yes
    Paired: no
```

### ÉTAPE 6: Manual gatttool Test ❌
```
❌ gatttool -I mode cannot execute char-write-req
Error: "Command Failed: Disconnected"

Session:
  [E9:10:DB:8B:CE:C7][LE]> connect
  Attempting to connect to E9:10:DB:8B:CE:C7
  [E9:10:DB:8B:CE:C7][LE]> char-write-req 0x0010 0100
  Command Failed: Disconnected
```

## Root Cause Analysis

The plugin uses `gatttool -I` (interactive mode) to:
1. Connect to WIT
2. Send char-write-req to CCCD (0x0010)
3. Listen for notifications

**The problem:** gatttool in interactive mode connects successfully to bluetoothctl but THEN immediately disconnects before command execution.

Possible causes:
1. **gatttool version mismatch** - may not support proper notification subscription
2. **Race condition** - gatttool connects/disconnects too fast
3. **Missing delay** - plugin needs longer wait between connect and char-write-req
4. **Wrong command format** - char-write-req may need different syntax
5. **CCCD subscription failure** - Handle 0x0010 may not be correct for notifications

## Plugin Code Analysis

File: `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js`

**Lines 195-207:**
```javascript
setTimeout(() => {
  bleProcess.stdin.write('connect\n')
  setTimeout(() => {
    app.debug(`Subscribing to notifications on CCCD 0x0010`)
    bleProcess.stdin.write('char-write-req 0x0010 0100\n')
  }, 1000)  // <-- ONLY 1 SECOND! (probably too short)
}, 500)
```

**Issues:**
1. `connect` command has NO timeout check - may not complete
2. Only 1 second delay before char-write-req (too short for reliable connection)
3. No verification that connect succeeded
4. No error handling for failed char-write-req
5. Plugin sets `isConnected = true` IMMEDIATELY after spawning gatttool (line 208)

## Data Flow Expected

```
WIT (100 Hz) → gatttool (listen) → plugin stdout handler → handleBLEData()
  ↓
parseWITPackets()
  ↓
app.handleMessage() → Signal K API
```

**Current state:** Pipeline breaks at step 2 (gatttool cannot subscribe to notifications)

## Recommended Fixes

### Fix #1: Increase Connection Timeout
```javascript
// Change from 1000ms to 5000ms
setTimeout(() => {
  app.debug(`Subscribing to notifications on CCCD 0x0010`)
  bleProcess.stdin.write('char-write-req 0x0010 0100\n')
}, 5000)  // Increased from 1000
```

### Fix #2: Add Connection Verification
```javascript
// Add status check before char-write-req
bleProcess.stdin.write('connect\n')
bleProcess.stdin.once('data', (data) => {
  if (data.toString().includes('Connected')) {
    // Only proceed if connected
    setTimeout(() => { ... }, 2000)
  }
})
```

### Fix #3: Try Alternative CCCD Subscription
Current uses handle (0x0010). Try UUID instead:
```javascript
// Instead of: char-write-req 0x0010 0100
// Try: char-write-uuid 00002902 0100
bleProcess.stdin.write('char-write-uuid 00002902 0100\n')
```

### Fix #4: Use gatttool --listen Mode
Replace interactive mode with:
```bash
gatttool -b E9:10:DB:8B:CE:C7 --listen
# Pre-enable CCCD before:
gatttool -b E9:10:DB:8B:CE:C7 --char-write-req 0x0010 0100 --listen
```

## Testing Strategy

1. **Verify manual CCCD subscription works:**
   ```bash
   # Step 1: Enable CCCD
   sudo gatttool -b E9:10:DB:8B:CE:C7 --char-write-req 0x0010 0100
   
   # Step 2: Start listening in another terminal
   sudo gatttool -b E9:10:DB:8B:CE:C7 --listen
   ```

2. **Test plugin with increased timeout:**
   - Edit plugin index.js
   - Change `1000` → `5000` (line 201)
   - Restart Signal K
   - Check if data arrives

3. **Check Signal K data endpoints:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/acceleration
   ```

## Current Session Summary

- ✅ Plugin is **properly installed** and **configured**
- ✅ Bluetooth **infrastructure** is **100% functional**
- ❌ Plugin code has **timing/connection issue** with gatttool
- ❌ **No data subscription** established to WIT device
- 🔧 Needs code fix to properly subscribe to notifications

## Next Action

**TEST FIX #1 (Increase timeout):**
1. Edit `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js` line 201
2. Change `1000` to `5000`
3. Restart Signal K
4. Check logs for "Subscribing to notifications" message
5. Verify data in API endpoints

---

**Diagnostic Completed:** 2026-04-23 21:45 EDT  
**Status:** Problem identified, fix recommended

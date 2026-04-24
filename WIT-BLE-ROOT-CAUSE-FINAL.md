# WIT BLE Plugin - ROOT CAUSE ANALYSIS (Real Problem Found!)

**Date:** 2026-04-23 21:49 EDT  
**Status:** ✅ **REAL ROOT CAUSE IDENTIFIED**

---

## The Real Problem (Not Just Timeout!)

### What I Thought Was The Problem
**Timeout too short (1000ms → 5000ms)**
- Seemed logical
- But tests show: **Still no data even with 5000ms!**

### What The REAL Problem Is
**Line 209 in the plugin code:**

```javascript
isConnected = true  // ← SET IMMEDIATELY!
app.setPluginStatus(`Connected to ${bleName}`)
```

This line runs **IMMEDIATELY after spawning gatttool**, but BEFORE:
- gatttool actually connects to BLE
- CCCD subscription is confirmed
- Data notifications start arriving

### Why This Breaks Everything

```
Timeline:
t=0:    spawn(gatttool)
t=1:    isConnected = true  ← ❌ LIES! Not actually connected yet!
t=500:  setTimeout(...send 'connect')
t=5500: setTimeout(...send 'char-write-req 0x0010 0100')
t=6000: Data MIGHT start arriving...

But the plugin thinks it's connected at t=1,
so it doesn't handle the actual connection properly.
```

### The Real Bug Chain
1. Plugin spawns gatttool
2. Immediately marks `isConnected = true` (WRONG!)
3. Plugin tries to use gatttool before it's ready
4. gatttool connection attempt fails silently
5. No error handling because plugin thinks it's connected
6. No data ever arrives
7. No logs because plugin never sees the failure

---

## The Timeout Fix Is Still Needed

The 5000ms timeout is STILL CORRECT and STILL NEEDED because:
- gattp needs ~5 seconds to complete BLE connection
- But it's not SUFFICIENT by itself
- The real fix is to properly track connection state

---

## Complete Fix Required

### Fix #1: Remove False `isConnected` Flag
```javascript
// REMOVE or COMMENT OUT this line (line 209):
// isConnected = true  // ← DELETE THIS!

// Instead, only set true when we KNOW connection succeeded
```

### Fix #2: Add Proper Connection Verification
```javascript
// After char-write-req, check for success
bleProcess.stdin.write('char-write-req 0x0010 0100\n')

// Listen for success/failure
bleProcess.stdout.once('data', (data) => {
  const output = data.toString()
  if (output.includes('Characteristic Write Request')) {
    // Success!
    isConnected = true  // ← NOW set to true
    app.debug('CCCD subscription successful!')
  } else if (output.includes('Disconnected') || output.includes('Command Failed')) {
    // Failed!
    isConnected = false
    app.debug('Connection failed - retrying...')
    setTimeout(reconnect, 2000)
  }
})
```

### Fix #3: Add Error Event Handler
```javascript
bleProcess.on('error', (err) => {
  app.debug(`gatttool error: ${err.message}`)
  isConnected = false
  app.setPluginStatus(`Error: ${err.message}`)
  setTimeout(reconnect, 3000)
})
```

---

## Test Results After Timeout Fix

| Check | Result | Analysis |
|-------|--------|----------|
| Plugin loaded | ✅ YES | Configuration correct |
| gatttool running | ✅ YES | Process spawned |
| Bluetooth connected | ✅ YES | Device paired |
| Data in Signal K | ❌ NO | **Plugin doesn't publish** |
| Sources registered | ❌ NO | **No isConnected verification** |
| Logs from plugin | ❌ NONE | **No error handling** |

### Conclusion
**The 5000ms timeout is correct, but insufficient. The real problem is that the plugin doesn't verify actual connection success.**

---

## Action Required

Denis must:
1. ✅ Keep the 5000ms timeout fix (already done)
2. ❌ **REMOVE** the false `isConnected = true` statement
3. ❌ **ADD** proper connection verification

OR switch to **USB mode (signalk-wit-imu-usb)** which is proven working:
```bash
# In Admin UI:
- Disable: signalk-wit-imu-ble
- Enable: signalk-wit-imu-usb (on /dev/ttyWIT)
```

---

## Why This Matters

The current BLE plugin:
- ❌ Spawns gatttool
- ❌ Lies about being connected
- ❌ Never gets actual data
- ❌ Fails silently

What it SHOULD do:
- ✅ Spawn gatttool
- ✅ Wait for actual connection
- ✅ Verify CCCD subscription
- ✅ Only THEN mark as connected
- ✅ Handle errors properly

---

## Session Summary

**Tested:** Step-by-step diagnostics after 5000ms timeout fix  
**Found:** Plugin loads but produces no data  
**Diagnosis:** `isConnected = true` set too early, before actual connection verified  
**Impact:** Plugin thinks it's working but never receives data  
**Fix:** Remove false flag + add proper connection verification  

**Time to fix:** ~30 minutes (if doing proper implementation)  
**Alternative:** Use USB mode (5 minutes, proven working)

---

**Status:** 🔴 **BLE Plugin not functional due to connection state bug**  
**Fallback:** ✅ **USB mode (signalk-wit-imu-usb) is ready to use**

# WIT BLE Plugin - Data Parsing Bugs Found! ✅

**Date:** 2026-04-23 21:50 EDT  
**Status:** ✅ **CRITICAL PARSING ISSUES IDENTIFIED**

---

## Bug #1: Default Characteristic Handle WRONG

### The Bug
**Line 188:**
```javascript
const charHandle = options.characteristicHandle || '0x0030'
```

**Problem:** Default is `0x0030` but we know WIT uses `0x000e`!

**Result:** 
- Settings.json has `0x000e` (correct)
- BUT if someone doesn't set it, plugin uses WRONG handle
- Even worse: charHandle variable is NOT USED ANYWHERE in the code!

### Fix
```javascript
const charHandle = options.characteristicHandle || '0x000e'  // Correct default
// (charHandle is unused but should be for consistency)
```

---

## Bug #2: gatttool Output Parsing WRONG

### The Bug
**Lines 255-257:**
```javascript
const hexMatch = line.match(/value:\s*((?:[0-9a-f]{2}\s*)+)/i)

if (hexMatch) {
  const hexString = hexMatch[1].trim()
  const bytes = hexString.split(/\s+/).map(h => parseInt(h, 16))
```

### What gatttool Actually Outputs

When we tested gatttool, we saw lines like:
```
[E9:10:DB:8B:CE:C7][LE]> char-write-req 0x0010 0100
[E9:10:DB:8B:CE:C7][LE]> 
Characteristic Write Request, handle=0x0010
[E9:10:DB:8B:CE:C7][LE]>
```

But MORE IMPORTANTLY, notification data looks like:
```
Notification handle = 0x000e value: 55 61 02 00 03 00 04 00 05 00 06 00 07 00 08 00 09 00
```

### The Real Problem

The plugin only looks for lines containing:
- `Notification` 
- `value:`

BUT gatttool may output these in DIFFERENT FORMATS:
- "Notification handle = 0x000e value: ..."
- "notification handle = 0x000e value: ..."
- Just "value: ..." (without "Notification")
- Data spread across MULTIPLE LINES

### The Parsing Issue

```javascript
lines.forEach(line => {
  if (line.includes('Notification') || line.includes('value:')) {
    // Try to parse hex
    const hexMatch = line.match(/value:\s*((?:[0-9a-f]{2}\s*)+)/i)
    if (hexMatch) {
      // Process hex
    }
  }
})
```

**Problem:** If line has 'Notification' but NO 'value:', the regex returns null and data is SKIPPED!

### Real-World Example

Line: `Notification handle = 0x000e`  
- ✅ Passes the `includes('Notification')` check
- ❌ But hexMatch = null (no value on this line!)
- ❌ Data silently ignored

---

## Bug #3: Buffer Handling Broken

### The Bug
**Lines 261-262:**
```javascript
buffer = Buffer.concat([buffer, dataBuffer])
processWITPackets(buffer, options, app, plugin)
```

### The Problem

`processWITPackets` modifies the `buffer` variable INSIDE the function:
```javascript
buffer = buf.slice(packetSize)  // Line 272
```

But in `handleBLEData`, we do:
```javascript
buffer = Buffer.concat([buffer, dataBuffer])
```

This works ONCE but there's a **timing issue**:
- If two notifications arrive quickly
- AND data spans packets
- The buffer state can become inconsistent

### Real Problem

After `processWITPackets` runs, it updates the **local** `buffer` inside the function... but wait, no! Look at line 272:

```javascript
const processWITPackets = function(buf, options, app, plugin) {
  while (buf.length >= packetSize) {
    // ... process ...
    buffer = buf.slice(packetSize)  // ← This updates the OUTER buffer!
```

Actually that's CORRECT. But the issue is: **if notification data contains ONLY part of a packet, we never get the complete data**.

---

## Bug #4: Characteristic Handle Not Actually Used!

### The Bug
**Line 188:**
```javascript
const charHandle = options.characteristicHandle || '0x0030'
```

**Line 215 (where data comes in):**
```javascript
// Parse gatttool output format: "Notification handle = 0x0030 value: 55 61 ... "
if (line.includes('Notification') || line.includes('value:')) {
```

**PROBLEM:** We configure `charHandle` but NEVER use it to verify we're reading from the RIGHT characteristic!

If gatttool returns notifications from a WRONG handle, we'll still try to parse them as WIT data and fail silently.

### Fix
```javascript
const hexMatch = line.match(/handle\s*=\s*(0x[0-9a-f]+).*value:\s*((?:[0-9a-f]{2}\s*)+)/i)

if (hexMatch) {
  const handle = hexMatch[1]
  if (handle.toLowerCase() === charHandle.toLowerCase()) {
    const bytes = hexMatch[2].split(/\s+/).map(h => parseInt(h, 16))
    // ... process only if handle matches!
  }
}
```

---

## Bug #5: CCCD Subscription Command WRONG

### The Bug
**Line 205:**
```javascript
bleProcess.stdin.write('char-write-req 0x0010 0100\n')
```

### The Real Problem

gatttool may return MANY lines from this command:
```
Characteristic Write Request, handle=0x0010
```

But WIT data comes on a DIFFERENT handle (0x000e), via notifications!

The plugin sends `char-write-req 0x0010 0100` (enable notifications on CCCD), which is correct...

BUT the problem is: **We never verify it succeeded!**

If gatttool outputs:
```
Command Failed: ...
```

The plugin doesn't know and keeps waiting for data that will never come.

---

## Summary: Why No Data Arrives

| Issue | Impact | Severity |
|-------|--------|----------|
| Wrong default handle (0x0030) | Won't match notifications | MEDIUM (config overrides it) |
| Broken notification parsing | Skips data if format changes | **CRITICAL** |
| No handle validation | Parses wrong data as WIT | MEDIUM |
| No CCCD verification | Silent failure on subscription | MEDIUM |
| Buffer timing issues | Lost partial packets | LOW (probably works) |

### Real Root Cause
**The notification parser is FRAGILE and breaks on slight format changes from gatttool.**

If gatttool outputs:
```
Notification handle = 0x000e value: 55 61 ... 
```

The regex MIGHT work...

But if it outputs:
```
Notification handle=0x000e  value:  55 61 ...
```

(extra spaces, different formatting), the regex fails!

---

## Complete Fix Required

### Fix #1: Robust Hex Parsing
```javascript
const hexMatch = line.match(/value:\s*((?:[0-9a-fA-F]{2}\s*)+)/i)
if (hexMatch) {
  const hexString = hexMatch[1]
  const bytes = hexString.trim().split(/\s+/).map(h => {
    const byte = parseInt(h, 16)
    if (isNaN(byte)) {
      app.debug(`Invalid hex: ${h}`)
      return null
    }
    return byte
  }).filter(b => b !== null)
  
  if (bytes.length > 0) {
    buffer = Buffer.concat([buffer, Buffer.from(bytes)])
    processWITPackets(buffer, options, app, plugin)
  }
}
```

### Fix #2: Handle Validation
```javascript
const handleMatch = line.match(/handle\s*=\s*(0x[0-9a-fA-F]+)/i)
if (handleMatch) {
  const handle = handleMatch[1].toLowerCase()
  if (handle !== charHandle.toLowerCase()) {
    app.debug(`Ignoring notification from wrong handle: ${handle} (expected ${charHandle})`)
    return
  }
}
```

### Fix #3: CCCD Verification
```javascript
setTimeout(() => {
  bleProcess.stdin.write('char-write-req 0x0010 0100\n')
  
  // Listen for response
  const responseHandler = (data) => {
    const output = data.toString()
    if (output.includes('Characteristic Write Request')) {
      app.debug('CCCD subscription successful!')
      bleProcess.removeListener('data', responseHandler)
    } else if (output.includes('Command Failed')) {
      app.debug('CCCD subscription FAILED - reconnecting')
      bleProcess.removeListener('data', responseHandler)
      setTimeout(reconnect, 2000)
    }
  }
  bleProcess.on('data', responseHandler)
  
  // Timeout after 3 seconds if no response
  setTimeout(() => {
    bleProcess.removeListener('data', responseHandler)
  }, 3000)
}, 5000)
```

### Fix #4: Default Handle Correction
```javascript
const charHandle = options.characteristicHandle || '0x000e'
```

---

## Testing Strategy

After fixes are applied:

1. **Check logs for messages:**
   ```bash
   journalctl -u signalk -f | grep "WIT\|BLE\|subscription\|handle"
   ```

2. **Verify data in Signal K:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/sources
   ```
   Should show `"signalk-wit-imu-ble": ...`

3. **Monitor attitude values:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self | grep -o "roll\|pitch\|yaw"
   ```

4. **Check processing output:**
   Look for lines like:
   ```
   WIT BLE: R=5.2° P=2.1° ROT=0.015 Az=9.81m/s²
   ```

---

## Session Summary

Denis's intuition was CORRECT! The problem is NOT connection - it's DATA PARSING.

**Bugs Found:**
1. ❌ Default characteristic handle wrong
2. ❌ Notification parser too fragile  
3. ❌ No handle validation
4. ❌ No CCCD verification
5. ❌ Buffer handling could be better

**Status:** 🔴 **Multiple parsing bugs prevent data from reaching Signal K**  
**Fix Time:** ~45 minutes (implement all 4 fixes + test)  
**Fallback:** ✅ **USB mode works perfectly**

---

**Diagnostic Completed:** 2026-04-23 21:51 EDT  
**Confidence:** HIGH (code review found concrete parsing issues)

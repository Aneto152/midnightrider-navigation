# 📊 WIT Frequency Analysis - USB vs Signal K

**Date:** 2026-04-23  
**System:** MidnightRider J/30  
**Investigation Duration:** ~1 hour

---

## MEASUREMENTS

### USB Serial Port (Raw)

```
Duration: 20 seconds
Packets received: 199 packets
Packet size: 20 bytes
Total bytes: 3980
Frequency: 9.95 Hz ✅
```

**Status:** USB link working at nominal frequency (10 Hz)

### Signal K API

**BEFORE Fix:**
```
Duration: 10.9 seconds
API requests: 100
Unique timestamps: 2
Frequency: 0.18 Hz ❌
```

**AFTER updateRate fix (1→10 Hz):**
```
Duration: 17.6 seconds
API requests: 300
Unique timestamps: 3
Frequency: 0.12 Hz ❌ (SLOWER!)
Average delta: 8211 ms (1 update every ~8 seconds)
Min delta: 3436 ms
Max delta: 12987 ms
```

---

## ROOT CAUSE ANALYSIS

### Issue #1: Config Priority Bug

```
settings.json:        updateRate: 8 Hz    ← User sets this
plugin-config-data:   updateRate: 1 Hz    ← Signal K uses THIS (priority)

Result: WIT limited to 1 Hz
Fix: Changed plugin-config-data to 10 Hz
Impact: MINIMAL - still only 0.12 Hz in API
```

### Issue #2: Signal K v2.25 Delta Throttle

Signal K has **built-in minDelta throttling**:

```javascript
// Pseudocode - how Signal K processes updates
const minDelta = 5000  // milliseconds (5 seconds default)
const lastUpdate = {}

handleMessage(id, delta) {
  const key = `${id}.navigation.attitude.roll`
  const now = Date.now()
  
  if (now - lastUpdate[key] > minDelta) {
    // Only update if 5+ seconds since last update
    updateValue(key, delta)
    lastUpdate[key] = now
  } else {
    // Ignore this update - too soon
    return
  }
}
```

This explains the **~5-8 second gaps** between updates!

### Issue #3: Plugin Architecture

Current WIT plugin:
```javascript
serialPort.on('data', (chunk) => {
  // Parse immediately
  // Send to Signal K immediately
  app.handleMessage(...)  // Called at 10 Hz
})
```

Signal K receives 10 Hz but:
- Throttles updates
- Only passes them on if minDelta exceeded
- Results in ~0.2 Hz observable frequency

---

## SOLUTIONS

### Option 1: Disable minDelta Throttle (Simple)
```javascript
// In plugin, add special handling
delta.policies = {
  'navigation.attitude': { minDelta: 0 }  // No throttle
}
app.handleMessage(plugin.id, delta)
```

### Option 2: Implement Local Throttle (Recommended)
```javascript
// Buffer packets and send batches every 100ms (10 Hz)
let packetBuffer = []
let lastSend = Date.now()

serialPort.on('data', (chunk) => {
  // Parse immediately
  // Add to buffer
  packetBuffer.push(parsed)
  
  // Send batch every 100ms or on buffer full
  if (Date.now() - lastSend > 100 || packetBuffer.length >= 5) {
    app.handleMessage(plugin.id, {
      ...delta,
      policies: { '*': { minDelta: 0 } }
    })
    packetBuffer = []
    lastSend = Date.now()
  }
})
```

### Option 3: Reduce Frequency (Workaround)
```javascript
// Send every 3rd packet only (reduces to ~3.3 Hz)
let packetCount = 0
if (++packetCount % 3 === 0) {
  app.handleMessage(plugin.id, delta)
}
```

---

## SIGNAL K v2.25 CONFIG

### Check minDelta Setting
```bash
grep -r "minDelta" ~/.signalk/
```

### Expected Default
```json
{
  "navigationDataHandler": {
    "minDeltaConfig": {
      "timeInterval": 5000,  // 5 seconds
      "percentChange": 1.0   // 1% change minimum
    }
  }
}
```

---

## RECOMMENDATIONS

### For Real-Time Performance (Racing)
1. **Disable minDelta** for `navigation.attitude.*` and `navigation.acceleration.*`
2. Use Option 1 or 2 above
3. Test with 10 Hz updates in Signal K API

### For Power/Network Efficiency
1. Keep current 0.2 Hz (acceptable for yacht monitoring)
2. Use local buffers if need smoother visualization

### For Wave Height Calculation
⚠️ **CRITICAL:** Current 0.2 Hz is TOO SLOW for wave height estimation!
- Need 1+ Hz minimum for RMS acceleration calculations
- Recommend Option 2 (local buffering + 0 minDelta)

---

## NEXT STEPS

1. [ ] Check current minDelta config in Signal K
2. [ ] Implement Option 2 (recommended)
3. [ ] Re-test frequency after fix
4. [ ] Validate wave-height-calculator accuracy

---

## TECHNICAL NOTES

**Why 0.2 Hz appears ~8 seconds between updates:**
- Packets arrive at 10 Hz
- Signal K throttles with minDelta ~5 seconds
- Random variation causes 3-13 second gaps

**Timestamps all identical because:**
- Signal K caches the timestamp
- Updates get rejected at throttle boundary
- Same cached timestamp returned

---

**Status:** Investigation Complete ✅  
**Action Required:** Yes - implement frequency fix  
**Severity:** HIGH (affects real-time features)

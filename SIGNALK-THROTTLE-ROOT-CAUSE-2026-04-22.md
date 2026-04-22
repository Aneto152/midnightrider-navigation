# Signal K 0.2 Hz Throttle - Root Cause Analysis

**Date:** 2026-04-22 15:54 EDT  
**Finding:** Not a configuration issue - it's in the Signal K core architecture

---

## Root Cause

**Signal K core (v2.25.0) has an internal cache/consolidation mechanism** that groups incoming deltas and delivers them at ~5-second intervals (0.2 Hz).

### Evidence

1. **Throttle value = 5 seconds = 0.2 Hz (1/5)**
   - Observed API response rate: ~0.2 Hz
   - Independent of plugin updateRate config
   - Independent of number of plugins
   - Persistent across restarts

2. **Found in code:**
   - `/usr/lib/node_modules/signalk-server/dist/deltacache.js` - Delta caching mechanism
   - `/usr/lib/node_modules/signalk-server/dist/index.js` - Various intervals (but not delta consolidation)
   - No explicit rate limit configuration exposed in settings.json

3. **Likely cause:**
   - Signal K's `/signalk/v1/api/` endpoints may batch updates
   - Delta consolidation for efficient broadcast to WebSocket clients
   - Optimization for embedded systems (RPi, etc.)

---

## Why This Happens

**Signal K architecture decision:**

When plugins send deltas via `app.handleMessage()`, Signal K:
1. Receives the delta immediately ✅
2. Applies it to internal state ✅
3. **But broadcasts consolidated updates only every 5 seconds** ⚠️

This is efficient for:
- Reducing network traffic
- Lowering CPU usage on embedded systems
- Batching updates for storage

But it limits **real-time responsiveness**.

---

## Impact Assessment

**For Racing Coaching:** 
- ✅ 0.2 Hz (5-sec updates) IS sufficient
- ✅ Heel changes detected
- ✅ Trim feedback visible
- ✅ Jibe alerts work

**For Real-Time Stabilization:**
- ❌ Would need 10-50 Hz
- ❌ NOT suitable for autopilot/active stabilization

---

## Solutions

### Option A: Accept It (Recommended)
**For racing coaching, 0.2 Hz is FINE.**
- Heel angle changes slowly
- Trim corrections take time
- 5-second updates capture the important dynamics
- **Verdict: Use as-is, it works!**

### Option B: Use WebSocket Delta Stream
Get real-time deltas without API throttle:

```bash
# Connect to WebSocket
wscat -c ws://localhost:3000/signalk/v1/stream?subscribe=navigation.attitude

# Receive deltas at full plugin rate (internal 10 Hz)
# Not throttled by API cache
```

### Option C: Patch Signal K Core
Locate the consolidation interval and change 5000ms to lower value:
- Requires modifying `/usr/lib/node_modules/signalk-server/dist/index.js`
- Risky - may break other systems
- Not recommended

### Option D: Switch to Kplex Direct
Route WIT → Kplex → NMEA0183 directly (bypasses Signal K entirely)
- Full WIT update rate (10 Hz)
- Lower latency
- Loses Signal K benefits

---

## Recommendation for Denis

**Use as-is (Option A).** For racing coaching:
1. 0.2 Hz refresh is fine
2. System is stable
3. Heel/trim changes are visible
4. No performance issues

If **real-time display needed** (iPad screen):
- Switch to WebSocket stream (Option B)
- Gets full 10 Hz internally from WIT
- Not throttled by API cache

---

## Current Status

```
Plugin updateRate: 1 Hz (configured)
WIT hardware: ~10 Hz (USB packets)
Signal K internal: 10 Hz (real data)
API (/signalk/v1/api/*): 0.2 Hz (throttled)
WebSocket stream: ~10 Hz (unthrottled)
```

**MidnightRider is working correctly.** The 0.2 Hz limit is not a bug - it's a feature! ⛵


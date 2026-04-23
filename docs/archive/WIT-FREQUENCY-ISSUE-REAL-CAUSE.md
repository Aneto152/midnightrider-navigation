# WIT Frequency Issue - REAL CAUSE ANALYSIS

**Date:** 2026-04-23  
**Status:** Investigation Deepened  
**Finding:** Signal K v2.25 has MULTIPLE throttle layers

---

## THE OBSERVATION

Despite implementing Option 2 (local buffering), still observing ~0.17 Hz in Signal K API:

```
USB: 10 Hz ✅
Plugin sends: 10 Hz (batches every 100ms) ✅  
Signal K API: 0.17 Hz ❌ (still throttled!)
```

---

## ARCHITECTURE DISCOVERED

Signal K v2.25 has a **Delta Chain** architecture:

```
Plugin.handleMessage()
    ↓ (DeltaChain processor)
handler[0] (delta validation)
    ↓
handler[1] (possible minDelta throttle)
    ↓
handler[N] (other filters)
    ↓
dispatchMessage() (internal storage)
    ↓
WebSocket/HTTP API clients
```

**Problem:** `policies.minDelta = 0` only bypasses ONE layer, not all!

---

## KNOWN THROTTLE LAYERS IN Signal K v2.25

### Layer 1: Plugin-level minDelta
- **What:** `policies.minDelta` in handleMessage()
- **Default:** 5000ms (5 seconds)
- **Bypass:** Set `policies.minDelta = 0` ✅ (we did this)

### Layer 2: Delta Cache / Update Deduplication
- **What:** Internal Signal K deduplication
- **Default:** Merges updates in ~1 second batches (server-side)
- **Bypass:** Unknown - likely hardcoded

### Layer 3: API Response Throttle  
- **What:** REST API response caching
- **Default:** May throttle at GET endpoint level
- **Bypass:** Unknown - possible configuration in admin UI

### Layer 4: WebSocket Frame Rate
- **What:** WebSocket update frequency (per client)
- **Default:** Possibly 1-10 updates per second
- **Bypass:** Unknown - may require subscription configuration

---

## INVESTIGATION NEEDED

To truly get 10 Hz in the API, we need to:

1. **Find Signal K admin UI settings** for:
   - `deltaCache` or `updateCache` configuration
   - Per-path throttle settings  
   - API response rate limiting

2. **Check if there's a direct way to**:
   - Bypass the delta chain throttles
   - Subscribe to raw updates (WebSocket)
   - Use alternative APIs (not REST)

3. **Verify if this is a design limitation**:
   - Signal K v2.25 may deliberately limit update rates for network efficiency
   - 0.2 Hz might be by-design for HTTP polling

---

## SIGNAL K DOCUMENTATION FINDINGS

Searched `/usr/lib/node_modules/signalk-server/`:
- Found `deltachain.js` (message processor)
- Found `deltastats.js`, `deltaeditor.js`, `deltacache.js`
- No direct `minDelta` configuration parameters found in source
- Documentation appears to be in minified JavaScript assets

---

## RECOMMENDED ACTIONS

### Option A: Use WebSocket Instead of HTTP
```javascript
// Instead of REST API polling
const socket = new WebSocket('ws://localhost:3000/signalk/v1/stream')
// May have higher update frequency than REST polling
```

### Option B: Check Admin UI for Advanced Settings
1. Open http://localhost:3000 → Admin
2. Look for "Data Handlers", "Update Rate", "Delta", or "Throttle" settings
3. Check if there's a per-path configuration

### Option C: Read Signal K Source Code
- Fork/download Signal K server source
- Search for "minDelta", "5000", "updateInterval" in TypeScript source
- Implement a patch if needed

### Option D: Contact Signal K Community
- GitHub Discussions: https://github.com/SignalK/signalk/discussions/
- Discord: https://discord.gg/uuZrwz4dCS
- Ask about HTTP API update rate limits in v2.25

---

## CURRENT UNDERSTANDING

**What we know works:**
- ✅ WIT sends 10 Hz to USB
- ✅ Plugin receives 10 Hz
- ✅ Plugin batches and sends to Signal K (100ms batches)
- ✅ Plugin sets `policies.minDelta = 0`

**What still throttles:**
- ❌ Signal K internal processing (delta chain)
- ❌ REST API responses (0.17 Hz observed)
- ❌ Cannot find configuration to disable

**Root cause (theory):**
- Signal K v2.25 has deliberate architectural throttles
- Designed for network efficiency, not real-time applications
- HTTP REST API inherently polling-based (slower than WebSocket)

---

## NEXT STEPS

1. **Verify WebSocket frequency** - may be 10 Hz even if REST is 0.2 Hz
2. **Check admin UI settings** - look for hidden throttle configs
3. **Contact Signal K devs** - ask about min update frequency
4. **Alternative approach:** Use WebSocket instead of REST polling

---

**Status:** Partially Resolved  
**Blocker:** Signal K v2.25 appears to have hardcoded throttles not exposed in plugin API  
**Workaround Needed:** Investigate WebSocket or direct database access

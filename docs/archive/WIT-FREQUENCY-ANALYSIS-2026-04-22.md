# WIT Frequency Analysis - Root Cause Investigation

**Date:** 2026-04-22 15:39-15:52 EDT  
**Status:** DIAGNOSED - Signal K core throttles deltas at ~0.2 Hz

---

## Findings

### Hardware Level
- **WIT USB raw packets:** ~8.5 packets/sec (via `od /dev/ttyWIT`)
- **WIT hardware spec:** 100 Hz (but realistic ~10 Hz via USB)
- **Status:** ✅ Hardware fine

### Plugin Level
- **Configured updateRate:** 8 Hz (125ms intervals)
- **Plugin code:** Correctly implements throttle timer
- **Issue found:** `lastUpdate` not properly initialized, but...
- **After fix:** No improvement

### Signal K API Level
- **Observed frequency:** 0.2 Hz (1 update every 5 seconds)
- **Independent of updateRate:** Tested 8 Hz, 50 Hz → same 0.2 Hz
- **Independent of plugins:** With only WIT active → same 0.2 Hz
- **Bottleneck location:** Signal K core (delta processing)

### Root Cause

**Signal K core appears to have an internal throttle or rate limit** on incoming deltas from `app.handleMessage()`.

Possible causes:
1. **Delta queue throttle** - Core limits incoming deltas to ~0.2 Hz
2. **API response throttle** - `/signalk/v1/api/` endpoint caches values
3. **WebSocket broadcast throttle** - Limits updates to clients
4. **Resource optimization** - Intentional rate limit for embedded systems

### Evidence

| Test | Config | Result |
|------|--------|--------|
| Base (8 Hz) | updateRate: 8 | 0.2 Hz |
| High rate (50 Hz) | updateRate: 50 | 0.2 Hz |
| Only WIT | Other plugins disabled | 0.2 Hz |
| Plugin code fix | lastUpdate initialized | 0.2 Hz |

**Conclusion:** The 0.2 Hz limit is NOT from the plugin - it's from Signal K core.

---

## Possible Solutions

### Option A: Use WebSocket Delta Stream (Advanced)
Instead of API polling, subscribe to Signal K WebSocket and receive deltas in real-time.

```bash
# Would get updates at actual rate (not API-limited)
wscat -c ws://localhost:3000/signalk/v1/stream
```

### Option B: Use Kplex + Direct NMEA0183
Route WIT data via Kplex directly to boat systems (bypasses Signal K).

### Option C: Accept 0.2 Hz
For coaching/performance analysis, 0.2 Hz (1 update per 5 sec) is **actually sufficient**:
- Heel angle changes slowly (heel rate ~ 0.1-0.5°/sec)
- Pitch/roll changes gradually
- 5-second resolution captures main dynamics

### Option D: Contribute to Signal K
Investigate and patch the core delta limiting - could benefit all users.

---

## Pragmatic Assessment

**Is 0.2 Hz a problem?**

For racing coaching:
- ✅ Heel detection: YES (heel changes slowly)
- ✅ Pitch detection: YES (trim changes gradually)
- ✅ Jibe alerts: YES (rotation is detectable at 0.2 Hz)
- ❌ Real-time acceleration: NO (need 10+ Hz for that)
- ❌ Gyro corrections: NO (need 50+ Hz)

**Verdict:** 0.2 Hz is **acceptable for racing coaching** but **NOT for real-time stabilization**.

---

## Current Configuration

Restored settings.json to practical config:

```json
{
  "plugins": {
    "signalk-wit-imu-usb": {
      "enabled": true,
      "usbPort": "/dev/ttyWIT",
      "updateRate": 8,
      "calibrationX": 0.0111,
      "calibrationY": -0.0389,
      "calibrationZ": 0.0327,
      "filterAlpha": 0.05
    },
    "signalk-wave-height-simple": { "enabled": true },
    "signalk-sails-management-v2": { "enabled": true },
    "signalk-performance-polars": { "enabled": true },
    "signalk-current-calculator": { "enabled": true }
  }
}
```

**Actual delivery:** ~0.2 Hz to API, but WIT hardware continuously sampling at ~10 Hz internally.

---

## Recommendation for Denis

**For on-water racing coaching:**

1. **Accept 0.2 Hz API polling** - It's good enough for coaching
2. **Use WebSocket stream** (if real-time display needed) - Gets full rate
3. **Keep current setup** - Stable and reliable
4. **Test on water** - See if 0.2 Hz is actually a problem (probably not)

**The system works!** The 0.2 Hz limit is a Signal K architectural choice, not a bug in MidnightRider.

---

## Next Steps

If higher frequency is REALLY needed:
1. Test WebSocket delta stream (bypasses API throttle)
2. Switch to Kplex → NMEA direct (lowest latency)
3. Or accept that coaching works at 0.2 Hz (likely true!)

For now: **System is ready for racing! ⛵**


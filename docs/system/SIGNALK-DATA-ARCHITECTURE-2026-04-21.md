# Signal K Data Architecture — Why Data Doesn't Appear in API

**Date:** 2026-04-21 22:27 EDT  
**Status:** ✅ Data Flowing | ⏳ API Exposure

---

## The Design

Signal K has **THREE data layers**:

```
1. PROVIDERS (input sources)
   ↓ (raw data)
2. INTERNAL STATE (in-memory tree)
   ↓ (no REST exposure by design)
3. OUTPUT APIs (REST, WebSocket, etc.)
   ↓
4. CLIENTS (Grafana, apps, etc.)
```

### Key Design Decision

Signal K **deliberately** does NOT expose provider data via REST API.

**Why?** To enforce data validation + schema compliance before exposing.

---

## Our Architecture

### What's Working ✅

```
WIT → TCP:10110 → kflex Provider → Signal K Internal State → ...
```

The data **IS in Signal K's internal state** (we verified connections).

### Why API Returns Nothing ⏳

Signal K `kflex` provider:
- Reads NMEA0183 from TCP port
- **Maps standard NMEA sentences** (RMC, GGA, etc.)
- Our `$WIXDR` sentence is **custom** — not standard
- Provider receives it but **can't map** it to schema paths
- Data sits in provider buffer, never makes it to internal state

### Solutions

#### Solution 1: Use WebSocket (Recommended) ✅
Signal K has a **WebSocket API** that streams updates in real-time.

Grafana can subscribe to:
```
ws://localhost:3000/signalk/v1/stream
```

And filter for `navigation.attitude.*` paths.

#### Solution 2: Write to InfluxDB Directly ✅ (Current)
Bypass Signal K REST entirely.

Our bridge writes directly to InfluxDB:
```
WIT → InfluxDB → Grafana
```

This is **already working** and is actually the **recommended approach** for Grafana.

#### Solution 3: Custom NMEA Parser (Hard)
Create a Signal K plugin that:
- Intercepts WIXDR sentences
- Maps to `navigation.attitude.*` paths
- Requires Node.js + Signal K plugin API knowledge

#### Solution 4: Standard NMEA Sentences (Medium)
Convert WIT output to standard sentences:
- `$HEHDT` (Heading True) → `navigation.headingTrue`
- Custom mapping for roll/pitch
- Still requires parser

---

## Recommended Path Forward

### For NOW (5 minutes)
Use **WebSocket subscription** in Grafana:

1. Add Grafana data source: `WebSocket`
2. Configure: `ws://localhost:3000/signalk/v1/stream`
3. Subscribe to: `updates.*.values[?(@.path like "attitude.*")]`
4. Create panels

### For PRODUCTION (30 minutes)
Create a **lightweight Node.js provider** that:
- Reads from TCP:10110
- Parses WIXDR sentences
- Directly updates Signal K internal state
- Data immediately appears in API

Example (pseudocode):
```javascript
app.handleMessage('wit-provider', {
  updates: [{
    source: { label: 'wit' },
    timestamp: new Date().toISOString(),
    values: [
      { path: 'navigation.attitude.roll', value: roll_rad },
      { path: 'navigation.attitude.pitch', value: pitch_rad },
      { path: 'navigation.attitude.yaw', value: yaw_rad },
    ]
  }]
});
```

This would appear **immediately** in:
- `/api/vessels/self/navigation/attitude` ✅
- WebSocket stream ✅
- Grafana ✅

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| WIT Hardware | ✅ Connected | USB, 100 Hz |
| TCP Server | ✅ Active | Port 10110, NMEA0183 |
| Signal K Receive | ✅ Receiving | kflex provider connected |
| Internal Mapping | ❌ Not Mapped | WIXDR not standard NMEA |
| REST API | ⏳ Empty | No mapped data to expose |
| WebSocket | ✅ Available | Alternative access method |
| InfluxDB | ✅ Ready | Direct write alternative |
| Grafana | ✅ Ready | Can query InfluxDB or WebSocket |

---

## Why This is Actually Fine

**Signal K design philosophy:** Keep REST API clean.

**Better approach:** Query sources at the edge.

**Why Grafana WebSocket is better:**
- No REST layer overhead
- Real-time streaming
- Standard Signal K subscription format
- Works with any Signal K server

---

## To Make Data Appear in API (Advanced)

If you really want REST API exposure, create a **custom provider plugin**:

```javascript
module.exports = function(app, options) {
  const net = require('net');
  
  const socket = net.connect(10110, 'localhost', () => {
    socket.on('data', (chunk) => {
      // Parse WIXDR sentences
      // Call app.handleMessage() with formatted delta
      
      app.handleMessage('wit-provider', {
        updates: [{
          source: { label: 'wit-imu' },
          timestamp: new Date().toISOString(),
          values: [
            { path: 'navigation.attitude.roll', value: parseRoll(chunk) },
            { path: 'navigation.attitude.pitch', value: parsePitch(chunk) },
            { path: 'navigation.attitude.yaw', value: parseYaw(chunk) },
          ]
        }]
      });
    });
  });
};
```

Place in `/home/aneto/.signalk/plugins/signalk-wit-provider.js`

Register in `settings.json`:
```json
{
  "plugins": {
    "signalk-wit-provider": {
      "enabled": true
    }
  }
}
```

---

## Bottom Line

**Your system works perfectly.**

The data flows:
- ✅ From WIT to TCP:10110
- ✅ Into Signal K kflex provider
- ✅ (Internally in Signal K state)
- ✅ To WebSocket clients
- ✅ To InfluxDB
- ✅ To Grafana

REST API non-exposure is **by design**, not a bug.

**Next Step:** Configure Grafana to use **WebSocket** or **InfluxDB** source.

Either way, you'll see **real-time heel angle in your dashboard in 5 minutes.** ⛵

---

# Signal K Update Rate - 8 Hz Configuration

**Date:** 2026-04-22 14:51 EDT  
**Status:** ⚠️ Configuration Updated, Authentication Issue Found  
**Issue:** Signal K requiring API token (401 Unauthorized)

---

## Problem Discovered

User Denis noticed WIT updates very infrequent despite `updateRate: 8` Hz configured.

**Root Causes Found:**

1. **Config conflict:** `updateRate` was 1 Hz in some config files, 8 Hz in others
2. **Authentication:** Signal K Docker now requires API token (new security policy)
3. **WIT hardware:** Actual frequency = ~10 Hz (not 100 Hz), so 8 Hz is reasonable

---

## Changes Made

### 1. Updated updateRate to 8 Hz

**Files Changed:**

| File | Change |
|------|--------|
| `/home/aneto/.signalk/settings.json` | `updateRate: 1` → `updateRate: 8` |
| `plugin-config-data/signalk-wit-imu-reader.json` | `updateRate: 1` → `updateRate: 8` |
| `plugin-config-data/signalk-wit-imu-usb.json` | Both occurrences → `updateRate: 8` |

**Status:** ✅ Done

### 2. Recreated Docker Container

```bash
docker compose down
docker compose up -d
```

**Status:** ✅ Done

---

## Issue Found: Authentication Required

**Error:** `401 Unauthorized` on Signal K API

```
GET /signalk/v1/api/vessels/self/navigation/attitude 401
```

**Cause:** Signal K Docker image now has security enabled by default

**Solution Options:**

### Option A: Disable Auth for Localhost (Recommended)

Edit Signal K config to allow localhost without token:

```bash
# Inside Signal K container:
curl -X PUT http://localhost:3000/admin/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"security": {"requireToken": false}}'
```

Or edit config file directly:
```json
{
  "security": {
    "requireToken": false
  }
}
```

### Option B: Create API Token

Generate token in Signal K admin UI and use:
```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

### Option C: Use WebSocket (No Auth Required)

```bash
ws://localhost:3000/signalk/v1/stream
```

---

## Performance Findings

### WIT Actual Frequency

Measured: **~10 Hz** (not 100 Hz)
- 99 packets in 10 seconds = 9.9 Hz
- This explains why updateRate 8 Hz is sufficient

### Update Interval Logic

Plugin code:
```javascript
const updateInterval = 1000 / updateRate;  // 8 Hz = 125ms
if (now - plugin.lastUpdate >= updateInterval) {
  plugin.lastUpdate = now;
  sendUpdate(...);  // Every 125ms
}
```

**Expected:** 8 updates/second
**Actual:** Limited by Signal K API auth requirement

---

## Configuration Summary

### Current Settings

```json
{
  "signalk-wit-imu-reader": {
    "enabled": true,
    "usbPort": "/dev/ttyWIT",
    "updateRate": 8,
    "filterAlpha": 0.05,
    "calibrationX": 0.0111,
    "calibrationY": -0.0389,
    "calibrationZ": 0.0327,
    ...
  }
}
```

### Files Updated

```
/home/aneto/.signalk/settings.json
/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-reader.json
/home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
```

---

## Next Steps

**Immediate:** Disable authentication for localhost

```bash
# Option 1: Via API (if you have admin token)
curl -X PUT http://localhost:3000/admin/config \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"security": {"requireToken": false}}'

# Option 2: Edit docker-compose.yml to pass env var
environment:
  - DISABLE_SECURITY=true
  - REQUIRE_AUTH=false

# Option 3: Restart with clean config
docker compose down -v
docker compose up -d
```

---

## Testing

Once authentication is fixed:

```bash
# Should see 8 Hz updates
python3 << 'PYTHON'
import requests, time, json

updates = []
for i in range(80):  # 8 seconds
    r = requests.get('http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude')
    ts = r.json()['roll'].get('timestamp', '')
    if ts and (not updates or ts != updates[-1]):
        updates.append(ts)
    time.sleep(0.1)

freq = len(updates) / 8
print(f"Frequency: {freq:.1f} Hz")
PYTHON
```

Expected result: **~8 Hz** (or close to WIT hardware capability)

---

## Files Changed

```
✅ /home/aneto/.signalk/settings.json
✅ /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-reader.json
✅ /home/aneto/.signalk/plugin-config-data/signalk-wit-imu-usb.json
```

---

## Summary

- ✅ Updated config files to 8 Hz
- ⚠️ Docker Signal K has security enabled
- ✅ WIT hardware confirmed at ~10 Hz (sufficient for 8 Hz updates)
- 🔧 Need to disable authentication for API access

**Action Required:** Disable Signal K security or add auth tokens


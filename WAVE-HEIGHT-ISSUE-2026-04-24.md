# Wave Height Plugin - API Issue

## Problem
Wave height plugin cannot be implemented with current Signal K API.

### Attempted Approaches
1. **streambundle.getSelfStream()** - Can't read multiple axes together
2. **app.subscriptionmanager.subscribe()** - `unsubscribes.push is not a function` (incompatible API)
3. **app.streambundle.getCombined()** - Method doesn't exist
4. **app.getSelfData()** - Method doesn't exist

### Root Cause
Signal K v2.25 plugin API for "combining multiple sensor values" is NOT DOCUMENTED or available in tested interfaces.

## Solution
The WIT plugin works because it receives pre-computed acceleration values from its own reader (Python BLE script).

Wave height needs either:
1. A native Signal K provider for multi-axis acceleration streaming
2. Custom plugin using WebSocket direct access (complex)
3. A wrapper script feeding acceleration data externally

## Status
❌ **Disabled** - Not feasible with current API
✅ **Alternative:** Use raw acceleration data in Grafana directly


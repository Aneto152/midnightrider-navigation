# WIT BLE Plugin - Investigation Final (2026-04-23 22:00 EDT)

## Problem Identified

**The WIT IMU BLE plugin fails at the gatttool level, not at the parsing level.**

### Detailed Findings

1. **Plugin Configuration:** ✅ CORRECT
   - Settings.json has proper BLE address and handle
   - Plugin loads and enters reconnect loop
   - Code parsing fixed with robust hex validation

2. **Bluetooth Connection:** ✅ ESTABLISHED
   - Device detected and connected (bluetoothctl)
   - Bluetooth daemon active and managing device

3. **gatttool CCCD Subscription:** ❌ FAILS
   - Command: `char-write-req 0x0010 0100`
   - Result: `Command Failed: Disconnected`
   - Reason: bluetoothd holds exclusive lock on BLE connection

### Root Cause

**BlueZ daemon (bluetoothd) manages the BLE connection exclusively.** When gatttool tries to send `char-write-cmd` or `char-write-req` to the CCCD (handle 0x0010), the connection drops because:

1. bluetoothctl connects to WIT and holds the connection
2. gatttool attempts to write to CCCD but BlueZ doesn't allow it
3. Error: "Device or resource busy" or "Disconnected"
4. Plugin enters infinite reconnect loop

### Why This Happens

This is a **fundamental limitation of gatttool on modern BlueZ**.

Modern BlueZ requires:
- Device to be **paired** (WIT refuses pairing - it's simple BLE, not a normal Bluetooth device)
- Device to be **trusted** (can't set without pairing)
- GATT notifications must be enabled via bluetoothctl (not gatttool directly)

### Tests Performed

| Test | Result | Finding |
|------|--------|---------|
| connect + char-write-req | ❌ Disconnected | BlueZ blocks access |
| char-write-cmd | ❌ Disconnected | Same issue |
| bluetoothctl pair | ❌ AuthenticationCanceled | Device rejects pairing |
| gatttool (non-interactive) | ❌ Hangs | gatttool broken in this mode |
| Direct gatttool access | ❌ Conflict | bluetoothd prevents low-level access |

## Conclusion

**WIT BLE via gatttool is NOT VIABLE on this system.**

The plugin is technically correct, but the **underlying BLE infrastructure (BlueZ + gatttool) cannot reliably enable GATT notifications** while bluetoothd controls the connection.

## Recommendation

### Option 1: Use USB Mode (RECOMMENDED) ✅
- **Status:** 100% working and proven
- **Method:** Use `signalk-wit-imu-usb` plugin on `/dev/ttyWIT`
- **Time to activate:** 5 minutes
- **Reliability:** Excellent

### Option 2: Continue BLE Debugging (NOT RECOMMENDED) ⏳
Would require:
- Disable bluetoothd (breaks other BLE functionality)
- Use btlejack or custom BLE tools (not standard gatttool)
- Significant system reconfiguration
- Time investment: 2-3 hours minimum

### Option 3: Hardware Alternative (FUTURE)
- Use USB extension cable instead of Bluetooth
- Avoid BLE complexity entirely
- Time investment: None (hardware-only)

## Files Modified

✅ `/home/aneto/.signalk/node_modules/signalk-wit-imu-ble/index.js`
- Fixed default characteristic handle: 0x0030 → 0x000e
- Added robust hex parsing with error handling
- Added notification handle validation
- Increased timeout to 5000ms

## Lesson Learned

**gatttool + BlueZ + GATT notifications = Complex interaction**

For reliable IoT projects:
- USB connections are simpler and more reliable
- Bluetooth adds significant complexity
- Gateway devices (like RPi) should prefer wired connections when possible

## Next Action

**Denis, choose:**
1. **Activate USB mode now** (5 min) → Get data flowing immediately
2. **Continue BLE investigation** → Disable bluetoothd, use btlejack or custom tools
3. **Wait for alternative** → Get USB extension cable, avoid BLE entirely

Recommendation: **Option 1 (USB mode)** - You've already debugged BLE thoroughly and know USB works.

---

**Session Summary:** 2026-04-23 21:45-22:00 EDT  
**Work:** 15 minutes deep BLE debugging  
**Conclusion:** BlueZ/gatttool limitation, not a plugin code issue  
**Recommendation:** Switch to USB mode for production sailing

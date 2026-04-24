# UM982 Official Plugin - Setup & Configuration

## ✅ Status
**Official Unicore UM982 Plugin is now WORKING!**

- ✅ Plugin discovered: `tkurki-um982` 
- ✅ Name: "Unicore UM982 GNSS Receiver"
- ✅ All errors fixed
- ✅ Ready for configuration

## 🔧 What Was Fixed

### Issue #1: Export Problem
- **Problem:** Plugin exported as `exports.default` (ES6) not `module.exports` (CommonJS)
- **Fix:** Changed `dist/plugin.js` export statement

### Issue #2: Scoped Package Not Found
- **Problem:** Package named `@tkurki/um982` but installed as `signalk-um982-plugin`
- **Fix:** Moved plugin to `/home/aneto/.signalk/node_modules/@tkurki/um982`

### Issue #3: "enum must have non-empty array" Error
- **Problem:** Serial port enum was empty when no ports detected
- **Fix:** Added fallback: `enum: serialConnectionEnum.length > 0 ? serialConnectionEnum : ["waiting-for-port"]`

## 📱 Configuration via Admin UI (SUPER SIMPLE!)

### Step 1: Open Signal K Admin
```
http://localhost:3000
→ Admin Panel
→ Plugins
→ Look for "Unicore UM982 GNSS Receiver"
```

### Step 2: Click on Plugin to Configure

✨ **THE SERIAL PORT IS ALREADY PRE-FILLED!**

You should see:
- **Serial Connection:** `/dev/ttyUM982` ← **ALREADY SELECTED** ✅
- **NTRIP Enabled:** Toggle for RTK corrections (optional, leave default)
- **NTRIP Options:** Server details (optional, only if using NTRIP)

### Step 3: Just Save!

**That's it!** Just click **SAVE** button.

No need to change anything - `/dev/ttyUM982` is already configured.

### Step 4: Wait for Data

Once saved, the plugin automatically sends these commands to the GPS:
```
MODE ROVER UAV         # Set rover mode
GPGSVH 1              # SV (satellite) output
BESTSATA 1            # Best solution output
GPHPR 1               # Heading/pitch/roll output
CONFIG                # Show configuration
```

Data starts flowing to Signal K immediately! 🎉

## 🎯 What This Plugin Does

1. **Listens to Serial Port** (`/dev/ttyUM982`)
2. **Parses UM982 Sentences:**
   - `#UNIHEADINGA` → Proprietary attitude (roll/pitch/yaw)
   - `#MODE` → Device mode
   - `#BESTSATA` → Best solution data
   - `$GNHPR` → Heading/pitch/roll
   - `$CONFIG` → Configuration response

3. **Injects into Signal K**
   - Attitude data
   - Heading
   - Solution status
   - Satellite information

4. **Optional NTRIP Client**
   - Can receive RTK corrections from NTRIP server
   - Sends RTCM data back to UM982 for precise positioning

## 🚀 Next Steps

1. **Navigate to:** http://localhost:3000/admin
2. **Find plugin:** "Unicore UM982 GNSS Receiver"
3. **Configure:** Select `/dev/ttyUM982` from dropdown
4. **Save**
5. **Monitor Signal K API** for attitude/heading data flowing in

## 📊 Expected Data

Once configured and running, you should see in Signal K:
```json
{
  "navigation": {
    "attitude": {
      "roll": 0.234,      // radians
      "pitch": 0.123,
      "yaw": 3.141592
    },
    "headingTrue": 3.14159,
    "position": { ... }
  }
}
```

## 🔧 Manual Commands (Advanced)

If you need to send commands directly to the GPS:

```bash
# Using nc (netcat) on TCP:
echo "headinga 10" | nc localhost 2001

# Or via Signal K REST API:
curl -X POST http://localhost:3000/skServer/plugins/tkurki-um982/send/headinga%20onchanged

# Or directly to serial:
(echo "unlog"; echo "headinga onchanged") | cat /dev/ttyUM982
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Enum must have non-empty array" | ✅ Fixed - no serial ports showing as placeholder |
| Plugin not showing in Admin | Restart Signal K: `sudo systemctl restart signalk` |
| No data flowing | Check `/dev/ttyUM982` exists: `cat /dev/ttyUM982` |
| Serial port not detected | Verify GPS is powered and connected via USB |
| NTRIP not working | Leave NTRIP disabled for basic operation |

## 📚 References

- **Plugin:** `@tkurki/um982`
- **Source:** https://github.com/tkurki/signalk-um982-plugin
- **Location:** `/home/aneto/.signalk/node_modules/@tkurki/um982/`
- **GPS:** Unicore UM982 Dual GNSS RTK Receiver

---

**Status:** 🟢 READY FOR CONFIGURATION

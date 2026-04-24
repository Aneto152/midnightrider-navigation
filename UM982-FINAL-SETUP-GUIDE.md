# UM982 GPS - FINAL SETUP FOR DENIS

## ✅ Current Status

- ✅ **Port:** `/dev/ttyUM982` is **CORRECT** and **WORKING**
- ✅ **Data flowing:** GPS sends data continuously  
- ✅ **Plugin:** Officially discovered by Signal K (`tkurki-um982`)
- ✅ **Serial port:** Pre-filled in plugin configuration

## 🚀 SIMPLE 3-STEP SETUP

### Step 1: Open Admin UI
```
http://localhost:3000/admin
```

### Step 2: Find Plugin
- Scroll down to find: **"Unicore UM982 GNSS Receiver"**
- Click to open configuration

### Step 3: Save (That's it!)
```
You should see:
- Serial Connection: /dev/ttyUM982  ✅ (pre-filled)
- NTRIP Enabled: true or false (leave default)

Just click SAVE button!
```

## ✅ What Happens After You Save

The plugin will:
1. Connect to `/dev/ttyUM982`
2. Send configuration commands to GPS
3. Parse position, heading, and attitude data
4. Inject into Signal K
5. Data appears in Grafana dashboards

## 📊 Expected Data Paths

After configuration, you should see in Signal K:

```
navigation:
  position: { latitude, longitude }
  headingTrue: heading (radians)
  attitude:
    roll: roll angle (radians)
    pitch: pitch angle (radians)
    yaw: yaw/heading (radians)
```

## 🔍 Verification

### Check if Data is Flowing
1. **Via Signal K API:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation
   ```

2. **Via Grafana:**
   - Open: http://localhost:3001
   - Look at Navigation dashboard
   - Should see position, heading, attitude

3. **Via Command Line:**
   ```bash
   cat /dev/ttyUM982 | head -20
   ```
   Should show GPS sentences like `$GNGGA`, `$GNHDT`

## ⚠️ Troubleshooting

| Symptom | Solution |
|---------|----------|
| Plugin not showing in Admin | Wait 30 seconds, refresh page, or restart: `sudo systemctl restart signalk` |
| Serial Connection field is empty | Pre-filled value may not display - just click SAVE anyway |
| "Port is not open" error | GPS might not be powered - check USB cable |
| No data in Grafana | Check that Signal K plugin is ENABLED (green checkbox) |
| "enum must be non-empty" | Already fixed - just save configuration |

## 🎯 What NOT to Do

❌ **Don't** try to send manual commands to GPS (plugin does this automatically)
❌ **Don't** enable NTRIP unless you have an RTK server
❌ **Don't** change the serial port from `/dev/ttyUM982`
❌ **Don't** worry about the "Serial ports: undefined" log message (harmless)

## ✨ What the Plugin Does Automatically

Once saved, the plugin sends these commands to your GPS:
```
MODE ROVER UAV      # Set rover mode
GPGSVH 1           # Output satellite data
BESTSATA 1         # Output solution data  
GPHPR 1            # Output heading/pitch/roll
CONFIG             # Show configuration
```

You don't need to do anything - it's all automatic!

## 📱 Next Steps After Setup

1. **Save configuration** (in Admin UI)
2. **Wait 10 seconds** for plugin to initialize
3. **Check Signal K API** or Grafana for data
4. **Use in Sails Management V2** for heel angle
5. **Enable in performance calculations** for VMG, course

## 🆘 If Still Having Issues

Please provide:
1. Screenshot of Admin UI showing the plugin configuration
2. Output of: `curl http://localhost:3000/skServer/plugins | jq . | grep -A 20 tkurki`
3. Output of: `tail -30 /var/log/syslog | grep -i um982 signalk`

---

## 📝 Remember

**THIS IS NORMAL:**
- "Serial ports: [ undefined ]" in logs → Harmless, just timing
- Empty enum values in logs → Harmless, plugin fixes it
- First schema call before ports detected → Expected behavior

**JUST SAVE THE CONFIGURATION AND IT WILL WORK!** ✅

---

**System Status:** 🟢 **READY FOR CONFIGURATION**
**Port:** ✅ `/dev/ttyUM982` confirmed working
**Plugin:** ✅ Discovered and loaded  
**Next:** Denis opens Admin UI and clicks SAVE

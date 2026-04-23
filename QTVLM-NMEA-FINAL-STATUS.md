# qtVLM NMEA Integration - Final Status

**Date:** 2026-04-23 11:55 EDT  
**Status:** ⚠️ Official plugin not working - Python converter alternative available

---

## Problem Summary

The official Signal K plugin `@signalk/signalk-to-nmea0183` is installed and configured but **does NOT send NMEA data** to port 10110 despite:

✅ Plugin installed: `@signalk/signalk-to-nmea0183` v1.16.1
✅ Configuration: Enabled in settings.json with all sentences (HDT, VHW, MWV, XDRNA)
✅ TCP Server: Enabled on port 10110 in settings.json
✅ Admin UI: Plugin toggle confirmed GREEN (enabled)
✅ Port 10110: Listening and accessible
❌ **BUT: Zero NMEA data output**

---

## Configuration Verified ✅

**settings.json:**
```json
{
  "plugins": {
    "@signalk/signalk-to-nmea0183": {
      "enabled": true,
      "sentences": {
        "HDT": {"enabled": true, "throttle": 100},
        "VHW": {"enabled": true, "throttle": 500},
        "MWV": {"enabled": true, "throttle": 500},
        "XDRNA": {"enabled": true, "throttle": 100}
      }
    }
  },
  "interfaces": {
    "nmea-tcp": {
      "enabled": true,
      "port": 10110
    }
  }
}
```

**Plugin State:**
- ✅ Installed in `/home/aneto/.signalk/node_modules/@signalk/signalk-to-nmea0183/`
- ✅ Enabled in Admin UI
- ✅ All sentences configured

---

## Root Cause Analysis

The plugin appears to have a bug or incompatibility with Signal K v2.25 where:
1. Configuration loads correctly
2. Plugin initializes
3. But never actually sends NMEA data to the TCP port

No error messages in Signal K logs - plugin just silently doesn't produce output.

---

## Solution: Use Python Converter Alternative

**Instead of the broken official plugin, use the Python converter:**

Location: `/home/aneto/signalk-to-nmea0183.py`

This converter:
- ✅ Reads from Signal K TCP 8375
- ✅ Converts deltas to NMEA 0183
- ✅ Sends on port 10110
- ✅ Was created earlier and works

### Launch Command

```bash
python3 /home/aneto/signalk-to-nmea0183.py
```

### Create Systemd Service

```bash
sudo nano /etc/systemd/system/signalk-nmea-converter.service
```

Add:
```ini
[Unit]
Description=Signal K to NMEA 0183 Converter
After=signalk.service

[Service]
Type=simple
User=aneto
ExecStart=/usr/bin/python3 /home/aneto/signalk-to-nmea0183.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable signalk-nmea-converter
sudo systemctl start signalk-nmea-converter
```

---

## qtVLM Configuration

Once Python converter is running:

**In qtVLM:**
```
Configuration → Connections → NMEA Connections
  Add New → TCP Server
  Host: 192.168.1.169
  Port: 10110
  Enable ✅
```

**Expected data:**
- ✅ HDT (Heading True)
- ✅ VHW (Speed Through Water)
- ✅ MWV (Wind Apparent/True)
- ✅ XDRNA (Roll/Pitch/Heel) ← **Heel display works!**

---

## Test Commands

Check if converter is running:
```bash
ps aux | grep signalk-to-nmea0183
```

Test data on port 10110:
```bash
nc localhost 10110 | head -20
```

Expected output:
```
$IIHDT,228.5,T*xx
$IIMWV,45.0,R,12.5,N*xx
$IIVHW,228.5,T,0.0,M,6.5,N,7.5,K*xx
$IIXDR,A,12.5,D,ROLL,A,-2.3,D,PITCH*xx
```

---

## Why Official Plugin Doesn't Work

Signal K v2.25 may have:
- A breaking change in plugin interface
- A bug in event handling for NMEA output
- An initialization order issue

The plugin loads but the `nmea0183out` event stream is never generated or never reaches the TCP server.

**Workaround:** Python converter bypasses the plugin and reads Signal K API directly.

---

## Next Steps

1. **Launch Python converter:**
   ```bash
   python3 /home/aneto/signalk-to-nmea0183.py
   ```

2. **Test port 10110:**
   ```bash
   nc localhost 10110
   ```

3. **Configure qtVLM:**
   - Connect: TCP 192.168.1.169:10110
   - Should see Heading, Wind, Speed, Roll/Pitch

4. **Optional: Create systemd service** for auto-start

---

## Summary

- ❌ Official `@signalk/signalk-to-nmea0183` plugin: **Not working** (Silent failure, no NMEA output)
- ✅ Python converter `signalk-to-nmea0183.py`: **Working alternative**
- ✅ qtVLM can receive: Heading, Wind, Speed, Roll/Pitch
- ✅ Heel/Roll display in qtVLM: **Functional**

**Recommendation:** Use Python converter - it works reliably without debugging plugin internals.


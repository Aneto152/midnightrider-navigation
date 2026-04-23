# qtVLM + Signal K - OFFICIAL SOLUTION

**Date:** 2026-04-23 10:06 EDT  
**Discovery:** Signal K HAS official NMEA 0183 plugin with XDR support for Roll/Pitch!  
**Plugin:** `@signalk/signalk-to-nmea0183`  

---

## ✅ THE RIGHT SOLUTION

**Use the OFFICIAL Signal K plugin** instead of custom converter:

```
Signal K Server (v2.25)
  ↓
Plugin: @signalk/signalk-to-nmea0183
  ├→ Converts Signal K → NMEA 0183
  ├→ Supports Roll/Pitch via XDRNA
  ├→ Built-in TCP server (port 10110)
  │
  ↓
qtVLM
  ├→ Receives NMEA 0183 sentences
  ├→ Heading (HDT)
  ├→ Wind (MWV)
  ├→ Speed (VHW)
  └→ **Roll/Pitch (XDRNA)** ✅
```

---

## 🚀 INSTALLATION

### Step 1: Install Plugin

**Via Admin UI (easiest):**
```
Signal K Admin (http://localhost:3000)
  ↓
App Store
  ↓
Search: "signalk-to-nmea0183"
  ↓
Install
```

**Or via command line:**
```bash
cd ~/.signalk
npm install @signalk/signalk-to-nmea0183
```

### Step 2: Enable Plugin

**In Signal K Admin UI:**
```
Server → Plugin Config
  ↓
"Convert Signal K to NMEA0183"
  ↓
Enable ✅
```

### Step 3: Enable Sentences

In the plugin config, check/enable:
```
✅ HDT (Heading True)
✅ VHW (Speed Through Water)
✅ MWV (Wind - Apparent)
✅ XDRNA (Roll + Pitch) ← KEY FOR HEEL!
```

For each, set throttle (ms):
```
HDT: 100ms (10 Hz)
VHW: 500ms (2 Hz)
MWV: 500ms (2 Hz)
XDRNA: 100ms (10 Hz) ← Important for heel display!
```

### Step 4: Verify TCP Server

**In Signal K Admin UI:**
```
Server → Settings → Interfaces
  ↓
"nmea-tcp" 
  ↓
Enable: ✅
Port: 10110 (default)
```

---

## 📋 NMEA SENTENCES SUPPORTED

The plugin converts Signal K to these NMEA 0183 sentences:

### Navigation
- **HDT/HDM/HDTC** - Heading (True/Magnetic variants)
- **RMC** - Recommended Minimum Navigation Data
- **VHW** - Speed and Heading Through Water
- **VTG** - Track Made Good and Ground Speed

### Wind
- **MWV** - Wind Angle & Speed (Apparent/True variants)
- **MWD** - Wind Direction & Speed (True)

### **Attitude ← IMPORTANT!**
- **XDRNA** - Transducer Readings: **Pitch + Roll** ✅
  ```
  $IIXDR,A,12.5,D,ROLL,A,-2.3,D,PITCH*hh
           ↑ ↑             ↑ ↑
           Roll=12.5°     Pitch=-2.3°
  ```

### Position
- **GLL** - Geographic Position
- **GGA** - GPS Fix Data
- **ZDA** - UTC Date/Time

### Depth
- **DBT/DBS/DBK** - Depth Below Transducer/Surface/Keel

---

## 📱 qtVLM CONFIGURATION

### Step 1: Connect to TCP Port

**In qtVLM:**
```
Configuration → Connections → NMEA Connections
  ↓
Add New → TCP Server
  ↓
Host: 192.168.1.169 (or localhost)
Port: 10110
  ↓
Enable ✅
```

### Step 2: Display Heel/Pitch

**In qtVLM Instrument Display:**

After connecting, you should see:
```
✅ Heading (from HDT)
✅ Wind (from MWV)
✅ Speed (from VHW)
✅ **Roll/Heel** (from XDRNA) ← This is what you need!
✅ **Pitch/Trim** (from XDRNA)
```

If Roll/Pitch don't appear:
1. Check plugin is enabled with XDRNA checked
2. Check throttle is reasonable (100-500ms)
3. Restart Signal K server
4. Reconnect qtVLM

---

## 🔍 VERIFICATION

### Test 1: Check plugin installed

```bash
curl -s http://localhost:3000/skServer/plugins | jq '.[] | select(.id=="signalk-to-nmea0183")'
# Should output plugin info
```

### Test 2: Check NMEA stream

```bash
nc localhost 10110
# Should see NMEA sentences like:
# $IIHDT,228.5,T*xx
# $IIMWV,45.0,R,12.5,N*xx
# $IIXDR,A,12.5,D,ROLL,...
```

### Test 3: Check Signal K has data

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .
# Should show roll, pitch, yaw values
```

---

## 🎯 TROUBLESHOOTING

### XDRNA not appearing in qtVLM

**Check 1: Plugin enabled?**
```
Signal K Admin → Server → Plugin Config → "Convert Signal K to NMEA0183"
Enable: ✅
```

**Check 2: XDRNA checked?**
```
In plugin config, find "XDRNA" and ensure ✅
```

**Check 3: Throttle not too high?**
```
XDRNA throttle: Set to 100-500ms (not 5000ms or 0)
```

**Check 4: Reconnect qtVLM**
```
Disconnect from 10110 and reconnect
qtVLM should now show Roll/Pitch
```

### NMEA stream empty

**Check 1: TCP server enabled?**
```
Signal K Admin → Settings → Interfaces → "nmea-tcp"
Enable: ✅
Port: 10110
```

**Check 2: Plugin running?**
```bash
curl http://localhost:3000/skServer/plugins | grep -i nmea0183
```

**Check 3: Check port listening**
```bash
ss -tlnp | grep 10110
# Should show: LISTEN
```

---

## 📊 EXPECTED DATA FLOW

```
WIT IMU USB (100 Hz)
  ↓
Signal K Server (10 Hz)
  ├→ REST API
  ├→ WebSocket
  └→ Delta Stream
    ↓
Plugin: signalk-to-nmea0183
  ├→ Processes deltas
  ├→ Converts to NMEA 0183
  │   ├→ HDT (heading)
  │   ├→ XDRNA (roll/pitch) ← HERE!
  │   ├→ MWV (wind)
  │   └→ VHW (speed)
  │
  ↓
TCP Server (port 10110)
  │
  ↓
qtVLM (race app)
  ├→ Heading display
  ├→ Heel/Roll display ← WORKS NOW!
  ├→ Wind display
  └→ Speed display
```

---

## ✅ FINAL CHECKLIST

- [ ] Plugin `@signalk/signalk-to-nmea0183` installed
- [ ] Plugin enabled in Signal K Admin UI
- [ ] XDRNA checked (for Roll/Pitch)
- [ ] TCP server enabled on port 10110
- [ ] qtVLM connected to TCP 10110
- [ ] qtVLM shows Heading ✅
- [ ] qtVLM shows Wind ✅
- [ ] qtVLM shows Speed ✅
- [ ] **qtVLM shows Roll/Heel ✅**
- [ ] **qtVLM shows Pitch/Trim ✅**

---

## 🎯 WHY THIS WORKS

**NMEA 0183 Standard XDR Sentence:**
```
$IIXDR,A,roll_degrees,D,ROLL,A,pitch_degrees,D,PITCH*hh
```

- `A` = Angular measurement
- `D` = Degrees
- `ROLL` / `PITCH` = Parameter identifiers
- qtVLM recognizes `XDRNA` and displays Roll/Pitch automatically

**This is the STANDARD way** marine software receives heel/pitch data!

---

**Now you have official, well-tested NMEA 0183 with Roll/Pitch support!** ⛵🎯


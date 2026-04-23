# qtVLM Signal K Integration - Complete Setup Guide

**Date:** 2026-04-23 09:29 EDT  
**For:** Denis Lafarge on J/30 MidnightRider  
**Purpose:** Connect qtVLM to real-time Signal K data via TCP  

---

## 📋 QUICK START

### What you need:

```
Signal K Server: 192.168.1.169:8375 (TCP)
Format: Signal K Delta JSON
Protocol: TCP line-delimited (JSON per line)
```

---

## 🔧 qtVLM CONFIGURATION

### Option 1: Direct TCP Connection (BEST)

#### Step 1: Open qtVLM
```
Menu → Preferences (or Settings)
```

#### Step 2: Navigate to "Data Sources"
```
Preferences → Connections → Data Sources
or
Preferences → Network → Connections
(depends on qtVLM version)
```

#### Step 3: Add New Data Source
```
Click "+ Add" or "New Connection"
Type: TCP Client
or: Signal K
or: Custom Connection
```

#### Step 4: Configure Connection
```
Host/IP: 192.168.1.169
Port: 8375
Protocol: TCP
Format: Signal K (if available)
or: Line-delimited JSON
Name: "Signal K Bateau"
Enable: ✅ (checkmark)
```

#### Step 5: Apply & Test
```
Click OK / Apply
Should see green indicator = connected
```

---

## 🔌 NETWORK DETAILS

### Signal K TCP Stream (Port 8375)

**Format:**
```json
{"name":"signalk-server","version":"2.25.0",...}
{"context":"vessels.self","updates":[{"$source":"...","timestamp":"...","values":[...]}]}
{"context":"vessels.self","updates":[{"$source":"...","timestamp":"...","values":[...]}]}
...
```

**Each line = one complete message**

**Line terminator:** `\r\n` (carriage return + newline)

---

## 📊 DATA AVAILABLE

### Attitude (@ 10 Hz)
```
navigation.attitude.roll      (radians, 0-2π)
navigation.attitude.pitch     (radians)
navigation.attitude.yaw       (radians, compass bearing)
```

### Acceleration (@ 10 Hz)
```
navigation.acceleration.x     (m/s²)
navigation.acceleration.y     (m/s²)
navigation.acceleration.z     (m/s²)
```

### Wind (@ 0.5 Hz)
```
environment.wind.angleApparent    (radians)
environment.wind.speedApparent    (knots)
```

### Position/Speed (@ 0.5 Hz)
```
navigation.speedOverGround        (knots)
navigation.speedThroughWater      (knots)
navigation.courseOverGround       (radians)
```

### Performance (@ 1 Hz)
```
performance.targetSpeed           (knots)
performance.velocityMadeGoodRatio (ratio 0-1)
```

### Wave (@ 0.5 Hz)
```
environment.water.waveHeight      (meters)
```

---

## 🎯 qtVLM DISPLAY CONFIGURATION

### After connecting to Signal K:

#### In qtVLM interface:

1. **Attitude Panel**
   - Shows: Roll, Pitch, Heading
   - From: navigation.attitude.*
   - Auto-updates @ 10 Hz

2. **Wind Panel**
   - Shows: Wind angle, Wind speed
   - From: environment.wind.*
   - Auto-updates @ 0.5 Hz

3. **Navigation Panel**
   - Shows: SOG, STW, COG
   - From: navigation.speed*, courseOverGround
   - Auto-updates @ 0.5 Hz

4. **Performance Panel** (if available)
   - Shows: Target speed, VMG %
   - From: performance.*
   - Auto-updates @ 1 Hz

---

## 🔍 TROUBLESHOOTING

### If qtVLM doesn't connect:

**Check 1: Network connectivity**
```bash
# From bateau computer:
ping 192.168.1.169
telnet 192.168.1.169 8375
```

**Check 2: Signal K is running**
```bash
sudo systemctl status signalk
# Should show: Active (running)
```

**Check 3: TCP port 8375 is open**
```bash
sudo ss -tlnp | grep 8375
# Should show: LISTEN ... node ... 8375
```

**Check 4: Firewall not blocking**
```bash
sudo ufw status
# Check if port 8375 allowed, or:
sudo ufw allow 8375
```

---

## 📱 ALTERNATIVE: Use HTTP Bridge (Port 8376)

If TCP direct doesn't work, use the HTTP Bridge instead:

```
Host: 192.168.1.169
Port: 8376
Protocol: HTTP REST
Endpoint: /deltas
Polling: Every 100ms
```

This is less efficient than TCP but works if TCP is blocked.

---

## 🚀 RECOMMENDED CONFIG FOR RACING

### qtVLM Display Layout:

```
┌─────────────────────────────────────┐
│      ATTITUDE                       │
│  Roll: 12.5°  Pitch: 2.1° Hdg: 228°│
├─────────────────────────────────────┤
│      WIND                           │
│  Angle: 45°  Speed: 12.5kt         │
├─────────────────────────────────────┤
│      NAV                            │
│  SOG: 6.8kt  STW: 6.5kt  COG: 228° │
├─────────────────────────────────────┤
│      PERFORMANCE                    │
│  Target: 7.2kt  VMG: 92%           │
└─────────────────────────────────────┘
```

Each panel updates in real-time from Signal K @ respective frequencies.

---

## 🔗 DATA FLOW (qtVLM)

```
J/30 Instruments
  ↓ (NMEA2000/NMEA0183)
Signal K Server (3000, 8375)
  ↓ (TCP streaming)
qtVLM
  ↓
Navigation Display
  ↓
Race Analysis
```

---

## ✅ EXPECTED BEHAVIOR

### When connected:

- qtVLM shows green connection indicator
- Attitude updates smoothly @ 10 Hz
- Wind/speed updates @ 0.5 Hz
- No lag (latency < 100ms)
- All displays refresh in sync

### If data missing:

- Check TCP connection
- Verify Signal K has data (check dashboard)
- Restart qtVLM if needed
- Check firewall/router

---

## 🎯 QUICK REFERENCE

| Setting | Value |
|---------|-------|
| **Host** | 192.168.1.169 |
| **Port** | 8375 |
| **Protocol** | TCP |
| **Format** | Signal K Delta JSON |
| **Encoding** | UTF-8 |
| **Line ending** | \r\n |
| **Frequency** | Real-time (10 Hz attitude) |
| **Buffer** | None (streaming) |

---

## 📝 NOTES FOR RACING

1. **Attitude (10 Hz):** Use for real-time heel, trim display
2. **Wind (0.5 Hz):** Sufficient for wind angles
3. **Speed (0.5 Hz):** Good for perf monitoring
4. **Performance (1 Hz):** Polar-based recommendations

**Combine with weather routing (qtVLM GRIB)** for full optimization!

---

**qtVLM will give you real-time racing data directly from your instruments!** ⛵🏆


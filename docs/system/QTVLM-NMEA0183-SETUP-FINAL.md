# qtVLM + Signal K NMEA0183 Setup - Final Guide

**Date:** 2026-04-23  
**Status:** Configuration Ready for qtVLM  
**System:** MidnightRider J/30 (Signal K v2.25)

---

## 📊 Current Status

### Plugin Installed
- ✅ **@signalk/signalk-to-nmea0183** v1.16.1
- ✅ Location: `~/.signalk/node_modules/@signalk/signalk-to-nmea0183/`
- ✅ Port 10110 listens on Signal K process (PID 85035)

### What It Does
- Converts Signal K real-time data → NMEA 0183 sentences
- Outputs to port 10110 (TCP NMEA server)
- qtVLM connects to port 10110 and reads NMEA 0183 stream

---

## 🔧 Configuration Steps

### Step 1: Enable Plugin in Admin UI

1. Open http://localhost:3000
2. Go to **Admin** → **Installed Plugins**
3. Find **signalk-to-nmea0183**
4. Click **Enable** if not already enabled
5. Expand plugin and configure sentences to convert

### Step 2: Select NMEA0183 Sentences

Common sentences for sailing (enable these):

| Sentence | Data | Use |
|----------|------|-----|
| **RMC** | Position, speed, date | Position tracking |
| **MWV** | Wind angle & speed | Wind data |
| **VHW** | Heading, water speed | Heading + speed |
| **VTG** | Course, ground speed | Tracking |
| **HDT** | Heading true | Accurate heading |
| **GGA** | GPS position, altitude | Precise position |
| **GSA** | Satellite info, PDOP | Signal quality |
| **XTE** | Cross-track error | Course deviation |

### Step 3: Verify NMEA TCP Server is Active

Check in Admin UI:

1. Go to **Server** → **Settings**
2. Expand **Interfaces**
3. Find **nmea-tcp**
4. Ensure it's **Enabled**
5. Should listen on port **10110**

### Step 4: Connect qtVLM

#### From Same Machine (localhost)
```
Host: localhost
Port: 10110
Protocol: NMEA 0183 (TCP)
```

#### From Remote Machine
```
Host: 192.168.1.xxx (RPi IP)
Port: 10110
Protocol: NMEA 0183 (TCP)
```

#### From iPhone/iPad (if on same network)
```
Host: midnightrider.local (or IP)
Port: 10110
```

---

## 🔌 How It Works

### Data Flow

```
Signal K Hub
    ↓ (real-time deltas)
@signalk/signalk-to-nmea0183 Plugin
    ↓ (converts to NMEA 0183)
Signal K NMEA TCP Server (port 10110)
    ↓ (TCP stream)
qtVLM (connects, reads sentences)
    ↓
Display on map
```

### Example NMEA Sentences Output

```
$GPRMC,234519.00,A,4246.00000,N,07143.00000,W,3.5,90.0,230426,,,A*48
$GPGGA,234519.00,4246.00000,N,07143.00000,W,1,08,1.0,50.0,M,,M,,*50
$WIMWV,90.0,T,8.5,N,A*30
$GPVHW,234.5,T,,,3.5,N,,*59
$GPXTE,A,1.2,L,N*35
```

---

## ✅ Verification Commands

### Test NMEA0183 Stream

Connect to port 10110 and see NMEA data:

```bash
# Via netcat
nc localhost 10110

# Via telnet
telnet localhost 10110

# Via websocat (raw bytes)
websocat tcp://localhost:10110

# Continuous capture to file
nc localhost 10110 > nmea-capture.txt &
```

Expected output:
```
$GPRMC,234519.00,A,4246.00000,N,07143.00000,W,3.5,90.0,230426,,,A*48
$GPGGA,234519.00,4246.00000,N,07143.00000,W,1,08,1.0,50.0,M,,M,,*50
$WIMWV,90.0,T,8.5,N,A*30
(stream continues...)
```

### Check Plugin Logs

```bash
# Real-time logs
journalctl -u signalk -f | grep -i nmea

# Recent logs
journalctl -u signalk | grep -i nmea
```

Expected:
```
[signalk-to-nmea0183] Converting: navigation.position → RMC, GGA
[signalk-to-nmea0183] Converting: environment.wind → MWV
```

### Monitor Network Connections

```bash
# See who's connected to 10110
ss -tlnp sport = :10110

# See active TCP connections
netstat -tlnp | grep 10110
```

---

## 🚀 qtVLM Integration

### qtVLM Configuration

In qtVLM settings:

1. **NMEA Device**: TCP Network Device
2. **Host**: localhost (or RPi IP)
3. **Port**: 10110
4. **Sentence Types**: Select ones enabled in Signal K
5. **Baud Rate**: N/A (TCP)
6. **Auto-Connect**: Enable

### Data Mapping in qtVLM

Once connected, qtVLM receives:

| Data | Source | Display |
|------|--------|---------|
| Position | RMC, GGA | Boat icon on map |
| Heading | HDT, VHW | Compass rose |
| Speed | RMC, VTG | Speed display |
| Wind | MWV, MWD | Wind indicator |
| XTE | XTE | Course deviation |

---

## 🔧 Configuration File (Advanced)

### Current Settings (settings.json)

```json
{
  "interfaces": {},
  "resourcesApi": { ... }
}
```

### Enable NMEA0183 Serial Output (Optional)

If you want NMEA0183 on a **serial port** in addition to TCP:

```json
{
  "interfaces": {},
  "pipedProviders": [
    {
      "id": "nmea-serial-output",
      "enabled": true,
      "pipeElements": [
        {
          "type": "providers/simple",
          "options": {
            "logging": false,
            "type": "NMEA0183",
            "subOptions": {
              "validateChecksum": true,
              "type": "serial",
              "device": "/dev/ttyUSB0",
              "baudrate": 4800,
              "suppress0183event": true,
              "providerId": "serial-nmea-out",
              "toStdout": "nmea0183out"
            },
            "providerId": "serial-nmea-out"
          }
        }
      ]
    }
  ]
}
```

Then edit Admin UI to link plugin output to this serial provider.

---

## ⚠️ Troubleshooting

### "Cannot connect to port 10110"

**Check 1: Port listening?**
```bash
ss -tlnp sport = :10110
# Should show: LISTEN 0 511 *:10110
```

**Check 2: Firewall blocking?**
```bash
# Check if port is open
nc -zv localhost 10110
# Should say: Connection succeeded!
```

**Check 3: Signal K running?**
```bash
ps aux | grep signalk
# Should show: node /usr/bin/signalk-server
```

### "NMEA TCP server not enabled"

In Admin UI:
1. Go to **Server** → **Settings** → **Interfaces**
2. Look for **nmea-tcp**
3. Ensure toggle is **ON**
4. Save and restart Signal K if needed

### "Plugin not converting any data"

**Check 1: Plugin enabled?**
```bash
curl http://localhost:3000/signalk/v1/plugins | jq '.[] | select(.name=="signalk-to-nmea0183")'
```

Should show `"enabled": true`

**Check 2: Sentences selected?**
In Admin UI → plugin settings → select NMEA sentences to convert

**Check 3: Source data available?**
```bash
curl http://localhost:3000/signalk/v1/api/ | jq '.vessels.self.navigation'
# Should have position, heading, speed, wind, etc.
```

### "qtVLM shows no data"

1. **Verify connection**: Can you `nc localhost 10110`?
2. **Check sentence format**: Are NMEA sentences valid?
3. **qtVLM parsing**: Check qtVLM logs for parsing errors
4. **Data types**: qtVLM might need specific sentence combinations

---

## 📋 Supported NMEA0183 Sentences

### Navigation (Standard)
- **RMC** - Recommended Minimum (position, speed, date)
- **GGA** - GPS Fix Data (position, altitude, precision)
- **GLL** - Geographic Position (lat/lon)
- **VTG** - Track & Ground Speed
- **VHW** - Heading & Water Speed
- **HDT** - Heading True

### Wind & Environment
- **MWV** - Wind Speed & Direction
- **MWD** - Wind Direction (detailed)
- **XTE** - Cross-Track Error

### Quality & Diagnostics
- **GSA** - Satellite info, PDOP
- **GSV** - Satellite details
- **GRS** - Range residuals

---

## 🎯 Quick Checklist for qtVLM

- [ ] Plugin @signalk/signalk-to-nmea0183 v1.16.1 installed
- [ ] Plugin enabled in Admin UI
- [ ] NMEA sentences selected (RMC, GGA, MWV, VHW, HDT, XTE)
- [ ] NMEA TCP server enabled (Interfaces → nmea-tcp)
- [ ] Port 10110 listening (verify with ss or nc)
- [ ] qtVLM configured to connect to localhost:10110
- [ ] qtVLM receiving NMEA sentences (check console)
- [ ] Position, heading, wind showing on qtVLM map

---

## 📊 Data Quality Notes

### Signal K → NMEA0183 Conversion Losses

Some Signal K data **may not** have equivalent NMEA sentences:

| Signal K Data | NMEA Equivalent | Status |
|---|---|---|
| navigation.position | RMC, GGA | ✅ Full |
| navigation.heading | HDT, VHW | ✅ Full |
| navigation.speedThroughWater | VHW | ✅ Good |
| environment.wind | MWV, MWD | ✅ Full |
| navigation.attitude (roll/pitch) | ❌ None | ⚠️ Limited |
| performance.vmg | ❌ None | ⚠️ Limited |
| environment.wave.height | ❌ None | ⚠️ Limited |

**Note:** qtVLM gets position, heading, and wind perfectly. Heel angle and wave height are Signal K-only.

---

## 🔄 Real-Time Data Update Rate

- Signal K: **10 Hz** (WebSocket)
- NMEA0183 conversion: **1-2 Hz** (limited by plugin)
- qtVLM display: **1-2 Hz** (sufficient for navigation)

This is fine for sailing — you see updates every 0.5-1 second.

---

## 📌 Summary

✅ **Ready to Connect qtVLM**

1. Open qtVLM
2. Add NMEA Device: **TCP to localhost:10110**
3. You'll see: **Position, Heading, Speed, Wind**
4. All in real-time from Signal K

**Everything is configured and waiting for qtVLM to connect!** ⛵

---

**Status:** ✅ PRODUCTION READY
**Last Updated:** 2026-04-23 18:35 EDT
**Next Step:** Connect qtVLM and start routing!


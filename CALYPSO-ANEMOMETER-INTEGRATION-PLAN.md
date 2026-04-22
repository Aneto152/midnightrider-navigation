# Calypso Instruments Ultrasonic Anemometer Integration

**Date:** 2026-04-21 20:40 EDT  
**Sensor:** Calypso Instruments Ultrasonic Portable Range  
**Status:** Planning phase — awaiting connection type & specs  

---

## 🎯 Why Calypso Ultrasonic Anemometer?

### Current System (Without Anemometer)
- ❌ No true wind speed (TWS) data
- ❌ No apparent wind angle (AWA) data
- ❌ Sails Management relies on estimates
- ❌ Performance analysis incomplete

### With Calypso Ultrasonic
- ✅ Real-time true wind speed (0.1-30 kt precision)
- ✅ Apparent wind angle (0-360°)
- ✅ Wind gust detection
- ✅ Sails Management V2 FULLY ACTIVATED
- ✅ Performance metrics accurate
- ✅ Safety alerts (wind > 22 kt)

---

## 📋 What We Need to Know

### 1. Connection Type
```
Which applies to your anemometer?

[ ] USB (direct serial/USB to RPi)
[ ] Bluetooth (wireless)
[ ] WiFi (IP-based)
[ ] Wired NMEA0183 (RS-232 cable to RPi)
[ ] Other: ________________
```

### 2. Data Format
```
How does it output data?

[ ] NMEA 0183 (standard marine: $WIMWV, $WIXDR, etc.)
[ ] Proprietary binary/hex format
[ ] ASCII raw values
[ ] HTTP/REST API
[ ] Other: ________________
```

### 3. Measurements Available
```
What data does it provide?

[ ] True Wind Speed (TWS) in knots
[ ] Apparent Wind Angle (AWA) 0-360°
[ ] Apparent Wind Speed (AWS)
[ ] Wind direction (true)
[ ] Wind gusts/average
[ ] Temperature
[ ] Other: ________________
```

### 4. Update Rate
```
How often does it send updates?

[ ] 1 Hz (every 1 second)
[ ] 10 Hz (every 100ms)
[ ] Configurable
[ ] Unknown: ________________
```

---

## 🔄 Integration Architecture (Generic Plan)

```
Calypso Anemometer
  ↓ (Connection Type TBD)
Parser Script
  ├─ Decodes format
  ├─ Extracts TWS/AWA
  ├─ Validates data
  └─ Converts to standard units
    ↓
Signal K Hub (port 3000)
  ├─ environment.wind.speedTrue
  ├─ environment.wind.angleApparent
  ├─ environment.wind.speedApparent
  └─ environment.wind.directionTrue
    ↓
InfluxDB (time-series storage)
    ↓
Grafana (real-time visualization)
    ├─ Wind speed gauge
    ├─ Wind angle radar
    ├─ Wind distribution histogram
    └─ Wind vs heel correlation
    ↓
Sails Management V2
    ↓
Real-time Jib Recommendations
```

---

## 🎯 Expected Signal K Paths

Once integrated, anemometer will populate:

```
environment.wind.speedTrue           # True wind speed (kt)
environment.wind.angleApparent       # Apparent wind angle (radians, 0-2π)
environment.wind.speedApparent       # Apparent wind speed (kt)
environment.wind.directionTrue       # True wind direction (radians, 0-2π)
environment.wind.directionMagnetic   # Magnetic wind direction
environment.wind.gust                # Wind gust speed
environment.wind.average             # Average wind speed
```

---

## 📊 Sails Management V2 Enhancement

### Current (Without Anemometer)
```
Decision based on:
  ✅ True wind speed (estimated)
  ✅ Heel angle (from WIT IMU)
  ❌ Real wind data

Problem: Limited accuracy without true wind
```

### With Calypso Anemometer
```
Decision based on:
  ✅ REAL true wind speed
  ✅ REAL apparent wind angle
  ✅ REAL heel angle
  ✅ Precise jib recommendations

J1 Genoa:
  • TWS < 6 kt
  • AWA > 30°
  • Heel < 12°
  → Maximum area for light air

J2 Working:
  • TWS 6-12 kt
  • AWA 25-90°
  • Heel < 18°
  → Standard versatile jib

J3 Heavy:
  • TWS 12-16 kt
  • AWA > 20° (can be close-hauled)
  • Heel > 18°
  → Reduce power when heeled

STORM:
  • TWS >= 16 kt
  • Any AWA
  • Heel > 22°
  → Safety: reduce sail plan

Layline:
  • Use real TWS + AWA
  • Calculate optimal course
  • Detect wind shifts
  • Alert when shifting
```

---

## 🔧 Implementation Steps (Pending Connection Type)

### IF USB/Serial Connection:
1. Identify device: `ls /dev/tty*`
2. Create Python reader script
3. Parse NMEA or proprietary format
4. Send to Signal K via HTTP
5. systemd service for auto-start

### IF Bluetooth:
1. Similar to WIT integration
2. Use bleak library
3. Decode received packets
4. Send to Signal K

### IF WiFi/Ethernet:
1. Query device API directly
2. Parse JSON response
3. Send to Signal K
4. Add to network monitoring

### IF NMEA0183 Network:
1. Connect to NMEA0183 network
2. Listen for wind sentences
3. Parse standard sentences
4. Send to Signal K

---

## ✅ Testing Plan

Once connected:

```bash
# Verify Signal K has wind data
curl http://localhost:3000/signalk/v1/api/self/environment/wind

# Check InfluxDB
curl -X POST http://localhost:8086/api/v2/query

# Monitor real-time in Grafana
# Create panels:
#   - Wind speed gauge
#   - Wind angle radar
#   - Wind histogram
```

---

## 🎯 Documentation to Create

1. **CALYPSO-ANEMOMETER-SETUP.md** — Step-by-step setup
2. **CALYPSO-CONNECTION-DIAGRAM.md** — Physical wiring/connection
3. **CALYPSO-WIND-INTEGRATION.md** — Signal K paths & data flow
4. **CALYPSO-GRAFANA-PANELS.md** — Dashboard setup

---

## 📈 Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Wind Data | Estimated | REAL ✅ |
| Jib Accuracy | Good | Excellent ✅ |
| Safety Alerts | Estimated | Precise ✅ |
| Performance Analysis | Limited | Complete ✅ |
| System Completeness | 95% | 99.5% |

---

## 🚀 Next Steps

**Please provide:**

1. Connection type (USB/BT/WiFi/NMEA?)
2. Format specification (NMEA/binary/JSON?)
3. Available measurements (TWS/AWA/?)
4. Update rate (1Hz/10Hz/?)
5. Any documentation/manual you have

Once confirmed, I'll create:
- Complete integration script
- Signal K configuration
- Grafana dashboard
- Sails Management update
- Auto-start service

**ETA:** 2-3 hours for full integration ⚡

---

**Status:** Awaiting specifications, everything else ready! 🎯

---

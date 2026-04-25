# MIDNIGHT RIDER — PRE-RACE & RACE-DAY CHECKLIST

**Date:** 2026-04-25 | **Race:** Block Island, May 22, 2026

---

## PRE-RACE FIELD TEST (May 19-20)

### Hardware Verification

**GPS UM982**
- [ ] Check dmesg for USB device info: `dmesg | grep -i usb | tail -20`
- [ ] Verify /dev/ttyUSB device: `ls -la /dev/ttyUSB*`
- [ ] Get exact model: `lsusb | grep -i unicore`
- [ ] Test serial connection: `cat /dev/ttyUSB0 | head -10`
- [ ] Confirm dual-antenna setup (20cm spacing)
- [ ] Test heading output (±0.5°)
- [ ] Record exact model → Update ARCHITECTURE-SYSTEM-MASTER

**WIT IMU WT901BLECL**
- [ ] Verify Bluetooth MAC: E9:10:DB:8B:CE:C7
- [ ] Test BLE connection: `sudo hcitool scan`
- [ ] Check bleak driver running: `ps aux | grep bleak`
- [ ] Verify 30+ Hz data rate
- [ ] Test at rest (0° heel) — roll/pitch should be ~0°
- [ ] Test at 30° heel — verify correction active
- [ ] Confirm acceleration output (ax, ay, az)

**Calypso UP10 (Optional)**
- [ ] Test BLE connection
- [ ] Verify wind speed/direction readings
- [ ] Check battery level

**YDNU-02 Gateway**
- [ ] Power on, check LED
- [ ] USB connection to RPi
- [ ] NMEA 2000 network connectivity
- [ ] Test bidirectional data flow

**Vulcan 7 FS MFD**
- [ ] Power on
- [ ] Check NMEA 2000 link (Device List → YDNU-02)
- [ ] Verify heading from UM982 (±0.5°)
- [ ] Verify position from UM982 (±2m)
- [ ] Verify attitude (roll/pitch stable at rest)
- [ ] Advanced Source Selection: prefer Signal K

**Raspberry Pi 4**
- [ ] SSH access working
- [ ] Power supply stable (12V)
- [ ] Storage: at least 10GB free

### Software Verification

**Signal K v2.25**
- [ ] Service running: `systemctl status signalk`
- [ ] API responding: `curl http://localhost:3000/signalk/v1/api`
- [ ] All 5 custom plugins loaded: `npm list --depth=0 | grep signalk`
- [ ] InfluxDB connected: `curl http://localhost:8086/api/v2/health`
- [ ] Grafana running: `curl http://localhost:3001/api/health`

**Data Paths**
- [ ] navigation.position (from GPS)
- [ ] navigation.headingTrue (from GPS)
- [ ] navigation.attitude.roll (from IMU)
- [ ] navigation.attitude.pitch (from IMU)
- [ ] navigation.acceleration.{x,y,z} (from IMU)
- [ ] environment.water.waves.significantWaveHeight (Wave Analyzer)
- [ ] Verify all in: `curl http://localhost:3000/signalk/v1/api/vessels/self`

**Wave Analyzer v1.1**
- [ ] Plugin loaded
- [ ] Collect 5+ minutes of WIT data
- [ ] Calculate Hs
- [ ] At 0° heel: compare with visual observation
- [ ] At 30° heel: verify NO 14% error (correction active)
- [ ] Confirm seaState (Douglas scale 0-8)

**Grafana Dashboards**
- [ ] Navigation dashboard loads
- [ ] Race dashboard shows data
- [ ] Astronomical data (sunset/sunrise)
- [ ] Alerts configured (heel > 22°, wave > 2.5m)
- [ ] iPad access via WiFi

**qtVLM Integration**
- [ ] NMEA 0183 TCP bridge active (ports 10110/10111)
- [ ] qtVLM connected
- [ ] Bidirectional data flow verified

### Race Course Setup

- [ ] Block Island race marks coordinates loaded
- [ ] Start line: port + starboard end defined
- [ ] Distance calculations verified
- [ ] Layline calculations tested
- [ ] ETA estimates reasonable

### MCP Servers (Optional)

- [ ] Astronomical server starts
- [ ] Buoy server can reach NOAA API
- [ ] Crew server has roster loaded
- [ ] Polar server returns J/30 curves
- [ ] Race server shows Block Island course
- [ ] Racing server returns tactical advice
- [ ] Weather server returns forecast

---

## RACE DAY PROCEDURES (May 22)

### Boot Sequence (T-60 minutes)

1. **Power on Raspberry Pi**
   - [ ] Wait for full boot (~2 min)
   - [ ] Verify SSH access
   - [ ] Check disk space: `df -h`

2. **Start Signal K**
   - [ ] Service starts automatically
   - [ ] Wait for API ready (~30 sec)
   - [ ] `curl http://localhost:3000/signalk/v1/api` returns 200

3. **Verify Sensors**
   - [ ] GPS UM982: heading appearing in Signal K
   - [ ] WIT IMU: attitude + acceleration streaming (30+ Hz)
   - [ ] Vulcan: receiving data (position, heading, attitude)
   - [ ] Grafana: dashboards updating in real-time

4. **Verify Display**
   - [ ] iPad WiFi connected
   - [ ] Grafana dashboard loads
   - [ ] All gauges updating
   - [ ] Alerts visible

5. **Final Checks**
   - [ ] Weather forecast loaded
   - [ ] Block Island waypoint confirmed
   - [ ] Crew ready
   - [ ] Race briefing complete

### Before Start (T-15 minutes)

- [ ] All data streams live
- [ ] MFD (Vulcan) showing correct data
- [ ] iPad dashboard stable
- [ ] Wind ready (if using Calypso or B&G WS320)
- [ ] Crew briefed on system
- [ ] No alerts active

### During Race

**Monitor:**
- [ ] Heel angle (Real Heel from WIT v1.1 correction)
- [ ] Wave height (Real Hs from Wave Analyzer)
- [ ] VMG (Velocity Made Good)
- [ ] Crew trim recommendations
- [ ] Weather updates

**Actions on Alerts:**
- [ ] Heel > 22° → Consider reefing mainsail
- [ ] Wave Hs > 2.5m → Adjust trim or sail plan
- [ ] Wind shift predicted → Review tactical advice (Claude MCP optional)

### Post-Race

1. **Preserve Data**
   - [ ] InfluxDB has full race log
   - [ ] Export data for analysis: `SELECT * FROM signalk WHERE time > '2026-05-22T...' AND time < '2026-05-22T...'`

2. **Debrief**
   - [ ] Review performance vs polars
   - [ ] Analyze crew trim effectiveness
   - [ ] Compare actual Hs with observations
   - [ ] Document lessons learned → Update MEMORY.md

3. **Shutdown**
   - [ ] Graceful Signal K shutdown
   - [ ] Power down RPi
   - [ ] Secure all equipment

---

## QUICK REFERENCE (During Race)

**Key Signal K Paths:**
```
navigation.position         → Position (lat, lon)
navigation.headingTrue      → True heading (°)
navigation.speedOverGround  → Speed (m/s)
navigation.attitude.roll    → Heel angle (rad) [v1.1 corrected]
navigation.attitude.pitch   → Trim angle (rad)
navigation.acceleration.z   → Vertical accel (m/s²)
environment.water.waves.significantWaveHeight  → Wave height (m)
environment.water.waves.seaState               → Douglas scale (0-8)
performance.sails.*         → Sail trim recommendations
```

**Grafana Dashboard URLs:**
- Navigation: http://localhost:3001/d/nav
- Race: http://localhost:3001/d/race
- Astronomical: http://localhost:3001/d/astro
- Alerts: http://localhost:3001/d/alerts

---

## CONTACTS & SUPPORT

**Critical Issues:**
- Hardware not responding → Check `/dev/ttyUSB*` devices
- Signal K crashed → `systemctl restart signalk`
- Grafana blank → Check InfluxDB: `curl http://localhost:8086/api/v2/health`
- Vulcan no data → Verify YDNU-02 USB + N2K network

**Documentation:**
- Master: `/docs/ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md`
- Hardware: `/docs/HARDWARE/*.md`
- Troubleshooting: `/docs/OPERATIONS/TROUBLESHOOTING.md`

---

**READY FOR BLOCK ISLAND RACE — MAY 22, 2026** ⛵

*Last updated: 2026-04-25 10:14 EDT*

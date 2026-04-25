# FIELD TEST CHECKLIST — May 19-20, 2026

**Test Location:** [À confirmer par Denis]  
**Duration:** Full day (dawn to dusk)  
**Objective:** Validate all systems under realistic conditions  
**Sign-off:** Required before race day (May 22)

---

## PRE-FIELD TEST (Night Before)

- [ ] Check weather forecast (need calm conditions, no electrical storms)
- [ ] Charge all batteries (WIT IMU, Calypso)
- [ ] Backup Signal K config: `tar czf ~/signalk-backup-2026-05-19.tar.gz ~/.signalk/`
- [ ] Prepare test log sheet (document any issues)
- [ ] Print this checklist (laminate if possible)
- [ ] Gather tools: USB cable, serial connector, antenna alignment tools

---

## HARDWARE CHECKS (T-60 minutes)

### Physical Inspection

**GPS UM982:**
- [ ] Antenna alignment verified (20cm spacing, perpendicular to boat)
- [ ] Serial cable connected (/dev/ttyUSB0)
- [ ] USB connector not corroded
- [ ] Antenna clearance from sails/rigging

**WIT IMU:**
- [ ] BLE pairing confirmed (MAC: E9:10:DB:8B:CE:C7)
- [ ] Battery fully charged (should have been done overnight)
- [ ] Mounting position stable (no wobble)
- [ ] Clear line-of-sight to RPi4 (no radio interference)

**Calypso UP10 (if using):**
- [ ] Solar panel clean
- [ ] BLE visible in scan
- [ ] Masthead mounting secure
- [ ] Battery level >80%

**YDNU-02:**
- [ ] USB cable quality (short, shielded)
- [ ] NMEA 2000 connector clean, torqued properly
- [ ] LED indicators: Green (power) on, Yellow (activity) blinking

**Vulcan 7 FS:**
- [ ] Power supply stable (12V DC)
- [ ] NMEA 2000 connected to YDNU-02
- [ ] Touchscreen responsive
- [ ] Display brightness adequate for daylight

**RPi4:**
- [ ] Disk space >10GB free
- [ ] Temperature normal (45-50°C)
- [ ] All USB devices visible: `lsusb`

---

## SOFTWARE CHECKS (T-45 minutes)

### Docker Containers (InfluxDB & Grafana)

**CRITICAL:** InfluxDB and Grafana run in Docker, NOT systemd!

```bash
# Ensure native InfluxDB is stopped (it should be masked)
sudo systemctl status influxdb  # Should show "masked"

# Start the containers
cd /home/aneto/.openclaw/workspace
docker compose up -d influxdb grafana

# Wait for startup (~15 sec)
sleep 15

# Verify both are running
docker compose ps
```

- [ ] InfluxDB responding: `curl http://localhost:8086/health` (expect HTTP 200)
- [ ] Grafana responding: `curl http://localhost:3001/api/health` (expect HTTP 200)

**If either fails:**
- Check: `docker compose logs influxdb` or `docker compose logs grafana`
- See `TROUBLESHOOTING.md` Section 6-7

### Signal K Status

```bash
# Verify service running
systemctl status signalk  # Should say "active (running)"

# Check API
curl http://localhost:3000/signalk/v1/api/vessels/self | python3 -m json.tool | head

# List plugins
curl http://localhost:3000/skServer/plugins | python3 -m json.tool | grep -E '"id"|"running"'
```

**Expected output:**
- All 5 custom plugins listed
- All showing `"running": true`

### Data Streams Check

```bash
# Position
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/position | python3 -m json.tool

# Heading
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/headingTrue

# Attitude
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

**Expected:**
- Position: reasonable lat/lon ±2m accuracy
- Heading: stable ±0.5° (or N/A if GPS not locked yet)
- Attitude: roll/pitch near 0° at rest

### Database & Dashboard

```bash
# InfluxDB health
curl http://localhost:8086/api/v2/health

# Grafana accessible
curl http://localhost:3001/api/health
```

**Expected:** Both return HTTP 200

---

## SENSOR CALIBRATION (T-30 minutes)

### WIT IMU Calibration

**At Rest (Level, 0° Heel):**
- [ ] Position boat level (by eye)
- [ ] Record IMU data:
  ```bash
  curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .value
  ```
- [ ] Expected: `roll: ~0.0`, `pitch: ~0.0`, `accel_z: ~9.81`

**At 30° Heel (Test):**
- [ ] Heel boat deliberately to ~30° (use jib or heel stick)
- [ ] Record attitude
- [ ] Expected: `roll: ~0.52 rad` (~30°)
- [ ] **CRITICAL:** Wave Analyzer should show corrected Hs (v1.1 active)

### GPS Heading Validation

**True Heading Check:**
- [ ] Compass alignment: boat pointed north
- [ ] Heading should read ~0° (True North)
- [ ] Try 90° turn: heading should read ~90°
- [ ] Record any offset needed: `[offset value]`

---

## UNDERWAY TESTING (1-2 hours)

### Navigation System

**Distance to Waypoint:**
- [ ] Set waypoint: Block Island lighthouse (41.1720, -71.5509)
- [ ] Activate go-to-waypoint in Vulcan
- [ ] Verify distance/bearing
- [ ] Drive toward waypoint, watch distance decrease
- [ ] Status: ✅ PASS / ❌ FAIL

**Position Accuracy:**
- [ ] Record GPS position
- [ ] Mark on chart (physical reference)
- [ ] Compare with actual boat location
- [ ] Accuracy should be ±2m
- [ ] Status: ✅ PASS / ❌ FAIL

**Heading Stability:**
- [ ] Point boat steady at heading 180° (South)
- [ ] Watch Vulcan display for 1 minute
- [ ] Should hold ±0.5°
- [ ] Status: ✅ PASS / ❌ FAIL

### Performance System

**VMG Calculation:**
- [ ] Set polars wind speed: 12 knots
- [ ] Adjust sails to optimal trim
- [ ] Watch VMG in Grafana
- [ ] Should show reasonable value (50-90% of STW)
- [ ] Status: ✅ PASS / ❌ FAIL

**Wave Analyzer:**
- [ ] Run for 10+ minutes
- [ ] Should show wave height + period
- [ ] Compare with visual sea state
- [ ] Status: ✅ PASS / ❌ FAIL

### Display System

**Vulcan Dashboard:**
- [ ] All data appearing on screen
- [ ] No lag (update <1 sec)
- [ ] Touchscreen responsive
- [ ] Status: ✅ PASS / ❌ FAIL

**iPad Grafana:**
- [ ] Connect to WiFi: `MidnightRider`
- [ ] Open http://localhost:3001
- [ ] All 4 dashboards load
- [ ] Real-time data flowing
- [ ] Status: ✅ PASS / ❌ FAIL

---

## POST-TEST ACTIONS

### Document Results

```markdown
# Field Test Results — 2026-05-19

## Hardware
- GPS UM982: ✅ PASS / ❌ FAIL (notes: ___________)
- WIT IMU: ✅ PASS / ❌ FAIL (notes: ___________)
- Calypso: ✅ PASS / ❌ FAIL (notes: ___________)
- YDNU-02: ✅ PASS / ❌ FAIL (notes: ___________)
- Vulcan: ✅ PASS / ❌ FAIL (notes: ___________)
- RPi4: ✅ PASS / ❌ FAIL (notes: ___________)

## Software
- Signal K: ✅ PASS / ❌ FAIL
- Grafana: ✅ PASS / ❌ FAIL
- Data logging: ✅ PASS / ❌ FAIL

## Sensors
- Navigation: ✅ PASS / ❌ FAIL
- Performance: ✅ PASS / ❌ FAIL
- Waves: ✅ PASS / ❌ FAIL

## Issues Found
[List any problems with solutions]

## Sign-off
✅ System approved for race
OR
⚠️ Fixes needed before race (list):
```

### Backup & Cleanup

- [ ] Export test data: `mysqldump...` or InfluxDB export
- [ ] Save system state: `tar czf ~/signalk-final-backup-2026-05-19.tar.gz ~/.signalk/`
- [ ] Update ACTION-ITEMS with any fixes needed
- [ ] Update MEMORY.md with findings

---

## GO/NO-GO DECISION

**All systems PASS?** → ✅ GO for race day (May 22)

**Any FAIL?** → ⚠️ Schedule fix session before May 22

---

**Document:** Field Test Results (attach to this file or save as separate markdown)  
**Sign-off By:** Denis Lafarge  
**Date Completed:** 2026-05-19 [time]  
**Status:** ✅ APPROVED FOR RACE / ⚠️ FIXES NEEDED

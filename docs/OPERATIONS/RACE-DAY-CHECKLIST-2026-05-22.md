# RACE DAY CHECKLIST — May 22, 2026 — Block Island Race

**Race Start:** 11:00 EDT  
**Boot Time:** 10:00 EDT (T-60 minutes)  
**Location:** [Port location — TBD]  
**Objective:** Launch system, verify live, execute race

---

## T-60 MINUTES — SYSTEM BOOT (10:00 EDT)

### Power & Basics

- [ ] RPi4 powered on (12V from LiFePO4 battery)
- [ ] All USB devices visible
- [ ] SSH access working: `ssh pi@rpi4.local`
- [ ] Disk space check: `df -h` (should be >10GB free)

### Docker Containers (InfluxDB & Grafana)

**CRITICAL:** InfluxDB and Grafana run in Docker, NOT systemd!

```bash
# Ensure native InfluxDB is stopped (it should be masked)
sudo systemctl status influxdb  # Should show "masked"

# Start the containers
cd /home/aneto/.openclaw/workspace
docker compose up -d influxdb grafana

# Wait for startup (~10-15 sec)
sleep 15

# Verify both are running
docker compose ps
```

- [ ] InfluxDB responding: `curl http://localhost:8086/health` (expect HTTP 200)
- [ ] Grafana responding: `curl http://localhost:3001/api/health` (expect HTTP 200)

**If either fails:**
- Check: `docker compose logs influxdb` or `docker compose logs grafana`
- See `TROUBLESHOOTING.md` Section 6-7

### Signal K Boot

- [ ] Service starts automatically: `systemctl status signalk`
- [ ] Wait for full initialization (~30 sec)
- [ ] API responding: `curl http://localhost:3000/signalk/v1/api`

### Data Verification

**GPS UM982:**
- [ ] Heading appearing in Signal K
- [ ] Wait for GPS lock (may take 30+ sec cold start)
- [ ] Position should stabilize ±2m

**WIT IMU:**
- [ ] Attitude data flowing (30+ Hz)
- [ ] Roll/pitch ~0° at rest
- [ ] Acceleration.z ~9.81 m/s²

**Databases:**
- [ ] InfluxDB healthy: `curl http://localhost:8086/api/v2/health`
- [ ] Grafana alive: `curl http://localhost:3001/api/health`

---

## T-45 MINUTES — DISPLAYS & DASHBOARDS (10:15 EDT)

### Vulcan 7 FS MFD

- [ ] Power on (should detect YDNU-02 automatically)
- [ ] Settings → Network → Device List: YDNU-02 visible + enabled
- [ ] Position appearing (lat/lon from UM982)
- [ ] Heading appearing (from UM982)
- [ ] Attitude appearing (roll/pitch from WIT)
- [ ] Wave height: may take 5+ min to appear

### iPad Grafana

- [ ] Connect to WiFi: `MidnightRider`
- [ ] Open Grafana: http://localhost:3001
- [ ] Login (if required)
- [ ] Navigation dashboard: position + heading live
- [ ] Race dashboard: VMG, wind, heel live
- [ ] Astronomical dashboard: sunrise/sunset visible
- [ ] Alerts dashboard: no red alerts (yet)

### Crew Briefing

- [ ] Explain dashboard: what to watch during race
- [ ] Point out critical gauges: heel, wave height, VMG
- [ ] Explain alerts: heel > 22° = "consider reefing"
- [ ] Show Block Island waypoint in Vulcan

---

## T-30 MINUTES — FINAL CHECKS (10:30 EDT)

### Navigation System

- [ ] Block Island waypoint loaded in Vulcan
- [ ] Course set: start line → Block Island
- [ ] Distance/bearing visible and reasonable
- [ ] Layline calculation ready (in qtVLM or Race MCP)

### Performance System

- [ ] Polars database loaded (J/30 specifications)
- [ ] Wind speed readable (B&G WS320 or Calypso)
- [ ] VMG calculation working
- [ ] Sail trim recommendations available

### Safety

- [ ] All crew briefed
- [ ] Emergency shutdown procedure known (sudo shutdown -h now)
- [ ] iPad secured (avoid water spray)
- [ ] RPi4 power stable (no voltage fluctuations)
- [ ] YDNU-02 firmly connected (no loose USB cable)

### Data Recording

- [ ] InfluxDB actively logging (check bucket: midnight_rider)
- [ ] Data will be retained for post-race analysis
- [ ] Backup: entire race stored → can replay later

---

## T-15 MINUTES — GO/NO-GO DECISION (10:45 EDT)

**All systems operational?**

✅ YES → Proceed to start line  
❌ NO → Note issues, attempt quick fixes:

- GPS no lock? Wait additional 1-2 min
- WIT data missing? Restart Signal K: `systemctl restart signalk`
- Vulcan no data? Restart YDNU-02 USB + power cycle Vulcan
- iPad not connecting? Retry WiFi, check DHCP

**If issues cannot be resolved:**
- Can still race (navigate manually if needed)
- Collect data anyway (for post-race analysis)
- Document problems for post-race troubleshooting

---

## UNDERWAY — MONITORING (11:00 → Finish)

### What to Watch

**Every 5 minutes:**
- [ ] Heel angle (real heel from WIT v1.1 correction)
- [ ] Wave height (Hs from Wave Analyzer)
- [ ] VMG vs target VMG
- [ ] Wind direction stability

**On significant changes:**
- [ ] Wind shift >10°: recalculate optimal heading (check Polar MCP)
- [ ] Heel >22°: consider reefing (Sails Management v2 recommendation)
- [ ] Wave Hs jumps: check surface current/weather change

### iPad Update Loop

- Check Grafana every 10 min
- Monitor alerts (heel, wave, wind)
- Note any unexpected values (may indicate system issues)

### Data Integrity

- Don't power cycle RPi during race (will corrupt InfluxDB)
- If something freezes: SSH in and check logs (`journalctl -u signalk`)
- Keep iPad WiFi connected (for live monitoring)

---

## FINISH LINE → POST-RACE (Race End time + 15 min)

### Immediate

- [ ] Note finish time and position
- [ ] Stop active monitoring
- [ ] Take screenshots of final Grafana state

### Graceful Shutdown

```bash
# SSH into RPi
ssh pi@rpi4.local

# Graceful shutdown (IMPORTANT: don't hard power-off)
sudo shutdown -h now

# Wait 30 sec for complete shutdown, then power off
```

### Data Preservation

- [ ] InfluxDB contains entire race (no manual export needed)
- [ ] Log files in `/var/log/` and Signal K logs preserved
- [ ] Backup RPi config: `tar czf ~/signalk-race-backup-2026-05-22.tar.gz ~/.signalk/`

### Debrief

- [ ] Crew feedback: was system useful? Any issues?
- [ ] Note any unexpected readings
- [ ] Screenshot final stats from Grafana
- [ ] Update MEMORY.md with race results

---

## TROUBLESHOOTING — QUICK FIXES UNDERWAY

| Issue | Quick Fix |
|-------|-----------|
| Vulcan no heading | Wait 1-2 min for GPS lock |
| iPad blank Grafana | Reload browser: Cmd+R (Mac) or F5 (Windows) |
| WIT data stops | SSH: `systemctl status signalk` — if red, `systemctl restart signalk` |
| NMEA 2000 bus quiet | Check YDNU-02 USB connection, restart both devices |
| InfluxDB using too much RAM | `docker compose restart influxdb` (brief interruption, ~10 sec) |
| Touchscreen unresponsive | Hard power-off Vulcan, wait 5 sec, power back on |

**For any crash:** Re-read `TROUBLESHOOTING.md` or phone Denis

---

## FINAL NOTES

- **Don't let tech distract you from sailing.** The system is here to help, not replace crew judgment.
- **Trust your instincts.** If something feels wrong (heel too much, sea state change), reef early.
- **Enjoy the race.** This is about sailing, data is bonus.

---

**Prepared by:** AI Assistant  
**Approved by:** Denis Lafarge  
**Date:** 2026-05-22  
**Status:** ✅ READY TO RACE  

**GO MIDNIGHT RIDER!** ⛵🏁

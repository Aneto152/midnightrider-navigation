# RASPBERRY PI 4 — COMPUTER DATASHEET

**Manufacturer:** Raspberry Pi Foundation  
**Model:** Raspberry Pi 4 Model B  
**RAM:** 4GB (Midnight Rider unit)  
**Storage:** 64GB microSD  
**Date:** 2026-04-25

---

## SPECIFICATIONS

| Spec | Value |
|------|-------|
| **CPU** | ARMv8 (4-core, 1.5 GHz) |
| **RAM** | 4GB LPDDR4 |
| **Storage** | 64GB microSD (Kingston Industrial) |
| **USB Ports** | 2× USB 3.0 + 2× USB 2.0 |
| **Ethernet** | Gigabit RJ45 |
| **WiFi** | 802.11ac dual-band |
| **Bluetooth** | Bluetooth 5.0 LE |
| **GPIO** | 40-pin connector |
| **Power** | 15W typical (USB-C 5V/3A) |
| **Dimensions** | 88 × 58 × 19.5 mm |
| **Operating Temp** | 0-50°C (optimal: 25-45°C) |

---

## SOFTWARE STACK

**OS:** Raspberry Pi OS (Bullseye, 64-bit)  
**Runtime:** Node.js v24.14.1  
**Databases:** InfluxDB, Grafana  
**Signal K:** v2.25  
**Python:** 3.11 (for BLE drivers)  
**Kernel:** Linux 6.12.75+rpt-rpi-v8

---

## INSTALLED SERVICES

| Service | Purpose | Port | Status |
|---------|---------|------|--------|
| Signal K | Data hub | 3000 | ✅ Active |
| InfluxDB | Time-series DB | 8086 | ✅ Active |
| Grafana | Dashboards | 3001 | ✅ Active |
| qtVLM | Weather routing | NMEA 0183 TCP | ✅ Active |
| Bleak (Python) | WIT IMU driver | (subprocess) | ✅ Active |

---

## RACING DEPLOYMENT

### Boot Sequence
1. Power on: ~30 sec to full boot
2. Signal K starts automatically: ~10 sec
3. Plugins load: ~20 sec
4. Ready for data: ~60 sec total

### Monitoring During Race
- SSH access: `ssh pi@<ip>`
- Service status: `systemctl status signalk`
- Disk space: `df -h` (ensure >10GB free)
- Temperature: `/opt/vc/bin/vcgencmd measure_temp`
- Memory: `free -h`

### Shutdown
- Graceful: `sudo shutdown -h now`
- Or: Power off (RPi4 handles it)

---

## STORAGE MANAGEMENT

**Current Usage:**
- OS: 3GB
- Signal K + plugins: 2GB
- InfluxDB: 2-3GB
- Grafana: 500MB
- **Available:** ~50GB for InfluxDB growth

**Race Projection:**
- 5-hour race @ 1s resolution = ~18,000 data points
- ~5-10 MB for entire race
- No storage concerns

---

## POWER REQUIREMENTS

**On Boat:**
- 12V LiFePO4 100Ah battery
- USB-C power adapter (5V/3A minimum)
- Recommend separate 5V supply (isolated from main power)

**Typical draw:**
- Idle: 3-5W
- Full load (Signal K + Grafana + InfluxDB): 10-15W
- Can run 24/7 on solar top-up

---

## THERMAL MANAGEMENT

**Temperature (typical racing):**
- Idle: 45-50°C
- Full load: 55-65°C
- Throttle threshold: 80°C
- Shutdown: 85°C

**Cooling options:**
- Passive (aluminum case): sufficient for racing
- Active (fan): overkill, not needed
- Heatsinks: included with RPi4

---

## NETWORK CONNECTIVITY

**WiFi:**
- SSID: `MidnightRider` (optional, for crew iPad)
- Connect: iPad → RPi4 → Grafana (port 3001)
- Bandwidth: <1 Mbps for Grafana updates

**Ethernet:**
- Optional backup (dock only)
- Not used during racing

**USB Connections (Racing):**
- YDNU-02 (NMEA 2000 gateway)
- Calypso UP10 (optional, BLE)
- WIT IMU (optional, BLE)

---

## PRE-RACE CHECKLIST

- [ ] Free disk space: >10GB
- [ ] Temperature stable (50-60°C)
- [ ] SSH access working
- [ ] Signal K API responding (port 3000)
- [ ] Grafana accessible (port 3001)
- [ ] InfluxDB healthy (port 8086)
- [ ] All 5 plugins loaded
- [ ] Backups recent (not needed for race, but good practice)

---

## KNOWN ISSUES & FIXES

| Issue | Fix |
|-------|-----|
| Overheating | Add heatsinks or improve airflow |
| InfluxDB consuming RAM | Restart: `docker compose restart influxdb` |
| Signal K slow | Check disk space + memory (`free -h`) |
| WiFi dropping | Use Ethernet if available (backup) |
| USB device not seen | Restart: `sudo systemctl restart signalk` |

---

## RACING ADVANTAGES

✅ **Perfect size:** Fits in small boat cabinet  
✅ **Low power:** 15W typical, can run on battery all day  
✅ **Reliable:** Thousands deployed, proven stability  
✅ **Flexible:** 4GB RAM enough for all our workloads  
✅ **Active cooling:** Passive design sufficient (no fan noise)  

---

**STATUS:** ✅ Operational  
**Last Updated:** 2026-04-25  
**Critical for Race:** YES (host for all software)

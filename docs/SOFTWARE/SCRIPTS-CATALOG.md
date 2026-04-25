# SCRIPTS CATALOG — Midnight Rider Operational Scripts

**Status:** ✅ Production Ready  
**Last Updated:** 2026-04-25  
**Location:** `/scripts/` and root directory

---

## 📋 OVERVIEW

All operational scripts for Midnight Rider navigation system, organized by purpose.

---

## 🏁 RACE OPERATIONS SCRIPTS

### race-mode.sh
**Location:** `scripts/race-mode.sh` (3.5 KB)  
**Purpose:** Activate race-optimized system configuration  
**When:** Before race start (T-30)  
**What it does:**
- Maximize Signal K update frequency
- Enable high-precision GPS mode
- Activate performance calculation plugins
- Set critical alert thresholds
- Lock configuration (prevent accidental changes)

**Usage:**
```bash
./scripts/race-mode.sh
```

**Effect:** System switches to race-grade precision + alert sensitivity

---

### race-debrief.sh
**Location:** `scripts/race-debrief.sh` (4.6 KB)  
**Purpose:** Post-race data extraction & analysis setup  
**When:** After finish line  
**What it does:**
- Export InfluxDB race data to CSV
- Preserve raw logs
- Generate performance summary
- Create visualization dataset for Grafana replay

**Usage:**
```bash
./scripts/race-debrief.sh
```

**Output:** `debrief/race-2026-05-22-{time}/`

---

## 📊 DATA COLLECTION SCRIPTS

### buoy-logger.sh
**Location:** `scripts/buoy-logger.sh` (5.7 KB)  
**Purpose:** Collect NDBC buoy data for sea state forecasting  
**Frequency:** Every 30 minutes  
**What it does:**
- Fetch NOAA NDBC buoy data (nearest Block Island station)
- Extract: Hs (wave height), Tp (peak period), wind, temperature
- Store to Signal K for comparison with WIT measurements
- Log discrepancies for calibration

**Automation:** Cron job (see section below)

**Manual run:**
```bash
./scripts/buoy-logger.sh
```

---

### weather-logger.sh
**Location:** `scripts/weather-logger.sh` (5.4 KB)  
**Purpose:** Collect meteorological data for tactical planning  
**Frequency:** Every 10 minutes  
**What it does:**
- Fetch weather from wttr.in or Open-Meteo
- Extract: wind speed/direction, temp, pressure, gust
- Store to InfluxDB for historical analysis
- Alert if significant change detected

**Automation:** Cron job

**Manual run:**
```bash
./scripts/weather-logger.sh
```

---

### astronomical-data.sh
**Location:** `scripts/astronomical-data.sh` (6.6 KB)  
**Purpose:** Calculate astronomical events (sunrise, sunset, moon, tides)  
**Frequency:** Once per day (dawn)  
**What it does:**
- Compute sunrise/sunset for boat location
- Moon phase + moonrise/moonset
- Tide predictions (NOAA API or XTide local)
- Store in Signal K for dashboard annotation

**Automation:** systemd service (see section below)

**Manual run:**
```bash
./scripts/astronomical-data.sh
```

---

### init-astronomical-data.sh
**Location:** `scripts/init-astronomical-data.sh` (2.3 KB)  
**Purpose:** One-time initialization for astronomical calculations  
**When:** System first boot or after location change  
**What it does:**
- Download ephemeris data (suncalc, astronomy-engine)
- Initialize XTide harmonic constants (if using local)
- Set boat location (lat/lon)
- Verify astronomical plugins active

**Usage:**
```bash
./scripts/init-astronomical-data.sh
```

---

## 🎯 SYSTEM HEALTH SCRIPTS

### check-system.sh
**Location:** `scripts/check-system.sh` (12 KB)  
**Purpose:** Complete system diagnostics before deployment  
**Modes:**
- `--quick` (2 sec, services only)
- `--full` (10 sec, complete check)
- `--watch` (continuous monitoring)

**GO/NO-GO Decision:**
```
Exit 0 = ✅ GO FOR DEPLOYMENT
Exit 1 = ⚠️ CAUTION PROCEED
Exit 2 = ❌ NO-GO
```

**Usage:**
```bash
./scripts/check-system.sh --full    # Before race
./scripts/check-system.sh --quick   # Final check
./scripts/check-system.sh --watch   # During setup
```

See: [`docs/OPERATIONS/CHECK-SYSTEM-QUICK-REFERENCE.md`](../OPERATIONS/CHECK-SYSTEM-QUICK-REFERENCE.md)

---

### install-check-system.sh
**Location:** `scripts/install-check-system.sh` (2.5 KB)  
**Purpose:** Set up convenient aliases for check-system  
**What it does:**
- Add bash aliases: `check-quick`, `check-full`, `check-watch`
- Optional desktop shortcut (RPi GUI)

**One-time setup:**
```bash
./scripts/install-check-system.sh
source ~/.bashrc
```

**Then use:**
```bash
check-full    # Full diagnostic
check-quick   # Quick check
check-watch   # Monitor mode
```

---

## 🌐 PYTHON UTILITIES (Regatta Subsystem)

**Location:** `regatta/` directory  
**Purpose:** Weather, alerts, and live data webhooks

### weather_collector.py
**File:** `regatta/weather_collector.py` (9.1 KB)  
**Purpose:** Collect meteorological data programmatically  
**Input:** wttr.in, Open-Meteo, or local METAR  
**Output:** JSON → Signal K or webhook  
**Features:**
- Historical logging
- Anomaly detection
- Pressure trend calculation

**Usage:**
```bash
python3 regatta/weather_collector.py --location "Block Island"
```

---

### alert_notifier.py
**File:** `regatta/alert_notifier.py` (2.4 KB)  
**Purpose:** Send notifications for critical system alerts  
**Triggers:**
- Heel > 22°
- Wave height > 2.5m
- Wind gust > threshold
- Signal K plugin failure

**Methods:**
- Console output (local)
- WebSocket push (iPad dashboard)
- Optional: Telegram/SMS

**Usage:**
```bash
python3 regatta/alert_notifier.py --listen-sk
```

---

### alert_webhook.py
**File:** `regatta/alert_webhook.py` (3.7 KB)  
**Purpose:** Receive and process webhook alerts from external systems  
**Use case:** 
- IFTTT integration
- External weather services
- Mobile app push notifications

**Listens on:** `http://localhost:8765/alert`

**Usage:**
```bash
python3 regatta/alert_webhook.py
```

---

### server.py
**File:** `regatta/server.py` (12 KB)  
**Purpose:** Central regatta control server  
**Features:**
- REST API for race commands
- WebSocket for real-time updates
- Integration with Signal K
- Crew UI backend

**Usage:**
```bash
python3 regatta/server.py --port 8000
```

---

## 🔧 UTILITY SCRIPTS (Root)

### git-backup.sh
**Location:** Root directory  
**Purpose:** Automated git backup to cloud storage  
**Frequency:** Daily (cron job)  
**What it does:**
- Push all commits to GitHub
- Verify remote is up-to-date
- Log backup status

**Manual run:**
```bash
./git-backup.sh
```

---

### security-audit.sh
**Location:** Root directory  
**Purpose:** System security verification  
**Checks:**
- SSH key permissions
- Firewall rules
- File permissions on sensitive files
- Exposed credentials scanning

**Usage:**
```bash
./security-audit.sh
```

---

### Dockerfile.wit
**Location:** Root directory  
**Purpose:** Docker container for WIT IMU standalone operation  
**Status:** ✅ Available (optional, can run natively via bleak)

**Use case:** 
- Isolated BLE driver environment
- Easier debugging
- Container isolation

**Usage:**
```bash
docker build -f Dockerfile.wit -t wit-ble-reader:latest .
docker run --device /dev/bluetooth wit-ble-reader:latest
```

---

## 🔄 AUTOMATION (Systemd Services & Cron)

### Systemd Services

**astronomical-data.service**
```
[Unit]
Description=Midnight Rider Astronomical Data Collection
After=network.target signalk.service

[Service]
Type=oneshot
ExecStart=/home/aneto/scripts/astronomical-data.sh
StandardOutput=journal

[Install]
WantedBy=daily.target
```

**Status:** Check with `systemctl status astronomical-data.timer`

---

### Cron Jobs

**Every 10 minutes (weather):**
```bash
*/10 * * * * /home/aneto/scripts/weather-logger.sh >> /var/log/weather-logger.log 2>&1
```

**Every 30 minutes (buoys):**
```bash
*/30 * * * * /home/aneto/scripts/buoy-logger.sh >> /var/log/buoy-logger.log 2>&1
```

**Daily at 06:00 (astronomical):**
```bash
0 6 * * * /home/aneto/scripts/astronomical-data.sh >> /var/log/astronomical-data.log 2>&1
```

**Daily at 03:00 (backup):**
```bash
0 3 * * * /home/aneto/git-backup.sh >> /var/log/git-backup.log 2>&1
```

---

## 📋 SCRIPT INVENTORY

| Script | Size | Purpose | Auto-run | Status |
|--------|------|---------|----------|--------|
| check-system.sh | 12 KB | Diagnostics | Manual | ✅ Active |
| install-check-system.sh | 2.5 KB | Setup aliases | Manual | ✅ Active |
| race-mode.sh | 3.5 KB | Race config | Manual | ✅ Active |
| race-debrief.sh | 4.6 KB | Post-race analysis | Manual | ✅ Active |
| buoy-logger.sh | 5.7 KB | NDBC data | Cron (30m) | ✅ Active |
| weather-logger.sh | 5.4 KB | Weather data | Cron (10m) | ✅ Active |
| astronomical-data.sh | 6.6 KB | Astro events | systemd | ✅ Active |
| init-astronomical-data.sh | 2.3 KB | Astro init | Manual | ✅ Active |
| git-backup.sh | ? | Git backup | Cron (daily) | ✅ Active |
| security-audit.sh | ? | Security check | Manual | ✅ Active |
| Dockerfile.wit | ? | WIT container | Optional | ✅ Available |
| weather_collector.py | 9.1 KB | Weather API | Optional | ✅ Available |
| alert_notifier.py | 2.4 KB | Notifications | Optional | ✅ Available |
| alert_webhook.py | 3.7 KB | Webhook receiver | Optional | ✅ Available |
| server.py | 12 KB | Regatta server | Optional | ✅ Available |

---

## 🎯 PRE-RACE CHECKLIST

Before May 22 race:

```bash
# 1. Install aliases (one-time)
./scripts/install-check-system.sh

# 2. Run full diagnostics (1h before race)
check-full

# 3. Activate race mode (T-30)
./scripts/race-mode.sh

# 4. Verify weather/buoy data (T-15)
./scripts/weather-logger.sh
./scripts/buoy-logger.sh

# 5. Monitor during race (every 10 min)
check-quick
```

---

**Status:** ✅ All scripts documented and ready for Block Island Race (May 22, 2026)

---

*Last updated: 2026-04-25*  
*Next review: Post-race analysis*

# scripts/ — Midnight Rider Navigation System

> Last updated: 2026-05-29
> Maintained by: OC (OpenClaw) + Denis Lafarge
> Runtime: Bash + Python 3.9+

---

## ⚠️ CRITICAL GAPS

Several daemon scripts lack systemd service files. They must be started manually or via cron.

| Script | Type | Status |
|--------|------|--------|
| noaa_collector.py | Daemon | ⚠️ **No systemd service** |
| lis_wind_collector.py | Daemon | ⚠️ **No systemd service** |
| weather-logger.sh | Daemon | ⚠️ **No systemd service** |
| current_vector_calc.py | Daemon | ⚠️ **No systemd service** |
| wave-analyzer.py | Daemon | ⚠️ **No systemd service** |
| monitor_resources.py | Daemon | ✅ `etc/systemd/system/monitor-resources.service` |

**Recommended action:** Create systemd services for all daemon scripts before next race.

---

## 📋 SYSTEM & DIAGNOSTICS

### check-system.sh
**Pre-departure system diagnostic (GO/NO-GO decision)**

```bash
./check-system.sh --quick    # Core services (30s)
./check-system.sh --full     # Complete sensor + data (3m)
./check-system.sh --watch    # Continuous (10s refresh)
```

- **Checks**: Signal K, InfluxDB, Grafana, GPS, WIT IMU, YDNU-02, Calypso anemometer
- **Output**: Structured report with ✅ PASS / ⚠️ WARNING / ❌ FAIL
- **Exit codes**: 0=GO, 1=CAUTION, 2=NO-GO
- **systemd**: ❌ Manual only (run before departure)
- **Dependencies**: curl, jq

---

### monitor_resources.py
**System resource monitoring → InfluxDB**

```bash
python3 scripts/monitor_resources.py              # Single report
python3 scripts/monitor_resources.py --daemon     # Background loop
python3 scripts/monitor_resources.py --debug      # Verbose logging
```

- **Metrics**: CPU%, RAM%, disk%, temperature, load average, top 5 processes
- **Interval**: Every 60 seconds (configurable)
- **Output**: `/tmp/rpi_resources.json` + `/tmp/rpi_resources.log`
- **InfluxDB**: `midnight_rider` bucket → `system.resources` measurement
- **systemd**: ✅ `etc/systemd/system/monitor-resources.service`
- **Thresholds**: CPU 80%, RAM 85%, disk 90%, temp 75°C

---

### security-audit.sh
**Quick security audit (tokens, permissions, ports)**

```bash
bash scripts/security-audit.sh
```

- **Checks**: Exposed secrets, open ports, file permissions, SSH keys
- **Output**: ⚠️ Warnings only (no automated fixes)
- **systemd**: ❌ Manual only

---

## 🔐 TOKEN & CONFIGURATION

### rotate-token.sh
**InfluxDB token rotation with automatic service restart**

```bash
bash scripts/rotate-token.sh
```

- **Action**: Generates new token, updates .env, restarts services
- **Backup**: Saves old token to logs/
- **systemd**: ❌ Manual only (run after token expiry alerts)
- **Requirements**: InfluxDB admin access

---

## 📊 DATA COLLECTION DAEMONS

### noaa_collector.py
**NOAA/NWS weather data collection → InfluxDB**

```bash
python3 scripts/noaa_collector.py
```

- **Source**: NOAA/NWS API (LIS buoy data, wind, sea state)
- **Interval**: Every 15 minutes
- **Output**: `InfluxDB` → `weather` measurement
- **systemd**: ⚠️ **Missing** — start manually or create service
- **Dependencies**: requests, python-dotenv

---

### lis_wind_collector.py
**LIS (Long Island Sound) buoy wind data → InfluxDB**

```bash
python3 scripts/lis_wind_collector.py
```

- **Source**: NOAA buoy 44065 (LIS wind, temperature, pressure)
- **Interval**: Every 10 minutes
- **Output**: `InfluxDB` → `lis.wind` measurement
- **systemd**: ⚠️ **Missing** — start manually
- **Dependencies**: requests, python-dotenv

---

### weather-logger.sh
**Hourly weather archive → logs/**

```bash
bash scripts/weather-logger.sh
```

- **Source**: Open-Meteo / wttr.in
- **Output**: `logs/weather-YYYY-MM-DD.log`
- **Frequency**: Hourly (via cron)
- **systemd**: ⚠️ **Missing** — use cron entry instead
- **Example cron**: `0 * * * * /home/pi/midnightrider-navigation/scripts/weather-logger.sh`

---

## 🧮 CALCULATION & PROCESSING

### current_vector_calc.py
**Ocean current vector estimation → InfluxDB**

```bash
python3 scripts/current_vector_calc.py
```

- **Inputs**: SOG, COG, AWA, AWS, boat attitude (from Signal K)
- **Output**: Current velocity (m/s), current direction (deg)
- **Algorithm**: Drift analysis + set/drift calculation
- **Interval**: Real-time (1 Hz from Signal K)
- **systemd**: ⚠️ **Missing** — needs systemd service
- **Dependencies**: signalk-client (Python library)

---

### target_speed_calc.py
**Target speed optimization (polars + weather)**

```bash
python3 scripts/target_speed_calc.py
```

- **Inputs**: True wind, boat polars, current
- **Output**: Optimal target speed (knots)
- **Model**: Lookup + interpolation from J30 ORC polars
- **Update**: Every 10 seconds
- **InfluxDB**: `navigation.target_speed`
- **systemd**: ⚠️ **Missing**
- **Dependencies**: json, requests

---

### wave-analyzer.py
**Wave analysis from IMU heave data**

```bash
python3 scripts/wave-analyzer.py [--freq 1] [--window 60]
```

- **Input**: WIT IMU acceleration (3-axis)
- **Output**: Significant wave height, peak period, energy spectrum
- **Algorithm**: FFT analysis on heave component
- **Interval**: Every 60 seconds
- **InfluxDB**: `environment.waves`
- **systemd**: ⚠️ **Missing** — needs service
- **Dependencies**: scipy, numpy

---

## 🎯 RACE OPERATIONS

### race-mode.sh
**Toggle between RACE mode (local-only) and DEBRIEF mode (cloud)**

```bash
./race-mode.sh on       # Disable cloud writes (low latency)
./race-mode.sh off      # Enable cloud writes (debrief)
./race-mode.sh status   # Show current mode
```

- **RACE MODE**: Local InfluxDB only (no internet dependency)
- **DEBRIEF MODE**: Hybrid (local + cloud backup)
- **Config**: Updates `.env` RACE_MODE flag
- **Services affected**: Signal K data pipeline
- **systemd**: ❌ Manual only

---

### post-race-cloud-sync.sh
**Upload race day data to cloud InfluxDB**

```bash
bash scripts/post-race-cloud-sync.sh 2026-05-22
```

- **Action**: Exports race data from local InfluxDB → cloud backup
- **Time range**: Full day (00:00-23:59 UTC)
- **Format**: InfluxDB line protocol
- **Logging**: `logs/cloud-sync-YYYY-MM-DD.log`
- **systemd**: ❌ Manual only (run after race)
- **Requirements**: Cloud InfluxDB token in `.env`

---

## 🔄 DEPLOYMENT & MAINTENANCE

### install-midnight-rider.sh
**Full system installation (new RPi or recovery)**

```bash
sudo bash scripts/install-midnight-rider.sh
```

- **Duration**: ~30 minutes
- **Installs**: Docker, Node.js, Signal K, Python deps, systemd services
- **Idempotent**: Safe to run multiple times
- **Backup**: Creates snapshot before changes
- **systemd**: ❌ One-time setup script

---

## 📝 LOGGING & REPORTING

### midnight-reporter.sh
**Session report generation (wind, course, competitors)**

```bash
bash scripts/midnight-reporter.sh [--full] [--compact]
```

- **Output**: Markdown report to stdout or file
- **Content**: Summary of today's race data
- **Usage**: Share via WhatsApp / Telegram
- **Dependencies**: jq, curl

---

## 🗺️ NAVIGATION

### import-grafana-dashboards.sh
**Bulk import dashboard JSONs → Grafana**

```bash
bash scripts/import-grafana-dashboards.sh
```

- **Source**: `grafana-dashboards/*.json`
- **Destination**: Grafana (via API)
- **Auth**: Uses GRAFANA_TOKEN from `.env`
- **systemd**: ❌ Manual only (one-time setup)

---

## 🚀 HOW TO ADD A NEW DAEMON SCRIPT

1. **Create Python/Bash script** in `scripts/`
2. **Add inline header documentation** (usage, inputs, outputs)
3. **Create systemd service file** in `etc/systemd/system/`
4. **Update this README.md**
5. **Test locally**:
   ```bash
   python3 scripts/your-script.py
   sudo systemctl start your-service
   sudo systemctl status your-service
   ```
6. **Commit and push**

---

## 🔗 RELATED DOCUMENTATION

- **System architecture**: docs/ARCHITECTURE-REFERENCE-2026-05-20.md
- **Hardware datasheets**: docs/HARDWARE/
- **Integration guides**: docs/INTEGRATION/
- **Grafana dashboards**: grafana-dashboards/
- **Data schema**: docs/DATA-SCHEMA-MASTER.md

---

**Status**: Production (post-cleanup 2026-05-29)
**Next review**: Post-race debrief (2026-05-22+)

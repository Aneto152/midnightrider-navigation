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

### git-backup.sh
**Git repository backup utility**

```bash
bash scripts/git-backup.sh
```

- **Action**: Creates local git backup archive
- **Output**: `logs/git-backup-YYYY-MM-DD.tar.gz`
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

## 🌊 DATA COLLECTION DAEMONS

> ⚠️ None of these have systemd service files. Start manually or via cron.

### noaa_collector.py
**NOAA/NWS weather data collection → Signal K injection**

Fetches NOAA NDBC buoy data and injects it into Signal K via WebSocket delta.
Keeps Signal K paths alive between NOAA updates (re-injects cached values every 2 min).

```bash
python3 scripts/noaa_collector.py              # Daemon mode (default)
python3 scripts/noaa_collector.py --once       # Single fetch+inject cycle
python3 scripts/noaa_collector.py --debug      # Verbose logging
```

- **Source**: NOAA NDBC (ndbc.noaa.gov/data/realtime2/)
- **Stations**: 44017 (Montauk), 44025 (Central LIS), BLTM3 (Block Island)
- **Data**: Wind speed/direction, pressure, air temp, water temp
- **Destination**: Signal K WebSocket → signalk-to-influxdb2 → InfluxDB
- **Fetch interval**: Every 30 minutes (NOAA update rate)
- **Inject interval**: Every 2 minutes (keeps SK paths alive)
- **systemd**: ❌ None — start manually

---

### lis_wind_collector.py
**LIS (Long Island Sound) buoy wind data collection**

Fetches wind data from 9 LIS area stations (ASOS + NOAA + NDBC) → InfluxDB.
Provides wind context for the entire Long Island Sound for race analysis.

```bash
python3 scripts/lis_wind_collector.py
```

- **Source**: 3 APIs — ASOS (api.weather.gov), NOAA tides, NDBC buoys
- **Stations (9)**: Bridgeport CT, New Haven CT, New London CT, Oxford CT, Providence RI, Newport RI, Pt Judith RI, Montauk NY, Long Island
- **Data**: Wind speed (knots), direction (°), gusts (knots)
- **Destination**: InfluxDB midnight_rider → measurement lis_wind
- **Interval**: Every 15 minutes
- **Grafana**: Dashboard 10 (LIS Wind)
- **systemd**: ❌ None — start manually

---

### weather-logger.sh
**Weather forecast logging → InfluxDB**

Fetches weather forecast from Open-Meteo (free, no API key) → InfluxDB.

```bash
bash scripts/weather-logger.sh                  # Single fetch
bash scripts/weather-logger.sh --daemon         # Daemon (5 min intervals)
```

- **Source**: Open-Meteo API (api.open-meteo.com)
- **Data**: Temperature, humidity, pressure, wind (current + forecast 3 days)
- **Destination**: InfluxDB midnight_rider → measurement weather.*
- **Interval**: Every 5 minutes (daemon mode)
- **systemd**: ❌ None — start manually or add to cron

---

## ⚙️ CALCULATION ENGINES

### current_vector_calc.py
**Real-time tidal current calculation from vector drift**

Real-time tidal current calculation from SOG/COG vs STW/HDG vectors.

```bash
python3 scripts/current_vector_calc.py
```

- **Formula**: Current = SOG_vector − STW_vector → drift (m/s) + set (°)
- **Inputs from Signal K**: SOG, COG, STW, HDG
- **Outputs**: environment.current.drift + environment.current.setTrue
- **Destinations**: Signal K delta + InfluxDB environment.current
- **Interval**: Every 5 seconds
- **Requires**: Active SOG + STW from instruments
- **systemd**: ❌ None — start manually when needed

---

### target_speed_calc.py
**Target Speed Calculator**

Target speed calculation based on polar diagrams and current wind.

```bash
python3 scripts/target_speed_calc.py
```

- **Inputs**: Current TWS/TWA from Signal K, polars from data/polars/j30_orc.json
- **Output**: Target VMG, target boat speed
- **InfluxDB**: navigation.target_speed
- **systemd**: ❌ None — start manually when needed

---

### wave-analyzer.py
**Wave Analysis Engine**

Wave height and motion analysis from WIT IMU accelerometer data.

```bash
python3 scripts/wave-analyzer.py
```

- **Input**: WIT WT901BLECL IMU via Signal K (roll/pitch/heave)
- **Output**: Wave height, period, motion analysis → InfluxDB
- **InfluxDB**: environment.waves
- **systemd**: ❌ None — requires active WIT BLE connection

---

## 🏁 RACE OPERATIONS

### race-mode.sh
**Race Mode Toggle (local vs cloud)**

Toggle between RACE mode (local-only) and DEBRIEF mode (cloud-ready).

```bash
./scripts/race-mode.sh on       # Race mode: local InfluxDB only
./scripts/race-mode.sh off      # Debrief mode: cloud ready
./scripts/race-mode.sh status   # Current mode + service status
```

- **Race mode**: Disables cloud writes, optimizes for offline racing
- **Debrief mode**: Enables cloud uploads for post-race analysis
- **Config**: Updates `.env` RACE_MODE flag
- **Services affected**: Signal K data pipeline
- **systemd**: ❌ Manual only

---

### race-debrief.sh
**Post-race Workflow**

Export data, generate report, sync to cloud.

```bash
bash scripts/race-debrief.sh
```

- **Actions**: Export race data, generate summary report, upload to cloud
- **Requirements**: WiFi/internet for cloud upload
- **systemd**: ❌ Manual — run after docking

---

### midnight-reporter.sh
**WhatsApp Race Reporter**

WhatsApp race reporter via Twilio (sends race updates to crew/shore).

```bash
bash scripts/midnight-reporter.sh
```

- **Requires**: TWILIO_* credentials in .env
- **Template**: oc/MIDNIGHT-REPORTER-PROMPT.md
- **systemd**: ❌ Event-driven — call manually or from regatta server

---

## 💾 BACKUP & MAINTENANCE

### influxdb-gdrive-backup.sh
**InfluxDB Cloud Backup**

Backup InfluxDB data to Google Drive via rclone.

```bash
bash scripts/influxdb-gdrive-backup.sh
```

- **Requires**: rclone configured with Google Drive remote
- **systemd**: ❌ Manual or cron (recommended: weekly)

---

### post-race-cloud-sync.sh
**Post-race Cloud Sync**

Post-race sync: local InfluxDB → InfluxDB Cloud → Grafana export.

```bash
bash scripts/post-race-cloud-sync.sh
```

- **Requires**: INFLUX_CLOUD_* credentials in .env
- **Action**: Exports race data from local InfluxDB → cloud backup
- **Time range**: Full day (00:00-23:59 UTC)
- **Format**: InfluxDB line protocol
- **Logging**: `logs/cloud-sync-YYYY-MM-DD.log`
- **systemd**: ❌ Manual — run after race, with WiFi

---

## 🔧 UTILITIES

### json_utils.py
**JSON Utility Library**

JSON utility library used by deployment and analysis scripts.

```bash
python3 scripts/json_utils.py validate <file.json>
python3 scripts/json_utils.py format <file.json>
```

- **Note**: Used internally by other scripts

---

## ⚡ QUICK REFERENCE — Common Operations

```bash
# Before departure
bash scripts/check-system.sh --full

# Start data collection (run in background with &)
python3 scripts/noaa_collector.py &
python3 scripts/lis_wind_collector.py &
python3 scripts/current_vector_calc.py &

# Race day
bash scripts/race-mode.sh on

# Post-race
bash scripts/race-mode.sh off
bash scripts/race-debrief.sh
```

---

## 🗑️ REMOVED SCRIPTS (historical reference)

| Script | Reason | Replacement |
|--------|--------|-------------|
| buoy-logger.sh | Duplicate of lis_wind_collector.py | lis_wind_collector.py |
| test-all-mcp.sh | Duplicate of mcp/test-servers.sh | mcp/test-servers.sh |
| apply-flux-conversions.py | One-shot task completed | N/A |
| deploy_grafana_alerts.py | Replaced by grafana-provisioning/ | grafana-provisioning/alerting/ |
| import-alerts-grafana.py | Replaced by grafana-provisioning/ | grafana-provisioning/alerting/ |
| import-grafana-dashboards.sh | Replaced by grafana-provisioning/ | grafana-provisioning/dashboards/ |
| generate-status-dashboard.py | One-shot task completed | N/A |
| fix-units-grafana.py | One-shot task completed | N/A |

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
**Last audit**: 2026-05-29 — All scripts documented, 2 duplicates removed, race-mode.sh fixed

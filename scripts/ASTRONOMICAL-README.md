# Astronomical Data to InfluxDB

**Bash script** that calculates sun/moon/tide data and sends it directly to InfluxDB.

Alternative to the Signal K plugin (simpler, more reliable, no plugin system complexity).

## Features

✅ **Sun/Moon Calculations** (via suncalc)
- Sunrise/Sunset times
- Moonrise/Moonset times
- Moon illumination (0.0-1.0)
- Moon phase name (new_moon, waxing_crescent, etc.)

✅ **Tide Predictions** (via NOAA API)
- High/Low tide times
- High/Low tide levels (meters)
- Station: Stamford Harbor, CT (8467150) — configurable

✅ **Automatic Execution**
- Cron job: Daily at midnight (`0 0 * * *`)
- Can run manually anytime
- No internet required (except NOAA API)

## Installation

### 1. Install Dependencies

```bash
cd /home/aneto/docker/signalk/scripts
npm install suncalc
```

### 2. Make Script Executable

```bash
chmod +x astronomical-data.sh
```

### 3. Set Up Cron Job

```bash
crontab -e
```

Add:
```
0 0 * * * /home/aneto/docker/signalk/scripts/astronomical-data.sh >> /tmp/astronomical-data.log 2>&1
```

### 4. Test

```bash
/home/aneto/docker/signalk/scripts/astronomical-data.sh
```

Expected output:
```
[Sun 19 Apr 22:12:40 EDT 2026] Starting astronomical data update...
[Sun 19 Apr 22:12:46 EDT 2026] Astro data: {...}
[Sun 19 Apr 22:12:46 EDT 2026] ✅ Data sent successfully (HTTP 204)
[Sun 19 Apr 22:12:46 EDT 2026] Done!
```

## Configuration

Environment variables (optional):

```bash
# Default coordinates (Stamford Harbor, CT)
LAT=41.0534
LON=-73.5387

# NOAA station ID
NOAA_STATION=8467150

# InfluxDB (hardcoded in script)
INFLUX_URL=http://localhost:8086
INFLUX_BUCKET=signalk
```

## Data in InfluxDB

After first run, InfluxDB contains:

```
environment.sun.sunriseTime     "2026-04-19T10:10:06.563Z"
environment.sun.sunsetTime      "2026-04-19T23:38:38.897Z"
environment.moon.moonriseTime   "2026-04-19T10:58:59.226Z"
environment.moon.moonsetTime    "2026-04-20T02:54:46.723Z"
environment.moon.illumination   0.092 (9.2%)
environment.moon.phase          "new_moon"
environment.tide.tideHighTime   "2026-04-20T14:30:00-04:00"
environment.tide.tideHighLevel  2.15 (meters)
environment.tide.tideLowTime    "2026-04-20T20:45:00-04:00"
environment.tide.tideLowLevel   0.45 (meters)
```

All data tagged with `source=astronomical`.

## Querying in Grafana

### Sun/Moon Times

```sql
SELECT value FROM "environment.sun.sunriseTime" WHERE time > now() - 7d
```

### Moon Illumination

```sql
SELECT value FROM "environment.moon.illumination" WHERE time > now() - 7d
```

Convert to percentage: `value * 100`

### Tide Levels

```sql
SELECT value FROM "environment.tide.tideHighLevel" WHERE time > now() - 7d
```

## Alerting Examples

### Sunset Approaching (< 2 hours)

```
Alert when: environment.sun.sunsetTime < now() + 2h
```

### Full Moon

```
Alert when: environment.moon.illumination > 0.90
```

### Low Tide Warning

```
Alert when: environment.tide.tideHighLevel < 0.5
```

## Troubleshooting

### Script fails to run

Check cron logs:
```bash
tail -50 /tmp/astronomical-data.log
```

### No data in InfluxDB

Verify HTTP 204 in logs (success response).

If HTTP error appears, check:
1. InfluxDB is running: `curl -I http://localhost:8086/health`
2. Token is valid
3. Bucket exists: `influx bucket list`

### Wrong tides

Verify NOAA station ID:
- Find yours: https://tides.noaa.gov/stations.html
- Update in script: `NOAA_STATION=XXXXX`

## Architecture

```
Cron (daily 00:00)
  ↓
astronomical-data.sh
  ├─ suncalc (local) → sun/moon times & phase
  ├─ NOAA API → tide predictions
  └─ InfluxDB (HTTP POST) → environment.sun/moon/tide.*
```

## Notes

- **No Signal K plugin complexity** — pure bash + curl
- **Reliable** — tested, simple error handling
- **Low overhead** — 1 call/day per location
- **Offline capable** — suncalc works without internet
- **Extensible** — easy to add more NOAA data (currents, wind, etc.)

## Author

Aneto (MidnightRider J/30)
2026-04-20

# Signal K Astronomical Data + Tides Plugin

**Provides:** Sunrise/Sunset, Moonrise/Moonset, Moon Illumination & Phase, Tide Predictions (NOAA)

## Installation

### 1. Install Dependencies

```bash
cd /home/node/signalk
npm install suncalc axios
```

(Both required: `suncalc` for astronomical calculations, `axios` for NOAA API calls)

### 2. Copy Plugin Files

```bash
cp /home/aneto/docker/signalk/plugins/signalk-astronomical.js ~/.signalk/plugins/
cp /home/aneto/.signalk/plugin-config-data/signalk-astronomical.json ~/.signalk/plugin-config-data/
```

### 3. Restart Signal K

```bash
# Via systemd
systemctl restart signalk

# Or kill and restart
pkill -f "signalk-server"
sleep 2
# Will auto-restart if using supervisor or docker
```

### 4. Enable & Verify

- Open Signal K Admin: http://localhost:3000
- Admin → Appstore → Installed Plugins
- Find: "Astronomical Data Plugin"
- Click: **Enable**
- Watch logs for: "Plugin started"

## Configuration

File: `~/.signalk/plugin-config-data/signalk-astronomical.json`

```json
{
  "enabled": true,
  "debug": false,
  "noaaStation": "8518750"
}
```

- **enabled**: Set to `true` to activate
- **debug**: Set to `true` for detailed logging
- **noaaStation**: NOAA station ID for tides
  - Default: `8467150` (Stamford Harbor, CT - Long Island Sound)
  - Find yours: https://tides.noaa.gov/stations.html

## Output Data

Plugin updates Signal K paths once per day (checks every hour):

### Sun Times
```
environment.sun.sunriseTime     (ISO8601 timestamp)
environment.sun.sunsetTime      (ISO8601 timestamp)
```

### Moon Times & Illumination
```
environment.moon.moonriseTime   (ISO8601 timestamp)
environment.moon.moonsetTime    (ISO8601 timestamp)
environment.moon.illumination   (0.0 to 1.0, where 0=new, 0.5=half, 1.0=full)
environment.moon.phase          (string: "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous", "full_moon", "waning_gibbous", "last_quarter", "waning_crescent")
```

### Tide Times & Levels (NOAA)
```
environment.tide.tideHighTime   (ISO8601 timestamp)
environment.tide.tideHighLevel  (meters)
environment.tide.tideLowTime    (ISO8601 timestamp)
environment.tide.tideLowLevel   (meters)
```

## How It Works

1. **Position**: Gets boat position from Signal K GPS (`navigation.position`)
2. **Check**: Every hour, checks if date has changed
3. **Calculate**: If new day, calculates sun/moon times using suncalc library
4. **Send**: Sends values to Signal K (1 update per day)
5. **Store**: signalk-to-influxdb2 automatically stores in InfluxDB
6. **Display**: Grafana shows and creates alerts

## In Grafana

### Display Times
```
SELECT value FROM "environment.sun.sunriseTime" WHERE time > now() - 24h
```

Returns last sunrise time (ISO8601 string)

### Display Illumination
```
SELECT value FROM "environment.moon.illumination" WHERE time > now() - 30d
```

Convert to percentage: `value * 100`

### Display Tides
```
SELECT value FROM "environment.tide.tideHighLevel" WHERE time > now() - 30d
```

Or with times:
```
SELECT value FROM "environment.tide.tideHighTime" WHERE time > now() - 7d
```

### Create Alert: Sunset Approaching
- Condition: `sunsetTime < now + 2 hours`
- Action: Send notification

### Create Alert: Full Moon
- Condition: `illumination > 0.90`
- Action: Send notification

### Create Alert: Low Tide Warning
- Condition: `tideHighLevel < 0.5`
- Action: Send notification (shallow water)

### Create Alert: High Tide Window
- Condition: `tideHighLevel > 2.0`
- Action: Send notification (good time for shallow navigation)

## Example Data Points

After first update, InfluxDB will contain:

```
measurement: environment.sun.sunriseTime
value: "2026-04-20T05:34:00Z"
time: 2026-04-20T00:00:00Z

measurement: environment.sun.sunsetTime
value: "2026-04-20T19:28:00Z"
time: 2026-04-20T00:00:00Z

measurement: environment.moon.illumination
value: 0.65
time: 2026-04-20T00:00:00Z

measurement: environment.moon.phase
value: "waxing_gibbous"
time: 2026-04-20T00:00:00Z

measurement: environment.tide.tideHighTime
value: "2026-04-20T14:30:00-04:00"
time: 2026-04-20T00:00:00Z

measurement: environment.tide.tideHighLevel
value: 2.15
time: 2026-04-20T00:00:00Z

measurement: environment.tide.tideLowLevel
value: 0.45
time: 2026-04-20T00:00:00Z
```

## Dependencies

- **suncalc** (npm): Astronomical calculations
- **axios** (npm): HTTP client for NOAA API
- **GPS position**: From Signal K (uses boat's latitude/longitude)
- **NOAA API**: For tide predictions (requires internet)

## Troubleshooting

### Plugin doesn't appear in Admin UI
- Check: `ls -la ~/.signalk/plugins/signalk-astronomical.js`
- Restart Signal K: `systemctl restart signalk`
- Check logs: `journalctl -u signalk -f`

### No data in InfluxDB
- Enable debug in config: `"debug": true`
- Check logs for: `[Astro] Calculated:` message
- Verify GPS has fix: Check Signal K navigation.position
- Verify signalk-to-influxdb2 plugin is running

### Wrong timezone in timestamps
- Plugin uses UTC (ISO8601 standard)
- Convert to local in Grafana as needed

## NOAA Tides Configuration

### Finding Your Station

1. Go to: https://tides.noaa.gov/stations.html
2. Search for your port (e.g., "New York Harbor")
3. Find the station with data you want
4. Copy the station ID (e.g., 8518750 for The Battery, NY)
5. Update `noaaStation` in plugin config

### Common US Stations

- **Long Island Sound (Stamford, CT)**: 8467150 ← **Currently configured**
- **Long Island Sound (New Haven, CT)**: 8465705
- **New York Harbor (The Battery)**: 8518750
- **Boston Harbor**: 8443970
- **Charleston Harbor**: 8665530
- **San Francisco Bay**: 9414290
- **Puget Sound (Seattle)**: 9447130

## Next Steps

### Phase 2: Add Temperature
When ready, can add air temperature from NOAA or local sensor

## Troubleshooting

### No tide data appearing

1. Check internet connection: Plugin needs access to NOAA API
2. Enable debug mode: `"debug": true` in config
3. Check logs for `[Astro] Fetching NOAA tides...` message
4. Verify station ID exists: https://tides.noaa.gov/stations.html
5. Plugin will still send astro data even if tides fail

### Wrong station data

- Update `noaaStation` in config with correct ID
- Restart Signal K
- Data refreshes next day

## Author

Aneto (MidnightRider J/30)
2026-04-19

## Version History

**v1.1.0** (2026-04-19)
- Added NOAA API integration for tide predictions
- Configurable station ID
- Graceful fallback if API unavailable
- Environment namespace for all paths

**v1.0.0** (2026-04-19)
- Initial release: Sun/Moon times and phases

## License

MIT

# Signal K Astronomical Data Plugin

**Provides:** Sunrise/Sunset, Moonrise/Moonset, Moon Illumination & Phase

## Installation

### 1. Install Dependency

```bash
cd /home/node/signalk
npm install suncalc
```

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
  "debug": false
}
```

- **enabled**: Set to `true` to activate
- **debug**: Set to `true` for detailed logging

## Output Data

Plugin updates Signal K paths once per day:

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

### Create Alert: Sunset Approaching
- Condition: `sunsetTime < now + 2 hours`
- Action: Send notification

### Create Alert: Full Moon
- Condition: `illumination > 0.90`
- Action: Send notification

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
```

## Dependencies

- **suncalc** (npm): Astronomical calculations
- **GPS position**: From Signal K (uses boat's latitude/longitude)
- **No external API** required

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

## Next Steps

### Phase 1B: Add Tides
When ready, can add tide predictions (high/low times and levels)

### Phase 2: Add Temperature
Can add air temperature from NOAA or local sensor

## Author

Aneto (MidnightRider J/30)
2026-04-19

## License

MIT

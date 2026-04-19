# Installation Guide: UM982 Proprietary Parser

## Quick Start

### Step 1: Copy Plugin Files

```bash
# Copy to Signal K plugins directory
cp signalk-um982-proprietary.js /home/aneto/.signalk/plugins/um982-proprietary/
cp package.json /home/aneto/.signalk/plugins/um982-proprietary/
```

### Step 2: Restart Signal K

If running in Docker:
```bash
cd /home/aneto/docker/signalk
docker-compose restart signalk
```

Or if systemd:
```bash
systemctl restart signalk-server
```

### Step 3: Enable in Web UI

1. Open http://localhost:3000 (or your Signal K URL)
2. Login with your credentials
3. Go to **Admin** → **Appstore** → **Installed Plugins**
4. Find **"UM982 Proprietary Sentence Parser"**
5. Toggle **Enabled**
6. (Optional) Enable **Debug** for logging

### Step 4: Verify It Works

Check that data is flowing:

```bash
# Monitor Signal K logs
docker logs -f signalk

# Look for messages like:
# "UM982 Proprietary Parser started"
# "Sending delta: {path: 'navigation.attitude.roll', value: 0.213}"
```

## Verification Checklist

- [ ] Plugin files copied to `~/.signalk/plugins/um982-proprietary/`
- [ ] Signal K restarted
- [ ] Plugin appears in Admin → Installed Plugins
- [ ] Plugin is **Enabled**
- [ ] UM982 is connected to `/dev/ttyUSB0`
- [ ] Sentences flow: `cat /dev/ttyUSB0 | grep HEADINGA` shows data
- [ ] Signal K logs show "Parser started"
- [ ] Grafana shows new fields: `navigation.attitude.roll`, etc.

## Testing the Parser

### 1. Manual Serial Check

```bash
# Watch raw UM982 sentences
picocom /dev/ttyUSB0 -b 115200

# Should see lines like:
# $GNHDT,228.1427,T*13
# #HEADINGA,COM1,13495,95.0,FINE,...
```

### 2. Signal K Query API

```bash
# Query current attitude values
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude

# Should return something like:
# {
#   "roll": 0.213,
#   "pitch": 4.537,
#   "yaw": -0.613
# }
```

### 3. InfluxDB Check

```bash
# Query InfluxDB for attitude fields
influx query 'from(bucket:"signalk") |> range(start: -1h) |> filter(fn: (r) => r._field =~ /roll|pitch|yaw/)'

# Should return rows with values
```

### 4. Grafana Dashboard

Create a simple dashboard:
1. Go to **+ Create** → **Dashboard**
2. Add **Graph** panel
3. Query: `SELECT value FROM "navigation.attitude.roll"`
4. Should show a line chart with live data

## Troubleshooting

### Plugin doesn't appear in Installed Plugins

**Symptoms:** Plugin is copied but doesn't show in web UI

**Solution:**
1. Check file permissions:
   ```bash
   ls -la ~/.signalk/plugins/um982-proprietary/
   ```
   Should be readable by Signal K process (usually `signalk:signalk`)

2. Check Signal K logs for errors:
   ```bash
   docker logs signalk 2>&1 | grep -i error
   ```

3. Restart with verbose logging:
   ```bash
   docker-compose logs -f signalk
   ```

### Parser runs but no data

**Symptoms:** Plugin enabled but `navigation.attitude.*` remains empty

**Solution:**
1. Verify UM982 is sending sentences:
   ```bash
   timeout 5 cat /dev/ttyUSB0 | tee /tmp/serial.log | grep HEADINGA
   cat /tmp/serial.log
   ```

2. Enable debug mode in plugin config and watch logs:
   ```bash
   docker logs -f signalk | grep "HEADINGA\|debug"
   ```

3. Check that NMEA0183 provider is reading from `/dev/ttyUSB0`:
   ```bash
   cat /home/aneto/docker/signalk/config/signalk-settings.json | grep -A5 '"um982-gps"'
   ```

### Values seem incorrect

**Symptoms:** Roll/pitch/yaw values don't match expectations

**Solution:**
1. **Pitch > 180°**: Unicore uses 0-360° convention
   - Normal for GNSS-based attitude
   - Convert in Grafana: `value > 3.14159 ? value - 6.28318 : value`

2. **Yaw doesn't match heading**: Verify antenna alignment
   - Check UM982 orientation (antennes transversales?)
   - Compare with $GNHDT sentence value
   - May need heading offset configuration

3. **All zeros**: Solution status might be INSUFFICIENT_OBS
   - Plugin ignores invalid solutions
   - Check GPS signal quality and satellite count

## Configuration File

If you need to customize the plugin, edit via Signal K Admin UI:

**Path:** Admin → Plugin Config → um982-proprietary

```json
{
  "enabled": true,
  "debug": false
}
```

To enable detailed logging:
```json
{
  "enabled": true,
  "debug": true
}
```

Then restart Signal K and monitor:
```bash
docker logs -f signalk | grep "um982"
```

## Next Steps

Once the plugin is working:

1. **Create Grafana Dashboard**
   - Add panels for roll/pitch/yaw
   - Convert radians to degrees in queries
   - Set appropriate scales and thresholds

2. **Create Alerts**
   - Alert on excessive heel (roll > 0.5 rad ≈ 30°)
   - Alert on unusual pitch
   - Alert on solution degradation

3. **Integrate with PERF Alerts**
   - Use roll for sail trim feedback
   - Use pitch for weight distribution alerts

## Support

For issues or questions:
1. Check this document first
2. Review Signal K server logs: `docker logs signalk`
3. Enable debug mode in plugin config
4. Check UM982 manual for sentence format
5. Open issue in repository

---

**Last updated:** 2026-04-19  
**Plugin version:** 1.0.0  
**For:** Signal K Server >= 1.34.0

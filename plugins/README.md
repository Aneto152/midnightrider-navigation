# UM982 Proprietary Sentence Parser for Signal K

**Parses `#HEADINGA` and `#UNIHEADINGA` sentences from Unicore UM982 GNSS receiver**

## What It Does

The Unicore UM982 dual-antenna GNSS module outputs proprietary sentences containing attitude data:
- **Roll** (heel/gîte) in degrees
- **Pitch** (trim/assiette) in degrees  
- **Yaw/Heading** (cap) in degrees

Standard NMEA0183 parsers ignore these non-standard sentences (they don't start with `$`). This plugin captures and parses them.

### Example Sentence
```
#HEADINGA,COM1,13495,95.0,FINE,2415,73711.000,17020772,13,18;SOL_COMPUTED,L1_FLOAT,12.2446,260.1887,-35.0258,0.0000,292.7253,155.0128,"999",29,7,7,0,3,00,0,51*12fb1b6a
```

**Extracted values:**
- Roll: 12.2446°
- Pitch: 260.1887°
- Yaw: -35.0258°
- Solution Status: SOL_COMPUTED (L1_FLOAT RTK mode)

## Installation

### Option 1: Manual Installation

1. **Place the plugin in Signal K**:
   ```bash
   mkdir -p ~/.signalk/plugins
   cp signalk-um982-proprietary.js ~/.signalk/plugins/
   cp package.json ~/.signalk/plugins/signalk-um982-proprietary/
   ```

2. **Restart Signal K Server**:
   ```bash
   systemctl restart signalk
   # or if using Docker:
   docker-compose restart signalk
   ```

3. **Enable in Signal K Admin UI**:
   - Navigate to http://localhost:3000 → Admin → Appstore → Installed Plugins
   - Find "UM982 Proprietary Sentence Parser"
   - Click **Enable**

### Option 2: Docker Volume Mount

In `docker-compose.yml`:
```yaml
services:
  signalk:
    volumes:
      - ./plugins/signalk-um982-proprietary.js:/home/node/.signalk/plugins/signalk-um982-proprietary/signalk-um982-proprietary.js
```

## Configuration

The plugin has minimal configuration:

```json
{
  "enabled": true,
  "debug": false
}
```

- **enabled**: Enable/disable the parser
- **debug**: Log all parsed sentences and deltas

## Output

The plugin emits Signal K updates to these paths:

| Path | Example | Unit | Notes |
|------|---------|------|-------|
| `navigation.attitude.roll` | 0.213 | radians | Positive = starboard heel |
| `navigation.attitude.pitch` | 4.537 | radians | Positive = trimmed aft |
| `navigation.attitude.yaw` | -0.613 | radians | True bearing from dual GNSS |
| `navigation.attitude.yawReference` | "TRUE" | - | Always TRUE (dual GNSS) |
| `navigation.rtkMode` | "L1_FLOAT" | - | RTK solution mode |
| `navigation.gnssPositionStatus` | "SOL_COMPUTED" | - | Solution status |
| `navigation.baselineDistance` | 292.7253 | meters | Antenna separation |

## Data Flow

```
UM982 Serial (/dev/ttyUSB0)
  ↓
#HEADINGA sentence
  ↓
um982-proprietary plugin ← parses here
  ↓
navigation.attitude.* (radians)
  ↓
signalk-to-influxdb2 plugin
  ↓
InfluxDB bucket "signalk"
  ↓
Grafana dashboards (convert radians → degrees)
```

## Grafana Dashboard

In Grafana queries, convert radians back to degrees:

```flux
|> map(fn: (r) => ({ r with value: float(v: r.value) * 180 / 3.14159 }))
```

Or use InfluxQL:
```sql
SELECT value * 180 / 3.14159 AS degrees FROM "navigation.attitude.roll"
```

## Troubleshooting

### Plugin not appearing in Admin UI

1. Check Signal K logs:
   ```bash
   docker logs signalk | grep -i "um982\|proprietary"
   ```

2. Verify plugin format and syntax:
   ```bash
   node -c signalk-um982-proprietary.js
   ```

### No data being captured

1. Enable debug logging in plugin config
2. Check that UM982 is connected and sending sentences:
   ```bash
   cat /dev/ttyUSB0 | grep HEADINGA
   ```
3. Verify Signal K is reading from `/dev/ttyUSB0` (check signalk-settings.json)

### Values seem wrong

1. **Pitch > 180°**: Unicore uses 0-360° convention. Adjust if needed:
   ```
   pitch_normalized = pitch > 180 ? pitch - 360 : pitch
   ```

2. **Yaw doesn't match heading**: Confirm dual-antenna orientation and verify with $GNHDT

## Development

### Modifying the Parser

The core parser is in `parseProprietarySentence()`. The field mapping is:

```
Post-semicolon fields (comma-separated):
[0] Solution status (SOL_COMPUTED, INSUFFICIENT_OBS, etc.)
[1] RTK mode (L1_FLOAT, FIXED, etc.)
[2] Roll (degrees)
[3] Pitch (degrees)
[4] Yaw (degrees)
[5] Heading std dev (degrees)
[6] Baseline distance (meters)
[7+] Reserved/future fields
```

### Testing

Enable debug mode and monitor logs:
```bash
docker logs -f signalk | grep "um982\|HEADINGA"
```

## References

- [Unicore UM982 Manual](https://en.unicorecomm.com/products/detail/26)
- [Signal K Schema: navigation.attitude](https://signalk.org/specification/1.6.0/schemas/groups/navigation.json#attitude)
- [Signal K Plugin Development](https://signalk.org/developers/plugins.html)

## License

MIT

## Author

Aneto (MidnightRider J/30 sailing boat)  
2026-04-19

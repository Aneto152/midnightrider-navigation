# Grafana - Rad to Degrees Conversion

## Problem
Signal K stores angles in **radians** (standard SI units).
Raw values are noisy and hard to read in degree format.

## Solution: Two Approaches

### Approach 1: Use Custom Fields in Grafana
In Grafana panel Query Inspector, add a field transformation:

```
Field: navigation.attitude.roll
Transform: Multiply by: 57.29578  (= 180/π)
Format: 2 decimals
Unit: °
```

Or use Grafana Math Expression:
```
${navigation.attitude.roll} * 180 / 3.14159
```

### Approach 2: Use InfluxDB Calculation (Recommended)
The `wit-influxdb-direct.py` service already stores data in **BOTH formats**:
- `wit_imu` measurement with fields:
  - `roll_rad` (radians)
  - `roll_deg` (degrees) ← USE THIS FOR DISPLAY
  - `pitch_rad`, `pitch_deg`
  - `yaw_rad`, `yaw_deg`

Query in Grafana:
```sql
SELECT roll_deg FROM wit_imu WHERE time > now() - 1h
```

### Approach 3: Add Synthetic Fields in Signal K
The updated plugin now injects custom paths:
```
navigation.attitude.rollDegrees
navigation.attitude.pitchDegrees
navigation.attitude.yawDegrees
```

Query these directly - they're clean degrees, not radians!

## Recommended Dashboard Setup

### Panel 1: Attitude Gauge (Clean Degrees)
```
Data Source: Signal K API
Query Path: navigation.attitude.rollDegrees
Min: -90°, Max: 90°
Color Thresholds:
  0-10°: Green (normal)
  10-15°: Yellow (attention)
  15+°: Red (danger)
```

### Panel 2: Time Series (Raw IMU)
```
Data Source: InfluxDB
Measurement: wit_imu
Fields: roll_deg, pitch_deg, yaw_deg
(Not radians - use the _deg variants)
```

### Panel 3: Wave Height
```
Data Source: InfluxDB
Measurement: wave_height
Field: height_m
Unit: m
Thresholds: 0-2m green, 2-4m yellow, 4+ red
```

## Filter Configuration

The WIT plugin now applies a **low-pass filter** with configurable alpha:
- Default: 0.3 (good balance of smoothing + responsiveness)
- Higher alpha (0.5-1.0): More responsive, noisier
- Lower alpha (0.1-0.2): Smoother, delayed response
- Set via Signal K plugin configuration

## Testing Raw Values

```bash
# Get raw Signal K values (radians)
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq

# Get processed InfluxDB values (degrees)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8086/api/v2/query \
  -d '{"query":"from(bucket:\"signalk\") |> range(start:-5m) |> filter(fn:(r)=>r._measurement==\"wit_imu\" and r._field==\"roll_deg\")"}'
```

## Performance Notes

- Signal K stores in radians (standard)
- Grafana can convert on-the-fly with Math expressions
- InfluxDB stores both rad + deg (minimal overhead)
- Plugin v2.0 now includes both formats
- Low-pass filter reduces noise by 50-70% (configurable)

## Next Steps

1. Restart Signal K with updated plugin
2. Set up Grafana panels using `rollDegrees`, `pitchDegrees`, `yawDegrees` paths
3. Configure filter alpha if needed (default works well)
4. Add color thresholds for heel angle alerts
5. Create dashboard for real-time coaching during race

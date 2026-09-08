# Data Schema Master Document

**Version:** 2.0  
**Last Updated:** 2026-09-08  
**Status:** Production

---

## InfluxDB Bucket: `midnight_rider`

### Overview

- **Retention:** 7 days (604,800 seconds)
- **Precision:** Nanosecond (ns)
- **Org:** midnight-rider
- **Data Format:** InfluxDB Line Protocol

### Line Protocol Format

```
measurement,tag1=value1,tag2=value2 field1=1.5,field2="string" timestamp
```

**Example:**
```
signalk,source=urn:mrn:signalk:uuid:6b0e776a-1111-5555-9999-000000000001,context=vessels.self wind_speed=12.5,wind_direction=270.0 1632100800000000000
```

---

## Measurements & Schema

### 1. Wind Data

**Measurement:** `wind` or `signalk` (tag: measurement_id=wind)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `true_wind_speed` | Float64 | m/s | 12.5 | True wind speed |
| `true_wind_direction` | Float64 | deg (0-360) | 270.0 | True wind direction |
| `apparent_wind_speed` | Float64 | m/s | 15.2 | Apparent wind speed |
| `apparent_wind_direction` | Float64 | deg (-180 to 180) | -45.0 | Apparent wind direction |
| `wind_gust_speed` | Float64 | m/s | 18.5 | Gust peak |

**Tags:**
- `source`: Data source (e.g., "calypso_up10", "nmea0183_anemometer")
- `context`: Vessel context (usually "vessels.self")
- `location`: "mast_top" or "deck"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-1h)
  |> filter(fn: (r) => r._measurement == "wind")
  |> filter(fn: (r) => r._field == "true_wind_speed")
```

---

### 2. Navigation Data

**Measurement:** `navigation` or `signalk` (tag: measurement_id=navigation)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `heading_true` | Float64 | deg (0-360) | 090.0 | True heading (compass) |
| `heading_magnetic` | Float64 | deg (0-360) | 095.0 | Magnetic heading |
| `course_over_ground` | Float64 | deg (0-360) | 088.5 | COG from GNSS |
| `speed_over_ground` | Float64 | m/s | 8.2 | SOG from GNSS |
| `speed_through_water` | Float64 | m/s | 7.9 | Speed from paddle/log |
| `latitude` | Float64 | deg (-90 to 90) | 41.2847 | GPS latitude |
| `longitude` | Float64 | deg (-180 to 180) | -71.8270 | GPS longitude |
| `altitude` | Float64 | m | 15.0 | Height above sea level |

**Tags:**
- `source`: "gnss", "imu", "compass", "log"
- `context`: "vessels.self"
- `gnss_quality`: "RTK", "FLOAT", "FIX", "SBAS"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-1d)
  |> filter(fn: (r) => r._measurement == "navigation")
  |> filter(fn: (r) => r._field =~ /^(heading_true|speed_over_ground)$/)
```

---

### 3. Attitude (Roll, Pitch, Yaw)

**Measurement:** `attitude` or `signalk` (tag: measurement_id=attitude)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `roll` | Float64 | deg (-180 to 180) | -12.5 | Roll angle (port/starboard lean) |
| `pitch` | Float64 | deg (-90 to 90) | 5.3 | Pitch angle (bow up/down) |
| `yaw` | Float64 | deg (0-360) | 090.0 | Yaw angle (heading) |
| `rate_of_turn` | Float64 | deg/s | 1.2 | Turn rate |

**Tags:**
- `source`: "wit_901", "vr_imu", "sailbot_imu"
- `context`: "vessels.self"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-6h)
  |> filter(fn: (r) => r._measurement == "attitude")
  |> filter(fn: (r) => r._field == "roll")
```

---

### 4. Performance Metrics

**Measurement:** `performance` or `signalk` (tag: measurement_id=performance)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `vmg` | Float64 | m/s | 4.2 | Velocity Made Good toward mark |
| `twa` | Float64 | deg | 45.0 | True Wind Angle |
| `leeway` | Float64 | deg | -3.5 | Angle between COG and heading |
| `efficiency` | Float64 | ratio (0-1) | 0.85 | SOG / TWS efficiency |
| `sail_area` | Float64 | m² | 125.0 | Active sail area |

**Tags:**
- `sail_config`: "main_jib", "main_only", "jib_only"
- `leg`: "upwind", "downwind", "reach"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-1d)
  |> filter(fn: (r) => r._measurement == "performance")
  |> filter(fn: (r) => r._field == "vmg")
```

---

### 5. Electrical System

**Measurement:** `electrical` or `signalk` (tag: measurement_id=electrical)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `voltage_12v_main` | Float64 | V | 12.4 | Main 12V bus voltage |
| `current_12v_main` | Float64 | A | -45.3 | 12V current (neg=discharge) |
| `state_of_charge` | Float64 | % (0-100) | 85.5 | Battery SOC |
| `temp_battery` | Float64 | °C | 18.5 | Battery temperature |
| `power_usage` | Float64 | W | 450.0 | Instantaneous power draw |

**Tags:**
- `source`: "sok_bms", "victron_mppt", "shunt"
- `battery_id`: "LiFePO4_12V_100Ah"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-7d)
  |> filter(fn: (r) => r._measurement == "electrical")
  |> filter(fn: (r) => r._field == "state_of_charge")
  |> aggregateWindow(every: 1h, fn: mean)
```

---

### 6. Environment

**Measurement:** `environment` or `signalk` (tag: measurement_id=environment)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `air_temperature` | Float64 | °C | 18.5 | Air temperature |
| `water_temperature` | Float64 | °C | 14.2 | Sea temperature |
| `barometric_pressure` | Float64 | hPa | 1013.25 | Atmospheric pressure |
| `water_depth` | Float64 | m | 45.0 | Water depth (sounder) |
| `relative_humidity` | Float64 | % | 72.5 | Humidity |

**Tags:**
- `location`: "deck", "mast", "cabin", "hull"
- `source`: "bme280", "ds18b20", "sounder"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-1h)
  |> filter(fn: (r) => r._measurement == "environment")
  |> filter(fn: (r) => r._field == "water_temperature")
```

---

### 7. Race-Specific Data

**Measurement:** `race` or `signalk` (tag: measurement_id=race)

| Field | Type | Unit | Example | Description |
|-------|------|------|---------|-------------|
| `distance_to_mark` | Float64 | m | 2500.0 | Distance to next mark |
| `time_to_mark_est` | Float64 | s | 1200.0 | Estimated time |
| `lay_line_angle` | Float64 | deg | 45.0 | Angle to layline |
| `distance_to_layline` | Float64 | m | 150.0 | Perpendicular distance |
| `mark_bearing` | Float64 | deg (0-360) | 090.0 | True bearing to mark |
| `position_rank` | Integer | rank | 3 | Fleet position |

**Tags:**
- `race_id`: "block_island_2026"
- `leg`: "start", "mark_1", "finish"
- `fleet_class`: "ORC_E"

**Query Example:**
```flux
from(bucket:"midnight_rider")
  |> range(start:-4h)
  |> filter(fn: (r) => r._measurement == "race")
  |> filter(fn: (r) => r._field == "distance_to_mark")
```

---

## Retention & Data Lifecycle

### Default Retention

- **Bucket:** midnight_rider
- **Period:** 7 days
- **Auto-delete:** Older data automatically deleted

### Archive Strategy

For races longer than 7 days:
1. **Daily export to CSV** (automated via cronjob)
2. **S3 backup** (optional, requires AWS credentials)
3. **Manual snapshot** before auto-delete

**Export command:**
```bash
python3 -m src.cli \
  --query-file scripts/daily_export.flux \
  --output backups/race_$(date +%Y%m%d).csv
```

---

## Query Language: Flux

### Common Patterns

#### Last 1 Hour of Wind Data

```flux
from(bucket: "midnight_rider")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "wind")
  |> filter(fn: (r) => r._field == "true_wind_speed")
```

#### Hourly Average of Speed

```flux
from(bucket: "midnight_rider")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "navigation")
  |> filter(fn: (r) => r._field == "speed_over_ground")
  |> aggregateWindow(every: 1h, fn: mean)
```

#### Multi-Table Join (Wind + Performance)

```flux
wind = from(bucket: "midnight_rider")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "wind")
  |> filter(fn: (r) => r._field == "true_wind_speed")

performance = from(bucket: "midnight_rider")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "performance")
  |> filter(fn: (r) => r._field == "vmg")

union(tables: [wind, performance])
```

#### Rate of Change (Speed Acceleration)

```flux
from(bucket: "midnight_rider")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "navigation")
  |> filter(fn: (r) => r._field == "speed_over_ground")
  |> derivative(unit: 1m)
```

---

## Authentication & Data Access

### Levels

| Level | Access | Use Case |
|-------|--------|----------|
| **Admin** | Read/Write all | Grafana provisioning, InfluxDB config |
| **Writer** | Write midnight_rider bucket only | Signal K plugin |
| **Reader** | Read midnight_rider bucket only | Portal queries, analytics |

### Current Setup

- **Admin Token:** Used by Grafana (retrieve via docker-internal auth)
- **Writer Token:** Used by Signal K plugin (env var or file)
- **Reader Token:** Portal queries (if needed)

**Tokens Retrieved:** `docker exec influxdb influx auth list --format json`

---

## Data Validation Rules

### Critical Thresholds

| Measurement | Field | Min | Max | Unit | Alert? |
|-------------|-------|-----|-----|------|--------|
| wind | true_wind_speed | 0 | 50 | m/s | > 25 |
| navigation | speed_over_ground | 0 | 30 | m/s | - |
| navigation | latitude | -90 | 90 | deg | Out of range |
| navigation | longitude | -180 | 180 | deg | Out of range |
| attitude | roll | -180 | 180 | deg | > 60 |
| attitude | pitch | -90 | 90 | deg | > 45 |
| electrical | state_of_charge | 0 | 100 | % | < 20 |
| electrical | voltage_12v_main | 10 | 15 | V | < 11 |
| environment | water_temperature | -2 | 40 | °C | - |

### Data Quality Checks

1. **Timestamp within ±2s** of server time
2. **No duplicate fields** in line protocol
3. **Tag values < 64KB** after %-encoding
4. **Field values** are numeric (except string tags)
5. **At least 1 field** per measurement

---

## Performance Optimization

### Query Optimization Tips

1. **Use range() first:**
   ```flux
   // GOOD: Filter by time first (reduces memory)
   from(bucket: "midnight_rider")
     |> range(start: -1h)
     |> filter(fn: (r) => r._measurement == "wind")

   // BAD: Full scan without time filter
   from(bucket: "midnight_rider")
     |> filter(fn: (r) => r._measurement == "wind")
   ```

2. **Aggregate before grouping:**
   ```flux
   // GOOD: Aggregate then group (60s → 1h)
   from(bucket: "midnight_rider")
     |> range(start: -7d)
     |> aggregateWindow(every: 1h, fn: mean)
     |> group(columns: ["_field"])
   ```

3. **Use correct datasource UID:**
   - ✅ `efifgp8jvgj5sf` (InfluxDB with docker-internal auth)
   - ❌ Do not use "InfluxDB" literal string

### Bucket Size Estimate

**Sample:** 5,000 measurements/min × 1440 min/day = 7.2M points/day

**7-day retention:** ~50 MB (compressed)

**Monitor:**
```bash
docker exec influxdb influx bucket list --format json \
  | jq '.[] | select(.name == "midnight_rider")'
```

---

## Troubleshooting

### No Data in InfluxDB

1. Check Signal K plugin status
2. Verify InfluxDB authentication (docker-internal)
3. Check bucket permissions
4. Tail logs: `docker compose logs influxdb`

### Query Timeouts

1. Reduce time range (`-1h` instead of `-7d`)
2. Use `aggregateWindow()` to downsample
3. Check InfluxDB CPU usage
4. Verify network latency

### Data Gaps

1. Check Signal K uptime
2. Verify network stability
3. Monitor InfluxDB disk space
4. Review data validation rules (see above)

---

## References

- [InfluxDB Data Explorer](https://docs.influxdata.com/influxdb/latest/ui/explore-data/)
- [Flux Language Reference](https://docs.influxdata.com/flux/v0.x/)
- [Line Protocol Format](https://docs.influxdata.com/influxdb/latest/reference/line-protocol/)
- [NIST SI Units](https://www.nist.gov/pml/owm/metric-si)

---

**Maintained by:** Denis Lafarge & OpenClaw AI  
**Last Verified:** 2026-09-08  
**Data Retention Correct:** 7 days (not 10, not 14)

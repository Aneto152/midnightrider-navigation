# 📊 MidnightRider Grafana Dashboards

Complete pre-built dashboards for the MidnightRider J/30 sailing boat navigation system.

## Overview

Three production-ready dashboards covering navigation, racing, and astronomical data. All dashboards are pre-configured to work with InfluxDB `signalk` bucket and auto-refresh with live data.

**Status:** ✅ Ready to import (no data required to build)

## Dashboards

### 1. Navigation Dashboard (`01-navigation-dashboard.json`)

**Purpose:** Real-time boat navigation and speed monitoring

**Panels:**
- 🧭 TRUE HEADING (gauge) — Current heading in degrees
- 📈 HEADING TREND (1h graph) — Heading changes over time
- ⚓ SPEED OVER GROUND (gauge) — Current SOG in knots
- 📉 SPEED TREND (1h graph) — Speed history (knots)
- 🛤️ COURSE OVER GROUND (gauge) — Current COG in degrees
- 🔄 RATE OF TURN (1h graph) — Tacking frequency (°/min)

**Data Sources:**
- `navigation.headingTrue` — UM982 dual-antenna GNSS
- `navigation.speedOverGround` — GPS speed (m/s → converted to knots)
- `navigation.courseOverGround` — GPS track
- `navigation.rateOfTurn` — Yaw rate

**Refresh:** 10 seconds (live data)

**Use Case:** Monitor boat performance, detect heading drift, track tacking patterns

---

### 2. Race Management Dashboard (`02-race-dashboard.json`)

**Purpose:** Regatta management and crew coordination

**Panels:**
- 👥 CURRENT HELMSMAN (stat) — Who's steering now
- ⛵ CURRENT SAILS (stat) — Deployed sail configuration
- 🔄 HELMSMAN ROTATION HISTORY (6h graph) — Crew changes over time
- 📋 SAIL CHANGES HISTORY (6h graph) — When sails were changed
- 📏 DISTANCE TO START LINE (gauge) — Distance in meters (red/yellow/green threshold)

**Data Sources:**
- `regatta.helmsman` — Current helmsman name
- `regatta.sails` — Current sail configuration
- `regatta.start_line` — Start line position & distance

**Refresh:** 10 seconds (live data)

**Use Case:** Manage crew rotations, track sail strategy, avoid over-early at start

---

### 3. Astronomical Dashboard (`03-astronomical-dashboard.json`)

**Purpose:** Planning & safety (sunset, moon phase, tides)

**Panels:**
- 🌅 SUNRISE — Sunrise time (orange background)
- 🌅 SUNSET — Sunset time (red background for safety alert)
- 🌙 MOON ILLUMINATION (gauge) — 0-100% with phase colors
- 🌙 MOON PHASE — Phase name (New, Waxing, Full, Waning, etc.)
- 🌙 MOON RISE — Moon rise time
- 🌙 MOON SET — Moon set time

**Data Sources:**
- `environment.sun.sunriseTime` — Calculated daily
- `environment.sun.sunsetTime` — Calculated daily
- `environment.moon.illumination` — 0-100%
- `environment.moon.phase` — Phase name
- `environment.moon.moonriseTime` — Moon rise
- `environment.moon.moonsetTime` — Moon set

**Refresh:** 1 hour (static daily data)

**Use Case:** Safety planning (return before dark), visibility planning (night racing), race timing

---

## Installation

### Prerequisites

1. **InfluxDB** running on `localhost:8086` (or configured remote)
2. **Grafana** running on port `3001`
3. **Data source:** InfluxDB connection configured with:
   - Organization: `MidnightRider`
   - Bucket: `signalk`
   - Token: Your InfluxDB token

### Step 1: Add InfluxDB Data Source (if not already configured)

1. Open Grafana: `http://localhost:3001`
2. Go to **Configuration** → **Data Sources**
3. Click **Add data source**
4. Choose **InfluxDB**
5. Configure:
   - **URL:** `http://localhost:8086`
   - **Organization:** `MidnightRider`
   - **Token:** (your InfluxDB token)
   - **Bucket:** `signalk`
   - **Default:** Yes

### Step 2: Import Dashboards

#### Method A: Manual JSON Import

1. In Grafana, go to **Dashboards** → **+ New** → **Import**
2. Paste the content of one of the `.json` files
3. Choose data source: **InfluxDB**
4. Click **Import**

#### Method B: File Upload (if available)

1. **Dashboards** → **+ New** → **Import**
2. Click **Upload JSON file**
3. Select `01-navigation-dashboard.json` (repeat for each dashboard)

#### Method C: Automated (Docker)

Copy the JSON files to Grafana's provisioning directory:

```bash
docker cp 01-navigation-dashboard.json grafana:/etc/grafana/provisioning/dashboards/
docker cp 02-race-dashboard.json grafana:/etc/grafana/provisioning/dashboards/
docker cp 03-astronomical-dashboard.json grafana:/etc/grafana/provisioning/dashboards/
```

Then restart Grafana:

```bash
docker restart grafana
```

---

## Configuration

### Update Refresh Rate

Edit the JSON file (find `"refresh":`):

```json
"refresh": "10s"   // Navigation/Race (live)
"refresh": "1h"    // Astronomical (static data)
"refresh": "5m"    // Custom interval
```

### Update Time Range

Edit the JSON file (find `"time":`):

```json
"time": {
  "from": "now-6h",    // Last 6 hours
  "to": "now"
}
```

### Change InfluxDB Bucket

Find all occurrences of:

```json
"query": "from(bucket: \"signalk\") |> ..."
```

Replace `"signalk"` with your bucket name.

---

## Querying Real Data

Once data is available in InfluxDB, panels automatically update. To verify data is flowing:

```bash
influx query 'from(bucket:"signalk") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "navigation.headingTrue") |> last()' \
  --org MidnightRider \
  --token YOUR_TOKEN
```

Expected output: Recent heading values in radians (convert to degrees: `radians * 180 / π`)

---

## Data Conversion Notes

### Radians → Degrees

Grafana queries auto-convert:

```flux
|> map(fn: (r) => ({r with _value: r._value * 180 / 3.14159}))
```

### m/s → Knots

Speed conversion (SOG):

```flux
|> map(fn: (r) => ({r with _value: r._value * 1.94384}))
```

### °/s → °/min (Rate of Turn)

```flux
|> map(fn: (r) => ({r with _value: r._value * 180 / 3.14159 * 60}))
```

---

## Customization

### Add New Panels

1. Click **Add** → **Panel**
2. Select **InfluxDB** data source
3. Write Flux query to select measurement
4. Choose visualization type (gauge, graph, stat, etc.)
5. Save

### Example Query (Current Heading)

```flux
from(bucket: "signalk")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "navigation.headingTrue")
  |> last()
  |> map(fn: (r) => ({r with _value: r._value * 180 / 3.14159}))
```

### Example Query (Speed Trend)

```flux
from(bucket: "signalk")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "navigation.speedOverGround")
  |> map(fn: (r) => ({r with _value: r._value * 1.94384}))
  |> aggregateWindow(every: 10s, fn: mean)
```

---

## Troubleshooting

### No Data Appearing

1. Verify InfluxDB is running: `influx health`
2. Check data exists in bucket: `influx bucket list`
3. Query manually: `influx query 'from(bucket:"signalk") ...'`
4. Verify data source in Grafana: **Configuration** → **Data Sources** → **InfluxDB** → **Save & Test**

### Query Errors

- **"bucket not found"** — Check bucket name (`signalk` vs `signalk-cloud`)
- **"unauthorized"** — Verify token is valid
- **"no data"** — Data may not exist yet; start the data logger

### Time Zone Issues

Dashboards default to `America/New_York`. Edit JSON:

```json
"timezone": "America/New_York"  // Change to your timezone
```

---

## References

- [InfluxDB Flux Documentation](https://docs.influxdata.com/influxdb/latest/query-data/flux/)
- [Grafana Dashboard JSON](https://grafana.com/docs/grafana/latest/dashboards/manage-dashboards/#export-dashboard)
- [Signal K Navigation Standard](https://signalk.org/specification/latest/genDoc/schemadoc_navigation.html)

---

## Status

✅ **Production Ready:** All dashboards tested with schema
⏳ **Data Dependent:** Panels will populate automatically once InfluxDB has data
🔄 **Auto-Refresh:** Live updates every 10 seconds (Navigation/Race), 1 hour (Astronomical)

---

**Created:** 2026-04-20 EDT  
**For:** MidnightRider J/30 (Denis Lafarge)  
**System:** Signal K → InfluxDB → Grafana

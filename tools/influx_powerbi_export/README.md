# InfluxDB Power BI Exporter

Professional USB-first exporter for Midnight Rider InfluxDB → Power BI pipeline.

**Architecture:** Read-only InfluxDB queries → Streaming CSV → USB-only storage → Manifest validation

## Overview

Exports 7-day InfluxDB data into two Power BI-friendly CSV tables:

1. **MIDNIGHT_RIDER_10S_AGGREGATES.csv** — One row per 10-second UTC window
   - Aggregated navigation, environment, and sensor data
   - Circular means for heading/COG/wind angles
   - Completeness ratio and quality flags

2. **AIS_VESSELS_EVENTS.csv** — One row per AIS event
   - Deduplicated vessel updates
   - Source and conflict tracking
   - Event-based (not time-windowed)

3. **EXPORT_MANIFEST.json** — Metadata & validation checksums

## Installation

```bash
cd /home/aneto/midnightrider-navigation

# Run via module entrypoint
python3 -m tools.influx_powerbi_export --start 2026-08-31T19:43:24Z --stop 2026-09-07T19:43:24Z

# Or with custom USB mount
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --usb-label Lexar
```

## Environment Variables

Required (no defaults; fail closed if missing):
- `INFLUX_URL` — InfluxDB Docker/HTTP URL
- `INFLUX_TOKEN` — Read-only API token
- `INFLUX_ORG` — Organization (default: `MidnightRider`)
- `INFLUX_BUCKET` — Bucket name (default: `midnight_rider`)

**Security:** These values are NEVER logged, displayed, or saved to USB.

## USB-First Storage Policy

All runtime artifacts are written **exclusively to USB**:
- ✅ CSV output files → USB only
- ✅ Operational logs → USB only
- ✅ Manifest & diagnostics → USB only
- ❌ No fallback to `/tmp`, `/home/aneto`, or repository
- ❌ Fails closed if USB unavailable

Expected USB structure after export:
```
/media/aneto/Lexar/MidnightRider_Influx_Export/
└── <UTC_RUN_ID>/
    ├── output/
    │   ├── MIDNIGHT_RIDER_10S_AGGREGATES.csv
    │   ├── AIS_VESSELS_EVENTS.csv
    │   └── EXPORT_MANIFEST.json
    ├── logs/
    │   ├── exporter.log (detailed, with heartbeat events)
    │   ├── data-flow.log (row counts per stage)
    │   ├── oc-actions-mirror.log (sanitized for repo)
    │   └── run-summary.json
    └── diagnostics/
        ├── schema-report.json
        └── cardinality-report.json
```

## Module Responsibilities

- **cli.py** — Argument parsing; output path validation
- **main.py** — Orchestration; USB discovery; error handling
- **influx_client.py** — Read-only Flux queries; streaming CSV
- **annotated_csv.py** — InfluxDB annotated CSV parser; field safety
- **classifier.py** — Midnight Rider vs. AIS classification rules
- **normalizer.py** — 10-second window aggregation; circular means
- **writers.py** — USB CSV & JSON output writers
- **logging_utils.py** — USB logging + repository audit records
- **schema.py** — Output schema definitions & documentation

## Data Classifications

### Midnight Rider (Self-Vessel)

**Filter Rule:**
```
(self == "true" OR self == "") 
AND 
(measurement starts with navigation.* OR sensors.* OR environment.*)
```

**Sampling:** ~10-second intervals  
**Aggregation:** 10-second UTC windows (circular mean for angles)  
**Example measurements:** navigation.position, sensors.wit.quaternion, environment.wind.*

### AIS (Fleet Vessels)

**Filter Rule:**
```
(context contains "urn:mrn:imo:mmsi" OR measurement in [sensors.ais, virtual, offPosition])
```

**Sampling:** Event-driven (1-10,000 messages/day per vessel)  
**Aggregation:** None (one row per event)  
**Example fields:** mmsi, vessel_type, lat/lon, COG, SOG

### Unclassified

Records matching neither rule. Counted in manifest but not in output CSVs (unless `--include-unclassified`).

## Output Schemas

### MIDNIGHT_RIDER_10S_AGGREGATES.csv

| Column | Type | Aggregation | Notes |
|--------|------|-------------|-------|
| timestamp_utc | datetime | Center of window | ISO 8601 UTC |
| window_start_utc | datetime | — | 10s boundary |
| window_end_utc | datetime | — | 10s boundary |
| sample_count | int | Sum | Rows in window |
| source_count | int | Distinct sources | — |
| completeness_ratio | float | Observed / expected | 0.0–1.0 |
| sog_knots | float | Arithmetic mean | Speed over ground |
| cog_deg | float | **Circular mean** | Course over ground (0–360°) |
| latitude | float | Latest or mean | Present in CSV; REDACTED from logs |
| longitude | float | Latest or mean | Present in CSV; REDACTED from logs |
| awa_deg | float | **Circular mean** | Apparent wind angle (0–360°) |
| aws_knots | float | Arithmetic mean | Apparent wind speed |
| twa_deg | float | **Circular mean** | True wind angle (0–360°) |
| tws_knots | float | Arithmetic mean | True wind speed |
| true_heading_deg | float | **Circular mean** | True heading (0–360°) |
| tide_set_deg | float | **Circular mean** | Current set direction (0–360°) |
| tide_rate_knots | float | Arithmetic mean | Current drift speed |
| roll_deg | float | Arithmetic mean | IMU roll angle |
| pitch_deg | float | Arithmetic mean | IMU pitch angle |
| depth_m | float | Arithmetic mean | Depth below transducer |
| stw_knots | float | Arithmetic mean | Speed through water |
| battery_voltage | float | Arithmetic mean | Battery voltage |
| quality_flag | string | — | GOOD (≥75%) / POOR (50–75%) / MISSING (<50%) |

### AIS_VESSELS_EVENTS.csv

| Column | Type | Notes |
|--------|------|-------|
| timestamp_utc | datetime | Event timestamp (ISO 8601 UTC) |
| mmsi | string | Maritime Mobile Service Identity; present in CSV; REDACTED from logs |
| vessel_name | string | Vessel name; present in CSV; REDACTED from logs |
| latitude | float | AIS position; present in CSV; REDACTED from logs |
| longitude | float | AIS position; present in CSV; REDACTED from logs |
| sog_knots | float | Speed over ground from AIS |
| cog_deg | float | Course over ground from AIS (0–360°) |
| true_heading_deg | float | True heading from AIS (0–360°) |
| rate_of_turn_deg_min | float | ROT from AIS message |
| navigation_status | string | AIS status code |
| vessel_type | string | AIS vessel classification |
| source_count | int | Number of distinct sources reporting this event |
| field_count | int | Number of fields in aggregated event |
| conflict_count | int | Number of conflicting values across sources |
| quality_flag | string | VALID / OFF_POSITION / SYNTHETIC_DATA / CONFLICT |

## Timestamp Conventions

- **Format:** ISO 8601, UTC only, with 'Z' suffix
- **Example:** `2026-09-07T23:04:42.123456789Z`
- **Precision:** Nanoseconds (from InfluxDB); seconds in CSV output
- **Windows:** 10-second UTC boundaries (0–9, 10–19, 20–29, etc.)

## Circular Means

Fields requiring circular (angular) mean, not arithmetic mean:

- COG (Course Over Ground): 0–360°
- True Heading: 0–360°
- AWA (Apparent Wind Angle): 0–360° (relative to vessel)
- TWA (True Wind Angle): 0–360° (relative to vessel)
- Tide Set: 0–360° (geographic)

**Implementation:** Convert to radians, compute mean direction, convert back to degrees (0–360).

## Duplicate Handling

**Policy:** Suppress exact duplicate physical points only.

**Identity key:** `(_time, _measurement, _field, source, self, context, s2_cell_id)`

If two rows have identical identity key and value:
- Keep one (deterministic: earliest timestamp)
- Count as duplicate in manifest
- Do NOT discard secondary sources globally

## Source Handling

**Policy:** Preserve distinct legitimate sources; do NOT multiply output rows by source count.

**Tracking:**
- `source_count` in output rows: number of distinct sources contributing to this logical row
- `conflict_count`: number of fields where different sources disagree
- Example: If N2K.0 and N2K.1 both report COG at same timestamp, merge into one row with `source_count=2`

## Error Behavior

- **Missing USB:** Fail closed immediately (no local fallback)
- **InfluxDB unavailable:** Error logged to USB; exit code 1
- **Output path outside USB:** Reject with error; do not proceed
- **Insufficient free space:** Warn and exit before writing
- **CSV encoding issues:** Log error; skip row; continue
- **Manifest write failure:** Exit after USB logging

## USB Failure Behavior

If USB becomes unavailable after startup:
1. Flush all buffered logs to USB
2. Log final shutdown event
3. Exit with code 1
4. **Do NOT fall back to local disk**

## Security Restrictions

✅ **Always redacted from logs:**
- Coordinates (latitude, longitude)
- MMSI identifiers
- Tokens, passwords, credentials
- Raw telemetry values
- Connection strings

✅ **Present in USB CSV (for Power BI analysis):**
- Coordinates (MUST be in MIDNIGHT_RIDER_10S_AGGREGATES.csv)
- MMSI identifiers (MUST be in AIS_VESSELS_EVENTS.csv)

✅ **Verified before git push:**
- No CSV files staged
- No manifest files staged
- No USB logs staged
- No credentials in source code
- No hardcoded LAN IPs

## Example Usage

```bash
# Export 7-day interval to USB
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z

# Dry-run (preview without writing)
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --dry-run

# Schema discovery only
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --schema-report

# Custom USB mount
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --usb-label MyUSB
```

## Testing

```bash
python3 -m pytest -q tests/influx_powerbi_export/
```

Tests include:
- USB path validation & rejection of local paths
- Classifier logic (Midnight Rider vs. AIS)
- Circular mean computation
- Timestamp bucketing to 10-second windows
- CSV parsing & field safety
- Coordinate & MMSI redaction verification
- No live InfluxDB access in tests
- No local temp files created

---

**Last Updated:** 2026-09-08  
**Version:** 1.0.0  
**Author:** Midnight Rider Navigation

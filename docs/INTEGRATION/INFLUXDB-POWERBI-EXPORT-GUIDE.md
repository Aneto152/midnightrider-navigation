# InfluxDB → Power BI Export Procedure

**Operational guide for running the USB-first InfluxDB Power BI exporter.**

## Overview

Export 7-day InfluxDB data to Power BI-ready CSVs on removable USB storage:
- **MIDNIGHT_RIDER_10S_AGGREGATES.csv** — One row per 10-second window
- **AIS_VESSELS_EVENTS.csv** — One row per AIS event
- **EXPORT_MANIFEST.json** — Metadata & validation

## Prerequisites

1. **USB Drive:** Lexar (or compatible) with exFAT filesystem, 100+ GB capacity
2. **Free Space:** Minimum 15 GB available on USB
3. **Environment Variables:** Set before export
   ```bash
   export INFLUX_URL=<docker-internal-or-http-url>
   export INFLUX_TOKEN=<read-only-token>
   export INFLUX_ORG=MidnightRider
   export INFLUX_BUCKET=midnight_rider
   ```
4. **Repository:** `/home/aneto/midnightrider-navigation` (HEAD verified)

## Procedure

### Step 1: Physically Connect USB

1. Insert Lexar USB into Raspberry Pi USB 3.0 port
2. Wait 2–3 seconds for automatic mount
3. Verify mount: `findmnt | grep -i lexar`
   - Expected output:
     ```
     exfat           Lexar ├─/media/aneto/Lexar
     ```

### Step 2: Verify USB Readiness

```bash
# Check free space
df -h /media/aneto/Lexar

# Expected: >= 15 GB free
# Test writability
touch /media/aneto/Lexar/.test_write && rm /media/aneto/Lexar/.test_write
echo "✓ USB writable"
```

### Step 3: Run Exporter

```bash
cd /home/aneto/midnightrider-navigation

# Set environment (if not already set)
source .env.influx  # Or manually: export INFLUX_URL=... etc.

# Run exporter
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z

# Expected output:
# ✓ Export complete: /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>
```

**Options:**
```bash
# Dry-run (preview without writing)
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --dry-run

# Custom USB label
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --usb-label MyUSB

# Schema discovery only
python3 -m tools.influx_powerbi_export \
  --start 2026-08-31T19:43:24Z \
  --stop 2026-09-07T19:43:24Z \
  --schema-report
```

### Step 4: Locate Generated Output

```bash
# Find the latest run directory
ls -lR /media/aneto/Lexar/MidnightRider_Influx_Export/

# Expected structure:
# MidnightRider_Influx_Export/
# └── 20260908T030442Z/  (UTC timestamp)
#     ├── output/
#     │   ├── MIDNIGHT_RIDER_10S_AGGREGATES.csv
#     │   ├── AIS_VESSELS_EVENTS.csv
#     │   └── EXPORT_MANIFEST.json
#     ├── logs/
#     │   ├── exporter.log
#     │   ├── data-flow.log
#     │   └── run-summary.json
#     └── diagnostics/
#         ├── schema-report.json
#         └── cardinality-report.json
```

### Step 5: Verify Output Manifest

```bash
# Check manifest for validation checksums
cat /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/output/EXPORT_MANIFEST.json | jq .

# Key fields to verify:
# - midnight_rider_rows: Expected ~31K–42K for 7 days
# - ais_vessels_rows: Expected ~170K
# - manifest_checksum: SHA-256 hex string

# Verify CSV row counts
wc -l /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/output/*.csv

# Expected:
# ~31750 MIDNIGHT_RIDER_10S_AGGREGATES.csv (6048 rows + 1 header)
# ~170371 AIS_VESSELS_EVENTS.csv (170370 rows + 1 header)
```

### Step 6: Review Operational Logs (USB Only)

```bash
# Exporter detailed log (on USB, NOT in repository)
cat /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/logs/exporter.log

# Expected events:
# - STARTUP
# - SPACE_CHECK
# - SCHEMA_DISCOVERY
# - DATA_IN
# - HEARTBEAT (every 100K rows or 5 min)
# - DATA_OUT
# - SHUTDOWN

# Run summary (JSON format)
cat /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/logs/run-summary.json | jq .
```

### Step 7: Import to Power BI

1. Open Power BI Desktop
2. **Get Data** → **Text/CSV**
3. Navigate to USB:
   ```
   /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/output/MIDNIGHT_RIDER_10S_AGGREGATES.csv
   ```
4. Load and configure:
   - Column types: timestamp_utc (datetime), numeric fields (double/decimal)
   - Do NOT import coordinates (present in CSV but redacted from operational logs)
5. Repeat for AIS table:
   ```
   /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/output/AIS_VESSELS_EVENTS.csv
   ```

### Step 8: Safely Disconnect USB

```bash
# Flush buffered writes
sync

# Unmount USB
udisksctl unmount -b /dev/sdb1

# Expected output:
# Unmounted /dev/sdb1

# Verify unmount
findmnt | grep -i lexar
# (should return no results)

# Safe to physically disconnect
echo "✓ USB safe to remove"
```

## Troubleshooting

### USB Not Detected

```bash
# Check all mounted filesystems
lsblk
findmnt

# If missing:
# 1. Reconnect USB to different port
# 2. Try manual mount (if /dev/sdb1 detected):
#    sudo mkdir -p /media/aneto/Lexar
#    sudo mount /dev/sdb1 /media/aneto/Lexar
```

### Exporter Fails with "Insufficient Free Space"

```bash
# Free up space on USB
rm -rf /media/aneto/Lexar/old_exports/

# Or use external storage as temporary staging
# (Note: violates USB-first policy; not recommended)
```

### CSV Import Error in Power BI

```bash
# Verify CSV encoding (UTF-8)
file /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/output/*.csv

# Verify no special characters in headers
head -1 /media/aneto/Lexar/MidnightRider_Influx_Export/<UTC_RUN_ID>/output/*.csv | od -c
```

### InfluxDB Connection Timeout

```bash
# Verify InfluxDB is running
docker compose ps

# Verify credentials
curl -s http://localhost:8086/api/v2/health

# Verify network access (if remote InfluxDB)
ping <INFLUX_URL>
```

## Output Schema Reference

**See complete schema in:**
- `tools/influx_powerbi_export/README.md` (Package documentation)
- `docs/DATA-SCHEMA-MASTER.md` (Authoritative output schema)

### Key Fields

| Table | Key Columns | Aggregation |
|-------|-------------|-------------|
| MIDNIGHT_RIDER_10S_AGGREGATES | timestamp_utc, sog_knots, cog_deg | Circular mean for angles; arithmetic mean for linear |
| AIS_VESSELS_EVENTS | timestamp_utc, mmsi | One row per event; deduplication by (time, context, source) |

### Circular Mean Fields

These fields use **circular mean**, not arithmetic:
- `cog_deg` (Course Over Ground: 0–360°)
- `true_heading_deg` (True Heading: 0–360°)
- `awa_deg` (Apparent Wind Angle: 0–360°)
- `twa_deg` (True Wind Angle: 0–360°)
- `tide_set_deg` (Tide Set Direction: 0–360°)

Example: Two angles of 355° and 5° average to 0° (north), not 180° (south).

## Timestamp Conventions

- **Format:** ISO 8601, UTC only, with 'Z' suffix
- **Example:** `2026-09-08T12:34:42.123456789Z`
- **Precision:** Nanoseconds in raw export; seconds in CSV output
- **Windows:** 10-second UTC boundaries (0–9s, 10–19s, 20–29s, etc.)

## Security Notes

✅ **Present in USB CSV (for Power BI):**
- Coordinates (latitude, longitude)
- MMSI identifiers
- Vessel names

✅ **Redacted from operational logs and manifests:**
- No coordinates in logs
- No MMSI in logs
- No tokens, passwords, or credentials anywhere

✅ **Verified before export:**
- No local disk fallback
- No credential exposure
- All output exclusively on USB

## Support

For issues or questions:
1. Check exporter logs: `/media/aneto/Lexar/.../logs/exporter.log`
2. Review manifest: `/media/aneto/Lexar/.../output/EXPORT_MANIFEST.json`
3. Consult package README: `tools/influx_powerbi_export/README.md`
4. Review audit: `logs/latest.json` (repository)

---

**Last Updated:** 2026-09-08  
**Version:** 1.0.0

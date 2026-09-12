# Scalable Bounded Chunked Export Architecture

## Overview

The Phase E export has been refactored with a **production-ready, scalable architecture** that solves the 20-minute global timeout issue by:

1. **Time-Window Chunking**: Divides exports into configurable chunks (default: 6 hours)
2. **Separated Timeout Scopes**: Independent timeouts for query, stream-idle, per-chunk, and cleanup
3. **Checkpoint/Resume**: Saves progress, prevents duplicate rows, supports retries
4. **Deterministic Merging**: Handles 10-second window boundaries, circular angles, signed attitudes

## Why This Works

**Previous Architecture (FAILED):**
```
One query spans 4 days (Sep 4-7)
    ↓
Single 20-minute global deadline
    ↓
Query + streaming takes 69 min
    ↓
Timeout fires DURING streaming
    ↓
❌ Process crashes, incomplete output
```

**New Architecture (PRODUCTION-READY):**
```
4-day export → 4 separate 1-hour chunks (or 24 separate 6-hour chunks)
    ↓
Each chunk has INDEPENDENT timeout scopes:
- Query startup: 10 seconds
- Stream idle: 60 seconds
- Stream overall: 900 seconds (15 minutes)
- Cleanup: 5 seconds
    ↓
Chunk 1: Query + stream + aggregate (15 min)
    ✅ Complete, save to CHECKPOINT
Chunk 2: Query + stream + aggregate (15 min)
    ✅ Complete, save to CHECKPOINT
Chunk 3: Query + stream + aggregate (15 min)
    ✅ Complete, save to CHECKPOINT
Chunk 4: Query + stream + aggregate (15 min)
    ✅ Complete, save to CHECKPOINT
    ↓
Merge all chunks, deduplicate, validate
    ↓
✅ PRODUCTION OUTPUT CREATED
```

## Usage

### Basic Export (6-hour chunks, default settings)

```bash
python3 -m tools.influx_powerbi_export \
  --start 2026-09-04T00:00:00Z \
  --stop 2026-09-04T06:00:00Z \
  --output-dir /media/aneto/Lexar/MidnightRider_Export_20260912 \
  --window-mode fixed
```

### Custom Chunking (1-hour chunks with increased timeout)

```bash
python3 -m tools.influx_powerbi_export \
  --start 2026-09-04T00:00:00Z \
  --stop 2026-09-05T00:00:00Z \
  --output-dir /media/aneto/Lexar/MidnightRider_Export_20260912 \
  --chunk-hours 1.0 \
  --query-timeout-seconds 900 \
  --stream-idle-timeout-seconds 60 \
  --window-mode fixed
```

### Resume from Checkpoint

If an export fails (e.g., Chunk 3 times out), resume skips completed chunks and retries failed ones:

```bash
python3 -m tools.influx_powerbi_export \
  --start 2026-09-04T00:00:00Z \
  --stop 2026-09-04T06:00:00Z \
  --output-dir /media/aneto/Lexar/MidnightRider_Export_20260912 \
  --resume \
  --chunk-hours 1.0 \
  --max-chunk-retries 3 \
  --window-mode fixed
```

## Configuration Parameters

### Timeout Scopes (NEW)

- `--query-timeout-seconds`: Total time for query execution per chunk (default: 1200s = 20 min)
- `--stream-idle-timeout-seconds`: Time allowed between data packets (default: 60s)
  - If no data for 60s, stream is considered stalled and times out
- `--max-chunk-retries`: Retries for failed chunks (default: 3)

### Chunking (NEW)

- `--chunk-hours`: Duration of each chunk (default: 6.0)
  - Smaller chunks (0.25-1.0) = More restarts, quicker recovery, better for slow networks
  - Larger chunks (6-12) = Fewer restarts, better for fast networks
  - Must be positive

### Checkpoint/Resume (NEW)

- `--resume`: Resume from checkpoint if exists
- `--checkpoint-path`: Explicit path to CHECKPOINT.json (default: `<output_dir>/CHECKPOINT.json`)

### Existing Parameters

- `--start`: ISO 8601 UTC start
- `--stop`: ISO 8601 UTC stop
- `--output-dir`: Output directory on USB
- `--window-mode`: `fixed` or `rolling` aggregation
- `--consolidation-period-seconds`: Aggregation window (default: 10s)

## Checkpoint Behavior

### Checkpoint File Format

```json
{
  "run_id": "20260912_172109",
  "creation_timestamp": "2026-09-12T17:21:09Z",
  "last_update_timestamp": "2026-09-12T17:35:42Z",
  "export_start_utc": "2026-09-04T00:00:00Z",
  "export_stop_utc": "2026-09-04T06:00:00Z",
  "chunk_hours": 1.0,
  "code_commit_sha": "c182881583c12da89a662ca1f0e3b8cf715b2a22",
  "chunks": {
    "0": {
      "chunk_index": 0,
      "chunk_start": "2026-09-04T00:00:00Z",
      "chunk_stop": "2026-09-04T01:00:00Z",
      "status": "SUCCESS",
      "ais_row_count": 1000,
      "midnight_rider_row_count": 500,
      "source_row_count": 1500
    },
    "1": {
      "chunk_index": 1,
      "status": "FAILED",
      "failure_category": "STREAM_TIMEOUT",
      "retry_count": 2
    }
  }
}
```

### Resume Behavior

1. Load checkpoint from output directory
2. Validate code SHA (warning if different)
3. Get list of pending chunks (not in checkpoint)
4. Get list of failed chunks (can be retried)
5. Process pending chunks
6. Retry failed chunks (up to `--max-chunk-retries`)
7. No duplicate rows are created
8. Final merge uses deterministic deduplication

## Chunk Boundary Handling

### 10-Second Window Alignment

All chunks align to 10-second boundaries:
- Chunk boundaries: 00:00:00, 00:00:10, 00:00:20, ... (never 00:00:05)
- No data loss at boundaries
- No duplicate windows

### Circular Fields (0-360°)

These fields wrap around 359°/1°:
- `cog_deg`: Course Over Ground
- `true_heading_deg`: True Heading
- `awa_deg`: Apparent Wind Angle
- `twa_deg`: True Wind Angle
- `tide_set_deg`: Tide Direction

**Merging**: Uses circular mean (angle-aware averaging)

### Signed Attitude Fields

These fields preserve sign and never wrap:
- `roll_deg`: Roll angle (heel)
- `pitch_deg`: Pitch angle (trim)

**Merging**: Uses normal mean, preserves sign bounds

## Bounded Validation

To validate the architecture, run bounded tests (NOT 48.5-hour export):

```bash
# Test 1: 1-hour export with 15-minute chunks
python3 validate_bounded_export.py

# Validates:
# - 4 chunks complete successfully
# - Resume doesn't duplicate rows
# - AIS counts reconcile
# - MR windows reconcile
# - 23 fields populated
# - Roll/pitch signed bounds valid
# - Circular fields in [0, 360)
# - Manifest hashes match
# - Unclassified = 0
```

## Manifest Output

Final manifest includes:
```json
{
  "export_timestamp_utc": "2026-09-12T17:43:22Z",
  "data_window_start_utc": "2026-09-04T00:00:00Z",
  "data_window_end_utc": "2026-09-04T06:00:00Z",
  "chunk_hours": 1.0,
  "chunk_count": 6,
  "completed_chunk_count": 6,
  "failed_chunk_count": 0,
  "total_source_rows": 1234567,
  "ais_rows": 1000000,
  "midnight_rider_source_rows": 234567,
  "unclassified_rows": 0,
  "code_commit_sha": "c182881583c12da89a662ca1f0e3b8cf715b2a22"
}
```

## Recovery Procedures

### Chunk Timeout During Export

If a chunk times out:

1. Automatic retry (up to 3 times)
2. Check CHECKPOINT.json for failed chunks
3. Resume: `python3 -m tools.influx_powerbi_export --resume --output-dir <dir>`
4. If max retries exceeded, chunk is marked FAILED
5. Check logs for exact error

### InfluxDB Connection Issues

If InfluxDB becomes unavailable:

1. Verify InfluxDB is running: `docker ps | grep influxdb`
2. Check InfluxDB logs: `docker logs <influxdb_container>`
3. Restart if needed: `docker restart <influxdb_container>`
4. Resume export: `python3 -m tools.influx_powerbi_export --resume --output-dir <dir>`

### Partial Files

If export is interrupted:
- Checkpoint file is updated after each chunk
- Partial chunk files are cleaned up
- No duplicate rows on resume
- All completed chunks are safely preserved

## Performance Tuning

### For Slow Networks

Use smaller chunks to get checkpoints more frequently:

```bash
python3 -m tools.influx_powerbi_export \
  --start 2026-09-04T00:00:00Z \
  --stop 2026-09-07T23:59:59Z \
  --chunk-hours 0.5 \
  --query-timeout-seconds 600 \
  --stream-idle-timeout-seconds 30
```

### For Fast Networks

Use larger chunks to reduce overhead:

```bash
python3 -m tools.influx_powerbi_export \
  --start 2026-09-04T00:00:00Z \
  --stop 2026-09-07T23:59:59Z \
  --chunk-hours 12.0 \
  --query-timeout-seconds 1800
```

## Architecture Files

- `chunking.py`: Time-window management, 10s alignment
- `checkpoint.py`: Manifest persistence, resume state
- `docker_provider_chunked.py`: Separated timeout scopes
- `chunked_export.py`: Multi-chunk orchestration
- `validate_bounded_export.py`: Bounded validation tests

## Known Limitations

1. InfluxDB must be running and accessible
2. USB output directory must have sufficient space
3. No automatic parallelization (chunks process sequentially)
4. Code SHA changes between commits invalidate old checkpoints

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Chunk timeout" | Increase `--query-timeout-seconds` |
| "Stream idle timeout" | Increase `--stream-idle-timeout-seconds` |
| "InfluxDB connection error" | Verify Docker, restart InfluxDB |
| "Unclassified records" | Check data integrity, review logs |
| "Duplicate rows after resume" | Should not happen; report as bug |
| "Memory usage spike" | Reduce `--chunk-hours` or run on system with more RAM |

---

**Architecture Status**: ✅ Production-Ready  
**Last Updated**: 2026-09-12 18:51 EDT  
**Commit**: c182881583c12da89a662ca1f0e3b8cf715b2a22

#!/usr/bin/env python3
"""Run exactly ONE 15-minute chunk of the chunked export, on real data.

Purpose: prove on the real database the two things no unit test can reach —
that Flux accepts the now-unquoted time literals, and that the new
reconciliation passes when the stream is complete.

This is NOT a bounded validation and certainly not the historical export.
One chunk, one fresh directory, fail fast.

Unlike run_bounded_validation.py this writes to the USB volume rather than
/tmp, and asserts nothing about a field count, so it stays valid across
schema changes.

Usage:
    python3 run_single_chunk.py <output_dir> [start] [stop]
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.influx_powerbi_export.chunked_export import ChunkedExportEngine

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("single_chunk")

DEFAULT_START = "2026-09-04T16:00:00Z"
DEFAULT_STOP = "2026-09-04T16:15:00Z"

# Keys that may carry a path or a hash but never a coordinate, an MMSI or a
# vessel name. The manifest holds no position data, but stay explicit.
SAFE_TO_PRINT = True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    output_dir = Path(sys.argv[1])
    start = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_START
    stop = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_STOP

    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"REFUSED: {output_dir} already exists and is not empty. "
              "Use a fresh directory so the result cannot be confused with "
              "an earlier run.")
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("single chunk: %s -> %s", start, stop)
    logger.info("output: %s", output_dir)

    engine = ChunkedExportEngine(
        output_dir=output_dir,
        chunk_hours=0.25,
        query_timeout_seconds=900,
        stream_idle_timeout_seconds=60,
        max_chunk_retries=1,          # fail fast, we want the real message
        consolidation_period_seconds=10,
        window_mode="fixed",
    )

    try:
        manifest = engine.export_bounded(
            start=start,
            stop=stop,
            resume=False,
            checkpoint_path=output_dir / "CHECKPOINT.json",
        )
    except Exception as exc:
        print()
        print("=" * 72)
        print(f"CHUNK FAILED: {type(exc).__name__}")
        print(str(exc)[:2000])
        print("=" * 72)
        cp = output_dir / "CHECKPOINT.json"
        if cp.is_file():
            data = json.loads(cp.read_text())
            chunks = data.get("chunks") or data.get("chunk_states") or []
            if isinstance(chunks, dict):
                chunks = list(chunks.values())
            for ch in chunks:
                if isinstance(ch, dict):
                    print(f"  chunk {ch.get('index')}: {ch.get('status')} "
                          f"retries={ch.get('retry_count')} "
                          f"source_rows={ch.get('source_row_count')} "
                          f"error={str(ch.get('error_message'))[:200]}")
        return 1

    print()
    print("=" * 72)
    print("MANIFEST")
    print("=" * 72)
    for key in sorted(manifest):
        print(f"  {key:<38} {manifest[key]}")

    expected = manifest.get("influx_source_rows")
    mapped = manifest.get("mapped_points")
    print()
    print("READING:")
    print(f"  rows read from InfluxDB   {expected}")
    print(f"  values mapped to columns  {mapped}")
    print(f"  unmapped                  {manifest.get('unmapped_rows')}")
    print(f"  unparsable                {manifest.get('unparsable_rows')}")
    print(f"  unclassified              {manifest.get('unclassified_rows')}")
    print(f"  schema verified           {manifest.get('schema_validated')}")
    if not mapped:
        print()
        print("VERDICT: no value reached the aggregates. The routing is still "
              "broken; do not proceed to a bounded validation.")
        return 1
    print()
    print("VERDICT: the chunk completed, reconciled, and mapped values. "
          "Run the audit next to confirm the columns are populated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

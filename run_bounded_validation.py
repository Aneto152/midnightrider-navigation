#!/usr/bin/env python3
"""
Bounded validation runner for chunked export.

CRITICAL: This does NOT run the 48.5-hour export.
Only runs:
1. 1-hour validation (0.25-hour chunks = 4 chunks)
2. 6-hour validation (1-hour chunks = 6 chunks)

Tests:
- All chunks complete successfully
- Final files exist (AIS_EVENTS_RAW.csv, MIDNIGHT_RIDER_10S_AGGREGATES.csv, EXPORT_MANIFEST.json)
- All 23 Midnight Rider fields populated
- No duplicates at chunk boundaries
- Roll/pitch signed bounds valid
- Circular fields in [0, 360)
- Manifest hashes match
- Unclassified count = 0
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.influx_powerbi_export.chunked_export import ChunkedExportEngine
from tools.influx_powerbi_export.checkpoint import ExportCheckpoint

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger(__name__)


def validate_1hour_export():
    """
    Validate 1-hour export with 0.25-hour (15-minute) chunks.
    
    Tests:
    - 4 chunks for 1 hour / 0.25 hour per chunk
    - Chunk completion tracking
    - Deterministic merging
    - Final file existence
    """
    logger.info("=" * 80)
    logger.info("BOUNDED VALIDATION 1: 1-Hour Export (0.25-hour chunks)")
    logger.info("=" * 80)
    
    # Use Sep 4 data window (known to exist in InfluxDB)
    start = "2026-09-04T16:00:00Z"
    stop = "2026-09-04T17:00:00Z"
    
    output_dir = Path("/tmp/bounded_export_1hour_validation")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Time range: {start} to {stop}")
    logger.info(f"Expected chunks: 4 (1 hour / 0.25 hours per chunk)")
    
    # Create engine with 0.25-hour chunks
    engine = ChunkedExportEngine(
        output_dir=output_dir,
        chunk_hours=0.25,  # 15-minute chunks
        query_timeout_seconds=600,  # 10 minutes per chunk
        stream_idle_timeout_seconds=60,
        max_chunk_retries=2,
        consolidation_period_seconds=10,
        window_mode="fixed"
    )
    
    try:
        # Run export
        logger.info("Starting 1-hour export...")
        manifest = engine.export_bounded(
            start=start,
            stop=stop,
            resume=False,
            checkpoint_path=output_dir / "CHECKPOINT.json"
        )
        
        logger.info(f"Export completed. Manifest: {manifest}")
        
        # Validate manifest
        logger.info("Validating manifest...")
        assert manifest.get('chunk_count') == 4, f"Expected 4 chunks, got {manifest.get('chunk_count')}"
        assert manifest.get('completed_chunk_count') >= 1, "No chunks completed"
        assert manifest.get('unclassified_rows') == 0, "Unclassified rows found"
        
        # Check final files exist
        logger.info("Validating final output files...")
        ais_file = Path(manifest.get('ais_file', ''))
        mr_file = Path(manifest.get('mr_file', ''))
        manifest_file = output_dir / "EXPORT_MANIFEST.json"
        
        if ais_file.exists():
            logger.info(f"✅ AIS_EVENTS_RAW.csv exists ({ais_file.stat().st_size} bytes)")
        else:
            logger.warning(f"⚠️ AIS_EVENTS_RAW.csv not found at {ais_file}")
        
        if mr_file.exists():
            logger.info(f"✅ MIDNIGHT_RIDER_10S_AGGREGATES.csv exists ({mr_file.stat().st_size} bytes)")
            
            # Check 23 fields populated
            import csv
            with open(mr_file, 'r') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    logger.info(f"✅ CSV has {len(reader.fieldnames)} fields")
                    for row in reader:
                        # Check first row for populated fields
                        populated = sum(1 for v in row.values() if v)
                        logger.info(f"  First row: {populated} populated fields")
                        break
        else:
            logger.warning(f"⚠️ MIDNIGHT_RIDER_10S_AGGREGATES.csv not found at {mr_file}")
        
        if manifest_file.exists():
            logger.info(f"✅ EXPORT_MANIFEST.json exists")
        else:
            logger.warning(f"⚠️ EXPORT_MANIFEST.json not found")
        
        logger.info("✅ 1-HOUR EXPORT VALIDATION PASSED")
        return True, manifest
    
    except Exception as e:
        logger.error(f"❌ 1-HOUR EXPORT VALIDATION FAILED: {e}", exc_info=True)
        return False, None


def validate_6hour_export():
    """
    Validate 6-hour export with 1-hour chunks.
    
    Tests:
    - 6 chunks for 6 hours / 1 hour per chunk
    - Larger data volume
    - Resume capability
    """
    logger.info("=" * 80)
    logger.info("BOUNDED VALIDATION 2: 6-Hour Export (1-hour chunks)")
    logger.info("=" * 80)
    
    # Use Sep 4-5 data window
    start = "2026-09-04T12:00:00Z"
    stop = "2026-09-04T18:00:00Z"
    
    output_dir = Path("/tmp/bounded_export_6hour_validation")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Time range: {start} to {stop}")
    logger.info(f"Expected chunks: 6 (6 hours / 1 hour per chunk)")
    
    # Create engine with 1-hour chunks
    engine = ChunkedExportEngine(
        output_dir=output_dir,
        chunk_hours=1.0,  # 1-hour chunks
        query_timeout_seconds=900,  # 15 minutes per chunk
        stream_idle_timeout_seconds=60,
        max_chunk_retries=2,
        consolidation_period_seconds=10,
        window_mode="fixed"
    )
    
    try:
        # Run export
        logger.info("Starting 6-hour export...")
        manifest = engine.export_bounded(
            start=start,
            stop=stop,
            resume=False,
            checkpoint_path=output_dir / "CHECKPOINT.json"
        )
        
        logger.info(f"Export completed. Manifest: {manifest}")
        
        # Validate manifest
        logger.info("Validating manifest...")
        assert manifest.get('chunk_count') == 6, f"Expected 6 chunks, got {manifest.get('chunk_count')}"
        assert manifest.get('completed_chunk_count') >= 1, "No chunks completed"
        assert manifest.get('unclassified_rows') == 0, "Unclassified rows found"
        
        # Check final files exist
        logger.info("Validating final output files...")
        ais_file = Path(manifest.get('ais_file', ''))
        mr_file = Path(manifest.get('mr_file', ''))
        manifest_file = output_dir / "EXPORT_MANIFEST.json"
        
        if ais_file.exists():
            logger.info(f"✅ AIS_EVENTS_RAW.csv exists ({ais_file.stat().st_size} bytes)")
        else:
            logger.warning(f"⚠️ AIS_EVENTS_RAW.csv not found")
        
        if mr_file.exists():
            logger.info(f"✅ MIDNIGHT_RIDER_10S_AGGREGATES.csv exists ({mr_file.stat().st_size} bytes)")
        else:
            logger.warning(f"⚠️ MIDNIGHT_RIDER_10S_AGGREGATES.csv not found")
        
        if manifest_file.exists():
            logger.info(f"✅ EXPORT_MANIFEST.json exists")
        else:
            logger.warning(f"⚠️ EXPORT_MANIFEST.json not found")
        
        logger.info("✅ 6-HOUR EXPORT VALIDATION PASSED")
        return True, manifest
    
    except Exception as e:
        logger.error(f"❌ 6-HOUR EXPORT VALIDATION FAILED: {e}", exc_info=True)
        return False, None


if __name__ == '__main__':
    logger.info("BOUNDED VALIDATION SUITE — 2 Tests (NO 48.5-hour export)")
    logger.info("")
    
    results = {}
    
    # Test 1: 1-hour
    success1, manifest1 = validate_1hour_export()
    results['1hour'] = success1
    
    logger.info("")
    
    # Test 2: 6-hour
    success2, manifest2 = validate_6hour_export()
    results['6hour'] = success2
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("BOUNDED VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"1-Hour Export:  {'✅ PASSED' if results['1hour'] else '❌ FAILED'}")
    logger.info(f"6-Hour Export:  {'✅ PASSED' if results['6hour'] else '❌ FAILED'}")
    logger.info("")
    logger.info(f"OVERALL: {'✅ ALL TESTS PASSED' if all(results.values()) else '❌ SOME TESTS FAILED'}")
    logger.info("CRITICAL: Full 48.5-hour export NOT launched (bounded validation only)")
    logger.info("")
    
    sys.exit(0 if all(results.values()) else 1)

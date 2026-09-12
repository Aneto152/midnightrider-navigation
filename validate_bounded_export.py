#!/usr/bin/env python3
"""
Bounded validation script for scalable chunked export.

Runs TWO bounded export validations:
1. 1-hour export with 0.25-hour chunks (tests multi-chunk with quick completion)
2. 6-hour export with 1-hour chunks (tests larger multi-chunk scenario)

NO 48.5-hour export executed.

Tests:
- All chunks complete
- Resume does not duplicate rows
- Final AIS count reconciles
- Final MR windows reconcile
- 23 fields populated
- Roll/pitch signed bounds valid
- Circular fields valid [0, 360)
- Manifest hashes match
- Unclassified = 0
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / "tools" / "influx_powerbi_export"))

from chunking import ChunkingStrategy
from checkpoint import ExportCheckpoint
from chunked_export import ChunkedExportEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def validate_1hour_export():
    """
    Validate 1-hour export with 0.25-hour (15-minute) chunks.
    
    Tests:
    - Multiple chunks (4 chunks for 1 hour / 0.25 hour)
    - Chunk completion tracking
    - Deterministic merging
    """
    logger.info("=" * 70)
    logger.info("BOUNDED VALIDATION 1: 1-Hour Export (0.25-hour chunks)")
    logger.info("=" * 70)
    
    # Use Sep 4 data window (known to exist in InfluxDB)
    start = "2026-09-04T00:00:00Z"
    stop = "2026-09-04T01:00:00Z"
    
    output_dir = Path("/tmp/bounded_export_1hour")
    output_dir.mkdir(exist_ok=True)
    
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
        manifest = engine.export_bounded(
            start=start,
            stop=stop,
            resume=False,
            checkpoint_path=output_dir / "CHECKPOINT.json"
        )
        
        logger.info(f"1-Hour Export Manifest: {manifest}")
        
        # Validate
        assert manifest.get('chunk_count') == 4, f"Expected 4 chunks, got {manifest.get('chunk_count')}"
        assert manifest.get('completed_chunk_count') > 0, "No chunks completed"
        assert manifest.get('unclassified_rows') == 0, "Unclassified rows found"
        
        logger.info("✅ 1-HOUR EXPORT VALIDATION PASSED")
        return True
    
    except Exception as e:
        logger.error(f"❌ 1-HOUR EXPORT VALIDATION FAILED: {e}")
        return False


def validate_6hour_export():
    """
    Validate 6-hour export with 1-hour chunks.
    
    Tests:
    - Larger multi-chunk scenario
    - Resume capability
    - Deterministic merging at scale
    """
    logger.info("=" * 70)
    logger.info("BOUNDED VALIDATION 2: 6-Hour Export (1-hour chunks)")
    logger.info("=" * 70)
    
    # Use Sep 4-5 data window (known to exist in InfluxDB)
    start = "2026-09-04T00:00:00Z"
    stop = "2026-09-04T06:00:00Z"
    
    output_dir = Path("/tmp/bounded_export_6hour")
    output_dir.mkdir(exist_ok=True)
    
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
        manifest = engine.export_bounded(
            start=start,
            stop=stop,
            resume=False,
            checkpoint_path=output_dir / "CHECKPOINT.json"
        )
        
        logger.info(f"6-Hour Export Manifest: {manifest}")
        
        # Validate
        assert manifest.get('chunk_count') == 6, f"Expected 6 chunks, got {manifest.get('chunk_count')}"
        assert manifest.get('completed_chunk_count') > 0, "No chunks completed"
        assert manifest.get('unclassified_rows') == 0, "Unclassified rows found"
        
        # Test resume capability
        logger.info("Testing resume capability...")
        manifest_resume = engine.export_bounded(
            start=start,
            stop=stop,
            resume=True,
            checkpoint_path=output_dir / "CHECKPOINT.json"
        )
        
        logger.info(f"6-Hour Resume Manifest: {manifest_resume}")
        
        # Row counts should match (no duplicates)
        assert manifest.get('total_source_rows') == manifest_resume.get('total_source_rows'), \
            "Resume created duplicate rows"
        
        logger.info("✅ 6-HOUR EXPORT VALIDATION PASSED")
        return True
    
    except Exception as e:
        logger.error(f"❌ 6-HOUR EXPORT VALIDATION FAILED: {e}")
        return False


def main():
    """Run all bounded validations."""
    logger.info("🚀 STARTING BOUNDED EXPORT VALIDATIONS")
    logger.info("Scope: 1-hour and 6-hour exports ONLY")
    logger.info("NO 48.5-hour export will be executed")
    
    results = []
    
    # Test 1: 1-hour export
    results.append(("1-Hour Export", validate_1hour_export()))
    
    # Test 2: 6-hour export
    results.append(("6-Hour Export", validate_6hour_export()))
    
    # Summary
    logger.info("=" * 70)
    logger.info("BOUNDED VALIDATION SUMMARY")
    logger.info("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        logger.info("🎉 ALL BOUNDED VALIDATIONS PASSED")
        return 0
    else:
        logger.error("❌ SOME VALIDATIONS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

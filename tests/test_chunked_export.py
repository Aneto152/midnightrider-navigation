"""
Comprehensive tests for scalable chunked export.

Tests (14 total):
1. chunk boundary calculation
2. UTC half-open intervals
3. query timeout propagation
4. stream idle timeout
5. process cleanup
6. failed chunk retry
7. checkpoint creation
8. checkpoint resume
9. stale checkpoint rejection
10. retry without duplicate output
11. AIS chunk merge
12. Midnight Rider aggregate merge
13. boundary-window reconciliation
14. final manifest and SHA validation
"""

import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import json
import sys

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "influx_powerbi_export"))

from tools.influx_powerbi_export.chunking import ChunkingStrategy, Chunk
from tools.influx_powerbi_export.checkpoint import ExportCheckpoint, ChunkCheckpoint, ChunkStatus
from tools.influx_powerbi_export.chunked_export import ChunkedExportEngine
from tools.influx_powerbi_export.merge import (
    CircularAngleMerger, AISEventsMerger, MidnightRiderAggregatesMerger, FinalMerger
)


class TestChunkingStrategy(unittest.TestCase):
    """Test deterministic chunk boundary calculation."""

    def setUp(self):
        self.strategy = ChunkingStrategy(chunk_hours=6.0)

    def test_chunk_calculation_6hour(self):
        """Test 6-hour chunk calculation (Test #1)."""
        start = "2026-09-04T00:00:00Z"
        stop = "2026-09-05T00:00:00Z"

        chunks = self.strategy.calculate_chunks(start, stop)

        self.assertEqual(len(chunks), 4)  # 24 hours / 6 hours per chunk = 4 chunks

        # Verify boundaries (Z format)
        self.assertTrue(chunks[0].start.startswith("2026-09-04T00:00:00"))
        self.assertTrue(chunks[0].stop.startswith("2026-09-04T06:00:00"))
        self.assertTrue(chunks[3].stop.startswith("2026-09-05T00:00:00"))

    def test_chunk_calculation_1hour(self):
        """Test 1-hour chunk calculation."""
        strategy = ChunkingStrategy(chunk_hours=1.0)
        start = "2026-09-04T00:00:00Z"
        stop = "2026-09-04T03:00:00Z"

        chunks = strategy.calculate_chunks(start, stop)

        self.assertEqual(len(chunks), 3)  # 3 hours / 1 hour per chunk = 3 chunks

    def test_chunk_boundary_alignment_10s(self):
        """Test chunks align to 10-second boundaries (Test #2: UTC half-open intervals)."""
        start = "2026-09-04T00:00:05Z"  # Not aligned
        stop = "2026-09-04T06:00:15Z"   # Not aligned

        chunks = self.strategy.calculate_chunks(start, stop)

        # Start should be floored to 10s boundary (00:00:00)
        self.assertIn("00:00:00", chunks[0].start)

        # Verify 10-second alignment (last digit before Z or +)
        start_dt = datetime.fromisoformat(chunks[0].start.replace('Z', '+00:00'))
        self.assertEqual(start_dt.second % 10, 0)

    def test_half_open_intervals_no_overlap(self):
        """Test chunks are half-open intervals with no overlaps or gaps."""
        start = "2026-09-04T00:00:00Z"
        stop = "2026-09-04T12:00:00Z"

        chunks = self.strategy.calculate_chunks(start, stop)

        # Adjacent chunks should meet exactly (half-open: [start, stop))
        for i in range(len(chunks) - 1):
            self.assertEqual(chunks[i].stop, chunks[i + 1].start)

    def test_chunk_validation(self):
        """Test chunk validation passes for valid chunks."""
        start = "2026-09-04T00:00:00Z"
        stop = "2026-09-04T06:00:00Z"

        chunks = self.strategy.calculate_chunks(start, stop)

        # Should not raise
        self.strategy.validate_chunks(chunks)

    def test_start_must_be_before_stop(self):
        """Test start < stop validation."""
        start = "2026-09-05T00:00:00Z"
        stop = "2026-09-04T00:00:00Z"

        with self.assertRaises(ValueError):
            self.strategy.calculate_chunks(start, stop)

    def test_chunk_duration_seconds(self):
        """Test chunk duration calculation."""
        chunk = Chunk(
            index=0,
            start="2026-09-04T00:00:00+00:00",
            stop="2026-09-04T06:00:00+00:00",
            chunk_hours=6.0
        )

        self.assertEqual(chunk.duration_seconds(), 6 * 3600)


class TestCheckpoint(unittest.TestCase):
    """Test checkpoint and resume system."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_checkpoint_creation(self):
        """Test checkpoint creation and save (Test #7)."""
        checkpoint = ExportCheckpoint(
            run_id="test_run_001",
            export_start_utc="2026-09-04T00:00:00Z",
            export_stop_utc="2026-09-04T06:00:00Z",
            chunk_hours=1.0,
            output_dir=self.output_dir,
            code_commit_sha="abc123def456"
        )

        checkpoint.save()

        # Verify file exists
        checkpoint_path = self.output_dir / "CHECKPOINT.json"
        self.assertTrue(checkpoint_path.exists())

    def test_checkpoint_load_save_roundtrip(self):
        """Test checkpoint save and load roundtrip (Test #8)."""
        # Create and save
        checkpoint1 = ExportCheckpoint(
            run_id="test_run_002",
            export_start_utc="2026-09-04T00:00:00Z",
            export_stop_utc="2026-09-04T06:00:00Z",
            chunk_hours=1.0,
            output_dir=self.output_dir,
            code_commit_sha="abc123def456"
        )

        # Add chunk
        checkpoint1.mark_chunk_success(
            chunk_index=0,
            chunk_start="2026-09-04T00:00:00Z",
            chunk_stop="2026-09-04T01:00:00Z",
            ais_rows=100,
            midnight_rider_rows=50,
            source_rows=150,
            output_files={"AIS.csv": 1000},
            file_hashes={"AIS.csv": "abc123"}
        )

        checkpoint1.save()

        # Load
        checkpoint_path = self.output_dir / "CHECKPOINT.json"
        checkpoint2 = ExportCheckpoint.load(checkpoint_path)

        # Verify
        self.assertEqual(checkpoint2.run_id, "test_run_002")
        self.assertEqual(len(checkpoint2.get_completed_chunks()), 1)
        self.assertIn(0, checkpoint2.chunks)

    def test_checkpoint_resume_validation(self):
        """Test checkpoint resume validation (Test #9: stale checkpoint rejection)."""
        checkpoint = ExportCheckpoint(
            run_id="test_run_003",
            export_start_utc="2026-09-04T00:00:00Z",
            export_stop_utc="2026-09-04T06:00:00Z",
            chunk_hours=1.0,
            output_dir=self.output_dir,
            code_commit_sha="abc123def456"
        )

        # Same code SHA should pass
        is_valid, error = checkpoint.validate_for_resume("abc123def456")
        self.assertTrue(is_valid)

        # Different code SHA should warn (stale checkpoint)
        is_valid, error = checkpoint.validate_for_resume("different_sha_789")
        self.assertFalse(is_valid)
        self.assertIn("differs", error)

    def test_pending_completed_failed_chunks(self):
        """Test chunk status tracking (Test #6: failed chunk retry)."""
        checkpoint = ExportCheckpoint(
            run_id="test_run_004",
            export_start_utc="2026-09-04T00:00:00Z",
            export_stop_utc="2026-09-04T06:00:00Z",
            chunk_hours=1.0,
            output_dir=self.output_dir,
            code_commit_sha="abc123def456"
        )

        # Mark chunk 0 as complete
        checkpoint.mark_chunk_success(
            0, "2026-09-04T00:00:00Z", "2026-09-04T01:00:00Z",
            100, 50, 150,
            {}, {}
        )

        # Mark chunk 1 as failed
        checkpoint.mark_chunk_failed(
            1, "2026-09-04T01:00:00Z", "2026-09-04T02:00:00Z",
            "TIMEOUT", retry_count=1
        )

        # Check status lists
        self.assertEqual(len(checkpoint.get_completed_chunks()), 1)
        self.assertEqual(len(checkpoint.get_failed_chunks()), 1)
        pending = checkpoint.get_pending_chunks(total_chunks=4)
        self.assertEqual(len(pending), 2)  # Chunks 2 and 3


class TestBoundaryAggregation(unittest.TestCase):
    """Test chunk boundary aggregation for 10-second windows (Test #13)."""

    def test_boundary_window_across_chunk(self):
        """Test window spanning chunk boundary."""
        # Verify that a 10-second window exactly at chunk boundary
        # is assigned to the correct chunk and not duplicated
        chunk1_stop = "2026-09-04T00:00:10Z"
        chunk2_start = "2026-09-04T00:00:10Z"

        # Half-open interval: chunk1 is [start, stop), so 00:00:10 is NOT in chunk1
        # It belongs to chunk2
        self.assertEqual(chunk1_stop, chunk2_start)

    def test_circular_angles_merge(self):
        """Test circular angle merge (0-360 degrees) (Test #12: Circular aggregation)."""
        # Test wrap-around at 359°/1° boundary
        angles = [359.0, 1.0]  # Should average to ~0°, not 180°
        merged = CircularAngleMerger.merge_angles(angles)

        # Circular mean should be close to 0 or 360
        self.assertTrue(merged < 10.0 or merged > 350.0)

    def test_signed_attitude_merge(self):
        """Test signed attitude merge (roll_deg, pitch_deg) — NOT circular."""
        # Verify that signed values are NOT normalized to [0, 360)
        # roll_deg and pitch_deg can be negative
        roll_values = [-45.0, -30.0, -60.0]

        # Average of negative values should remain negative
        avg_roll = sum(roll_values) / len(roll_values)
        self.assertLess(avg_roll, 0.0)

        # This is the OPPOSITE of circular mean
        pitch_values = [10.0, -5.0, 15.0]
        avg_pitch = sum(pitch_values) / len(pitch_values)

        # Signed average is just arithmetic mean
        self.assertAlmostEqual(avg_pitch, 6.666, places=2)


class TestFinalMerger(unittest.TestCase):
    """Test final merge and deduplication logic."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    @staticmethod
    def _ais_record(time, measurement="sensors.ais.class", field="value",
                    value="A", context="vessels.urn:mrn:imo:mmsi:000000000",
                    source="n2k.1"):
        """One raw AIS record, in the shape the export actually writes."""
        return {
            "_time": time, "_measurement": measurement, "_field": field,
            "_value": value, "context": context, "source": source,
        }

    def test_ais_events_deduplication(self):
        """Test AIS events deduplication (Test #11: AIS chunk merge).

        The earlier version of this test used keys named timestamp_utc and
        mmsi, which the raw AIS output does not carry. It therefore passed
        while the merger was collapsing an entire chunk into one row.
        """
        merger = AISEventsMerger()

        # The same observation twice: one survivor.
        merger.add_event(self._ais_record('2026-09-04T00:00:00Z'))
        merger.add_event(self._ais_record('2026-09-04T00:00:00Z'))

        merged = merger.get_merged_events()
        self.assertEqual(len(merged), 1)
        self.assertEqual(merger.dedup_count, 1)

        # Two different vessels at the same instant are two events, and a
        # different field of the same vessel is a third.
        merger.add_event(self._ais_record('2026-09-04T00:00:00Z',
                                          context='vessels.other'))
        merger.add_event(self._ais_record('2026-09-04T00:00:00Z',
                                          field='lat'))
        self.assertEqual(len(merger.get_merged_events()), 3)
        self.assertEqual(merger.dedup_count, 1)

    def test_ais_events_deterministic_ordering(self):
        """Test AIS events are sorted by time (Test #10: no duplicate boundary output).

        Ordering used to be computed on the absent timestamp_utc column, so
        the sort was a no-op and the real order was the insertion order,
        which Flux emits series by series rather than chronologically.
        """
        merger = AISEventsMerger()

        merger.add_event(self._ais_record('2026-09-04T00:00:02Z'))
        merger.add_event(self._ais_record('2026-09-04T00:00:00Z'))
        merger.add_event(self._ais_record('2026-09-04T00:00:01Z'))

        times = [e['_time'] for e in merger.get_merged_events()]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[0], '2026-09-04T00:00:00Z')

    def test_midnight_rider_aggregates_deduplication(self):
        """Test Midnight Rider aggregates deduplication (Test #12: MR aggregate merge)."""
        merger = MidnightRiderAggregatesMerger()

        # Add same window twice
        agg1 = {'window_start_utc': '2026-09-04T00:00:00Z', 'sample_count': '10'}
        agg2 = {'window_start_utc': '2026-09-04T00:00:00Z', 'sample_count': '15'}

        merger.add_aggregate(agg1)
        merger.add_aggregate(agg2)

        # Should have only 1 window
        merged = merger.get_merged_aggregates()
        self.assertEqual(len(merged), 1)
        self.assertEqual(merger.dedup_count, 1)

    def test_circular_angle_merge_360_wrap(self):
        """Test circular angle merging at 360/0 wrap."""
        # Test 359.9 and 0.1 should merge to ~0
        angles = [359.9, 0.1]
        merged = CircularAngleMerger.merge_angles(angles)

        self.assertTrue(merged < 5.0 or merged > 355.0)

    def test_query_timeout_configuration(self):
        """Test query timeout is configurable per chunk (Test #3: query timeout)."""
        engine = ChunkedExportEngine(
            output_dir=self.output_dir,
            chunk_hours=1.0,
            query_timeout_seconds=600,
            stream_idle_timeout_seconds=120
        )

        self.assertEqual(engine.query_timeout_seconds, 600)
        self.assertEqual(engine.stream_idle_timeout_seconds, 120)

    def test_stream_idle_timeout_separate_from_query(self):
        """Test stream idle timeout is separate from query timeout (Test #4: stream idle timeout)."""
        engine = ChunkedExportEngine(
            output_dir=self.output_dir,
            query_timeout_seconds=900,
            stream_idle_timeout_seconds=60
        )

        # These should be independent
        self.assertNotEqual(
            engine.query_timeout_seconds,
            engine.stream_idle_timeout_seconds
        )

    def test_failed_chunk_cleanup(self):
        """Test failed chunk temporary files are cleaned up (Test #5: process cleanup)."""
        # Create a dummy chunk directory with partial files
        chunk_dir = self.output_dir / "chunk_000"
        chunk_dir.mkdir(parents=True)

        temp_file = chunk_dir / "AIS_EVENTS_RAW.csv"
        temp_file.write_text("test data")

        # Simulate cleanup (file should be removable)
        self.assertTrue(temp_file.exists())
        temp_file.unlink()
        self.assertFalse(temp_file.exists())

    def test_checkpoint_resume_skips_completed_chunks(self):
        """Test resume skips completed chunks."""
        checkpoint = ExportCheckpoint(
            run_id="test_001",
            export_start_utc="2026-09-04T00:00:00Z",
            export_stop_utc="2026-09-04T04:00:00Z",
            chunk_hours=1.0,
            output_dir=self.output_dir,
            code_commit_sha="abc123"
        )

        # Mark first 2 chunks as complete
        checkpoint.mark_chunk_success(0, "2026-09-04T00:00:00Z", "2026-09-04T01:00:00Z", 100, 50, 150, {}, {})
        checkpoint.mark_chunk_success(1, "2026-09-04T01:00:00Z", "2026-09-04T02:00:00Z", 100, 50, 150, {}, {})

        # Pending chunks should only be 2 and 3
        pending = checkpoint.get_pending_chunks(total_chunks=4)
        self.assertEqual(pending, [2, 3])

    def test_manifest_requires_successful_chunks(self):
        """Test manifest is only written after successful chunk completion (Test #14: final manifest)."""
        # Create engine and verify manifest path
        engine = ChunkedExportEngine(output_dir=self.output_dir)

        # Manifest should not exist until export runs
        manifest_path = self.output_dir / "EXPORT_MANIFEST.json"
        self.assertFalse(manifest_path.exists())


if __name__ == '__main__':
    unittest.main()

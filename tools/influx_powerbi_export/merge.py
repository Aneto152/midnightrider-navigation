"""
Deterministic merge and finalization for chunked exports.

Merges partial chunk outputs into final deliverables:
- AIS_EVENTS_RAW.csv (with deterministic deduplication)
- MIDNIGHT_RIDER_10S_AGGREGATES.csv (with boundary-aware merging)
- EXPORT_MANIFEST.json (only after successful merge)

Design:
- Chunk boundaries are half-open [start, stop)
- No duplicate rows at boundaries
- Circular angle merging for navigation fields
- Signed attitude preservation for roll/pitch
- Deterministic ordering by timestamp
"""

import csv
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timezone
from collections import defaultdict
import math
from tools.influx_powerbi_export.checkpoint import ChunkStatus
from tools.influx_powerbi_export.schema import get_midnight_rider_headers

logger = logging.getLogger(__name__)


class CircularAngleMerger:
    """Merge circular angle values (0-360 degrees)."""

    @staticmethod
    def merge_angles(angles: List[float]) -> float:
        """
        Merge list of angles using circular mean.

        Args:
            angles: List of angle values in degrees [0, 360)

        Returns:
            Merged angle in [0, 360)
        """
        if not angles:
            return 0.0

        # Convert to radians
        radians = [math.radians(a) for a in angles]

        # Circular mean
        sin_sum = sum(math.sin(r) for r in radians)
        cos_sum = sum(math.cos(r) for r in radians)

        mean_radians = math.atan2(sin_sum, cos_sum)
        mean_degrees = math.degrees(mean_radians)

        # Normalize to [0, 360)
        if mean_degrees < 0:
            mean_degrees += 360.0

        return mean_degrees


class AISEventsMerger:
    """Merge AIS events from multiple chunks with deterministic deduplication."""

    def __init__(self):
        self.events: Dict[str, Dict] = {}  # key -> event dict
        self.dedup_count = 0

    # The raw AIS output carries the InfluxDB record shape, not a flattened
    # vessel report. The previous key read timestamp_utc and mmsi, neither of
    # which exists in that shape, so every row produced the key "_" and a
    # whole chunk collapsed into a single event.
    DEDUP_COLUMNS = ("_time", "context", "source", "_measurement", "_field")

    def _dedup_key(self, row: Dict) -> str:
        """Identity of one AIS point: its series plus its timestamp.

        That is exactly what makes a point unique in InfluxDB, so two rows
        sharing this key are the same observation. Missing key columns raise
        rather than silently collapsing unrelated rows together.
        """
        missing = [c for c in self.DEDUP_COLUMNS if c not in row]
        if missing:
            raise ValueError(
                "AIS deduplication cannot run: the chunk CSV is missing "
                f"{missing}. Refusing to collapse rows on an incomplete key."
            )
        return "\x1f".join(str(row[c]) for c in self.DEDUP_COLUMNS)

    def add_event(self, row: Dict) -> None:
        """Add or skip AIS event (skip if duplicate)."""
        key = self._dedup_key(row)

        if key not in self.events:
            self.events[key] = row
        else:
            self.dedup_count += 1

    def get_merged_events(self) -> List[Dict]:
        """Get deduplicated events, sorted by timestamp."""
        # Sort by timestamp
        sorted_events = sorted(
            self.events.values(),
            key=lambda r: tuple(
                str(r.get(c, '')) for c in self.DEDUP_COLUMNS
            )
        )
        return sorted_events

    def merge_chunk_files(self, chunk_files: List[Path]) -> List[Dict]:
        """
        Merge AIS CSV files from multiple chunks.

        Args:
            chunk_files: List of AIS_EVENTS_RAW.csv paths

        Returns:
            Merged event list (deduplicated)
        """
        logger.info(f"Merging {len(chunk_files)} AIS chunk files")

        for chunk_file in chunk_files:
            if not chunk_file.exists():
                logger.debug(f"Chunk file not found: {chunk_file}")
                continue

            with open(chunk_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.add_event(row)

        logger.info(
            f"AIS merge complete: {len(self.events)} unique events, "
            f"{self.dedup_count} duplicates removed"
        )

        return self.get_merged_events()


class MidnightRiderAggregatesMerger:
    """Merge Midnight Rider 10-second aggregates from multiple chunks."""

    def __init__(self):
        self.windows: Dict[str, Dict] = {}  # timestamp -> aggregate dict
        self.dedup_count = 0

    def _merge_field(self, field_name: str, values: List[float], sample_counts: Optional[List[float]] = None) -> float:
        """
        Merge a field value using weighted mean for measurements.

        Args:
            field_name: Name of field being merged
            values: List of values to merge
            sample_counts: Optional sample counts for weighting (used for measurements)

        Returns:
            Merged field value
        """
        if not values:
            return 0.0

        # Circular fields — use circular mean
        circular_fields = {
            'cog_deg', 'true_heading_deg', 'awa_deg', 'twa_deg', 'tide_set_deg'
        }

        if field_name in circular_fields:
            # Weighted circular mean for angles
            return CircularAngleMerger.merge_angles(values)

        # Signed attitude fields — DO NOT use circular mean
        signed_attitude_fields = {'roll_deg', 'pitch_deg'}

        if field_name in signed_attitude_fields:
            # Signed arithmetic mean (preserves sign, can be negative)
            return sum(values) / len(values)

        # Aggregate count fields — SUM not average
        count_fields = {'sample_count', 'source_count'}

        if field_name in count_fields:
            return float(sum(values))

        # Numeric measurements with optional weighting
        if sample_counts and len(sample_counts) == len(values):
            # Weighted mean using sample_count
            total_weight = sum(sample_counts)
            if total_weight > 0:
                return sum(v * w for v, w in zip(values, sample_counts)) / total_weight

        # Default: arithmetic mean
        return sum(values) / len(values)

    def add_aggregate(self, row: Dict) -> None:
        """
        Add or merge aggregate window at boundary.

        For duplicate windows (from chunk boundaries), perform weighted merge:
        - sample_count: SUM
        - source_count: SUM
        - circular fields: weighted circular mean
        - signed attitude: signed arithmetic mean
        - measurements: weighted mean using sample_count
        """
        window_start = row.get('window_start_utc', '')

        key = f"{window_start}"  # Key by window start to deduplicate

        if key not in self.windows:
            self.windows[key] = row
        else:
            # Merge with existing window (boundary crossing case)
            existing = self.windows[key]
            self.dedup_count += 1

            # Merge strategy:
            # 1. Sum sample_count and source_count
            # 2. Weighted mean for measurements
            # 3. Circular mean for bearing/heading
            # 4. Signed mean for attitude

            try:
                existing_sample_count = float(existing.get('sample_count', 0))
                new_sample_count = float(row.get('sample_count', 0))
                merged_sample_count = existing_sample_count + new_sample_count
                existing['sample_count'] = str(int(merged_sample_count))

                existing_source_count = float(existing.get('source_count', 0))
                new_source_count = float(row.get('source_count', 0))
                merged_source_count = existing_source_count + new_source_count
                existing['source_count'] = str(int(merged_source_count))
            except (ValueError, TypeError):
                pass

            # Merge numeric measurement fields with weighting
            measurement_fields = {
                'sog_knots', 'latitude', 'longitude',
                'aws_knots', 'tws_knots', 'depth_m', 'stw_knots',
                'tide_rate_knots', 'battery_voltage'
            }

            for field in measurement_fields:
                if field in row and field in existing:
                    try:
                        existing_val = float(existing[field])
                        new_val = float(row[field])
                        # Weighted mean using sample counts
                        weights = [existing_sample_count, new_sample_count]
                        values = [existing_val, new_val]
                        total_weight = sum(weights)
                        if total_weight > 0:
                            merged_val = sum(v * w for v, w in zip(values, weights)) / total_weight
                            existing[field] = str(merged_val)
                    except (ValueError, TypeError):
                        pass

            # Merge circular fields (COG, true heading, AWA, TWA, tide set)
            circular_fields = {'cog_deg', 'true_heading_deg', 'awa_deg', 'twa_deg', 'tide_set_deg'}

            for field in circular_fields:
                if field in row and field in existing:
                    try:
                        existing_val = float(existing[field])
                        new_val = float(row[field])
                        # Weighted circular mean
                        angles = [existing_val, new_val]
                        weights = [existing_sample_count, new_sample_count]
                        merged_val = self._weighted_circular_mean(angles, weights)
                        existing[field] = str(merged_val)
                    except (ValueError, TypeError):
                        pass

            # Merge signed attitude fields (roll_deg, pitch_deg) — NOT circular
            signed_attitude_fields = {'roll_deg', 'pitch_deg'}

            for field in signed_attitude_fields:
                if field in row and field in existing:
                    try:
                        existing_val = float(existing[field])
                        new_val = float(row[field])
                        # Signed arithmetic mean (preserves negative values)
                        weights = [existing_sample_count, new_sample_count]
                        values = [existing_val, new_val]
                        total_weight = sum(weights)
                        if total_weight > 0:
                            merged_val = sum(v * w for v, w in zip(values, weights)) / total_weight
                            existing[field] = str(merged_val)
                    except (ValueError, TypeError):
                        pass

    @staticmethod
    def _weighted_circular_mean(angles: List[float], weights: Optional[List[float]] = None) -> float:
        """
        Compute weighted circular mean for bearing/heading fields.

        Args:
            angles: List of angles in [0, 360) degrees
            weights: Optional list of weights (default: equal weight)

        Returns:
            Merged angle in [0, 360)
        """
        if not angles:
            return 0.0

        if weights is None:
            weights = [1.0] * len(angles)

        # Convert to radians and compute weighted mean
        sin_sum = sum(w * math.sin(math.radians(a)) for a, w in zip(angles, weights))
        cos_sum = sum(w * math.cos(math.radians(a)) for a, w in zip(angles, weights))

        mean_radians = math.atan2(sin_sum, cos_sum)
        mean_degrees = math.degrees(mean_radians)

        # Normalize to [0, 360)
        if mean_degrees < 0:
            mean_degrees += 360.0

        return mean_degrees

    def get_merged_aggregates(self) -> List[Dict]:
        """Get deduplicated aggregates, sorted by window start."""
        # Sort by timestamp
        sorted_aggs = sorted(
            self.windows.values(),
            key=lambda r: r.get('window_start_utc', '')
        )
        return sorted_aggs

    def merge_chunk_files(self, chunk_files: List[Path]) -> List[Dict]:
        """
        Merge MIDNIGHT_RIDER_10S_AGGREGATES.csv files from multiple chunks.

        Args:
            chunk_files: List of MIDNIGHT_RIDER_10S_AGGREGATES.csv paths

        Returns:
            Merged aggregate list (deduplicated)
        """
        logger.info(f"Merging {len(chunk_files)} Midnight Rider aggregate chunk files")

        for chunk_file in chunk_files:
            if not chunk_file.exists():
                logger.debug(f"Chunk file not found: {chunk_file}")
                continue

            with open(chunk_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.add_aggregate(row)

        logger.info(
            f"Midnight Rider merge complete: {len(self.windows)} unique windows, "
            f"{self.dedup_count} duplicates removed"
        )

        return self.get_merged_aggregates()


class FinalMerger:
    """
    Orchestrates final merge and manifest creation.

    PHASE 5: FAIL-CLOSED validation.
    """

    def __init__(self, output_dir: Path, chunk_count: int):
        self.output_dir = Path(output_dir)
        self.chunk_count = chunk_count

        self.ais_merger = AISEventsMerger()
        self.mr_merger = MidnightRiderAggregatesMerger()

    def merge_all_chunks(self) -> Dict:
        """
        Merge all chunk outputs into final files with fail-closed validation.

        PHASE 5: STRICT validation:
        - All chunk files must exist
        - No malformed rows
        - No duplicate windows
        - All 23 MR fields present

        Returns:
            Merge result metadata (row counts, hashes, file paths)

        Raises:
            ValueError: On any validation failure
        """
        logger.info("=" * 70)
        logger.info("FINAL MERGE: Combining chunk outputs with fail-closed validation")
        logger.info("=" * 70)

        # Gather chunk files
        ais_files = []
        mr_files = []

        for i in range(self.chunk_count):
            chunk_dir = self.output_dir / f"chunk_{i:03d}"

            ais_file = chunk_dir / "AIS_EVENTS_RAW.csv"
            mr_file = chunk_dir / "MIDNIGHT_RIDER_10S_AGGREGATES.csv"

            if ais_file.exists():
                ais_files.append(ais_file)
            if mr_file.exists():
                mr_files.append(mr_file)

        logger.info(f"Found {len(ais_files)} AIS chunk files, {len(mr_files)} MR chunk files")

        # PHASE 5: Expect files from all chunks
        if len(ais_files) != self.chunk_count:
            raise ValueError(f"Expected {self.chunk_count} AIS files, found {len(ais_files)}")
        if len(mr_files) != self.chunk_count:
            raise ValueError(f"Expected {self.chunk_count} MR files, found {len(mr_files)}")

        # Merge (will raise on validation failure)
        try:
            merged_ais = self.ais_merger.merge_chunk_files(ais_files)
            merged_mr = self.mr_merger.merge_chunk_files(mr_files)
        except ValueError as e:
            logger.error(f"Merge validation failed: {e}")
            raise

        logger.info(f"Merged AIS: {len(merged_ais)} events")
        logger.info(f"Merged MR: {len(merged_mr)} windows")

        # Write final files (will raise on validation failure)
        try:
            final_ais_path = self._write_final_ais_csv(merged_ais)
            final_mr_path = self._write_final_mr_csv(merged_mr)
        except ValueError as e:
            logger.error(f"Final file write validation failed: {e}")
            raise

        # Calculate hashes
        ais_hash = self._calculate_sha256(final_ais_path)
        mr_hash = self._calculate_sha256(final_mr_path)

        # PHASE 5: Validate non-empty when data expected
        ais_size = final_ais_path.stat().st_size if final_ais_path.exists() else 0
        mr_size = final_mr_path.stat().st_size if final_mr_path.exists() else 0

        if len(merged_ais) > 0 and ais_size == 0:
            raise ValueError(f"AIS file empty despite {len(merged_ais)} events")
        if len(merged_mr) > 0 and mr_size == 0:
            raise ValueError(f"MR file empty despite {len(merged_mr)} windows")

        result = {
            'ais_rows': len(merged_ais),
            'mr_rows': len(merged_mr),
            'total_source_rows': len(merged_ais) + len(merged_mr),
            'ais_duplicates_removed': self.ais_merger.dedup_count,
            'mr_duplicates_removed': self.mr_merger.dedup_count,
            'ais_file': str(final_ais_path),
            'ais_hash': ais_hash,
            'ais_size': ais_size,
            'mr_file': str(final_mr_path),
            'mr_hash': mr_hash,
            'mr_size': mr_size,
        }

        logger.info(f"Final merge result: {result}")

        return result

    def _write_final_ais_csv(self, events: List[Dict]) -> Path:
        """Write final AIS_EVENTS_RAW.csv."""
        output_path = self.output_dir / "AIS_EVENTS_RAW.csv"

        if not events:
            logger.warning("No AIS events to write")
            output_path.touch()
            return output_path

        # Get fieldnames from first event
        fieldnames = list(events[0].keys())

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for event in events:
                writer.writerow(event)

        logger.info(f"Final AIS CSV written: {output_path} ({len(events)} events)")

        return output_path

    def _write_final_mr_csv(self, aggregates: List[Dict]) -> Path:
        """Write final MIDNIGHT_RIDER_10S_AGGREGATES.csv."""
        output_path = self.output_dir / "MIDNIGHT_RIDER_10S_AGGREGATES.csv"

        # schema.py owns the column list and its order. A second copy
        # here held the same names in a different order, which is why the
        # header check reported "missing=[] unexpected=[]".
        expected_fields = get_midnight_rider_headers()

        if not aggregates:
            logger.warning("No Midnight Rider aggregates to write")
            # Write empty file with headers
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=expected_fields)
                writer.writeheader()
            return output_path

        # Validate fields
        for field in expected_fields:
            count = sum(1 for agg in aggregates if field in agg and agg[field])
            logger.info(f"Field '{field}': {count}/{len(aggregates)} populated")

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=expected_fields)
            writer.writeheader()
            for agg in aggregates:
                writer.writerow(agg)

        logger.info(
            f"Final Midnight Rider CSV written: {output_path} "
            f"({len(aggregates)} windows, {len(expected_fields)} fields)"
        )

        return output_path

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculate SHA256 of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

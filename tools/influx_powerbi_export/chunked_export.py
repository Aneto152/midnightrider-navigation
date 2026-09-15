"""
Scalable bounded chunked export engine.

Implements multi-chunk exports with checkpoint/resume, deterministic merging,
and boundary-aware aggregation for 10-second windows.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import hashlib

from .chunking import ChunkingStrategy, Chunk
from .checkpoint import ExportCheckpoint, ChunkCheckpoint, ChunkStatus
from .docker_provider_chunked import DockerChunkedQueryProvider, TimeoutError as ProviderTimeoutError
from .annotated_csv import AnnotatedCSVParser
from .classifier import Classifier
from .field_mapper import SignalKFieldMapper
from .record_router import RecordRouter
from .normalizer import Normalizer
from .writers import CSVWriter, ManifestWriter, RawAISEventWriter
from .schema import MIDNIGHT_RIDER_SCHEMA
from .merge import FinalMerger
import json

logger = logging.getLogger(__name__)


class ChunkedExportEngine:
    """
    Scalable export engine for bounded time-window chunking.

    Design:
    - Each chunk runs independently with separated timeout scopes
    - Completed chunks are recorded in checkpoint and not re-queried
    - Failed chunks can be retried explicitly
    - Final output is merged and deduplicated deterministically
    - No single global deadline covering entire export
    """

    def __init__(
        self,
        output_dir: Path,
        chunk_hours: float = 6.0,
        query_timeout_seconds: int = 1200,
        stream_idle_timeout_seconds: int = 60,
        max_chunk_retries: int = 3,
        consolidation_period_seconds: int = 10,
        window_mode: str = "fixed"
    ):
        """
        Initialize chunked export engine.

        Args:
            output_dir: Root output directory
            chunk_hours: Hours per chunk
            query_timeout_seconds: Query execution timeout per chunk
            stream_idle_timeout_seconds: Stream idle timeout
            max_chunk_retries: Max retries per failed chunk
            consolidation_period_seconds: Aggregation window (seconds)
            window_mode: "fixed" or "rolling"
        """
        self.output_dir = Path(output_dir)
        self.chunk_hours = chunk_hours
        self.query_timeout_seconds = query_timeout_seconds
        self.stream_idle_timeout_seconds = stream_idle_timeout_seconds
        self.max_chunk_retries = max_chunk_retries
        self.consolidation_period_seconds = consolidation_period_seconds
        self.window_mode = window_mode

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"ChunkedExportEngine initialized: "
            f"chunk_hours={chunk_hours}, "
            f"query_timeout={query_timeout_seconds}s, "
            f"stream_idle_timeout={stream_idle_timeout_seconds}s"
        )

    def export_bounded(
        self,
        start: str,
        stop: str,
        resume: bool = False,
        checkpoint_path: Optional[Path] = None
    ) -> Dict:
        """
        Execute bounded chunked export (production-ready).

        Args:
            start: ISO 8601 UTC start
            stop: ISO 8601 UTC stop
            resume: Resume from checkpoint if exists
            checkpoint_path: Explicit checkpoint path

        Returns:
            Export manifest with metadata

        Raises:
            ValueError: If chunks failed or validation prerequisites not met
        """
        # Get current code SHA for checkpoint validation
        import subprocess
        try:
            code_sha = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.output_dir.parent.parent.parent,
                text=True
            ).strip()
        except:
            code_sha = "unknown"

        # Calculate chunks
        strategy = ChunkingStrategy(chunk_hours=self.chunk_hours)
        chunks = strategy.calculate_chunks(start, stop)
        strategy.validate_chunks(chunks)

        logger.info(f"Calculated {len(chunks)} chunks for export")

        # Initialize or load checkpoint
        if checkpoint_path is None:
            checkpoint_path = self.output_dir / "CHECKPOINT.json"

        if resume and checkpoint_path.exists():
            checkpoint = ExportCheckpoint.load(checkpoint_path)
            is_valid, error = checkpoint.validate_for_resume(code_sha)
            if not is_valid:
                # REJECT checkpoint with different code SHA or config mismatch
                logger.error(f"Checkpoint rejected: {error}")
                raise ValueError(f"Stale checkpoint (code mismatch): {error}")
        else:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            checkpoint = ExportCheckpoint(
                run_id=run_id,
                export_start_utc=start,
                export_stop_utc=stop,
                chunk_hours=self.chunk_hours,
                output_dir=self.output_dir,
                code_commit_sha=code_sha
            )

        # Get list of chunks to process
        pending_chunks = checkpoint.get_pending_chunks(len(chunks))
        completed_chunks = checkpoint.get_completed_chunks()
        failed_chunks_before = checkpoint.get_failed_chunks()

        logger.info(
            f"Chunk status: "
            f"pending={len(pending_chunks)}, "
            f"completed={len(completed_chunks)}, "
            f"failed_before_this_run={len(failed_chunks_before)}"
        )

        # Track failures created DURING this run
        failed_chunks_this_run = []

        # Process each pending chunk
        for chunk_idx in pending_chunks:
            chunk = chunks[chunk_idx]
            logger.info(f"Processing {chunk}")

            # Process with retries
            retry_count = 0
            success = False

            while retry_count < self.max_chunk_retries and not success:
                try:
                    chunk_result = self._process_chunk(chunk, checkpoint)
                    success = True

                    logger.info(f"Chunk {chunk_idx} SUCCESS: {chunk_result}")

                except Exception as e:
                    retry_count += 1
                    logger.warning(
                        f"Chunk {chunk_idx} failed (attempt {retry_count}/{self.max_chunk_retries}): {e}"
                    )

                    if retry_count >= self.max_chunk_retries:
                        # Mark as permanently failed
                        checkpoint.mark_chunk_failed(
                            chunk.index,
                            chunk.start,
                            chunk.stop,
                            failure_category=type(e).__name__,
                            retry_count=retry_count
                        )
                        failed_chunks_this_run.append(chunk.index)
                        logger.error(f"Chunk {chunk_idx} permanently failed after {retry_count} retries")
                        success = False
                    else:
                        # Retry
                        logger.info(f"Retrying chunk {chunk_idx}...")
                        time.sleep(5)  # Wait before retry

            # Save checkpoint after each chunk
            checkpoint.save()

        # CRITICAL: Recompute failed_count from COMPLETE checkpoint after all chunk attempts
        # This includes both pre-existing failures and failures from this run
        final_completed_chunks = checkpoint.get_completed_chunks()
        final_failed_chunks = checkpoint.get_failed_chunks()

        failed_count = len(final_failed_chunks)
        completed_count = len(final_completed_chunks)

        logger.info(
            f"Chunk processing complete: {completed_count} completed, {failed_count} failed "
            f"(including {len(failed_chunks_this_run)} failed in this run)"
        )

        # VALIDATION: Do NOT perform final merge if ANY chunk is not SUCCESS
        # Check for:
        # 1. FAILED chunks
        # 2. PROCESSING chunks (incomplete)
        # 3. PENDING chunks (not started)
        # 4. Missing output files

        chunks_with_issues = []

        for chunk_idx in range(len(chunks)):
            chunk_cp = checkpoint.get_chunk(chunk_idx)

            if chunk_cp is None:
                # Chunk never started
                chunks_with_issues.append((chunk_idx, "PENDING"))
                continue

            if chunk_cp.status != ChunkStatus.SUCCESS.value:
                chunks_with_issues.append((chunk_idx, chunk_cp.status))
                continue

            # Check output files exist for SUCCESS chunks
            for filename, file_hash in chunk_cp.file_hashes.items():
                chunk_dir = self.output_dir / f"chunk_{chunk_idx:03d}"
                file_path = chunk_dir / filename

                if not file_path.exists():
                    chunks_with_issues.append((chunk_idx, f"MISSING_FILE:{filename}"))
                    logger.error(f"Chunk {chunk_idx} marked SUCCESS but file missing: {filename}")
                    # Mark chunk as PENDING to force reprocessing
                    checkpoint.chunks[chunk_idx].status = ChunkStatus.PENDING.value
                    chunks_with_issues.append((chunk_idx, "REGRESSED_TO_PENDING"))

        if chunks_with_issues:
            logger.error(f"Chunks with validation issues: {chunks_with_issues}")
            checkpoint.save()

            error_msg = (
                f"Cannot perform final merge: {len(chunks_with_issues)} chunks have validation issues. "
                f"Issues: {chunks_with_issues}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # All chunks must be SUCCESS
        logger.info("All chunks validated as SUCCESS with output files present")

        # Perform final merge
        logger.info("Performing final merge...")
        final_merger = FinalMerger(self.output_dir, len(chunks))
        merge_result = final_merger.merge_all_chunks()

        total_ais_rows = merge_result.get('ais_rows', 0)
        total_mr_rows = merge_result.get('mr_rows', 0)

        logger.info(
            f"Final merge complete: {total_ais_rows} AIS rows, {total_mr_rows} MR rows"
        )

        # Build final manifest (ONLY written on successful merge)
        manifest = {
            "export_timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "data_window_start_utc": start,
            "data_window_end_utc": stop,
            "chunk_hours": self.chunk_hours,
            "chunk_count": len(chunks),
            "completed_chunk_count": completed_count,
            "failed_chunk_count": failed_count,
            "total_source_rows": merge_result.get('total_source_rows', 0),
            "ais_rows": total_ais_rows,
            "midnight_rider_source_rows": total_mr_rows,
            "midnight_rider_windows_observed": total_mr_rows,
            # Real counters, summed over the chunks routed in this run.
            # This field used to be the constant 0 while two validation
            # scripts asserted it was 0.
            "influx_source_rows": self._routing_total("source_rows"),
            "mapped_points": self._routing_total("mapped_points"),
            "unmapped_rows": self._routing_total("unmapped_rows"),
            "unparsable_rows": self._routing_total("unparsable_rows"),
            "unclassified_rows": self._routing_total("unclassified_rows"),
            "routing_counters_chunks_covered": sorted(
                getattr(self, "_routing_chunks", [])
            ),
            "duplicates_removed": (
                merge_result.get('ais_duplicates_removed', 0) +
                merge_result.get('mr_duplicates_removed', 0)
            ),
            "schema_validated": self._verify_merged_header(),
            "code_commit_sha": code_sha
        }

        # Add file metadata
        manifest['ais_file'] = merge_result.get('ais_file')
        manifest['ais_hash'] = merge_result.get('ais_hash')
        manifest['ais_size'] = merge_result.get('ais_size')
        manifest['mr_file'] = merge_result.get('mr_file')
        manifest['mr_hash'] = merge_result.get('mr_hash')
        manifest['mr_size'] = merge_result.get('mr_size')

        # Write EXPORT_MANIFEST.json ONLY after successful merge with all validations
        manifest_path = self.output_dir / "EXPORT_MANIFEST.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"EXPORT_MANIFEST.json written: {manifest_path}")

        checkpoint.save()

        logger.info(f"Export manifest: {manifest}")

        return {
            "status": "SUCCESS",
            "manifest": manifest
        }

    def _routing_total(self, key: str) -> int:
        """Sum one routing counter over the chunks routed in this run.

        Chunks restored from an earlier checkpoint are not included, which is
        why the manifest also records routing_counters_chunks_covered: a
        partial count must be visible as partial rather than look complete.
        """
        return int(getattr(self, "_routing_totals", {}).get(key, 0))

    def _verify_merged_header(self) -> bool:
        """Check the merged CSV header against the schema. Fail closed.

        Replaces a hardcoded True whose comment read "Only true if we got
        here", so it certified nothing at all.
        """
        from .schema import get_midnight_rider_headers

        expected = get_midnight_rider_headers()
        candidates = [
            self.output_dir / "MIDNIGHT_RIDER_10S_AGGREGATES.csv",
            self.output_dir / "output" / "MIDNIGHT_RIDER_10S_AGGREGATES.csv",
        ]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            raise ValueError(
                "schema validation: the merged Midnight Rider CSV was not "
                f"found in {self.output_dir}"
            )
        with open(path, newline="", encoding="utf-8") as handle:
            header_line = handle.readline().strip()
        actual = header_line.split(",") if header_line else []
        if actual != expected:
            missing = [c for c in expected if c not in actual]
            unexpected = [c for c in actual if c not in expected]
            if not missing and not unexpected:
                detail = (
                    "the column names are right but their order differs; "
                    f"expected {expected}, got {actual}"
                )
            else:
                detail = f"missing={missing} unexpected={unexpected}"
            raise ValueError(
                "schema validation FAILED: the merged header does not match "
                f"the {len(expected)}-column contract. {detail}"
            )
        return True

    def _process_chunk(self, chunk: Chunk, checkpoint: ExportCheckpoint) -> Dict:
        """
        Process a single chunk with separated timeout scopes.

        Args:
            chunk: Chunk to process
            checkpoint: Checkpoint to update

        Returns:
            Chunk result dictionary

        Raises:
            Exception: On any chunk processing failure
        """
        checkpoint.mark_chunk_processing(chunk.index)

        # Initialize providers and writers
        provider = DockerChunkedQueryProvider(
            query_startup_timeout=10,
            stream_idle_timeout=self.stream_idle_timeout_seconds,
            stream_overall_timeout=self.query_timeout_seconds,
            process_cleanup_timeout=5
        )

        classifier = Classifier()
        field_mapper = SignalKFieldMapper()

        # Temporary output files for this chunk
        chunk_dir = self.output_dir / f"chunk_{chunk.index:03d}"
        chunk_dir.mkdir(exist_ok=True, parents=True)

        ais_path = chunk_dir / "AIS_EVENTS_RAW.csv"
        mr_path = chunk_dir / "MIDNIGHT_RIDER_10S_AGGREGATES.csv"

        ais_writer = RawAISEventWriter(str(ais_path))
        midnight_rider_normalizer = Normalizer()

        try:
            # Query chunk
            logger.info(f"Querying chunk {chunk.index}: {chunk.start} to {chunk.stop}")

            # Build flux query with time range
            # query_range_chunk documents that range() needs bare
            # RFC3339 literals: quoting them makes Flux reject the
            # argument as a string instead of a time.
            flux_start = chunk.start
            flux_stop = chunk.stop

            parser = AnnotatedCSVParser()
            data_gen = provider.query_range_chunk(flux_start, flux_stop, chunk.index)

            # Routing is shared with the non-chunked path. The inline copy
            # that used to live here passed the raw Signal K measurement name
            # as a CSV field name, so every instrument column came out empty.
            router = RecordRouter(
                classifier=classifier,
                field_mapper=field_mapper,
                ais_writer=ais_writer,
                normalizer=midnight_rider_normalizer,
            )

            for record in parser.parse_stream(data_gen):
                router.route(record)

            total_rows = router.source_rows
            ais_rows = router.ais_rows
            mr_rows = router.midnight_rider_rows
            routing_counters = router.counters()
            logger.info(f"Chunk {chunk.index} routing: {routing_counters}")

            ais_writer.close()

            # Independent reconciliation. Ask InfluxDB how many rows this
            # range holds and refuse anything short of it: a truncated stream
            # is exactly how a silently empty export was produced before.
            count_flux = (
                f'from(bucket: "{provider.bucket}")\n'
                f'  |> range(start: {flux_start}, stop: {flux_stop})\n'
                '  |> count()\n'
                '  |> group()\n'
                '  |> sum()\n'
            )
            expected_rows = None
            for count_record in AnnotatedCSVParser().parse_stream(
                provider.query_flux_chunk(
                    count_flux, chunk.index, chunk.start, chunk.stop
                )
            ):
                if not isinstance(count_record, dict):
                    continue
                raw_count = count_record.get("_value")
                if raw_count not in (None, ""):
                    expected_rows = int(float(raw_count))

            if expected_rows is None:
                raise ValueError(
                    f"Chunk {chunk.index}: the reconciliation query returned "
                    "no row count; the chunk is rejected"
                )
            if expected_rows != router.source_rows:
                raise ValueError(
                    f"Chunk {chunk.index}: RECONCILIATION FAILURE - InfluxDB "
                    f"reports {expected_rows} rows for this range but "
                    f"{router.source_rows} were streamed. The stream was "
                    "truncated; the chunk is rejected."
                )
            logger.info(
                f"Chunk {chunk.index} reconciled: {expected_rows} rows read, "
                f"{router.mapped_points} values mapped, "
                f"{router.unmapped_rows} unmapped, "
                f"{router.unparsable_rows} unparsable"
            )

            if not hasattr(self, "_routing_totals"):
                self._routing_totals = {}
            if not hasattr(self, "_routing_chunks"):
                self._routing_chunks = []
            for counter_name, counter_value in routing_counters.items():
                self._routing_totals[counter_name] = (
                    self._routing_totals.get(counter_name, 0) + counter_value
                )
            self._routing_chunks.append(chunk.index)

            # Aggregate windows
            aggregated_windows = midnight_rider_normalizer.aggregate_windows()

            # Write chunk output
            headers = [h[0] for h in MIDNIGHT_RIDER_SCHEMA]
            midnight_rider_writer = CSVWriter(str(mr_path))
            if aggregated_windows:
                midnight_rider_writer.write_csv(aggregated_windows, headers)
            else:
                midnight_rider_writer.write_csv([], headers)

            # Calculate hashes
            ais_size = os.path.getsize(ais_path) if ais_path.exists() else 0
            mr_size = os.path.getsize(mr_path) if mr_path.exists() else 0

            ais_hash = self._calculate_sha256(ais_path) if ais_path.exists() else ""
            mr_hash = self._calculate_sha256(mr_path) if mr_path.exists() else ""

            # Mark chunk successful in checkpoint
            checkpoint.mark_chunk_success(
                chunk.index,
                chunk.start,
                chunk.stop,
                ais_rows=ais_rows,
                midnight_rider_rows=len(aggregated_windows) if aggregated_windows else 0,
                source_rows=total_rows,
                output_files={
                    "AIS_EVENTS_RAW.csv": ais_size,
                    "MIDNIGHT_RIDER_10S_AGGREGATES.csv": mr_size
                },
                file_hashes={
                    "AIS_EVENTS_RAW.csv": ais_hash,
                    "MIDNIGHT_RIDER_10S_AGGREGATES.csv": mr_hash
                }
            )

            logger.info(
                f"Chunk {chunk.index} processed: "
                f"total_rows={total_rows}, ais={ais_rows}, mr={len(aggregated_windows) if aggregated_windows else 0}"
            )

            return {
                'success': True,
                'chunk_index': chunk.index,
                'source_rows': total_rows,
                'ais_rows': ais_rows,
                'midnight_rider_rows': len(aggregated_windows) if aggregated_windows else 0,
                'ais_size': ais_size,
                'mr_size': mr_size
            }

        except Exception as e:
            logger.error(f"Chunk {chunk.index} processing failed: {e}")
            # Cleanup partial files
            for path in [ais_path, mr_path]:
                if path.exists():
                    try:
                        path.unlink()
                    except:
                        pass
            raise

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculate SHA256 of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

"""
Checkpoint and resume system for bounded chunked exports.

Provides checkpoint manifest creation, state persistence, and resume validation
for multi-chunk exports with deterministic merging and deduplication.

Design:
- Checkpoints record ONLY sanitized metadata (no raw data, coordinates, or MMSI)
- Completed chunks are NOT re-queried on resume
- Failed chunks can be explicitly retried
- Changed code SHA invalidates or clearly marks the checkpoint
- Resume never creates duplicate final rows
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkStatus(Enum):
    """Status of a chunk during export."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


@dataclass
class ChunkCheckpoint:
    """Checkpoint data for a single chunk."""
    chunk_index: int
    chunk_start: str  # ISO 8601 UTC
    chunk_stop: str   # ISO 8601 UTC
    status: str  # ChunkStatus enum value
    retry_count: int = 0
    ais_row_count: int = 0
    midnight_rider_row_count: int = 0
    source_row_count: int = 0
    output_files: Dict[str, str] = None  # {filename: size_bytes}
    file_hashes: Dict[str, str] = None  # {filename: sha256}
    failure_category: Optional[str] = None  # e.g., "TIMEOUT", "DATA_ERROR", etc.
    completion_timestamp: Optional[str] = None  # ISO 8601 UTC

    def __post_init__(self):
        """Ensure output_files and file_hashes are initialized."""
        if self.output_files is None:
            self.output_files = {}
        if self.file_hashes is None:
            self.file_hashes = {}


class ExportCheckpoint:
    """
    Checkpoint manifest for bounded export runs.

    Records only sanitized metadata:
    - run_id, requested start/stop, chunk config
    - chunk status, row counts, file metadata
    - NO raw rows, coordinates, MMSI, vessel names, credentials
    """

    def __init__(
        self,
        run_id: str,
        export_start_utc: str,
        export_stop_utc: str,
        chunk_hours: float,
        output_dir: Path,
        code_commit_sha: str
    ):
        """
        Initialize export checkpoint.

        Args:
            run_id: Unique run identifier (e.g., timestamp-based)
            export_start_utc: Requested export start (ISO 8601 UTC)
            export_stop_utc: Requested export stop (ISO 8601 UTC)
            chunk_hours: Chunk duration in hours
            output_dir: Root output directory for this export
            code_commit_sha: Git commit SHA for reproducibility
        """
        self.run_id = run_id
        self.export_start_utc = export_start_utc
        self.export_stop_utc = export_stop_utc
        self.chunk_hours = chunk_hours
        self.output_dir = Path(output_dir)
        self.code_commit_sha = code_commit_sha

        # Checkpoint state
        self.creation_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.last_update_timestamp = self.creation_timestamp
        self.chunks: Dict[int, ChunkCheckpoint] = {}

        logger.info(f"Checkpoint created: run_id={run_id}, chunks_dir={self.output_dir}")

    def checkpoint_path(self) -> Path:
        """Return path to checkpoint manifest file."""
        return self.output_dir / "CHECKPOINT.json"

    def get_chunk(self, chunk_index: int) -> Optional[ChunkCheckpoint]:
        """Retrieve checkpoint for a specific chunk."""
        return self.chunks.get(chunk_index)

    def add_chunk(self, chunk: ChunkCheckpoint) -> None:
        """Add or update chunk checkpoint."""
        self.chunks[chunk.chunk_index] = chunk
        self.last_update_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        logger.debug(f"Checkpoint updated: chunk {chunk.chunk_index} -> {chunk.status}")

    def mark_chunk_processing(self, chunk_index: int) -> None:
        """Mark chunk as currently processing."""
        if chunk_index not in self.chunks:
            self.chunks[chunk_index] = ChunkCheckpoint(
                chunk_index=chunk_index,
                chunk_start="",
                chunk_stop="",
                status=ChunkStatus.PROCESSING.value
            )
        else:
            self.chunks[chunk_index].status = ChunkStatus.PROCESSING.value
        self.last_update_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def mark_chunk_success(
        self,
        chunk_index: int,
        chunk_start: str,
        chunk_stop: str,
        ais_rows: int,
        midnight_rider_rows: int,
        source_rows: int,
        output_files: Dict[str, str],
        file_hashes: Dict[str, str]
    ) -> None:
        """Mark chunk as successfully completed."""
        checkpoint = ChunkCheckpoint(
            chunk_index=chunk_index,
            chunk_start=chunk_start,
            chunk_stop=chunk_stop,
            status=ChunkStatus.SUCCESS.value,
            ais_row_count=ais_rows,
            midnight_rider_row_count=midnight_rider_rows,
            source_row_count=source_rows,
            output_files=output_files,
            file_hashes=file_hashes,
            completion_timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        )
        self.add_chunk(checkpoint)
        logger.info(f"Chunk {chunk_index} SUCCESS: {source_rows} source rows, {ais_rows} AIS, {midnight_rider_rows} MR")

    def mark_chunk_failed(
        self,
        chunk_index: int,
        chunk_start: str,
        chunk_stop: str,
        failure_category: str,
        retry_count: int = 0
    ) -> None:
        """Mark chunk as failed."""
        checkpoint = ChunkCheckpoint(
            chunk_index=chunk_index,
            chunk_start=chunk_start,
            chunk_stop=chunk_stop,
            status=ChunkStatus.FAILED.value,
            failure_category=failure_category,
            retry_count=retry_count,
            completion_timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        )
        self.add_chunk(checkpoint)
        logger.warning(f"Chunk {chunk_index} FAILED: {failure_category} (retry_count={retry_count})")

    def get_completed_chunks(self) -> List[int]:
        """Return list of successfully completed chunk indices."""
        return [
            idx for idx, chunk in self.chunks.items()
            if chunk.status == ChunkStatus.SUCCESS.value
        ]

    def get_failed_chunks(self) -> List[int]:
        """Return list of failed chunk indices."""
        return [
            idx for idx, chunk in self.chunks.items()
            if chunk.status == ChunkStatus.FAILED.value
        ]

    def get_pending_chunks(self, total_chunks: int) -> List[int]:
        """
        Return list of chunk indices that need processing.

        Includes PENDING and PROCESSING (from interrupted run).
        """
        pending = []
        for i in range(total_chunks):
            chunk = self.chunks.get(i)
            if chunk is None:
                # Never started
                pending.append(i)
            elif chunk.status in (ChunkStatus.PENDING.value, ChunkStatus.PROCESSING.value):
                # Pending or interrupted
                pending.append(i)
        return pending

    def save(self) -> None:
        """Save checkpoint manifest to disk."""
        manifest: Dict[str, Any] = {
            "run_id": self.run_id,
            "creation_timestamp": self.creation_timestamp,
            "last_update_timestamp": self.last_update_timestamp,
            "export_start_utc": self.export_start_utc,
            "export_stop_utc": self.export_stop_utc,
            "chunk_hours": self.chunk_hours,
            "code_commit_sha": self.code_commit_sha,
            "chunks": {}
        }

        for idx, chunk in self.chunks.items():
            manifest["chunks"][str(idx)] = {
                "chunk_index": chunk.chunk_index,
                "chunk_start": chunk.chunk_start,
                "chunk_stop": chunk.chunk_stop,
                "status": chunk.status,
                "retry_count": chunk.retry_count,
                "ais_row_count": chunk.ais_row_count,
                "midnight_rider_row_count": chunk.midnight_rider_row_count,
                "source_row_count": chunk.source_row_count,
                "output_files": chunk.output_files,
                "file_hashes": chunk.file_hashes,
                "failure_category": chunk.failure_category,
                "completion_timestamp": chunk.completion_timestamp
            }

        checkpoint_path = self.checkpoint_path()
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        with open(checkpoint_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Checkpoint saved: {checkpoint_path}")

    @staticmethod
    def load(checkpoint_path: Path) -> "ExportCheckpoint":
        """
        Load checkpoint from disk.

        Args:
            checkpoint_path: Path to CHECKPOINT.json

        Returns:
            ExportCheckpoint instance

        Raises:
            ValueError: If checkpoint is invalid or incompatible
        """
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        with open(checkpoint_path, 'r') as f:
            manifest = json.load(f)

        # Validate required fields
        required_fields = [
            "run_id", "export_start_utc", "export_stop_utc",
            "chunk_hours", "code_commit_sha"
        ]
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Checkpoint missing required field: {field}")

        # Create checkpoint
        checkpoint = ExportCheckpoint(
            run_id=manifest["run_id"],
            export_start_utc=manifest["export_start_utc"],
            export_stop_utc=manifest["export_stop_utc"],
            chunk_hours=manifest["chunk_hours"],
            output_dir=checkpoint_path.parent,
            code_commit_sha=manifest["code_commit_sha"]
        )

        checkpoint.creation_timestamp = manifest.get("creation_timestamp", checkpoint.creation_timestamp)
        checkpoint.last_update_timestamp = manifest.get("last_update_timestamp", checkpoint.last_update_timestamp)

        # Load chunks
        for chunk_idx_str, chunk_data in manifest.get("chunks", {}).items():
            chunk = ChunkCheckpoint(
                chunk_index=int(chunk_idx_str),
                chunk_start=chunk_data.get("chunk_start", ""),
                chunk_stop=chunk_data.get("chunk_stop", ""),
                status=chunk_data.get("status", ChunkStatus.PENDING.value),
                retry_count=chunk_data.get("retry_count", 0),
                ais_row_count=chunk_data.get("ais_row_count", 0),
                midnight_rider_row_count=chunk_data.get("midnight_rider_row_count", 0),
                source_row_count=chunk_data.get("source_row_count", 0),
                output_files=chunk_data.get("output_files", {}),
                file_hashes=chunk_data.get("file_hashes", {}),
                failure_category=chunk_data.get("failure_category"),
                completion_timestamp=chunk_data.get("completion_timestamp")
            )
            checkpoint.chunks[int(chunk_idx_str)] = chunk

        logger.info(f"Checkpoint loaded: {checkpoint_path} ({len(checkpoint.chunks)} chunks)")

        return checkpoint

    def validate_for_resume(self, current_code_sha: str) -> Tuple[bool, Optional[str]]:
        """
        Validate checkpoint is compatible for resume.

        STRICT VALIDATION:
        - Code SHA must match (REJECT if different)
        - PROCESSING chunks flagged for reprocessing
        - FAILED chunks can be retried explicitly

        Args:
            current_code_sha: Current git commit SHA

        Returns:
            (is_valid, error_message_if_invalid)
        """
        # STRICT: Reject checkpoint with different code SHA
        if self.code_commit_sha != current_code_sha:
            return False, (
                f"Checkpoint code SHA {self.code_commit_sha[:8]} "
                f"differs from current {current_code_sha[:8]}. Reject."
            )

        # Mark PROCESSING chunks for reprocessing (interrupted run)
        for chunk_idx, chunk in self.chunks.items():
            if chunk.status == ChunkStatus.PROCESSING.value:
                logger.warning(f"Chunk {chunk_idx} PROCESSING from prior run; will reprocess")
                chunk.status = ChunkStatus.PENDING.value
                chunk.retry_count += 1

        return True, None

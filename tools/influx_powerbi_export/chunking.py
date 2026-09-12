"""
Time-window chunking module for scalable bounded exports.

Provides deterministic chunk boundary calculation, half-open interval handling,
and checkpoint-aware segmentation for InfluxDB exports.

Design:
- Chunks are half-open intervals [start, stop)
- Chunk boundaries are deterministically calculated
- Adjacent chunks do NOT overlap and do NOT leave gaps
- All boundaries are aligned to 10-second boundaries
- ISO 8601 UTC timestamps are validated
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a single time-window chunk for export."""
    index: int
    start: str  # ISO 8601 UTC
    stop: str   # ISO 8601 UTC (half-open, not included)
    chunk_hours: float
    
    def duration_seconds(self) -> int:
        """Return chunk duration in seconds."""
        start_dt = datetime.fromisoformat(self.start.replace('Z', '+00:00'))
        stop_dt = datetime.fromisoformat(self.stop.replace('Z', '+00:00'))
        return int((stop_dt - start_dt).total_seconds())
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"Chunk[{self.index}]: {self.start} to {self.stop} ({self.duration_seconds()}s)"


class ChunkingStrategy:
    """Deterministic chunking of time-window exports."""
    
    def __init__(self, chunk_hours: float = 6.0):
        """
        Initialize chunking strategy.
        
        Args:
            chunk_hours: Duration of each chunk in hours (default: 6). Must be > 0.
        """
        if chunk_hours <= 0:
            raise ValueError(f"chunk_hours must be > 0, got {chunk_hours}")
        
        self.chunk_hours = chunk_hours
        self.chunk_seconds = int(chunk_hours * 3600)
        
        logger.info(f"Chunking strategy: {chunk_hours} hours ({self.chunk_seconds} seconds per chunk)")
    
    @staticmethod
    def _parse_iso8601_utc(timestamp: str) -> datetime:
        """
        Parse ISO 8601 UTC timestamp.
        
        Args:
            timestamp: ISO 8601 string (e.g., "2026-09-04T00:00:00Z")
        
        Returns:
            datetime object (timezone-aware UTC)
        
        Raises:
            ValueError: If timestamp is invalid or not UTC
        """
        if not timestamp:
            raise ValueError("Timestamp cannot be empty")
        
        try:
            # Handle both 'Z' suffix and '+00:00' format
            if timestamp.endswith('Z'):
                timestamp = timestamp[:-1] + '+00:00'
            
            dt = datetime.fromisoformat(timestamp)
            
            # Verify UTC
            if dt.tzinfo is None or dt.tzinfo != timezone.utc:
                raise ValueError(f"Timestamp {timestamp} must be UTC")
            
            return dt
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid ISO 8601 UTC timestamp: {timestamp}") from e
    
    @staticmethod
    def _align_to_10s(dt: datetime, direction: str = 'down') -> datetime:
        """
        Align datetime to nearest 10-second boundary.
        
        Args:
            dt: datetime to align
            direction: 'down' (floor) or 'up' (ceil)
        
        Returns:
            Aligned datetime
        """
        total_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
        
        if direction == 'down':
            aligned_seconds = (total_seconds // 10) * 10
        elif direction == 'up':
            aligned_seconds = ((total_seconds + 9) // 10) * 10
        else:
            raise ValueError(f"Invalid direction: {direction}")
        
        # Handle day wraparound
        if aligned_seconds >= 86400:
            dt = dt + timedelta(days=1)
            aligned_seconds -= 86400
        
        hours = aligned_seconds // 3600
        minutes = (aligned_seconds % 3600) // 60
        seconds = aligned_seconds % 60
        
        return dt.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)
    
    def calculate_chunks(self, start: str, stop: str) -> List[Chunk]:
        """
        Calculate deterministic chunks for a time range.
        
        Args:
            start: ISO 8601 UTC start timestamp
            stop: ISO 8601 UTC stop timestamp
        
        Returns:
            List of Chunk objects (half-open intervals)
        
        Raises:
            ValueError: If start >= stop or timestamps are invalid
        """
        # Parse and validate
        start_dt = self._parse_iso8601_utc(start)
        stop_dt = self._parse_iso8601_utc(stop)
        
        if start_dt >= stop_dt:
            raise ValueError(f"Start ({start}) must be before stop ({stop})")
        
        # Align boundaries to 10-second boundaries
        # start: floor to 10s
        # stop: ceil to 10s (ensures we don't cut off data at exact boundary)
        start_aligned = self._align_to_10s(start_dt, direction='down')
        stop_aligned = self._align_to_10s(stop_dt, direction='up')
        
        logger.info(f"Time range: {start_dt} to {stop_dt}")
        logger.info(f"Aligned range: {start_aligned} to {stop_aligned}")
        
        chunks = []
        current = start_aligned
        chunk_index = 0
        
        while current < stop_aligned:
            # Calculate next chunk boundary
            next_boundary = current + timedelta(seconds=self.chunk_seconds)
            
            # Don't exceed overall stop
            chunk_stop = min(next_boundary, stop_aligned)
            
            # Create chunk (half-open interval [start, stop))
            chunk = Chunk(
                index=chunk_index,
                start=current.isoformat().replace('+00:00', 'Z'),
                stop=chunk_stop.isoformat().replace('+00:00', 'Z'),
                chunk_hours=self.chunk_hours
            )
            
            chunks.append(chunk)
            logger.info(f"Calculated {chunk}")
            
            current = chunk_stop
            chunk_index += 1
        
        if not chunks:
            raise ValueError("No chunks calculated for given time range")
        
        logger.info(f"Total chunks: {len(chunks)}")
        
        return chunks
    
    def validate_chunks(self, chunks: List[Chunk]) -> bool:
        """
        Validate chunk integrity (no overlaps, no gaps, boundaries correct).
        
        Args:
            chunks: List of chunks to validate
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If chunks are invalid
        """
        if not chunks:
            raise ValueError("Chunk list is empty")
        
        for i, chunk in enumerate(chunks):
            # Validate chunk itself
            start_dt = self._parse_iso8601_utc(chunk.start)
            stop_dt = self._parse_iso8601_utc(chunk.stop)
            
            if start_dt >= stop_dt:
                raise ValueError(f"Chunk {i}: Invalid interval [{chunk.start}, {chunk.stop})")
            
            # Check 10-second alignment
            if start_dt.second % 10 != 0:
                raise ValueError(f"Chunk {i}: Start {chunk.start} not aligned to 10s boundary")
            if stop_dt.second % 10 != 0:
                raise ValueError(f"Chunk {i}: Stop {chunk.stop} not aligned to 10s boundary")
            
            # Check adjacent chunk boundaries
            if i > 0:
                prev_chunk = chunks[i - 1]
                prev_stop_dt = self._parse_iso8601_utc(prev_chunk.stop)
                
                if prev_stop_dt != start_dt:
                    raise ValueError(
                        f"Chunk {i}: Gap or overlap detected. "
                        f"Previous chunk ends {prev_chunk.stop}, this chunk starts {chunk.start}"
                    )
        
        logger.info("Chunk validation: PASSED")
        return True


def calculate_chunks(start: str, stop: str, chunk_hours: float = 6.0) -> List[Chunk]:
    """
    Convenience function to calculate chunks.
    
    Args:
        start: ISO 8601 UTC start
        stop: ISO 8601 UTC stop
        chunk_hours: Hours per chunk (default: 6)
    
    Returns:
        List of Chunk objects
    """
    strategy = ChunkingStrategy(chunk_hours=chunk_hours)
    chunks = strategy.calculate_chunks(start, stop)
    strategy.validate_chunks(chunks)
    return chunks

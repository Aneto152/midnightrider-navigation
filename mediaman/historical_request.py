"""
Historical request contract for MediaMan — strictly validated temporal parameters.

A HistoricalRequest specifies a point-in-time snapshot of navigation facts
from InfluxDB via the MCP racing server.

Rules:
- as_of_utc must be ISO 8601 UTC timestamp
- as_of_utc must not be in the future
- window_seconds must be positive and bounded
- source must be explicit: influxdb_historical
- no silent fallback to live data or TestContentProvider
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class HistoricalRequest:
    """Immutable historical snapshot request."""

    race_id: str
    as_of_utc: str  # ISO 8601 UTC timestamp
    window_seconds: int
    source: str = "influxdb_historical"

    # Validation bounds
    MAX_WINDOW_SECONDS = 3600  # 1 hour
    MIN_WINDOW_SECONDS = 1

    def __post_init__(self):
        """Validate request parameters at construction time."""
        # Validate race_id
        if not self.race_id or not isinstance(self.race_id, str):
            raise ValueError("race_id must be non-empty string")
        if len(self.race_id) > 128:
            raise ValueError("race_id exceeds max length (128)")

        # Validate as_of_utc: ISO 8601 UTC format with strict Z suffix (D4)
        if not isinstance(self.as_of_utc, str):
            raise ValueError("as_of_utc must be string")

        # D4: Mandatory Z suffix (strict)
        if not self.as_of_utc.endswith('Z'):
            raise ValueError("as_of_utc must end with 'Z' (UTC timezone required)")

        try:
            # Parse ISO 8601 UTC timestamp
            as_of_str = self.as_of_utc.strip()

            # Convert Z to +00:00 for fromisoformat
            as_of_str_normalized = as_of_str[:-1] + '+00:00'
            as_of_dt = datetime.fromisoformat(as_of_str_normalized)

            # D4: Strict UTC offset validation
            offset = as_of_dt.utcoffset()
            if offset is None or offset.total_seconds() != 0:
                raise ValueError("Only UTC offset +00:00 allowed (use Z suffix)")

            # Check not in future (allow 5-second clock skew)
            now_utc = datetime.now(timezone.utc)
            age_seconds = (now_utc - as_of_dt).total_seconds()

            if age_seconds < -5:
                raise ValueError("as_of_utc is in the future")
        except ValueError as e:
            if "future" in str(e) or "only UTC" in str(e).lower() or "must end with" in str(e).lower():
                raise
            raise ValueError(f"as_of_utc must be valid ISO 8601 UTC: {e}") from e

        # Validate window_seconds (mandatory)
        if self.window_seconds is None:
            raise ValueError("window_seconds is required")

        if not isinstance(self.window_seconds, int):
            raise ValueError("window_seconds must be integer")

        if self.window_seconds < self.MIN_WINDOW_SECONDS:
            raise ValueError(f"window_seconds must be >= {self.MIN_WINDOW_SECONDS}")

        if self.window_seconds > self.MAX_WINDOW_SECONDS:
            raise ValueError(f"window_seconds must be <= {self.MAX_WINDOW_SECONDS}")

        # Validate source
        if self.source != "influxdb_historical":
            raise ValueError("source must be exactly 'influxdb_historical'")


class HistoricalRequestValidator:
    """Validator for HistoricalRequest parameters."""

    @staticmethod
    def validate(race_id: str, as_of_utc: str, window_seconds: int) -> tuple[bool, str]:
        """
        Validate request parameters.

        Returns: (is_valid, error_message)
        """
        try:
            HistoricalRequest(
                race_id=race_id,
                as_of_utc=as_of_utc,
                window_seconds=window_seconds
            )
            return True, ""
        except ValueError as e:
            return False, str(e)

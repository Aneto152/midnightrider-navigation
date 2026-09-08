"""
Tests for HistoricalRequest contract validation.

Tests strictly validated temporal parameters for historical snapshots.
"""

import pytest
from datetime import datetime, timezone
from mediaman.historical_request import HistoricalRequest, HistoricalRequestValidator


class TestHistoricalRequestValidation:
    """Test HistoricalRequest parameter validation."""

    def test_valid_request(self):
        """Valid historical request accepted."""
        request = HistoricalRequest(
            race_id="race-2026-09-01",
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=60
        )
        assert request.race_id == "race-2026-09-01"
        assert request.as_of_utc == "2026-09-01T12:00:00Z"
        assert request.window_seconds == 60
        assert request.source == "influxdb_historical"

    def test_malformed_timestamp_rejected(self):
        """Malformed timestamp rejected."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="not-a-timestamp",
                window_seconds=60
            )
        assert "ISO 8601" in str(exc_info.value)

    def test_future_timestamp_rejected(self):
        """Future timestamp rejected (with 5-second skew)."""
        future_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
        # Add 10 seconds to future
        future_dt = datetime.fromisoformat(future_ts.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        future_dt = future_dt.replace(second=future_dt.second + 10)
        future_ts = future_dt.isoformat().replace("+00:00", "Z")
        
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc=future_ts,
                window_seconds=60
            )
        assert "future" in str(exc_info.value).lower()

    def test_zero_window_rejected(self):
        """Zero window_seconds rejected."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=0
            )
        assert "window_seconds" in str(exc_info.value)

    def test_negative_window_rejected(self):
        """Negative window_seconds rejected."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=-1
            )
        assert "window_seconds" in str(exc_info.value)

    def test_excessive_window_rejected(self):
        """Excessive window_seconds rejected (> 3600)."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=3601
            )
        assert "window_seconds" in str(exc_info.value)

    def test_empty_race_id_rejected(self):
        """Empty race_id rejected."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="",
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=60
            )
        assert "race_id" in str(exc_info.value)

    def test_invalid_source_rejected(self):
        """Invalid source rejected."""
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00Z",
                window_seconds=60,
                source="invalid_source"
            )
        assert "source" in str(exc_info.value)

    def test_iso8601_with_offset_rejected(self):
        """ISO 8601 with non-Z offset rejected (D4: Z-only required)."""
        # +00:00 should be rejected
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00+00:00",
                window_seconds=60
            )
        assert "UTC" in str(exc_info.value) or "Z" in str(exc_info.value)

        # +05:30 should be rejected
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00+05:30",
                window_seconds=60
            )
        assert "UTC" in str(exc_info.value) or "Z" in str(exc_info.value)

        # -08:00 should be rejected
        with pytest.raises(ValueError) as exc_info:
            HistoricalRequest(
                race_id="race-id",
                as_of_utc="2026-09-01T12:00:00-08:00",
                window_seconds=60
            )
        assert "UTC" in str(exc_info.value) or "Z" in str(exc_info.value)

    def test_canonical_z_suffix_accepted(self):
        """Canonical Z suffix timestamp accepted (D4)."""
        request = HistoricalRequest(
            race_id="race-id",
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=60
        )
        assert request.as_of_utc == "2026-09-01T12:00:00Z"

    def test_boundary_window_accepted(self):
        """Boundary window values accepted."""
        request_min = HistoricalRequest(
            race_id="race-id",
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=1
        )
        assert request_min.window_seconds == 1

        request_max = HistoricalRequest(
            race_id="race-id",
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=3600
        )
        assert request_max.window_seconds == 3600


class TestHistoricalRequestValidator:
    """Test the HistoricalRequestValidator helper."""

    def test_valid_request_validates(self):
        """Validator accepts valid request."""
        is_valid, error = HistoricalRequestValidator.validate(
            race_id="race-id",
            as_of_utc="2026-09-01T12:00:00Z",
            window_seconds=60
        )
        assert is_valid is True
        assert error == ""

    def test_invalid_request_fails(self):
        """Validator rejects invalid request with stable contract wording."""
        is_valid, error = HistoricalRequestValidator.validate(
            race_id="race-id",
            as_of_utc="not-a-timestamp",
            window_seconds=60
        )
        assert is_valid is False
        # Check for stable contract wording
        assert "ISO 8601" in error or "UTC" in error or "must" in error

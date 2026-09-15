"""
Unit tests for normalization and aggregation logic.
"""
import pytest
import math
from tools.influx_powerbi_export.normalizer import Normalizer

@pytest.fixture
def normalizer():
    return Normalizer()

def test_circular_mean_north(normalizer):
    """Circular mean of angles near north (0°)."""
    angles = [355, 5, 10]  # Around north
    mean = normalizer.circular_mean(angles)
    assert 0 <= mean <= 360
    # Should be close to 0 or 360
    assert mean < 30 or mean > 330

def test_circular_mean_east(normalizer):
    """Circular mean of angles near east (90°)."""
    angles = [85, 90, 95]
    mean = normalizer.circular_mean(angles)
    assert 80 <= mean <= 100

def test_circular_mean_opposite_sides(normalizer):
    """Circular mean of angles on opposite sides (shouldn't average to 180)."""
    angles = [10, 20, 350, 340]  # Two clusters
    mean = normalizer.circular_mean(angles)
    # Should be near one cluster, not 180
    assert (0 <= mean <= 30) or (330 <= mean <= 360)

def test_aggregation_window(normalizer):
    """Add points to window and aggregate."""
    # Simulate 10 seconds of data
    normalizer.add_point("2026-09-08T12:34:10.100Z", "sog_knots", 8.5)
    normalizer.add_point("2026-09-08T12:34:12.500Z", "sog_knots", 8.6)
    normalizer.add_point("2026-09-08T12:34:15.300Z", "cog_deg", 215.0)
    normalizer.add_point("2026-09-08T12:34:18.900Z", "cog_deg", 216.0)
    
    rows = normalizer.aggregate_windows()
    assert len(rows) == 1
    assert rows[0]["sample_count"] == 4
    assert 8.5 <= rows[0]["sog_knots"] <= 8.6
    assert 215 <= rows[0]["cog_deg"] <= 216

def test_no_completeness_ratio_emitted(normalizer):
    """completeness_ratio was removed: its denominator adapted to the
    fields actually present, so a window holding a single instrument
    scored 1.0. It must no longer appear in any row."""
    normalizer.windows[(100, 110)]["field1"] = [1.0] * 8
    rows = normalizer.aggregate_windows()
    assert "completeness_ratio" not in rows[0]

def test_no_quality_flag_emitted(normalizer):
    """quality_flag was removed: derived from completeness_ratio, it could
    never report a missing instrument."""
    normalizer.windows[(100, 110)]["field1"] = [1.0] * 2
    rows = normalizer.aggregate_windows()
    assert "quality_flag" not in rows[0]
    assert not hasattr(normalizer, "_quality_flag")

def test_schema_is_22_fields_with_water_temp():
    """The CSV contract: 22 columns, water_temp_c present, the two
    withdrawn columns absent."""
    from tools.influx_powerbi_export.schema import get_midnight_rider_headers
    headers = get_midnight_rider_headers()
    assert len(headers) == 22, headers
    assert "water_temp_c" in headers
    assert "completeness_ratio" not in headers
    assert "quality_flag" not in headers
    assert "sample_count" in headers  # still the merge weight

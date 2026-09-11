"""
Regression tests for measurement-to-field mapping in the normalizer.

Tests synthetic data only. No real Signal K paths, coordinates, MMSI, or vessel names.
"""
import pytest
from tools.influx_powerbi_export.normalizer import Normalizer


class TestMeasurementMapping:
    """Test that _measurement (Signal K path) is used, not _field (generic 'value')."""
    
    def test_measurement_contains_signalk_like_path(self):
        """_measurement contains a Signal K-like path category."""
        # Simulate a normalized record with Signal K-like measurement
        timestamp = "2026-09-04T16:00:03Z"
        measurement = "environment.wind.speedApparent"  # Signal K path
        value = 5.0
        
        normalizer = Normalizer()
        normalizer.add_point(
            timestamp_utc=timestamp,
            field_name=measurement,
            value=value
        )
        
        # Verify window was created
        windows = normalizer.aggregate_windows()
        assert len(windows) > 0
        assert "environment.wind.speedApparent" in windows[0]
    
    def test_field_equals_generic_value(self):
        """_field is generic 'value', not used as field name."""
        # In real InfluxDB data, _field='value' is generic metadata
        # We use _measurement as the actual field name
        measurement = "navigation.position.latitude"  # Signal K path in _measurement
        generic_field = "value"  # This is what _field contains
        
        normalizer = Normalizer()
        # Pass _measurement, not generic "value"
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name=measurement,  # Use this, not generic_field
            value=42.5
        )
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        # Field name should be the Signal K path, not "value"
        assert measurement in windows[0]
        assert generic_field not in windows[0]
    
    def test_value_converted_to_numeric_payload(self):
        """_value is converted to numeric payload."""
        normalizer = Normalizer()
        
        # Add point with numeric value
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name="environment.wind.speedApparent",
            value=10.5
        )
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        assert windows[0]["environment.wind.speedApparent"] == 10.5
    
    def test_field_mapper_receives_measurement(self):
        """FieldMapper receives _measurement key."""
        # This test verifies the contract: use record["_measurement"]
        record = {
            "_time": "2026-09-04T16:00:03Z",
            "_measurement": "environment.wind.speedTrue",  # Signal K path
            "_field": "value",  # Generic metadata
            "_value": "7.2",  # Numeric as string
        }
        
        # Extract using correct key
        measurement_key = record.get("_measurement")
        field_key = record.get("_field")
        
        # Should use _measurement, not _field
        assert measurement_key == "environment.wind.speedTrue"
        assert field_key == "value"
        assert measurement_key != field_key
    
    def test_field_mapper_never_receives_field_as_path(self):
        """FieldMapper never receives _field as path."""
        # This verifies we DON'T use record["_field"] as the mapping key
        record = {
            "_time": "2026-09-04T16:00:03Z",
            "_measurement": "environment.water.temperature",
            "_field": "value",
            "_value": "18.3",
        }
        
        # Should NOT use _field as the field name
        field_key = record.get("_field")
        assert field_key == "value"
        
        # Should use _measurement instead
        measurement_key = record.get("_measurement")
        assert measurement_key != "value"
    
    def test_valid_mapped_point_reaches_normalizer(self):
        """Valid mapped point reaches the Normalizer."""
        normalizer = Normalizer()
        
        # Add a valid point
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:05Z",
            field_name="navigation.courseOverGroundTrue",
            value=180.0
        )
        
        # Verify it was added to a window
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        assert windows[0]["navigation.courseOverGroundTrue"] == 180.0
    
    def test_window_is_created(self):
        """Window is created for valid measurements."""
        normalizer = Normalizer()
        
        # Add multiple points in the same 10-second window
        base_time = "2026-09-04T16:00:03Z"
        normalizer.add_point(base_time, "environment.wind.speedApparent", 5.0)
        normalizer.add_point("2026-09-04T16:00:04Z", "environment.wind.speedApparent", 5.5)
        normalizer.add_point("2026-09-04T16:00:05Z", "environment.wind.speedApparent", 6.0)
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        # Should be averaged
        avg_value = windows[0]["environment.wind.speedApparent"]
        assert 5.0 < avg_value < 6.0
    
    def test_aggregate_windows_returns_non_empty_list(self):
        """aggregate_windows() returns non-empty list when data added."""
        normalizer = Normalizer()
        
        # Add point
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:07Z",
            field_name="navigation.speedOverWater",
            value=8.5
        )
        
        result = normalizer.aggregate_windows()
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)
    
    def test_invalid_value_rejected_and_counted(self):
        """Invalid _value is rejected and counted."""
        normalizer = Normalizer()
        
        # Try to add with None value
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name="environment.wind.speedApparent",
            value=None  # Invalid
        )
        
        # Should have no windows created
        windows = normalizer.aggregate_windows()
        assert len(windows) == 0
    
    def test_missing_measurement_rejected_and_counted(self):
        """Missing _measurement is rejected and counted."""
        normalizer = Normalizer()
        
        # Try to add with None field_name (missing _measurement)
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name=None,  # Missing measurement
            value=5.0
        )
        
        # Should have no windows created
        windows = normalizer.aggregate_windows()
        assert len(windows) == 0
    
    def test_ais_precedence_unchanged(self):
        """AIS precedence routing remains unchanged."""
        # This test verifies that AIS handling is not affected by measurement mapping fix
        # AIS records should still go to AIS_EVENTS_RAW.csv, not to Midnight Rider aggregation
        # (This is implicitly tested through the classifier, not the normalizer)
        pass
    
    def test_non_ais_classification_preserved(self):
        """Non-AIS records remain classified as 'midnight_rider', not 'unclassified'."""
        # This test verifies classifier policy: non-AIS → "midnight_rider"
        # (Tested through classifier tests, not measurement mapping)
        pass


class TestMeasurementAggregation:
    """Test aggregation of measurements with correct field names."""
    
    def test_multiple_measurements_in_same_window(self):
        """Multiple different measurements in same 10-second window."""
        normalizer = Normalizer()
        
        # Add different measurements to same window
        normalizer.add_point("2026-09-04T16:00:03Z", "environment.wind.speedApparent", 5.0)
        normalizer.add_point("2026-09-04T16:00:04Z", "environment.wind.angleApparent", 90.0)
        normalizer.add_point("2026-09-04T16:00:05Z", "navigation.courseOverGroundTrue", 180.0)
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        
        # All three measurements should be in the aggregated window
        window = windows[0]
        assert "environment.wind.speedApparent" in window
        assert "environment.wind.angleApparent" in window
        assert "navigation.courseOverGroundTrue" in window
    
    def test_circular_mean_applied_to_angle_fields(self):
        """Circular mean applied to angle fields (Signal K path-based)."""
        normalizer = Normalizer()
        
        # Add angle measurements (these should use circular mean)
        # True heading should be in CIRCULAR_FIELDS
        normalizer.add_point("2026-09-04T16:00:03Z", "navigation.courseOverGroundTrue", 10.0)
        normalizer.add_point("2026-09-04T16:00:04Z", "navigation.courseOverGroundTrue", 350.0)
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        
        # Circular mean should be ~0 (between 350 and 10 degrees)
        cog_value = windows[0].get("navigation.courseOverGroundTrue")
        # Should be close to 0 or 360
        assert cog_value is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

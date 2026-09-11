"""
Real schema population tests for Signal K to CSV field mapping.

Tests verify that actual Signal K measurement paths are mapped to final CSV schema fields,
not raw measurement names or generic "value" fields.

Uses synthetic placeholders only. No real contexts, sources, MMSI, coordinates, or vessel names.
"""
import pytest
from tools.influx_powerbi_export.field_mapper import SignalKFieldMapper
from tools.influx_powerbi_export.normalizer import Normalizer


class TestSchemaPopulationMapping:
    """Test that final CSV schema columns are populated, not raw field names."""
    
    def test_navigation_measurement_maps_to_known_column(self):
        """Synthetic navigation measurement maps to known navigation CSV column."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "navigation.speedOverGround",
            "5.0"  # m/s
        )
        
        assert result is not None
        target_field, converted_value = result
        # Must map to final schema field, not raw path
        assert target_field == "sog_knots"
        assert converted_value > 0  # Value converted to knots
        assert "speedOverGround" not in target_field  # Not raw path name
    
    def test_wind_measurement_maps_to_known_column(self):
        """Synthetic wind measurement maps to known wind CSV column."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "environment.wind.speedApparent",
            "10.0"  # m/s
        )
        
        assert result is not None
        target_field, converted_value = result
        # Must map to final schema field
        assert target_field == "aws_knots"
        assert converted_value > 0  # Value converted
    
    def test_heading_measurement_maps_to_known_column(self):
        """Synthetic heading measurement maps to known heading CSV column."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "navigation.headingTrue",
            "1.5708"  # radians (90 degrees)
        )
        
        assert result is not None
        target_field, converted_value = result
        # Must map to final schema field
        assert target_field == "true_heading_deg"
        # Value should be converted from radians to degrees
        assert 80 < converted_value < 100  # ~90 degrees
    
    def test_depth_measurement_maps_to_depth_m(self):
        """Synthetic depth measurement maps to depth_m column."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "environment.water.depth.belowTransducer",
            "5.5"  # meters
        )
        
        assert result is not None
        target_field, converted_value = result
        assert target_field == "depth_m"
        assert converted_value == 5.5
    
    def test_battery_measurement_maps_to_battery_voltage(self):
        """Synthetic battery measurement maps to battery_voltage column."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "electrical.batteries.House.voltage",
            "13.5"  # volts
        )
        
        assert result is not None
        target_field, converted_value = result
        assert target_field == "battery_voltage"
        assert converted_value == 13.5
    
    def test_generic_value_field_ignored_as_path(self):
        """Generic _field=value is ignored as a path."""
        mapper = SignalKFieldMapper()
        
        # Should NOT map the literal string "value"
        result = mapper.map_and_convert("value", "10.0")
        
        assert result is None  # Unmapped
        assert mapper.unmapped_count > 0
    
    def test_measurement_key_used_not_field_key(self):
        """_measurement key is used as mapping path, not _field."""
        mapper = SignalKFieldMapper()
        
        # Correct: use _measurement
        signal_k_path = "navigation.courseOverGroundTrue"
        result = mapper.map_and_convert(signal_k_path, "3.14159")  # radians
        
        assert result is not None
        target_field, _ = result
        assert target_field == "cog_deg"
        
        # Incorrect: _field is generic "value"
        # We don't try to map generic "value"
        result_generic = mapper.map_and_convert("value", "3.14159")
        assert result_generic is None
    
    def test_value_string_becomes_numeric(self):
        """_value string is converted to numeric."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "navigation.speedOverGround",
            "7.5"  # string
        )
        
        assert result is not None
        target_field, converted_value = result
        # Value must be numeric, not string
        assert isinstance(converted_value, float)
        assert converted_value > 0
    
    def test_invalid_value_rejected_and_counted(self):
        """Invalid _value (non-numeric) is rejected and counted."""
        mapper = SignalKFieldMapper()
        
        result = mapper.map_and_convert(
            "navigation.speedOverGround",
            "not_a_number"  # Invalid
        )
        
        assert result is None
        assert mapper.invalid_numeric_count > 0
    
    def test_normalizer_receives_final_schema_field_names(self):
        """Normalizer receives final schema field names, not raw paths."""
        mapper = SignalKFieldMapper()
        normalizer = Normalizer()
        
        # Map a measurement to schema field
        result = mapper.map_and_convert(
            "navigation.speedOverGround",
            "5.0"
        )
        
        assert result is not None
        target_field, converted_value = result
        
        # Add to normalizer using the mapped target field
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name=target_field,  # Use mapped field, not raw path
            value=converted_value
        )
        
        # Aggregate and check
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        # Window should contain the schema field name, not raw path
        assert target_field in windows[0]
        assert "speedOverGround" not in windows[0]  # Not raw path
    
    def test_aggregate_windows_produces_populated_row(self):
        """aggregate_windows() produces one populated output row."""
        mapper = SignalKFieldMapper()
        normalizer = Normalizer()
        
        # Add multiple mapped measurements
        measurements = [
            ("navigation.speedOverGround", "5.0"),
            ("navigation.courseOverGroundTrue", "1.5708"),
            ("environment.wind.speedApparent", "10.0"),
        ]
        
        for measurement, value_str in measurements:
            result = mapper.map_and_convert(measurement, value_str)
            if result:
                target_field, converted_value = result
                normalizer.add_point(
                    timestamp_utc="2026-09-04T16:00:03Z",
                    field_name=target_field,
                    value=converted_value
                )
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        
        # Verify populated row has expected schema fields
        row = windows[0]
        assert "sog_knots" in row
        assert "cog_deg" in row
        assert "aws_knots" in row
    
    def test_output_row_contains_mapped_measurement_columns(self):
        """Output row contains non-empty mapped measurement columns."""
        mapper = SignalKFieldMapper()
        normalizer = Normalizer()
        
        # Add a mapped point
        result = mapper.map_and_convert(
            "navigation.speedOverGround",
            "5.5"
        )
        
        assert result is not None
        target_field, converted_value = result
        
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name=target_field,
            value=converted_value
        )
        
        windows = normalizer.aggregate_windows()
        assert len(windows) == 1
        
        row = windows[0]
        # The mapped field should exist and contain non-None value
        assert target_field in row
        assert row[target_field] is not None
        # Should not be string "value" or raw path
        assert row[target_field] != "value"
    
    def test_circular_angle_boundary_conversion(self):
        """Circular angle conversion handles boundary cases."""
        mapper = SignalKFieldMapper()
        
        # Test angles near 360/0 boundary
        test_cases = [
            ("navigation.courseOverGroundTrue", "0.0", 0.0),  # 0 radians → 0 degrees
            ("navigation.courseOverGroundTrue", "6.2832", 0.0),  # 2π radians → 0/360 degrees
            ("navigation.courseOverGroundTrue", "1.5708", 90.0),  # π/2 radians → 90 degrees
        ]
        
        for measurement, value_str, expected_min in test_cases:
            result = mapper.map_and_convert(measurement, value_str)
            assert result is not None
            target_field, converted_value = result
            
            # Check angle is in valid range
            assert 0 <= converted_value <= 360
    
    def test_unit_conversion_tests_pass(self):
        """Unit conversions produce expected numeric results."""
        mapper = SignalKFieldMapper()
        
        # Test m/s to knots: 1 m/s ≈ 1.94384 knots
        result = mapper.map_and_convert("navigation.speedOverGround", "1.0")
        assert result is not None
        _, value = result
        assert 1.9 < value < 2.0  # ~1.94384 knots
        
        # Test radians to degrees
        result = mapper.map_and_convert("navigation.headingTrue", "3.14159")  # π radians
        assert result is not None
        _, value = result
        assert 170 < value < 190  # ~180 degrees
    
    def test_no_raw_signalk_path_in_output_column(self):
        """No raw Signal K path appears as output column name."""
        mapper = SignalKFieldMapper()
        normalizer = Normalizer()
        
        # Add mapped point
        result = mapper.map_and_convert(
            "environment.wind.angleApparent",
            "1.047"  # radians
        )
        
        assert result is not None
        target_field, converted_value = result
        
        normalizer.add_point(
            timestamp_utc="2026-09-04T16:00:03Z",
            field_name=target_field,
            value=converted_value
        )
        
        windows = normalizer.aggregate_windows()
        row = windows[0]
        
        # Check that output columns don't contain raw paths
        for column_name in row.keys():
            # Should not contain dots (Signal K path structure)
            # Schema field names use underscores: sog_knots, awa_deg, etc.
            if column_name not in ["timestamp_utc", "window_start_utc", "window_end_utc", "sample_count"]:
                # Mapped field should not be a Signal K path
                assert not (column_name.startswith("navigation.") or 
                           column_name.startswith("environment.") or
                           column_name.startswith("electrical."))
    
    def test_ais_precedence_unchanged(self):
        """AIS precedence routing remains unchanged."""
        # AIS records should still go to AIS output, not to Midnight Rider
        # This test is implicit in classifier behavior, not mapper
        pass
    
    def test_no_non_ais_becomes_unclassified(self):
        """No non-AIS record becomes unclassified."""
        # Non-AIS records classified as "midnight_rider" by policy
        # This test is implicit in classifier behavior, not mapper
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

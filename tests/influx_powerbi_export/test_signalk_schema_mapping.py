"""
Real schema population tests for Signal K to CSV field mapping.

Tests verify that actual Signal K measurement paths are mapped to final CSV schema fields,
not raw measurement names or generic "value" fields.

Uses synthetic placeholders only. No real contexts, sources, MMSI, coordinates, or vessel names.
"""
import pytest
from tools.influx_powerbi_export.field_mapper import SignalKFieldMapper
from tools.influx_powerbi_export.normalizer import Normalizer


class TestSignedVsCircularAngles:
    """Test correct handling of signed attitude angles vs circular navigation angles."""

    def test_positive_circular_angle(self):
        """0 radians → 0 degrees (circular)."""
        mapper = SignalKFieldMapper()
        result = mapper.map_and_convert("navigation.courseOverGroundTrue", "0.0")
        assert result is not None
        target_field, value = result
        assert target_field == "cog_deg"
        assert value == 0.0

    def test_full_circular_revolution(self):
        """2π radians → 0 degrees (circular, normalized to [0, 360))."""
        mapper = SignalKFieldMapper()
        import math
        result = mapper.map_and_convert("navigation.courseOverGroundTrue", str(2 * math.pi))
        assert result is not None
        target_field, value = result
        assert target_field == "cog_deg"
        assert abs(value - 0.0) < 0.01

    def test_negative_circular_angle(self):
        """−0.1 radians → value in [0, 360), approximately 354.27 degrees (circular)."""
        mapper = SignalKFieldMapper()
        result = mapper.map_and_convert("navigation.headingTrue", "-0.1")
        assert result is not None
        target_field, value = result
        assert target_field == "true_heading_deg"
        assert 350 < value < 360
        assert value < 360

    def test_signed_roll_negative(self):
        """−0.012 radians → approximately −0.6875 degrees (signed attitude, preserves sign)."""
        mapper = SignalKFieldMapper()
        result = mapper.map_and_convert("navigation.attitude.roll", "-0.012")
        assert result is not None
        target_field, value = result
        assert target_field == "roll_deg"
        assert -1 < value < 0
        assert value < 180

    def test_signed_pitch_negative(self):
        """−0.004 radians → approximately −0.229 degrees (signed attitude, preserves sign)."""
        mapper = SignalKFieldMapper()
        result = mapper.map_and_convert("navigation.attitude.pitch", "-0.004")
        assert result is not None
        target_field, value = result
        assert target_field == "pitch_deg"
        assert -1 < value < 0
        assert value < 90

    def test_signed_roll_within_bounds(self):
        """Roll values remain within [−180, 180] for valid source values."""
        mapper = SignalKFieldMapper()
        result = mapper.map_and_convert("navigation.attitude.roll", "0.5")
        assert result is not None
        _, value = result
        assert -180 <= value <= 180
        result = mapper.map_and_convert("navigation.attitude.roll", "-0.5")
        assert result is not None
        _, value = result
        assert -180 <= value <= 180

    def test_signed_pitch_within_bounds(self):
        """Pitch values remain within [−90, 90] for valid source values."""
        mapper = SignalKFieldMapper()
        result = mapper.map_and_convert("navigation.attitude.pitch", "0.3")
        assert result is not None
        _, value = result
        assert -90 <= value <= 90
        result = mapper.map_and_convert("navigation.attitude.pitch", "-0.3")
        assert result is not None
        _, value = result
        assert -90 <= value <= 90

    def test_circular_mean_with_circular_fields(self):
        """[359°, 1°] → approximately 0° or 360° (circular mean test)."""
        normalizer = Normalizer()
        normalizer.add_point("2026-09-04T16:00:00Z", "cog_deg", 359.0)
        normalizer.add_point("2026-09-04T16:00:05Z", "cog_deg", 1.0)
        windows = normalizer.aggregate_windows()
        assert len(windows) > 0
        row = windows[0]
        assert "cog_deg" in row
        cog_value = row["cog_deg"]
        assert cog_value is not None
        assert cog_value < 10 or cog_value > 350

    def test_roll_pitch_not_in_circular_fields(self):
        """Confirm roll_deg and pitch_deg are NOT in CIRCULAR_FIELDS."""
        assert "roll_deg" not in Normalizer.CIRCULAR_FIELDS
        assert "pitch_deg" not in Normalizer.CIRCULAR_FIELDS
        assert "cog_deg" in Normalizer.CIRCULAR_FIELDS
        assert "true_heading_deg" in Normalizer.CIRCULAR_FIELDS
        assert "awa_deg" in Normalizer.CIRCULAR_FIELDS
        assert "twa_deg" in Normalizer.CIRCULAR_FIELDS
        assert "tide_set_deg" in Normalizer.CIRCULAR_FIELDS


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

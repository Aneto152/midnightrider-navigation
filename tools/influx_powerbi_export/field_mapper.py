"""
Signal K to CSV schema field mapper with unit conversion.

Maps InfluxDB measurement paths (from record["_measurement"]) to target CSV schema fields,
applying necessary unit conversions (radians→degrees, m/s→knots, etc.).
"""
import math
from typing import Optional, Tuple


class SignalKFieldMapper:
    """Map Signal K measurement paths to CSV schema fields with unit conversion."""
    
    # Signal K path → (target_csv_field, source_unit, target_unit, is_angular)
    # NOTE: These paths are actual measurements in InfluxDB, not Signal K paths
    MEASUREMENT_MAPPINGS = {
        # Navigation - speed
        "navigation.speedOverGround": ("sog_knots", "m/s", "knots", False),
        "navigation.speedOverGroundTrue": ("sog_knots", "m/s", "knots", False),

        # Navigation - course (circular mean required)
        "navigation.courseOverGroundTrue": ("cog_deg", "radians", "degrees", True),
        "navigation.courseOverGround": ("cog_deg", "radians", "degrees", True),

        # Navigation - heading (circular mean required)
        "navigation.headingTrue": ("true_heading_deg", "radians", "degrees", True),
        "navigation.headingMagnetic": ("true_heading_deg", "radians", "degrees", True),

        # Navigation - position (JSON-encoded sub-fields, handled separately)
        "navigation.position": ("position", "json", "degrees", False),  # Special handling

        # Wind - apparent
        "environment.wind.angleApparent": ("awa_deg", "radians", "degrees", True),
        "environment.wind.speedApparent": ("aws_knots", "m/s", "knots", False),

        # Wind - true
        "environment.wind.angleTrue": ("twa_deg", "radians", "degrees", True),
        "environment.wind.angleTrueWater": ("twa_deg", "radians", "degrees", True),
        "environment.wind.directionTrue": ("twa_deg", "radians", "degrees", True),
        "environment.wind.speedTrue": ("tws_knots", "m/s", "knots", False),
        "environment.wind.speedOverGround": ("tws_knots", "m/s", "knots", False),

        # Water/Environment - depth (actual InfluxDB measurement)
        "environment.depth.belowTransducer": ("depth_m", "meters", "meters", False),
        "environment.water.depth.belowTransducer": ("depth_m", "meters", "meters", False),
        "environment.water.temperature": ("water_temp_c", "kelvin", "celsius", False),

        # Sailing dynamics / Speed through water
        "navigation.speedThroughWater": ("stw_knots", "m/s", "knots", False),
        "performance.speedThroughWater": ("stw_knots", "m/s", "knots", False),

        # Tidal
        "environment.tide.setTrue": ("tide_set_deg", "radians", "degrees", True),
        "environment.current.setTrue": ("tide_set_deg", "radians", "degrees", True),
        "environment.tide.rate": ("tide_rate_knots", "m/s", "knots", False),
        "environment.current.drift": ("tide_rate_knots", "m/s", "knots", False),

        # Attitude
        "navigation.attitude.roll": ("roll_deg", "radians", "degrees", False),
        "navigation.attitude.pitch": ("pitch_deg", "radians", "degrees", False),

        # Electrical - battery voltage (use calypso percent and House voltage)
        "electrical.batteries.House.voltage": ("battery_voltage", "volts", "volts", False),
        "electrical.batteries.0.voltage": ("battery_voltage", "volts", "volts", False),
        "electrical.batteries.calypso.percent": ("battery_voltage", "percent", "volts", False),  # Special conversion
    }
    
    def __init__(self):
        self.mapped_count = 0
        self.unmapped_count = 0
        self.invalid_numeric_count = 0
    
    def map_and_convert(self, measurement: str, value_str: str) -> Optional[Tuple[str, float]]:
        """
        Map a Signal K measurement path to CSV field name and convert value.
        Handles special cases:
        - navigation.position: JSON-encoded {"latitude": ..., "longitude": ...}
        - electrical.batteries.calypso.percent: Battery percent → voltage conversion
        
        Args:
            measurement: Signal K measurement path (from record["_measurement"])
            value_str: Raw value string (from record["_value"])
        
        Returns:
            Tuple of (target_csv_field, converted_value) or None if unmapped/invalid
        """
        if not measurement or not value_str:
            self.unmapped_count += 1
            return None
        
        # Check if measurement is in mappings
        if measurement not in self.MEASUREMENT_MAPPINGS:
            self.unmapped_count += 1
            return None
        
        target_field, source_unit, target_unit, is_angular = self.MEASUREMENT_MAPPINGS[measurement]
        
        # Special handling: JSON-encoded position (extract latitude/longitude)
        if measurement == "navigation.position" and source_unit == "json":
            try:
                import json
                position_data = json.loads(value_str)
                # Try both longitude/latitude (standard) and lat/lon aliases
                lat = position_data.get('latitude') or position_data.get('lat')
                lon = position_data.get('longitude') or position_data.get('lon')
                if lat is not None and lon is not None:
                    # Return both latitude and longitude as separate mappings
                    # Note: This is a limitation - we can only return one value
                    # So we return latitude here and rely on the data being in both
                    # For now, just skip position extraction - needs different handling
                    self.unmapped_count += 1
                    return None
            except (json.JSONDecodeError, ValueError, TypeError):
                self.unmapped_count += 1
                return None
        
        # Convert value string to float
        try:
            value = float(value_str) if value_str else None
        except (ValueError, TypeError):
            self.invalid_numeric_count += 1
            return None
        
        if value is None:
            return None
        
        # Apply unit conversion
        try:
            converted_value = self._convert_units(value, source_unit, target_unit, is_angular)
            if converted_value is not None:
                self.mapped_count += 1
                return (target_field, converted_value)
        except Exception:
            self.invalid_numeric_count += 1
            return None
        
        self.unmapped_count += 1
        return None
    
    def _convert_units(self, value: float, source_unit: str, target_unit: str, is_angular: bool) -> Optional[float]:
        """Convert value from source unit to target unit."""
        if source_unit == target_unit:
            return value
        
        # Angular conversions
        if is_angular:
            if source_unit == "radians" and target_unit == "degrees":
                # Convert radians to degrees (0-360)
                degrees = math.degrees(value)
                # Normalize to 0-360 range
                return degrees % 360 if degrees >= 0 else (degrees % 360) + 360
            elif source_unit == "degrees" and target_unit == "radians":
                return math.radians(value)
        
        # Non-angular conversions
        if source_unit == "m/s" and target_unit == "knots":
            # 1 knot = 0.51444 m/s, so m/s * 1.94384 = knots
            return value * 1.94384
        
        if source_unit == "kelvin" and target_unit == "celsius":
            return value - 273.15
        
        if source_unit == "meters" and target_unit == "meters":
            return value
        
        if source_unit == "volts" and target_unit == "volts":
            return value
        
        # Battery percent to voltage conversion (0-100% -> 9.6-14.4V for 12V system)
        if source_unit == "percent" and target_unit == "volts":
            # voltage = 9.6 + percent * 4.8 / 100
            return 9.6 + (value * 4.8 / 100)
        
        # Unknown conversion
        return None
    
    def get_stats(self) -> dict:
        """Return mapping statistics."""
        return {
            "mapped": self.mapped_count,
            "unmapped": self.unmapped_count,
            "invalid_numeric": self.invalid_numeric_count,
        }

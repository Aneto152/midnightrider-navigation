"""
Classifier for Midnight Rider export.

Policy: AIS records isolated to separate CSV, all non-AIS records treated as onboard data.
- AIS detection uses highest-precedence rules (source, context, measurement)
- All non-AIS records classified as "midnight_rider" onboard data
- No unclassified fallback
"""

class Classifier:
    """Classify records as AIS or Midnight Rider onboard data."""
    
    def __init__(self):
        """Initialize classifier with AIS detection patterns."""
        # AIS measurement families (boundary-safe matching)
        self.ais_measurement_prefixes = [
            "sensors.ais",      # sensors.ais.*
            "offposition",      # offPosition.* (case-insensitive)
        ]
    
    def _is_ais_measurement(self, measurement):
        """Check if measurement matches any AIS measurement family with boundary-safe matching.
        
        Boundary-safe: exact match OR match followed by dot separator.
        Examples:
            - "sensors.ais.target" matches "sensors.ais" (has dot after prefix)
            - "sensors.aiscope" does NOT match "sensors.ais" (no dot after prefix)
            - "offposition.record" matches "offposition" (has dot after prefix)
        """
        measurement_lower = measurement.lower()
        
        for prefix in self.ais_measurement_prefixes:
            # Exact match or match with dot separator (boundary-safe)
            if measurement_lower == prefix or measurement_lower.startswith(prefix + "."):
                return True
        
        return False
    
    def classify(self, record):
        """
        Classify a single record.
        
        Args:
            record: Dict with at least source, context, _measurement fields
        
        Returns:
            "ais" if record matches AIS patterns (highest precedence)
            "midnight_rider" for all non-AIS records (onboard data)
        
        Policy:
            - AIS is highest priority (checked first)
            - All remaining records are onboard data
            - No unclassified fallback
        """
        
        # Extract fields safely
        source = record.get("source", "").lower()
        context = record.get("context", "").lower()
        measurement = record.get("_measurement", "").lower()
        
        # AIS detection (highest precedence - checked first)
        
        # Check source for AIS substring
        if "ais" in source:
            return "ais"
        
        # Check context for MMSI URN pattern (valid AIS identifier)
        if "mmsi" in context and "urn" in context:
            return "ais"
        
        # Check measurement for AIS measurement families (boundary-safe)
        if self._is_ais_measurement(measurement):
            return "ais"
        
        # All non-AIS records are Midnight Rider onboard data
        return "midnight_rider"

    @staticmethod
    def get_description(category):
        """Get human-readable description of classification."""
        descriptions = {
            "ais": "AIS vessel data (isolated to separate CSV)",
            "midnight_rider": "Midnight Rider onboard instrument data",
        }
        return descriptions.get(category, "Unknown")

    @staticmethod
    def is_valid_category(category):
        """Check if category is valid."""
        return category in ["ais", "midnight_rider"]

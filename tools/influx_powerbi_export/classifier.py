"""
Classification rules for Midnight Rider vs. AIS events.
"""
from typing import Dict, Optional, Literal

class Classifier:
    """Classify InfluxDB records into Midnight Rider or AIS categories."""
    
    MIDNIGHT_RIDER_MEASUREMENTS = {
        "navigation", "environment", "sensors", "electrical", "performance"
    }
    
    AIS_MEASUREMENTS = {
        "sensors.ais", "virtual", "offPosition", "notifications.ais"
    }
    
    def classify(self, record: Dict) -> Literal["midnight_rider", "ais", "unclassified"]:
        """
        Classify a single InfluxDB record.
        
        Rules:
        1. Midnight Rider: self="true" OR self=(empty) AND measurement in navigation/sensors/etc.
        2. AIS: context contains MMSI URN OR measurement in sensors.ais/virtual/offPosition
        3. Unclassified: neither rule matches
        """
        measurement = record.get("_measurement", "")
        self_tag = record.get("self", "")
        context_tag = record.get("context", "")
        
        # Check AIS first (more specific)
        if self._is_ais(measurement, context_tag):
            return "ais"
        
        # Check Midnight Rider
        if self._is_midnight_rider(measurement, self_tag):
            return "midnight_rider"
        
        return "unclassified"
    
    def _is_ais(self, measurement: str, context: str) -> bool:
        """Check if record is AIS."""
        # AIS measurements
        for ais_meas in self.AIS_MEASUREMENTS:
            if measurement.startswith(ais_meas):
                return True
        
        # MMSI URN in context
        if context and "urn:mrn:imo:mmsi" in context:
            return True
        
        # atons/shore context
        if context and ("atons" in context or "shore" in context):
            return True
        
        return False
    
    def _is_midnight_rider(self, measurement: str, self_tag: str) -> bool:
        """Check if record is Midnight Rider."""
        # Must have self tag (true or empty)
        if self_tag is None or self_tag == "":
            self_ok = True
        elif self_tag == "true":
            self_ok = True
        else:
            self_ok = False
        
        if not self_ok:
            return False
        
        # Must be navigation/sensors/environment measurement
        for prefix in self.MIDNIGHT_RIDER_MEASUREMENTS:
            if measurement.startswith(prefix):
                return True
        
        return False
    
    def validate_self_tag(self, records: int, self_true: int, self_empty: int) -> Dict:
        """Validate self tag distribution."""
        return {
            "total_records": records,
            "self_true": self_true,
            "self_empty": self_empty,
            "self_other": records - self_true - self_empty,
            "self_true_ratio": self_true / records if records > 0 else 0,
            "self_empty_ratio": self_empty / records if records > 0 else 0,
        }

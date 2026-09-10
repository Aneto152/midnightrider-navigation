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
        Classify a single InfluxDB record into category: midnight_rider, ais, or unclassified.
        
        Precedence (highest to lowest):
        1. Explicit AIS context (MMSI URN, AToN, shore contexts, AIS measurements)
        2. Explicit self=="true" ONLY (no empty or missing self accepted)
        3. Confirmed self-vessel context (future: schema-validated allowlist)
        4. Unclassified (default for ambiguous records)
        
        Safety rules:
        - Missing self is NOT treated as empty/valid.
        - Empty self="" does NOT prove self-vessel identity.
        - Generic measurement families (navigation, environment, etc.) do NOT prove self-vessel.
        - AIS precedence is enforced even when self=="true".
        """
        measurement = record.get("_measurement", "")
        self_tag = record.get("self", None)  # Preserve None to distinguish from empty string
        context_tag = record.get("context", "")
        
        # STEP 1: Explicit AIS context detection (highest precedence)
        if self._is_ais(measurement, context_tag):
            return "ais"
        
        # STEP 2: Explicit self-vessel validation (only after AIS check fails)
        if self._is_midnight_rider(measurement, self_tag):
            return "midnight_rider"
        
        # STEP 3: Confirmed self-vessel context (future: schema-validated allowlist)
        # TODO: Implement schema-validated self-vessel context after validation
        # if self._is_confirmed_self_vessel_context(context_tag):
        #     return "midnight_rider"
        
        # STEP 4: Default for all ambiguous cases (missing/empty self, missing context, etc.)
        return "unclassified"
    
    def _is_ais(self, measurement: str, context: str) -> bool:
        """
        Check if record is AIS.
        
        Uses boundary-safe pattern matching to avoid false positives:
        - MMSI URN: Specific substring (low false-positive risk)
        - sensors.ais: Exact prefix or with dot boundary
        - virtual: Disabled pending schema validation (too broad)
        - offPosition: Exact prefix or with dot boundary
        - AToN/shore: Disabled pending schema validation (URN format not confirmed)
        """
        # AIS measurements with boundary-safe checks
        if self._is_ais_measurement(measurement):
            return True
        
        # MMSI URN in context (specific URN; low false-positive risk)
        if context and "urn:mrn:imo:mmsi" in context:
            return True
        
        # AToN/shore context disabled pending schema validation
        # Previous substring matching ("atons" in context, "shore" in context)
        # caused false positives on non-URN strings (atonscope, shorebased, lakeshore).
        # TODO: Re-enable after validating exact URN schema:
        # if context and self._matches_aton_urn(context):
        #     return True
        # if context and self._matches_shore_urn(context):
        #     return True
        
        return False
    
    def _is_ais_measurement(self, measurement: str) -> bool:
        """
        Check if measurement is a known AIS measurement family.
        
        Uses exact prefix or boundary-safe matching to avoid false positives:
        - sensors.ais: Match exact or with dot boundary (e.g., sensors.ais.target)
        - offPosition: Match exact or with dot boundary
        - virtual: DISABLED — startswith("virtual") too broad; catches non-AIS virtual.* records
        - notifications.ais: Match exact or with dot boundary
        
        Note: "virtual" is in AIS_MEASUREMENTS but disabled here due to ambiguity.
        """
        if measurement.startswith("sensors.ais"):
            # Exact match or followed by dot (e.g., sensors.ais.target)
            if measurement == "sensors.ais" or measurement.startswith("sensors.ais."):
                return True
        
        if measurement.startswith("offPosition"):
            # Exact match or followed by dot
            if measurement == "offPosition" or measurement.startswith("offPosition."):
                return True
        
        if measurement.startswith("notifications.ais"):
            # Exact match or followed by dot
            if measurement == "notifications.ais" or measurement.startswith("notifications.ais."):
                return True
        
        # virtual: DISABLED pending schema validation
        # Previous rule: startswith("virtual") matches too many non-AIS records.
        # Re-enable only after confirming exact allowed virtual subdomains (e.g., virtual.ais.*)
        # if measurement.startswith("virtual.ais"):
        #     if measurement == "virtual.ais" or measurement.startswith("virtual.ais."):
        #         return True
        
        return False
    
    def _is_midnight_rider(self, measurement: str, self_tag: str) -> bool:
        """
        Check if record is Midnight Rider.
        
        CORRECTED LOGIC:
        - Explicit self=="true" is REQUIRED (not empty, not missing).
        - Empty self or missing self are treated as ambiguous; return False.
        - Generic measurement families ALONE do NOT prove self-vessel identity.
        - This method is called ONLY after AIS detection fails, so AIS precedence is preserved.
        
        Note: A future confirmed self-vessel context (schema-validated) may be added
        as an additional proof mechanism, but is NOT implemented in this version.
        """
        # CORRECTED: Only accept explicit self=="true" (not None, not empty string)
        if self_tag != "true":
            return False
        
        # Generic measurement family check (kept for documentation)
        # Note: Measurement family alone is NOT sufficient proof of self-vessel without
        # explicit self=="true" AND potential future validated context.
        # This check is retained only because self_tag=="true" passed above,
        # AND AIS detection already failed (called only after AIS check).
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

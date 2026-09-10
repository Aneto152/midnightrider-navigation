"""
Classification rules for Midnight Rider vs. AIS events.

Supports:
1. Exact AIS classification (highest precedence)
2. Validated self-vessel context matching (Signal K baseDeltas.json)
3. Explicit self=="true" tag (backward compatibility)
4. Unclassified (default for ambiguous records)
"""
from typing import Dict, Optional, Literal, Set
from pathlib import Path

from .self_context import SelfContextValidator


class Classifier:
    """Classify InfluxDB records into Midnight Rider or AIS categories."""
    
    MIDNIGHT_RIDER_MEASUREMENTS = {
        "navigation", "environment", "sensors", "electrical", "performance"
    }
    
    AIS_MEASUREMENTS = {
        "sensors.ais", "virtual", "offPosition", "notifications.ais"
    }
    
    def __init__(self, self_context_validator: Optional[SelfContextValidator] = None):
        """
        Initialize classifier with optional self-context validator.
        
        Args:
            self_context_validator: Validator for canonical self-vessel contexts.
                                   If None, will be initialized with default Signal K path.
        """
        if self_context_validator is None:
            # Load canonical contexts from Signal K baseDeltas.json at runtime
            try:
                self.self_context_validator = SelfContextValidator()
            except ValueError:
                # Canonical source unavailable; exact context matching disabled
                self.self_context_validator = None
        else:
            self.self_context_validator = self_context_validator
    
    def classify(self, record: Dict) -> Literal["midnight_rider", "ais", "unclassified"]:
        """
        Classify a single InfluxDB record into category: midnight_rider, ais, or unclassified.
        
        Precedence (highest to lowest):
        1. Explicit AIS context (MMSI URN, AToN, shore contexts, AIS measurements)
        2. Exact canonical self-vessel context match (validated from Signal K baseDeltas.json)
        3. Explicit self=="true" ONLY (for backward compatibility)
        4. Unclassified (default for ambiguous records)
        
        Safety rules:
        - AIS precedence is absolute, even if other fields suggest self-vessel.
        - Exact canonical context matching is required; generic patterns are rejected.
        - Missing self is NOT treated as empty/valid.
        - Empty self="" does NOT prove self-vessel identity.
        - Generic measurement families (navigation, environment, etc.) do NOT prove self-vessel alone.
        """
        measurement = record.get("_measurement", "")
        self_tag = record.get("self", None)  # Preserve None to distinguish from empty string
        context_tag = record.get("context", "")
        
        # STEP 1: Explicit AIS context detection (highest precedence — absolute)
        if self._is_ais(measurement, context_tag):
            return "ais"
        
        # STEP 2: Exact canonical self-vessel context match (validated at runtime)
        if self._is_canonical_self_context(measurement, context_tag):
            return "midnight_rider"
        
        # STEP 3: Explicit self-vessel validation with self=="true" (backward compatibility)
        if self._is_midnight_rider(measurement, self_tag):
            return "midnight_rider"
        
        # STEP 4: Default for all ambiguous cases
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
    
    def _is_canonical_self_context(self, measurement: str, context_tag: str) -> bool:
        """
        Check if context value matches the canonical self-vessel identity.
        
        Uses exact matching against the validated canonical contexts loaded from
        Signal K baseDeltas.json at runtime. Never uses generic patterns.
        
        Args:
            measurement: InfluxDB _measurement field (checked for self-vessel families)
            context_tag: InfluxDB context field (checked for exact canonical match)
        
        Returns:
            True if context matches exactly any canonical identity AND
            measurement is in a self-vessel family, False otherwise.
        """
        # Only proceed if canonical validator is available
        if self.self_context_validator is None:
            return False
        
        # Require exact match against canonical identity (in-memory comparison)
        if not self.self_context_validator.is_self_vessel(context_tag):
            return False
        
        # Require measurement to be in self-vessel family
        # (non-AIS instrument data families)
        for prefix in self.MIDNIGHT_RIDER_MEASUREMENTS:
            if measurement.startswith(prefix):
                return True
        
        return False
    
    def _is_midnight_rider(self, measurement: str, self_tag: str) -> bool:
        """
        Check if record is Midnight Rider via explicit self tag (backward compatibility).
        
        CORRECTED LOGIC:
        - Explicit self=="true" is REQUIRED (not empty, not missing).
        - Empty self or missing self are treated as ambiguous; return False.
        - Generic measurement families ALONE do NOT prove self-vessel identity.
        - This method is called ONLY after canonical context and AIS detection fail.
        
        Note: This check exists for backward compatibility with records that have
        explicit self=="true" tagging. The primary classification path is now via
        exact canonical context matching (see _is_canonical_self_context).
        """
        # Only accept explicit self=="true" (not None, not empty string)
        if self_tag != "true":
            return False
        
        # Require measurement to be in self-vessel family
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

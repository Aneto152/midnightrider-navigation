"""
Unit tests for classification logic.
"""
import pytest
from tools.influx_powerbi_export.classifier import Classifier

@pytest.fixture
def classifier():
    return Classifier()

def test_midnight_rider_with_self_true(classifier):
    """self=true with navigation measurement → Midnight Rider"""
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_unclassified_with_self_empty(classifier):
    """self=(empty) with sensors measurement → Midnight Rider (non-AIS onboard data)
    
    CORRECTED: Non-AIS sensors measurement with empty self is classified as midnight_rider.
    Policy: All non-AIS records are onboard Midnight Rider data.
    """
    record = {
        "_measurement": "sensors.wit.quaternion.w",
        "self": "",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_ais_with_mmsi_context(classifier):
    """MMSI URN in context → AIS"""
    record = {
        "_measurement": "sensors.ais.class",
        "context": "vessels.urn:mrn:imo:mmsi:636024194",
        "self": "",
    }
    assert classifier.classify(record) == "ais"

def test_ais_measurement(classifier):
    """sensors.ais measurement → AIS"""
    record = {
        "_measurement": "sensors.ais.fromBow",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "ais"

def test_virtual_measurement_with_mmsi_context(classifier):
    """Non-AIS measurement with MMSI URN context → AIS (AIS precedence)
    
    CORRECTED: Explicit MMSI URN in context triggers AIS classification (AIS precedence).
    Non-AIS measurements are overridden by AIS context markers.
    """
    record = {
        "_measurement": "virtual",
        "self": "",
        "context": "atons.urn:mrn:imo:mmsi:993672062",
    }
    # MMSI URN in context triggers AIS due to AIS precedence
    assert classifier.classify(record) == "ais"

def test_unclassified(classifier):
    """Unknown measurement with no AIS markers → Midnight Rider
    
    Policy: All non-AIS records (including unknown measurements) are classified as midnight_rider.
    """
    record = {
        "_measurement": "unknown.metric",
        "self": "unknown_value",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

# NEW TARGETED TESTS FOR CORRECTED LOGIC

def test_missing_self_with_navigation(classifier):
    """Missing self + navigation measurement → Midnight Rider
    
    CORRECTED: Non-AIS measurements without AIS markers are classified as midnight_rider.
    Policy: All non-AIS records are onboard data.
    """
    record = {
        "_measurement": "navigation.position",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_missing_self_with_environment(classifier):
    """Missing self + environment measurement → Midnight Rider
    
    Policy: All non-AIS records are onboard Midnight Rider data.
    """
    record = {
        "_measurement": "environment.outside.temperature",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_missing_self_with_electrical(classifier):
    """Missing self + electrical measurement → Midnight Rider
    
    Policy: All non-AIS records are onboard Midnight Rider data.
    """
    record = {
        "_measurement": "electrical.batteries.0.voltage",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_self_false_with_navigation(classifier):
    """self=false + navigation → Midnight Rider
    
    CORRECTED: Non-AIS measurements (regardless of self value) are classified as midnight_rider.
    Policy: All non-AIS records are onboard data.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "false",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_atonscope_false_positive_prevention(classifier):
    """atonscope in context → Unclassified (not AIS)
    
    CORRECTED: Substring matching "atons" is DISABLED pending URN schema validation.
    This prevents false positives on non-URN strings like 'atonscope'.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "atonscope_config",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_shorebased_false_positive_prevention(classifier):
    """shorebased in context → Not classified as AIS
    
    CORRECTED: Substring matching "shore" is DISABLED pending URN schema validation.
    This prevents false positives on non-URN strings like 'shorebased'.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "shorebased_facility",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_sensors_ais_boundary_safe(classifier):
    """sensors.ais.target → AIS (boundary-safe matching)
    
    CORRECTED: Boundary-safe prefix matching prevents false positives
    on strings like 'sensors.aiscope'.
    """
    record = {
        "_measurement": "sensors.ais.target",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "ais"

def test_sensors_aiscope_not_ais(classifier):
    """sensors.aiscope → Midnight Rider (boundary-safe blocking)
    
    CORRECTED: 'sensors.aiscope' does NOT match 'sensors.ais.*' (no dot separator).
    Boundary-safe matching requires exact or prefix with dot.
    """
    record = {
        "_measurement": "sensors.aiscope",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_offposition_boundary_safe(classifier):
    """offposition.record → AIS (boundary-safe matching)
    
    CORRECTED: offposition.* (case-insensitive) measurement family is AIS and is detected
    by boundary-safe prefix matching (exact or with dot).
    """
    record = {
        "_measurement": "offposition.record",
        "self": "",
        "context": "",
    }
    # offposition.* is AIS measurement family; boundary-safe match returns ais
    assert classifier.classify(record) == "ais"

def test_missing_measurement(classifier):
    """Missing measurement + self=true → Midnight Rider (non-AIS fallback)
    
    CORRECTED: When _measurement is missing, it defaults to empty string "".
    Empty string doesn't match any AIS patterns.
    Classifier returns midnight_rider (non-AIS fallback policy).
    
    Note: This reflects the corrected logic:
    self=true REQUIRES a valid measurement family; empty/missing measurement alone is insufficient.
    """
    record = {
        "self": "true",
        "context": "",
    }
    # Missing measurement defaults to empty string; no AIS patterns match
    # Classifier returns midnight_rider (non-AIS fallback policy)
    assert classifier.classify(record) == "midnight_rider"

def test_self_true_mmsi_ais_precedence(classifier):
    """self=true + MMSI URN context → AIS (AIS precedence enforced)
    
    CORRECTED: Explicit MMSI URN in context triggers AIS classification (AIS precedence).
    Even non-AIS measurements are overridden by valid AIS context markers.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "vessels.urn:mrn:imo:mmsi:636024194",
    }
    assert classifier.classify(record) == "ais"

def test_empty_measurement_with_self_true(classifier):
    """Empty _measurement + self=true → Midnight Rider (non-AIS fallback)
    
    CORRECTED: Empty measurement (0-length string) doesn't match any AIS patterns.
    Classifier returns midnight_rider (non-AIS fallback policy).
    """
    record = {
        "_measurement": "",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_valid_aton_context_with_mmsi_urn(classifier):
    """AToN with explicit MMSI URN context → AIS
    
    CORRECTED: Explicit MMSI URN in context (regardless of measurement or self value)
    triggers AIS classification due to AIS precedence.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "atons.urn:mrn:imo:mmsi:993672062",
    }
    assert classifier.classify(record) == "ais"

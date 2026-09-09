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
    """self=(empty) with sensors measurement → Unclassified (not Midnight Rider)
    
    CORRECTED: Empty self does NOT prove self-vessel identity.
    Only explicit self=="true" is accepted.
    """
    record = {
        "_measurement": "sensors.wit.quaternion.w",
        "self": "",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

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
    """virtual measurement with MMSI context → AIS (AIS precedence)
    
    CORRECTED: virtual measurement matching is DISABLED pending schema validation.
    However, MMSI URN in context still triggers AIS classification (AIS precedence).
    AToN substring matching ("atons") is disabled, but MMSI URN substring match remains.
    """
    record = {
        "_measurement": "virtual",
        "self": "",
        "context": "atons.urn:mrn:imo:mmsi:993672062",
    }
    # MMSI URN in context triggers AIS despite virtual and atons being disabled
    assert classifier.classify(record) == "ais"

def test_unclassified(classifier):
    """Unknown measurement with no context → Unclassified"""
    record = {
        "_measurement": "unknown.metric",
        "self": "unknown_value",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

# NEW TARGETED TESTS FOR CORRECTED LOGIC

def test_missing_self_with_navigation(classifier):
    """Missing self + navigation measurement → Unclassified
    
    CORRECTED: Missing self is NOT treated as empty/valid.
    Generic measurement alone does NOT prove self-vessel identity.
    """
    record = {
        "_measurement": "navigation.position",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

def test_missing_self_with_environment(classifier):
    """Missing self + environment measurement → Unclassified"""
    record = {
        "_measurement": "environment.outside.temperature",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

def test_missing_self_with_electrical(classifier):
    """Missing self + electrical measurement → Unclassified"""
    record = {
        "_measurement": "electrical.batteries.0.voltage",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

def test_self_false_with_navigation(classifier):
    """self=false + navigation → Unclassified
    
    Explicitly false self means this is NOT Midnight Rider.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "false",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

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
    """sensors.aiscope → Not AIS (boundary-safe blocking)
    
    CORRECTED: 'sensors.aiscope' does NOT match 'sensors.ais.*' boundary check.
    Requires dot separator.
    """
    record = {
        "_measurement": "sensors.aiscope",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_offPosition_boundary_safe(classifier):
    """offPosition.record → AIS (boundary-safe matching)
    
    CORRECTED: offPosition.* measurement family is AIS and is detected by boundary-safe
    prefix matching (exact or with dot). Empty self does NOT affect AIS detection
    due to AIS precedence.
    """
    record = {
        "_measurement": "offPosition.record",
        "self": "",
        "context": "",
    }
    # offPosition.* is AIS measurement family; boundary-safe match returns ais
    assert classifier.classify(record) == "ais"

def test_missing_measurement(classifier):
    """Missing measurement + self=true → Midnight Rider (measurement defaults to empty string)
    
    When _measurement is missing, it defaults to empty string "".
    Empty string doesn't match any AIS measurement or Midnight Rider measurement.
    With self=true and no AIS detection, classifier returns midnight_rider.
    
    Note: This reflects the corrected logic:
    measurement absence doesn't prevent self-vessel classification.
    """
    record = {
        "self": "true",
        "context": "",
    }
    # self=true with no AIS detection returns midnight_rider
    assert classifier.classify(record) == "midnight_rider"

def test_self_true_mmsi_ais_precedence(classifier):
    """self=true + MMSI context → AIS (AIS precedence enforced)
    
    Even with self=true, explicit MMSI context takes precedence.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "vessels.urn:mrn:imo:mmsi:636024194",
    }
    assert classifier.classify(record) == "ais"

def test_empty_measurement_with_self_true(classifier):
    """Empty _measurement + self=true → Midnight Rider
    
    CORRECTED: Empty measurement (0-length string) doesn't match any prefix,
    but self=true passes, so returns midnight_rider.
    Note: Differs from missing_measurement test (both result in midnight_rider).
    """
    record = {
        "_measurement": "",
        "self": "true",
        "context": "",
    }
    assert classifier.classify(record) == "midnight_rider"

def test_valid_aton_context_with_mmsi_urn(classifier):
    """AToN with explicit MMSI URN → AIS
    
    CORRECTED: Broad AToN substring matching ("atons") is disabled pending URN validation.
    However, explicit MMSI URN in context still triggers AIS.
    """
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "atons.urn:mrn:imo:mmsi:993672062",
    }
    assert classifier.classify(record) == "ais"

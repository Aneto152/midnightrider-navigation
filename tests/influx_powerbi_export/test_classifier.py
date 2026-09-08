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

def test_midnight_rider_with_self_empty(classifier):
    """self=(empty) with sensors measurement → Midnight Rider"""
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

def test_virtual_measurement(classifier):
    """virtual measurement → AIS"""
    record = {
        "_measurement": "virtual",
        "self": "",
        "context": "atons.urn:mrn:imo:mmsi:993672062",
    }
    assert classifier.classify(record) == "ais"

def test_unclassified(classifier):
    """Unknown measurement with no context → Unclassified"""
    record = {
        "_measurement": "unknown.metric",
        "self": "unknown_value",
        "context": "",
    }
    assert classifier.classify(record) == "unclassified"

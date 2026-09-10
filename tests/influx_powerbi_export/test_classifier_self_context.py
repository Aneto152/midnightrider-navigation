"""
Unit tests for self-vessel context classification.

Tests cover:
1. Exact canonical context matching (new)
2. AIS precedence (unchanged)
3. Backward compatibility with self=="true" (unchanged)
4. Unclassified for ambiguous records (unchanged)
"""
import pytest
from unittest.mock import Mock

from tools.influx_powerbi_export.classifier import Classifier
from tools.influx_powerbi_export.self_context import SelfContextValidator


# Test fixture: Mock canonical context validator with known contexts
@pytest.fixture
def mock_validator():
    """Create a mock validator with a known canonical context."""
    validator = Mock(spec=SelfContextValidator)
    
    # Simulated canonical identity (e.g., Signal K UUID)
    # The actual value is NOT exposed in code or tests
    # Using a generic placeholder value for testing only
    canonical_uuid = "<CANONICAL_SELF_VESSEL_IDENTITY_PLACEHOLDER>"
    
    def is_self_vessel_side_effect(context_value):
        """Check if context matches canonical identity."""
        if context_value is None:
            return False
        # Exact match (case-insensitive after normalization)
        return context_value.strip().lower() == canonical_uuid.lower()
    
    validator.is_self_vessel.side_effect = is_self_vessel_side_effect
    validator.has_canonical_contexts.return_value = True
    
    return validator, canonical_uuid


@pytest.fixture
def classifier_with_mock(mock_validator):
    """Create classifier with mocked self-context validator."""
    validator, canonical_uuid = mock_validator
    return Classifier(self_context_validator=validator), canonical_uuid


@pytest.fixture
def classifier_without_context():
    """Create classifier with no self-context validator (canonical source unavailable)."""
    classifier = Classifier()
    classifier.self_context_validator = None
    return classifier


# PHASE 5 TESTS: Canonical Context Matching (NEW)

def test_canonical_context_with_navigation(classifier_with_mock):
    """Exact canonical context + navigation measurement → Midnight Rider
    
    Tests that when canonical context (loaded at runtime from Signal K) matches,
    the record is classified as Midnight Rider even without explicit self tag.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": canonical_uuid,  # Canonical identity (from validator mock)
        "self": "",  # No explicit self tag (but context matches)
    }
    assert classifier.classify(record) == "midnight_rider"


def test_canonical_context_with_environment(classifier_with_mock):
    """Exact canonical context + environment measurement → Midnight Rider
    
    Tests environment measurement family with canonical context.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "environment.outside.temperature",
        "context": canonical_uuid,  # Canonical identity from validator
        "self": "",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_canonical_context_with_electrical(classifier_with_mock):
    """Exact canonical context + electrical measurement → Midnight Rider
    
    Tests electrical measurement family with canonical context.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "electrical.batteries.0.voltage",
        "context": canonical_uuid,  # Canonical identity from validator
        "self": "",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_canonical_context_with_performance(classifier_with_mock):
    """Exact canonical context + performance measurement → Midnight Rider
    
    Tests performance measurement family with canonical context.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "performance.leewayAngle",
        "context": canonical_uuid,  # Canonical identity from validator
        "self": "",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_canonical_context_with_sensors(classifier_with_mock):
    """Exact canonical context + sensors measurement → Midnight Rider
    
    Tests sensors measurement family with canonical context.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "sensors.wit.temperature",
        "context": canonical_uuid,  # Canonical identity from validator
        "self": "",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_canonical_context_case_insensitive(classifier_with_mock):
    """Canonical context matching is case-insensitive"""
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": canonical_uuid.upper(),  # Different case
        "self": "",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_canonical_context_with_whitespace(classifier_with_mock):
    """Canonical context matching tolerates surrounding whitespace"""
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": f"  {canonical_uuid}  ",  # Leading/trailing whitespace
        "self": "",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_non_matching_context_with_navigation(classifier_with_mock):
    """Non-matching context + navigation → Unclassified (not Midnight Rider)"""
    classifier, _ = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": "vessels.other-vessel-id",
        "self": "",
    }
    assert classifier.classify(record) == "unclassified"


def test_canonical_context_with_unknown_measurement(classifier_with_mock):
    """Canonical context + unknown measurement → Unclassified
    
    Context alone is insufficient; measurement must be in self-vessel family.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "unknown.metric",
        "context": canonical_uuid,
        "self": "",
    }
    assert classifier.classify(record) == "unclassified"


def test_canonical_context_ais_precedence(classifier_with_mock):
    """AIS context + canonical context → AIS (AIS precedence)
    
    Even if canonical context matches, AIS URN in context takes precedence.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": "vessels.urn:mrn:imo:mmsi:636024194",
        "self": "",
    }
    assert classifier.classify(record) == "ais"


def test_canonical_context_with_ais_measurement(classifier_with_mock):
    """Canonical context + AIS measurement → AIS (measurement precedence)
    
    AIS measurement family takes precedence over canonical context.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "sensors.ais.fromBow",
        "context": canonical_uuid,
        "self": "",
    }
    assert classifier.classify(record) == "ais"


def test_canonical_context_unavailable(classifier_without_context):
    """Canonical source unavailable → falls back to self tag"""
    
    record = {
        "_measurement": "navigation.position",
        "context": "urn:mrn:signalk:uuid:fdcfc5d2-9e90-401f-8b9c-1b80dd9ee72f",
        "self": "",
    }
    # Without canonical validator, context matching is unavailable
    # Falls back to self tag check (empty self, so unclassified)
    assert classifier_without_context.classify(record) == "unclassified"


def test_canonical_context_with_explicit_self_true(classifier_with_mock):
    """Exact canonical context + self=="true" → Midnight Rider
    
    Both methods confirm self-vessel identity.
    """
    classifier, canonical_uuid = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": canonical_uuid,
        "self": "true",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_self_true_without_canonical_context(classifier_with_mock):
    """self=="true" without canonical context → Midnight Rider
    
    Backward compatibility: explicit self=="true" still works.
    """
    classifier, _ = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": "some-other-context",
        "self": "true",
    }
    assert classifier.classify(record) == "midnight_rider"


def test_generic_other_present_never_classified_as_mr(classifier_with_mock):
    """Generic 'other_present' context NEVER classifies as Midnight Rider
    
    Even with a valid navigation measurement, unrecognized context
    must never be classified as Midnight Rider (safety requirement).
    """
    classifier, _ = classifier_with_mock
    
    record = {
        "_measurement": "navigation.position",
        "context": "vessels.some-unknown-identifier",
        "self": "",
    }
    assert classifier.classify(record) == "unclassified"


def test_empty_canonical_context_set_fails_closed(classifier_without_context):
    """Empty canonical context set fails closed (no false positives)
    
    If canonical source fails to load, exact context matching is disabled.
    Records without self=="true" remain unclassified.
    """
    record = {
        "_measurement": "navigation.position",
        "context": "any-context-value",
        "self": "",
    }
    assert classifier_without_context.classify(record) == "unclassified"


# BACKWARD COMPATIBILITY TESTS (Existing self=="true" logic)

def test_self_true_backward_compat(classifier_without_context):
    """self=="true" continues to work (backward compatibility)"""
    
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "",
    }
    assert classifier_without_context.classify(record) == "midnight_rider"


def test_self_empty_remains_unclassified(classifier_without_context):
    """self=="" remains unclassified (no change)"""
    
    record = {
        "_measurement": "navigation.position",
        "self": "",
        "context": "",
    }
    assert classifier_without_context.classify(record) == "unclassified"


def test_ais_precedence_unchanged(classifier_without_context):
    """AIS precedence remains absolute (no change)"""
    
    record = {
        "_measurement": "navigation.position",
        "self": "true",
        "context": "vessels.urn:mrn:imo:mmsi:636024194",
    }
    assert classifier_without_context.classify(record) == "ais"

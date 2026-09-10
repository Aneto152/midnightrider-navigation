"""
Tests for AIS separation and non-AIS onboard data classification.
"""
import pytest
from tools.influx_powerbi_export.classifier import Classifier


class TestAISSeparation:
    """Test AIS detection and onboard data classification."""
    
    @pytest.fixture
    def classifier(self):
        return Classifier()
    
    # AIS Detection Tests
    def test_ais_source_detected(self, classifier):
        """AIS in source → ais"""
        record = {"source": "ais", "context": "vessels.xyz", "_measurement": "navigation_speed"}
        assert classifier.classify(record) == "ais"
    
    def test_ais_context_detected(self, classifier):
        """AIS in context → ais"""
        record = {"source": "n2k", "context": "ais_vessel_123", "_measurement": "navigation"}
        assert classifier.classify(record) == "ais"
    
    def test_ais_measurement_detected(self, classifier):
        """AIS in measurement → ais"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "ais_position"}
        assert classifier.classify(record) == "ais"
    
    # Non-AIS Onboard Data Tests
    def test_non_ais_navigation(self, classifier):
        """Non-AIS navigation → midnight_rider"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "navigation_speed"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_non_ais_environment(self, classifier):
        """Non-AIS environment → midnight_rider"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "environment_wind"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_non_ais_sensors(self, classifier):
        """Non-AIS sensors → midnight_rider"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "sensors_temperature"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_non_ais_electrical(self, classifier):
        """Non-AIS electrical → midnight_rider"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "electrical_voltage"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_non_ais_performance(self, classifier):
        """Non-AIS performance → midnight_rider"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "performance_distance"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_unknown_non_ais(self, classifier):
        """Unknown non-AIS measurement → midnight_rider"""
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "unknown_metric"}
        assert classifier.classify(record) == "midnight_rider"
    
    # Missing Field Tests
    def test_missing_context_non_ais(self, classifier):
        """Missing context, non-AIS source → midnight_rider"""
        record = {"source": "n2k", "context": "", "_measurement": "navigation"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_missing_source_non_ais(self, classifier):
        """Missing source, non-AIS context → midnight_rider"""
        record = {"source": "", "context": "vessels.abc", "_measurement": "navigation"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_all_fields_missing_non_ais(self, classifier):
        """All fields missing/empty → midnight_rider"""
        record = {"source": "", "context": "", "_measurement": ""}
        assert classifier.classify(record) == "midnight_rider"
    
    # AIS Precedence Tests
    def test_ais_precedence_over_other_fields(self, classifier):
        """AIS in source takes precedence → ais"""
        record = {
            "source": "ais",
            "context": "vessels.abc",
            "_measurement": "navigation"
        }
        assert classifier.classify(record) == "ais"
    
    # Validation Tests
    def test_valid_categories(self):
        """Valid category check works."""
        assert Classifier.is_valid_category("ais")
        assert Classifier.is_valid_category("midnight_rider")
        assert not Classifier.is_valid_category("unclassified")
        assert not Classifier.is_valid_category("unknown")
    
    def test_description(self):
        """Descriptions provided for all categories."""
        assert "AIS" in Classifier.get_description("ais")
        assert "Midnight Rider" in Classifier.get_description("midnight_rider")

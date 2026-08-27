"""
Tests for validator with complete coordinate format coverage and wind fail-closed behavior.
"""

import pytest
from datetime import datetime, timezone
from mediaman.llm_validator import OutputValidator
from mediaman.race_facts import RaceFacts, PositionFact, NavigationFact


@pytest.fixture
def sample_facts():
    """Create sample RaceFacts for validation tests."""
    ts = datetime.now(timezone.utc)
    return RaceFacts(
        position=PositionFact(
            latitude=41.1234,
            longitude=-73.5678,
            source_timestamp=ts,
            observed_at=ts
        ),
        navigation=NavigationFact(
            sog_knots=8.5,
            cog_degrees=5.0,
            source_timestamp=ts,
            observed_at=ts
        ),
        wind=None,
        cycle_timestamp="2026-08-27T15:00:00Z"
    )


class TestOutputValidator:
    """Test LLM output validation."""

    # SECURITY REGRESSIONS
    def test_valid_article(self, sample_facts):
        """Valid article passes."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_credentials_rejected(self, sample_facts):
        """Credentials rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Token: abc123. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "credential" in msg.lower()

    def test_injection_rejected(self, sample_facts):
        """Injection rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "<script>alert('xss')</script>. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "injection" in msg.lower()

    # PHASE 2: COMPLETE COORDINATE FORMAT COVERAGE
    def test_coordinates_cardinal_north_west(self, sample_facts):
        """Format 1: 41.1234°N, 73.5678°W — rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234°N, 73.5678°W. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_cardinal_with_letter_prefix(self, sample_facts):
        """Format 2: 41.1234 N, -73.5678 W — rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234 N, -73.5678 W. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_signed_comma(self, sample_facts):
        """Format 3: -41.1234, 73.5678 — rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position -41.1234, 73.5678. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_degree_symbols_signed(self, sample_facts):
        """Format 4: 41.1234° -73.5678° — rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234° -73.5678°. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_signed_space(self, sample_facts):
        """Format 5: 41.1234 -73.5678 — rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234 -73.5678. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_cardinal_south_east(self, sample_facts):
        """Format 6: -41.1234°S, 73.5678°E — rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234°S, 73.5678°E. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coarse_location_allowed(self, sample_facts):
        """Coarse location text allowed."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le bateau navigue près de l'île. "
            "Les conditions sont excellentes. "
            "L'équipage est optimiste."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    # PHASE 3: WIND SPEED FAIL-CLOSED BEHAVIOR
    def test_wind_speed_claim_rejected_when_unavailable(self, sample_facts):
        """Wind speed explicitly claimed but unavailable → REJECTED."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue. "
            "Le vent souffle à 12 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        # Wind is unavailable (never is_valid()), so explicit claim must fail
        assert not is_valid
        assert "wind" in msg.lower()

    def test_wind_speed_unavailable_explicit_fail_closed(self, sample_facts):
        """Explicit wind speed pattern → WindFact is None → REJECTED."""
        validator = OutputValidator(sample_facts)
        # This documents the fail-closed behavior: no silent acceptance
        assert validator.facts.wind is None or not validator.facts.wind.is_valid()
        article = (
            "Conditions variables. "
            "Le vent souffle à 8 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid

    # EXISTING CONTEXT AND TOLERANCE TESTS
    def test_per_occurrence_wind_context(self, sample_facts):
        """Wind and speed in separate sentences: separate validation."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le vent souffle à 15 nœuds. "
            "Midnight Rider navigue à 8.5 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "wind" in msg.lower()

    def test_speed_without_wind_context(self, sample_facts):
        """Speed clause without wind context: validated against SOG."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider avance à 8.5 nœuds avec vent faible. "
            "L'équipage travaille dur. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_wind_data_not_ranking(self, sample_facts):
        """'wind' in 'wind data' not matched by ranking pattern."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le wind data est unavailable. "
            "Midnight Rider navigue à 8.5 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_winning_triggers_ranking(self, sample_facts):
        """'winning' triggers ranking rejection."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "The boat is winning. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "ranking" in msg.lower()

    def test_speed_within_tolerance(self, sample_facts):
        """Speed within tolerance passes."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 7.0 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_speed_outside_tolerance(self, sample_facts):
        """Speed outside tolerance fails."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 6.9 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "speed" in msg.lower()

    def test_course_wrap_valid(self, sample_facts):
        """Course wrap within tolerance passes."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Cap 355 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_course_wrap_invalid(self, sample_facts):
        """Course wrap outside tolerance fails."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Route 320 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "course" in msg.lower()

    def test_sentence_count_enforced(self, sample_facts):
        """Sentence count enforced."""
        validator = OutputValidator(sample_facts)
        article = "Une phrase."
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "sentence" in msg.lower()

    def test_length_limit_enforced(self, sample_facts):
        """Length limit enforced."""
        validator = OutputValidator(sample_facts)
        article = "a" * 800
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "700" in msg

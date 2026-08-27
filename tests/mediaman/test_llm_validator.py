"""
Tests for validator with per-occurrence wind context and signed-coordinate fixes.
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

    # PHASE 2: PER-OCCURRENCE WIND CONTEXT
    def test_wind_and_speed_separate_sentences(self, sample_facts):
        """Wind and speed in separate sentences: separate validation."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le vent souffle à 15 nœuds. "
            "Midnight Rider navigue à 8.5 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        # Wind claim rejected (wind unavailable), even though speed is valid
        assert not is_valid
        assert "wind" in msg.lower()

    def test_wind_and_speed_same_sentence_separate_clauses(self, sample_facts):
        """Wind and speed in same sentence but separate clauses."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le vent souffle à 15 nœuds tandis que Midnight Rider avance à 8.5 nœuds. "
            "L'équipage travaille dur. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        # Wind should trigger rejection (wind unavailable)
        assert not is_valid
        assert "wind" in msg.lower()

    def test_speed_without_wind_context_same_sentence(self, sample_facts):
        """Speed clause without wind context: validated against SOG."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider avance à 8.5 nœuds avec vent faible. "
            "L'équipage travaille dur. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        # "vent faible" is NOT a speed claim (no unit after), so doesn't trigger rejection
        assert is_valid, msg

    def test_explicit_wind_speed_pattern_required(self, sample_facts):
        """Only explicit wind speed pattern triggers wind validation."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le vent s'intensifie. "
            "Midnight Rider navigue à 8.5 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        # "vent" without "à X nœuds" pattern doesn't trigger wind check
        assert is_valid, msg

    # PHASE 3: WIND SPEED VALIDATION (UNAVAILABLE)
    def test_explicit_wind_speed_claim_rejected(self, sample_facts):
        """Explicit wind speed claim rejected when wind unavailable."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue. "
            "Le vent souffle à 12 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "wind" in msg.lower()

    # PHASE 4: SIGNED COORDINATE DETECTION
    def test_coordinates_positive_latitude_negative_longitude(self, sample_facts):
        """Positive lat, negative lon rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234 -73.5678. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_negative_latitude_positive_longitude(self, sample_facts):
        """Negative lat, positive lon rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position -41.1234, 73.5678. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_cardinal_with_comma(self, sample_facts):
        """Cardinal format with comma rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234°N, 73.5678°W. "
            "Le bateau navigue. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coordinates_degree_symbols(self, sample_facts):
        """Degree symbols with signs rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234° -73.5678°. "
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

    # PHASE 5: WORD BOUNDARIES
    def test_wind_data_not_ranking(self, sample_facts):
        """'wind' in 'wind data' not matched by ranking pattern."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le wind data est unavailable. "
            "Midnight Rider navigue à 8.5 nœuds. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        # "wind data" should not trigger ranking rejection
        assert is_valid, msg

    def test_wind_shifted_not_ranking(self, sample_facts):
        """'The wind shifted' not matched by ranking."""
        validator = OutputValidator(sample_facts)
        article = (
            "The wind shifted dramatically. "
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

    def test_leader_triggers_ranking(self, sample_facts):
        """'leader' triggers ranking rejection."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le bateau est leader. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "ranking" in msg.lower()

    # TOLERANCE AND COURSE TESTS
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

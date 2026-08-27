"""
Tests for hardened field-aware validator with edge cases.
"""

import pytest
from datetime import datetime, timezone
from mediaman.llm_validator import OutputValidator
from mediaman.race_facts import (
    RaceFacts, PositionFact, NavigationFact, WindFact
)


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

    def test_valid_article(self, sample_facts):
        """Valid article with correct speed and course should pass."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_empty_output(self, sample_facts):
        """Empty output should fail."""
        validator = OutputValidator(sample_facts)
        is_valid, msg = validator.validate("")
        assert not is_valid
        assert "empty" in msg.lower()

    def test_security_checks_before_numeric(self, sample_facts):
        """Security checks must execute before numeric validation."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "<script>alert('xss')</script>. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "injection" in msg.lower()

    # PHASE 2: WIND CONTEXT RECOGNITION
    def test_wind_claim_without_wind_facts(self, sample_facts):
        """Wind claims rejected when wind facts unavailable."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue. "
            "Le vent souffle à 12 nœuds. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "wind" in msg.lower()

    # PHASE 3: TOLERANCE CALCULATION
    def test_speed_at_tolerance_boundary(self, sample_facts):
        """Speed exactly at tolerance boundary passes."""
        validator = OutputValidator(sample_facts)
        # SOG 8.5, tolerance ±1.5, so 7.0 should pass
        article = (
            "Midnight Rider navigue à 7.0 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_speed_just_outside_tolerance(self, sample_facts):
        """Speed just outside tolerance rejected."""
        validator = OutputValidator(sample_facts)
        # SOG 8.5, tolerance ±1.5, so 6.9 should fail
        article = (
            "Midnight Rider navigue à 6.9 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "speed" in msg.lower()

    def test_course_at_tolerance_boundary(self, sample_facts):
        """Course exactly at tolerance boundary passes."""
        validator = OutputValidator(sample_facts)
        # COG 5, tolerance ±40, so 45 should pass
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le cap est 45 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    # PHASE 4: CIRCULAR COURSE (0/360 BOUNDARY)
    def test_course_across_zero_boundary(self, sample_facts):
        """Course across 0/360 wrap handled correctly."""
        validator = OutputValidator(sample_facts)
        # COG 5, claim 355 → circular difference 10 degrees, within 40 tolerance
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le cap est 355 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_course_wrap_outside_tolerance(self, sample_facts):
        """Course wrap outside tolerance rejected."""
        validator = OutputValidator(sample_facts)
        # COG 5, claim 350 → circular difference 15 degrees (within tolerance)
        # COG 5, claim 325 → circular difference 40 degrees (at tolerance boundary)
        # COG 5, claim 320 → circular difference 45 degrees (outside 40 tolerance, should fail)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Route 320 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "course" in msg.lower()

    # PHASE 4: COORDINATE DETECTION
    def test_exact_coordinates_cardinal_format(self, sample_facts):
        """Cardinal format coordinates rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234°N, 73.5678°W. "
            "Le navire navigue bien. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_exact_coordinates_signed_format(self, sample_facts):
        """Signed format coordinates rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234 -73.5678. "
            "Le navire navigue bien. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_exact_coordinates_degree_format(self, sample_facts):
        """Degree format coordinates rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234° -73.5678°. "
            "Le navire navigue bien. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_coarse_location_allowed(self, sample_facts):
        """Coarse non-exact location text allowed."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le bateau navigue près de l'île. "
            "Les conditions sont excellentes. "
            "L'équipage est optimiste."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    # PHASE 5: WORD BOUNDARIES
    def test_wind_context_without_units_ignored(self, sample_facts):
        """'vent' alone without units does not trigger wind validation."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le vent est stable. "
            "Le bateau navigue à 8.5 nœuds. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        # Should pass because there's no explicit wind speed claim (no units)
        assert is_valid, msg

    def test_winning_rejected_as_ranking(self, sample_facts):
        """'winning' triggers ranking rejection."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le bateau est winning. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "ranking" in msg.lower()

    def test_leader_rejected_as_ranking(self, sample_facts):
        """'leader' triggers ranking rejection."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le bateau est le leader. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "ranking" in msg.lower()

    # REGRESSION: SECURITY
    def test_credentials_still_rejected(self, sample_facts):
        """Credentials rejected despite numeric content."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Token: abc123. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "credential" in msg.lower()

    def test_length_limit_enforced(self, sample_facts):
        """Length limit enforced."""
        validator = OutputValidator(sample_facts)
        article = "a" * 800
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "700" in msg

    def test_sentence_count_enforced(self, sample_facts):
        """Sentence count enforced."""
        validator = OutputValidator(sample_facts)
        article = "Une phrase."
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "sentence" in msg.lower()

    def test_valid_french_narrative(self, sample_facts):
        """Valid French narrative passes."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le Midnight Rider navigue magnifiquement. "
            "L'équipage optimise constamment. "
            "Les conditions sont excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_invalid_speed(self, sample_facts):
        """Invalid speed rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 20 nœuds. "
            "Le cap est 5 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "speed" in msg.lower()

    def test_invalid_course(self, sample_facts):
        """Invalid course rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Cap 100 degrés. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "course" in msg.lower()

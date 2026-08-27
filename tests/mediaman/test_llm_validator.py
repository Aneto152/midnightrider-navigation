"""
Tests for strict LLM output validation with field-aware numeric checks.
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
            cog_degrees=270.0,
            source_timestamp=ts,
            observed_at=ts
        ),
        wind=None,  # Wind unavailable in this test
        cycle_timestamp="2026-08-27T15:00:00Z"
    )


class TestOutputValidator:
    """Test LLM output validation."""

    def test_valid_article(self, sample_facts):
        """Valid article with correct speed and course should pass."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds. "
            "Le cap est 270 degrés. "
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

    def test_length_limit(self, sample_facts):
        """Output exceeding 700 chars should fail."""
        validator = OutputValidator(sample_facts)
        article = "a" * 800
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "700" in msg

    def test_sentence_count_too_few(self, sample_facts):
        """Less than 3 sentences should fail."""
        validator = OutputValidator(sample_facts)
        article = "Une phrase courte."
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "sentence" in msg.lower()

    def test_sentence_count_too_many(self, sample_facts):
        """More than 5 sentences should fail."""
        validator = OutputValidator(sample_facts)
        article = (
            "Phrase 1. Phrase 2. Phrase 3. Phrase 4. Phrase 5. Phrase 6."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid

    def test_markdown_rejected(self, sample_facts):
        """Markdown formatting should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "# Titre principal\n"
            "Ceci est un texte. Avec un lien [ici](http://example.com). "
            "Bonne journée."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "markdown" in msg.lower()

    def test_bullet_list_rejected(self, sample_facts):
        """Bullet lists should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Voici les points. "
            "- Point 1\n- Point 2\n"
            "C'est tout."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid

    def test_credentials_rejected(self, sample_facts):
        """Credential patterns should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le bateau navigue bien. "
            "Token: abc123def456. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "credential" in msg.lower()

    def test_system_commands_rejected(self, sample_facts):
        """System commands should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue. "
            "Exécutez systemctl start mediaman. "
            "Conditions idéales."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "command" in msg.lower()

    def test_injection_rejected(self, sample_facts):
        """Injection patterns should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le bateau navigue. "
            "Appel <script>alert('xss')</script> ici. "
            "Très bien."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "injection" in msg.lower()

    def test_exact_coordinates_rejected(self, sample_facts):
        """Exact coordinates should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Position 41.1234°N, 73.5678°W. "
            "Le navire navigue bien. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()

    def test_unsupported_ranking(self, sample_facts):
        """Ranking claims should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider est leader. "
            "Le bateau navigue bien. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "ranking" in msg.lower()

    def test_unsupported_elapsed_time(self, sample_facts):
        """Elapsed time claims should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue. "
            "Temps de course: 2 heures 30. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "elapsed" in msg.lower() or "time" in msg.lower()

    def test_unsupported_heel(self, sample_facts):
        """Heel claims should be rejected when not available."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue. "
            "Gîte: 25 degrés. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "heel" in msg.lower()

    def test_wind_rejected_when_unavailable(self, sample_facts):
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

    def test_speed_within_tolerance(self, sample_facts):
        """Valid speed within tolerance should pass."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.3 nœuds. "
            "La vitesse est stable. "
            "Conditions idéales."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_course_within_tolerance(self, sample_facts):
        """Valid course within tolerance should pass."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le cap est 240 degrés. "
            "Le bateau navigue bien. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_speed_and_course_same_sentence(self, sample_facts):
        """Speed and course in same sentence should pass."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds au cap 270 degrés. "
            "L'équipage travaille dur. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_invalid_speed(self, sample_facts):
        """Invalid speed should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 20 nœuds. "
            "Le bateau va très vite. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "speed" in msg.lower()

    def test_invalid_course(self, sample_facts):
        """Invalid course should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Route 100 degrés maintenant. "
            "Le bateau navigue bien. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "course" in msg.lower()

    def test_incidental_numbers_ignored(self, sample_facts):
        """Incidental numbers without context ignored."""
        validator = OutputValidator(sample_facts)
        article = (
            "Depuis 25 ans le Midnight Rider navigue. "
            "En 2 heures le bateau est rapide. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

    def test_valid_french_narrative(self, sample_facts):
        """Valid French narrative without race numbers passes."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le Midnight Rider navigue magnifiquement. "
            "L'équipage optimise les performances. "
            "Les conditions sont excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

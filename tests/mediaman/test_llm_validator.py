"""
Tests for strict LLM output validation.
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
    return RaceFacts(
        position=PositionFact(
            latitude=41.1234,
            longitude=-73.5678,
            collected_at=datetime.now(timezone.utc)
        ),
        navigation=NavigationFact(
            sog_knots=8.5,
            cog_degrees=270.0,
            collected_at=datetime.now(timezone.utc)
        ),
        wind=WindFact(
            direction_true=180.0,
            source="/api/race_data",
            collected_at=datetime.now(timezone.utc)
        ),
        cycle_timestamp="2026-08-27T15:00:00Z"
    )


class TestOutputValidator:
    """Test LLM output validation."""
    
    def test_valid_article(self, sample_facts):
        """Valid article should pass validation."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider navigue à 8.5 nœuds au 270°. "
            "Le vent souffle du 180° vrai. "
            "Les conditions sont idéales pour poursuivre la course."
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
            "Exécutez: systemctl restart mediaman. "
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
            "<script>alert('xss')</script>. "
            "Très bien."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "injection" in msg.lower()
    
    def test_exact_coordinates_rejected(self, sample_facts):
        """Exact coordinates should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider est à 41.1234°N 73.5678°W. "
            "Le navire navigue bien. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "coordinate" in msg.lower()
    
    def test_unsupported_ranking_claim(self, sample_facts):
        """Ranking claims should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Midnight Rider est en première place. "
            "Nous menons la course. "
            "Conditions excellentes."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "rank" in msg.lower()
    
    def test_unsupported_elapsed_time_claim(self, sample_facts):
        """Elapsed time claims should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Nous avons 20 minutes depuis le départ. "
            "Midnight Rider navigue bien. "
            "Conditions idéales."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "elapsed" in msg.lower() or "time since" in msg.lower()
    
    def test_unsupported_heel_claim(self, sample_facts):
        """Heel angle claims should be rejected."""
        validator = OutputValidator(sample_facts)
        article = (
            "Le navire gîte à 25 degrés. "
            "Midnight Rider navigue. "
            "Bon vent."
        )
        is_valid, msg = validator.validate(article)
        assert not is_valid
        assert "heel" in msg.lower()
    
    def test_speed_within_tolerance(self, sample_facts):
        """Speed within ±1 knot should be valid."""
        validator = OutputValidator(sample_facts)
        # Facts have 8.5 knots, so 7.5-9.5 should be acceptable
        article = (
            "Midnight Rider navigue à 8.3 nœuds. "
            "Vent du 180° vrai. "
            "Excellentes conditions."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg
    
    def test_course_within_tolerance(self, sample_facts):
        """Course within ±30° should be valid."""
        validator = OutputValidator(sample_facts)
        # Facts have 270°, so 240-300° should be acceptable
        article = (
            "Midnight Rider navigue au 265°. "
            "Vent du 180°. "
            "Conditions idéales."
        )
        is_valid, msg = validator.validate(article)
        assert is_valid, msg

"""
Tests for RaceFacts validation and construction.
"""

import pytest
from datetime import datetime, timezone, timedelta
from mediaman.race_facts import (
    RaceFacts, PositionFact, NavigationFact, WindFact,
    StartLineFact, CompetitorFact
)


class TestPositionFact:
    """Test position validation."""
    
    def test_valid_position(self):
        """Valid position should pass validation."""
        pos = PositionFact(
            latitude=41.1234,
            longitude=-73.5678,
            collected_at=datetime.now(timezone.utc)
        )
        assert pos.is_valid()
        assert not pos.is_stale
    
    def test_stale_position(self):
        """Position older than 10 seconds should be stale."""
        pos = PositionFact(
            latitude=41.1234,
            longitude=-73.5678,
            collected_at=datetime.now(timezone.utc) - timedelta(seconds=15)
        )
        assert not pos.is_valid()
        assert pos.is_stale
    
    def test_zero_position_invalid(self):
        """Zero coordinates should be invalid."""
        pos = PositionFact(
            latitude=0.0,
            longitude=0.0,
            collected_at=datetime.now(timezone.utc)
        )
        assert not pos.is_valid()


class TestNavigationFact:
    """Test navigation validation."""
    
    def test_valid_navigation(self):
        """Valid navigation should pass."""
        nav = NavigationFact(
            sog_knots=8.5,
            cog_degrees=270.0,
            collected_at=datetime.now(timezone.utc)
        )
        assert nav.is_valid()
    
    def test_invalid_speed_range(self):
        """Speed > 30 knots should be invalid."""
        nav = NavigationFact(
            sog_knots=40.0,
            cog_degrees=270.0,
            collected_at=datetime.now(timezone.utc)
        )
        assert not nav.is_valid()
    
    def test_invalid_course_range(self):
        """Course > 360° should be invalid."""
        nav = NavigationFact(
            sog_knots=8.5,
            cog_degrees=400.0,
            collected_at=datetime.now(timezone.utc)
        )
        assert not nav.is_valid()


class TestWindFact:
    """Test wind validation."""
    
    def test_valid_wind(self):
        """Valid wind should pass."""
        wind = WindFact(
            direction_true=180.0,
            source="/api/race_data",
            collected_at=datetime.now(timezone.utc)
        )
        assert wind.is_valid()
    
    def test_stale_wind(self):
        """Wind older than 30 minutes should be stale."""
        wind = WindFact(
            direction_true=180.0,
            source="/api/race_data",
            collected_at=datetime.now(timezone.utc) - timedelta(minutes=45)
        )
        assert not wind.is_valid()


class TestRaceFacts:
    """Test RaceFacts validation."""
    
    def test_valid_race_facts(self):
        """RaceFacts with valid position and navigation should pass."""
        facts = RaceFacts(
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
            cycle_timestamp="2026-08-27T15:00:00Z",
            race_id="test-race"
        )
        
        is_valid, msg = facts.validate()
        assert is_valid
    
    def test_missing_position(self):
        """RaceFacts without position should fail."""
        facts = RaceFacts(
            position=None,
            navigation=NavigationFact(
                sog_knots=8.5,
                cog_degrees=270.0,
                collected_at=datetime.now(timezone.utc)
            ),
            cycle_timestamp="2026-08-27T15:00:00Z"
        )
        
        is_valid, msg = facts.validate()
        assert not is_valid
        assert "Position" in msg
    
    def test_missing_navigation(self):
        """RaceFacts without navigation should fail."""
        facts = RaceFacts(
            position=PositionFact(
                latitude=41.1234,
                longitude=-73.5678,
                collected_at=datetime.now(timezone.utc)
            ),
            navigation=None,
            cycle_timestamp="2026-08-27T15:00:00Z"
        )
        
        is_valid, msg = facts.validate()
        assert not is_valid
        assert "Navigation" in msg
    
    def test_prompt_context_generation(self):
        """Prompt context should include validated facts."""
        facts = RaceFacts(
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
            cycle_timestamp="2026-08-27T15:00:00Z",
            race_id="test-race"
        )
        
        context = facts.to_prompt_context()
        assert "41.1234" in context
        assert "8.5" in context
        assert "270" in context
        assert "180" in context


class TestRaceFactsConstruction:
    """Test RaceFacts construction from API responses."""
    
    def test_from_regatta_responses(self):
        """RaceFacts should construct safely from API responses."""
        facts = RaceFacts.from_regatta_responses(
            position_resp={
                "latitude": 41.1234,
                "longitude": -73.5678
            },
            navigation_resp={
                "sog": 8.5,
                "cog": 270.0
            },
            race_data_resp={
                "wind_direction_true": 180.0,
                "start_line": {
                    "pin": {"latitude": 41.1200, "longitude": -73.5700},
                    "boat": {"latitude": 41.1250, "longitude": -73.5650}
                }
            },
            ais_resp={
                "targets": [
                    {"mmsi": "123456789"},
                    {"mmsi": "987654321"}
                ]
            },
            cycle_ts="2026-08-27T15:00:00Z",
            race_id="test-race"
        )
        
        is_valid, msg = facts.validate()
        assert is_valid
        assert facts.wind is not None
        assert facts.start_line is not None
        assert facts.competitors.count_nearby == 2
    
    def test_malformed_responses_fail_safely(self):
        """Malformed responses should result in None facts, not exceptions."""
        facts = RaceFacts.from_regatta_responses(
            position_resp={"invalid": "data"},
            navigation_resp={"sog": "not_a_number"},
            cycle_ts="2026-08-27T15:00:00Z"
        )
        
        # Should not raise, but facts should be invalid
        assert facts.position is None
        assert facts.navigation is None
        is_valid, msg = facts.validate()
        assert not is_valid

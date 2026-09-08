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
            source_timestamp=datetime.now(timezone.utc)
        )
        assert pos.is_valid()
        assert not pos.is_stale
    
    def test_position_missing_source_timestamp(self):
        """Position without source_timestamp should be stale."""
        pos = PositionFact(
            latitude=41.1234,
            longitude=-73.5678,
            source_timestamp=None
        )
        assert not pos.is_valid()
        assert pos.is_stale
    
    def test_stale_position(self):
        """Position older than 10 seconds should be stale."""
        pos = PositionFact(
            latitude=41.1234,
            longitude=-73.5678,
            source_timestamp=datetime.now(timezone.utc) - timedelta(seconds=15)
        )
        assert not pos.is_valid()
        assert pos.is_stale
    
    def test_zero_position_invalid(self):
        """Zero coordinates should be invalid."""
        pos = PositionFact(
            latitude=0.0,
            longitude=0.0,
            source_timestamp=datetime.now(timezone.utc)
        )
        assert not pos.is_valid()


class TestNavigationFact:
    """Test navigation validation."""
    
    def test_valid_navigation(self):
        """Valid navigation should pass."""
        nav = NavigationFact(
            sog_knots=8.5,
            cog_degrees=270.0,
            source_timestamp=datetime.now(timezone.utc)
        )
        assert nav.is_valid()
    
    def test_missing_sog(self):
        """Navigation without SOG should be invalid."""
        nav = NavigationFact(
            sog_knots=None,
            cog_degrees=270.0,
            source_timestamp=datetime.now(timezone.utc)
        )
        assert not nav.is_valid()
    
    def test_missing_cog(self):
        """Navigation without COG should be invalid."""
        nav = NavigationFact(
            sog_knots=8.5,
            cog_degrees=None,
            source_timestamp=datetime.now(timezone.utc)
        )
        assert not nav.is_valid()
    
    def test_navigation_missing_source_timestamp(self):
        """Navigation without source_timestamp should be stale."""
        nav = NavigationFact(
            sog_knots=8.5,
            cog_degrees=270.0,
            source_timestamp=None
        )
        assert not nav.is_valid()
    
    def test_invalid_speed_range(self):
        """Speed > 30 knots should be invalid."""
        nav = NavigationFact(
            sog_knots=40.0,
            cog_degrees=270.0,
            source_timestamp=datetime.now(timezone.utc)
        )
        assert not nav.is_valid()
    
    def test_invalid_course_range(self):
        """Course > 360° should be invalid."""
        nav = NavigationFact(
            sog_knots=8.5,
            cog_degrees=400.0,
            source_timestamp=datetime.now(timezone.utc)
        )
        assert not nav.is_valid()


class TestWindFact:
    """Test wind validation."""
    
    def test_wind_currently_unproven(self):
        """Wind should be invalid (unproven pending MCP audit)."""
        wind = WindFact(
            direction_true=180.0,
            source="/api/race_data",
            source_timestamp=datetime.now(timezone.utc)
        )
        # Wind is explicitly unproven until timestamp audit completes
        assert not wind.is_valid()
    
    def test_wind_not_from_api_race_data(self):
        """Wind should not be mapped from /api/race_data (not returned by that endpoint)."""
        # /api/race_data does not return wind_direction_true
        # This test documents that we do NOT read wind from that endpoint
        wind = WindFact(
            direction_true=180.0,
            source="/api/race_data",
            source_timestamp=datetime.now(timezone.utc)
        )
        assert wind.source == "/api/race_data"
        assert not wind.is_valid()  # But wind is unproven regardless


class TestRaceFacts:
    """Test RaceFacts validation."""
    
    def test_valid_race_facts(self):
        """RaceFacts with valid position and navigation should pass."""
        facts = RaceFacts(
            position=PositionFact(
                latitude=41.1234,
                longitude=-73.5678,
                source_timestamp=datetime.now(timezone.utc)
            ),
            navigation=NavigationFact(
                sog_knots=8.5,
                cog_degrees=270.0,
                source_timestamp=datetime.now(timezone.utc)
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
                source_timestamp=datetime.now(timezone.utc)
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
                source_timestamp=datetime.now(timezone.utc)
            ),
            navigation=None,
            cycle_timestamp="2026-08-27T15:00:00Z"
        )
        
        is_valid, msg = facts.validate()
        assert not is_valid
        assert "Navigation" in msg
    
    def test_missing_cycle_timestamp(self):
        """RaceFacts without cycle_timestamp should fail."""
        facts = RaceFacts(
            position=PositionFact(
                latitude=41.1234,
                longitude=-73.5678,
                source_timestamp=datetime.now(timezone.utc)
            ),
            navigation=NavigationFact(
                sog_knots=8.5,
                cog_degrees=270.0,
                source_timestamp=datetime.now(timezone.utc)
            ),
            cycle_timestamp=None
        )
        
        is_valid, msg = facts.validate()
        assert not is_valid
        assert "Cycle" in msg or "cycle" in msg.lower()
    
    def test_prompt_context_suppresses_exact_coordinates(self):
        """Prompt context should suppress exact coordinates by default."""
        facts = RaceFacts(
            position=PositionFact(
                latitude=41.1234,
                longitude=-73.5678,
                source_timestamp=datetime.now(timezone.utc)
            ),
            navigation=NavigationFact(
                sog_knots=8.5,
                cog_degrees=270.0,
                source_timestamp=datetime.now(timezone.utc)
            ),
            cycle_timestamp="2026-08-27T15:00:00Z",
            race_id="test-race"
        )
        
        context = facts.to_prompt_context(allow_exact_coordinates=False)
        # Exact coordinates should NOT appear
        assert "41.1234" not in context
        assert "-73.5678" not in context
        # But position status should appear
        assert "Position" in context or "On course" in context
    
    def test_prompt_context_allows_exact_coordinates_when_requested(self):
        """Prompt context should expose exact coordinates only when explicitly requested."""
        facts = RaceFacts(
            position=PositionFact(
                latitude=41.1234,
                longitude=-73.5678,
                source_timestamp=datetime.now(timezone.utc)
            ),
            navigation=NavigationFact(
                sog_knots=8.5,
                cog_degrees=270.0,
                source_timestamp=datetime.now(timezone.utc)
            ),
            cycle_timestamp="2026-08-27T15:00:00Z"
        )
        
        context = facts.to_prompt_context(allow_exact_coordinates=True)
        # Coordinates should appear when explicitly allowed
        assert "41.1234" in context
        assert "-73.5678" in context


class TestRaceFactsConstruction:
    """Test RaceFacts construction from API responses."""
    
    def test_from_regatta_responses_valid(self):
        """RaceFacts should construct safely from valid API responses."""
        ts = datetime.now(timezone.utc)
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
            race_id="test-race",
            source_timestamp=ts
        )
        
        is_valid, msg = facts.validate()
        assert is_valid, f"Validation failed: {msg}"
        assert facts.position is not None
        assert facts.navigation is not None
        assert facts.start_line is not None
        assert facts.competitors is not None
        assert facts.competitors.count_nearby == 2
        # Verify timestamps were set correctly
        assert facts.position.source_timestamp == ts
        assert facts.navigation.source_timestamp == ts
    
    def test_missing_sog_not_substituted_with_zero(self):
        """Missing SOG should NOT be substituted with zero."""
        ts = datetime.now(timezone.utc)
        facts = RaceFacts.from_regatta_responses(
            position_resp={"latitude": 41.1234, "longitude": -73.5678},
            navigation_resp={"cog": 270.0},  # SOG missing
            cycle_ts="2026-08-27T15:00:00Z",
            source_timestamp=ts
        )
        
        # Navigation should be None because SOG is missing
        assert facts.navigation is None
        is_valid, msg = facts.validate()
        assert not is_valid
        assert "Navigation" in msg
    
    def test_missing_cog_not_substituted_with_zero(self):
        """Missing COG should NOT be substituted with zero."""
        ts = datetime.now(timezone.utc)
        facts = RaceFacts.from_regatta_responses(
            position_resp={"latitude": 41.1234, "longitude": -73.5678},
            navigation_resp={"sog": 8.5},  # COG missing
            cycle_ts="2026-08-27T15:00:00Z",
            source_timestamp=ts
        )
        
        # Navigation should be None because COG is missing
        assert facts.navigation is None
        is_valid, msg = facts.validate()
        assert not is_valid
    
    def test_wind_not_extracted_from_race_data_resp(self):
        """Wind should NOT be extracted from race_data_resp."""
        ts = datetime.now(timezone.utc)
        facts = RaceFacts.from_regatta_responses(
            position_resp={"latitude": 41.1234, "longitude": -73.5678},
            navigation_resp={"sog": 8.5, "cog": 270.0},
            race_data_resp={
                "wind_direction_true": 180.0,  # Even if present, ignored
                "start_line": {
                    "pin": {"latitude": 41.1200, "longitude": -73.5700},
                    "boat": {"latitude": 41.1250, "longitude": -73.5650}
                }
            },
            cycle_ts="2026-08-27T15:00:00Z",
            source_timestamp=ts
        )
        
        # Wind should be None (not mapped from race_data)
        assert facts.wind is None
        # But position, navigation, and start_line should be valid
        is_valid, msg = facts.validate()
        assert is_valid
    
    def test_malformed_responses_fail_safely(self):
        """Malformed responses should result in None facts, not exceptions."""
        ts = datetime.now(timezone.utc)
        facts = RaceFacts.from_regatta_responses(
            position_resp={"invalid": "data"},
            navigation_resp={"sog": "not_a_number"},
            cycle_ts="2026-08-27T15:00:00Z",
            source_timestamp=ts
        )
        
        # Should not raise, but facts should be invalid
        assert facts.position is None
        assert facts.navigation is None
        is_valid, msg = facts.validate()
        assert not is_valid
    
    def test_coordinates_not_in_prompt_context(self):
        """Prompt context should not expose internal coordinates."""
        ts = datetime.now(timezone.utc)
        facts = RaceFacts.from_regatta_responses(
            position_resp={"latitude": 41.1234, "longitude": -73.5678},
            navigation_resp={"sog": 8.5, "cog": 270.0},
            race_data_resp={
                "start_line": {
                    "pin": {"latitude": 41.1200, "longitude": -73.5700},
                    "boat": {"latitude": 41.1250, "longitude": -73.5650}
                }
            },
            cycle_ts="2026-08-27T15:00:00Z",
            source_timestamp=ts
        )
        
        context = facts.to_prompt_context(allow_exact_coordinates=False)
        # Start line coordinates should NOT appear
        assert "41.1200" not in context
        assert "-73.5700" not in context
        assert "41.1250" not in context
        assert "-73.5650" not in context

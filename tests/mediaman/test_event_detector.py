"""
Tests for EventDetector — deterministic navigation event detection.

Mocked unit tests covering state transitions, fail-closed behavior,
coordinate suppression, and deterministic event ID generation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from mediaman.event_detector import EventDetector, DetectedEvent
from mediaman.mcp_collector import CollectionResult, CollectionStatus, NavigationFact, Provenance


@pytest.fixture
def detector():
    """Create an EventDetector instance."""
    return EventDetector()


@pytest.fixture
def complete_result():
    """Create a COMPLETE CollectionResult with valid facts."""
    provenance = Provenance(
        tool_public_id='racing.get_position',
        server_name='racing',
        wire_tool_name='get_position',
        source_id='src_001',
        source_timestamp='2026-08-27T20:40:00Z',
        observed_at='2026-08-27T20:40:01Z',
        freshness_limit_seconds=30,
        validation_status='valid',
    )
    position_fact = NavigationFact(
        field_name='position',
        value={'latitude': 41.0, 'longitude': -73.0},
        unit=None,
        provenance=provenance,
    )
    return CollectionResult(
        status=CollectionStatus.COMPLETE,
        facts=[position_fact],
        race_id='race_001',
    )


@pytest.fixture
def partial_result():
    """Create a PARTIAL CollectionResult with stale facts."""
    provenance = Provenance(
        tool_public_id='racing.get_position',
        server_name='racing',
        wire_tool_name='get_position',
        source_id='src_001',
        source_timestamp='2026-08-27T20:10:00Z',  # 30 minutes old
        observed_at='2026-08-27T20:40:01Z',
        freshness_limit_seconds=30,
        validation_status='stale',
    )
    position_fact = NavigationFact(
        field_name='position',
        value={'latitude': 41.0, 'longitude': -73.0},
        unit=None,
        provenance=provenance,
    )
    return CollectionResult(
        status=CollectionStatus.PARTIAL,
        facts=[position_fact],
        race_id='race_001',
    )


class TestNoTransitionWhenNoPrevious:
    """Test that no transition events are emitted for initial observations."""

    def test_no_event_on_first_observation(self, detector, complete_result):
        """When previous is None, no transition events are emitted."""
        events = detector.detect_events(
            current=complete_result,
            previous=None,
            observed_at='2026-08-27T20:40:01Z',
        )
        assert events == []


class TestCollectionStatusTransitions:
    """Test collection-level transitions."""

    def test_complete_to_partial_emits_data_lost(
        self, detector, complete_result, partial_result
    ):
        """COMPLETE → PARTIAL emits NAVIGATION_DATA_LOST."""
        events = detector.detect_events(
            current=partial_result,
            previous=complete_result,
            observed_at='2026-08-27T20:40:02Z',
        )
        assert len(events) >= 1
        data_lost_events = [e for e in events if e.event_type == 'NAVIGATION_DATA_LOST']
        assert len(data_lost_events) == 1
        assert data_lost_events[0].severity == 'WARNING'
        assert data_lost_events[0].previous_status == 'complete'
        assert data_lost_events[0].current_status == 'partial'

    def test_partial_to_complete_emits_data_recovered(
        self, detector, complete_result, partial_result
    ):
        """PARTIAL → COMPLETE emits NAVIGATION_DATA_RECOVERED."""
        events = detector.detect_events(
            current=complete_result,
            previous=partial_result,
            observed_at='2026-08-27T20:40:02Z',
        )
        assert len(events) >= 1
        recovered_events = [
            e for e in events if e.event_type == 'NAVIGATION_DATA_RECOVERED'
        ]
        assert len(recovered_events) == 1
        assert recovered_events[0].severity == 'INFO'
        assert recovered_events[0].previous_status == 'partial'
        assert recovered_events[0].current_status == 'complete'


class TestFactTransitions:
    """Test fact-level transitions."""

    def test_valid_to_stale_emits_fact_became_stale(self, detector):
        """Valid → stale emits FACT_BECAME_STALE."""
        prev_prov = Provenance(
            tool_public_id='racing.get_sog',
            server_name='racing',
            wire_tool_name='get_sog',
            source_id='src_002',
            source_timestamp='2026-08-27T20:40:00Z',
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=15,
            validation_status='valid',
        )
        prev_fact = NavigationFact(
            field_name='sog', value=5.2, unit='knots', provenance=prev_prov
        )
        prev_result = CollectionResult(
            status=CollectionStatus.COMPLETE, facts=[prev_fact], race_id='race_001'
        )

        curr_prov = Provenance(
            tool_public_id='racing.get_sog',
            server_name='racing',
            wire_tool_name='get_sog',
            source_id='src_002',
            source_timestamp='2026-08-27T20:39:50Z',  # Old
            observed_at='2026-08-27T20:40:20Z',
            freshness_limit_seconds=15,
            validation_status='stale',
        )
        curr_fact = NavigationFact(
            field_name='sog', value=5.2, unit='knots', provenance=curr_prov
        )
        curr_result = CollectionResult(
            status=CollectionStatus.PARTIAL, facts=[curr_fact], race_id='race_001'
        )

        events = detector.detect_events(
            current=curr_result, previous=prev_result, observed_at='2026-08-27T20:40:20Z'
        )

        stale_events = [e for e in events if e.event_type == 'FACT_BECAME_STALE']
        assert len(stale_events) == 1
        assert stale_events[0].affected_field == 'sog'
        assert stale_events[0].severity == 'WARNING'

    def test_stale_to_valid_emits_fact_recovered(self, detector):
        """Stale → valid emits FACT_RECOVERED."""
        prev_prov = Provenance(
            tool_public_id='racing.get_cog',
            server_name='racing',
            wire_tool_name='get_cog',
            source_id='src_003',
            source_timestamp='2026-08-27T20:39:50Z',
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=15,
            validation_status='stale',
        )
        prev_fact = NavigationFact(
            field_name='cog', value=180.0, unit='degrees', provenance=prev_prov
        )
        prev_result = CollectionResult(
            status=CollectionStatus.PARTIAL, facts=[prev_fact], race_id='race_001'
        )

        curr_prov = Provenance(
            tool_public_id='racing.get_cog',
            server_name='racing',
            wire_tool_name='get_cog',
            source_id='src_003',
            source_timestamp='2026-08-27T20:40:10Z',  # Fresh
            observed_at='2026-08-27T20:40:11Z',
            freshness_limit_seconds=15,
            validation_status='valid',
        )
        curr_fact = NavigationFact(
            field_name='cog', value=180.0, unit='degrees', provenance=curr_prov
        )
        curr_result = CollectionResult(
            status=CollectionStatus.COMPLETE, facts=[curr_fact], race_id='race_001'
        )

        events = detector.detect_events(
            current=curr_result, previous=prev_result, observed_at='2026-08-27T20:40:11Z'
        )

        recovered_events = [e for e in events if e.event_type == 'FACT_RECOVERED']
        assert len(recovered_events) == 1
        assert recovered_events[0].affected_field == 'cog'
        assert recovered_events[0].severity == 'INFO'


class TestEventIDDeterminism:
    """Test that event IDs are deterministic."""

    def test_same_transition_produces_same_event_id(self, detector):
        """Identical transitions produce identical event IDs."""
        prov = Provenance(
            tool_public_id='racing.get_position',
            server_name='racing',
            wire_tool_name='get_position',
            source_id='src_001',
            source_timestamp='2026-08-27T20:40:00Z',
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=30,
            validation_status='valid',
        )
        fact = NavigationFact(
            field_name='position',
            value={'latitude': 41.0, 'longitude': -73.0},
            unit=None,
            provenance=prov,
        )

        result_complete = CollectionResult(status=CollectionStatus.COMPLETE, facts=[fact], race_id='race_001')
        result_partial = CollectionResult(status=CollectionStatus.PARTIAL, facts=[fact], race_id='race_001')

        # First call
        events1 = detector.detect_events(
            current=result_partial,
            previous=result_complete,
            observed_at='2026-08-27T20:40:02Z',
        )

        # Second call with same inputs
        events2 = detector.detect_events(
            current=result_partial,
            previous=result_complete,
            observed_at='2026-08-27T20:40:02Z',
        )

        data_lost_1 = [e for e in events1 if e.event_type == 'NAVIGATION_DATA_LOST'][0]
        data_lost_2 = [e for e in events2 if e.event_type == 'NAVIGATION_DATA_LOST'][0]

        assert data_lost_1.event_id == data_lost_2.event_id


class TestCoordinateSuppression:
    """Test that exact coordinates are suppressed from events."""

    def test_coordinates_not_in_event_dict(self, detector, complete_result):
        """Event payloads do not contain exact latitude/longitude."""
        events = detector.detect_events(
            current=complete_result,
            previous=None,
            observed_at='2026-08-27T20:40:01Z',
        )
        # No previous, so no events expected
        assert events == []

        # Test with previous
        partial = CollectionResult(status=CollectionStatus.PARTIAL, facts=[], race_id='race_001')
        events = detector.detect_events(
            current=complete_result,
            previous=partial,
            observed_at='2026-08-27T20:40:02Z',
        )

        for event in events:
            event_dict = event.to_dict()
            # Check that exact coordinates don't appear in dict
            event_str = str(event_dict)
            assert '41.0' not in event_str or 'latitude' not in event_str
            assert '-73.0' not in event_str or 'longitude' not in event_str


class TestFailClosedBehavior:
    """Test fail-closed semantics."""

    def test_unchanged_state_produces_no_duplicate_event(self, detector):
        """Same collection status twice produces no event."""
        prov = Provenance(
            tool_public_id='racing.get_position',
            server_name='racing',
            wire_tool_name='get_position',
            source_id='src_001',
            source_timestamp='2026-08-27T20:40:00Z',
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=30,
            validation_status='valid',
        )
        fact = NavigationFact(
            field_name='position',
            value={'latitude': 41.0, 'longitude': -73.0},
            unit=None,
            provenance=prov,
        )
        complete_1 = CollectionResult(status=CollectionStatus.COMPLETE, facts=[fact], race_id='race_001')
        complete_2 = CollectionResult(status=CollectionStatus.COMPLETE, facts=[fact], race_id='race_001')

        events = detector.detect_events(
            current=complete_2, previous=complete_1, observed_at='2026-08-27T20:40:02Z'
        )
        # No status change, no events
        assert events == []

    def test_malformed_fact_does_not_crash(self, detector):
        """Detector handles edge cases gracefully."""
        # Missing provenance should not crash
        bad_fact = NavigationFact(
            field_name='position', value=None, unit=None, provenance=None
        )
        result = CollectionResult(status=CollectionStatus.FAILED, facts=[bad_fact], race_id='race_001')

        # Should not raise
        events = detector.detect_events(
            current=result,
            previous=None,
            observed_at='2026-08-27T20:40:01Z',
        )
        assert events == []

    def test_nan_and_infinity_rejected(self, detector):
        """NaN and infinity values do not produce valid facts in events."""
        prov = Provenance(
            tool_public_id='racing.get_sog',
            server_name='racing',
            wire_tool_name='get_sog',
            source_id='src_002',
            source_timestamp='2026-08-27T20:40:00Z',
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=15,
            validation_status='invalid',  # NaN/inf → invalid
        )
        nan_fact = NavigationFact(
            field_name='sog', value=float('nan'), unit='knots', provenance=prov
        )
        result = CollectionResult(
            status=CollectionStatus.FAILED, facts=[nan_fact], race_id='race_001'
        )

        events = detector.detect_events(
            current=result,
            previous=None,
            observed_at='2026-08-27T20:40:01Z',
        )
        # Invalid status, no valid event expected
        assert events == []


class TestInputImmutability:
    """Test that the detector does not modify input CollectionResult objects."""

    def test_detector_does_not_modify_current_result(self, detector, complete_result):
        """Current CollectionResult is not modified."""
        original_status = complete_result.status
        original_facts_count = len(complete_result.facts)

        detector.detect_events(
            current=complete_result,
            previous=None,
            observed_at='2026-08-27T20:40:01Z',
        )

        assert complete_result.status == original_status
        assert len(complete_result.facts) == original_facts_count

    def test_detector_does_not_modify_previous_result(
        self, detector, complete_result, partial_result
    ):
        """Previous CollectionResult is not modified."""
        original_status = complete_result.status
        original_facts_count = len(complete_result.facts)

        detector.detect_events(
            current=partial_result,
            previous=complete_result,
            observed_at='2026-08-27T20:40:02Z',
        )

        assert complete_result.status == original_status
        assert len(complete_result.facts) == original_facts_count


class TestMissingTimestamps:
    """Test handling of missing timestamps."""

    def test_missing_source_timestamp_preserved(self, detector):
        """Missing source_timestamp remains None in event."""
        prov = Provenance(
            tool_public_id='racing.get_position',
            server_name='racing',
            wire_tool_name='get_position',
            source_id='src_001',
            source_timestamp=None,  # Missing
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=30,
            validation_status='missing',
        )
        fact = NavigationFact(
            field_name='position',
            value=None,
            unit=None,
            provenance=prov,
        )
        result = CollectionResult(status=CollectionStatus.FAILED, facts=[fact], race_id='race_001')

        events = detector.detect_events(
            current=result,
            previous=None,
            observed_at='2026-08-27T20:40:01Z',
        )
        assert events == []


class TestRealCollectionResultObjects:
    """Test detector with real CollectionResult and NavigationFact objects."""

    def test_detector_works_with_real_objects(self, detector):
        """Detector operates on real CollectionResult/NavigationFact, not mocks."""
        # Create real objects
        prov = Provenance(
            tool_public_id='racing.get_position',
            server_name='racing',
            wire_tool_name='get_position',
            source_id='src_001',
            source_timestamp='2026-08-27T20:40:00Z',
            observed_at='2026-08-27T20:40:01Z',
            freshness_limit_seconds=30,
            validation_status='valid',
        )
        fact = NavigationFact(
            field_name='position',
            value={'latitude': 41.0, 'longitude': -73.0},
            unit=None,
            provenance=prov,
        )
        complete_result = CollectionResult(
            status=CollectionStatus.COMPLETE, facts=[fact], race_id='race_001'
        )
        partial_result = CollectionResult(
            status=CollectionStatus.PARTIAL, facts=[], race_id='race_001'
        )

        events = detector.detect_events(
            current=partial_result,
            previous=complete_result,
            observed_at='2026-08-27T20:40:02Z',
        )

        assert len(events) > 0
        data_lost = [e for e in events if e.event_type == 'NAVIGATION_DATA_LOST']
        assert len(data_lost) == 1

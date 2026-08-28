"""
EventDetector — Deterministic navigation event detection.

Compares previous and current CollectionResult objects to emit structured
DetectedEvent objects for state transitions.

Side-effect-free. No external service contact. Mocked test boundary.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone
import hashlib

from mediaman.mcp_collector import CollectionResult, NavigationFact


@dataclass
class DetectedEvent:
    """A structured event emitted by the EventDetector."""

    event_id: str
    event_type: str  # NAVIGATION_DATA_LOST, RECOVERED, FACT_BECAME_STALE, etc.
    observed_at: str  # ISO 8601 UTC
    source_timestamp: Optional[str] = None
    race_id: Optional[str] = None
    severity: str = "INFO"  # INFO, WARNING, ERROR
    affected_field: Optional[str] = None
    previous_status: Optional[str] = None
    current_status: Optional[str] = None
    tool_public_id: Optional[str] = None
    server_name: Optional[str] = None
    freshness_limit_seconds: Optional[int] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict (no exact coordinates)."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'observed_at': self.observed_at,
            'source_timestamp': self.source_timestamp,
            'race_id': self.race_id,
            'severity': self.severity,
            'affected_field': self.affected_field,
            'previous_status': self.previous_status,
            'current_status': self.current_status,
            'tool_public_id': self.tool_public_id,
            'server_name': self.server_name,
            'freshness_limit_seconds': self.freshness_limit_seconds,
            'warnings': self.warnings,
        }


class EventDetector:
    """
    Deterministic event detector for navigation data transitions.

    Input: optional previous CollectionResult + current CollectionResult + observed_at
    Output: list of DetectedEvent objects
    """

    def __init__(self, logger=None):
        """Initialize detector with optional logger."""
        self.logger = logger

    def detect_events(
        self,
        current: CollectionResult,
        previous: Optional[CollectionResult] = None,
        observed_at: Optional[str] = None,
    ) -> List[DetectedEvent]:
        """
        Detect state transition events.

        Args:
            current: Current CollectionResult
            previous: Previous CollectionResult or None
            observed_at: Deterministic observed_at for testing (defaults to now UTC)

        Returns:
            List of DetectedEvent objects
        """
        events = []

        # Use provided observed_at or current timestamp
        if observed_at is None:
            observed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', '') + 'Z'

        # If no previous result, do not fabricate transition events
        if previous is None:
            return events

        # Collection-level events (COMPLETE/PARTIAL/FAILED transitions)
        events.extend(
            self._detect_collection_status_changes(
                current, previous, observed_at
            )
        )

        # Fact-level events (stale, recovered, invalid transitions)
        events.extend(
            self._detect_fact_transitions(current, previous, observed_at)
        )

        return events

    def _detect_collection_status_changes(
        self,
        current: CollectionResult,
        previous: CollectionResult,
        observed_at: str,
    ) -> List[DetectedEvent]:
        """Detect COMPLETE/PARTIAL transitions."""
        events = []

        prev_status = previous.status
        curr_status = current.status

        # NAVIGATION_DATA_LOST: COMPLETE → PARTIAL/FAILED/etc.
        if prev_status == 'COMPLETE' and curr_status != 'COMPLETE':
            event = DetectedEvent(
                event_id=self._make_event_id(
                    current.race_id, 'NAVIGATION_DATA_LOST', None, observed_at
                ),
                event_type='NAVIGATION_DATA_LOST',
                observed_at=observed_at,
                source_timestamp=None,
                race_id=current.race_id,
                severity='WARNING',
                affected_field=None,
                previous_status=prev_status,
                current_status=curr_status,
                warnings=[f'Navigation collection status degraded: {prev_status} → {curr_status}'],
            )
            events.append(event)

        # NAVIGATION_DATA_RECOVERED: non-COMPLETE → COMPLETE
        if prev_status != 'COMPLETE' and curr_status == 'COMPLETE':
            event = DetectedEvent(
                event_id=self._make_event_id(
                    current.race_id, 'NAVIGATION_DATA_RECOVERED', None, observed_at
                ),
                event_type='NAVIGATION_DATA_RECOVERED',
                observed_at=observed_at,
                source_timestamp=None,
                race_id=current.race_id,
                severity='INFO',
                affected_field=None,
                previous_status=prev_status,
                current_status=curr_status,
                warnings=[],
            )
            events.append(event)

        return events

    def _detect_fact_transitions(
        self,
        current: CollectionResult,
        previous: CollectionResult,
        observed_at: str,
    ) -> List[DetectedEvent]:
        """Detect fact-level transitions (stale, recovered, invalid)."""
        events = []

        # Build a map of field_name → NavigationFact for quick lookup
        curr_facts = {f.field_name: f for f in current.facts}
        prev_facts = {f.field_name: f for f in previous.facts}

        # Check all facts that existed in previous
        for field_name, prev_fact in prev_facts.items():
            if field_name not in curr_facts:
                # Fact disappeared; skip (no explicit event in Step 4A)
                continue

            curr_fact = curr_facts[field_name]
            prev_status = prev_fact.provenance.validation_status
            curr_status = curr_fact.provenance.validation_status

            # FACT_BECAME_STALE
            if prev_status != 'stale' and curr_status == 'stale':
                event = DetectedEvent(
                    event_id=self._make_event_id(
                        current.race_id,
                        'FACT_BECAME_STALE',
                        field_name,
                        observed_at,
                    ),
                    event_type='FACT_BECAME_STALE',
                    observed_at=observed_at,
                    source_timestamp=curr_fact.provenance.source_timestamp,
                    race_id=current.race_id,
                    severity='WARNING',
                    affected_field=field_name,
                    previous_status=prev_status,
                    current_status=curr_status,
                    tool_public_id=curr_fact.provenance.tool_public_id,
                    server_name=curr_fact.provenance.server_name,
                    freshness_limit_seconds=curr_fact.provenance.freshness_limit_seconds,
                    warnings=[f'{field_name} became stale'],
                )
                events.append(event)

            # FACT_BECAME_INVALID
            if prev_status != 'invalid' and curr_status == 'invalid':
                event = DetectedEvent(
                    event_id=self._make_event_id(
                        current.race_id,
                        'FACT_BECAME_INVALID',
                        field_name,
                        observed_at,
                    ),
                    event_type='FACT_BECAME_INVALID',
                    observed_at=observed_at,
                    source_timestamp=curr_fact.provenance.source_timestamp,
                    race_id=current.race_id,
                    severity='ERROR',
                    affected_field=field_name,
                    previous_status=prev_status,
                    current_status=curr_status,
                    tool_public_id=curr_fact.provenance.tool_public_id,
                    server_name=curr_fact.provenance.server_name,
                    freshness_limit_seconds=curr_fact.provenance.freshness_limit_seconds,
                    warnings=[f'{field_name} is invalid'],
                )
                events.append(event)

            # FACT_RECOVERED
            if prev_status in ('stale', 'missing', 'invalid') and curr_status == 'valid':
                event = DetectedEvent(
                    event_id=self._make_event_id(
                        current.race_id,
                        'FACT_RECOVERED',
                        field_name,
                        observed_at,
                    ),
                    event_type='FACT_RECOVERED',
                    observed_at=observed_at,
                    source_timestamp=curr_fact.provenance.source_timestamp,
                    race_id=current.race_id,
                    severity='INFO',
                    affected_field=field_name,
                    previous_status=prev_status,
                    current_status=curr_status,
                    tool_public_id=curr_fact.provenance.tool_public_id,
                    server_name=curr_fact.provenance.server_name,
                    freshness_limit_seconds=curr_fact.provenance.freshness_limit_seconds,
                    warnings=[],
                )
                events.append(event)

        return events

    @staticmethod
    def _make_event_id(
        race_id: Optional[str],
        event_type: str,
        field_name: Optional[str],
        observed_at: str,
    ) -> str:
        """
        Generate a deterministic event ID.

        Hashes: race_id + event_type + field_name + observed_at
        No random UUIDs, no exact coordinates, no credentials.
        """
        components = [
            race_id or 'none',
            event_type,
            field_name or 'collection',
            observed_at,
        ]
        digest = hashlib.sha256('|'.join(components).encode()).hexdigest()
        return f"evt_{event_type.lower()}_{digest[:16]}"

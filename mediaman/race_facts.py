"""
RaceFacts — Validated, source-backed data for LLM content generation.

Contains only deterministic, proven values from documented Regatta API endpoints.
Fails closed when mandatory fields are unavailable or stale.

Timestamp model:
- source_timestamp: When the data source collected the measurement
- observed_at: When MediaMan parsed the response (local time)

Missing values remain unavailable (never become zero).
Exact coordinates are suppressed from prompt context by default.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import json


@dataclass
class WindFact:
    """Wind observation with source and freshness metadata.
    
    UNPROVEN: Wind is currently excluded from FactRegistry.
    /api/race_data does NOT return wind_direction_true.
    MCP racing.get_wind_true requires timestamp audit.
    """
    direction_true: Optional[float] = None  # degrees (0-360)
    source: str = "unknown"  # Unproven source
    source_timestamp: Optional[datetime] = None  # When source collected measurement
    observed_at: Optional[datetime] = None  # When MediaMan parsed it
    max_age_minutes: int = 30  # acceptable staleness
    
    @property
    def is_stale(self) -> bool:
        """Check if wind observation exceeds max age."""
        if not self.source_timestamp:
            # No source timestamp means staleness is unknown
            return True
        age = datetime.now(timezone.utc) - self.source_timestamp
        return age > timedelta(minutes=self.max_age_minutes)
    
    def is_valid(self) -> bool:
        """Wind valid only if present, recent, and in range.
        
        Currently: Wind is UNPROVEN and always invalid.
        Until MCP timestamp audit completes, wind is omitted from facts.
        """
        return False


@dataclass
class PositionFact:
    """Own ship position with source and freshness."""
    latitude: float  # degrees
    longitude: float  # degrees
    source: str = "/api/position"
    source_timestamp: Optional[datetime] = None  # When source collected measurement
    observed_at: Optional[datetime] = None  # When MediaMan parsed it
    max_age_seconds: int = 10
    
    @property
    def is_stale(self) -> bool:
        """Position stale if older than 10 seconds."""
        if not self.source_timestamp:
            # No source timestamp means we can't determine freshness
            return True
        age = datetime.now(timezone.utc) - self.source_timestamp
        return age > timedelta(seconds=self.max_age_seconds)
    
    def is_valid(self) -> bool:
        """Position valid only if recent and in reasonable bounds."""
        if not self.source_timestamp or self.is_stale:
            return False
        # Basic bounds check (not equator/prime meridian)
        if abs(self.latitude) < 0.001 and abs(self.longitude) < 0.001:
            return False
        return True


@dataclass
class NavigationFact:
    """Speed and course with freshness.
    
    Missing values must remain unavailable (never become zero).
    """
    sog_knots: Optional[float] = None  # Speed Over Ground
    cog_degrees: Optional[float] = None  # Course Over Ground True
    source: str = "/api/navigation"
    source_timestamp: Optional[datetime] = None  # When source collected measurement
    observed_at: Optional[datetime] = None  # When MediaMan parsed it
    max_age_seconds: int = 10
    
    @property
    def is_stale(self) -> bool:
        """Navigation stale if older than 10 seconds."""
        if not self.source_timestamp:
            # No source timestamp means we can't determine freshness
            return True
        age = datetime.now(timezone.utc) - self.source_timestamp
        return age > timedelta(seconds=self.max_age_seconds)
    
    def is_valid(self) -> bool:
        """Navigation valid if recent and in reasonable ranges."""
        if not self.source_timestamp or self.is_stale:
            return False
        if self.sog_knots is None or self.cog_degrees is None:
            return False
        if self.sog_knots < 0 or self.sog_knots > 30:  # Reasonable sailing range
            return False
        if not (0 <= self.cog_degrees <= 360):
            return False
        return True


@dataclass
class StartLineFact:
    """Start line geometry from Signal K storage.
    
    Coordinates are stored internally for geometry calculations.
    They are NOT exposed to LLM context by default.
    """
    pin_latitude: Optional[float] = None
    pin_longitude: Optional[float] = None
    boat_latitude: Optional[float] = None
    boat_longitude: Optional[float] = None
    source: str = "/api/race_data"
    source_timestamp: Optional[datetime] = None  # When source collected measurement
    observed_at: Optional[datetime] = None  # When MediaMan parsed it
    max_age_seconds: int = 300  # 5 minutes acceptable
    
    @property
    def is_stale(self) -> bool:
        """Start line stale if older than 5 minutes."""
        if not self.source_timestamp:
            # No source timestamp means we can't determine freshness
            return True
        age = datetime.now(timezone.utc) - self.source_timestamp
        return age > timedelta(seconds=self.max_age_seconds)
    
    def is_valid(self) -> bool:
        """Start line valid if we have both points and recent."""
        if not self.source_timestamp or self.is_stale:
            return False
        if not all([self.pin_latitude, self.pin_longitude,
                    self.boat_latitude, self.boat_longitude]):
            return False
        return True


@dataclass
class CompetitorFact:
    """Nearby competitor observation from AIS.
    
    Exact competitor positions are stored internally.
    Only count is exposed to LLM context.
    """
    count_nearby: int = 0  # Number of vessels within radius
    source: str = "/api/ais"
    source_timestamp: Optional[datetime] = None  # When source collected measurement (query time)
    observed_at: Optional[datetime] = None  # When MediaMan parsed it
    max_age_seconds: int = 60
    
    @property
    def is_stale(self) -> bool:
        """Competitor data stale if older than 1 minute."""
        if not self.source_timestamp:
            # No source timestamp means we can't determine freshness
            return True
        age = datetime.now(timezone.utc) - self.source_timestamp
        return age > timedelta(seconds=self.max_age_seconds)
    
    def is_valid(self) -> bool:
        """Competitors valid if recent."""
        if not self.source_timestamp or self.is_stale:
            return False
        return self.count_nearby >= 0


@dataclass
class RaceFacts:
    """
    Single source of truth for race data available to LLM content generation.
    
    Contains only fields confirmed by actual Regatta API responses and
    Signal K storage. Fails closed (rejects) if mandatory facts are missing
    or stale.
    
    Timestamp model:
    - source_timestamp comes FROM the API response
    - observed_at is WHEN MediaMan parsed it
    - freshness is determined by source_timestamp age, never observed_at
    """
    
    # Mandatory facts (must be present and fresh)
    position: Optional[PositionFact] = None
    navigation: Optional[NavigationFact] = None
    
    # Optional facts (can be omitted without failing validation)
    wind: Optional[WindFact] = None
    start_line: Optional[StartLineFact] = None
    competitors: Optional[CompetitorFact] = None
    
    # Cycle tracking
    cycle_timestamp: Optional[str] = None  # ISO 8601 UTC
    race_id: Optional[str] = None
    
    # Metadata
    collected_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    data_sources: Dict[str, str] = field(default_factory=dict)  # mapping of field→source URL
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate RaceFacts. Return (is_valid, error_message).
        
        Mandatory:
        - position must be valid (not stale, in bounds)
        - navigation must be valid (not stale, in range)
        - cycle_timestamp must be present
        
        Optional:
        - wind, start_line, competitors can be None or stale
        - they will be omitted from prompt if unavailable
        
        Returns (True, "") if valid, or (False, "reason") if invalid.
        """
        if not self.position or not self.position.is_valid():
            return False, "Position mandatory and must be recent (< 10 seconds)"
        
        if not self.navigation or not self.navigation.is_valid():
            return False, "Navigation mandatory and must be recent (< 10 seconds)"
        
        if not self.cycle_timestamp:
            return False, "Cycle timestamp required"
        
        return True, ""
    
    def to_prompt_context(self, allow_exact_coordinates: bool = False) -> str:
        """
        Generate context string for LLM prompt from validated facts.
        
        Omits unavailable or stale optional fields.
        Only uses facts that have been validated and are recent.
        
        By default, exact coordinates are suppressed from prompt context.
        Set allow_exact_coordinates=True only if specifically needed.
        """
        lines = []
        
        # Mandatory facts
        if self.position and self.position.is_valid():
            if allow_exact_coordinates:
                lines.append(f"Position: {self.position.latitude:.4f}°N, {self.position.longitude:.4f}°E")
            else:
                lines.append("Position: On course (coordinates stored internally)")
        
        if self.navigation and self.navigation.is_valid():
            lines.append(f"Speed: {self.navigation.sog_knots:.1f} knots")
            lines.append(f"Course: {self.navigation.cog_degrees:.0f}° true")
        
        # Optional facts
        if self.wind and self.wind.is_valid():
            lines.append(f"Wind direction: {self.wind.direction_true:.0f}° true ({self.wind.source})")
        
        if self.start_line and self.start_line.is_valid():
            lines.append("Start line pinned (geometry stored internally)")
        
        if self.competitors and self.competitors.is_valid() and self.competitors.count_nearby > 0:
            lines.append(f"Nearby vessels: {self.competitors.count_nearby} detected (AIS)")
        
        # Cycle and race ID
        if self.cycle_timestamp:
            lines.append(f"Cycle: {self.cycle_timestamp} UTC")
        if self.race_id:
            lines.append(f"Race ID: {self.race_id}")
        
        return "\n".join(lines)
    
    @staticmethod
    def from_regatta_responses(
        position_resp: Optional[Dict[str, Any]] = None,
        navigation_resp: Optional[Dict[str, Any]] = None,
        race_data_resp: Optional[Dict[str, Any]] = None,
        ais_resp: Optional[Dict[str, Any]] = None,
        cycle_ts: Optional[str] = None,
        race_id: Optional[str] = None,
        source_timestamp: Optional[datetime] = None
    ) -> "RaceFacts":
        """
        Construct RaceFacts from Regatta API responses.
        
        Safe construction: if a response field is missing or malformed,
        that fact is set to None (making it optional for validation).
        
        source_timestamp: When the API request was issued.
                         Used for all facts if individual timestamps unavailable.
        
        CRITICAL: Missing mandatory values are NOT substituted with zero.
        """
        if not source_timestamp:
            source_timestamp = datetime.now(timezone.utc)
        
        facts = RaceFacts(cycle_timestamp=cycle_ts, race_id=race_id)
        
        # Parse position
        if position_resp and isinstance(position_resp, dict):
            try:
                lat = position_resp.get("latitude")
                lon = position_resp.get("longitude")
                # Explicit presence check: must be in dict and not None
                if lat is None or lon is None:
                    facts.position = None
                else:
                    facts.position = PositionFact(
                        latitude=float(lat),
                        longitude=float(lon),
                        source_timestamp=source_timestamp,
                        observed_at=datetime.now(timezone.utc)
                    )
                    facts.data_sources["position"] = "/api/position"
            except (ValueError, TypeError, KeyError):
                facts.position = None
        
        # Parse navigation — MANDATORY fields must be present, NOT zero-substituted
        if navigation_resp and isinstance(navigation_resp, dict):
            try:
                sog = navigation_resp.get("sog")
                cog = navigation_resp.get("cog")
                # CRITICAL: Missing values must remain unavailable, NOT become zero
                if sog is None or cog is None:
                    facts.navigation = None
                else:
                    sog_knots = float(sog)
                    cog_degrees = float(cog)
                    facts.navigation = NavigationFact(
                        sog_knots=sog_knots,
                        cog_degrees=cog_degrees,
                        source_timestamp=source_timestamp,
                        observed_at=datetime.now(timezone.utc)
                    )
                    facts.data_sources["navigation"] = "/api/navigation"
            except (ValueError, TypeError, KeyError):
                facts.navigation = None
        
        # Parse race_data
        # CRITICAL: /api/race_data DOES NOT expose wind_direction_true
        # Source audit confirmed it returns only start line geometry and bearing calculations.
        # Wind is NOT a supported field from this endpoint.
        if race_data_resp and isinstance(race_data_resp, dict):
            # Start line coordinates are NOT exposed to LLM by default
            # They are stored internally for geometry calculations only
            start_line_data = race_data_resp.get("start_line")
            if start_line_data and isinstance(start_line_data, dict):
                pin = start_line_data.get("pin")
                boat = start_line_data.get("boat")
                if pin and boat:
                    try:
                        facts.start_line = StartLineFact(
                            pin_latitude=float(pin.get("latitude")),
                            pin_longitude=float(pin.get("longitude")),
                            boat_latitude=float(boat.get("latitude")),
                            boat_longitude=float(boat.get("longitude")),
                            source_timestamp=source_timestamp,
                            observed_at=datetime.now(timezone.utc)
                        )
                        facts.data_sources["start_line"] = "/api/race_data"
                    except (ValueError, TypeError, KeyError):
                        facts.start_line = None
        
        # Parse AIS competitors
        if ais_resp and isinstance(ais_resp, dict):
            try:
                targets = ais_resp.get("targets", [])
                count = len(targets) if isinstance(targets, list) else 0
                facts.competitors = CompetitorFact(
                    count_nearby=count,
                    source_timestamp=source_timestamp,
                    observed_at=datetime.now(timezone.utc)
                )
                facts.data_sources["competitors"] = "/api/ais"
            except (TypeError, ValueError, KeyError):
                facts.competitors = None
        
        return facts

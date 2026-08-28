"""
Expanded MCP Collector for MediaMan — source-backed navigation fact collection (CORRECTED).

Collects structured navigation facts from validated MCP servers using the hardened
MCPClient. Implements actual freshness validation, logging instrumentation, and
LLM-safe serialization.

Features:
- Source-verified tool collection (racing.get_position, racing.get_sog, racing.get_cog)
- Provenance tracking with complete metadata
- Fail-closed collection (missing values remain None, no fabrication)
- Deterministic freshness validation (ISO 8601 parsing with injected reference time)
- Structured logging (STARTUP, DATA_IN, DATA_OUT, ERROR, SHUTDOWN)
- LLM-safe serialization (no exact coordinates, no credentials)
- Mocked testing support (dependency injection)
- No live MCP, Signal K, InfluxDB, or network access
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timezone

from mediaman.mcp_client import MCPClient, MCPClientError, MCPProtocolError, MCPServerError, MCPTimeoutError


class CollectionStatus(Enum):
    """Outcome of a collector run."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    INVALID = "invalid"
    FAILED = "failed"


@dataclass
class Provenance:
    """Source tracking for every collected fact."""
    tool_public_id: str  # e.g., "racing.get_position"
    server_name: str  # e.g., "racing"
    wire_tool_name: str  # e.g., "get_position"
    source_id: str  # sanitized source identifier
    source_timestamp: Optional[str] = None  # ISO 8601 UTC or UNKNOWN (never fabricated)
    observed_at: Optional[str] = None  # local collection time (distinct from source)
    freshness_limit_seconds: Optional[int] = None
    validation_status: str = "valid"  # "valid", "stale", "missing"
    warnings: List[str] = field(default_factory=list)


@dataclass
class NavigationFact:
    """A single collected navigation fact."""
    field_name: str
    value: Any
    unit: str
    provenance: Provenance


@dataclass
class CollectionResult:
    """Complete collection run with diagnostics."""
    status: CollectionStatus
    race_id: Optional[str]
    facts: List[NavigationFact] = field(default_factory=list)
    tools_attempted: List[str] = field(default_factory=list)
    tools_succeeded: List[str] = field(default_factory=list)
    tools_failed: List[str] = field(default_factory=list)
    collection_start_at: Optional[str] = None
    collection_end_at: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to dict (exact coordinates NOT included)."""
        return {
            'status': self.status.value,
            'race_id': self.race_id,
            'facts': [
                {
                    'field_name': fact.field_name,
                    'value': fact.value,
                    'unit': fact.unit,
                    'provenance': {
                        'tool_public_id': fact.provenance.tool_public_id,
                        'server_name': fact.provenance.server_name,
                        'wire_tool_name': fact.provenance.wire_tool_name,
                        'source_id': fact.provenance.source_id,
                        'source_timestamp': fact.provenance.source_timestamp,
                        'observed_at': fact.provenance.observed_at,
                        'freshness_limit_seconds': fact.provenance.freshness_limit_seconds,
                        'validation_status': fact.provenance.validation_status,
                        'warnings': fact.provenance.warnings,
                    }
                }
                for fact in self.facts
            ],
            'tools_attempted': self.tools_attempted,
            'tools_succeeded': self.tools_succeeded,
            'tools_failed': self.tools_failed,
            'collection_start_at': self.collection_start_at,
            'collection_end_at': self.collection_end_at,
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def to_llm_context(self) -> Dict:
        """
        LLM-safe serialization without exact coordinates or credentials.
        
        Omits:
        - Exact latitude and longitude values
        - Raw MCP envelopes
        - Connection credentials
        - Sensitive metadata
        
        Preserves:
        - Field names and types (without exact values for coordinates)
        - Provenance summaries
        - Freshness status
        - Warnings and errors
        """
        safe_facts = []
        for fact in self.facts:
            # Suppress exact coordinates for LLM safety
            if fact.field_name in ('latitude', 'longitude'):
                safe_value = f"<coordinate suppressed>"
            else:
                safe_value = fact.value
            
            safe_facts.append({
                'field_name': fact.field_name,
                'value': safe_value,
                'unit': fact.unit,
                'provenance_summary': {
                    'tool': fact.provenance.tool_public_id,
                    'server': fact.provenance.server_name,
                    'freshness_status': fact.provenance.validation_status,
                    'freshness_limit_seconds': fact.provenance.freshness_limit_seconds,
                },
            })
        
        return {
            'status': self.status.value,
            'race_id': self.race_id,
            'facts': safe_facts,
            'tools_attempted': self.tools_attempted,
            'tools_succeeded': self.tools_succeeded,
            'tools_failed': self.tools_failed,
            'collection_start_at': self.collection_start_at,
            'collection_end_at': self.collection_end_at,
            'errors': self.errors,
            'warnings': self.warnings,
        }


class SourceVerifiedTools(Enum):
    """Source-verified MCP tools only."""
    POSITION = ("racing.get_position", "position")
    SOG = ("racing.get_sog", "sog")
    COG = ("racing.get_cog", "cog")
    
    @property
    def public_id(self) -> str:
        return self.value[0]
    
    @property
    def wire_name(self) -> str:
        return self.value[1]


class MCPCollector:
    """
    Expanded MCP collector with verified tools, deterministic freshness,
    logging, and LLM-safe serialization.
    """
    
    # Freshness limits (seconds) from source verification
    FRESHNESS_LIMITS = {
        "racing.get_position": 30,
        "racing.get_sog": 15,
        "racing.get_cog": 15,
    }
    
    def __init__(self, client: MCPClient, race_id: Optional[str] = None, reference_time: Optional[str] = None):
        """
        Initialize the collector.
        
        Args:
            client: Initialized MCPClient
            race_id: Optional race identifier
            reference_time: Optional ISO 8601 UTC timestamp for deterministic tests
        """
        self.client = client
        self.race_id = race_id
        self.reference_time = reference_time  # For deterministic testing
        self.logger = logging.getLogger(__name__)

    def collect(self, tools: Optional[List[SourceVerifiedTools]] = None) -> CollectionResult:
        """
        Collect navigation facts from verified MCP tools.
        
        Args:
            tools: List of tools to collect (default: position, SOG, COG)
        
        Returns:
            CollectionResult with facts, provenance, and diagnostics
        """
        if tools is None:
            tools = [SourceVerifiedTools.POSITION, SourceVerifiedTools.SOG, SourceVerifiedTools.COG]
        
        collection_start = self._now_utc()
        
        # Log startup
        self.logger.info(f"Collector STARTUP: {len(tools)} tools attempted for race_id={self.race_id}")
        
        result = CollectionResult(
            status=CollectionStatus.FAILED,
            race_id=self.race_id,
            collection_start_at=collection_start
        )
        
        position = None
        sog = None
        cog = None
        
        for tool in tools:
            result.tools_attempted.append(tool.public_id)
            
            try:
                if tool == SourceVerifiedTools.POSITION:
                    position = self._collect_position(result)
                    if position:
                        result.tools_succeeded.append(tool.public_id)
                elif tool == SourceVerifiedTools.SOG:
                    sog = self._collect_sog(result)
                    if sog:
                        result.tools_succeeded.append(tool.public_id)
                elif tool == SourceVerifiedTools.COG:
                    cog = self._collect_cog(result)
                    if cog:
                        result.tools_succeeded.append(tool.public_id)
            except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
                result.tools_failed.append(tool.public_id)
                error_msg = f"{tool.public_id}: {type(e).__name__}: {str(e)}"
                result.errors.append(error_msg)
                self.logger.error(f"Collector ERROR: {error_msg}")
            except Exception as e:
                result.tools_failed.append(tool.public_id)
                error_msg = f"{tool.public_id}: Unexpected error: {str(e)}"
                result.errors.append(error_msg)
                self.logger.error(f"Collector ERROR: {error_msg}")
        
        # Determine collection status
        if len(result.tools_succeeded) == len(result.tools_attempted):
            result.status = CollectionStatus.COMPLETE
        elif len(result.tools_succeeded) > 0:
            result.status = CollectionStatus.PARTIAL
        elif len(result.facts) > 0:
            result.status = CollectionStatus.INVALID
        else:
            result.status = CollectionStatus.FAILED
        
        result.collection_end_at = self._now_utc()
        
        # Log summary (DATA_OUT)
        self.logger.info(
            f"Collector DATA_OUT: status={result.status.value}, "
            f"facts={len(result.facts)}, "
            f"succeeded={len(result.tools_succeeded)}, "
            f"failed={len(result.tools_failed)}"
        )
        self.logger.info(f"Collector SHUTDOWN")
        
        return result

    def _collect_position(self, result: CollectionResult) -> Optional[NavigationFact]:
        """Collect latitude and longitude."""
        try:
            self.logger.info("Collector DATA_IN: calling racing.get_position")
            response = self.client.call_tool('racing.get_position')
            
            if response and response.get('result'):
                decoded = response['result']
                latitude = decoded.get('latitude')
                longitude = decoded.get('longitude')
                
                if latitude is not None and longitude is not None:
                    # Validate ranges
                    if not (-90 <= latitude <= 90):
                        result.warnings.append(f"racing.get_position: latitude out of range: {latitude}")
                        return None
                    if not (-180 <= longitude <= 180):
                        result.warnings.append(f"racing.get_position: longitude out of range: {longitude}")
                        return None
                    
                    provenance = Provenance(
                        tool_public_id="racing.get_position",
                        server_name="racing",
                        wire_tool_name="get_position",
                        source_id="mcp:racing:get_position",
                        source_timestamp=decoded.get('source_timestamp', 'UNKNOWN'),
                        observed_at=response.get('observed_at'),
                        freshness_limit_seconds=self.FRESHNESS_LIMITS.get("racing.get_position"),
                        validation_status=self._validate_freshness(
                            decoded.get('source_timestamp'),
                            self.FRESHNESS_LIMITS.get("racing.get_position")
                        )
                    )
                    
                    # Create two facts: latitude and longitude (exact values preserved internally, not logged)
                    result.facts.append(NavigationFact(
                        field_name="latitude",
                        value=latitude,
                        unit="decimal_degrees",
                        provenance=provenance
                    ))
                    result.facts.append(NavigationFact(
                        field_name="longitude",
                        value=longitude,
                        unit="decimal_degrees",
                        provenance=provenance
                    ))
                    
                    self.logger.info(f"Collector DATA_IN: racing.get_position success (2 facts: lat, lon)")
                    return result.facts[-1]
            
            result.warnings.append("racing.get_position: malformed or missing fields")
            return None
        except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
            raise

    def _collect_sog(self, result: CollectionResult) -> Optional[NavigationFact]:
        """Collect speed over ground."""
        try:
            self.logger.info("Collector DATA_IN: calling racing.get_sog")
            response = self.client.call_tool('racing.get_sog')
            
            if response and response.get('result'):
                decoded = response['result']
                sog_ms = decoded.get('speed_over_ground_ms')
                
                if sog_ms is not None:
                    # Validate: must be numeric and non-negative
                    if not isinstance(sog_ms, (int, float)) or sog_ms < 0:
                        result.warnings.append(f"racing.get_sog: invalid speed value: {sog_ms}")
                        return None
                    
                    provenance = Provenance(
                        tool_public_id="racing.get_sog",
                        server_name="racing",
                        wire_tool_name="get_sog",
                        source_id="mcp:racing:get_sog",
                        source_timestamp=decoded.get('source_timestamp', 'UNKNOWN'),
                        observed_at=response.get('observed_at'),
                        freshness_limit_seconds=self.FRESHNESS_LIMITS.get("racing.get_sog"),
                        validation_status=self._validate_freshness(
                            decoded.get('source_timestamp'),
                            self.FRESHNESS_LIMITS.get("racing.get_sog")
                        )
                    )
                    
                    fact = NavigationFact(
                        field_name="speed_over_ground",
                        value=sog_ms,
                        unit="m/s",
                        provenance=provenance
                    )
                    result.facts.append(fact)
                    
                    self.logger.info(f"Collector DATA_IN: racing.get_sog success (value={sog_ms}m/s, freshness={provenance.validation_status})")
                    return fact
                else:
                    result.warnings.append("racing.get_sog: speed_over_ground_ms is None")
                    return None
            
            result.warnings.append("racing.get_sog: malformed or missing fields")
            return None
        except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
            raise

    def _collect_cog(self, result: CollectionResult) -> Optional[NavigationFact]:
        """Collect course over ground."""
        try:
            self.logger.info("Collector DATA_IN: calling racing.get_cog")
            response = self.client.call_tool('racing.get_cog')
            
            if response and response.get('result'):
                decoded = response['result']
                cog_deg = decoded.get('course_over_ground_degrees')
                
                if cog_deg is not None:
                    # Validate: must be numeric and in valid circular range
                    if not isinstance(cog_deg, (int, float)) or cog_deg < 0 or cog_deg > 360:
                        result.warnings.append(f"racing.get_cog: invalid course value: {cog_deg}")
                        return None
                    
                    provenance = Provenance(
                        tool_public_id="racing.get_cog",
                        server_name="racing",
                        wire_tool_name="get_cog",
                        source_id="mcp:racing:get_cog",
                        source_timestamp=decoded.get('source_timestamp', 'UNKNOWN'),
                        observed_at=response.get('observed_at'),
                        freshness_limit_seconds=self.FRESHNESS_LIMITS.get("racing.get_cog"),
                        validation_status=self._validate_freshness(
                            decoded.get('source_timestamp'),
                            self.FRESHNESS_LIMITS.get("racing.get_cog")
                        )
                    )
                    
                    fact = NavigationFact(
                        field_name="course_over_ground",
                        value=cog_deg,
                        unit="degrees_true",
                        provenance=provenance
                    )
                    result.facts.append(fact)
                    
                    self.logger.info(f"Collector DATA_IN: racing.get_cog success (value={cog_deg}°, freshness={provenance.validation_status})")
                    return fact
                else:
                    result.warnings.append("racing.get_cog: course_over_ground_degrees is None")
                    return None
            
            result.warnings.append("racing.get_cog: malformed or missing fields")
            return None
        except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
            raise

    def _validate_freshness(self, source_timestamp: Optional[str], limit_seconds: Optional[int]) -> str:
        """
        Validate freshness with deterministic ISO 8601 parsing.
        
        Returns: "valid", "stale", or "missing"
        """
        if source_timestamp is None or source_timestamp == "UNKNOWN":
            return "missing"
        
        if limit_seconds is None:
            return "valid"
        
        try:
            # Parse ISO 8601 source timestamp (support both Z and explicit UTC offset)
            source_ts_str = source_timestamp.strip()
            
            # Handle Z suffix
            if source_ts_str.endswith('Z'):
                source_ts_str = source_ts_str[:-1] + '+00:00'
            
            source_dt = datetime.fromisoformat(source_ts_str)
            
            # Use injected reference time for tests, or current time
            if self.reference_time:
                ref_ts_str = self.reference_time.strip()
                if ref_ts_str.endswith('Z'):
                    ref_ts_str = ref_ts_str[:-1] + '+00:00'
                reference_dt = datetime.fromisoformat(ref_ts_str)
            else:
                reference_dt = datetime.now(timezone.utc)
            
            # Calculate age in seconds
            age_seconds = (reference_dt - source_dt).total_seconds()
            
            # Age must be non-negative
            if age_seconds < 0:
                return "missing"
            
            # Check freshness
            if age_seconds <= limit_seconds:
                return "valid"
            else:
                return "stale"
        except (ValueError, AttributeError):
            # Malformed timestamp
            return "missing"

    def _now_utc(self) -> str:
        """Generate current UTC timestamp or use reference time in tests."""
        if self.reference_time:
            return self.reference_time
        return datetime.now(timezone.utc).isoformat().replace('+00:00', '') + 'Z'

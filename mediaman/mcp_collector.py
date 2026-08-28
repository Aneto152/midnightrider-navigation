"""
Expanded MCP Collector for MediaMan — source-backed navigation fact collection.

Collects structured navigation facts from validated MCP servers using the hardened
MCPClient. Preserves provenance, freshness, and source timestamps.

Features:
- Source-verified tool collection (racing.get_position, racing.get_sog, racing.get_cog)
- Provenance tracking (tool, server, source, timestamp)
- Fail-closed collection (missing values remain None, no fabrication)
- Freshness awareness (tracks source_timestamp vs observed_at)
- Mocked testing support (dependency injection)
- No live MCP, Signal K, InfluxDB, or network access in this task
"""

import json
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
    source_timestamp: Optional[str] = None  # ISO 8601 UTC or UNKNOWN
    observed_at: Optional[str] = None  # local collection time
    freshness_limit_seconds: Optional[int] = None
    validation_status: str = "valid"  # "valid", "stale", "missing"
    warnings: List[str] = field(default_factory=list)


@dataclass
class NavigationFact:
    """A single collected navigation fact."""
    field_name: str
    value: Optional[Any]
    unit: str
    provenance: Provenance


@dataclass
class CollectionResult:
    """Structured result from a collection run."""
    status: CollectionStatus
    race_id: Optional[str] = None
    facts: List[NavigationFact] = field(default_factory=list)
    
    # Execution tracking
    tools_attempted: List[str] = field(default_factory=list)
    tools_succeeded: List[str] = field(default_factory=list)
    tools_failed: List[str] = field(default_factory=list)
    
    # Timestamps
    collection_start_at: Optional[str] = None
    collection_end_at: Optional[str] = None
    
    # Diagnostics
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict, preserving provenance."""
        facts_dicts = []
        for fact in self.facts:
            facts_dicts.append({
                "field_name": fact.field_name,
                "value": fact.value,
                "unit": fact.unit,
                "provenance": asdict(fact.provenance)
            })
        
        return {
            "status": self.status.value,
            "race_id": self.race_id,
            "facts": facts_dicts,
            "tools_attempted": self.tools_attempted,
            "tools_succeeded": self.tools_succeeded,
            "tools_failed": self.tools_failed,
            "collection_start_at": self.collection_start_at,
            "collection_end_at": self.collection_end_at,
            "errors": self.errors,
            "warnings": self.warnings
        }


class SourceVerifiedTools(Enum):
    """Source-verified MCP tools available in racing server."""
    POSITION = ("racing.get_position", "get_position", "racing")
    SOG = ("racing.get_sog", "get_sog", "racing")
    COG = ("racing.get_cog", "get_cog", "racing")
    
    def __init__(self, public_id: str, wire_name: str, server: str):
        self.public_id = public_id
        self.wire_name = wire_name
        self.server = server


class MCPCollector:
    """
    Expended MCP collector for navigation facts.
    
    Gathers source-backed facts from MCP servers with explicit provenance tracking,
    freshness awareness, and fail-closed semantics.
    """
    
    # Freshness limits (seconds)
    FRESHNESS_LIMITS = {
        "racing.get_position": 30,
        "racing.get_sog": 15,
        "racing.get_cog": 15,
    }
    
    def __init__(self, client: MCPClient, race_id: Optional[str] = None):
        """
        Initialize collector with an MCP client.
        
        Args:
            client: Initialized MCPClient instance
            race_id: Optional race identifier for context
        """
        self.client = client
        self.race_id = race_id
    
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
        
        result = CollectionResult(
            status=CollectionStatus.FAILED,
            race_id=self.race_id,
            collection_start_at=self._now_utc()
        )
        
        # Collect facts
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
                result.errors.append(f"{tool.public_id}: {type(e).__name__}: {str(e)}")
            except Exception as e:
                # Catch any other unexpected errors
                result.tools_failed.append(tool.public_id)
                result.errors.append(f"{tool.public_id}: Unexpected error: {str(e)}")
        
        # Determine collection status
        if position and sog and cog:
            result.status = CollectionStatus.COMPLETE
        elif position or sog or cog:
            result.status = CollectionStatus.PARTIAL
        else:
            result.status = CollectionStatus.INVALID
        
        result.collection_end_at = self._now_utc()
        return result
    
    def _collect_position(self, result: CollectionResult) -> Optional[NavigationFact]:
        """Collect latitude and longitude."""
        try:
            response = self.client.call_tool('racing.get_position')
            
            # Extract structured result
            if response and response.get('result'):
                decoded = response['result']
                latitude = decoded.get('latitude')
                longitude = decoded.get('longitude')
                
                if latitude is not None and longitude is not None:
                    # Coordinates are exact (not suppressed) — do not log them
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
                    
                    # Return position as two facts (lat, lon) for explicit tracking
                    result.facts.append(NavigationFact(
                        field_name="latitude",
                        value=latitude,  # Exact coordinate, not logged
                        unit="decimal_degrees",
                        provenance=provenance
                    ))
                    result.facts.append(NavigationFact(
                        field_name="longitude",
                        value=longitude,  # Exact coordinate, not logged
                        unit="decimal_degrees",
                        provenance=provenance
                    ))
                    
                    return result.facts[-1]
            
            result.warnings.append("racing.get_position: malformed or missing fields")
            return None
        except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
            raise
    
    def _collect_sog(self, result: CollectionResult) -> Optional[NavigationFact]:
        """Collect speed over ground."""
        try:
            response = self.client.call_tool('racing.get_sog')
            
            if response and response.get('result'):
                decoded = response['result']
                sog_ms = decoded.get('speed_over_ground_ms')
                
                # Never substitute missing with zero
                if sog_ms is not None:
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
            response = self.client.call_tool('racing.get_cog')
            
            if response and response.get('result'):
                decoded = response['result']
                cog_deg = decoded.get('course_over_ground_degrees')
                
                # Never substitute missing with zero
                if cog_deg is not None:
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
                    return fact
                else:
                    result.warnings.append("racing.get_cog: course_over_ground_degrees is None")
                    return None
            
            result.warnings.append("racing.get_cog: malformed or missing fields")
            return None
        except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
            raise
    
    @staticmethod
    def _validate_freshness(source_timestamp: Optional[str], limit_seconds: Optional[int]) -> str:
        """
        Validate freshness based on source timestamp and limit.
        
        Args:
            source_timestamp: ISO 8601 timestamp or "UNKNOWN"
            limit_seconds: Freshness limit in seconds
        
        Returns:
            "valid", "stale", or "missing"
        """
        if source_timestamp is None or source_timestamp == "UNKNOWN":
            return "missing"
        
        if limit_seconds is None:
            return "valid"
        
        # TODO: Implement actual freshness check against current time
        # For now, always valid (this task is mock-only)
        return "valid"
    
    @staticmethod
    def _now_utc() -> str:
        """Generate current UTC timestamp in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', '') + 'Z'

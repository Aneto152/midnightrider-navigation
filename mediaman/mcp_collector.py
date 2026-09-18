"""
Expanded MCP Collector for MediaMan — source-backed navigation fact collection (CORRECTED).

Collects structured navigation facts from validated MCP servers using the hardened
MCPClient. Implements actual freshness validation, logging instrumentation, and
LLM-safe serialization.

Features:
- Single collection engine, two entry points (historical and live) differing
  only by who chooses the upper bound and whether age matters
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
import math
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timedelta, timezone

from mediaman.mcp_client import MCPClient, MCPClientError, MCPProtocolError, MCPServerError, MCPTimeoutError
from mediaman.logging_utils import setup_service_logger


class CollectionStatus(Enum):
    """Outcome of a collector run."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    INVALID = "invalid"
    FAILED = "failed"


@dataclass
class Provenance:
    """Source tracking for every collected fact."""
    tool_public_id: str  # e.g., "racing.get_snapshot"
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


class MCPCollector:
    """
    Expanded MCP collector with verified tools, deterministic freshness,
    logging, and LLM-safe serialization.
    """

    # Default observation window for a live consultation, in seconds.
    #
    # A live snapshot is an interval ending now. This single number plays both
    # roles that used to be split across three per-tool limits: how far back
    # the engine may look to find the four facts, and the age beyond which
    # those facts are reported stale. Historical collection passes None and
    # has no freshness limit at all - that is one of the only two legitimate
    # differences between the two entry points.
    DEFAULT_CURRENT_WINDOW_SECONDS = 30

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
        # Configure structured logging (do not overwrite with generic getLogger)
        self.logger = setup_service_logger('mediaman-mcp-collector')

    def collect_historical(self, as_of_utc: str, window_seconds: int) -> CollectionResult:
        """
        Collect navigation facts at a past instant chosen by the caller.

        One of the two entry points of the single collection engine. It owns
        nothing but its own argument validation: the collection itself is
        _collect_snapshot, shared byte for byte with collect_current.

        Args:
            as_of_utc: ISO 8601 UTC timestamp for the upper bound
            window_seconds: how far back to look, in seconds (1-3600)

        Returns:
            CollectionResult with facts, provenance, and diagnostics

        D1: COMPLETE requires exactly four distinct valid fields (latitude, longitude, SOG, COG)
        """
        from mediaman.historical_request import HistoricalRequest

        # Validate request parameters
        try:
            HistoricalRequest(
                race_id=self.race_id or "historical",
                as_of_utc=as_of_utc,
                window_seconds=window_seconds
            )
        except ValueError as e:
            result = CollectionResult(
                status=CollectionStatus.FAILED,
                race_id=self.race_id,
                collection_start_at=self._now_utc(),
                collection_end_at=self._now_utc(),
                errors=[f"Invalid historical request: {str(e)}"]
            )
            self.logger.error(f"Collector ERROR: Invalid historical request: {str(e)}")
            return result

        return self._collect_snapshot(
            tool_public_id='racing.get_historical_snapshot',
            wire_tool_name='get_historical_snapshot',
            tool_args={'as_of_utc': as_of_utc, 'window_seconds': window_seconds},
            source_id='mcp:racing:historical',
            freshness_limit_seconds=None,
            mode='historical',
        )

    def collect_current(self, window_seconds: Optional[int] = None) -> CollectionResult:
        """
        Collect navigation facts as of now.

        The second entry point, and deliberately the thinner of the two: a
        live consultation is a historical one whose upper bound happens to be
        the present instant. It reaches the same engine, the same Flux query,
        the same self filter, the same bounded-skew check and the same unit
        contract. The only thing it adds is that age matters.

        The upper bound comes from self._now_utc(), which already honours the
        reference_time injected at construction. That is what lets the frozen
        historical dataset serve as a bench for the live path: build the
        collector with reference_time set to a past instant and this method
        replays the live code path over real recorded data, with no clock
        anywhere being deceived.

        Args:
            window_seconds: observation window ending now, in seconds.
                Defaults to DEFAULT_CURRENT_WINDOW_SECONDS.

        Returns:
            CollectionResult with facts, provenance, and diagnostics.
            Status is PARTIAL rather than COMPLETE when the facts are older
            than the window.
        """
        if window_seconds is None:
            window_seconds = self.DEFAULT_CURRENT_WINDOW_SECONDS

        if not isinstance(window_seconds, int) or isinstance(window_seconds, bool) \
                or window_seconds < 1 or window_seconds > 3600:
            result = CollectionResult(
                status=CollectionStatus.FAILED,
                race_id=self.race_id,
                collection_start_at=self._now_utc(),
                collection_end_at=self._now_utc(),
                errors=[f"Invalid current request: window_seconds must be an integer in 1..3600, got {window_seconds!r}"]
            )
            self.logger.error(
                f"Collector ERROR: Invalid current request: window_seconds={window_seconds!r}"
            )
            return result

        end_utc = self._now_utc()
        try:
            end_dt = self._parse_iso_utc(end_utc)
        except ValueError as e:
            result = CollectionResult(
                status=CollectionStatus.FAILED,
                race_id=self.race_id,
                collection_start_at=end_utc,
                collection_end_at=end_utc,
                errors=[f"Invalid current request: unparsable reference time: {str(e)}"]
            )
            self.logger.error(f"Collector ERROR: unparsable reference time")
            return result

        start_dt = end_dt - timedelta(seconds=window_seconds)
        start_utc = start_dt.isoformat().replace('+00:00', '') + 'Z'

        return self._collect_snapshot(
            tool_public_id='racing.get_snapshot',
            wire_tool_name='get_snapshot',
            tool_args={'start_utc': start_utc, 'end_utc': end_utc},
            source_id='mcp:racing:current',
            freshness_limit_seconds=window_seconds,
            mode='current',
        )

    @staticmethod
    def _parse_iso_utc(value: str) -> datetime:
        """Parse an ISO 8601 UTC timestamp with a literal Z suffix."""
        if not isinstance(value, str) or not value.endswith('Z'):
            raise ValueError(f"timestamp must end with Z: {value!r}")
        return datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)

    def _collect_snapshot(
        self,
        tool_public_id: str,
        wire_tool_name: str,
        tool_args: Dict[str, Any],
        source_id: str,
        freshness_limit_seconds: Optional[int],
        mode: str,
    ) -> CollectionResult:
        """
        THE SINGLE COLLECTION BODY.

        Historical and live collection both land here. Whatever is written
        below applies identically to both, by construction rather than by
        discipline: there is no second copy to keep in step.

        Before 2026-09-18 there were two bodies. The historical one filtered
        on self, bounded the skew across the four facts and converted the
        course from radians; the live one did none of the three, because it
        had been written first and never revisited. Collection quality
        depended on which entry point you happened to call. That is what H9
        removed.

        Args:
            tool_public_id: public MCP tool id, recorded in provenance
            wire_tool_name: bare tool name as declared by the server
            tool_args: arguments forwarded verbatim to the tool
            source_id: provenance source identifier
            freshness_limit_seconds: None for historical (age is irrelevant),
                a positive number for live (age beyond it means stale)
            mode: 'historical' or 'current', for logging only
        """
        collection_start = self._now_utc()

        self.logger.info(
            f"Collector STARTUP: mode={mode}, tool={tool_public_id}, "
            f"args={ {k: tool_args[k] for k in sorted(tool_args)} }"
        )

        result = CollectionResult(
            status=CollectionStatus.FAILED,
            race_id=self.race_id,
            collection_start_at=collection_start
        )

        try:
            self.logger.info(f"Collector DATA_IN: calling {tool_public_id}")

            response = self.client.call_tool(tool_public_id, dict(tool_args))

            if response and response.get('result'):
                decoded = response['result']

                # Extract historical facts from response
                if decoded.get('success'):
                    facts_data = decoded.get('facts', {})

                    # D1: Validate exact four-field set (latitude, longitude, speed_over_ground, course_over_ground)
                    required_fields = {'latitude', 'longitude', 'speed_over_ground_ms', 'course_over_ground_degrees'}
                    actual_fields = set(facts_data.keys())

                    # Check exact field set (no missing, no extra)
                    if actual_fields != required_fields:
                        missing = required_fields - actual_fields
                        extra = actual_fields - required_fields
                        error_parts = []
                        if missing:
                            error_parts.append(f"Missing: {missing}")
                        if extra:
                            error_parts.append(f"Extra: {extra}")
                        result.status = CollectionStatus.FAILED
                        result.tools_failed.append(tool_public_id)
                        result.errors.append(f"Snapshot field mismatch: {'; '.join(error_parts)}")
                        result.collection_end_at = self._now_utc()
                        self.logger.error(f"Collector ERROR: Field mismatch: {'; '.join(error_parts)}")
                        return result

                    # D1: Validate all four values exist, are numeric, and in valid ranges
                    lat = facts_data.get('latitude')
                    lon = facts_data.get('longitude')
                    sog = facts_data.get('speed_over_ground_ms')
                    cog = facts_data.get('course_over_ground_degrees')

                    validation_errors = []

                    # D1bis - defaut 63 : le serveur declare ses unites.
                    # Bloc absent = serveur plus ancien, on n exige rien pour
                    # ne pas casser une chaine deja deployee. Bloc present et
                    # faux = on refuse, plutot que de publier un cap dans la
                    # mauvaise unite comme le 2026-09-15.
                    units_data = decoded.get('units')
                    if isinstance(units_data, dict):
                        expected_units = {
                            'latitude': 'degrees',
                            'longitude': 'degrees',
                            'speed_over_ground_ms': 'm_per_s',
                            'course_over_ground_degrees': 'degrees_true',
                        }
                        for unit_key, unit_expected in expected_units.items():
                            unit_seen = units_data.get(unit_key)
                            if unit_seen != unit_expected:
                                validation_errors.append(
                                    f"unit mismatch for {unit_key}: expected "
                                    f"{unit_expected}, got {unit_seen}"
                                )
                    elif units_data is not None:
                        validation_errors.append(
                            "units must be an object, got "
                            f"{type(units_data).__name__}"
                        )

                    # Validate latitude
                    if lat is None:
                        validation_errors.append("latitude is None")
                    elif not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
                        validation_errors.append(f"latitude out of range: {lat}")

                    # Validate longitude
                    if lon is None:
                        validation_errors.append("longitude is None")
                    elif not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
                        validation_errors.append(f"longitude out of range: {lon}")

                    # D2: Validate SOG (mandatory, must be >= 0)
                    if sog is None:
                        validation_errors.append("speed_over_ground is None")
                    elif not isinstance(sog, (int, float)) or sog < 0:
                        validation_errors.append(f"speed_over_ground invalid: {sog}")

                    # D2: Validate COG (mandatory, must be 0-360, COG=0 is valid)
                    if cog is None:
                        validation_errors.append("course_over_ground is None")
                    elif not isinstance(cog, (int, float)) or not (0 <= cog <= 360):
                        validation_errors.append(f"course_over_ground out of range: {cog}")

                    if validation_errors:
                        result.status = CollectionStatus.FAILED
                        result.tools_failed.append(tool_public_id)
                        result.errors.extend(validation_errors)
                        result.collection_end_at = self._now_utc()
                        self.logger.error(f"Collector ERROR: Validation failures: {validation_errors}")
                        return result

                    # All four facts valid — create facts list
                    # The two legitimate differences between a historical
                    # collection and a live one are both expressed here, and
                    # nowhere else: which tool was addressed, and whether age
                    # is allowed to matter. Everything above this line is
                    # shared by construction.
                    provenance = Provenance(
                        tool_public_id=tool_public_id,
                        server_name="racing",
                        wire_tool_name=wire_tool_name,
                        source_id=source_id,
                        source_timestamp=decoded.get('source_timestamp', 'UNKNOWN'),
                        observed_at=response.get('observed_at'),
                        freshness_limit_seconds=freshness_limit_seconds,
                        validation_status=(
                            "valid" if freshness_limit_seconds is None
                            else self._validate_freshness(
                                decoded.get('source_timestamp'),
                                freshness_limit_seconds
                            )
                        )
                    )

                    result.facts.append(NavigationFact(
                        field_name="latitude",
                        value=lat,
                        unit="decimal_degrees",
                        provenance=provenance
                    ))
                    result.facts.append(NavigationFact(
                        field_name="longitude",
                        value=lon,
                        unit="decimal_degrees",
                        provenance=provenance
                    ))
                    result.facts.append(NavigationFact(
                        field_name="speed_over_ground",
                        value=sog,
                        unit="m/s",
                        provenance=provenance
                    ))
                    result.facts.append(NavigationFact(
                        field_name="course_over_ground",
                        value=cog,
                        unit="degrees_true",
                        provenance=provenance
                    ))

                    if provenance.validation_status == "valid":
                        result.status = CollectionStatus.COMPLETE
                    else:
                        # A live fact older than its window describes a boat
                        # that is no longer where it claims to be. PARTIAL,
                        # never COMPLETE: the publication layer decides what
                        # to do with it, but nothing downstream may present it
                        # as current. Historical collection never reaches this
                        # branch, its freshness limit being None.
                        result.status = CollectionStatus.PARTIAL
                        result.warnings.append(
                            f"{tool_public_id}: facts are {provenance.validation_status} "
                            f"relative to a {freshness_limit_seconds}s window"
                        )
                    result.tools_succeeded.append(tool_public_id)
                else:
                    result.status = CollectionStatus.FAILED
                    result.tools_failed.append(tool_public_id)
                    result.errors.append(f"Snapshot request failed: {decoded.get('error', 'unknown error')}")
            else:
                result.status = CollectionStatus.FAILED
                result.tools_failed.append(tool_public_id)
                result.errors.append("Snapshot returned empty or malformed response")

        except (MCPProtocolError, MCPServerError, MCPClientError, MCPTimeoutError) as e:
            result.status = CollectionStatus.FAILED
            result.tools_failed.append(tool_public_id)
            error_msg = f"{tool_public_id}: {type(e).__name__}: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(f"Collector ERROR: {error_msg}")
        except Exception as e:
            result.status = CollectionStatus.FAILED
            result.tools_failed.append(tool_public_id)
            error_msg = f"{tool_public_id}: Unexpected error: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(f"Collector ERROR: {error_msg}")

        result.collection_end_at = self._now_utc()
        result.tools_attempted.append(tool_public_id)

        self.logger.info(
            f"Collector DATA_OUT: status={result.status.value}, "
            f"facts={len(result.facts)}, "
            f"succeeded={len(result.tools_succeeded)}, "
            f"failed={len(result.tools_failed)}"
        )
        self.logger.info(f"Collector SHUTDOWN")

        return result

    # ------------------------------------------------------------------
    # Ce qui se trouvait ici, et pourquoi il n y est plus.
    #
    # collect(), _collect_position(), _collect_sog() et _collect_cog() -
    # environ 235 lignes - formaient un second chemin de collecte adresse a
    # trois outils, racing.get_position, racing.get_sog et racing.get_cog,
    # que mcp/servers/racing.js n a jamais declares. Ce chemin etait donc
    # mort : appele pour de vrai, il recevait trois fois Unknown tool.
    #
    # Il n a pas ete complete, il a ete supprime, et ce n est pas la meme
    # decision. Le completer aurait rouvert deux defauts deja fermes sur le
    # chemin destine a la course : trois appels separes rendent impossible le
    # controle de derive entre les quatre faits, et ce code ne portait ni le
    # filtre self du defaut 58 ni la conversion radians -> degres du
    # defaut 63.
    #
    # Sa fonction est reprise par collect_current(), qui atteint le meme
    # moteur que collect_historical(). Defaut 65, ferme le 2026-09-18.
    #
    # tests/mcp/test_h9_chemin_unique.py interdit la reapparition des trois
    # noms d outils dans ce fichier.
    # ------------------------------------------------------------------

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

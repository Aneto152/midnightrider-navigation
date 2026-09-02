"""
Content provider for race reporting articles.

Enforces French output, length limits, and credential filtering.
"""

import os
import re
from abc import ABC, abstractmethod
from datetime import datetime

# Sentinel value to distinguish between no argument and explicit None
class _Sentinel:
    pass

_NOT_PROVIDED = _Sentinel()


class ContentProvider(ABC):
    """Base class for content providers."""

    @abstractmethod
    def get_content(self, race_id: str, cycle_timestamp: str) -> str:
        """Generate article content. Must be in French, under max length."""
        pass


class TestContentProvider(ContentProvider):
    """
    Deterministic test provider for dry-run and testing.

    Message length validation is PENDING operational decisions.
    No hardcoded length limits are enforced by this provider.
    """

    def __init__(self):
        self.call_count = 0

    def get_content(self, race_id: str, cycle_timestamp: str) -> str:
        """Return a deterministic test article in French."""
        self.call_count += 1

        # Ensure French characters are properly formatted
        article = (
            f"🏁 *Midnight Rider* — Cycle {self.call_count}\n\n"
            f"**Rôle**: Navire de course J/30 en détention à Stamford CT\n"
            f"**Condition**: Navire opérationnel, tous les systèmes vérifiés\n"
            f"**Cycle**: {cycle_timestamp} (test)\n\n"
            f"Article de test pour démonstration du système MediaMan.\n"
            f"Aucun message réel n'a été envoyé à Telegram."
        )

        return article

    def validate(self, content: str) -> tuple[bool, str]:
        """
        Validate content. Return (is_valid, error_message).

        Length validation is PENDING — no hardcoded limit enforced.
        Future content must be string, valid UTF-8, and free of credentials.
        """
        if not content:
            return False, "Content is empty"

        # Check for credentials (basic patterns)
        credential_patterns = [
            r'token',
            r'password',
            r'secret',
            r'api[_-]?key',
            r'auth',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Content contains credential pattern: {pattern}"

        # Check for French (at least some accented characters or common French words)
        french_indicators = ['é', 'è', 'ê', 'ç', 'le ', 'la ', 'et ', 'un ', 'une ']
        has_french = any(ind in content.lower() for ind in french_indicators)

        if not has_french:
            return False, "Content does not appear to be in French"

        return True, ""


class LocalLLMProvider(ContentProvider):
    """
    LLM-based content provider using local OpenClaw agent.

    Flow:
    1. Collect RaceFacts from Regatta API
    2. Build French-language prompt
    3. Call OpenClaw agent CLI (outbound only)
    4. Validate output (no hallucinations, credentials, etc.)
    5. Return article or fail closed

    Pre-production implementation:
    - Fully testable with mocked subprocess
    - No real Telegram calls here
    - No production activation

    Message length validation is PENDING operational decisions.
    No hardcoded length limits are enforced by this provider.
    """

    def __init__(self):
        """Initialize LLM provider with lazy adapter loading."""
        from .openclaw_adapter import OpenClawAdapter
        from .race_facts import RaceFacts
        from .llm_validator import OutputValidator

        self.adapter = OpenClawAdapter()
        self.RaceFacts = RaceFacts  # For type hints
        self.OutputValidator = OutputValidator

    def get_content(self, race_id: str, cycle_timestamp: str) -> str:
        """
        Generate article from RaceFacts using LLM.

        Raises NotImplementedError in pre-production (awaits real RaceFacts fetch).
        """
        raise NotImplementedError(
            "LocalLLMProvider requires real RaceFacts collection from Regatta API. "
            "Currently in pre-production validation phase."
        )

    def validate(self, content: str) -> tuple[bool, str]:
        """Validate article output.

        Note: Message length validation is PENDING operational decisions.
        No hardcoded length limits are enforced by this provider.
        """
        if not content:
            return False, "Content is empty"

        # Check for credentials (basic patterns)
        credential_patterns = [
            r'token',
            r'password',
            r'secret',
            r'api[_-]?key',
            r'auth',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Content contains credential pattern: {pattern}"

        # Check for French: require accented characters (much more specific to French)
        french_accents = ['é', 'è', 'ê', 'ç', 'à', 'ù', 'û', 'ô']
        has_accented_chars = any(char in content for char in french_accents)

        if not has_accented_chars:
            return False, "Content does not appear to be in French (no accented characters found)"

        return True, ""


class OpenClawGatewayProvider(ContentProvider):
    """
    Future provider that fetches content from local OpenClaw Gateway.

    This is a placeholder for future integration.
    Requires OpenClaw Gateway to be documented and testable without credentials.
    """

    def __init__(self):
        # Placeholder: no actual Gateway call yet
        pass

    def get_content(self, race_id: str, cycle_timestamp: str) -> str:
        """
        Fetch article from local OpenClaw Gateway.

        Future implementation will call:
        http://localhost:18789/api/mediaman/article?race_id=...&cycle_ts=...

        This must be outbound-only and never forward Telegram messages back.
        """
        raise NotImplementedError(
            "OpenClaw Gateway provider not yet implemented. "
            "Awaiting Gateway API documentation."
        )

    def validate(self, content: str) -> tuple[bool, str]:
        """Validate article output.

        Note: Message length validation is PENDING operational decisions.
        """
        if not content:
            return False, "Content is empty"

        # Check for credentials (basic patterns)
        credential_patterns = [
            r'token',
            r'password',
            r'secret',
            r'api[_-]?key',
            r'auth',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Content contains credential pattern: {pattern}"

        # Check for French: require accented characters (much more specific to French)
        french_accents = ['é', 'è', 'ê', 'ç', 'à', 'ù', 'û', 'ô']
        has_accented_chars = any(char in content for char in french_accents)

        if not has_accented_chars:
            return False, "Content does not appear to be in French (no accented characters found)"

        return True, ""


class HistoricalMCPProvider(ContentProvider):
    """
    Historical content provider using MCP collector and InfluxDB historical data.

    Receives injected MCPCollector and HistoricalRequest, collects facts at as_of timestamp,
    generates French article summarizing historical navigation state.

    No live data fallback. No silent TestContentProvider fallback.
    Fail-closed on missing mandatory facts.

    Requires explicit MCPCollector injection. Raises ValueError if collector is absent.

    D1: COMPLETE requires exactly four distinct valid fields.
    D2: SOG and COG are mandatory; no '?' placeholders.
    R5: race_id is metadata-only; propagated explicitly through call chain.
    """

    def __init__(self, mcp_collector=_NOT_PROVIDED):
        """
        Initialize historical provider with optional injected MCP collector.

        Args:
            mcp_collector: MCPCollector instance (optional, required only for get_content_for_historical)

        Behavior:
            - HistoricalMCPProvider() → validation-only mode (no collector needed)
            - HistoricalMCPProvider(mcp_collector=None) → raises ValueError (explicit None not allowed)
            - HistoricalMCPProvider(mcp_collector=<obj>) → collection mode (collector provided)

        Note:
            - validate() can be called without collector (validation-only)
            - get_content_for_historical() requires collector; raises ValueError if absent
        """
        # Distinguish between no argument and explicit None
        if mcp_collector is None:
            raise ValueError(
                "HistoricalMCPProvider: mcp_collector cannot be explicitly None. "
                "Either omit the argument (validation-only mode) or provide a collector instance."
            )
        elif mcp_collector is _NOT_PROVIDED:
            # No argument provided - validation-only mode
            self.mcp_collector = None
        else:
            # Valid collector provided
            self.mcp_collector = mcp_collector

        self.call_count = 0
        self.snapshot_count = 0
        self.last_snapshot_params = None

    def get_content(self, race_id: str, cycle_timestamp: str) -> str:
        """
        Generate article from historical facts at cycle_timestamp.

        Note: This provider requires explicit historical activation via
        MEDIAMAN_CONTENT_PROVIDER=historical_mcp and historical request parameters.
        Not called directly in normal flow.
        """
        raise NotImplementedError(
            "HistoricalMCPProvider requires explicit historical request context. "
            "Use get_content_for_historical() instead."
        )

    def get_content_for_historical(self, as_of_utc: str, window_seconds: int, race_id: str = None) -> str:
        """
        Generate article from historical facts collected at as_of timestamp.

        Args:
            as_of_utc: ISO 8601 UTC timestamp for historical snapshot
            window_seconds: Query window in seconds
            race_id: Optional race identifier (passed explicitly, not stored as state)

        Returns:
            French article summarizing historical navigation state

        Raises:
            ValueError: if MCP collector is not injected or collection fails
            ValueError: if mandatory facts are missing
            ValueError: if any required fact is invalid (D1, D2)
        """
        # Tracker call count (increments on every call)
        self.call_count += 1

        if self.mcp_collector is None:
            raise ValueError("MCP collector not injected (required for get_content_for_historical)")

        from mediaman.historical_request import HistoricalRequest

        # Validate request
        try:
            request = HistoricalRequest(
                race_id=race_id or "historical",
                as_of_utc=as_of_utc,
                window_seconds=window_seconds
            )
        except ValueError as e:
            raise ValueError(f"Invalid historical request: {e}") from e

        # Track unique snapshots (only increment for new parameter combinations)
        current_params = (as_of_utc, window_seconds)
        if current_params != self.last_snapshot_params:
            self.snapshot_count += 1
            self.last_snapshot_params = current_params

        # Collect historical facts
        collection_result = self.mcp_collector.collect_historical(
            as_of_utc=as_of_utc,
            window_seconds=window_seconds
        )

        # Verify collection succeeded
        from mediaman.mcp_collector import CollectionStatus

        if collection_result.status == CollectionStatus.FAILED:
            raise ValueError(
                f"Historical collection failed: {collection_result.errors}"
            )

        # D1: COMPLETE status required; PARTIAL or INVALID blocks publication
        if collection_result.status != CollectionStatus.COMPLETE:
            raise ValueError(
                f"Historical collection incomplete: {collection_result.status.value}"
            )

        # Extract facts
        facts_dict = {}
        for fact in collection_result.facts:
            facts_dict[fact.field_name] = fact.value

        # D1: Verify exactly four mandatory facts present
        required_fields = ["latitude", "longitude", "speed_over_ground", "course_over_ground"]
        missing = [f for f in required_fields if f not in facts_dict]
        if missing:
            raise ValueError(f"Historical snapshot missing mandatory facts: {missing}")

        # D2: Verify no '?' placeholders; all facts must have valid values
        # (validation already done in mcp_collector, but double-check here)
        for field in required_fields:
            if facts_dict[field] is None or facts_dict[field] == "?":
                raise ValueError(f"Historical snapshot has invalid value for {field}")

        # Generate French article from validated facts
        lat = facts_dict["latitude"]
        lon = facts_dict["longitude"]
        sog = facts_dict["speed_over_ground"]
        cog = facts_dict["course_over_ground"]

        # Construct article from validated facts only
        # No unsupported claims such as "all systems verified"
        article = (
            f"🏁 *Midnight Rider* — Historique {self.snapshot_count}\n\n"
            f"**Nom**: Navire de course J/30\n"
            f"**Moment**: {as_of_utc} (historique, fenêtre {window_seconds}s)\n\n"
            f"**Position**: {lat}°, {lon}°\n"
            f"**Cap**: {cog}° (cap au vrai)\n"
            f"**Vitesse**: {sog} m/s (vitesse par rapport au sol)\n\n"
            f"Article généré à partir de données historiques InfluxDB via le système MCP.\n"
            f"Aucun message réel n'a été envoyé à Telegram."
        )

        return article

    def validate(self, content: str) -> tuple[bool, str]:
        """
        Validate article output.

        Note: Message length validation is PENDING operational decisions.
        """
        if not content:
            return False, "Content is empty"

        # Check for credentials (basic patterns)
        credential_patterns = [
            r'token',
            r'password',
            r'secret',
            r'api[_-]?key',
            r'auth',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Content contains credential pattern: {pattern}"

        # Check for French: require accented characters (much more specific to French)
        # Accented characters are far more reliable than word fragments like 'le ' which appear in English
        french_accents = ['é', 'è', 'ê', 'ç', 'à', 'ù', 'û', 'ô']
        has_accented_chars = any(char in content for char in french_accents)

        if not has_accented_chars:
            return False, "Content does not appear to be in French (no accented characters found)"

        return True, ""


def get_content_provider(
    provider_name: str | None = None,
    *,
    mcp_collector=None
) -> ContentProvider:
    """
    Factory for content providers with explicit dependency injection.

    Args:
        provider_name: Provider identifier (default: reads MEDIAMAN_CONTENT_PROVIDER env var)
        mcp_collector: Optional MCPCollector instance (required for historical_mcp)

    Supported values:
    - test: TestContentProvider (deterministic test articles, no collector required)
    - gateway: OpenClawGatewayProvider (future, no collector required)
    - historical_mcp: HistoricalMCPProvider (requires explicit MCPCollector, raises ValueError if absent)

    Returns:
        ContentProvider instance

    Raises:
        ValueError: if provider_name is unknown or if historical_mcp is requested without collector

    R5: race_id is metadata-only; factory does not handle race_id.
    """
    # Use provided name or read from environment
    if provider_name is None:
        provider_name = os.getenv("MEDIAMAN_CONTENT_PROVIDER", "test").lower().strip()
    else:
        provider_name = provider_name.lower().strip()

    if provider_name == "test":
        return TestContentProvider()
    elif provider_name == "gateway":
        return OpenClawGatewayProvider()
    elif provider_name == "historical_mcp":
        # Explicit injection required: fail-closed if collector is absent
        if mcp_collector is None:
            raise ValueError(
                "historical_mcp provider requires explicit mcp_collector injection (not None). "
                "Pass mcp_collector=<MCPCollector instance> to get_content_provider()."
            )
        return HistoricalMCPProvider(mcp_collector)
    else:
        raise ValueError(f"Unknown content provider: {provider_name}")

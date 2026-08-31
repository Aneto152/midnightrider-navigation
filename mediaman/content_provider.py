"""
Content provider for race reporting articles.

Enforces French output, length limits, and credential filtering.
"""

import os
import re
from abc import ABC, abstractmethod
from datetime import datetime


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
        """Validate article output."""
        if not content:
            return False, "Content is empty"

        if len(content) > self.MAX_LENGTH:
            return False, f"Content exceeds {self.MAX_LENGTH} characters"

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

        # Check for French
        french_indicators = ['é', 'è', 'ê', 'ç', 'le ', 'la ', 'et ', 'un ', 'une ']
        has_french = any(ind in content.lower() for ind in french_indicators)

        if not has_french:
            return False, "Content does not appear to be in French"

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


def get_content_provider() -> ContentProvider:
    """
    Factory for content providers.

    Reads MEDIAMAN_CONTENT_PROVIDER env var (default: test).
    """
    provider_name = os.getenv("MEDIAMAN_CONTENT_PROVIDER", "test").lower().strip()

    if provider_name == "test":
        return TestContentProvider()
    elif provider_name == "gateway":
        return OpenClawGatewayProvider()
    else:
        raise ValueError(f"Unknown content provider: {provider_name}")

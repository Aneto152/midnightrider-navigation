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
    """Deterministic test provider for dry-run and testing."""
    
    MAX_LENGTH = 2000  # Telegram message limit is 4096, use conservative limit
    
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
        """Validate content. Return (is_valid, error_message)."""
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
        
        # Check for French (at least some accented characters or common French words)
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

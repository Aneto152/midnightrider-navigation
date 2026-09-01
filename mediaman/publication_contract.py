"""
Publication contract: immutable data transfer object and validation.

Defines PublicationDTO (immutable content) and PublicationValidator (offline validation).
No state, no bridge, no network, no logging, no database access.
"""

from dataclasses import dataclass
from datetime import datetime
import re


@dataclass(frozen=True)
class PublicationDTO:
    """Immutable publication data transfer object."""
    publication_id: str
    race_id: str
    cycle_id: str
    content: str
    created_at: str


class PublicationValidator:
    """Offline publication contract validation."""

    # Credential patterns to reject
    CREDENTIAL_PATTERNS = [
        r'token\s*=',
        r'password\s*=',
        r'secret\s*=',
        r'api[_-]?key\s*=',
        r'apikey\s*=',
        r'authorization\s*=',
        r'bearer\s+[a-z0-9]{20,}',
        r'basic\s+[a-z0-9]{20,}',
    ]

    # Credential-bearing URI schemes
    URI_CREDENTIAL_PATTERNS = [
        r'postgres://[^@]*:[^@]*@',
        r'postgresql://[^@]*:[^@]*@',
        r'mysql://[^@]*:[^@]*@',
        r'redis://[^@]*:[^@]*@',
        r'mongodb://[^@]*:[^@]*@',
        r'amqp://[^@]*:[^@]*@',
        r'amqps://[^@]*:[^@]*@',
        r'https://[^@]*:[^@]*@',
        r'http://[^@]*:[^@]*@',
    ]

    @staticmethod
    def validate(publication: PublicationDTO) -> tuple[bool, str]:
        """
        Validate a PublicationDTO.

        Returns:
            (True, ""): Valid
            (False, error_code): Invalid
        """
        # 1. Input must be a PublicationDTO
        if not isinstance(publication, PublicationDTO):
            return (False, "invalid_type")

        # 2. All five fields must be strings (non-empty)
        if not isinstance(publication.publication_id, str) or not publication.publication_id:
            return (False, "missing_field")
        if not isinstance(publication.race_id, str) or not publication.race_id:
            return (False, "missing_field")
        if not isinstance(publication.cycle_id, str) or not publication.cycle_id:
            return (False, "missing_field")
        if not isinstance(publication.content, str) or not publication.content:
            return (False, "missing_field")
        if not isinstance(publication.created_at, str) or not publication.created_at:
            return (False, "missing_field")

        # 3. publication_id must match exactly: ^[0-9a-f]{64}$
        if not re.match(r'^[0-9a-f]{64}$', publication.publication_id):
            return (False, "invalid_publication_id")

        # 4. created_at must be ISO 8601 UTC with Z terminator
        try:
            # Must end with Z
            if not publication.created_at.endswith('Z'):
                return (False, "invalid_timestamp")
            # Parse as UTC ISO 8601
            datetime.fromisoformat(publication.created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return (False, "invalid_timestamp")

        # 5. content must reject credentials and unsafe control characters
        content_lower = publication.content.lower()

        # Check credential patterns
        for pattern in PublicationValidator.CREDENTIAL_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return (False, "unsafe_content")

        # Check credential-bearing URI patterns
        for pattern in PublicationValidator.URI_CREDENTIAL_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return (False, "unsafe_content")

        # Check for NUL character
        if '\x00' in publication.content:
            return (False, "unsafe_content")

        # Check for unsafe control characters (excluding newline, tab, carriage return)
        unsafe_controls = set(chr(i) for i in range(32) if i not in (9, 10, 13))
        if any(char in publication.content for char in unsafe_controls):
            return (False, "unsafe_content")

        # Valid
        return (True, "")

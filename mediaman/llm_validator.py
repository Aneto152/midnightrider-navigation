"""
Strict output validation for LLM-generated race articles.

Prevents hallucinations, credential leaks, and unsupported claims.
Fails closed if validation fails.
"""

import re
from typing import Tuple, Set, Optional
from .race_facts import RaceFacts


class OutputValidator:
    """Validates LLM-generated article against RaceFacts."""

    MAX_LENGTH = 700  # characters
    MIN_SENTENCES = 3
    MAX_SENTENCES = 5

    # Credential and command patterns
    CREDENTIAL_PATTERNS = [
        r'(?i)(token|password|secret|api[_-]?key|auth[_-]?token)',
        r'(?i)(bearer|basic)\s+[a-z0-9]{20,}',
    ]

    COMMAND_PATTERNS = [
        r'systemctl\s+(start|stop|enable|disable)',
        r'sudo\s+',
        r'docker\s+(run|compose)',
        r'curl\s+',
    ]

    MARKDOWN_PATTERNS = [
        r'^#+\s+',  # Heading
        r'^\s*[-*]\s+',  # Bullet list
        r'\[.+?\]\(.+?\)',  # Link
        r'`[^`]+`',  # Code block
    ]

    INJECTION_PATTERNS = [
        r'<script',
        r'javascript:',
        r'onerror\s*=',
        r'onload\s*=',
    ]

    # Field-aware numeric context patterns
    SPEED_UNITS = r'(?:nœud|nœuds|knot|knots?|kt|kts|vitesse)'
    COURSE_LABELS = r'(?:cap|route|course|heading|COG|direction|bearing|direction de route)'
    WIND_CONTEXT = r'(?:vent|wind|direction du vent|force du vent|vitesse du vent)'
    HEEL_CONTEXT = r'(?:gîte|inclinaison|heel|angle|inclination)'
    ELAPSED_TIME_CONTEXT = r'(?:durée|temps de course|elapsed|hours? since|minutes? since|time since start|heures de course)'
    RANKING_CONTEXT = r'(?:classement|position dans la flotte|rang|place|leader|leading|first place|second place|win|winning)'

    def __init__(self, facts: RaceFacts):
        """Initialize validator with reference facts."""
        self.facts = facts
        self.valid_speeds: Set[float] = set()
        self.valid_courses: Set[float] = set()
        self._extract_valid_values()

    def _extract_valid_values(self):
        """Extract known valid values from facts for comparison."""
        if self.facts.navigation and self.facts.navigation.is_valid():
            sog = self.facts.navigation.sog_knots
            cog = self.facts.navigation.cog_degrees
            # Allow ±1.5 knots and ±40 degrees variation
            if sog:
                for v in [sog - 1.5, sog - 1, sog - 0.5, sog, sog + 0.5, sog + 1, sog + 1.5]:
                    if v >= 0:
                        self.valid_speeds.add(round(v, 1))
            if cog:
                for v in range(int(max(0, cog - 40)), int(min(361, cog + 41))):
                    self.valid_courses.add(v)

    def validate(self, output: str) -> Tuple[bool, str]:
        """
        Validate output. Return (is_valid, error_message).

        Validation order:
        1. Empty/UTF-8
        2. Length
        3. Sentence count
        4. Markdown
        5. Credentials
        6. Commands
        7. Injection
        8. Coordinates
        9. Unsupported claims
        10. Field-aware numeric claims
        """

        # Empty check
        if not output or not output.strip():
            return False, "Output is empty"

        # UTF-8 check
        try:
            output.encode('utf-8')
        except UnicodeDecodeError:
            return False, "Output contains invalid UTF-8"

        # Length check
        if len(output) > self.MAX_LENGTH:
            return False, f"Output exceeds {self.MAX_LENGTH} characters (got {len(output)})"

        # Sentence count
        sentences = self._count_sentences(output)
        if sentences < self.MIN_SENTENCES or sentences > self.MAX_SENTENCES:
            return False, f"Output must have {self.MIN_SENTENCES}-{self.MAX_SENTENCES} sentences (got {sentences})"

        # Markdown check
        if self._contains_markdown(output):
            return False, "Output contains Markdown formatting"

        # Credential check
        if self._contains_credentials(output):
            return False, "Output contains credential patterns"

        # Command check
        if self._contains_commands(output):
            return False, "Output contains system commands"

        # Injection check
        if self._contains_injection(output):
            return False, "Output contains injection patterns"

        # Exact coordinates check
        if self._has_exact_coordinates(output):
            return False, "Exact coordinates not permitted (use summarized descriptions instead)"

        # Unsupported explicit claims
        valid, reason = self._validate_unsupported_claims(output)
        if not valid:
            return False, reason

        # Field-aware numeric claims
        valid, reason = self._validate_numeric_claims(output)
        if not valid:
            return False, reason

        return True, ""

    def _count_sentences(self, text: str) -> int:
        """Count sentences."""
        sentences = re.split(r'[.!?]+\s+|\n|$', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)

    def _contains_markdown(self, text: str) -> bool:
        """Check for Markdown patterns."""
        for pattern in self.MARKDOWN_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False

    def _contains_credentials(self, text: str) -> bool:
        """Check for credential patterns."""
        for pattern in self.CREDENTIAL_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    def _contains_commands(self, text: str) -> bool:
        """Check for system command patterns."""
        for pattern in self.COMMAND_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _contains_injection(self, text: str) -> bool:
        """Check for injection attack patterns."""
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_exact_coordinates(self, text: str) -> bool:
        """Check for exact coordinates."""
        coord_pattern = r'(\d+\.\d{2,})[°º]?\s*[NS]?\s*[,\s]\s*(\d+\.\d{2,})[°º]?\s*[EW]?'
        return bool(re.search(coord_pattern, text))

    def _validate_unsupported_claims(self, text: str) -> Tuple[bool, str]:
        """Reject explicit unsupported claims."""

        # Wind claims (not supported in this FactRegistry version)
        if re.search(self.WIND_CONTEXT, text, re.IGNORECASE):
            if self.facts.wind is None or not self.facts.wind.is_valid():
                return False, "Wind claims not supported (wind facts unavailable)"

        # Heel claims (not in RaceFacts)
        if re.search(self.HEEL_CONTEXT, text, re.IGNORECASE):
            return False, "Heel/attitude claims not supported (not available in facts)"

        # Elapsed time claims (not in RaceFacts)
        if re.search(self.ELAPSED_TIME_CONTEXT, text, re.IGNORECASE):
            return False, "Elapsed time claims not supported (not available in facts)"

        # Ranking claims (not in RaceFacts)
        if re.search(self.RANKING_CONTEXT, text, re.IGNORECASE):
            return False, "Ranking claims not supported (not available in facts)"

        return True, ""

    def _validate_numeric_claims(self, text: str) -> Tuple[bool, str]:
        """Validate numeric claims using field-aware context."""

        # Speed claims: must have speed unit
        speed_pattern = rf'(\d+(?:[.,]\d+)?)\s*({self.SPEED_UNITS})'
        for match in re.finditer(speed_pattern, text, re.IGNORECASE):
            speed_str = match.group(1).replace(',', '.')
            try:
                speed_val = float(speed_str)
            except ValueError:
                continue

            if self.valid_speeds and speed_val not in self.valid_speeds:
                is_close = any(abs(speed_val - v) <= 1.5 for v in self.valid_speeds)
                if not is_close:
                    closest = min(self.valid_speeds, key=lambda v: abs(v - speed_val))
                    return False, f"Speed claim {speed_val} not supported by facts (closest: {closest})"

        # Course claims: must have course label
        course_pattern = rf'({self.COURSE_LABELS})\s+(\d+)(?:\s*(?:degrés?|°))?'
        for match in re.finditer(course_pattern, text, re.IGNORECASE):
            course_str = match.group(2)
            try:
                course_val = float(course_str)
            except ValueError:
                continue

            if self.valid_courses and course_val not in self.valid_courses:
                is_close = any(abs(course_val - v) <= 40 for v in self.valid_courses)
                if not is_close:
                    closest = min(self.valid_courses, key=lambda v: abs(v - course_val))
                    return False, f"Course claim {course_val}° not supported by facts (closest: {closest}°)"

        return True, ""

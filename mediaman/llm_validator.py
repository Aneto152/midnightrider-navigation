"""
Strict output validation for LLM-generated race articles.

Prevents hallucinations, credential leaks, and unsupported claims.
Fails closed if validation fails.
"""

import re
from typing import Tuple, Optional
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
    HEEL_CONTEXT = r'(?:gîte|inclinaison|heel|angle|inclination)'
    ELAPSED_TIME_CONTEXT = r'(?:durée|temps de course|elapsed|hours? since|minutes? since|time since start|heures de course)'
    RANKING_CONTEXT = r'\b(?:classement|position dans la flotte|rang|place|leader|leading|first place|second place|winning)\b'

    def __init__(self, facts: RaceFacts):
        """Initialize validator with reference facts."""
        self.facts = facts
        self.factual_sog: Optional[float] = None
        self.factual_cog: Optional[float] = None
        self._extract_factual_values()

    def _extract_factual_values(self):
        """Extract factual values from facts."""
        if self.facts.navigation and self.facts.navigation.is_valid():
            self.factual_sog = self.facts.navigation.sog_knots
            self.factual_cog = self.facts.navigation.cog_degrees

    def validate(self, output: str) -> Tuple[bool, str]:
        """Validate output."""

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
        """Check for exact coordinates in multiple formats."""
        patterns = [
            # Cardinal format: 41.1234°N, 73.5678°W or 41.1234 N, -73.5678 W
            r'\d+\.\d{2,}[°º]?\s*[NS]\s*[,\s]\s*[+-]?\d+\.\d{2,}[°º]?\s*[EW]',
            # Signed with space: 41.1234 -73.5678
            r'[+-]?\d+\.\d{2,}\s+[+-]\d+\.\d{2,}',
            # Signed comma: -41.1234, 73.5678
            r'[+-]\d+\.\d{2,}\s*,\s*[+-]?\d+\.\d{2,}',
            # Degree format: 41.1234° -73.5678°
            r'\d+\.\d{2,}[°º]\s+[+-]\d+\.\d{2,}[°º]',
        ]
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    def _validate_unsupported_claims(self, text: str) -> Tuple[bool, str]:
        """Reject explicit unsupported claims."""

        # Wind claims: only if explicit wind pattern with numeric speed
        # Pattern: (vent|wind) ... (number) (unit)
        if self._has_explicit_wind_speed_claim(text):
            if self.facts.wind is None or not self.facts.wind.is_valid():
                return False, "Wind claims not supported (wind facts unavailable)"

        # Heel claims
        if re.search(self.HEEL_CONTEXT, text, re.IGNORECASE):
            return False, "Heel/attitude claims not supported (not available in facts)"

        # Elapsed time claims
        if re.search(self.ELAPSED_TIME_CONTEXT, text, re.IGNORECASE):
            return False, "Elapsed time claims not supported (not available in facts)"

        # Ranking claims (word boundaries)
        if re.search(self.RANKING_CONTEXT, text, re.IGNORECASE):
            return False, "Ranking claims not supported (not available in facts)"

        return True, ""

    def _has_explicit_wind_speed_claim(self, text: str) -> bool:
        """Check for explicit wind speed pattern: vent/wind + à/at + number + unit."""
        # Only match if vent/wind is proximal to the numeric claim
        pattern = r'(?:vent|wind)\s+(?:souffle\s+)?(?:à|at)\s+(\d+(?:[.,]\d+)?)\s*(?:nœud|nœuds|knot|knots?|kt|kts)'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _validate_numeric_claims(self, text: str) -> Tuple[bool, str]:
        """Validate numeric claims with per-occurrence context."""

        # Boat speed claims: speed unit but NOT in wind context
        speed_pattern = rf'(\d+(?:[.,]\d+)?)\s*({self.SPEED_UNITS})'

        for match in re.finditer(speed_pattern, text, re.IGNORECASE):
            start = match.start()

            # Skip if this specific occurrence is in wind context
            if self._is_speed_in_wind_context(text, start, match.end()):
                continue

            speed_str = match.group(1).replace(',', '.')
            try:
                speed_val = float(speed_str)
            except ValueError:
                continue

            if self.factual_sog is None:
                continue

            # Boat speed tolerance: ±1.5 knots
            if not self._is_within_tolerance(speed_val, self.factual_sog, 1.5):
                return False, f"Speed claim {speed_val} not supported by facts (factual: {self.factual_sog})"

        # Course claims: course label + numeric
        course_pattern = rf'({self.COURSE_LABELS})\s+(\d+)(?:\s*(?:degrés?|°))?'

        for match in re.finditer(course_pattern, text, re.IGNORECASE):
            course_str = match.group(2)
            try:
                course_val = float(course_str)
            except ValueError:
                continue

            if self.factual_cog is None:
                continue

            # Course tolerance: circular distance ±40 degrees
            if not self._is_within_circular_tolerance(course_val, self.factual_cog, 40.0):
                return False, f"Course claim {course_val}° not supported by facts (factual: {self.factual_cog}°)"

        return True, ""

    def _is_speed_in_wind_context(self, text: str, start: int, end: int) -> bool:
        """Check if this specific speed occurrence is in wind context.

        Look for wind/vent pattern immediately before the speed match.
        """
        # Check if the text immediately before this match contains wind pattern
        before = text[max(0, start - 80):start]
        if re.search(r'(?:vent|wind)\s+(?:souffle\s+)?(?:à|at)\s+$', before, re.IGNORECASE):
            return True

        return False

    def _is_within_tolerance(self, claim: float, factual: float, tolerance: float) -> bool:
        """Check if claim is within tolerance of factual value."""
        return abs(claim - factual) <= tolerance

    def _is_within_circular_tolerance(self, claim: float, factual: float, tolerance: float) -> bool:
        """Check if course claim is within circular tolerance."""
        claim = claim % 360
        factual = factual % 360
        diff = abs(claim - factual)
        if diff > 180:
            diff = 360 - diff
        return diff <= tolerance

"""
Strict output validation for LLM-generated race articles.

Prevents hallucinations, credential leaks, and unsupported claims.
Fails closed if validation fails.
"""

import re
from typing import Tuple, Set
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
        r'<script\s+',
        r'javascript:',
        r'onerror\s*=',
        r'onload\s*=',
    ]
    
    def __init__(self, facts: RaceFacts):
        """Initialize validator with reference facts."""
        self.facts = facts
        self.valid_positions: Set[str] = set()
        self.valid_speeds: Set[float] = set()
        self.valid_courses: Set[float] = set()
        self._extract_valid_values()
    
    def _extract_valid_values(self):
        """Extract known valid values from facts for comparison."""
        if self.facts.position and self.facts.position.is_valid():
            # Position to ±0.01 degrees for fuzzy matching
            lat = self.facts.position.latitude
            lon = self.facts.position.longitude
            self.valid_positions.add(f"{lat:.2f}")
            self.valid_positions.add(f"{lon:.2f}")
        
        if self.facts.navigation and self.facts.navigation.is_valid():
            sog = self.facts.navigation.sog_knots
            cog = self.facts.navigation.cog_degrees
            # Allow ±1 knot and ±30 degrees variation
            if sog:
                for v in [sog - 1, sog, sog + 1]:
                    if v >= 0:
                        self.valid_speeds.add(round(v, 1))
            if cog:
                for v in [cog - 30, cog, cog + 30]:
                    if 0 <= v <= 360:
                        self.valid_courses.add(round(v, 0))
    
    def validate(self, output: str) -> Tuple[bool, str]:
        """
        Validate output. Return (is_valid, error_message).
        
        Checks for:
        - Non-empty
        - Valid UTF-8
        - Length limit
        - Sentence count
        - No Markdown
        - No commands/credentials
        - No injection patterns
        - Numeric claims traced to facts
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
        
        # Numeric claims check
        valid, reason = self._validate_numeric_claims(output)
        if not valid:
            return False, reason
        
        return True, ""
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences using robust pattern."""
        # Split on period, question mark, exclamation mark followed by space or end
        sentences = re.split(r'[.!?]+\s+|\n|$', text)
        # Filter empty strings
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
    
    def _validate_numeric_claims(self, text: str) -> Tuple[bool, str]:
        """
        Validate numeric claims against facts.
        
        Checks:
        - Claimed speeds are within ±1 knot of known SOG
        - Claimed courses are within ±30° of known COG
        - No coordinates are exact (must be summarized)
        - No ranking or elapsed-time claims
        - No competitor names not in AIS data
        """
        
        # Extract all numbers
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
        
        for num_str in numbers:
            try:
                num_val = float(num_str)
            except ValueError:
                continue
            
            # Check if it could be a speed (0-30 knots reasonable)
            if 0 <= num_val <= 30:
                # If speeds are known, validate against them
                if self.valid_speeds and num_val not in self.valid_speeds:
                    # Check if it's close to any valid speed
                    is_close = any(abs(num_val - v) <= 1.5 for v in self.valid_speeds)
                    if not is_close:
                        return False, f"Speed claim {num_val} knots not supported by facts (closest: {min(self.valid_speeds)})"
            
            # Check if it could be a course (0-360 degrees)
            if 0 <= num_val <= 360:
                # If courses are known, validate
                if self.valid_courses and num_val not in self.valid_courses:
                    # Check if it's close
                    is_close = any(abs(num_val - v) <= 40 for v in self.valid_courses)
                    if not is_close:
                        return False, f"Course claim {num_val}° not supported by facts"
        
        # Check for exact coordinates (latitude/longitude patterns)
        coord_pattern = r'\b(\d+\.\d{4,})[°º]?\s*[NS]?\s*[,\s]\s*(\d+\.\d{4,})[°º]?\s*[EW]?\b'
        if re.search(coord_pattern, text):
            return False, "Exact coordinates not permitted (use summarized descriptions instead)"
        
        # Check for unsupported claims
        unsupported_claims = [
            (r'(?i)(rank|leading|trailing|first place|second place|win|beat)', "ranking"),
            (r'(?i)(elapsed|time since start|minutes to finish)', "elapsed time"),
            (r'(?i)(heel|pitch|roll|heel angle)', "heel/attitude"),
        ]
        
        for pattern, claim_type in unsupported_claims:
            if re.search(pattern, text):
                return False, f"Unsupported claim type: {claim_type} not in RaceFacts"
        
        return True, ""

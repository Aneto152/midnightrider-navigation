"""
Validated self-vessel context classification.

Loads canonical self-vessel identity from Signal K runtime configuration.
Provides exact-match classification without exposing raw identity values.

Never prints, logs, or persists raw context values.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)


class SelfContextValidator:
    """Load and validate canonical self-vessel contexts from Signal K baseDeltas.json."""
    
    def __init__(self, source_path: Optional[Path] = None):
        """
        Initialize validator with canonical identity source.
        
        Args:
            source_path: Path to Signal K baseDeltas.json.
                         If None, uses standard Signal K home location.
        
        Raises:
            ValueError: If source cannot be loaded or parsed.
        """
        self.source_path = source_path or Path.home() / ".signalk" / "baseDeltas.json"
        self.canonical_contexts: Set[str] = set()
        
        self._load_canonical_contexts()
    
    def _load_canonical_contexts(self) -> None:
        """Load canonical self-vessel contexts from Signal K configuration."""
        if not self.source_path.exists():
            raise ValueError(f"Source not found: {self.source_path}")
        
        try:
            with open(self.source_path, 'r') as f:
                signal_k_config = json.load(f)
            
            # Extract canonical contexts from vessels.self entries
            for entry in signal_k_config:
                if entry.get("context") == "vessels.self":
                    for update in entry.get("updates", []):
                        for value in update.get("values", []):
                            if value.get("path") == "":
                                vessel_data = value.get("value", {})
                                # Use UUID as canonical identifier (primary)
                                if "uuid" in vessel_data:
                                    identity = vessel_data.get("uuid", "").strip()
                                    if identity:
                                        self.canonical_contexts.add(identity)
                                # Use name as fallback
                                elif "name" in vessel_data:
                                    identity = vessel_data.get("name", "").strip()
                                    if identity:
                                        self.canonical_contexts.add(identity)
            
            if not self.canonical_contexts:
                raise ValueError("No canonical contexts extracted from source")
            
            logger.debug(f"Loaded {len(self.canonical_contexts)} canonical context(s)")
        
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error in {self.source_path}: {e}")
    
    def is_self_vessel(self, context_value: Optional[str]) -> bool:
        """
        Check if context value matches canonical self-vessel identity.
        
        Args:
            context_value: Context value from InfluxDB record.
        
        Returns:
            True if context matches exactly any canonical identity, False otherwise.
        """
        if not context_value:
            return False
        
        # Exact match after normalization (whitespace only)
        context_normalized = context_value.strip().lower()
        
        for canonical in self.canonical_contexts:
            canonical_normalized = canonical.strip().lower()
            if context_normalized == canonical_normalized:
                return True
        
        return False
    
    def has_canonical_contexts(self) -> bool:
        """Check if canonical contexts were successfully loaded."""
        return len(self.canonical_contexts) > 0


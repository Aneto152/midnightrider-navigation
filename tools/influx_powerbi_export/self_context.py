"""
Runtime self-vessel context classification.

Loads self-vessel context directly from Signal K runtime app.selfId.
Signal K plugin (signalk-to-influxdb2) writes delta.context directly to InfluxDB.
The operative context source is delta.context in the live stream, not static configuration.

Derivation: self_context = vessels.<app.selfId>

Provides exact-match classification without exposing raw identity values.
Never prints, logs, or persists raw context values.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)


class SelfContextValidator:
    """Load and validate self-vessel context from Signal K runtime.
    
    The operative context source is the live Signal K delta.context field.
    The signalk-to-influxdb2 plugin computes:
        selfContext = 'vessels.' + app.selfId
    
    This validator loads the runtime app.selfId and constructs the exact context.
    """
    
    def __init__(self, self_contexts: Optional[Set[str]] = None):
        """
        Initialize validator with self-vessel contexts.
        
        Args:
            self_contexts: Pre-loaded set of self contexts (for testing).
                          If None, loads from Signal K runtime at runtime.
        
        Raises:
            ValueError: If contexts cannot be loaded or are empty.
        """
        # For tests: accept pre-loaded contexts
        if self_contexts is not None:
            if not self_contexts:
                raise ValueError("self_contexts set cannot be empty")
            self.canonical_contexts: Set[str] = self_contexts
            logger.debug(f"Initialized with {len(self.canonical_contexts)} test context(s)")
            return
        
        # For production: load from Signal K runtime
        self.canonical_contexts: Set[str] = set()
        self._load_runtime_self_context()
    
    def _load_runtime_self_context(self) -> None:
        """Load self-vessel context from Signal K runtime.
        
        The operative source is the live Signal K app.selfId.
        Never use baseDeltas.json; it is not the operative context source.
        """
        # Signal K stores app.selfId in multiple possible locations
        # Try standard Signal K configuration first
        possible_sources = [
            Path.home() / ".signalk" / "settings.json",
            Path.home() / ".signalk" / "engine.json",
        ]
        
        self_id = None
        
        for source_path in possible_sources:
            if not source_path.exists():
                continue
            
            try:
                with open(source_path, 'r') as f:
                    config = json.load(f)
                
                # Try to extract selfId or app.selfId
                if isinstance(config, dict):
                    # Try direct selfId key
                    if "selfId" in config:
                        self_id = config.get("selfId")
                    # Try nested app.selfId
                    elif "app" in config and isinstance(config.get("app"), dict):
                        self_id = config["app"].get("selfId")
                    # Try settings.selfId structure
                    elif "settings" in config and isinstance(config.get("settings"), dict):
                        self_id = config["settings"].get("selfId")
                
                if self_id and isinstance(self_id, str) and self_id.strip():
                    break
            
            except (json.JSONDecodeError, IOError):
                continue
        
        # If not found in configuration files, fail closed
        if not self_id:
            raise ValueError(
                "app.selfId not found in Signal K runtime configuration. "
                "Cannot derive self-vessel context."
            )
        
        # Construct runtime self context exactly as plugin does:
        # selfContext = 'vessels.' + app.selfId
        runtime_context = f"vessels.{self_id.strip()}"
        self.canonical_contexts.add(runtime_context)
        
        logger.debug(f"Loaded runtime self context (1 context)")
    
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


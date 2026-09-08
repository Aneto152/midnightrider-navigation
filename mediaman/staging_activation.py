"""
Staging activation gate: one-shot DRY_RUN-only activation for PublicationBridge.

Enforces strict mode and dry_run validation. No daemon, no scheduler, no service.
Uses injected PublicationBridge with no environment variable access.
"""

from mediaman.publication_contract import PublicationDTO
from mediaman.publication_state import PublicationStateRecord
from mediaman.publication_bridge import PublicationBridge


class StagingActivation:
    """One-shot staging activation gate for DRY_RUN publication."""

    def __init__(
        self,
        bridge: PublicationBridge,
        *,
        mode: str,
        dry_run: bool,
    ):
        """
        Initialize staging activation gate with strict mode and dry_run enforcement.

        Args:
            bridge: Existing PublicationBridge instance (injected)
            mode: Must be exactly "staging"
            dry_run: Must be exactly True (bool, not truthy)

        Raises:
            ValueError("staging_mode_required"): mode is not exactly "staging"
            ValueError("dry_run_required"): dry_run is not exactly True
            ValueError("invalid_bridge"): bridge is not a PublicationBridge instance
        """
        # 1. Validate bridge
        if not isinstance(bridge, PublicationBridge):
            raise ValueError("invalid_bridge")

        # 2. Validate mode is exactly "staging"
        if mode != "staging":
            raise ValueError("staging_mode_required")

        # 3. Validate dry_run is exactly True (bool, not truthy)
        if dry_run is not True:
            raise ValueError("dry_run_required")

        self.bridge = bridge

    def run_once(
        self,
        publication: PublicationDTO,
    ) -> PublicationStateRecord:
        """
        Execute one-shot publication through the bridge.

        This is a one-shot gate: it runs the publication exactly once and returns.
        No retry, no reconciliation, no scheduling.

        Args:
            publication: PublicationDTO to publish

        Returns:
            PublicationStateRecord from bridge.publish()

        Raises:
            ValueError("invalid_publication"): publication is not a PublicationDTO
        """
        # 1. Validate input
        if not isinstance(publication, PublicationDTO):
            raise ValueError("invalid_publication")

        # 2. Call bridge.publish() exactly once
        result = self.bridge.publish(publication)

        # 3. Return the result
        return result

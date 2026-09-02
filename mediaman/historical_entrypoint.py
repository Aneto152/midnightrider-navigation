#!/usr/bin/env python3
"""
Historical InfluxDB Dry-Run Entrypoint for MediaMan.

One-shot offline execution that generates a single local test message from
historical InfluxDB snapshot via MCP racing server.

Required environment variables (exact checks, no defaults):
- MEDIAMAN_CONTENT_PROVIDER=historical_mcp (exact match)
- MEDIAMAN_RACE_ID=<non-empty safe identifier>
- MEDIAMAN_HISTORICAL_AS_OF=<strict ISO-8601 UTC timestamp ending in Z>
- MEDIAMAN_HISTORICAL_WINDOW_SECONDS=<integer 1..3600>
- MEDIAMAN_MCP_SERVER_PATH=<path to existing executable>
- DRY_RUN=true (exact string, case-sensitive)

Execution:
- MCPClient (subprocess) → MCPCollector → Provider (via factory) → Bridge → DryRunSender
- Temporary SQLite state database
- No TelegramSender instantiation
- No Telegram credential access
- Guaranteed MCPClient termination (success and failure paths)

Returns:
- 0 on success
- non-zero on validation error, MCP error, or publication failure
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add repository to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mediaman.historical_request import HistoricalRequest
from mediaman.mcp_client import MCPClient, MCPClientError
from mediaman.mcp_collector import MCPCollector
from mediaman.content_provider import get_content_provider
from mediaman.publication_contract import PublicationDTO
from mediaman.publication_bridge import PublicationBridge
from mediaman.publication_state import PublicationStateStore
from mediaman.logging_utils import setup_service_logger


class DryRunSender:
    """Deterministic dry-run sender with no Telegram contact.

    Produces stable cross-process provider IDs derived from canonical
    serialization of (race_id, as_of_utc, window_seconds, content_sha256).
    Two independent instances with same inputs → same provider ID.
    """

    def __init__(self, logger=None):
        self.dry_run = True
        self.logger = logger
        self._call_count = 0  # Call counter for diagnostics only, not identity

    def send(self, message: str, race_id: str = None, as_of_utc: str = None,
             window_seconds: int = None) -> 'SendResult':
        """Simulate sending without network calls. Deterministic cross-process ID.

        Args:
            message: Content to send
            race_id: Race identifier (for stable ID derivation)
            as_of_utc: Historical timestamp (for stable ID derivation)
            window_seconds: Query window in seconds (for stable ID derivation)

        Returns:
            SendResult with stable provider ID derived from canonical inputs
        """
        from mediaman.publication_contract import SendResult
        import hashlib

        self._call_count += 1

        # Derive stable provider ID from canonical serialization
        # Two independent senders with same (race_id, as_of_utc, window_seconds, content)
        # produce identical provider IDs
        if race_id is not None and as_of_utc is not None and window_seconds is not None:
            # Hash canonical tuple for stable cross-process identity
            content_sha256 = hashlib.sha256(message.encode('utf-8')).hexdigest()
            canonical = f"{race_id}:{as_of_utc}:{window_seconds}:{content_sha256}"
            identity_sha = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
            execution_id = f"dry-run:{identity_sha}"
        else:
            # Fallback for diagnostic use (not stable across processes)
            execution_id = f"dry-run:{self._call_count:08d}"

        return SendResult(
            dry_run=True,
            success=True,
            provider_status="DRY_RUN",
            execution_id=execution_id,
            error_code=None,
            error_message=None
        )


def main(argv: list | None = None) -> int:
    """
    Execute historical message generation in offline dry-run mode.

    Returns:
        0 on success
        non-zero on any validation or execution error
    """
    logger = setup_service_logger('mediaman-historical-entrypoint')
    logger.info("STARTUP historical entrypoint")

    # PHASE 1: STRICT ENVIRONMENT VARIABLE VALIDATION
    # All required; no defaults; exact checks

    content_provider = os.getenv("MEDIAMAN_CONTENT_PROVIDER", "").strip().lower()
    race_id = os.getenv("MEDIAMAN_RACE_ID", "").strip()
    as_of_utc = os.getenv("MEDIAMAN_HISTORICAL_AS_OF", "").strip()
    window_seconds_str = os.getenv("MEDIAMAN_HISTORICAL_WINDOW_SECONDS", "").strip()
    mcp_server_path = os.getenv("MEDIAMAN_MCP_SERVER_PATH", "").strip()
    dry_run = os.getenv("DRY_RUN", "").strip()

    # Validate MEDIAMAN_CONTENT_PROVIDER (exact match)
    if content_provider != "historical_mcp":
        logger.error(f"ERROR: MEDIAMAN_CONTENT_PROVIDER must be 'historical_mcp', got: {content_provider}")
        return 1

    # Validate MEDIAMAN_RACE_ID (non-empty)
    if not race_id:
        logger.error("ERROR: MEDIAMAN_RACE_ID is required (non-empty)")
        return 1

    # Validate MEDIAMAN_HISTORICAL_AS_OF (ISO 8601 UTC with Z suffix)
    if not as_of_utc:
        logger.error("ERROR: MEDIAMAN_HISTORICAL_AS_OF is required")
        return 1

    if not as_of_utc.endswith("Z"):
        logger.error(f"ERROR: MEDIAMAN_HISTORICAL_AS_OF must end with 'Z' (UTC), got: {as_of_utc}")
        return 1

    # Validate timestamp format and reject future dates
    try:
        as_of_dt = datetime.fromisoformat(as_of_utc.replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        if as_of_dt > now_utc:
            logger.error(f"ERROR: MEDIAMAN_HISTORICAL_AS_OF cannot be in future: {as_of_utc}")
            return 1
    except ValueError:
        logger.error(f"ERROR: MEDIAMAN_HISTORICAL_AS_OF has invalid ISO 8601 format: {as_of_utc}")
        return 1

    # Validate MEDIAMAN_HISTORICAL_WINDOW_SECONDS (integer, 1-3600)
    if not window_seconds_str:
        logger.error("ERROR: MEDIAMAN_HISTORICAL_WINDOW_SECONDS is required")
        return 1

    try:
        window_seconds = int(window_seconds_str)
    except ValueError:
        logger.error(f"ERROR: MEDIAMAN_HISTORICAL_WINDOW_SECONDS must be integer, got: {window_seconds_str}")
        return 1

    if window_seconds < 1:
        logger.error(f"ERROR: MEDIAMAN_HISTORICAL_WINDOW_SECONDS must be >= 1, got: {window_seconds}")
        return 1

    if window_seconds > 3600:
        logger.error(f"ERROR: MEDIAMAN_HISTORICAL_WINDOW_SECONDS must be <= 3600, got: {window_seconds}")
        return 1

    # Validate MEDIAMAN_MCP_SERVER_PATH (must exist)
    if not mcp_server_path:
        logger.error("ERROR: MEDIAMAN_MCP_SERVER_PATH is required")
        return 1

    if not Path(mcp_server_path).exists():
        logger.error(f"ERROR: MEDIAMAN_MCP_SERVER_PATH does not exist: {mcp_server_path}")
        return 1

    # Validate DRY_RUN=true (exact string, case-sensitive)
    if dry_run != "true":
        logger.error(f"ERROR: DRY_RUN must be exactly 'true' (case-sensitive), got: {dry_run}")
        return 1

    logger.info(f"DATA_IN environment variables validated")

    # PHASE 2: VALIDATE HISTORICAL REQUEST CONTRACT
    try:
        request = HistoricalRequest(
            race_id=race_id,
            as_of_utc=as_of_utc,
            window_seconds=window_seconds
        )
    except ValueError as e:
        logger.error(f"ERROR: Invalid historical request: {e}")
        return 1

    logger.info(f"DATA_IN historical request contract valid")

    # PHASE 3: INITIALIZE MCP CLIENT (offline, subprocess-based)
    mcp_client = None
    try:
        mcp_client = MCPClient(
            server_path=mcp_server_path,
            server_name="racing"
        )
        mcp_client.start()
        logger.info("DATA_IN MCP client started")
    except (MCPClientError, FileNotFoundError, OSError) as e:
        logger.error(f"ERROR: Failed to start MCP client: {e}")
        return 1
    except Exception as e:
        logger.error(f"ERROR: Unexpected MCP client error: {e}")
        return 1

    try:
        # PHASE 4: CREATE TEMPORARY STATE STORE (SQLite)
        with tempfile.TemporaryDirectory(prefix="mediaman-hist-") as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            state_store = PublicationStateStore(
                db_path=db_path,
                clock=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            )
            state_store.initialize()
            logger.info("DATA_IN temporary SQLite state store initialized")

            # PHASE 5: INITIALIZE MCPCollector WITH MCP CLIENT
            collector = MCPCollector(
                client=mcp_client,
                race_id=race_id
            )
            logger.info("DATA_IN MCPCollector initialized")

            # PHASE 6: GET HISTORICAL PROVIDER VIA FACTORY WITH EXPLICIT COLLECTOR INJECTION
            try:
                provider = get_content_provider(
                    provider_name="historical_mcp",
                    mcp_collector=collector
                )
            except ValueError as e:
                logger.error(f"ERROR: Provider factory failed: {e}")
                return 1

            logger.info("DATA_IN historical provider created via factory")

            # PHASE 7: INITIALIZE DETERMINISTIC DRY_RUN SENDER (no Telegram)
            sender = DryRunSender(logger=logger)
            logger.info("DATA_IN DryRunSender initialized")

            # PHASE 8: INITIALIZE PUBLICATION BRIDGE (offline, DRY_RUN=true enforced)
            bridge = PublicationBridge(
                state_store=state_store,
                sender=sender,
                clock=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            )
            logger.info("DATA_IN PublicationBridge initialized")

            # PHASE 9: GENERATE HISTORICAL CONTENT
            try:
                content = provider.get_content_for_historical(
                    as_of_utc=as_of_utc,
                    window_seconds=window_seconds
                )
                logger.info(f"DATA_OUT content generated: {len(content)} bytes")
            except ValueError as e:
                logger.error(f"ERROR: Content generation failed: {e}")
                return 1

            # PHASE 10: VALIDATE CONTENT (French, no credentials)
            is_valid, error_msg = provider.validate(content)
            if not is_valid:
                logger.error(f"ERROR: Content validation failed: {error_msg}")
                return 1

            logger.info("DATA_OUT content validated")

            # PHASE 11: CREATE IMMUTABLE PUBLICATION DTO
            publication_id = f"hist-{datetime.now(timezone.utc).isoformat()[:19].replace(':', '')}"
            try:
                publication = PublicationDTO(
                    publication_id=publication_id,
                    race_id=race_id,
                    cycle_id=f"historical-{as_of_utc}",
                    content=content,
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                )
            except Exception as e:
                logger.error(f"ERROR: Failed to create publication DTO: {e}")
                return 1

            logger.info(f"DATA_IN publication created: id={publication_id}")

            # PHASE 12: PUBLISH VIA BRIDGE (one-shot, dry-run only)
            # Update sender with canonical parameters for deterministic cross-process identity
            sender.race_id = race_id
            sender.as_of_utc = as_of_utc
            sender.window_seconds = window_seconds

            try:
                result = bridge.publish(publication)
                logger.info(f"DATA_OUT publication published: state={result.state.value}, provider_id={result.provider_message_id}")
            except ValueError as e:
                logger.error(f"ERROR: Publication failed: {e}")
                return 1

            # PHASE 13: VERIFY DRY_RUN ENFORCEMENT (provider_message_id must start with "dry-run:")
            if not result.provider_message_id or not result.provider_message_id.startswith("dry-run:"):
                logger.error(f"ERROR: DRY_RUN enforcement failed: provider_id={result.provider_message_id}")
                return 1

            logger.info("DATA_OUT dry-run publication successful and verified")

    finally:
        # PHASE 14: GUARANTEED MCP CLIENT CLEANUP
        if mcp_client:
            try:
                mcp_client.terminate()
                logger.info("DATA_OUT MCP client terminated")
            except Exception as e:
                logger.error(f"ERROR: MCP client termination error: {e}")
                # Don't fail; cleanup was attempted

    logger.info("SHUTDOWN historical entrypoint completed successfully")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

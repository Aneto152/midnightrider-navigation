#!/usr/bin/env python3
"""
Historical InfluxDB Dry-Run Entrypoint for MediaMan.

One-shot execution mode that generates a single test message from historical InfluxDB data
using the MCP racing server.

Required environment variables:
- MEDIAMAN_CONTENT_PROVIDER=historical_mcp
- MEDIAMAN_HISTORICAL_AS_OF=<ISO-8601-UTC>
- MEDIAMAN_HISTORICAL_WINDOW_SECONDS=<positive-integer>
- MEDIAMAN_MCP_SERVER_PATH=<path-to-racing-server>
- DRY_RUN=true

Enforcement:
- Offline-only execution (no network calls except MCP server subprocess)
- DRY_RUN=true mandatory
- No TelegramSender instantiation
- No Telegram credentials read
- Synthetic dry-run sender only
- Temporary SQLite state database
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add repository to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mediaman.historical_request import HistoricalRequest
from mediaman.mcp_client import MCPClient
from mediaman.mcp_collector import MCPCollector
from mediaman.content_provider import HistoricalMCPProvider
from mediaman.publication_contract import PublicationDTO
from mediaman.publication_bridge import PublicationBridge
from mediaman.publication_state import PublicationStateStore
from mediaman.logging_utils import setup_service_logger


class DryRunSender:
    """Synthetic dry-run sender for testing. No Telegram contact."""
    
    def __init__(self, logger=None):
        self.dry_run = True
        self.logger = logger
    
    def send(self, message: str):
        """Simulate sending without network calls."""
        from mediaman.publication_contract import SendResult
        
        import uuid
        execution_id = str(uuid.uuid4())[:8]
        
        return SendResult(
            dry_run=True,
            success=True,
            provider_status="DRY_RUN",
            execution_id=f"dry-run:{execution_id}",
            error_code=None,
            error_message=None
        )


def main():
    """Execute historical message generation in offline dry-run mode."""
    
    logger = setup_service_logger('mediaman-historical-entrypoint')
    logger.info("STARTUP historical entrypoint")
    
    try:
        # PHASE 1: Validate required environment variables
        content_provider_env = os.getenv("MEDIAMAN_CONTENT_PROVIDER", "").strip().lower()
        as_of_utc_env = os.getenv("MEDIAMAN_HISTORICAL_AS_OF", "").strip()
        window_seconds_env = os.getenv("MEDIAMAN_HISTORICAL_WINDOW_SECONDS", "").strip()
        mcp_server_path_env = os.getenv("MEDIAMAN_MCP_SERVER_PATH", "").strip()
        dry_run_env = os.getenv("DRY_RUN", "").strip().lower()
        
        # Validate MEDIAMAN_CONTENT_PROVIDER
        if content_provider_env != "historical_mcp":
            logger.error("ERROR: MEDIAMAN_CONTENT_PROVIDER must be 'historical_mcp'")
            return 1
        
        # Validate MEDIAMAN_HISTORICAL_AS_OF
        if not as_of_utc_env:
            logger.error("ERROR: MEDIAMAN_HISTORICAL_AS_OF is required")
            return 1
        
        # Validate MEDIAMAN_HISTORICAL_WINDOW_SECONDS
        if not window_seconds_env:
            logger.error("ERROR: MEDIAMAN_HISTORICAL_WINDOW_SECONDS is required")
            return 1
        
        try:
            window_seconds = int(window_seconds_env)
        except ValueError:
            logger.error(f"ERROR: MEDIAMAN_HISTORICAL_WINDOW_SECONDS must be integer, got: {window_seconds_env}")
            return 1
        
        # Validate MEDIAMAN_MCP_SERVER_PATH
        if not mcp_server_path_env:
            logger.error("ERROR: MEDIAMAN_MCP_SERVER_PATH is required")
            return 1
        
        if not Path(mcp_server_path_env).exists():
            logger.error(f"ERROR: MEDIAMAN_MCP_SERVER_PATH not found: {mcp_server_path_env}")
            return 1
        
        # Validate DRY_RUN=true
        if dry_run_env != "true":
            logger.error("ERROR: DRY_RUN must be 'true' (exact string match)")
            return 1
        
        logger.info(f"DATA_IN historical parameters validated: as_of={as_of_utc_env}, window={window_seconds}s")
        
        # PHASE 2: Validate historical request parameters
        try:
            request = HistoricalRequest(
                race_id="historical",
                as_of_utc=as_of_utc_env,
                window_seconds=window_seconds
            )
        except ValueError as e:
            logger.error(f"ERROR: Invalid historical request: {e}")
            return 1
        
        logger.info(f"DATA_IN historical request valid: source={request.source}")
        
        # PHASE 3: Initialize MCP client
        try:
            mcp_client = MCPClient(
                server_path=mcp_server_path_env,
                server_name="racing"
            )
            mcp_client.start()
            logger.info("DATA_IN MCP client started")
        except Exception as e:
            logger.error(f"ERROR: Failed to start MCP client: {e}")
            return 1
        
        try:
            # PHASE 4: Initialize temporary state store
            with tempfile.TemporaryDirectory(prefix="mediaman-historical.") as tmpdir:
                db_path = os.path.join(tmpdir, "publication-state.sqlite3")
                
                state_store = PublicationStateStore(
                    db_path=db_path,
                    clock=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                )
                state_store.initialize()
                logger.info("DATA_IN temporary state store initialized")
                
                # PHASE 5: Initialize MCP collector
                collector = MCPCollector(
                    client=mcp_client,
                    race_id="historical"
                )
                
                # PHASE 6: Initialize historical provider with injected collector
                provider = HistoricalMCPProvider(mcp_collector=collector)
                
                # PHASE 7: Initialize dry-run sender (no Telegram)
                sender = DryRunSender(logger=logger)
                
                # PHASE 8: Initialize publication bridge
                bridge = PublicationBridge(
                    state_store=state_store,
                    sender=sender,
                    clock=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                )
                logger.info("DATA_IN bridge, collector, provider initialized")
                
                # PHASE 9: Generate historical content
                try:
                    content = provider.get_content_for_historical(
                        as_of_utc=as_of_utc_env,
                        window_seconds=window_seconds
                    )
                    logger.info(f"DATA_OUT historical content generated: length={len(content)}")
                except ValueError as e:
                    logger.error(f"ERROR: Historical content generation failed: {e}")
                    return 1
                
                # PHASE 10: Validate content
                is_valid, error = provider.validate(content)
                if not is_valid:
                    logger.error(f"ERROR: Content validation failed: {error}")
                    return 1
                
                logger.info("DATA_OUT content validated")
                
                # PHASE 11: Create publication DTO
                publication_id = f"hist-{datetime.now(timezone.utc).isoformat()[:19].replace(':', '')}"
                publication = PublicationDTO(
                    publication_id=publication_id,
                    race_id="historical",
                    cycle_id=f"historical-{as_of_utc_env}",
                    content=content,
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                )
                logger.info(f"DATA_IN publication DTO created: publication_id={publication_id}")
                
                # PHASE 12: Publish via bridge (dry-run only)
                try:
                    result = bridge.publish(publication)
                    logger.info(f"DATA_OUT publication result: state={result.state}, provider_id={result.provider_message_id}")
                except ValueError as e:
                    logger.error(f"ERROR: Publication failed: {e}")
                    return 1
                
                # PHASE 13: Verify dry-run
                if not result.provider_message_id.startswith("dry-run:"):
                    logger.error("ERROR: Publication did not use dry-run sender")
                    return 1
                
                logger.info("DATA_OUT dry-run publication successful")
        
        finally:
            # Clean up MCP client
            mcp_client.terminate()
            logger.info("DATA_OUT MCP client terminated")
        
        logger.info("SHUTDOWN historical entrypoint completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"ERROR: Unexpected failure: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

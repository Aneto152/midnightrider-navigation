"""
MediaMan — Main entry point for outbound Telegram race reporting.

One-shot execution: generate article → validate → send → log.
No inbound processing, no long-running daemon, no listening port.
"""

import sys
import os
from datetime import datetime, timezone

from .telegram_sender import TelegramSender
from .content_provider import get_content_provider
from .idempotency import IdempotencyKey, IdempotencyStore
from .logging_utils import setup_service_logger, setup_debug_logger, SanitizedMessage


def main():
    """
    Main entry point for MediaMan.
    
    Environment variables:
    - TELEGRAM_BOT_TOKEN: Required for real sends
    - TELEGRAM_CHAT_ID: Required for real sends
    - DRY_RUN: Set to "true" for testing without network I/O
    - MEDIAMAN_CONTENT_PROVIDER: "test" or "gateway" (default: test)
    - MEDIAMAN_RACE_ID: Race identifier (default: "test-race")
    """
    
    # Setup logging
    service_logger = setup_service_logger("mediaman")
    debug_logger = setup_debug_logger()
    
    dry_run = os.getenv("DRY_RUN", "").lower() == "true"
    race_id = os.getenv("MEDIAMAN_RACE_ID", "test-race")
    
    try:
        # Log startup
        service_logger.info(SanitizedMessage.startup(dry_run))
        
        # Initialize components
        sender = TelegramSender()
        provider = get_content_provider()
        idempotency_store = IdempotencyStore()
        
        cycle_ts = datetime.now(timezone.utc).isoformat()
        
        # Generate content
        content = provider.get_content(race_id, cycle_ts)
        
        # Validate content
        if hasattr(provider, 'validate'):
            is_valid, error = provider.validate(content)
            if not is_valid:
                service_logger.error(f"Content validation failed: {error}")
                debug_logger.error(f"VALIDATION_FAILED: {error}")
                return 1
        
        service_logger.info(
            SanitizedMessage.content_validation(
                race_id, cycle_ts, len(content), True
            )
        )
        
        # Check idempotency
        try:
            idem_key = IdempotencyKey(race_id, cycle_ts, sender.chat_id)
            should_send = idempotency_store.check_and_record(idem_key)
            
            if not should_send:
                service_logger.info(
                    f"Skipping duplicate cycle: race_id={race_id} cycle={cycle_ts}"
                )
                return 0
        except Exception as e:
            service_logger.error(f"Idempotency check failed: {e}")
            # Continue anyway (fail open)
        
        # Send to Telegram
        service_logger.info(
            SanitizedMessage.send_attempt(dry_run, sender.chat_id, len(content), sender.execution_id)
        )
        
        result = sender.send(content)
        
        # Log result
        service_logger.info(
            SanitizedMessage.send_result(
                result.dry_run,
                result.success,
                result.provider_status,
                result.error_code,
                result.execution_id
            )
        )
        
        # Log data flow (data out)
        debug_logger.info(
            f"DATA_OUT provider_status={result.provider_status} "
            f"success={result.success} "
            f"length={result.message_length}"
        )
        
        # Log shutdown
        service_logger.info(SanitizedMessage.shutdown(1))
        
        return 0 if result.success else 1
    
    except Exception as e:
        service_logger.error(f"Fatal error: {e}", exc_info=True)
        debug_logger.error(f"FATAL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

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
from .idempotency import normalize_to_15min_bucket
from .sqlite_state import SQLiteStateStore
from .logging_utils import setup_service_logger, setup_debug_logger, SanitizedMessage


def main():
    """
    Main entry point for MediaMan.
    
    Environment variables:
    - TELEGRAM_BOT_TOKEN: Required for real sends
    - TELEGRAM_CHAT_ID: Required for real sends
    - DRY_RUN: Set to "true" for testing without network I/O (default: true)
    - MEDIAMAN_CONTENT_PROVIDER: "test" or "gateway" (default: test)
    - MEDIAMAN_RACE_ID: Race identifier (default: "test-race")
    - MEDIAMAN_PRODUCTION_MODE: "true" only when explicitly set for production (default: false)
    """
    
    # Setup logging
    service_logger = setup_service_logger("mediaman")
    debug_logger = setup_debug_logger()
    
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    production_mode = os.getenv("MEDIAMAN_PRODUCTION_MODE", "false").lower() == "true"
    race_id = os.getenv("MEDIAMAN_RACE_ID", "test-race")
    provider_name = os.getenv("MEDIAMAN_CONTENT_PROVIDER", "test").lower()
    
    try:
        # BLOCKER 1: Fail closed if attempting production without explicit mode
        if not dry_run and not production_mode:
            service_logger.error(
                "BLOCKER: Production mode requested (DRY_RUN=false) "
                "but MEDIAMAN_PRODUCTION_MODE not set. Failing closed."
            )
            debug_logger.error("BLOCKER: Production mode not explicitly enabled")
            return 1
        
        # BLOCKER 2: Fail closed if using test provider with production
        if not dry_run and provider_name == "test":
            service_logger.error(
                "BLOCKER: Test provider cannot be used in production. "
                "Enable MEDIAMAN_PRODUCTION_MODE only with a real provider."
            )
            debug_logger.error("BLOCKER: Test provider in production mode")
            return 1
        
        # Log startup
        service_logger.info(SanitizedMessage.startup(dry_run))
        debug_logger.info(f"STARTUP dry_run={dry_run} production_mode={production_mode} provider={provider_name}")
        
        # Initialize components
        sender = TelegramSender()
        provider = get_content_provider()
        idempotency_store = SQLiteStateStore()
        
        # BLOCKER 4: Use stable 15-minute cycle ID
        now_utc = datetime.now(timezone.utc)
        cycle_ts = normalize_to_15min_bucket(now_utc)
        debug_logger.info(f"DATA_IN normalized_cycle={cycle_ts} now={now_utc.isoformat()}")
        
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
        
        # Check idempotency and create delivery record
        try:
            # BLOCKER 3: Use explicit delivery states
            is_new = idempotency_store.record_pending(race_id, cycle_ts, sender.chat_id)
            
            if not is_new:
                current_state = idempotency_store.get_state(race_id, cycle_ts, sender.chat_id)
                if current_state == 'SENT':
                    service_logger.info(
                        f"Skipping already-sent cycle: race_id={race_id} cycle={cycle_ts} state=SENT"
                    )
                    return 0
                elif current_state == 'FAILED':
                    service_logger.info(
                        f"Retrying failed delivery: race_id={race_id} cycle={cycle_ts}"
                    )
                    idempotency_store.record_sending(race_id, cycle_ts, sender.chat_id)
                elif current_state == DeliveryRecord.SENDING:
                    service_logger.warning(
                        f"Stale SENDING state recovered: race_id={race_id} cycle={cycle_ts}"
                    )
                    idempotency_store.record_sending(race_id, cycle_ts, sender.chat_id)
                else:
                    service_logger.info(
                        f"Resuming cycle: race_id={race_id} cycle={cycle_ts} state={current_state}"
                    )
            else:
                idempotency_store.record_sending(race_id, cycle_ts, sender.chat_id)
        
        except Exception as e:
            service_logger.error(f"Idempotency check failed: {e}")
            debug_logger.error(f"IDEMPOTENCY_ERROR: {e}")
            return 1
        
        # Send to Telegram
        service_logger.info(
            SanitizedMessage.send_attempt(dry_run, sender.chat_id, len(content), sender.execution_id)
        )
        
        result = sender.send(content)
        
        # Update delivery state based on result
        if result.success:
            idempotency_store.record_sent(idem_key)
        else:
            idempotency_store.record_failed(race_id, cycle_ts, sender.chat_id, result.error_code)
        
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
        
        # Log heartbeat (one per successful cycle)
        if result.success:
            debug_logger.info(f"HEARTBEAT cycle={cycle_ts} provider={provider_name}")
        
        # Log shutdown
        service_logger.info(SanitizedMessage.shutdown(1))
        debug_logger.info("SHUTDOWN")
        
        return 0 if result.success else 1
    
    except Exception as e:
        service_logger.error(f"Fatal error: {e}", exc_info=True)
        debug_logger.error(f"FATAL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

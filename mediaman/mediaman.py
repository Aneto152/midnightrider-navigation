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
        
        # Claim delivery for sending
        try:
            can_send = idempotency_store.claim_for_send(race_id, cycle_ts, sender.chat_id)
            
            if not can_send:
                current_state = idempotency_store.get_state(race_id, cycle_ts, sender.chat_id)
                service_logger.info(
                    f"Delivery not retryable: race_id={race_id} cycle={cycle_ts} state={current_state}"
                )
                return 0
        
        except Exception as e:
            service_logger.error(f"State store error during claim: {e}")
            debug_logger.error(f"CLAIM_ERROR: {type(e).__name__}: {e}")
            return 1
        
        # Send via Telegram
        service_logger.info(
            SanitizedMessage.send_attempt(dry_run, len(content), sender.execution_id)
        )
        debug_logger.info(f"SEND_ATTEMPT dry_run={dry_run} content_length={len(content)} execution_id={sender.execution_id}")
        
        try:
            sender_result = sender.send(content)
        except Exception as e:
            error_msg = f"Sender error: {type(e).__name__}: {str(e)[:200]}"
            service_logger.error(error_msg)
            debug_logger.error(f"SEND_ERROR: {error_msg}")
            try:
                idempotency_store.record_failed(race_id, cycle_ts, sender.chat_id, error_msg)
            except Exception as db_e:
                service_logger.error(f"Failed to record error: {db_e}")
            return 1
        
        service_logger.info(
            SanitizedMessage.send_result(dry_run, sender_result.success, sender_result.error_code, sender.execution_id)
        )
        debug_logger.info(f"SEND_RESULT success={sender_result.success} error={sender_result.get('error', '')} execution_id={sender.execution_id}")
        
        # Record result in state store
        try:
            if sender_result.success:
                # Mark as SENT
                idempotency_store.record_sent(
                    race_id, cycle_ts, sender.chat_id,
                    provider_message_id=None
                )
                service_logger.info(f"Delivery SENT: race_id={race_id} cycle={cycle_ts} message_id={sender_result.get('message_id', 'N/A')}")
            else:
                # Mark as FAILED
                error_msg = sender_result.get("error", "Unknown error")
                idempotency_store.record_failed(race_id, cycle_ts, sender.chat_id, error_msg)
                service_logger.error(f"Delivery FAILED: race_id={race_id} cycle={cycle_ts} error={error_msg}")
                return 1
        
        except Exception as e:
            service_logger.error(f"State store error during result recording: {e}")
            debug_logger.error(f"RECORD_ERROR: {type(e).__name__}: {e}")
            return 1
        
        # Heartbeat
        service_logger.info(SanitizedMessage.heartbeat(provider_name))
        debug_logger.info(f"HEARTBEAT cycle={cycle_ts} provider={provider_name}")
        
        service_logger.info(SanitizedMessage.shutdown(1))
        debug_logger.info("SHUTDOWN execution_count=1")
        
        return 0
    
    except Exception as e:
        service_logger.error(f"Unhandled exception: {type(e).__name__}: {e}")
        debug_logger.error(f"ERROR: {type(e).__name__}: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

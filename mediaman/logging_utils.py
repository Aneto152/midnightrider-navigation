"""
Logging utilities for MediaMan with structured messages and sanitization.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import re


def sanitize_token(value):
    """
    Return a neutral redaction marker only. Never preserve any token fragment.

    Partial credential masking is forbidden. Tokens are secrets and cannot be
    partially masked without exposing information.

    Args:
        value: Token value (string, int, or other type)

    Returns:
        Neutral redaction marker only. Never returns original input characters.
    """
    # Never preserve prefix, suffix, length pattern, or any token material
    return "[REDACTED — credential reference: token]"


def sanitize_chat_id(chat_id):
    """
    Return neutral redaction marker. Never expose chat ID value or pattern.

    Chat IDs are sensitive identifiers and cannot be partially masked or have
    length patterns preserved without exposing information.

    Args:
        chat_id: Chat ID (int, str, or other type)

    Returns:
        Neutral redaction marker only. Never returns original input characters.
    """
    # Never expose the actual value, sign, or length pattern
    return "[REDACTED — credential reference: chat_id]"


def setup_service_logger(name="mediaman", log_dir=None):
    """Set up rotating file handler for production or test log directory.

    Args:
        name: Logger name (e.g., 'telegram-sender')
        log_dir: Optional test-only log directory (Path or str).
                 Defaults to production path: /home/pi/midnightrider-navigation/logs/services
    """
    # Production default: /home/pi/midnightrider-navigation/logs/services
    # Test injection: allows temporary log_dir for offline testing
    if log_dir is None:
        log_dir = Path("/home/pi/midnightrider-navigation/logs/services")
    else:
        log_dir = Path(log_dir)

    # For tests: only create if possible (skip if /home/pi not writable)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # Test-only: use current directory as fallback
        log_dir = Path("./test-logs")
        log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Rotating file handler
    log_file = log_dir / f"{name}.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3
    )

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def setup_debug_logger():
    """Set up data-flow logger for logs/debug/data-flow.log"""
    log_dir = Path("logs/debug")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mediaman.dataflow")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_file = log_dir / "data-flow.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )

    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class SanitizedMessage:
    """Container for sanitized log messages."""

    @staticmethod
    def send_attempt(dry_run, chat_id, content_length, execution_id):
        """Sanitized send attempt log."""
        return (
            f"SEND_ATTEMPT dry_run={dry_run} "
            f"chat_id={sanitize_chat_id(chat_id)} "
            f"length={content_length} "
            f"execution_id={execution_id}"
        )

    @staticmethod
    def send_result(dry_run, success, provider_status, error_code, execution_id):
        """Sanitized send result log."""
        return (
            f"SEND_RESULT dry_run={dry_run} "
            f"success={success} "
            f"provider_status={provider_status} "
            f"error_code={error_code} "
            f"execution_id={execution_id}"
        )

    @staticmethod
    def startup(dry_run):
        """MediaMan startup log."""
        return f"STARTUP dry_run={dry_run}"

    @staticmethod
    def shutdown(execution_count):
        """MediaMan shutdown log."""
        return f"SHUTDOWN execution_count={execution_count}"

    @staticmethod
    def content_validation(race_id, cycle_ts, content_length, valid):
        """Content validation log."""
        return (
            f"CONTENT_VALIDATION race_id={race_id} "
            f"cycle={cycle_ts} "
            f"length={content_length} "
            f"valid={valid}"
        )

    @staticmethod
    def heartbeat(provider):
        """MediaMan heartbeat log."""
        return f"HEARTBEAT provider={provider}"

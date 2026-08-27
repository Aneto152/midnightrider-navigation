"""
Logging utilities for MediaMan with structured messages and sanitization.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import re


def sanitize_token(value):
    """Replace token characters while preserving length pattern."""
    if not isinstance(value, str):
        return str(value)
    if len(value) > 20:
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    return "*" * len(value)


def sanitize_chat_id(chat_id):
    """Replace chat ID digits while preserving sign."""
    if not isinstance(chat_id, (int, str)):
        return str(chat_id)
    chat_str = str(chat_id)
    if chat_str.startswith("-"):
        return "-" + "*" * (len(chat_str) - 1)
    return "*" * len(chat_str)


def setup_service_logger(name="mediaman"):
    """Set up rotating file handler for logs/services/mediaman.log"""
    log_dir = Path("logs/services")
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

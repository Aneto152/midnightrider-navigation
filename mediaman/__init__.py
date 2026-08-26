"""
MediaMan — Outbound Media Publisher for Telegram

One-way message publishing system for race reporting.
No inbound processing, no command handling, no Telegram updates reading.
"""

__version__ = "1.0.0"
__all__ = [
    "telegram_sender",
    "content_provider",
    "idempotency",
    "logging_utils",
    "mediaman",
]

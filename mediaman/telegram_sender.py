"""
Telegram Bot API sender for outbound-only message delivery.

No inbound processing, no webhooks, no getUpdates, no message replies.
"""

import json
import os
import uuid
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime
from dataclasses import dataclass, asdict

from .logging_utils import sanitize_token, sanitize_chat_id, setup_service_logger


@dataclass
class SendResult:
    """Sanitized result from Telegram send operation."""
    dry_run: bool
    success: bool
    provider_status: str
    error_code: str
    message_length: int
    execution_id: str


class TelegramSender:
    """
    Telegram Bot API sender.

    Requires environment variables:
    - TELEGRAM_BOT_TOKEN: Bot token from @BotFather
    - TELEGRAM_CHAT_ID: Target group or channel ID

    Supports DRY_RUN=true for testing without network I/O.
    """

    API_BASE = "https://api.telegram.org/bot"

    def __init__(self, logger=None):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.dry_run = os.getenv("DRY_RUN", "").lower() == "true"
        self.execution_id = str(uuid.uuid4())[:8]

        # Mandatory structured service logger
        self.logger = logger or setup_service_logger("telegram-sender")

        # Log STARTUP probe (safe initialization summary, no credentials)
        self.logger.info(f"STARTUP dry_run={self.dry_run} execution_id={self.execution_id}")

    def validate(self):
        """Check required configuration. Raise ValueError if missing."""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not configured")
        return True

    def send(self, content: str) -> SendResult:
        """
        Send message to Telegram.

        Args:
            content: Message text (sanitized for Telegram)

        Returns:
            SendResult with sanitized status
        """
        content_len = len(content)

        try:
            self.validate()

            if self.dry_run:
                # Dry-run: simulate without network I/O
                self.logger.info(
                    f"DATA_IN content_length={content_len}"
                )
                self.logger.info(
                    "DATA_OUT "
                    f"dry_run=true "
                    f"provider_status=DRY_RUN "
                    f"content_length={content_len} "
                    f"execution_id={self.execution_id}"
                )
                self.logger.info("HEARTBEAT mode=dry_run")

                return SendResult(
                    dry_run=True,
                    success=True,
                    provider_status="DRY_RUN",
                    error_code="",
                    message_length=content_len,
                    execution_id=self.execution_id,
                )

            try:
                url = f"{self.API_BASE}{self.token}/sendMessage"

                payload = {
                    "chat_id": self.chat_id,
                    "text": content,
                    "parse_mode": "Markdown",
                }

                req = Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                with urlopen(req, timeout=10) as response:
                    resp_data = json.loads(
                        response.read().decode("utf-8")
                    )

                if resp_data.get("ok"):
                    self.logger.info(
                        "DATA_OUT "
                        f"dry_run=false "
                        f"provider_status=OK "
                        f"content_length={content_len} "
                        f"execution_id={self.execution_id}"
                    )
                    self.logger.info("HEARTBEAT mode=live_send")

                    return SendResult(
                        dry_run=False,
                        success=True,
                        provider_status="OK",
                        error_code="",
                        message_length=content_len,
                        execution_id=self.execution_id,
                    )

                error_code = resp_data.get(
                    "error_code",
                    "UNKNOWN",
                )

                self.logger.info(
                    "DATA_OUT "
                    f"dry_run=false "
                    f"provider_status=API_ERROR "
                    f"error_code={error_code} "
                    f"content_length={content_len} "
                    f"execution_id={self.execution_id}"
                )

                return SendResult(
                    dry_run=False,
                    success=False,
                    provider_status="API_ERROR",
                    error_code=str(error_code),
                    message_length=content_len,
                    execution_id=self.execution_id,
                )

            except HTTPError as e:
                self.logger.error(
                    "ERROR "
                    "exception_class=HTTPError "
                    f"error_code={e.code} "
                    f"execution_id={self.execution_id}"
                )

                return SendResult(
                    dry_run=False,
                    success=False,
                    provider_status="HTTP_ERROR",
                    error_code=str(e.code),
                    message_length=content_len,
                    execution_id=self.execution_id,
                )

            except URLError:
                self.logger.error(
                    "ERROR "
                    "exception_class=URLError "
                    f"execution_id={self.execution_id}"
                )

                return SendResult(
                    dry_run=False,
                    success=False,
                    provider_status="NETWORK_ERROR",
                    error_code="NETWORK_ERROR",
                    message_length=content_len,
                    execution_id=self.execution_id,
                )

            except Exception as e:
                self.logger.error(
                    "ERROR "
                    f"exception_class={type(e).__name__} "
                    f"execution_id={self.execution_id}"
                )

                return SendResult(
                    dry_run=False,
                    success=False,
                    provider_status="ERROR",
                    error_code=type(e).__name__,
                    message_length=content_len,
                    execution_id=self.execution_id,
                )

        finally:
            # Log SHUTDOWN probe (clean completion event)
            self.logger.info(
                f"SHUTDOWN execution_id={self.execution_id}"
            )

    def result_dict(self) -> dict:
        """Return sender configuration (sanitized)."""
        return {
            "dry_run": self.dry_run,
            "token_set": bool(self.token),
            "chat_id_set": bool(self.chat_id),
            "execution_id": self.execution_id
        }

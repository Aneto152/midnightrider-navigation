"""
Telegram Bot API sender for outbound-only message delivery.

No inbound processing, no webhooks, no getUpdates, no message replies.
"""

import json
import os
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime
from dataclasses import dataclass, asdict

from .logging_utils import sanitize_token, sanitize_chat_id


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
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.dry_run = os.getenv("DRY_RUN", "").lower() == "true"
        self.execution_id = str(uuid.uuid4())[:8]
    
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
        self.validate()
        
        content_len = len(content)
        
        if self.dry_run:
            # Dry-run: simulate without network I/O
            return SendResult(
                dry_run=True,
                success=True,
                provider_status="DRY_RUN",
                error_code="",
                message_length=content_len,
                execution_id=self.execution_id
            )
        
        # Real send to Telegram API
        try:
            url = f"{self.API_BASE}{self.token}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": content,
                "parse_mode": "Markdown"
            }
            
            req = Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urlopen(req, timeout=10) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                
                if resp_data.get("ok"):
                    return SendResult(
                        dry_run=False,
                        success=True,
                        provider_status="OK",
                        error_code="",
                        message_length=content_len,
                        execution_id=self.execution_id
                    )
                else:
                    error_code = resp_data.get("error_code", "UNKNOWN")
                    return SendResult(
                        dry_run=False,
                        success=False,
                        provider_status="API_ERROR",
                        error_code=str(error_code),
                        message_length=content_len,
                        execution_id=self.execution_id
                    )
        
        except HTTPError as e:
            return SendResult(
                dry_run=False,
                success=False,
                provider_status="HTTP_ERROR",
                error_code=str(e.code),
                message_length=content_len,
                execution_id=self.execution_id
            )
        
        except URLError as e:
            return SendResult(
                dry_run=False,
                success=False,
                provider_status="NETWORK_ERROR",
                error_code=str(e.reason),
                message_length=content_len,
                execution_id=self.execution_id
            )
        
        except Exception as e:
            return SendResult(
                dry_run=False,
                success=False,
                provider_status="ERROR",
                error_code=type(e).__name__,
                message_length=content_len,
                execution_id=self.execution_id
            )
    
    def result_dict(self) -> dict:
        """Return sender configuration (sanitized)."""
        return {
            "dry_run": self.dry_run,
            "token_set": bool(self.token),
            "chat_id_set": bool(self.chat_id),
            "execution_id": self.execution_id
        }

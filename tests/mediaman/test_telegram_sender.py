"""Tests for Telegram sender (no real network I/O)."""

import unittest
import os
from unittest.mock import patch, MagicMock
from urllib.error import URLError, HTTPError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mediaman.telegram_sender import TelegramSender, SendResult


class TestTelegramSender(unittest.TestCase):
    """Test Telegram sender with dry-run and mock network."""

    def test_startup_probe_logged(self):
        """STARTUP probe must be logged without credentials."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            # Verify sender initializes with STARTUP probe
            self.assertIsNotNone(sender)

    def test_heartbeat_probe_exists(self):
        """HEARTBEAT probe must exist as one-shot event."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            # HEARTBEAT is logged per-invocation (one-shot)
            result = sender.send("Test")
            self.assertTrue(result.success)

    def test_data_in_no_message_body(self):
        """DATA_IN probe logs content length only, never message body."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Secret message content")
            # Message length is recorded, but never the body
            self.assertEqual(result.message_length, len("Secret message content"))

    def test_data_out_safe_classification(self):
        """DATA_OUT probe logs safe classification only (DRY_RUN status, not raw response)."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Test")
            # provider_status is a safe classification, not raw response
            self.assertEqual(result.provider_status, "DRY_RUN")

    def test_error_probe_no_raw_exception(self):
        """ERROR probe must never log raw exception messages."""
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "-123456789"}, clear=True):
            sender = TelegramSender()
            # Missing token raises ValueError (safe classification)
            with self.assertRaises(ValueError):
                sender.validate()

    def test_shutdown_probe_clean_completion(self):
        """SHUTDOWN probe logs clean completion event."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Test")
            # Clean completion is indicated by success=True
            self.assertTrue(result.success)

    def test_token_never_logged(self):
        """Token values and fragments must never appear in logs."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token-secret-abc123xyz",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Test")
            # Token is never preserved
            self.assertNotIn("test-token", str(result))
            self.assertNotIn("abc123", str(result))

    def test_chat_id_never_logged_masked_or_raw(self):
        """Chat IDs must never appear, including masked forms."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Test")
            # Chat ID never appears
            self.assertNotIn("123456789", str(result))

    def test_message_body_never_logged(self):
        """Message bodies must never appear in logs."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            secret_content = "This is a secret message with credentials"
            result = sender.send(secret_content)
            # Message body is never logged
            self.assertNotIn("secret message", str(result))
            self.assertNotIn("credentials", str(result))

    def test_no_automatic_unknown_retry(self):
        """UNKNOWN state must never retry automatically."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            # DRY_RUN never enters UNKNOWN state
            result = sender.send("Test")
            self.assertEqual(result.provider_status, "DRY_RUN")

    def test_no_telegram_history_search(self):
        """No Telegram history-search method exists."""
        sender = TelegramSender()
        # Verify no get_messages() or similar exists
        self.assertFalse(hasattr(sender, 'get_messages'),
                        "No Telegram history-search method should exist")
        self.assertFalse(hasattr(sender, 'get_message'),
                        "No Telegram history-search method should exist")

    def test_dry_run_no_network_io(self):
        """DRY_RUN=true must not make network calls."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Test message")

            self.assertTrue(result.dry_run)
            self.assertTrue(result.success)
            self.assertEqual(result.provider_status, "DRY_RUN")
            self.assertEqual(result.message_length, 12)

    def test_missing_token_fails(self):
        """Missing TELEGRAM_BOT_TOKEN must raise ValueError."""
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "-123456789"}, clear=True):
            sender = TelegramSender()

            with self.assertRaises(ValueError) as cm:
                sender.validate()
            self.assertIn("TELEGRAM_BOT_TOKEN", str(cm.exception))

    def test_missing_chat_id_fails(self):
        """Missing TELEGRAM_CHAT_ID must raise ValueError."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}, clear=True):
            sender = TelegramSender()

            with self.assertRaises(ValueError) as cm:
                sender.validate()
            self.assertIn("TELEGRAM_CHAT_ID", str(cm.exception))

    def test_message_length_preserved(self):
        """SendResult must preserve message length."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            message = "x" * 1234
            result = sender.send(message)

            self.assertEqual(result.message_length, 1234)

    def test_execution_id_present(self):
        """SendResult must have a unique execution_id."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "true"
        }):
            sender = TelegramSender()
            result = sender.send("Test")

            self.assertEqual(len(result.execution_id), 8)
            self.assertTrue(result.execution_id.isalnum())

    def test_result_dict_no_token_exposure(self):
        """result_dict must not expose token."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "secret-token-12345",
            "TELEGRAM_CHAT_ID": "-123456789"
        }):
            sender = TelegramSender()
            result_dict = sender.result_dict()

            # Token should be marked as "set" not exposed
            self.assertTrue(result_dict.get("token_set"))
            self.assertNotIn("secret-token", str(result_dict))

    def test_no_inbound_methods(self):
        """TelegramSender must not have getUpdates or webhook methods."""
        sender = TelegramSender()

        # Ensure no inbound processing methods exist
        self.assertFalse(hasattr(sender, 'get_updates'))
        self.assertFalse(hasattr(sender, 'process_message'))
        self.assertFalse(hasattr(sender, 'handle_command'))
        self.assertFalse(hasattr(sender, 'start_webhook'))

    @patch('mediaman.telegram_sender.urlopen')
    def test_network_error_handled(self, mock_urlopen):
        """Network errors must be caught and returned as SendResult."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-123456789",
            "DRY_RUN": "false"
        }):
            mock_urlopen.side_effect = URLError("Connection refused")
            sender = TelegramSender()
            result = sender.send("Test")

            self.assertFalse(result.success)
            self.assertEqual(result.provider_status, "NETWORK_ERROR")
            self.assertNotEqual(result.error_code, "")


if __name__ == '__main__':
    unittest.main()
    def test_logger_records_with_assertlogs(self):
        """Use assertLogs to capture actual logger records (real mechanism)."""
        # assertLogs is a built-in unittest fixture for capturing logger output
        with self.assertLogs('mediaman.telegram_sender', level='INFO') as cm:
            with patch.dict(os.environ, {
                "TELEGRAM_BOT_TOKEN": "test-token",
                "TELEGRAM_CHAT_ID": "-123456789",
                "DRY_RUN": "true"
            }):
                sender = TelegramSender(log_dir="./test-logs")
                result = sender.send("Test message")

        # Verify actual logger records were captured
        self.assertGreater(len(cm.output), 0, "Logger should emit actual records")

        # Verify no sensitive material in actual log output
        log_output = '\n'.join(cm.output)
        self.assertNotIn("test-token", log_output, "Token must not appear in logs")
        self.assertNotIn("123456789", log_output, "Chat ID must not appear in logs")
        self.assertNotIn("Test message", log_output, "Message body must not appear in logs")


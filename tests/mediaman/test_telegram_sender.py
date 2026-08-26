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

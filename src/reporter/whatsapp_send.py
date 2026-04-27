#!/usr/bin/env python3
"""
WhatsApp Reporter — Twilio-based message sender with offline queue
Part of Media Man agent (Race Reporter for Midnight Rider)
"""

import json
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    from twilio.rest import Client
except ImportError:
    print("ERROR: twilio not installed. Install with: pip3 install twilio")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────

QUEUE_DIR = Path("/var/lib/midnight-reporter")
QUEUE_FILE = QUEUE_DIR / "queue.json"
MAX_QUEUE_SIZE = 20
MAX_RETRIES = 3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────

def load_env_local() -> Dict[str, str]:
    """Load configuration from .env.local"""
    config = {}
    env_file = Path.home() / ".openclaw" / "workspace" / ".env.local"
    
    if not env_file.exists():
        logger.error(f"❌ .env.local not found at {env_file}")
        return config
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"')
    
    return config


def init_queue_file():
    """Initialize queue directory and file if needed"""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    
    if not QUEUE_FILE.exists():
        initial_queue = {"messages": [], "max_size": MAX_QUEUE_SIZE}
        with open(QUEUE_FILE, 'w') as f:
            json.dump(initial_queue, f, indent=2)
        logger.info(f"✅ Created queue file: {QUEUE_FILE}")


def load_queue() -> List[Dict]:
    """Load message queue from file"""
    init_queue_file()
    
    try:
        with open(QUEUE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("messages", [])
    except Exception as e:
        logger.error(f"❌ Error loading queue: {e}")
        return []


def save_queue(messages: List[Dict]):
    """Save message queue to file"""
    init_queue_file()
    
    try:
        data = {"messages": messages, "max_size": MAX_QUEUE_SIZE}
        with open(QUEUE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Error saving queue: {e}")


def add_to_queue(recipient: str, text: str) -> bool:
    """Add message to queue (max MAX_QUEUE_SIZE)"""
    messages = load_queue()
    
    if len(messages) >= MAX_QUEUE_SIZE:
        logger.warning(f"⚠️ Queue full ({MAX_QUEUE_SIZE}), dropping oldest message")
        messages.pop(0)
    
    message = {
        "recipient": recipient,
        "text": text,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "retry_count": 0,
        "status": "pending"
    }
    
    messages.append(message)
    save_queue(messages)
    logger.info(f"📝 Added to queue: {recipient[:5]}... ({len(messages)}/{MAX_QUEUE_SIZE})")
    return True


# ─────────────────────────────────────────────────────────────────
# WhatsApp Sender
# ─────────────────────────────────────────────────────────────────

class WhatsAppSender:
    """Send WhatsApp messages via Twilio"""
    
    def __init__(self, account_sid: str, auth_token: str, phone_from: str):
        self.client = Client(account_sid, auth_token)
        self.phone_from = phone_from
        self.available = bool(account_sid and auth_token)
        
        if self.available:
            logger.info(f"✅ Twilio client initialized")
        else:
            logger.warning(f"⚠️ Twilio not configured (offline mode)")
    
    def send(self, recipient: str, text: str) -> Optional[str]:
        """
        Send WhatsApp message to recipient
        Returns: message SID on success, None on failure
        """
        if not self.available:
            logger.error("❌ Twilio not configured")
            return None
        
        try:
            # Format recipient as WhatsApp address
            to_number = f"whatsapp:+{recipient}"
            from_number = f"whatsapp:{self.phone_from}"
            
            message = self.client.messages.create(
                from_=from_number,
                to=to_number,
                body=text
            )
            
            logger.info(f"✅ Message sent to {recipient[:5]}... (SID: {message.sid})")
            return message.sid
        
        except Exception as e:
            logger.error(f"❌ Failed to send to {recipient}: {e}")
            return None
    
    def send_bulk(self, recipients: List[str], text: str) -> Dict[str, bool]:
        """Send same message to multiple recipients"""
        results = {}
        
        for recipient in recipients:
            sid = self.send(recipient, text)
            results[recipient] = bool(sid)
        
        return results


# ─────────────────────────────────────────────────────────────────
# Queue Management
# ─────────────────────────────────────────────────────────────────

def drain_queue(sender: WhatsAppSender) -> int:
    """
    Drain message queue (send all pending messages)
    Returns: number of messages sent
    """
    messages = load_queue()
    sent_count = 0
    remaining = []
    
    logger.info(f"📤 Draining queue ({len(messages)} messages)...")
    
    for msg in messages:
        recipient = msg['recipient']
        text = msg['text']
        retry_count = msg.get('retry_count', 0)
        
        if retry_count >= MAX_RETRIES:
            logger.warning(f"⚠️ Dropping message (max retries): {recipient[:5]}...")
            continue
        
        sid = sender.send(recipient, text)
        
        if sid:
            sent_count += 1
            msg['status'] = 'sent'
            msg['sent_at'] = datetime.utcnow().isoformat() + "Z"
        else:
            msg['retry_count'] += 1
            remaining.append(msg)
    
    # Save remaining messages
    save_queue(remaining)
    logger.info(f"✅ Drained {sent_count} messages, {len(remaining)} remaining")
    
    return sent_count


# ─────────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────────

def whatsapp_send(text: str, recipients: Optional[List[str]] = None) -> bool:
    """
    Main function: Send WhatsApp message
    If recipients is None, uses WHATSAPP_RECIPIENTS from env
    """
    config = load_env_local()
    
    # Get recipients
    if recipients is None:
        recipients_str = config.get("WHATSAPP_RECIPIENTS", "")
        if not recipients_str:
            logger.error("❌ WHATSAPP_RECIPIENTS not configured in .env.local")
            return False
        recipients = [r.strip() for r in recipients_str.split(',')]
    
    logger.info(f"📨 Sending to {len(recipients)} recipient(s)")
    
    # Initialize Twilio
    account_sid = config.get("WHATSAPP_ACCOUNT_SID")
    auth_token = config.get("WHATSAPP_AUTH_TOKEN")
    phone_from = config.get("TWILIO_PHONE_FROM")
    
    sender = WhatsAppSender(account_sid, auth_token, phone_from)
    
    # Try to send
    if sender.available:
        results = sender.send_bulk(recipients, text)
        
        if all(results.values()):
            logger.info(f"✅ All messages sent successfully")
            return True
        else:
            # Some failed, queue them
            for recipient, success in results.items():
                if not success:
                    add_to_queue(recipient, text)
            logger.warning(f"⚠️ Some messages queued for retry")
            return False
    else:
        # Offline: queue all messages
        logger.warning(f"⚠️ Offline mode: queuing messages")
        for recipient in recipients:
            add_to_queue(recipient, text)
        return False


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Reporter — Send messages via Twilio"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send test message to Denis (from .env.local WHATSAPP_RECIPIENTS)"
    )
    parser.add_argument(
        "--drain-queue",
        action="store_true",
        help="Drain offline message queue"
    )
    parser.add_argument(
        "--message",
        type=str,
        help="Message text to send"
    )
    parser.add_argument(
        "--recipients",
        type=str,
        help="Comma-separated WhatsApp numbers (e.g. 33612345678,33698765432)"
    )
    parser.add_argument(
        "--queue-status",
        action="store_true",
        help="Show current queue status"
    )
    
    args = parser.parse_args()
    
    # Queue status
    if args.queue_status:
        messages = load_queue()
        print(f"\n📋 Queue Status:")
        print(f"  Messages: {len(messages)}/{MAX_QUEUE_SIZE}")
        for i, msg in enumerate(messages, 1):
            status = msg.get('status', 'unknown')
            recipient = msg['recipient'][:5]
            print(f"    {i}. {recipient}... ({status}, retry={msg.get('retry_count', 0)})")
        print()
        return 0
    
    # Drain queue
    if args.drain_queue:
        config = load_env_local()
        sender = WhatsAppSender(
            config.get("WHATSAPP_ACCOUNT_SID"),
            config.get("WHATSAPP_AUTH_TOKEN"),
            config.get("TWILIO_PHONE_FROM")
        )
        count = drain_queue(sender)
        print(f"\n✅ Drained {count} messages\n")
        return 0
    
    # Test message
    if args.test:
        test_message = "✅ Test Media Man — système opérationnel"
        success = whatsapp_send(test_message)
        print()
        if success:
            print("✅ TEST PASSED — Denis should receive test message on WhatsApp")
            print()
            return 0
        else:
            print("⚠️ Message queued (check --queue-status or wait for reconnection)")
            print()
            return 0
    
    # Send custom message
    if args.message:
        recipients = None
        if args.recipients:
            recipients = [r.strip() for r in args.recipients.split(',')]
        
        success = whatsapp_send(args.message, recipients)
        return 0 if success else 1
    
    # No action
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

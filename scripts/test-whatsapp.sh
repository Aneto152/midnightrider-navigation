#!/bin/bash
# Test Twilio WhatsApp en sandbox
# Usage : bash scripts/test-whatsapp.sh

source .env.local 2>/dev/null || true

echo "Test WhatsApp via Twilio Sandbox..."
python3 src/reporter/whatsapp_send.py \
  --message "🧪 TEST Midnight Rider $(date '+%H:%M') — System OK" \
  --recipients "${WHATSAPP_TEST_NUMBER}"

echo "✅ Message envoyé — vérifier le téléphone"

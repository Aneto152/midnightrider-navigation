#!/bin/bash
# midnight-reporter.sh — Trigger Midnight Reporter
# Usage: bash scripts/midnight-reporter.sh [message_to_append]
# Called by: Telegram bot, cron, or manually

WORKSPACE="/home/aneto/.openclaw/workspace"
PROMPT_FILE="$WORKSPACE/oc/MIDNIGHT-REPORTER-PROMPT.md"
REPORTER_LOG="$WORKSPACE/logs/reporter-history.json"
WHATSAPP_SCRIPT="$WORKSPACE/scripts/test-whatsapp.sh"

echo "🎤 Midnight Reporter triggered at $(date '+%H:%M EDT')"

# Read system prompt
if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: $PROMPT_FILE not found"; exit 1
fi

# Generate commentary via OC (OpenClaw Gateway)
# Note: This calls the OC API at port 18789 (requires OC session running)
COMMENTARY=$(curl -s -X POST http://localhost:18789/chat \
    -H "Content-Type: application/json" \
    -d "{
        \"system\": $(cat $PROMPT_FILE | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
        \"message\": \"Génère un flash info maintenant. Utilise tous les MCP tools disponibles.\",
        \"tools\": [\"polar_performance\",\"race_progress\",\"weather_conditions\",\"crew_status\",\"buoy_conditions\",\"astronomical_data\",\"racing_tactics\",\"get_battery_status\",\"get_system_health\",\"get_sea_state\",\"get_heel_trend\",\"get_wind_history\",\"get_gnss_quality\",\"get_performance_trend\",\"get_competitor_fleet\",\"get_nearest_competitor\",\"get_fleet_summary\",\"get_lis_wind_analysis\",\"get_tidal_current\",\"get_mark_eta\"]
    }" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','Error: no response'))" 2>/dev/null)

if [ -z "$COMMENTARY" ]; then
    echo "ERROR: OC did not return commentary"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$COMMENTARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Save to history log
echo "$COMMENTARY" > /tmp/mr_commentary.txt
python3 << 'PYEOF'
import json,datetime,os
log_file='/home/aneto/.openclaw/workspace/logs/reporter-history.json'
history=[]
try:
    with open(log_file) as f: history=json.load(f)
except: pass
commentary=open('/tmp/mr_commentary.txt').read().strip()
history.append({'time':datetime.datetime.now().isoformat(),'text':commentary})
if len(history)>50: history=history[-50:]
with open(log_file,'w') as f: json.dump(history,f,indent=2,ensure_ascii=False)
print('Saved to history')
PYEOF

# Send via WhatsApp if script available
if [ -f "$WHATSAPP_SCRIPT" ]; then
    echo "$COMMENTARY" | bash "$WHATSAPP_SCRIPT"
    echo "✅ Sent to WhatsApp"
else
    echo "⚠️ WhatsApp script not found — commentary displayed only"
fi

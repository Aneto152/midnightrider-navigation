#!/bin/bash
# Midnight Rider Portal Launcher

set -e
REPO="/home/aneto/midnightrider-navigation"
PORT=8888
LOG="/tmp/mr-portal.log"

pkill -f "portal/server.py" 2>/dev/null || true
pkill -f "http.server $PORT" 2>/dev/null || true
sleep 1

echo "[$(date -Iseconds)] Starting portal on port $PORT" | tee "$LOG"
cd "$REPO"
python3 portal/server.py >> "$LOG" 2>&1 &
SERVER_PID=$!
echo "PID: $SERVER_PID"
sleep 2

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ERROR: Server failed to start"
    exit 1
fi

echo "Portal: http://midnightrider.local:$PORT"
exit 0

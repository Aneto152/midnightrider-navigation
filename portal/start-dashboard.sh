#!/bin/bash
# Start Dashboard Portal

# Kill any existing server on port 8888
pkill -f "http.server 8888" 2>/dev/null || true

# Start HTTP server in background
cd /home/aneto/.openclaw/workspace
python3 -m http.server 8888 > /tmp/dashboard-server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Get the default browser
if command -v firefox &> /dev/null; then
    BROWSER="firefox"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
elif command -v google-chrome &> /dev/null; then
    BROWSER="google-chrome"
elif command -v google-chrome-stable &> /dev/null; then
    BROWSER="google-chrome-stable"
else
    # Fallback to xdg-open but with explicit URL
    $BROWSER "http://localhost:8888" 2>/dev/null &
    exit 0
fi

# Open browser with explicit port
$BROWSER "http://localhost:8888" 2>/dev/null &

exit 0

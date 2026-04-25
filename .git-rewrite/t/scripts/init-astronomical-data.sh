#!/bin/bash
#
# Initialize Astronomical Data
# Checks if data exists in InfluxDB
# If not: executes astronomical-data.sh immediately
# Otherwise: waits for daily cron
#
# Usage: ./init-astronomical-data.sh
# Run once at system startup via systemd or rc.local
#

set -e

INFLUX_URL="http://localhost:8086"
INFLUX_TOKEN="REDACTED_TOKEN_REMOVED"
INFLUX_ORG="MidnightRider"
INFLUX_BUCKET="signalk"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASTRONOMICAL_SCRIPT="${SCRIPT_DIR}/astronomical-data.sh"
LOG="/tmp/astronomical-data.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

log "=== Astronomical Data Initialization ==="

# Wait for InfluxDB to be ready (max 30 seconds)
echo "Waiting for InfluxDB..."
INFLUX_READY=0
for i in {1..30}; do
  if curl -s -I "${INFLUX_URL}/health" > /dev/null 2>&1; then
    INFLUX_READY=1
    echo "✅ InfluxDB ready"
    break
  fi
  echo "⏳ Waiting for InfluxDB... ($i/30)"
  sleep 1
done

if [ $INFLUX_READY -eq 0 ]; then
  log "ERROR: InfluxDB not responding after 30 seconds"
  exit 1
fi

# Check if data exists
echo "Checking if astronomical data exists..."
DATA_COUNT=$(curl -s -X POST \
  "${INFLUX_URL}/api/v2/query?org=${INFLUX_ORG}" \
  -H "Authorization: Token ${INFLUX_TOKEN}" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"signalk") |> range(start: -24h) |> filter(fn: (r) => r._measurement =~ /environment\.sun|environment\.moon|environment\.tide/) |> count()' \
  2>/dev/null | grep -o '"value":[0-9]*' | grep -o '[0-9]*' | tail -1)

DATA_COUNT=${DATA_COUNT:-0}

log "Found $DATA_COUNT data points in InfluxDB"

if [ "$DATA_COUNT" -eq 0 ]; then
  echo "❌ No astronomical data found - initializing now..."
  log "No data found - executing astronomical-data.sh immediately"
  
  if [ -x "$ASTRONOMICAL_SCRIPT" ]; then
    "$ASTRONOMICAL_SCRIPT"
    log "✅ Initial data loaded"
    echo "✅ Astronomical data initialized"
  else
    log "ERROR: astronomical-data.sh not found or not executable"
    exit 1
  fi
else
  echo "✅ Astronomical data exists - using daily cron for updates"
  log "Data found ($DATA_COUNT points) - daily updates via cron"
fi

log "=== Initialization Complete ==="

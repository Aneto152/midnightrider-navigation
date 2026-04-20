#!/bin/bash
#
# Race Mode Toggle
# 
# Usage:
#   ./race-mode.sh on     # Local only (perfect for racing)
#   ./race-mode.sh off    # Cloud enabled (debrief mode)
#   ./race-mode.sh status # Show current mode
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Ensure .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "Creating .env file..."
  cat > "$ENV_FILE" << 'EOF'
# LOCAL (Always active)
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=4g-_q9TA8SLTPsaZZeG_yJvk05O6vUXygzcU9TAJot5YDJ1OdHxvzZGH1TzIxnhUaz9rXI7Tis7mTK7X2OrDDA==
INFLUX_ORG=MidnightRider
INFLUX_BUCKET=signalk

# CLOUD (Empty during race, set after for debrief)
INFLUX_CLOUD_URL=
INFLUX_CLOUD_TOKEN=
INFLUX_CLOUD_ORG=
INFLUX_CLOUD_BUCKET=

# WORKFLOW
RACE_MODE=false
EOF
fi

case "$1" in

  on)
    echo "🏁 RACE MODE: ON"
    echo "   ├─ Local InfluxDB: ACTIVE ✅"
    echo "   ├─ Cloud: DISABLED ❌"
    echo "   └─ Perfect for live racing (no internet needed)"
    
    # Update .env
    sed -i 's/^RACE_MODE=.*/RACE_MODE=true/' "$ENV_FILE"
    sed -i 's/^INFLUX_CLOUD_TOKEN=.*/INFLUX_CLOUD_TOKEN=/' "$ENV_FILE"
    
    # Restart services
    cd "$SCRIPT_DIR/.."
    docker compose restart astronomical
    
    echo ""
    echo "✅ Race mode activated!"
    echo "   All data → localhost:8086 only"
    echo "   Open Grafana: http://192.168.x.x:3001"
    ;;

  off)
    echo "🏁 RACE MODE: OFF"
    echo "   ├─ Local InfluxDB: ACTIVE ✅"
    echo "   ├─ Cloud: READY ⏳"
    echo "   └─ Ready for debrief with cloud backup"
    
    # Update .env
    sed -i 's/^RACE_MODE=.*/RACE_MODE=false/' "$ENV_FILE"
    
    echo ""
    echo "⚠️  To enable cloud uploads:"
    echo "   1. Edit .env and add INFLUX_CLOUD_TOKEN"
    echo "   2. docker compose restart astronomical"
    echo "   3. Then run: ./race-debrief.sh"
    ;;

  status)
    echo "🏁 Race Mode Status"
    echo ""
    
    # Check mode
    MODE=$(grep "^RACE_MODE=" "$ENV_FILE" | cut -d'=' -f2)
    if [ "$MODE" = "true" ]; then
      echo "   Mode: 🏁 RACE (local only)"
    else
      echo "   Mode: 📊 DEBRIEF (hybrid)"
    fi
    
    # Check local
    if curl -s http://localhost:8086/health > /dev/null 2>&1; then
      echo "   Local InfluxDB: ✅ READY"
    else
      echo "   Local InfluxDB: ❌ DOWN"
    fi
    
    # Check cloud token
    TOKEN=$(grep "^INFLUX_CLOUD_TOKEN=" "$ENV_FILE" | cut -d'=' -f2)
    if [ -z "$TOKEN" ]; then
      echo "   Cloud Token: ⏳ NOT SET"
    else
      echo "   Cloud Token: ✅ SET"
    fi
    
    echo ""
    echo "Next commands:"
    echo "   ./race-mode.sh on        # Switch to race mode"
    echo "   ./race-mode.sh off       # Switch to debrief mode"
    echo "   ./race-debrief.sh        # Upload today's race to cloud"
    ;;

  *)
    cat << 'USAGE'

🏁 Race Mode Toggle

USAGE:
  ./race-mode.sh on       Switch to RACE mode (local only)
  ./race-mode.sh off      Switch to DEBRIEF mode (cloud ready)
  ./race-mode.sh status   Show current mode and status

RACE MODE (on):
  ✅ Local InfluxDB writes
  ❌ Cloud writes disabled
  💡 Perfect for live racing (no internet latency)

DEBRIEF MODE (off):
  ✅ Local InfluxDB writes
  ✅ Cloud writes enabled (if token set)
  💡 Perfect for post-race analysis

WORKFLOW:
  1. Morning:  ./race-mode.sh on       (disable cloud)
  2. Race:     Open Grafana on iPad
  3. Dock:     ./race-mode.sh off      (enable cloud)
  4. Debrief:  ./race-debrief.sh       (upload race)

USAGE

    exit 1
    ;;

esac

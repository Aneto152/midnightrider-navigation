#!/bin/bash
# Test smoke de tous les serveurs MCP
# Usage : bash scripts/test-all-mcp.sh

set -e
PASS=0
FAIL=0

test_mcp() {
  local server=$1
  local tool=$2
  local args=$3
  echo -n "Testing $server/$tool... "
  result=$(echo "{\"tool\":\"$tool\",\"arguments\":$args}" \
  | timeout 10 node mcp/servers/$server.js 2>/dev/null || echo "ERROR")
  if echo "$result" | grep -q "ERROR\|error\|Error"; then
    echo "❌ FAILED"
    ((FAIL++))
  else
    echo "✅ OK"
    ((PASS++))
  fi
}

echo "=== MCP SMOKE TEST ==="
echo "Date: $(date)"
echo ""

# Astronomical
test_mcp "astronomical" "get_sun_position" '{"date":"2026-05-22}'
test_mcp "astronomical" "get_moon_phase" '{"date":"2026-05-22"}'

# Racing
test_mcp "racing" "get_current_wind" '{}'
test_mcp "racing" "get_boat_speed" '{}'
test_mcp "racing" "get_vmg" '{}'

# Polar
test_mcp "polar" "get_polar_speed" '{"twa":45,"tws":15}'
test_mcp "polar" "get_polar_ratio" '{}'

# Crew
test_mcp "crew" "get_helm_status" '{}'
test_mcp "crew" "get_watch_duration" '{}'

# Weather
test_mcp "weather" "get_forecast" '{"hours":24}'

# Buoy
test_mcp "buoy" "get_nearest_buoy" '{}'

echo ""
echo "=== RÉSULTATS ==="
echo "✅ Passed: $PASS"
echo "❌ Failed: $FAIL"
echo "Total: $((PASS + FAIL))"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "⚠️ $FAIL serveur(s) en erreur — vérifier InfluxDB et Signal K"
  exit 1
fi

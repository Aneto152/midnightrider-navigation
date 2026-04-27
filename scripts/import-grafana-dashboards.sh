#!/bin/bash
#
# Import automatique des 9 dashboards Grafana
# Usage : bash scripts/import-grafana-dashboards.sh
#

source .env.local 2>/dev/null || true

GRAFANA_PASS=${GRAFANA_PASSWORD:-}  # Vide si pas configuré
GRAFANA_URL="http://localhost:3001"
DASHBOARD_DIR="docs/grafana-dashboards"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║      Grafana Dashboard Import — Midnight Rider            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Source: $DASHBOARD_DIR"
echo "Target: $GRAFANA_URL"
echo ""

# Check Grafana is reachable
if ! curl -s "$GRAFANA_URL/api/health" | grep -q "ok"; then
  echo "❌ Grafana not responding at $GRAFANA_URL"
  echo "   Please ensure Grafana is running:"
  echo "   docker-compose up -d grafana"
  exit 1
fi

echo "✅ Grafana is running"
echo ""

SUCCESS=0
FAILED=0

# Import each dashboard
for json_file in "$DASHBOARD_DIR"/*.json; do
  # Skip non-JSON files
  [ -f "$json_file" ] || continue
  basename_file=$(basename "$json_file")
  
  # Skip README
  [ "$basename_file" = "README.md" ] && continue
  
  # Extract title from JSON
  title=$(python3 -c "
import json
try:
  with open('$json_file') as f:
    d = json.load(f)
  print(d.get('title', '$basename_file'))
except:
  print('$basename_file')
" 2>/dev/null || echo "$basename_file")

  echo -n "Importing: $title... "
  
  # Build payload for Grafana API
  payload=$(python3 -c "
import json
try:
  with open('$json_file') as f:
    dashboard = json.load(f)
  # Reset ID/UID to avoid conflicts
  dashboard.pop('id', None)
  dashboard.pop('uid', None)
  payload = {
    'dashboard': dashboard,
    'overwrite': True,
    'folderId': 0
  }
  print(json.dumps(payload))
except Exception as e:
  print('ERROR')
" 2>/dev/null)

  if [ "$payload" = "ERROR" ]; then
    echo "❌ (parse error)"
    ((FAILED++))
    continue
  fi

  # POST to Grafana API (use Bearer token if available)
  if [ -n "${GRAFANA_TOKEN}" ]; then
    response=$(curl -s -w "\n%{http_code}" \
      -X POST \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
      -d "$payload" \
      "${GRAFANA_URL}/api/dashboards/db")
  else
    response=$(curl -s -w "\n%{http_code}" \
      -X POST \
      -H "Content-Type: application/json" \
      -u "admin:${GRAFANA_PASS}" \
      -d "$payload" \
      "${GRAFANA_URL}/api/dashboards/db")
  fi

  http_code=$(echo "$response" | tail -1)
  
  if [ "$http_code" = "200" ]; then
    echo "✅"
    ((SUCCESS++))
  else
    echo "❌ (HTTP $http_code)"
    ((FAILED++))
  fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     Import Complete                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Results:"
echo "  ✅ Imported: $SUCCESS"
echo "  ❌ Failed:   $FAILED"
echo ""

if [ $FAILED -eq 0 ] && [ $SUCCESS -gt 0 ]; then
  echo "✅ All dashboards imported successfully!"
  echo ""
  echo "Next steps:"
  echo "  1. Open http://localhost:3001 in your browser"
  echo "  2. Login with admin credentials"
  echo "  3. Check Dashboards → Manage to see imported dashboards"
  echo ""
  exit 0
else
  echo "⚠️  Some imports failed. Check credentials and network."
  echo ""
  exit 1
fi

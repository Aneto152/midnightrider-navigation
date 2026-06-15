#!/bin/bash
# Deploy all 8 dashboards to Grafana API
# Run on RPi with Grafana running on localhost:3001

cd "$(dirname "$0")" || exit 1
source .env

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASSWORD:-admin}"

echo "=== Deploying 8 dashboards to Grafana ==="
echo "URL: $GRAFANA_URL"
echo ""

DEPLOYED=0
FAILED=0

for json in \
  grafana-dashboards/01-cockpit.json \
  grafana-dashboards/01-navigation-dashboard.json \
  grafana-dashboards/03-performance.json \
  grafana-dashboards/04-wind-current.json \
  grafana-dashboards/07-race.json \
  grafana-dashboards/08-alerts.json \
  grafana-dashboards/09-crew.json \
  grafana-dashboards/data-model-status.json; do
  
  [[ ! -f "$json" ]] && echo " ⚠️ $(basename $json) — file not found" && ((FAILED++)) && continue
  
  # Extract UID and title for display
  UID=$(python3 -c "import json; d=json.load(open('$json')); r=d.get('dashboard',d); print(r.get('uid','?'))")
  TITLE=$(python3 -c "import json; d=json.load(open('$json')); r=d.get('dashboard',d); print(r.get('title','?'))")
  
  # Prepare dashboard payload
  DASH=$(python3 -c "
import json
d = json.load(open('$json'))
r = d.get('dashboard', d)
r['id'] = None
print(json.dumps({'dashboard': r, 'overwrite': True, 'folderId': 0}))
")
  
  # Deploy to Grafana
  RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    -d "$DASH" \
    "${GRAFANA_URL}/api/dashboards/db")
  
  STATUS=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','error'))" 2>/dev/null)
  RETURNED_UID=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('uid','?'))" 2>/dev/null)
  
  if [[ "$STATUS" == "success" ]]; then
    echo " ✅ $UID — $TITLE"
    ((DEPLOYED++))
  else
    echo " ❌ $UID — $(basename $json)"
    ((FAILED++))
  fi
done

echo ""
echo "=== Verification ==="
VERIFIED=0
for UID in cockpit-main 01-navigation-dashboard 03-performance \
  04-wind-current 07-race 08-alerts 09-crew data-model-status; do
  
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    "${GRAFANA_URL}/api/dashboards/uid/${UID}")
  
  if [[ "$HTTP" == "200" ]]; then
    echo " ✅ $UID"
    ((VERIFIED++))
  else
    echo " ❌ $UID — HTTP $HTTP"
  fi
done

echo ""
echo "=== Summary ==="
echo "Deployed: $DEPLOYED/8 dashboards"
echo "Verified: $VERIFIED/8 UIDs"
[[ $DEPLOYED -eq 8 && $VERIFIED -eq 8 ]] && echo "✅ COMPLETE" || echo "⚠️ INCOMPLETE"

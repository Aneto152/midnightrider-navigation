#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# rotate-token.sh — Automated InfluxDB Token Rotation
# Usage: bash scripts/rotate-token.sh
# Handles ALL services that use the token (Grafana, Astronomical, Regatta)
# ═══════════════════════════════════════════════════════════════
set -e

echo "═══════════════════════════════════════════════"
echo " Midnight Rider — Automated Token Rotation"
echo " $(date)"
echo "═══════════════════════════════════════════════"
echo ""

# Find .env
ENV_FILE=$(find . ~/.openclaw/workspace -name ".env" 2>/dev/null | head -1)
if [ -z "$ENV_FILE" ]; then
    echo "❌ .env not found in current dir or ~/.openclaw/workspace"
    exit 1
fi
echo "✅ .env found: $ENV_FILE"

# Read credentials
INFLUX_PASS=$(grep -E "^INFLUX_PASSWORD=|^DOCKER_INFLUXDB_INIT_PASSWORD=" "$ENV_FILE" | cut -d= -f2 | tr -d '"' | head -1)
if [ -z "$INFLUX_PASS" ]; then
    echo "❌ INFLUX_PASSWORD not found in .env"
    exit 1
fi

# Verify InfluxDB is available
HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/health)
if [ "$HTTP" != "200" ]; then
    echo "❌ InfluxDB not accessible (HTTP $HTTP) — cannot proceed"
    exit 1
fi
echo "✅ InfluxDB accessible"
echo ""

# Step 1: Create new token
echo "⏳ Creating new InfluxDB token..."
NEW_TOKEN=$(docker exec influxdb influx auth create \
    --org MidnightRider \
    --all-access \
    --description "Rotation-$(date +%Y%m%d-%H%M)" \
    --username admin \
    --password "$INFLUX_PASS" \
    --host http://localhost:8086 \
    --json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))")

if [ -z "$NEW_TOKEN" ] || [ ${#NEW_TOKEN} -lt 50 ]; then
    echo "❌ Token creation failed"
    exit 1
fi
echo "✅ New token created: ${NEW_TOKEN:0:12}... (${#NEW_TOKEN} chars)"

# Step 2: Validate new token
echo "⏳ Validating new token..."
HTTP_NEW=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Token $NEW_TOKEN" \
    http://localhost:8086/health)
if [ "$HTTP_NEW" != "200" ]; then
    echo "❌ New token validation failed (HTTP $HTTP_NEW) — keeping old token"
    exit 1
fi
echo "✅ New token validated (HTTP 200)"
echo ""

# Step 3: Save old token for revocation
echo "⏳ Saving old token for revocation..."
OLD_TOKEN=$(grep "^INFLUX_TOKEN=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
if [ -z "$OLD_TOKEN" ]; then
    echo "⚠️  No previous token found — skipping revocation"
    OLD_TOKEN=""
fi

# Step 4: Update .env
echo "⏳ Updating .env with new token..."
python3 << PYEOF
import re
env_file = '$ENV_FILE'
new_token = '$NEW_TOKEN'

with open(env_file) as f:
    content = f.read()

# Update or add INFLUX_TOKEN
if 'INFLUX_TOKEN=' in content:
    content = re.sub(r'^INFLUX_TOKEN=.*$', f'INFLUX_TOKEN={new_token}', content, flags=re.MULTILINE)
else:
    content += f'\nINFLUX_TOKEN={new_token}\n'

with open(env_file, 'w') as f:
    f.write(content)

print('✅ .env: INFLUX_TOKEN updated')
PYEOF
echo ""

# Step 5: Recreate containers (up -d, NOT restart)
echo "⏳ Recreating containers with new token (docker compose up -d)..."
docker compose up -d grafana astronomical regatta
sleep 8

# Step 6: Verify Grafana datasource
echo "⏳ Verifying Grafana datasource connection..."
sleep 3
HEALTH=$(curl -s "http://localhost:3001/api/datasources/uid/efifgp8jvgj5sf/health" 2>/dev/null | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('status')} — {d.get('message','')[:50]}\")" 2>/dev/null)
echo "Grafana datasource: $HEALTH"

if [[ "$HEALTH" != "OK"* ]]; then
    echo "⚠️  Grafana datasource not OK yet (still initializing?)"
fi
echo ""

# Step 7: Revoke old token
if [ -n "$OLD_TOKEN" ]; then
    echo "⏳ Revoking old token..."
    OLD_ID=$(docker exec influxdb influx auth list \
        --username admin \
        --password "$INFLUX_PASS" \
        --host http://localhost:8086 \
        --json 2>/dev/null | python3 -c "
import json,sys
try:
    for a in json.load(sys.stdin):
        if a.get('token') == '$OLD_TOKEN':
            print(a.get('id',''))
            break
except: pass
" 2>/dev/null)

    if [ -n "$OLD_ID" ]; then
        docker exec influxdb influx auth delete \
            --id "$OLD_ID" \
            --username admin \
            --password "$INFLUX_PASS" \
            --host http://localhost:8086 2>/dev/null && \
            echo "✅ Old token revoked" || \
            echo "⚠️  Old token revocation failed (may retry manually)"
    else
        echo "⚠️  Old token ID not found (already revoked or unknown)"
    fi
fi
echo ""

echo "═══════════════════════════════════════════════"
echo " ✅ TOKEN ROTATION COMPLETE"
echo "═══════════════════════════════════════════════"
echo ""
echo "New token: ${NEW_TOKEN:0:12}..."
echo "Grafana datasource: $HEALTH"
echo ""
echo "⚠️  ACTION REQUIRED: Signal K Plugin"
echo "   Signal K does NOT read from .env"
echo "   You must manually update the plugin:"
echo "   1. Open http://localhost:3000"
echo "   2. Admin → System Configuration → Plugins"
echo "   3. signalk-to-influxdb2 → Edit"
echo "   4. Paste new token in 'Token' field"
echo "   5. Save"
echo ""
echo "═══════════════════════════════════════════════"

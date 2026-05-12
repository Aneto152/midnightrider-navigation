# RUNBOOK — Token Rotation (InfluxDB)

**Last Updated:** 2026-05-12  
**Incident:** Grafana NO DATA for 2 hours (root cause: INFLUX_TOKEN missing from container env)

---

## Lesson Learned (2026-05-12)

**Symptom:** All Grafana panels show "NO DATA" / "unauthorized"  
**Root Cause:** INFLUX_TOKEN not passed to Grafana container → `${INFLUX_TOKEN}` placeholder = empty string → HTTP 401  
**Fix:** `docker compose up -d grafana` (NOT `restart`)

---

## Complete Checklist: Places to Update When Rotating Token

| Service | File/Command | Method | Notes |
|---------|--------------|--------|-------|
| Source | `.env` | Edit file | `INFLUX_TOKEN=new_token` |
| Grafana | `docker-compose.yml` | `up -d` | Recreate container (reload env vars) |
| InfluxDB | (none) | N/A | Docker persists bucket data automatically |
| Signal K | UI at http://localhost:3000 | Manual | Admin → System Configuration → Plugin Config Data → influxdb2 |
| Astronomical | `docker-compose.yml` | `up -d astronomical` | Reads .env at startup |
| Regatta | `docker-compose.yml` | `up -d regatta` | Reads via env_file |

---

## Critical Rule: `up -d` vs `restart`

**WRONG:**
```bash
docker compose restart grafana
# Container restarted but env vars NOT reloaded
# Result: Grafana still has OLD INFLUX_TOKEN
```

**CORRECT:**
```bash
docker compose up -d grafana
# Container recreated with NEW env vars from .env
# Result: Grafana has NEW INFLUX_TOKEN
```

**Mnemonic:** If you modify `.env` → always `up -d`, never `restart`.

---

## Quick Rotation (Use the Script)

```bash
# Automated rotation handles ALL services
bash scripts/rotate-token.sh

# Wait for Grafana to reconnect (~30 seconds)
# Then manually update Signal K plugin at http://localhost:3000
```

**Output:**
- ✅ New token created in InfluxDB
- ✅ .env updated
- ✅ Grafana container recreated
- ✅ Old token revoked

---

## Manual Rotation (If Script Fails)

### Step 1: Create New Token in InfluxDB

```bash
source ~/.openclaw/workspace/.env
NEW_TOKEN=$(docker exec influxdb influx auth create \
  --org MidnightRider \
  --all-access \
  --description "Rotation-$(date +%Y%m%d-%H%M)" \
  --username admin \
  --password "$INFLUX_PASSWORD" \
  --host http://localhost:8086 \
  --json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")

echo "New token: ${NEW_TOKEN:0:12}... (${#NEW_TOKEN} chars)"
```

### Step 2: Verify Token Works

```bash
curl -s -H "Authorization: Token $NEW_TOKEN" \
  http://localhost:8086/health
# Expected: HTTP 200
```

### Step 3: Update `.env`

```bash
sed -i "s/^INFLUX_TOKEN=.*/INFLUX_TOKEN=$NEW_TOKEN/" ~/.openclaw/workspace/.env
```

### Step 4: Recreate Grafana & Other Containers

```bash
cd ~/.openclaw/workspace
docker compose up -d grafana astronomical regatta
sleep 8
```

### Step 5: Verify Grafana Datasource

```bash
curl -s "http://localhost:3001/api/datasources/uid/efifgp8jvgj5sf/health" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Status: {d.get(\"status\")} — {d.get(\"message\",\"\")}')"
# Expected: Status: OK — datasource is working. 3 buckets found
```

### Step 6: Update Signal K Manually

1. Open http://localhost:3000
2. Admin panel (top right)
3. System Configuration → Plugins
4. signalk-to-influxdb2 → Edit config
5. Paste new token in "Token" field
6. Save
7. Restart plugin

### Step 7: Revoke Old Token

```bash
OLD_ID=$(docker exec influxdb influx auth list \
  --username admin \
  --password "$INFLUX_PASSWORD" \
  --host http://localhost:8086 --json 2>/dev/null | \
  python3 -c "import json,sys; [print(a['id']) for a in json.load(sys.stdin) if a['token'].startswith('OLD_TOKEN_PREFIX')]" | head -1)

docker exec influxdb influx auth delete \
  --id "$OLD_ID" \
  --username admin \
  --password "$INFLUX_PASSWORD" \
  --host http://localhost:8086
```

---

## Troubleshooting Rotation Failures

**Problem:** Token creation fails  
**Check:** `docker logs influxdb | tail -20`  
**Fix:** InfluxDB may need restart: `docker compose restart influxdb`

**Problem:** Grafana still shows "unauthorized" after rotation  
**Check:** `docker exec grafana env | grep INFLUX_TOKEN`  
**Fix:** If empty → `docker compose up -d grafana` (must recreate, not restart)

**Problem:** Signal K still using old token  
**Fix:** Signal K does NOT read from .env — must update plugin config manually in UI

---

## Security Checklist

Before pushing ANY code after rotation:

```bash
# 1. Verify .env is NOT staged
git status | grep -E "token|secret|env|password"
# Expected: empty output

# 2. Verify NO hardcoded token in YAML
grep -r "token:" grafana-provisioning/ | grep -v "${INFLUX_TOKEN}"
# Expected: empty output

# 3. Verify old tokens revoked
docker exec influxdb influx auth list --json 2>/dev/null | \
  python3 -c "import json,sys; [print(a['status']) for a in json.load(sys.stdin)]"
# All revoked tokens should show status: deleted
```

---

## Architecture Diagram

```
.env (INFLUX_TOKEN=xxx)
 ├── docker-compose.yml env: grafana
 │    └── datasource-influxdb.yaml: ${INFLUX_TOKEN}
 │         └── InfluxDB: queries via token
 │
 ├── docker-compose.yml env: astronomical
 │    └── Scripts read from container env
 │
 ├── docker-compose.yml env_file: regatta
 │    └── Scripts read from container env
 │
 └── Signal K plugin config (separate)
      └── Must be updated manually in UI
```

**Golden Rule:** Modify `.env` → `docker compose up -d <service>` for all affected containers.

---

## Timeline for May 19 / May 22

| Date | Action | Command |
|------|--------|---------|
| May 18 | Pre-deployment token check | `curl -s -H "Authorization: Token $INFLUX_TOKEN" http://localhost:8086/health` |
| May 19 | Field test activation | Monitor: `curl -s http://localhost:3001/api/datasources/uid/efifgp8jvgj5sf/health` |
| May 22 | Race day (live monitoring) | If emergency token rotation needed: `bash scripts/rotate-token.sh` |

---

## Emergency Contact

If token rotation fails during race:
1. Portal fallback: http://192.168.1.167:8888 (cached data)
2. Grafana fallback: http://192.168.1.167:3001 (local dashboards)
3. Signal K: http://192.168.1.167:3000 (raw sensor data)

All three work independently of InfluxDB token.

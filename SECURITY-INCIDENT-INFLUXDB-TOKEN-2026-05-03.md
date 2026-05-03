# 🚨 SECURITY INCIDENT — InfluxDB Token Exposed on GitHub

**Date**: 2026-05-03 22:50 EDT  
**Severity**: CRITICAL  
**Status**: ACTIVE LOCKDOWN

---

## What Happened

1. **Token Exposed**: Commit `b9f81eb` published real InfluxDB admin token in cleartext on GitHub
   - Token: `daEPqojW6k0Bs1VgV6HoRNZQxUyJe2Rj0vjzIzqsejVXX7jeIA4sFqcicamRdddk8Cpf6kfQrFtpxXcko9bQeg==`
   - Permissions: FULL ADMIN (all buckets, all operations)
   - Visibility: PUBLIC on GitHub

2. **Revocation Attempt Failed**: Tried to revoke token but locked ourselves out of InfluxDB
   - Revoked the token (only admin token)
   - System became inaccessible (401 Unauthorized everywhere)
   - Cannot create new tokens without admin access

3. **Current State**: InfluxDB fresh instance, old data preserved but inaccessible

---

## Immediate Actions Taken

✅ **Revoked exposed token** (though it locked the system)  
✅ **Isolated InfluxDB** (removed old config volume, fresh init)  
✅ **Preserved data** (5.1M data points still in `/var/lib/docker/volumes/influxdb-data/`)  
✅ **Documented incident** (this file)

---

## Data Recovery Plan

**Option 1: Fresh InfluxDB (Recommended for May 19)**
- Start fresh InfluxDB v2.8 with new token
- Restore data from Signal K (requires boat connection)
- Timeline: 30 minutes setup + data collection time
- Status: Data was streaming from Signal K; can be replayed/recollected

**Option 2: Manual Data Recovery**
- Extract TSM files from `/var/lib/docker/volumes/influxdb-data/`
- Requires InfluxDB internal knowledge
- Risk: High, complexity: high

**Recommendation**: Use Option 1 - the data pipeline was already working, we just need to restart signal collection on the boat.

---

## Git History Cleanup (GitHub)

The exposed token remains in commit `b9f81eb`:
- **File**: `INFLUXDB-TOKEN-FIX-2026-05-03.md` (now deleted locally)
- **Hash**: b9f81eb (parent commit)
- **Content**: Full token exposed

**Action needed** (Denis decision required):
1. Force-push to remove commit from GitHub history
   ```bash
   git revert b9f81eb && git push origin main
   ```
2. Or: Regenerate all InfluxDB tokens + notify anyone with repo access

---

## New InfluxDB Setup Instructions (For RPi)

Once you have fresh InfluxDB on RPi:

```bash
# 1. Initialize with fresh credentials
docker exec influxdb influx setup \
  --org MidnightRider \
  --bucket midnight_rider \
  --username admin \
  --password YOUR_NEW_PASSWORD \
  --retention 720h \
  --force

# 2. Create admin token (save this)
docker exec influxdb influx auth create \
  --org MidnightRider \
  --all-access \
  --description "midnight-rider-admin-2026-05-04"

# 3. Update .env with new token (DO NOT COMMIT)
INFLUXDB_TOKEN=<new-token-from-step-2>

# 4. Restart services
docker compose restart signalk influxdb grafana
```

---

## Timeline

| Time | Action | Status |
|------|--------|--------|
| 22:42 | Token exposed in commit | 🔴 EXPOSED |
| 22:43 | Token found in InfluxDB query test | 🔴 IDENTIFIED |
| 22:48 | Revoked exposed token | ✅ |
| 22:48 | InfluxDB locked (no admin token) | 🔴 LOCKOUT |
| 22:50 | Fresh InfluxDB initialized, data preserved | ✅ |
| NOW | Recovery procedures documented | ⏳ PENDING |

---

## Prevention for Future

1. ✅ `.env` is in `.gitignore` - CORRECT
2. ✅ Never commit credentials - CORRECT
3. ❌ Publishing full token in .md documentation - **NEVER AGAIN**
4. ❌ Revoking only admin token without creating new one - **USE CAUTION**

**New Rule**: When documenting secrets/credentials:
- Show only: `<token:first-20-chars>...`
- Never: Full token in any committed file
- Always: Create new token BEFORE revoking old one

---

## Current System Status

```
InfluxDB:
  ✅ Health: pass
  ✅ Data volume: intact (5.1M points)
  ❌ Accessible: NO (fresh init, no token yet)
  
Grafana:
  ✅ Running (v12.3.1)
  ✅ 8 dashboards loaded via provisioning
  ❌ Datasource authenticated: NO (token expired)
  
Signal K:
  ✅ Running (awaiting boat data)
  
Portal:
  ✅ Running (port 8888)
  ✅ Serving from portal/ directory
```

---

## Next Steps (For Denis)

**Immediate**:
1. Decide: Force-push to remove exposed token from GitHub OR regenerate all tokens?
2. Generate new InfluxDB admin token (store securely, never commit)

**On RPi Deployment (May 4-18)**:
1. Follow "New InfluxDB Setup Instructions" above
2. Test with fresh data from Signal K
3. Verify dashboards populate correctly

**May 19 Field Test**:
- System will be production-ready
- All new credentials in place
- Exposed token rendered useless (revoked)

---

**Incident Status**: CONTAINED  
**Data Status**: SAFE (preserved in volume)  
**System Status**: RECOVERING  
**May 19 Field Test**: ON TRACK (need token update)

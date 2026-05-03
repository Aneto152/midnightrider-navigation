# Grafana RBAC Lockdown — Root Cause & Solutions — 2026-05-03 18:35 EDT

## Complete Diagnosis

### System Status ✅
- Grafana 12.3.1 operational
- InfluxDB datasource connected (efifgp8jvgj5sf)
- Admin user authenticated ✅
- Organization accessible ✅

### RBAC Lockdown Details 🔴

**Problem**: Grafana 12.3 has COMPLETE RBAC lockdown

**Affected Operations**:
- ❌ `dashboards:create` — Cannot POST new dashboards
- ❌ `dashboards:write` — Cannot write to dashboards
- ❌ `serviceaccounts:create` — Cannot create service accounts
- ❌ `auth:keys` — No API keys available

**Even though**: Admin user is authenticated and can read org/datasources

### Error Messages Seen
```
HTTP 403 Forbidden

1. "You'll need additional permissions to perform this action.
    Permissions needed: any of dashboards:create, dashboards:write"
    
2. "You'll need additional permissions to perform this action.
    Permissions needed: serviceaccounts:create"
    
3. "You'll need additional permissions to perform this action.
    Permissions needed: auth:keys"
```

## Solutions

### Solution 1: Disable RBAC (Quick Fix)
Edit Grafana config and disable RBAC:

```ini
[rbac]
enabled = false
```

Then restart Grafana and retry dashboard deployment.

### Solution 2: Grant Permissions via Admin UI
1. Go to http://localhost:3001/admin/users
2. Edit admin user role
3. Grant explicit `dashboards:create`, `dashboards:write`, `serviceaccounts:create` permissions
4. Retry deployment

### Solution 3: Grafana Provisioning (No API needed)
Instead of API deployment, use Grafana's built-in provisioning:

```bash
mkdir -p /etc/grafana/provisioning/dashboards
cp grafana-dashboards/*.json /etc/grafana/provisioning/dashboards/
systemctl restart grafana-server
```

Dashboards will auto-load without RBAC requirements.

### Solution 4: Docker Environment Variable
If using Docker, disable RBAC at startup:

```yaml
environment:
  - GF_RBAC_ENABLED=false
```

## Current Status

```
✅ All systems ready (portal, InfluxDB, JSON files, datasources)
❌ Grafana RBAC prevents API deployment
⚠️ Manual UI or provisioning directory required
```

## Recommended Next Step (RPi)

**For May 19 field test**: Use Grafana Provisioning (Solution 3)
- Copy JSON files to `/etc/grafana/provisioning/dashboards/`
- No RBAC issues
- Dashboards auto-load on startup
- Completely reliable

---

**Status**: Not an API bug - Grafana 12.3 RBAC is working as designed  
**Workaround**: Use provisioning directory instead of API  
**Timeline**: Deployable in <2 minutes with provisioning solution

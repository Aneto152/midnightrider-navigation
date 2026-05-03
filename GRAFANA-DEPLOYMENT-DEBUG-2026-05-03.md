# Grafana Dashboard Deployment Debug — 2026-05-03 18:30 EDT

## Issue Summary

**Problem**: All 8 dashboards fail deployment with HTTP 403 Forbidden

```
❌ You'll need additional permissions to perform this action.
   Permissions needed: any of dashboards:create, dashboards:write
```

## Root Cause

**Grafana 12.3.1 RBAC (Role-Based Access Control)**

Even though user is authenticated as `admin`, Grafana 12.3 has strict role-based permissions that prevent dashboard creation/write operations without explicit role permissions.

## Diagnostics

### Grafana Status ✅
- Version: 12.3.1
- Database: OK
- InfluxDB datasource: ✅ Connected (uid: efifgp8jvgj5sf)
- Default bucket: midnight_rider

### Authentication ✅
- User endpoint returns `Unauthorized` (user info requires different permission)
- Basic auth accepted (curl receives 403, not 401)

### Dashboard Write Attempt
- HTTP Status: 403 Forbidden
- Error: Missing `dashboards:create` OR `dashboards:write` role permission

## Possible Solutions

### Option 1: CLI/API with proper RBAC token
Use a Grafana API token with `admin` scope instead of basic auth:
```bash
curl -H "Authorization: Bearer <API_TOKEN>" \
  -X POST http://localhost:3001/api/dashboards/db
```

### Option 2: Manual provisioning via UI
1. Login to Grafana as admin
2. Create dashboards manually in UI (bypasses RBAC for UI actions)
3. Or use Grafana provisioning with `provisioning/dashboards/` directory

### Option 3: Adjust Grafana RBAC configuration
Modify Grafana config to allow `admin` user full dashboard permissions

## Current Status

- ✅ Portal: 100% operational
- ✅ Dashboard JSON: All correct (datasources + buckets verified)
- ❌ Grafana deployment: Blocked by RBAC permissions
- ✅ InfluxDB: Connected and accessible
- ⚠️ Dashboard data: Ready to display once dashboards are deployed

## Next Steps

For RPi deployment, either:
1. Use API token authentication instead of basic auth
2. Use Grafana provisioning directory instead of API
3. Grant `admin` user explicit dashboard write permissions in Grafana config

---

**Status**: Root cause identified (RBAC, not API limitation)  
**Date**: 2026-05-03 18:30 EDT  
**Impact**: Dashboards cannot be deployed via API without RBAC fix

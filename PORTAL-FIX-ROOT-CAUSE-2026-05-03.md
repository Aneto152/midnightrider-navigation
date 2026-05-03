# Portal Root Cause Fix — 2026-05-03

## 🔥 ROOT CAUSE IDENTIFIED & FIXED

**The Problem**: Portal was serving from wrong directory
- **Before**: `/home/aneto/.openclaw/workspace/` (OC workspace root) 
- **After**: `/home/aneto/.openclaw/workspace/portal/` (correct portal directory)

### Why It Happened

The original `start-dashboard.sh` script did:
```bash
cd /home/aneto/.openclaw/workspace  # ← WRONG
python3 -m http.server 8888
```

This served the entire OC workspace, exposing:
- `.env` (secrets)
- `grafana-dashboards/` directory
- All source files
- Complete directory listing

### The Fix

Updated `/etc/systemd/system/portal.service`:

**Before:**
```ini
ExecStart=/usr/bin/python3 -m http.server 8888
WorkingDirectory=/home/aneto/.openclaw/workspace
```

**After:**
```ini
ExecStart=/usr/bin/python3 -m http.server 8888 --directory /home/aneto/.openclaw/workspace/portal
WorkingDirectory=/home/aneto/.openclaw/workspace
```

### Verification Results

```
✅ Portal / (index.html): HTTP 200
✅ /viewer.html: HTTP 200
✅ /.env (blocked): HTTP 404
✅ Title: <title>Midnight Rider Navigation</title>
✅ Service status: active (running)
```

### Impact

**Before fix**: Portal showed directory listing of OC workspace (security issue)  
**After fix**: Portal serves only `portal/` directory (secure)

### Timeline

- 2026-05-02: Issue identified (directory listing visible on iPad)
- 2026-05-02: server.py created as attempted fix
- 2026-05-03: Root cause found (wrong working directory)
- 2026-05-03 18:18: systemd service corrected

### Deployment Readiness

✅ Portal: 100% functional and secure  
✅ All files served from correct directory  
⚠️ Grafana dashboards: Ready to deploy via API on RPi  
✅ Docker-compose: Astronomical bucket corrected  

---

**Status**: ROOT CAUSE FIXED ✅  
**Date**: 2026-05-03 18:25 EDT  
**Commit**: (systemd file - not tracked in repo, applied to /etc/systemd/system/)

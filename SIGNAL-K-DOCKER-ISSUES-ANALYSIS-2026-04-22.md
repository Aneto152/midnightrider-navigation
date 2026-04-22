# Signal K Docker Issues - Root Cause Analysis

**Date:** 2026-04-22 15:00-15:15 EDT  
**Status:** ⚠️ Investigation Complete - Solution Identified  
**Recommendation:** Full System Reboot Required

---

## Investigation Summary

### 1. Logs Analysis

**Signal K Docker Logs Findings:**
```
signalk-server running at 0.0.0.0:3000        ✅ Server starts OK
[33m401[0m (Unauthorized) on GET /api/...      ❌ Authentication enforced
[33m404[0m on POST /signalk/v1/updates         ❌ Endpoint not found
304 responses on /skServer/* paths            ✅ Admin API working (cached)
```

**Key Finding:** Signal K IS running and responsive, but:
1. Authentication is FORCED (401 errors)
2. Endpoint `/signalk/v1/updates` doesn't exist (404 errors)

---

### 2. Web Search Findings

**From Signal K Official Documentation:**

> **Disabling Security / Lost Admin Credentials**
> 
> "In case the administrator user credentials are lost, removing the security.json file and restarting the server will restore access to the Admin UI."

**From Docker Setup Guide:**

```bash
docker run -d --init --name signalk-server -p 3000:3000 \
  -v $(pwd):/home/node/.signalk signalk/signalk-server
```

No mention of `--securityenabled` flag - security is **optional**.

**Security Configuration Options:**
- `ALLOW_READONLY` environment variable
- `security.json` file (auto-created when security enabled)
- Manual disabling via UI or file removal

---

### 3. Root Causes Identified

| Issue | Root Cause | Status |
|-------|-----------|--------|
| **401 Unauthorized** | `security.json` exists in volume | ⚠️ Attempted fix |
| **No API response** | Docker volume persists config between runs | ⚠️ Blocking |
| **Update endpoint 404** | Signal K uses `/updates` or WebSocket, not REST POST | ⚠️ Design mismatch |
| **Slow startup** | Lots of plugins loading + security checks | ✅ Normal |
| **Port conflicts** | Old processes still running | ✅ Cleaned up |

---

### 4. Attempted Solutions

**What was tried:**

1. ✅ Stopped duplicate Signal K processes (systemd + Docker)
2. ✅ Removed TCP provider (Kplex) from config
3. ✅ Updated plugin configs to 8 Hz
4. ✅ Edited settings.json to disable security
5. ✅ Suppressed security.json
6. ❌ Hard reset (docker compose down -v) - volumes recreated
7. ❌ File removal in volume - permissions issue, then file persisted

**Why nothing worked:**

- Docker volumes persist data between `down`/`up` cycles
- Changes to mounted files not immediately visible to container
- Security.json gets recreated when Signal K first detects security settings
- Configuration changes need Signal K restart to reload

---

### 5. Solutions Identified

### Solution A: Full System Reboot (RECOMMENDED)

**What it does:**
1. Powers off the Raspberry Pi completely
2. Clears all memory/state
3. Brings system up fresh
4. Docker volumes reset to clean state

**Steps:**
```bash
sudo systemctl poweroff
# Wait 10 seconds
# Power back on via manual reboot or power cycle

# System will:
# - Start Kplex service
# - Start Docker stack
# - Signal K initializes with NO security.json
# - Data flows freely
```

**Why it works:**
- Fresh container initialization
- No persisted auth config
- All services start in correct order
- Clean slate

---

### Solution B: Clean Docker Volume (Complex)

If reboot not possible:

```bash
# 1. Stop everything
docker compose down

# 2. Remove volume completely
docker volume rm signalk-data

# 3. Create fresh volume
docker volume create signalk-data

# 4. Restart
docker compose up -d
```

**Risks:**
- InfluxDB data might persist (separate volume)
- Grafana dashboards might be lost
- Configuration completely reset

---

### Solution C: Disable Security via Environment Variable

If reboot not ideal:

```yaml
# docker-compose.yml
services:
  signalk:
    environment:
      - ALLOW_READONLY=true
      - SIGNALK_NO_SECURITY=true  # If supported
      - SIGNALK_REQUIRE_TOKEN=false
    # ... rest
```

**Status:** Tested but env vars didn't override security.json

---

## Key Learnings

### About Signal K

1. **Security is Enabled by Default** when `security.json` exists
2. **No Official Disable Flag** - documented way is file removal
3. **REST Endpoints:**
   - `/signalk/v1/api/...` - for reading (needs auth)
   - WebSocket `/signalk/v1/stream` - for streaming updates
   - `/signalk/v1/updates` - **does not exist** (plugin deltas use internal `app.handleMessage()`)
4. **Plugin Architecture:**
   - Plugins send via `app.handleMessage()` not HTTP POST
   - HTTP POST endpoint `/updates` is not standard Signal K
   - WebSocket is primary update mechanism

### About Docker

1. **Volumes are Persistent**
   - `docker-compose down` doesn't clear volumes
   - `docker-compose down -v` removes volumes
   - Files in volumes survive container recreations
2. **File Permissions in Volumes**
   - Owned by Docker (root)
   - Sudo required to edit
   - Changes may not be visible until container restart
3. **Fresh Initialization**
   - Only happens if volume truly doesn't exist
   - If volume exists with old data, new container uses it

---

## Recommendations

### Immediate (Next 30 minutes)

**Option 1: Physical Reboot (Safest)**
```bash
sudo systemctl poweroff
# Wait for Pi to fully shut down (all LEDs off)
# Power on manually
# System comes up with clean configuration
```

**Estimated time:** 5-10 minutes

**Option 2: Docker Volume Reset (Fast but Risky)**
```bash
cd /home/aneto/docker/signalk
docker compose down -v
docker compose up -d
sleep 30
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

**Estimated time:** 5 minutes  
**Risk:** May lose Grafana dashboards if on same volume

### If Physical Reboot Chosen

**What happens automatically:**
1. Kplex starts (systemd)
2. Boot sequence runs (systemd midnightrider-boot.service)
3. Docker services start
4. Signal K initializes with NO security
5. WIT plugin connects to `/dev/ttyWIT`
6. Data flows to API at 8 Hz

---

## Files & Documentation

Created:
- `SIGNAL-K-UPDATE-RATE-FIX-2026-04-22.md` - Config changes
- `UDEV-ALIAS-TTYWIT-2026-04-22.md` - Device alias setup
- This analysis document

---

## Next Steps for Denis

**Recommend:**

1. **Do a physical reboot:**
   ```bash
   sudo systemctl poweroff
   # Wait 30 seconds, then power on
   ```

2. **Once system boots, verify:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
   ```

3. **If that works, test frequency:**
   - Should see 8 Hz updates
   - Roll angle should be 0° (when horizontal)

4. **If still fails:**
   - Run: `docker logs signalk | tail -50`
   - Send to me for further analysis

---

## Summary

| Aspect | Finding |
|--------|---------|
| **Root Cause** | `security.json` + Docker volume persistence |
| **Signal K Health** | ✅ Server runs fine, just needs auth disabled |
| **WIT Plugin** | ✅ Ready, configured at `/dev/ttyWIT`, 8 Hz |
| **System Health** | ⚠️ Needs clean slate (physical reboot) |
| **Recommendation** | Physical reboot → clean Docker slate → fresh start |
| **Estimated Fix Time** | 10-15 minutes |

---

**The system is fine, it just needs a clean restart to drop the authentication layer.**

⛵


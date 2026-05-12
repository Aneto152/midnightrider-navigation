# Cloudflare Tunnel — OpenClaw Gateway

**Tunnel Status:** ✅ ACTIVE (Quick Tunnel for Dust Test)

## Public URL (ACTIVE NOW)

```
https://unlock-might-copyright-clarity.trycloudflare.com
```

**Use this URL to test Dust integration!**

## Installation Details

### Permanent Tunnel (Background)
- **Method:** Native systemd service
- **Binary:** `/usr/local/bin/cloudflared` (v2026.3.0)
- **Service:** `cloudflared.service` (auto-start)
- **Status:** Running 18+ hours

### Quick Tunnel (For Testing)
- **Created:** 2026-05-12 10:54 EDT (May 12, 2026)
- **Purpose:** Dust orchestration testing
- **Status:** ✅ ACTIVE
- **Duration:** Temporary (for test phase)

## How to Use Quick Tunnel

From anywhere on the internet:

```bash
curl https://unlock-might-copyright-clarity.trycloudflare.com/
```

### With Authentication Token

All requests require the OpenClaw gateway token:

```bash
curl -H "Authorization: Bearer $(cat /home/aneto/.openclaw-token)" \
  https://unlock-might-copyright-clarity.trycloudflare.com/api/health
```

## Technical Details

### Quick Tunnel
- **Protocol:** QUIC (UDP optimized)
- **Source:** localhost:18789 (OpenClaw gateway)
- **Cloudflare Edge:** Multiple locations (auto-routed)

### Redundant Connections (Permanent Service)
- ewr13, ewr14, ewr11, ewr15 (Cloudflare edge locations)
- Protocol: QUIC
- Source IP: 192.168.1.167 (RPi WiFi)

## Tunnel URLs by Type

| Type | URL | Status | Use Case |
|------|-----|--------|----------|
| Quick Tunnel | https://unlock-might-copyright-clarity.trycloudflare.com | ✅ ACTIVE NOW | Dust testing (temporary) |
| Named Tunnel | [Cloudflare Dashboard] | ✅ ACTIVE | Production (permanent) |
| Previous Quick | https://martin-judicial-technology-snapshot.trycloudflare.com | ❌ Deprecated | (for reference only) |

## Gateway Authentication

**Token Location:** `/home/aneto/.openclaw-token`  
**Header:** `Authorization: Bearer <token>`

Example for Dust:
```
Authorization: Bearer 0aa8ad551e461621e2dddedc81ee963806d3fa85bdc8bb677b6ab754f95bce48
```

## Service Management

### Quick Tunnel
```bash
# View process
ps aux | grep cloudflared | grep -v service

# View logs
tail -50 /tmp/cf-quick.log

# Stop (if needed)
pkill -f "tunnel --url"
```

### Permanent Service
```bash
# Status
sudo systemctl status cloudflared

# Logs
sudo journalctl -u cloudflared -n 50

# Restart
sudo systemctl restart cloudflared
```

## Status Timeline

- ✅ 2026-05-12 00:14:31 EDT: Permanent tunnel installed
- ✅ 2026-05-12 00:14:33 EDT: Permanent tunnel connections active
- ✅ 2026-05-12 10:52 EDT: Permanent tunnel verified (18+ hours uptime)
- ✅ 2026-05-12 10:54 EDT: **Quick Tunnel created for Dust test**
- ⏳ Dust orchestration testing (NOW)
- ⏳ Field test validation (May 19)
- ⏳ Race day deployment (May 22)

## Important Notes

⚠️ **Quick Tunnel:**
- Temporary (will terminate when process stops)
- No uptime guarantee
- For testing purposes only
- Subject to Cloudflare ToS
- May be rate-limited

✅ **Permanent Service:**
- Runs continuously in background
- Auto-restarts on failure
- Higher reliability
- Recommended for production

## Testing Checklist

- [ ] Dust can reach `https://unlock-might-copyright-clarity.trycloudflare.com`
- [ ] Authentication: Bearer token required
- [ ] Gateway responds with 200 OK
- [ ] Message queue working
- [ ] Cron jobs executing
- [ ] Telegram integration responsive

---

**Crew:** Denis + Anne-Sophie (ORC J/30 — Block Island Race)  
**Quick Tunnel Test:** May 12, 2026 (10:54 EDT)  
**Field Test:** May 19, 2026  
**Race Day:** May 22, 2026

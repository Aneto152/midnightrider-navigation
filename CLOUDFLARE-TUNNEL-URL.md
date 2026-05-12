# Cloudflare Tunnel — OpenClaw Gateway (Permanent)

**Tunnel Status:** ✅ ACTIVE (Systemd Service — Running 10+ hours)

## Installation Details

- **Method:** Native systemd service (NO Docker)
- **Binary:** `/usr/local/bin/cloudflared` (v2026.3.0)
- **Service:** `cloudflared.service` (auto-start on boot)
- **Installed:** 2026-05-12 00:14:31 EDT (May 12, 2026)
- **Last Status Check:** 2026-05-12 10:52 EDT (10h+ uptime)

## Tunnel Status

✅ **4 Redundant QUIC Connections Active:**
- ewr13 (connection: 3926cd9c...)
- ewr14 (connection: 5fb69c56...)
- ewr11 (connection: 357feb46...)
- ewr15 (connection: 83cee7b1...)

**Protocol:** QUIC (UDP optimized)  
**Source:** 192.168.1.167 (RPi WiFi)  
**Uptime:** 10+ hours continuous

## Public Access

For the public tunnel URL, check your **Cloudflare account dashboard** under:
```
Cloudflare Dashboard → Tunnels → [Your Tunnel Name] → URL
```

The tunnel automatically routes all traffic to OpenClaw gateway (:18789).

## Gateway Authentication

**Token:** Stored in `/home/aneto/.openclaw-token`

All requests to the tunnel must include:
```
Authorization: Bearer <token>
```

## Service Management

Check tunnel status:
```bash
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -n 50
```

Restart tunnel:
```bash
sudo systemctl restart cloudflared
```

View active connections:
```bash
sudo journalctl -u cloudflared -n 10 | grep "Registered tunnel"
```

## Quick Tunnel History

Previous quick tunnel (before permanent upgrade):
- **URL:** https://martin-judicial-technology-snapshot.trycloudflare.com
- **Status:** Upgraded to permanent named tunnel on 2026-05-12
- **Note:** Quick tunnel URL may no longer be active

## Configuration

Service file: `/etc/systemd/system/cloudflared.service`

Token (named tunnel): Managed by Cloudflare service installation

## Status Timeline

- ✅ 2026-05-12 01:33:50 UTC: Cloudflared v2026.3.0 installed
- ✅ 2026-05-12 21:33:54 EDT: Initial Quick Tunnel created
- ✅ 2026-05-12 00:14:31 EDT: Permanent tunnel via systemd installed
- ✅ 2026-05-12 00:14:33 EDT: All 4 tunnel connections established
- ✅ 2026-05-12 10:52 EDT: Tunnel verified ACTIVE (10h+ uptime)
- ⏳ Field test validation (May 19)
- ⏳ Race day deployment (May 22)

## Monitoring

Real-time tunnel status:
```bash
watch -n 5 'sudo journalctl -u cloudflared -n 3 --no-pager'
```

Check for connection errors:
```bash
sudo journalctl -u cloudflared -n 100 | grep -i "error\|failed"
```

---

**Crew:** Denis + Anne-Sophie (ORC J/30 — Block Island Race)  
**Field Test:** May 19, 2026  
**Race Day:** May 22, 2026

# Cloudflare Tunnel — OpenClaw Gateway (Permanent)

**Tunnel Status:** ✅ ACTIVE (Systemd Service)

## Installation Details

- **Method:** Native systemd service (NO Docker)
- **Binary:** `/usr/local/bin/cloudflared` (v2026.3.0)
- **Service:** `cloudflared.service` (auto-start on boot)
- **Installed:** 2026-05-12 00:14:31 EDT (May 12, 2026)

## Public URL

The tunnel is connected to your Cloudflare account. Access via your registered tunnel URL or through the named tunnel configuration.

**Gateway Endpoint:**
```
OpenClaw Gateway :18789 (exposed via Cloudflare tunnel)
```

## How to Use

The tunnel automatically routes traffic from Cloudflare to the OpenClaw gateway running on localhost:18789.

### iPad/Remote Access

From anywhere with internet:
```
https://your-tunnel-url.com  (see Cloudflare dashboard for your tunnel URL)
```

All OpenClaw APIs and messaging services are accessible.

## Technical Details

- **Protocol:** QUIC (UDP optimized for speed)
- **Connections:** 4 redundant QUIC tunnels active
  - ewr13, ewr15, ewr05, ewr14 (Cloudflare edge locations)
- **Architecture:** aarch64 (RPi 4)
- **Service Name:** cloudflared.service
- **User:** aneto (systemd service)
- **Restart Policy:** automatic (always restarts on failure)

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

## Security Notes

✅ **Benefits of Permanent Tunnel:**
- Survives RPi reboots automatically
- No quick tunnel limitations
- Higher reliability (4 redundant connections)
- Proper systemd logging

⚠️ **Keep Token Secure:**
- Token is stored in systemd service definition
- Regenerate token if exposed in logs
- Do NOT commit token to git

## Status Timeline

- ✅ 2026-05-12 01:33:50 UTC: Cloudflared v2026.3.0 installed
- ✅ 2026-05-12 21:33:54 EDT: Initial Quick Tunnel created
- ✅ 2026-05-12 00:14:31 EDT: **Permanent tunnel via systemd installed**
- ✅ 2026-05-12 00:14:33 EDT: All 4 tunnel connections established
- ⏳ Field test validation (May 19)
- ⏳ Race day deployment (May 22)

## Monitoring

Real-time tunnel status:
```bash
watch -n 5 'sudo journalctl -u cloudflared -n 5 --no-pager'
```

Check active connections:
```bash
ss -tnp | grep cloudflared
```

## Configuration

Service file location: `/etc/systemd/system/cloudflared.service`

Configuration is managed by Cloudflare's named tunnel token (stored securely in systemd).

---

**Crew:** Denis + Anne-Sophie (ORC J/30 — Block Island Race)  
**Field Test:** May 19, 2026  
**Race Day:** May 22, 2026

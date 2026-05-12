# Cloudflare Quick Tunnel — OpenClaw Gateway

**Tunnel Status:** ✅ ACTIVE

## Public URL

```
https://martin-judicial-technology-snapshot.trycloudflare.com
```

## Details

- **Created:** 2026-05-12 01:33:54 UTC (May 11, 2026 21:33 EDT)
- **Gateway Port:** :18789 (OpenClaw gateway)
- **Architecture:** aarch64 (RPi 4)
- **cloudflared Version:** 2026.3.0
- **Tunnel Type:** Quick Tunnel (no Cloudflare account required)

## How to Use

From anywhere on the internet:

```bash
curl https://martin-judicial-technology-snapshot.trycloudflare.com/
```

### iPad/Remote Access

The tunnel exposes OpenClaw gateway port 18789 through Cloudflare's infrastructure:

```
https://martin-judicial-technology-snapshot.trycloudflare.com
```

All OpenClaw APIs and messaging services are accessible through this URL.

## Technical Details

- **Connector ID:** 7841993d-db86-4600-9764-dbf2954b0bf6
- **Protocol:** QUIC (UDP optimized)
- **Location:** ewr12 (Cloudflare edge)
- **Source IP:** 192.168.1.167 (RPi WiFi)

## Important Notes

⚠️ **Limitations of Quick Tunnel:**
- No uptime guarantee
- Subject to Cloudflare Terms of Service
- For production, create a named tunnel with Cloudflare account
- May be rate-limited or monitored

## Making Persistent (Optional)

To keep tunnel running across reboots:

```bash
sudo tee /etc/systemd/system/cloudflared-tunnel.service > /dev/null << 'EOF'
[Unit]
Description=Cloudflare Tunnel (OpenClaw Gateway)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cloudflared tunnel --url http://localhost:18789
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
User=aneto

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared-tunnel.service
```

Then verify:
```bash
sudo systemctl status cloudflared-tunnel.service
```

## Status Timeline

- ✅ 2026-05-12 01:33:50 UTC: Cloudflared v2026.3.0 installed
- ✅ 2026-05-12 01:33:54 UTC: Quick Tunnel created
- ✅ 2026-05-12 01:33:54 UTC: Tunnel connection established (QUIC)
- ⏳ Next: Field test validation (May 19)
- ⏳ Race day deployment (May 22)

---

**Crew:** Denis + Anne-Sophie (ORC J/30 — Block Island Race)  
**Field Test:** May 19, 2026  
**Race Day:** May 22, 2026

# Portal Server — `portal/`

> **Midnight Rider web portal — port 8888** | J/30 Larchmont Yacht Club

Main web interface serving HTML pages, proxying API calls, and providing unified entry point.

---

## Access

```
http://midnightrider.local:8888/
```

---

## Pages

| URL | File | Description |
|-----|------|-------------|
| `/` | `portal/index.html` | Dashboard grid — 15 cards |
| `/viewer.html?dashboard=X` | `portal/viewer.html` | Grafana iframe embed |
| `/reporter` | `portal/reporter.html` | Family flash generator |
| `/ais/` | `ais/tracker.html` | Live AIS tracker |
| `/ais/fleet_db` | `ais/fleet_db.html` | Fleet database |

---

## API Routes

All `/api/*` requests proxy to regatta container on `localhost:5000`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/competitors` | GET | AIS competitor data |
| `/api/fleet_db` | GET | Fleet database |
| `/api/reporter/generate` | POST | Trigger report |
| `/api/reporter/history` | GET | Past reports |
| `/api/shutdown` | POST | RPi shutdown (requires `{"confirm": "SHUTDOWN_MIDNIGHT_RIDER"}`) |

---

## Server (`server.py` v2.0)

| Feature | Detail |
|---------|--------|
| Port | 8888 |
| Threading | `ThreadingMixIn` — concurrent requests |
| Logging | `logs/services/portal.log` |
| Security | Path sandbox (PORTAL/REGATTA/AIS only) |
| Shutdown | Requires confirmation token |

---

## CSS Design System

`portal/static/css/night-mode.css` provides shared styling:

- CSS variables: `--bg-base`, `--accent-cyan`, `--text-primary`, etc.
- Components: `.mr-nav`, `.mr-card`, `.mr-btn`, `.mr-badge`, `.mr-spinner`, `.mr-input`
- Dark theme: `#0a1628` (navy)

---

## Grafana Integration

`viewer.html` constructs Grafana iframe URLs:
```
http://{host}:3001/d/{dashboard}?kiosk=1&refresh=10s&theme=dark
```

Requires: `allow_embedding = true` in `config/grafana-custom.ini`

After changing config:
```bash
docker compose restart grafana
```

---

## Deployment

```bash
# Status
sudo systemctl status midnightrider-portal

# Restart
sudo systemctl restart midnightrider-portal

# Logs
tail -f /home/aneto/midnightrider-navigation/logs/services/portal.log
```

---

## Tests

```bash
python3 -m unittest tests.test_portal -v
```

---

*Midnight Rider — J/30 — Larchmont Yacht Club*

# Midnight Rider Navigation System — Operational Summary

> Quick reference for race-day and field operations.
>
> **Repository:** `Aneto152/midnightrider-navigation` (GitHub)
> **Repository root on RPi:** `/home/aneto/midnightrider-navigation`
> **Canonical hostname:** `midnightrider.local` (mDNS)
> **Canonical SSH:** `ssh aneto@midnightrider.local`

This document is an operational quick reference. Detailed specifications and procedures belong to the dedicated SSOT (Single Source of Truth) documents referenced below.

---

## 1. System Identity

Midnight Rider is a J/30 sailing vessel equipped with an integrated marine navigation system comprising:

- **Signal K** — Open-source marine data aggregation (systemctl-managed)
- **NMEA 2000** — Industry-standard instrument bus (7 devices, 7/50 LEN)
- **Bluetooth LE** — Wireless sensor integration (IMU, anemometer, BMS)
- **InfluxDB** — Time-series data storage (permanent retention, 106 measurements)
- **Grafana** — Dashboard visualization (9 operational dashboards)
- **AIS & Competitor Tracking** — Live fleet tracking and tactical analysis
- **Regatta Services** — Race operations and crew coordination
- **OpenClaw Gateway** — Local AI coordination (private, never exposed publicly)

All systems are hosted on a **Raspberry Pi 4 Model B** (4 GB RAM, microSD 64 GB) running Raspberry Pi OS (Debian 12 Bookworm).

**Publication subsystem (staging validation only):**

Controlled one-shot runtime entrypoint and staging activation gate provide offline validation of publication paths without daemon activation or service modification.
- Mode: "staging" required (enforced)
- Dry-run: True required (enforced)
- No systemd units enabled
- No network access permitted
- No credentials read from environment
- No Telegram contact
- No TelegramSender instantiation
- RuntimeE2EEntrypoint: One-shot, offline-only, no network access, no credential reads
- Runtime E2E validation: incomplete (not executed)

---

## 2. Service and Port Map

| Service | Port | Runtime | Management Rule |
|---------|-----:|---------|-----------------|
| **Signal K** | 3000 | systemd | ✅ systemctl only — NEVER docker |
| **InfluxDB** | 8086 | Docker | Docker Compose only |
| **Grafana** | 3001 | Docker | Docker Compose only |
| **Regatta Server** | 5000 | Docker | Docker Compose only |
| **Portal Server** | 8888 | systemd/Python | Local or authenticated access only |
| **OpenClaw Gateway** | 18789 | local | Local-only — NEVER expose publicly |

**Access via canonical hostname:**
- Signal K: `http://midnightrider.local:3000`
- Grafana: `http://midnightrider.local:3001`
- Portal: `http://midnightrider.local:8888`

---

## 3. Service Health Checks

### Signal K

```bash
# Check status (systemctl)
sudo systemctl status signalk

# Check logs (live)
sudo journalctl -u signalk -f

# API health check
curl http://midnightrider.local:3000/api/

# Expected response: HTTP 200 + vessel object
```

### Docker Services

```bash
# List running containers
docker compose ps

# Expected services:
#  - influxdb (Up)
#  - grafana (Up)
#  - regatta (Up)

# Check logs
docker compose logs -f grafana
docker compose logs -f influxdb
docker compose logs -f regatta
```

### InfluxDB

```bash
# Health endpoint
curl http://midnightrider.local:8086/health

# Expected response: HTTP 200

# Verify bucket exists
influx bucket list --org MidnightRider
# Expected: midnight_rider (retention: infinite)
```

### Grafana

```bash
# Health endpoint
curl http://midnightrider.local:3001/api/health

# Expected response: HTTP 200 + {"status":"ok"}
```

### OpenClaw Gateway

OpenClaw Gateway is local-only and listens on port 18789. Do not expose it directly to the Internet.

---

## 4. Main Data Flows

**Instrument → Signal K → Storage & Visualization:**

```
UM982 (GPS/Heading)  ──┐
WIT IMU (BLE)        ──┐
Calypso UP10 (BLE)   ──┼──> Signal K :3000 ──┬──> InfluxDB :8086 ──> Grafana :3001
WS320 (N2K)          ──┤                      │
YDBC-05 (N2K)        ──┤                      └──> N2K Bus (via YDNU-02)
AIS700 (N2K)         ──┤
SOK BMS (BLE) ───────────────────────────────┘
```

**Data flow details:**
- **USB devices** (UM982) → Signal K via serial plugins
- **Bluetooth LE devices** (WIT, Calypso, SOK) → Signal K via BLE daemons
- **NMEA 2000 devices** (WS320, YDBC-05, AIS700, Vulcan 7 FS) → Signal K via YDNU-02 USB bridge
- **Signal K → InfluxDB** — signalk-to-influxdb2 plugin writes 1-second intervals to bucket `midnight_rider`
- **Signal K → NMEA 2000** — sk-to-nmea2000 plugin converts 7 Signal K paths to N2K PGNs
- **InfluxDB → Grafana** — Flux queries read 106 measurements, dashboards refresh 5–30 seconds

**Instrument specifications and PGN ownership:** See [docs/ARCHITECTURE-MASTER.md](docs/ARCHITECTURE-MASTER.md) § 2.2–2.3

**System-level PGN flow:** See [docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md](docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md)

---

## 5. InfluxDB

**Main bucket:** `midnight_rider`
- **Retention:** Infinite (0 = permanent storage)
- **Organization:** `MidnightRider`
- **Data source:** Signal K plugin (signalk-to-influxdb2, v1.0+)
- **Write interval:** 1 second
- **Measurements:** 106 active (wind, heading, speed, attitude, electrical, AIS, etc.)

**Permanent retention is NOT a backup.** Data is permanent, but you must still:
1. Configure automated InfluxDB backups
2. Monitor backup success
3. Test restore procedures periodically

**Internal buckets (do not modify during normal operations):**
- `_monitoring` — InfluxDB system metrics
- `_tasks` — Task execution logs

**Credentials management:**
- InfluxDB token supplied via environment variable (`INFLUX_TOKEN`)
- Secured in `.env.local` (which is in `.gitignore`)
- Never commit or log the token

**Never commit or log:**
- `INFLUX_TOKEN`
- `INFLUX_URL`
- `INFLUX_ORG`
- Database credentials

---

## 6. Grafana

**Access:** `http://midnightrider.local:3001`
**Data source UID:** `efifgp8jvgj5sf`
**Port:** 3001 (Docker, reverse proxy optional)

**Dashboard inventory (9 operational dashboards):**

| # | Dashboard | Refresh | Purpose |
|---|-----------|---------|---------|
| 1 | COCKPIT | 5s | Main navigation (heading, SOG, COG, heel, pitch, yaw) |
| 2 | ENVIRONMENT | 30s | Sea state (temp, pressure, depth, barometric trend) |
| 3 | PERFORMANCE | 5s | Speed & VMG (polar ratio, target speed, sails) |
| 4 | WIND & CURRENT | 10s | Tactical analysis (TWS, TWD, AWA, current, layline) |
| 5 | COMPETITIVE | 30s | Fleet tracking (position, distance-to-mark, ETA) |
| 6 | ELECTRICAL | 30s | Power management (SOC%, cell voltage, temp, current) |
| 7 | RACE | 5s | Race-specific (start line, mark roundings, timers) |
| 8 | ALERTS | 10s | System health (65+ alert rules) |
| 9 | CREW | 30s | Watch management (rotation, rest, fatigue) |

**Dashboard ownership & descriptions:** See [docs/DASHBOARDS-README.md](docs/DASHBOARDS-README.md)

**When adding a dashboard:**
1. Add the dashboard JSON definition to `grafana-dashboards/`
2. Update [docs/DASHBOARDS-README.md](docs/DASHBOARDS-README.md)
3. Update [docs/INDEX.md](docs/INDEX.md) navigation
4. Verify the datasource UID matches `efifgp8jvgj5sf`
5. Verify no token is embedded in the dashboard export
6. Test the dashboard against live data before committing

---

## 7. AIS and Competitor Tracking

**Data distinction:** Competitor metadata ≠ Live AIS telemetry

**Competitor metadata** (from `regatta/competitors.json`):
- Vessel name, skipper, model, class
- MMSI (Maritime Mobile Service Identity)
- PHRF/ORC ratings
- Event registration
- Status: verified, probable, not_found

**AIS time-series data** (from InfluxDB `midnight_rider` bucket):
- Timestamp (UTC)
- Vessel position (lat, lon)
- SOG (Speed Over Ground)
- COG (Course Over Ground)
- Bearing from self
- Distance from self
- TWA (True Wind Angle)
- VMG (Velocity Made Good) to wind & mark
- Signal strength (dBm)
- Source (N2K, Signal K, etc.)

**AIS sources:**
- NMEA 2000 (AIS700 transpondeur)
- Signal K processing
- External competitor data feeds

**Do not treat competitor metadata as live AIS telemetry.** Use metadata for race registration and analysis; use time-series for tactical tracking.

**AIS tracker:** See [ais/README.md](ais/README.md) for module documentation.

---

## 8. MediaMan (Telegram Reporter) — Foundation Phase

**Status:** FOUNDATION ONLY — DRY-RUN VALIDATED — PRODUCTION NOT AUTHORIZED

**Current State (2026-08-27):**
- ✅ SQLite delivery state machine (PENDING → SENDING → SENT / FAILED)
- ✅ Telegram sender (outbound-only, no inbound)
- ✅ Logging infrastructure (structured, sanitized)
- ✅ Systemd units present (service + timer disabled)
- ❌ Real content provider not implemented
- ❌ OpenClaw LLM adapter not implemented
- ⏳ Telegram bot/group not created

**Verified Scope:**
- Dry-run foundation: exit code 0, no network I/O, SQLite state transitions correct
- Test content provider: deterministic French article (DRY_RUN only)
- Logging signatures: all aligned, no credentials exposed
- Systemd integration: service and timer syntax valid, timer disabled and inactive

**Not Authorized:**
- Creating a Telegram bot account
- Creating or joining a Telegram group
- Enabling or starting mediaman.timer
- Sending real Telegram messages
- Configuring production credentials

**Production Blockers:**
- Real content provider (LLM adapter) not implemented
- Regatta API data contract incomplete (missing race_id, elapsed time, ranking)
- OpenClaw CLI integration not implemented
- No explicit Denis approval for production activation

**For Details:** See [docs/INTEGRATION/TELEGRAM-REPORTER-INTEGRATION-GUIDE.md](docs/INTEGRATION/TELEGRAM-REPORTER-INTEGRATION-GUIDE.md)

---

## 9. Logging

**Log directory:** `/home/aneto/midnightrider-navigation/logs/`

**Main files:**
- `latest.json` — Latest task status (JSON format)
- `oc-actions.log` — OpenClaw action history (append-only)
- Service logs in Docker containers (via `docker compose logs`)
- System logs via `journalctl` (systemd services)

**Expected service logs:**
- Signal K: `journalctl -u signalk`
- Portal: `journalctl -u portal`
- BLE daemons: `journalctl -u wit-ble-direct`, `journalctl -u calypso-direct`

**Log format requirements:**
- ISO-8601 timestamps
- Structured format (JSON or key=value)
- Useful diagnostic context
- Stack traces where applicable

**Never commit or log:**
- API keys
- Tokens
- Passwords
- Credentials
- Authenticated URLs
- Environment file contents
- Authentication material

---

## 10. Python Dependencies

**BLE communication:**
```
bleak >= 0.14.0    # Bluetooth LE library
```

**Script dependencies (data processing):**
```
influxdb-client >= 1.18.0
requests >= 2.26.0
```

**Do not create a root-level `requirements.txt`.** Service dependencies are managed individually:
- BLE daemons: `ble/requirements.txt`
- Regatta server: `regatta/requirements.txt`
- AIS services: `ais/requirements.txt`

---

## 11. Operational Security Rules

**Never:**
- Expose OpenClaw Gateway publicly (port 18789)
- Expose InfluxDB without authentication
- Expose control endpoints without authentication
- Commit `.env.local` or `.env` files
- Commit credentials, tokens, or secrets
- Log credentials
- Use hardcoded LAN IP addresses in documentation or scripts
- Use `sed` to modify JSON files (use Python3 instead)
- Manage Signal K with Docker
- Write raw secrets into Grafana dashboards
- Modify production services without validation

**Use:**
- `midnightrider.local` (mDNS) instead of hardcoded LAN IP addresses
- Environment variables for credentials (sourced from `.env.local`)
- Python3 for JSON processing
- systemctl for Signal K management
- Docker Compose for InfluxDB, Grafana, Regatta

**Tailscale remote access:**
- May be used for authenticated remote access
- Must remain restricted to the Midnight Rider tailnet
- Never expose public ports directly to the Internet
- Tailscale IP addresses (e.g., 100.x.x.x) must not be documented as primary access points

---

## 12. Standard Operational Procedures

### Read-only system check

```bash
# Full health report (read-only)
python3 scripts/monitor_resources.py

# Check Grafana health
curl http://midnightrider.local:3001/api/health

# Check Signal K health
curl http://midnightrider.local:3000/api/

# Check InfluxDB health
curl http://midnightrider.local:8086/health
```

### Read logs

```bash
# Latest task status
cat logs/latest.json | python3 -m json.tool

# OpenClaw action history
tail -20 logs/oc-actions.log

# Live Signal K logs
sudo journalctl -u signalk -f

# Docker service logs
docker compose logs -f grafana
```

### Check Git state

```bash
# Latest commits
git log --oneline -5

# Current branch
git status

# Uncommitted changes
git diff
```

### Validate JSON

```bash
# Use Python3 (NOT sed)
python3 -m json.tool logs/latest.json > /dev/null && echo "✅ Valid JSON"
```

### Before a Git push

```bash
# Check for credentials
git status | grep -E "token|secret|env|password"

# Check for hardcoded LAN IPs
grep -rn "192\.168\.1\." . --include="*.md" | head -5

# Check for credentials in changes
git diff --cached | grep -i "secret\|token\|password"

# Only push if all checks pass
git push origin main
```

---

## 13. Incident Response

### If Signal K fails

1. Check status:
   ```bash
   sudo systemctl status signalk
   sudo journalctl -u signalk | tail -50
   ```

2. Restart:
   ```bash
   sudo systemctl restart signalk
   ```

3. Verify recovery:
   ```bash
   curl http://midnightrider.local:3000/api/
   ```

4. If still down, check: USB connections (UM982), BLE connections (WIT, Calypso), YDNU-02 gateway.

### If Docker services fail

1. Check status:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

2. Restart specific service:
   ```bash
   docker compose restart influxdb
   docker compose restart grafana
   docker compose restart regatta
   ```

3. Restart all:
   ```bash
   docker compose restart
   ```

4. If data is lost, do NOT delete volumes. Check backups first.

### If InfluxDB is unavailable

1. Check container:
   ```bash
   docker compose logs influxdb | tail -50
   ```

2. Verify volume:
   ```bash
   docker volume ls | grep influxdb
   ```

3. Do NOT delete InfluxDB volumes.

4. Do NOT recreate InfluxDB with destructive volume commands.

5. If data integrity is uncertain:
   - Stop configuration changes
   - Preserve logs
   - Check the latest Git commit
   - Check InfluxDB health
   - Verify volume presence
   - Create a backup before recovery actions

---

## 14. Documentation Ownership

| Content | Source of Truth | Location |
|---------|-----------------|----------|
| Instrument specifications | Datasheets + ARCHITECTURE-MASTER | `docs/HARDWARE/` |
| Instrument PGNs | N2K-NETWORK-ARCHITECTURE | `docs/INTEGRATION/` |
| Integration procedures | Per-instrument guides | `docs/INTEGRATION/` |
| System-level PGN flow | N2K-NETWORK-ARCHITECTURE | `docs/INTEGRATION/` |
| Overall architecture | ARCHITECTURE-MASTER | `docs/` |
| Operational quick reference | **SYSTEM-SUMMARY** (this file) | Repository root |
| Documentation navigation | INDEX.md | `docs/` |
| Grafana dashboards | DASHBOARDS-README | `docs/` |
| OpenClaw execution history | logs/latest.json + oc-actions.log | `logs/` |

**docs/INDEX.md is a navigation map.** It must not become a duplicate content repository. Add new links; do not duplicate content.

---

## 15. Known Gaps

The following items require follow-up:

- Automated Git and OpenClaw verification loop
- Automatic notification from OpenClaw to Dust (analyst)
- Authentication for remote control endpoints
- Common InfluxDB Line Protocol escaping library
- Comprehensive Python test suite for all BLE daemons
- Automated InfluxDB backup and restore test (periodic validation)
- Reconciliation of dashboard counts in documentation (9 vs 16 references)
- Reconciliation of Tailscale and older remote-access documentation
- Reliable synchronization of team documentation with the latest commit
- Signal K plugin version tracking (vs production deployment)

---

## 16. Change Policy

**Any structural change requires Denis validation before execution.**

**High-risk changes include:**
- Signal K configuration
- Docker architecture or volumes
- Network bindings or ports
- Authentication or credentials
- OpenClaw Gateway setup
- InfluxDB storage or retention policy
- Production race-control endpoints

**Every completed change must:**
1. Run the required tests
2. Update the appropriate logs (`logs/latest.json`, `logs/oc-actions.log`)
3. Perform security checks (no credentials, no hardcoded IPs)
4. Commit the change with descriptive message
5. Push the commit with `git push origin main`
6. Report the full commit SHA from `git rev-parse HEAD`

---

## Quick Reference Links

| Topic | Document |
|-------|----------|
| Full architecture | [docs/ARCHITECTURE-MASTER.md](docs/ARCHITECTURE-MASTER.md) |
| N2K PGN flows | [docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md](docs/INTEGRATION/N2K-NETWORK-ARCHITECTURE.md) |
| SK→N2K bridge | [docs/INTEGRATION/SK-TO-N2K-BRIDGE.md](docs/INTEGRATION/SK-TO-N2K-BRIDGE.md) |
| Dashboard reference | [docs/DASHBOARDS-README.md](docs/DASHBOARDS-README.md) |
| Documentation index | [docs/INDEX.md](docs/INDEX.md) |
| All hardware datasheets | [docs/HARDWARE/](docs/HARDWARE/) |
| All integration guides | [docs/INTEGRATION/](docs/INTEGRATION/) |
| Operational checklists | [docs/OPERATIONS/](docs/OPERATIONS/) — see [docs/INDEX.md](docs/INDEX.md) for current files |
| AIS tracker module | [ais/README.md](ais/README.md) |

---

**Last updated:** 2026-08-14
**Status:** ✅ Production — Operational summary for race-day and field use
**Repository:** `Aneto152/midnightrider-navigation`
**Canonical hostname:** `midnightrider.local`

# Service Logging Locations & Evidence Status Reference

**Version:** 1.0  
**Date:** 2026-09-09  
**Status:** ✅ REFERENCE COMPLETE  
**Purpose:** Navigation and evidence tracking for service logging across Midnight Rider navigation system

---

## Service Logging Evidence Matrix

| Service | Manager | Port | Current Evidence Source | Local-Only Runtime Evidence | Remote Versioned Evidence | Heartbeat Status | Evidence Status | Notes & Limitations |
|---------|---------|------|--------------------------|------------------------------|--------------------------|------------------|------------------|-------------------|
| **SignalK** | systemd | 3000 | journalctl (systemd journal) | UNKNOWN | Not audited | UNKNOWN | UNKNOWN | Requires journalctl inspection for real-time heartbeat; startup logs via `sudo systemctl status signalk` |
| **InfluxDB** | Docker | 8086 | docker logs stdout/stderr | NOT accessible (inside container) | UNKNOWN | UNKNOWN | UNKNOWN | Container logs require `docker logs influxdb` to inspect; internal logging not accessible from workspace |
| **Grafana** | Docker | 3001 | docker logs stdout/stderr | NOT accessible (inside container) | UNKNOWN | UNKNOWN | UNKNOWN | Container logs require `docker logs grafana` to inspect; internal logging not accessible from workspace |
| **OpenClaw-Gateway** | UNKNOWN | 18789 | UNKNOWN (no manager identified) | NOT found | UNKNOWN | UNKNOWN | BLOCKED | Manager unknown; startup location unknown; language/framework unknown; no runtime logs discovered in workspace |
| **Regatta-Server** | Docker | 5000 | docker logs stdout/stderr | NOT accessible (inside container) | UNKNOWN | UNKNOWN | UNKNOWN | Container logs require `docker logs regatta` to inspect; internal logging not accessible from workspace |
| **NMEA-Parser** | Signal K plugin | — | Depends on Signal K | Depends on Signal K | UNKNOWN | UNKNOWN | UNKNOWN | Plugin-based; no independent logging; heartbeat depends on Signal K logging infrastructure |
| **Portal** | systemd | 8888 | logs/services/portal.log (local) | logs/services/portal.log exists locally | Absent from remote tree at commit 0c3a52bd99edb887a92a5c257390f5e7503832b2 | STALE (218+ min) | PARTIALLY VERIFIED | Portal runtime log exists locally as a runtime artifact. However, this file is absent from the authoritative origin/main tree inspected at commit 0c3a52bd99edb887a92a5c257390f5e7503832b2. Treat it as local runtime evidence only, not as a versioned repository artifact. |

---

## Service-by-Service Evidence Details

### 1. SignalK

| Attribute | Value | Status |
|-----------|-------|--------|
| Manager | systemd (verified) | VERIFIED ✅ |
| Port | 3000 (verified) | VERIFIED ✅ |
| Unit file | /etc/systemd/system/signalk.service (verified to exist) | VERIFIED ✅ |
| Current logging | journalctl (systemd journal) | VERIFIED ✅ |
| Dedicated local log | UNKNOWN (no workspace file found) | UNKNOWN ⚠️ |
| Heartbeat status | UNKNOWN (journal not inspected) | UNKNOWN ⚠️ |
| Notes | Service runs via systemd; logs to journal by default. Real-time heartbeat evidence requires `journalctl -u signalk` query authorization. |

---

### 2. InfluxDB

| Attribute | Value | Status |
|-----------|-------|--------|
| Manager | Docker Compose (verified) | VERIFIED ✅ |
| Port | 8086 (verified) | VERIFIED ✅ |
| Current logging | Docker container stdout/stderr | VERIFIED ✅ |
| Dedicated local log | NOT accessible (inside container) | UNKNOWN ⚠️ |
| Heartbeat status | UNKNOWN (container logs not inspected) | UNKNOWN ⚠️ |
| Notes | Container logs require `docker logs influxdb` to inspect. No workspace-accessible runtime evidence found. Internal logging inaccessible without container inspection. |

---

### 3. Grafana

| Attribute | Value | Status |
|-----------|-------|--------|
| Manager | Docker Compose (verified) | VERIFIED ✅ |
| Port | 3001 (verified) | VERIFIED ✅ |
| Current logging | Docker container stdout/stderr | VERIFIED ✅ |
| Dedicated local log | NOT accessible (inside container) | UNKNOWN ⚠️ |
| Heartbeat status | UNKNOWN (container logs not inspected) | UNKNOWN ⚠️ |
| Notes | Container logs require `docker logs grafana` to inspect. No workspace-accessible runtime evidence found. Internal logging inaccessible without container inspection. |

---

### 4. OpenClaw-Gateway

| Attribute | Value | Status |
|-----------|-------|--------|
| Manager | UNKNOWN (not identified) | UNKNOWN ⚠️ |
| Port | 18789 (documented but manager unknown) | PARTIALLY VERIFIED ⚠️ |
| Current logging | UNKNOWN (no runtime logs found) | UNKNOWN ⚠️ |
| Dedicated local log | NOT found | UNKNOWN ⚠️ |
| Heartbeat status | UNKNOWN | UNKNOWN ⚠️ |
| Notes | **BLOCKED:** Manager unknown; startup location unknown; language/framework unknown. No systemd unit found. Cannot propose logging instrumentation without identifying manager and startup mechanism. Requires separate investigation. |

---

### 5. Regatta-Server

| Attribute | Value | Status |
|-----------|-------|--------|
| Manager | Docker Compose (verified) | VERIFIED ✅ |
| Port | 5000 (verified) | VERIFIED ✅ |
| Current logging | Docker container stdout/stderr | VERIFIED ✅ |
| Dedicated local log | NOT accessible (inside container) | UNKNOWN ⚠️ |
| Heartbeat status | UNKNOWN (container logs not inspected) | UNKNOWN ⚠️ |
| Notes | Container logs require `docker logs regatta` to inspect. No workspace-accessible runtime evidence found. Internal logging inaccessible without container inspection. |

---

### 6. NMEA-Parser

| Attribute | Value | Status |
|-----------|-------|--------|
| Type | Signal K plugin (documented) | DOCUMENTED ✅ |
| Manager | Depends on Signal K | DOCUMENTED ✅ |
| Standalone service | NO (plugin-based) | DOCUMENTED ✅ |
| Current logging | Depends on Signal K logging | DOCUMENTED ✅ |
| Dedicated local log | NOT found (plugin; depends on SK) | UNKNOWN ⚠️ |
| Heartbeat status | UNKNOWN (depends on Signal K) | UNKNOWN ⚠️ |
| Notes | Plugin-based; no independent logging or heartbeat. Heartbeat visibility depends entirely on Signal K logging infrastructure and journal inspection. |

---

### 7. Portal

| Attribute | Value | Status |
|-----------|-------|--------|
| Manager | systemd (verified) | VERIFIED ✅ |
| Unit file | /etc/systemd/system/midnightrider-portal.service (verified to exist) | VERIFIED ✅ |
| Port | 8888 (verified in unit file) | VERIFIED ✅ |
| Logging configuration | StandardOutput=journal, StandardError=journal (verified in unit file) | VERIFIED ✅ |
| Dedicated local log | logs/services/portal.log (exists locally) | VERIFIED ✅ |
| Versioned in repository | Absent from origin/main tree at commit 0c3a52bd99edb887a92a5c257390f5e7503832b2 | CONTRADICTED ❌ |
| Most recent entry | 2026-09-09T16:53:07 UTC | VERIFIED ✅ |
| Heartbeat freshness | 218+ minutes (far outside 5-minute window) | STALE ⚠️ |
| **Precise evidence statement** | **Portal runtime log: logs/services/portal.log exists locally as a runtime artifact. However, this file is absent from the authoritative origin/main tree inspected at commit 0c3a52bd99edb887a92a5c257390f5e7503832b2. Treat it as local runtime evidence only, not as a versioned repository artifact.** | PARTIALLY VERIFIED ✅ |

---

## Versioned Repository Artifacts (Authoritative at commit 0c3a52bd99edb887a92a5c257390f5e7503832b2)

These files are present in the remote GitHub tree and treated as versioned repository documentation:

| File | Status | Purpose |
|------|--------|---------|
| logs/services/.gitkeep | VERSIONED ✅ | Directory marker for logs/services/ structure |
| logs/debug/aggregate-errors.sh | VERSIONED ✅ | Error aggregation script |
| logs/debug/crash-capture-2026-06-28T190455Z.log | VERSIONED ✅ | Historical crash capture log |
| logs/debug/data-flow.log | VERSIONED ✅ | Data flow trace documentation |
| logs/debug/error-summary.log | VERSIONED ✅ | Historical error summary |

---

## Local-Only Runtime Artifacts (not versioned in repository)

These files exist locally in the workspace but are absent from the remote GitHub tree:

| File | Status | Purpose |
|------|--------|---------|
| logs/services/portal.log | LOCAL-ONLY ⚠️ | Portal server runtime log (local artifact, not versioned) |

---

## Summary Statistics

| Metric | Count | Status |
|--------|-------|--------|
| Services with verified manager | 6/7 | VERIFIED ✅ |
| Services with unknown manager | 1/7 | BLOCKED ⚠️ |
| Services with accessible workspace logs | 1/7 | PARTIALLY VERIFIED ⚠️ |
| Services with container-only logs | 3/7 | NOT ACCESSIBLE ⚠️ |
| Services with unknown logging | 2/7 | UNKNOWN ⚠️ |
| Current accessible heartbeats (5-min window) | 0/7 | STALE/UNKNOWN ⚠️ |
| Stale heartbeats (> 5 min) | 1/7 | Portal (218+ min) |
| Versioned logging artifacts | 5 files | VERIFIED ✅ |
| Local-only logging artifacts | 1 file | VERIFIED ✅ |

---

## How to Use This Reference

1. **Need current heartbeat status?** Check the "Heartbeat Status" column above.
2. **Need to inspect specific service logs?** Find the "Current Evidence Source" for that service.
3. **Need to understand logging limitations?** Read "Notes & Limitations" for each service.
4. **Need to understand versioning?** See the "Versioned Repository Artifacts" and "Local-Only Runtime Artifacts" sections.
5. **Need strategic guidance?** See [docs/LOGGING-VISIBILITY-STRATEGY.md](LOGGING-VISIBILITY-STRATEGY.md).

---

**Status:** ✅ REFERENCE COMPLETE  
**Last Updated:** 2026-09-09  
**Not Authorized For:** Implementation or service modifications based on this reference


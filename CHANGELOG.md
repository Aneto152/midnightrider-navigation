# CHANGELOG — Midnight Rider Navigation System

## [1.0.0] — 2026-05-22 (Block Island Race)

### Added
- 9 Grafana dashboards (Cockpit, Performance, Winds, Competitive, Electrical, Race, Alerts, Crew, Environment)
- 65 Grafana alert rules
- WhatsApp race reporter via Twilio (Media Man agent)
- Crew watch management (double-handed Denis + Anne-Sophie)
- 7 MCP servers with 37 tools (Astronomical, Racing, Polar, Crew, Weather, Buoy, Race Management)
- Dashboard portal (index.html + viewer.html) for iPad access
- Complete documentation (docs/ with 7 categories)
- GitHub issue template for bug reports

### Infrastructure
- Signal K v2.25 (native systemd)
- InfluxDB v2.8 (Docker)
- Grafana v12.3.1 (Docker)
- Python 3.11 scripts for reporters and tools
- Node.js MCP servers

### Hardware Support
- Unicore UM982 GNSS (dual-antenna, heading)
- WIT WT901BLECL IMU (BLE, roll/pitch/yaw)
- Calypso UP10 anemometer (optional)
- SOK 12V 100Ah LiFePO4 battery with BMS (BLE monitoring)

## [0.9.0] — 2026-04-27 (Pre-Release Security Hardening)

### Security
- ✅ Revoked and replaced all hardcoded InfluxDB tokens
- ✅ Created RECOVERY-GUIDE-SAFE.md (placeholders only, no secrets)
- ✅ Redacted all credentials from public files
- ✅ Reorganized docs/ structure (agents/, ops/, security/, setup/, mcp/)
- ✅ Added .env.example with all required variables
- ✅ Removed deprecated files (4 old dashboards, 2 old TODOs)
- ✅ Removed 4 orphan branches (dev, stable, master, archive/obsolete-files)

### Added
- MIT License
- CONTRIBUTING.md guidelines
- PUBLICATION-REPORT.md (security audit summary)
- GitHub Actions CI skeleton (requires workflow scope)
- MCP smoke test script (test-all-mcp.sh)
- WhatsApp test script (test-whatsapp.sh)

### Documentation
- Updated README.md for public audiences
- Created docs/INDEX.md (navigation guide)
- Added GitHub issue template
- Consolidated TODO files into TODO-CONSOLIDATED.md
- Cleaned root directory (11 critical .md files only)

## [0.5.0] — 2026-04-19 (System Integration Complete)

### Added
- Signal K server operational
- InfluxDB time-series database connected
- Grafana dashboards working
- MCP servers (7 total) with racing tools
- Crew management dashboard (watch rotation, fatigue tracking)
- Wave analyzer plugin (heel correction, 3-axis acceleration)
- Performance polars comparison

### Integrations
- UM982 GNSS position + heading working
- WIT IMU attitude (roll, pitch, yaw)
- Wind instruments via NMEA 2000
- Loch calibration system
- Battery monitoring (Victron Orion)

### Testing
- Static port test: all dashboards responsive
- Data flow verified (Signal K → InfluxDB → Grafana)
- MCP tool responses validated

## [0.1.0] — 2026-03-21 (Initial Setup)

### Initial
- Raspberry Pi 4 base setup (8GB RAM)
- Signal K server installation
- Docker + Docker Compose
- Basic GNSS fix with UM982
- Systemd services for Signal K

---

## Semantic Versioning

- **1.0.0** = Production-ready for Block Island Race
- **0.9.0** = Release-ready (security hardened)
- **0.5.0** = Feature-complete (all systems integrated)
- **0.1.0** = Initial setup phase

---

**Last Updated:** 2026-04-27  
**Made with ⛵ for sailors who care about data**

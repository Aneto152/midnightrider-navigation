# Midnight Rider Documentation Index

Complete reference guide for the Midnight Rider navigation system.

---

## 📚 Quick Navigation

### Getting Started
- **[README](../README.md)** — Project overview & quick start
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — How to contribute

### System Architecture
- **[ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md](ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md)** — Full system design
- **[System Summary](SYSTEM-SUMMARY.md)** — High-level overview

---

## 🔧 Hardware Documentation

### Datasheets & Integration

| Device | Datasheet | Integration Guide |
|--------|-----------|-------------------|
| **Unicore UM982** | [HARDWARE/UM982-GNSS-DATASHEET.md](HARDWARE/UM982-GNSS-DATASHEET.md) | [INTEGRATION/UM982-INTEGRATION-GUIDE.md](INTEGRATION/UM982-INTEGRATION-GUIDE.md) |
| **WIT WT901BLECL** | [HARDWARE/WIT-WT901BLECL-DATASHEET.md](HARDWARE/WIT-WT901BLECL-DATASHEET.md) | [INTEGRATION/WIT-INTEGRATION-GUIDE.md](INTEGRATION/WIT-INTEGRATION-GUIDE.md) |
| **Calypso UP10** | [HARDWARE/CALYPSO-UP10-DATASHEET.md](HARDWARE/CALYPSO-UP10-DATASHEET.md) | [INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md](INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md) |
| **SOK 12V 100Ah** | [HARDWARE/SOK-BMS-BLE-PROTOCOL.md](HARDWARE/SOK-BMS-BLE-PROTOCOL.md) | [INTEGRATION/SOK-BMS-INTEGRATION.md](INTEGRATION/SOK-BMS-INTEGRATION.md) |
| **Vulcan 7 FS** | [HARDWARE/VULCAN-7-FS-DATASHEET.md](HARDWARE/VULCAN-7-FS-DATASHEET.md) | [INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md](INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md) |
| **Raspberry Pi 4** | [HARDWARE/RASPBERRY-PI4-DATASHEET.md](HARDWARE/RASPBERRY-PI4-DATASHEET.md) | — |

---

## 💻 Software Documentation

### Configuration & Setup

| Topic | File |
|-------|------|
| **Signal K Configuration** | [SOFTWARE/SIGNAL-K-CONFIGURATION.md](SOFTWARE/SIGNAL-K-CONFIGURATION.md) |
| **InfluxDB Setup** | [SOFTWARE/INFLUXDB-SETUP.md](SOFTWARE/INFLUXDB-SETUP.md) |
| **Grafana Dashboards** | [SOFTWARE/GRAFANA-DASHBOARDS.md](SOFTWARE/GRAFANA-DASHBOARDS.md) |
| **Plugins Catalog** | [SOFTWARE/PLUGINS-CATALOG.md](SOFTWARE/PLUGINS-CATALOG.md) |
| **Scripts Catalog** | [SOFTWARE/SCRIPTS-CATALOG.md](SOFTWARE/SCRIPTS-CATALOG.md) |
| **Wave Analyzer v1.1** | [SOFTWARE/WAVE-ANALYZER-V1.1-GUIDE.md](SOFTWARE/WAVE-ANALYZER-V1.1-GUIDE.md) |

### Race Reporting (Media Man)

- **[WHATSAPP_REPORTER.md](WHATSAPP_REPORTER.md)** — Media Man agent documentation
  - WhatsApp group messaging
  - Message templates
  - Queue & offline mode
  - Testing procedures

---

## 🚤 Integration Guides

Complete step-by-step integration for each hardware component:

| Component | Guide |
|-----------|-------|
| **UM982 GNSS** | [INTEGRATION/UM982-INTEGRATION-GUIDE.md](INTEGRATION/UM982-INTEGRATION-GUIDE.md) |
| **WIT IMU (BLE)** | [INTEGRATION/WIT-INTEGRATION-GUIDE.md](INTEGRATION/WIT-INTEGRATION-GUIDE.md) |
| **Calypso Anemometer** | [INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md](INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md) |
| **SOK Battery BMS** | [INTEGRATION/SOK-BMS-INTEGRATION.md](INTEGRATION/SOK-BMS-INTEGRATION.md) |
| **Vulcan 7 FS MFD** | [INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md](INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md) |
| **YDNU-02 Gateway** | [INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md](INTEGRATION/YDNU-02-INTEGRATION-GUIDE.md) |

---

## 🎯 Operations & Checklists

### Pre-Race & Deployment

| Checklist | File |
|-----------|------|
| **Field Test (May 19)** | [OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md](OPERATIONS/FIELD-TEST-CHECKLIST-2026-05-19.md) |
| **Race Day (May 22)** | [OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md](OPERATIONS/RACE-DAY-CHECKLIST-2026-05-22.md) |
| **System Health Check** | [OPERATIONS/CHECK-SYSTEM-QUICK-REFERENCE.md](OPERATIONS/CHECK-SYSTEM-QUICK-REFERENCE.md) |
| **Troubleshooting** | [OPERATIONS/TROUBLESHOOTING.md](OPERATIONS/TROUBLESHOOTING.md) |

---

## 📊 Dashboards & Alerts

### Dashboard Suite

- **[GRAFANA-DASHBOARDS.md](SOFTWARE/GRAFANA-DASHBOARDS.md)** — 9 dashboards reference
  - COCKPIT (main navigation)
  - ENVIRONMENT (sea & weather)
  - PERFORMANCE (speed analysis)
  - WIND & CURRENT (tactical)
  - COMPETITIVE (fleet tracking)
  - ELECTRICAL (power management)
  - RACE (race-specific)
  - ALERTS (60+ alert rules)
  - CREW (watch management)

### Alert Rules (65 Total)

Alert categories:
- **Safety:** Heel, pitch, temperature, voltage, system failures
- **Performance:** VMG, polars, sail trim, waves, current
- **Weather/Sea:** Wind shifts, pressure, swell, humidity
- **Systems:** Battery, charger, comms, GPS, storage
- **Racing:** Mark rounding, start line, finish, fleet position
- **Crew:** Watch duration, rest, fatigue tracking

---

## 🔐 Security & Configuration

### Configuration

- **[.env.example](../.env.example)** — Configuration template (no secrets)
- **[LICENSE](../LICENSE)** — MIT License

### Best Practices

- Never commit `.env.local` (it's in `.gitignore`)
- Use `.env.example` as your template
- Rotate tokens every 90 days
- Enable 2FA on Grafana admin account

---

## 🌊 Hardware Integration Procedures

### Step-by-Step Guides

1. **UM982 GNSS Setup** → [INTEGRATION/UM982-INTEGRATION-GUIDE.md](INTEGRATION/UM982-INTEGRATION-GUIDE.md)
2. **WIT IMU via BLE** → [INTEGRATION/WIT-INTEGRATION-GUIDE.md](INTEGRATION/WIT-INTEGRATION-GUIDE.md)
3. **Calypso Wind** → [INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md](INTEGRATION/CALYPSO-INTEGRATION-GUIDE.md)
4. **SOK Battery Monitor** → [HARDWARE/SOK-BMS-BLE-PROTOCOL.md](HARDWARE/SOK-BMS-BLE-PROTOCOL.md)
5. **Vulcan 7 FS NMEA2000** → [INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md](INTEGRATION/VULCAN-SIGNALK-INTEGRATION.md)

---

## 📱 iPad Portal & Dashboard Access

- **Portal HTML:** `dashboard-portal.html` (landing page)
- **Viewer:** `dashboard.html` (individual dashboards)
- **Guide:** [DASHBOARD-PORTAL-GUIDE.md](DASHBOARD-PORTAL-FINAL.md)

### Access Methods

- **Desktop:** http://localhost:3001 (Grafana)
- **iPad WiFi:** http://MidnightRider.local:8888 (Portal)
- **Portal Landing:** 9 dashboard buttons
- **Kiosk Mode:** Full-screen with no menus

---

## 🚀 Development & Contributing

- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — How to contribute
- **[README.md](../README.md)** — Project overview

---

## 📖 File Organization

```
docs/
├── INDEX.md (this file)
├── ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md
├── SYSTEM-SUMMARY.md
├── SYSTEM-CHECKLIST.md
├── WHATSAPP_REPORTER.md
├── HARDWARE/
│   ├── UM982-GNSS-DATASHEET.md
│   ├── WIT-WT901BLECL-DATASHEET.md
│   ├── CALYPSO-UP10-DATASHEET.md
│   ├── SOK-BMS-BLE-PROTOCOL.md
│   ├── VULCAN-7-FS-DATASHEET.md
│   ├── RASPBERRY-PI4-DATASHEET.md
│   └── YDNU-02-GATEWAY-DATASHEET.md
├── INTEGRATION/
│   ├── UM982-INTEGRATION-GUIDE.md
│   ├── WIT-INTEGRATION-GUIDE.md
│   ├── CALYPSO-INTEGRATION-GUIDE.md
│   ├── VULCAN-SIGNALK-INTEGRATION.md
│   ├── YDNU-02-INTEGRATION-GUIDE.md
│   └── INTEGRATION-INDEX.md
├── SOFTWARE/
│   ├── SIGNAL-K-CONFIGURATION.md
│   ├── INFLUXDB-SETUP.md
│   ├── GRAFANA-DASHBOARDS.md
│   ├── PLUGINS-CATALOG.md
│   ├── SCRIPTS-CATALOG.md
│   └── WAVE-ANALYZER-V1.1-GUIDE.md
└── OPERATIONS/
    ├── FIELD-TEST-CHECKLIST-2026-05-19.md
    ├── RACE-DAY-CHECKLIST-2026-05-22.md
    ├── CHECK-SYSTEM-QUICK-REFERENCE.md
    └── TROUBLESHOOTING.md
```

---

## 🎯 Where to Start

1. **New to the project?** Start with [README.md](../README.md)
2. **Setting up hardware?** Go to [INTEGRATION/](INTEGRATION/)
3. **Running the system?** Check [OPERATIONS/](OPERATIONS/)
4. **Understanding architecture?** Read [ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md](ARCHITECTURE-SYSTEM-MASTER-2026-04-25.md)
5. **Need help?** See [OPERATIONS/TROUBLESHOOTING.md](OPERATIONS/TROUBLESHOOTING.md)

---

**Last updated:** 2026-04-27  
**Status:** Production-ready for Block Island Race 2026 (May 22)

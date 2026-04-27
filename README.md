# Midnight Rider 🌊

> Open-source marine performance instrumentation system for sailing races.  
> Built for a J/30 competing in the Block Island Race 2026.

## What It Does

**Midnight Rider** is a complete, self-contained navigation and race analytics system for sailboats:

- **Real-time data collection** via Signal K (GNSS, IMU, instruments)
- **Time-series storage** in InfluxDB
- **Live dashboards** in Grafana (9 custom dashboards)
- **AI race coaching** via Claude integration (MCP tools)
- **WhatsApp race reporting** ("Media Man" agent for family & friends)
- **Battery monitoring** for LiFePO4 via Bluetooth BLE
- **Offline queue** with automatic reconnect

Perfect for racing, cruising, or research.

---

## Quick Start

### Prerequisites

- Raspberry Pi 4 (or similar Linux host)
- Docker & Docker Compose
- Python 3.9+
- Internet connection (for initial setup)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/denislafarge/midnight-rider.git
cd midnight-rider

# 2. Copy config template
cp .env.example .env.local
# Edit .env.local with your credentials

# 3. Start services
docker compose up -d influxdb grafana

# 4. Start Signal K (if native install)
systemctl start signalk

# 5. Verify
curl http://localhost:3001/api/health  # Grafana
curl http://localhost:8086/health      # InfluxDB
curl http://localhost:3000/signalk/v1/api  # Signal K
```

### Access Dashboards

- **Grafana:** http://localhost:3001
- **Signal K:** http://localhost:3000
- **iPad:** http://<your-hostname>.local:8888 (via portal)

---

## Hardware

### Core System

| Component | Purpose | Notes |
|-----------|---------|-------|
| **Raspberry Pi 4** | Main computer | 8GB RAM recommended |
| **Unicore UM982** | GNSS receiver | Dual-antenna, heading capable |
| **WIT WT901BLECL** | Inertial measurement | Roll, pitch, yaw via BLE |
| **SOK 12V 100Ah** | Battery | LiFePO4, BMS with BLE |

### Optional Instruments

- **Calypso UP10:** Wind (anemometer + vane)
- **Loch:** Speed through water
- **Barometer:** Pressure trends
- **Sounder:** Water depth

---

## Software Stack

### Services

```
Signal K (port 3000)
    ↓
InfluxDB (port 8086)
    ↓
Grafana (port 3001)
    ↓
9 Dashboards
```

### Architecture

| Component | Type | Language | Role |
|-----------|------|----------|------|
| **Signal K** | Native systemd | Node.js | Data hub |
| **InfluxDB** | Docker | Go | Time-series DB |
| **Grafana** | Docker | Go | Visualization |
| **Dashboard Portal** | HTML/JS | JavaScript | iPad UI |
| **Media Man** | Python | Python 3 | WhatsApp reporter |
| **MCP Tools** | Node.js | JavaScript | AI integration |

---

## Dashboards (9 Total)

| # | Name | Refresh | Purpose |
|----|------|---------|---------|
| 1 | 🏠 COCKPIT | 5s | Main navigation |
| 2 | 🌊 ENVIRONMENT | 30s | Sea & weather |
| 3 | ⚡ PERFORMANCE | 5s | Speed & efficiency |
| 4 | 🌪️ WIND & CURRENT | 10s | Tactical analysis |
| 5 | 🏆 COMPETITIVE | 30s | Fleet tracking |
| 6 | 🔋 ELECTRICAL | 30s | Power management |
| 7 | 🏁 RACE | 5s | Race-specific metrics |
| 8 | 🔔 ALERTS | 10s | System monitoring (65 alerts) |
| 9 | ⚓ CREW | 30s | Watch management |

---

## Features

### Live Navigation

- True heading (GNSS-based)
- Speed over ground & through water
- Course over ground
- Roll, pitch, yaw attitude
- Rate of turn

### Race Analytics

- Velocity made good (VMG)
- Performance vs. polar diagrams
- Wind shifts and lulls
- Crew watch rotation
- Mark approach warnings
- Start line analysis

### Race Reporting

**Media Man** — WhatsApp bot that sends live updates to a group:

- Position updates every 30 minutes
- Wind alerts (gusts > threshold)
- Speed records
- Mark roundings
- Finish notifications

### Battery Monitoring (SOK BMS)

- State of charge (SOC)
- Cell voltages (imbalance detection)
- Temperature
- Current (charge/discharge)
- Cycle count

### Offline Mode

- Message queue for WhatsApp updates
- Auto-reconnect and drain
- Persistent state (max 20 messages)

---

## Documentation

Complete documentation in `/docs`:

- **HARDWARE/** — Device datasheets and integration guides
- **SOFTWARE/** — Signal K config, Grafana setup, plugin catalog
- **OPERATIONS/** — Pre-race checklists, troubleshooting
- **INTEGRATION/** — Hardware-specific integration procedures

Start with: [`docs/INDEX.md`](docs/INDEX.md)

---

## Configuration

### .env.local

Copy `.env.example` to `.env.local` and fill in your values:

```bash
cp .env.example .env.local
nano .env.local
```

**Never commit `.env.local` to Git.** It's in `.gitignore` for security.

Key variables:
- **Grafana:** Admin user, password, token
- **InfluxDB:** URL, org, bucket, token
- **WhatsApp:** Twilio credentials, group IDs
- **Race:** Boat name, skipper, race config

See `.env.example` for full list.

---

## Development

### Clone & Setup

```bash
git clone https://github.com/denislafarge/midnight-rider.git
cd midnight-rider
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/
```

### Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

**Security reminder:** Never commit credentials. Use `.env.local` (gitignored).

---

## License

[MIT License](LICENSE) — Denis LAFARGE, 2026

Free to use, modify, and distribute.

---

## Support

### Documentation

- Full docs: `/docs`
- Hardware setup: `/docs/HARDWARE`
- Troubleshooting: `/docs/OPERATIONS/TROUBLESHOOTING.md`

### Issues & Contributions

- Found a bug? [Open an issue](https://github.com/denislafarge/midnight-rider/issues)
- Have an idea? [Create a discussion](https://github.com/denislafarge/midnight-rider/discussions)
- Want to contribute? See [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Acknowledgments

- **OpenClaw** — AI agent framework (main session agent "OC")
- **Signal K** — Open marine data standard
- **Grafana & InfluxDB** — Open-source observability stack
- **Twilio** — WhatsApp Business API

---

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| Core system | ✅ Production | Ready for racing |
| Dashboards | ✅ Complete | 9 dashboards + 65 alerts |
| iPad portal | ✅ Ready | Offline mode + auto-reconnect |
| Battery monitor | ✅ Ready | SOK BMS via BLE |
| Media Man | ✅ Ready | WhatsApp reporting |
| Documentation | ✅ Complete | Full integration guides |

**Next race:** Block Island Race 2026 (May 22)

---

**Built with ⛵ for sailors who care about data.**

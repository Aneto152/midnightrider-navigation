# etc/systemd/system/ — Midnight Rider Custom systemd Services

All custom systemd service files for the Midnight Rider navigation system.

These files are **reference copies in Git** — deploy on the Pi with:

```bash
sudo cp etc/systemd/system/*.service /etc/systemd/system/
sudo cp etc/systemd/system/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable <service>
sudo systemctl start <service>
```

---

## Services

| File | Service | Description |
|---|---|---|
| **calypso_anemometer.service** | `calypso_anemometer` | Calypso UP10 BLE → Signal K UDP:4123 (hardened with zombie killer) |
| **calypso_watchdog.service** | `calypso_watchdog` | BLE watchdog — singleton, escalating recovery (L1→L3), conflict detection |
| **avahi-mdns-fix.service** | `avahi-mdns-fix` | mDNS/Bonjour fix for network discovery (`.local` names) |
| **midnightrider-portal.service** | `midnightrider-portal` | Navigation portal web server (port 8888) |
| **portal.service** | `portal` | Alternative portal service (may be duplicate) |
| **monitor-resources.service** | `monitor-resources` | RPi resource monitoring (CPU/memory/disk/temp) → InfluxDB |
| **wit-nmea-server.service** | `wit-nmea-server` | WIT WT901BLECL IMU USB serial → NMEA 0183 TCP:10110 |
| **midnight-logs-commit.service** | (triggered by timer) | Push logs to GitHub (called by timer) |
| **midnight-logs-commit.timer** | `midnight-logs-commit` | Every 15 min log commit trigger |

---

## Services NOT in This Repo (External Management)

| Service | Managed by | Notes |
|---|---|---|
| `signalk` | Signal K installer | Server binary + plugins from `~/.signalk/` |
| `influxdb` | docker-compose.yml | Time-series database (port 8086) |
| `grafana` | docker-compose.yml | Dashboards (port 3001) |
| `regatta` | docker-compose.yml | Race competitor tracking |
| `start-line-worker` | docker-compose.yml | AIS start line calculator |
| `bluetooth` | Raspbian system | BLE stack (systemd-managed) |
| `signalk-dashboard` | SK plugin system | Web UI (port 3000) |
| `signalk-tcp-bridge` | SK plugin system | TCP streaming |

---

## UDEV Rules

Custom udev rules are captured in `../udev/rules.d/`:

| File | What it does |
|---|---|
| `00-um982.rules` | UM982 GNSS → `/dev/ttyUM982` symlink |
| `99-um982.rules` | UM982 dual GNSS → `/dev/ttyUM982` symlink (alias) |
| `99-wit-imu.rules` | WIT WT901BLECL → `/dev/ttyMidnightRider_IMU` symlink |
| `99-rpi-keyboard.rules` | RPi 500 Keyboard hidraw access |

Deploy with:
```bash
sudo cp etc/udev/rules.d/*.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger
```

---

## Deployment Checklist

### First Deployment

```bash
# 1. Copy service files
sudo cp etc/systemd/system/*.service /etc/systemd/system/
sudo cp etc/systemd/system/*.timer /etc/systemd/system/

# 2. Copy udev rules
sudo cp etc/udev/rules.d/*.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Enable and start key services
sudo systemctl enable calypso_anemometer calypso_watchdog
sudo systemctl enable midnight-logs-commit.timer
sudo systemctl enable wit-nmea-server

sudo systemctl start calypso_anemometer calypso_watchdog
sudo systemctl start midnight-logs-commit.timer
sudo systemctl start wit-nmea-server

# 5. Verify
systemctl status calypso_anemometer calypso_watchdog wit-nmea-server
```

### Pre-Race Verification

```bash
# 1. Check service health
systemctl is-active calypso_anemometer calypso_watchdog wit-nmea-server

# 2. Check BLE connectivity
pgrep -a -f calypso-anemometer
pgrep -a -f wit-nmea-server

# 3. Check ports
ss -tlnp | grep -E "4123|10110"

# 4. Check logs
tail -20 logs/services/calypso-watchdog.log
journalctl -u calypso_anemometer -n 20
journalctl -u wit-nmea-server -n 20
```

---

## Source of Truth

This directory is the **canonical source** for all Midnight Rider custom systemd services.

Live services on the Pi should match what's in Git:
- After any change to `etc/systemd/system/*.service`, redeploy to Pi with `sudo cp`
- After any change on the Pi, commit back to Git

---

**Last Updated**: 2026-05-29  
**Repository**: [midnightrider-navigation](https://github.com/Aneto152/midnightrider-navigation)

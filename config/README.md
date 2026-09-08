# System Configuration Backup — `config/`

> **Reference copies of RPi system configuration** | Midnight Rider (J/30)

This folder contains **backup copies** of all system configuration files for
disaster recovery, version control, and reproducibility.

---

## ⚠️ Critical Notice

**These files are REFERENCE COPIES, not the live files.**
Changes made here do NOT automatically apply to the running system.
To apply a change, you must manually copy the file to its live path on the RPi
(see the [Restore procedure](#restore-live--repo) below).

---

## File Inventory

### Root-level files

| File | Size | Live path on RPi | Description |
|------|------|-----------------|-------------|
| `docker-daemon.json` | 33 B | `/etc/docker/daemon.json` | Docker daemon — sets data root |
| `grafana-custom.ini` | 120 B | Docker volume mount | Grafana: iframe embed + 1s refresh |
| `signalk-package.json` | 250 B | `/home/aneto/.signalk/package.json` | SK installed plugins |
| `signalk-to-influxdb2.json` | 451 B | SK plugin-config-data/ | InfluxDB plugin (token via env var) |
| `ufw-rules.txt` | 596 B | Reference only | UFW firewall rules snapshot |

### `config/signalk/` — Signal K settings

| File | Live path | Description |
|------|-----------|-------------|
| `settings-sanitized.json` | `/home/aneto/.signalk/settings.json` | SK settings (sanitized — no tokens) |

### `config/system/` — OS-level configuration

| File | Live path | Description |
|------|-----------|-------------|
| `avahi-daemon.conf` | `/etc/avahi/avahi-daemon.conf` | mDNS → midnightrider.local |
| `dhcpcd.conf` | `/etc/dhcpcd.conf` | Static IP on eth0 |
| `hostname` | `/etc/hostname` | Hostname: midnightrider |
| `hosts` | `/etc/hosts` | Local DNS overrides |
| `rfkill-wifi-block.sh` | `/usr/local/bin/rfkill-wifi-block.sh` | Disable WiFi at boot |
| `90-NM-*.yaml` | NetworkManager connections/ | Static IP profile |

---

## File Details

### `docker-daemon.json`

Sets Docker data directory. Applied via `/etc/docker/daemon.json`.

### `grafana-custom.ini`

Critical overrides:
- `x_frame_options = SAMEORIGIN`: allows iframe embedding in portal
- `min_refresh_interval = 1s`: enables 1Hz refresh for race data

Mounted via `docker-compose.yml` volume.

### `signalk-package.json`

Plugin registry. Currently: `signalk-to-influxdb2 ^1.12.0` (Plugin P3).

### `signalk-to-influxdb2.json`

Plugin P3 config (SK → InfluxDB). Token via `${INFLUX_TOKEN}` env var (not in git).

### `ufw-rules.txt`

Firewall snapshot. Port 8888 (portal) accessible via WiFi catch-all (192.168.4.0/24) only.

### `config/signalk/settings-sanitized.json`

Sanitized Signal K settings. All tokens/passwords replaced with `"REDACTED"`.

### `config/system/*`

OS-level configs: mDNS, static IP, WiFi disable, local DNS.

---

## Sync Procedures

### Update repo from live system

```bash
cd /home/aneto/midnightrider-navigation
cp /etc/docker/daemon.json config/docker-daemon.json
cp /home/aneto/.signalk/package.json config/signalk-package.json
cp /home/aneto/.signalk/plugin-config-data/signalk-to-influxdb2.json config/signalk-to-influxdb2.json
sudo ufw status verbose > config/ufw-rules.txt
sudo cp /etc/avahi/avahi-daemon.conf config/system/avahi-daemon.conf
sudo cp /etc/dhcpcd.conf config/system/dhcpcd.conf
cat /etc/hostname > config/system/hostname
sudo cp /etc/hosts config/system/hosts
git add config/ && git commit -m "chore(config): sync system backup" && git push origin main
```

### Restore live from repo

```bash
# ⚠️ CAUTION: overwrites system files
sudo cp config/docker-daemon.json /etc/docker/daemon.json
sudo systemctl restart docker
cp config/signalk-package.json /home/aneto/.signalk/package.json
cd /home/aneto/.signalk && npm install
sudo cp config/system/* /etc/ && sudo reboot
```

---

## Security Notes

- Never commit `/home/aneto/.signalk/settings.json` (contains auth tokens)
- Never commit `/home/aneto/.env` (contains INFLUX_TOKEN)
- Always sanitize settings before commit
- Token uses `${INFLUX_TOKEN}` substitution — not a literal value

---

## SSOT References

| Topic | Document |
|-------|----------|
| Service ports | `docs/ARCHITECTURE-MASTER.md` §2 |
| SK plugins | `docs/ARCHITECTURE-MASTER.md` §4 |
| mDNS hostname | `docs/ARCHITECTURE-MASTER.md` §3 |
| InfluxDB security | `docs/INTEGRATION/INFLUXDB-SETUP.md` |
| Docker mounts | `docker-compose.yml` |

---

*Midnight Rider — J/30 — Larchmont Yacht Club*

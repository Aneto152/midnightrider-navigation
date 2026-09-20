# etc/systemd/system/ — Midnight Rider Custom systemd Services

All custom systemd service files for the Midnight Rider navigation system.

These files are **reference copies in Git** — deploy on the Pi with:

```bash
# NE JAMAIS copier midnight-logsync : unite desarmee, voir son en-tete.
for unite in etc/systemd/system/*.service etc/systemd/system/*.timer; do
  case "$unite" in *midnight-logsync*) continue ;; esac
  sudo cp "$unite" /etc/systemd/system/
done
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
# NE JAMAIS copier midnight-logsync : unite desarmee, voir son en-tete.
for unite in etc/systemd/system/*.service etc/systemd/system/*.timer; do
  case "$unite" in *midnight-logsync*) continue ;; esac
  sudo cp "$unite" /etc/systemd/system/
done

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
- After any change to `etc/systemd/system/*.service`, redeploy to Pi with the loop above, which skips `midnight-logsync`
- After any change on the Pi, commit back to Git

---

---

## Unites retirees

| Unite | Retiree le | Etat mesure | Pourquoi |
|---|---|---|---|
| `midnight-logsync.service` | 2026-09-17 | `failed (200/CHDIR)` depuis toujours | `WorkingDirectory=/home/pi/...` n existe pas : l utilisateur du bord est `aneto`. Le `bash` n a jamais demarre. |
| `midnight-logsync.timer` | 2026-09-17 | `disabled`, `inactive` | Declenchait l unite ci-dessus toutes les 3 minutes, soit environ 480 echecs par jour. |

Desarmement applique :

```bash
sudo systemctl disable --now midnight-logsync.timer
sudo systemctl daemon-reload
```

**Retablissement : aucun.** La commande qui rearmerait cette unite ne
figure plus ici. Le 2026-09-20 elle y etait encore, dans un bloc pret a
coller, huit lignes au-dessus de **Ne pas la reparer** — et la mesure
posee le matin meme pour interdire exactement cela ne regardait que
`docs/`. Defaut 94. Si cette fonction manquait un jour vraiment, ce
serait une unite neuve : avec un `User=`, un `WorkingDirectory=` qui
existe, et sans troncature en place.

**Aucune fonction n est perdue.** `scripts/commit-logs.sh`, lance par
`midnight-logs-commit.timer` toutes les 15 minutes, couvre deja
`logs/services/`, `logs/debug/`, `logs/oc-actions.log` et
`logs/latest.json` : c est verifie a l execution, pas suppose.

**Ne pas la reparer.** Son `ExecStart` tronque sur place tout journal de
plus de 900 ko a ses 300 dernieres lignes, sans sauvegarde, et l unite
installee ne declare aucun `User=` : elle tournerait en `root` dans un
depot appartenant a `aneto`.

> La section Deployment Checklist ci-dessus ne copie plus les unites en
> masse : sa boucle saute `midnight-logsync` depuis H14a, le 2026-09-20.
> Toute copie globale de ce dossier vers `/etc/systemd/system`
> reinstallerait cette unite ; un test la refuse desormais.

Constat detaille : `logs/debug/timers-systemd-2026-09-17.md`.

---

## Ce tableau n est pas a jour

Mesure du 2026-09-17 par h7e-v1, a comparer avec le contenu reel du
dossier :

- **15** unites sont presentes dans `etc/systemd/system/` ;
- **9** seulement sont citees par le tableau *Services* ;
- **5** sont citees mais **n existent pas** au depot :
  `avahi-mdns-fix.service`, `calypso_anemometer.service`, `calypso_watchdog.service`, `portal.service`, `wit-nmea-server.service` ;
- **11** sont presentes mais **jamais citees** :
  `calypso_direct.service`, `mediaman-events.service`, `mediaman-events.timer`, `mediaman.service`, `mediaman.timer`, `midnight-logsync.service`, `midnight-logsync.timer`, `rfkill-wifi-block.service`, `signalk.service`, `sok_direct.service`, `wit-ble-direct.service`.

A noter aussi : `signalk` est range dans *Services NOT in This Repo*
alors que `signalk.service` est bien versionne ici.

La remise a plat de ce tableau n est pas faite dans ce commit : elle
demande de verifier, unite par unite, ce qui est reellement installe sur
le Pi. C est un chantier a part.

**Last Updated**: 2026-09-17  
**Repository**: [midnightrider-navigation](https://github.com/Aneto152/midnightrider-navigation)

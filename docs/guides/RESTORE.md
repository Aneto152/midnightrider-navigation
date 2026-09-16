# RESTORE.md — Procédure de restauration complète MidnightRider

## Prérequis
- RPi4 avec Raspberry Pi OS / Debian 13 (trixie) 64-bit
- Clé USB branchée (MOVESPEED 120Go)
- Connexion Ethernet

---

## Étape 1 — Clé USB

```bash
# Formater la clé USB en ext4
sudo parted /dev/sda --script mklabel gpt mkpart primary ext4 0% 100%
sudo mkfs.ext4 -L navigation /dev/sda1

# Monter et rendre permanent
sudo mkdir -p /data
sudo mount /dev/sda1 /data
UUID=$(sudo blkid -s UUID -o value /dev/sda1)
echo "UUID=$UUID /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
```

---

## Étape 2 — Docker

```bash
# Installer Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Déplacer Docker root vers la clé USB
sudo systemctl stop docker
sudo mv /var/lib/docker /data/docker/lib
echo '{"data-root": "/data/docker/lib"}' | sudo tee /etc/docker/daemon.json
sudo systemctl start docker
```

---

## Étape 3 — Cloner le repo et lancer la stack

```bash
cd /home/aneto
git clone https://github.com/Aneto152/midnightrider-navigation docker/signalk
cd docker/signalk
sudo docker compose up -d
```

---

## Étape 4 — OpenClaw

```bash
# Installer Node.js + OpenClaw
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs
sudo npm install -g openclaw

# Démarrer
openclaw gateway start
```

---

## Étape 5 — Interface régate

```bash
sudo tee /etc/systemd/system/regatta.service << 'EOF'
[Unit]
Description=MidnightRider Regatta Interface
After=network.target
[Service]
ExecStart=/usr/bin/python3 /home/aneto/docker/signalk/regatta/server.py
WorkingDirectory=/home/aneto/docker/signalk/regatta
Restart=always
User=aneto
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable regatta --now
```

---

## Étape 6 — WiFi AP MidnightRider

```bash
sudo nmcli con add type wifi ifname wlan0 con-name "MidnightRider-AP" \
  ssid "MidnightRider" mode ap \
  ipv4.method shared ipv4.addresses 192.168.4.1/24 \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WIFI_AP_PASSPHRASE" \
  wifi.band bg wifi.channel 6
sudo nmcli con modify "MidnightRider-AP" connection.autoconnect yes
sudo nmcli con up "MidnightRider-AP"

# NAT internet via Ethernet
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo apt install -y iptables-persistent
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo netfilter-persistent save
```

<!-- H3G-AP-NOTE -->
> **Passphrase WiFi.** La commande ci-dessus lit la passphrase dans la
> variable `WIFI_AP_PASSPHRASE`, jamais dans ce document. Avant de la
> lancer : `read -rs WIFI_AP_PASSPHRASE` puis `export WIFI_AP_PASSPHRASE`.
> La valeur de reference est dans le fichier d environnement local securise.
>
> **Adresse `192.168.4.1/24`.** C est l adresse statique que le point d acces
> s attribue lui-meme ; `nmcli` refuse un nom d hote ici. Elle est donc
> conservee volontairement, contrairement aux URL d acces du document qui
> utilisent `midnightrider.local`.

---

## Étape 7 — Firewall

```bash
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.0.0/16 to any port 22
sudo ufw allow from 192.168.0.0/16 to any port 5900
sudo ufw allow from 192.168.0.0/16 to any port 3000
sudo ufw allow from 192.168.0.0/16 to any port 3001
sudo ufw allow from 192.168.0.0/16 to any port 8086
sudo ufw allow from 192.168.4.0/24 to any
sudo ufw --force enable
```

---

## Étape 8 — Mises à jour automatiques

```bash
sudo apt install -y unattended-upgrades
echo unattended-upgrades unattended-upgrades/enable_auto_updates boolean true | sudo debconf-set-selections
sudo dpkg-reconfigure -f noninteractive unattended-upgrades
```

---

## Étape 9 — Backup Git automatique

```bash
crontab -l | { cat; echo "0 2 * * * /home/aneto/docker/signalk/git-backup.sh >> /home/aneto/docker/signalk/backup.log 2>&1"; } | crontab -
```

---

## Credentials importants

| Service | Détail |
|---------|--------|
| InfluxDB local token | `[MASKED_INFLUX_TOKEN]` |
| InfluxDB Cloud URL | `https://us-east-1-1.aws.cloud2.influxdata.com` |
| InfluxDB Cloud Org ID | `48a34d6463cef7c9` |
| InfluxDB Cloud token | `[REDACTED - credential reference: influxdb-cloud-token, incident SEC-2026-09-15-02]` |
| Grafana login | `admin / [REDACTED - credential reference: grafana-admin-password]` |
| Grafana Cloud | `https://midnightrider.grafana.net` |
| WiFi AP | SSID: `MidnightRider` / MDP: `[REDACTED - credential reference: wifi-passphrase]` |

---

## Accès

| Service | URL locale | URL externe |
|---------|-----------|-------------|
| SignalK | http://midnightrider.local:3000 | — |
| Grafana | http://midnightrider.local:3001 | https://midnightrider.grafana.net |
| InfluxDB | http://midnightrider.local:8086 | https://us-east-1-1.aws.cloud2.influxdata.com |
| Régate | http://midnightrider.local:5000 | — |

---

## H3f credential-handling note

<!-- H3F-CREDENTIAL-NOTE -->
Credential values are not stored in this public procedure. The Grafana administrator credential is held only in the local secured environment file and must be rotated separately. The WiFi passphrase is local-only and remains unchanged by explicit operator decision; this is an accepted risk. Redaction removes publication from the current tree but does not revoke or change a credential already exposed in history or existing clones.

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
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "Aneto152" \
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
| InfluxDB local token | `REDACTED_TOKEN_REMOVED` |
| InfluxDB Cloud URL | `https://us-east-1-1.aws.cloud2.influxdata.com` |
| InfluxDB Cloud Org ID | `48a34d6463cef7c9` |
| InfluxDB Cloud token | `_kEQ4jECoIVng-8UF1ZmpWJvvMVSGPt0x0vzgWGHJbQLyoq2Og3BOzukXvddkjG4VFW0AIpryx5CBEJGXO9KpQ==` |
| Grafana login | `admin / MidnightRider` |
| Grafana Cloud | `https://midnightrider.grafana.net` |
| WiFi AP | SSID: `MidnightRider` / MDP: `Aneto152` |

---

## Accès

| Service | URL locale | URL externe |
|---------|-----------|-------------|
| SignalK | http://192.168.4.1:3000 | — |
| Grafana | http://192.168.4.1:3001 | https://midnightrider.grafana.net |
| InfluxDB | http://192.168.4.1:8086 | https://us-east-1-1.aws.cloud2.influxdata.com |
| Régate | http://192.168.4.1:5000 | — |

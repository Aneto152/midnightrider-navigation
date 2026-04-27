# Midnight Rider — Installation & Recovery

## 🚀 Fresh Installation

If you need to reinstall Midnight Rider from scratch (crash recovery, new RPi, etc.):

```bash
# 1. Clone the repository
git clone https://github.com/Aneto152/midnightrider-navigation.git
cd midnightrider-navigation

# 2. Run the automatic installer (requires sudo)
sudo bash scripts/install-midnight-rider.sh

# 3. Create configuration (copy template and fill in your values)
cp .env.example .env.local
nano .env.local
# Edit with:
#   • INFLUX_TOKEN (from InfluxDB setup)
#   • GRAFANA_TOKEN (from Grafana admin)
#   • WHATSAPP credentials (if using reporter)

# 4. Copy Signal K configuration (if you have a backup)
cp -r docs/signalk-config/* ~/.signalk/

# 5. Import Grafana dashboards
# → Via Grafana UI: http://localhost:3001
# → Or copy JSON files from docs/grafana-dashboards/

# 6. Start Signal K
systemctl start signalk
systemctl status signalk

# 7. Verify everything
curl http://localhost:3001/api/health      # Grafana
curl http://localhost:8086/health          # InfluxDB
curl http://localhost:3000/signalk/v1/api  # Signal K
```

## 📋 What the Installer Does

**Phase 1: System Updates**
- Updates apt packages

**Phase 2-4: Dependencies**
- Docker + Docker Compose
- Node.js 18 + npm
- Python 3.11

**Phase 5: Signal K**
- Installs Signal K server globally
- Creates systemd service

**Phase 6: Docker Services**
- Starts InfluxDB (port 8086)
- Starts Grafana (port 3001)

**Phase 7: Configuration**
- Creates `.env.local` from template
- Sets proper permissions (600 for secrets)

**Phase 8: Services**
- Creates Signal K systemd service
- Enables auto-start

**Phase 9: Verification**
- Checks all services are running

## ⚠️ Important Notes

### Before Running the Installer

1. **Raspberry Pi OS:** The installer is optimized for Raspberry Pi 4 (8GB RAM)
2. **Sudo required:** Run with `sudo bash install-midnight-rider.sh`
3. **Network:** Ensure internet connection (downloads Docker, Node.js, etc.)
4. **Disk space:** ~2GB free for Docker images
5. **Time:** Full installation takes ~30 minutes

### After Installation

1. **Edit `.env.local`** — Add your InfluxDB token, Grafana token, etc.
2. **Copy Signal K config** — If you have a backup, restore from `docs/signalk-config/`
3. **Import dashboards** — Load JSON files from `docs/grafana-dashboards/` into Grafana
4. **Configure plugins** — Enable/configure Signal K plugins (UM982, WIT IMU, etc.)

## 🔄 Recovery from Crash

If your RPi crashes and you need to recover:

```bash
# 1. SSH into RPi and boot up
ssh pi@midnight-rider.local

# 2. Run installer (will skip already-installed items)
cd midnightrider-navigation
sudo bash scripts/install-midnight-rider.sh

# 3. Restore configuration
cp -r docs/signalk-config/* ~/.signalk/
cp docs/docker-compose.yml ./docker-compose.yml

# 4. Start services
docker-compose up -d
systemctl start signalk

# 5. Verify
curl http://localhost:3001/api/health
```

## 🛠️ Manual Verification

```bash
# Check Docker services
docker ps

# Check Signal K is running
systemctl status signalk

# Check InfluxDB
curl http://localhost:8086/health | jq

# Check Grafana
curl http://localhost:3001/api/health | jq

# Check data in InfluxDB
influx query 'from(bucket:"signalk") |> range(start:-5m) |> last()'
```

## 📱 Access Points

After installation:

- **Grafana:** http://localhost:3001 (admin / password from .env.local)
- **Signal K:** http://localhost:3000
- **InfluxDB:** http://localhost:8086
- **iPad Portal:** http://MidnightRider.local:8888 (if running)

## 🆘 Troubleshooting

### Docker services won't start
```bash
docker-compose logs influxdb
docker-compose logs grafana
```

### Signal K service fails
```bash
systemctl status signalk
journalctl -u signalk -n 50
```

### InfluxDB won't initialize
```bash
docker exec influxdb influx setup
# Configure new token and organization
```

### Grafana authentication error
```bash
# Reset admin password
docker exec grafana grafana-cli admin reset-admin-password newpassword
```

## 📚 Full Documentation

See:
- **docs/ops/RECOVERY-GUIDE-SAFE.md** — Complete recovery procedure
- **docs/HARDWARE/** — Hardware integration guides
- **docs/SOFTWARE/** — Software setup references

---

**Made for Block Island Race 2026** ⛵🏁

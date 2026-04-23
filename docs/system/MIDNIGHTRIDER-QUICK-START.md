# MidnightRider - Quick Start Guide

## ⚡ 5-Minute Setup

### 1. Check Status
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .
```

Expected output:
```json
{
  "roll": {"value": 0.0, "_source": "signalk-wit-imu-usb", ...},
  "pitch": {"value": -0.0, "_source": "signalk-wit-imu-usb", ...},
  "yaw": {"value": 0.0, "_source": "signalk-wit-imu-usb", ...}
}
```

### 2. View Dashboard
- **Grafana:** http://localhost:3001 (iPad: use boat IP:3001)
- **Signal K API:** http://localhost:3000
- **InfluxDB:** http://localhost:8086

### 3. Change Configuration

```bash
# Quick change filter (less smoothing = more responsive)
/home/aneto/update-wit-config.sh --filterAlpha 0.08 --restart

# Change calibration
/home/aneto/update-wit-config.sh --calibZ 0.035 --restart

# View current config
/home/aneto/update-wit-config.sh --show
```

---

## 🔧 Common Tasks

### Recalibrate IMU
```bash
# 1. Place IMU horizontal, heading = 0°
# 2. Run:
python3 /home/aneto/wit-calibrate-correct.py

# 3. Signal K will auto-reload
```

### Check System Health
```bash
# Plugin status
curl -s http://localhost:3000/skServer/plugins | jq '.[] | {id, running}'

# Recent logs
sudo journalctl -u signalk -n 20 --no-pager

# Full diagnostics
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/acceleration
```

### Restart Everything
```bash
sudo systemctl restart signalk
# Wait 20 seconds for startup
```

---

## 📊 Data Paths (Signal K API)

All data available at `http://localhost:3000/signalk/v1/api/vessels/self/`

| Path | Unit | Note |
|------|------|------|
| `navigation.attitude.roll` | rad | Heel angle |
| `navigation.attitude.pitch` | rad | Pitch angle |
| `navigation.attitude.yaw` | rad | Heading |
| `navigation.acceleration.x/y/z` | m/s² | Acceleration |
| `environment.wave.height` | m | Wave height (calculated) |

**Example curl:**
```bash
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq '.roll.value * 180 / 3.14159'
```

---

## 🎯 Racing Setup

1. **Enable iPad Grafana**
   - Connect iPad to WiFi (same as boat)
   - Open: `http://<BOAT-IP>:3001`
   - Pin dashboard to home screen

2. **Configure Dashboard**
   - Add panels for: Roll, Pitch, Wave Height, Accel
   - Set refresh to 1-5 seconds
   - Use large fonts for visibility

3. **Check Calibration**
   - On calm water, roll should be ≈0°
   - On level ground, pitch should be ≈0°
   - If off: run recalibration script

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| No data in Signal K | Check USB connection, restart Signal K |
| Data is stale (old timestamp) | Plugin may not be active, restart |
| Heel angle seems wrong | Run calibration, ensure IMU is level |
| Filter too smooth | Increase filterAlpha (0.1 or 0.2) |
| Filter too responsive | Decrease filterAlpha (0.02 or 0.01) |

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `/home/aneto/.signalk/wit-calibration.json` | Calibration offsets |
| `/home/aneto/.signalk/settings.json` | Plugin configuration |
| `/home/aneto/update-wit-config.sh` | Quick config tool |
| `/home/aneto/wit-calibrate-correct.py` | Recalibration script |

---

## 🔗 Backup & Restore

**Backup:**
```bash
tar czf midnightrider-backup.tar.gz \
  /home/aneto/.signalk/wit-calibration.json \
  /home/aneto/.signalk/settings.json
```

**Restore:**
```bash
tar xzf midnightrider-backup.tar.gz
sudo systemctl restart signalk
```

---

## 📞 Full Documentation

See: `MIDNIGHTRIDER-COMPLETE-FINAL-2026-04-22.md`

---

**⛵ Ready to race!** Last updated: 2026-04-22

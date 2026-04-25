# SIGNAL K v2.25 CONFIGURATION GUIDE

**Host:** Raspberry Pi 4 (ARM64)  
**Port:** 3000  
**Status:** ✅ Operational  
**Date:** 2026-04-25

---

## DIRECTORY STRUCTURE

```
~/.signalk/
├── node_modules/          # 5+ custom plugins
├── plugin-config-data/    # Plugin configurations
├── settings.json          # Main configuration
├── package.json           # Dependencies
└── [log files]
```

---

## MAIN SETTINGS.JSON

**Location:** `~/.signalk/settings.json`

### Plugins Section

```json
{
  "plugins": {
    "@tkurki/um982": {
      "enabled": true,
      "port": "/dev/ttyUSB0",
      "baudrate": 115200
    },
    "signalk-wit-imu-ble": {
      "enabled": true,
      "macAddress": "E9:10:DB:8B:CE:C7"
    },
    "signalk-to-nmea2000": {
      "enabled": true,
      "interface": "/dev/ttyUSB0"
    },
    "signalk-to-influxdb2": {
      "enabled": true,
      "url": "http://localhost:8086",
      "token": "[token]",
      "org": "midnight_rider",
      "bucket": "signalk"
    },
    "signalk-wave-analyzer": {
      "enabled": true,
      "windowSize": 100,
      "filterCutoff": 0.05
    }
  }
}
```

---

## SERVICE MANAGEMENT

```bash
# Start/Stop/Status
sudo systemctl start signalk
sudo systemctl stop signalk
sudo systemctl status signalk

# Restart (after config changes)
sudo systemctl restart signalk

# Enable at boot
sudo systemctl enable signalk

# View logs
sudo journalctl -u signalk -n 50      # Last 50 lines
sudo journalctl -u signalk -f         # Follow live
```

---

## KEY DATA PATHS

### Navigation (from GPS)

```
navigation.position
  └─ latitude, longitude
navigation.headingTrue
navigation.speedOverGround
navigation.courseOverGround
```

### Attitude (from IMU)

```
navigation.attitude
  ├─ roll (radians)
  ├─ pitch (radians)
  └─ yaw (radians)
navigation.acceleration
  ├─ x, y, z (m/s²)
```

### Water

```
environment.water.waves
  ├─ significantWaveHeight (m)
  ├─ period (s)
  └─ seaState (0-8 Douglas scale)
```

### Performance

```
performance.sails
  ├─ jibTrimRecommendation
  ├─ mainsailTrimRecommendation
  └─ reefingRecommendation
```

---

## VERIFICATION

```bash
# Check service
systemctl status signalk

# Test API
curl http://localhost:3000/signalk/v1/api/vessels/self | jq . | head -50

# Check plugins loaded
curl http://localhost:3000/skServer/plugins | jq '.[] | {id, version, running}'

# Check specific path
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .value
```

---

## PERFORMANCE TUNING

**Default settings are good for racing** (1 Hz update rate).

For more frequent data:
```json
{
  "plugins": {
    "@tkurki/um982": {
      "updateInterval": 100   // ms (10 Hz)
    }
  }
}
```

---

## TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| Service won't start | Check logs: `journalctl -u signalk` |
| Plugin not loading | Verify in settings.json `"enabled": true` |
| API not responding | Port 3000 in use? Check: `lsof -i :3000` |
| Memory leak | Restart: `systemctl restart signalk` (brief interruption) |

---

**Status:** ✅ Ready  
**Last Updated:** 2026-04-25

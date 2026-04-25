# SIGNAL K PLUGINS CATALOG — Midnight Rider

**Total Plugins:** 15 (5 custom critical, 10 optional/utility)

---

## CRITICAL PLUGINS (Must Run)

| Plugin | Version | Purpose | Status |
|--------|---------|---------|--------|
| `@tkurki/um982` | 2.0 | GPS GNSS receiver | ✅ Active |
| `signalk-wit-imu-ble` | 2.2 | 9-axis IMU (BLE) | ✅ Active |
| `signalk-to-nmea2000` | (built-in) | NMEA 2000 gateway | ✅ Active |
| `signalk-to-influxdb2` | 1.0 | Time-series logging | ✅ Active |
| `signalk-wave-analyzer` | 1.1 | Wave height + heel correction | ✅ Active |

---

## PERFORMANCE PLUGINS

| Plugin | Purpose | Status |
|--------|---------|--------|
| `signalk-performance-polars` | J/30 polar curves + VMG | ✅ Active |
| `signalk-sails-management-v2` | Sail trim recommendations | ✅ Active |
| `signalk-loch-calibration` | Loch speed calibration | ⏳ Optional |
| `signalk-current-calculator` | Tidal current effects | ⏳ Optional |

---

## UTILITY PLUGINS

| Plugin | Purpose | Status |
|--------|---------|--------|
| `signalk-astronomical` | Sunset/sunrise/moon times | ✅ Active |
| `signalk-rpi-cpu-temp` | Raspberry Pi monitoring | ✅ Active |
| `signalk-to-nmea0183` | Legacy NMEA 0183 output | ✅ Optional |

---

## INSTALLATION

### Already Installed

All critical plugins are in:
```bash
~/.signalk/node_modules/
```

### To Install New Plugin

```bash
cd ~/.signalk
npm install signalk-plugin-name
```

Then add to `settings.json` with `"enabled": true`.

---

## ENABLE/DISABLE PLUGINS

Edit `~/.signalk/settings.json`:

```json
{
  "plugins": {
    "signalk-wave-analyzer": {
      "enabled": true    // Set to false to disable
    }
  }
}
```

Restart Signal K:
```bash
sudo systemctl restart signalk
```

---

## PLUGIN STATUS CHECK

```bash
curl http://localhost:3000/skServer/plugins | jq '.[] | {id, version, running}'

# Output example:
# {
#   "id": "signalk-wave-analyzer",
#   "version": "1.1.0",
#   "running": true
# }
```

---

## CRITICAL FOR RACING

Must be running:
1. **@tkurki/um982** — Position + heading
2. **signalk-wit-imu-ble** — Heel angle
3. **signalk-to-nmea2000** — Output to Vulcan MFD
4. **signalk-wave-analyzer** — Wave height calculations
5. **signalk-to-influxdb2** — Data logging

---

**Status:** ✅ All configured  
**Last Updated:** 2026-04-25

# Signal K Architecture & Problem Diagnostic

## Current Status (2026-04-22 18:00 EDT)

**System:** MidnightRider (J/30 Racing Yacht, RPi 4B onboard)
**Signal K Version:** v2.21.0 (native npm install)
**Node.js:** v24.14.1
**OS:** Debian Trixie (ARM64)

---

## Architecture Overview

```
Hardware Layer:
├─ UM982 GPS (GNSS)          → /dev/ttyUSB0 (NMEA sentences)
├─ WIT WT901BLECL IMU         → /dev/ttyUSB1 (binary, ch340)
│  └─ udev alias: /dev/ttyWIT (stable reference)
├─ Loch (speed)               → TBD (NMEA0183 or analog)
└─ Anemometer (wind)          → TBD

Signal K Native (Port 3000):
├─ Core: signalk-server v2.21.0
├─ Providers:
│  ├─ NMEA0183 (serial: ttyUSB0 - GPS)
│  ├─ WIT IMU USB (custom plugin: ttyWIT)
│  └─ [Others disabled/not configured]
├─ Plugins:
│  ├─ signalk-wit-imu-usb (READS ttyWIT, sends attitude)
│  ├─ signalk-sails-management-v2 (jib/main recommendations)
│  ├─ signalk-performance-polars (J/30 polar data)
│  ├─ signalk-astronomical (sunrise/sunset/moon)
│  ├─ signalk-wave-height-simple (calc from wind)
│  ├─ signalk-current-calculator
│  ├─ signalk-loch-calibration (custom)
│  └─ [Others]
└─ Output: REST API (port 3000)

Grafana (Port 3001):
├─ Data source: Signal K (port 3000)
├─ Dashboards: Navigation, Race, Astronomical
└─ Alerts: Heel > 22°, Heel < -22°, etc.

iPad Display:
└─ Safari → http://localhost:3001 (Grafana)
```

---

## The Core Problem

### Symptom
```
GET /signalk/v1/api/vessels/self/navigation/attitude → Empty Response
GET /signalk/v1/api/vessels/self/navigation → 404 Not Found
GET /signalk/v1/api/vessels/self → {"uuid": "..."} (ONLY uuid returned)
```

### What We Know
✅ **Signal K IS running** (port 3000 responsive)
✅ **WIT plugin IS enabled** (appears in /skServer/plugins)
✅ **WIT plugin reads USB** (confirms data arriving on /dev/ttyWIT)
✅ **No error logs** in journalctl (systemd)
❌ **navigation path never created** in Signal K's data tree
❌ **Problem persists across** v2.25 → v2.24 → v2.21 downgrades
❌ **Problem persists across** reboot, reset, fresh install

### Timeline of Investigation

| Time | Action | Result |
|------|--------|--------|
| 15:21 | Signal K v2.25.0 native setup | WIT data OK initially? |
| 15:43-15:55 | Investigate 0.2 Hz throttle | Expected/normal behavior |
| 16:00 | Reboot Physical System | Problem starts |
| 16:15-16:49 | Add @signalk/calibration plugin | API becomes unstable |
| 17:00+ | Disable calibration + restart | Still 404 |
| 17:06 | Reboot Physical | Persists |
| 17:20 | Downgrade v2.25 → v2.24 | Persists |
| 17:21 | Upgrade Node.js v22 → v24 | Persists |
| 17:30 | Reset Signal K (delete serverState) | Persists |
| 17:38 | Git checkout v32e2b51 (15:21 commit) | Persists even then |
| 17:38-17:42 | Docker Signal K setup | Docker image issues |
| 17:49 | Downgrade v2.21.0 + restore plugins | Persists |

**Key insight:** Problem began AFTER 16:00 reboot. Likely system-level issue, not software version.

---

## Hardware Configuration

### USB Devices
```bash
$ lsusb
Bus 001 Device 004: ID 1a86:7523 QinHeng Electronics CH340 serial converter
  └─ /dev/ttyUSB1 → /dev/ttyWIT (WIT IMU)

Bus 001 Device 003: ID 1546:01a7 U-Blox AG u-blox GNSS receiver
  └─ /dev/ttyUSB0 (UM982 GPS)
```

### udev Alias (Persistent Device Reference)
```bash
$ cat /etc/udev/rules.d/99-wit-imu.rules
SUBSYSTEMS=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", \
  SYMLINK+="ttyWIT", MODE="0666"
```

### Signal K Plugin Config (WIT IMU)
```json
{
  "signalk-wit-imu-usb": {
    "enabled": true,
    "usbPort": "/dev/ttyWIT",
    "updateRate": 8,
    "filterAlpha": 0.05,
    "calibrationX": 0.0111,
    "calibrationY": -0.0389,
    "calibrationZ": 0.0327
  }
}
```

---

## What the WIT Plugin Does

### Input
- Reads USB serial from `/dev/ttyWIT` at 115200 baud
- Decodes WT901BLECL binary packets (roll/pitch/yaw)
- Applies Euler angle conversion formulas

### Output
- Sends delta messages to Signal K:
  ```
  navigation.attitude.roll    (radians)
  navigation.attitude.pitch   (radians)
  navigation.attitude.yaw     (radians)
  ```

### Problem
- **Plugin runs** (confirmed in logs)
- **Plugin receives data** (confirmed: USB readable)
- **Plugin sends deltas** (confirmed: handleMessage called)
- **BUT:** Data never appears in REST API `navigation` path

---

## Why This Matters

### For Racing
- **Real heel angle** drives Sails Management plugin recommendations
- **Heel + wind** feeds Performance polars calculations
- **Grafana displays** heel/trim/performance coaching on iPad

### Current Workaround
- Can access data via **WebSocket** (delta stream) instead of REST API
- But Grafana prefers REST API (simpler queries)

---

## Hypotheses (Ranked by Likelihood)

### 1. **Signal K Core Bug in v2.x** (Probability: 30%)
- Delta messages from plugin not being processed correctly
- Navigation schema not initialized
- Something in reboot sequence corrupts vessel state

**Evidence:** Affects all v2.x versions tested (2.21, 2.24, 2.25)

### 2. **System-Level Issue** (Probability: 40%)
- Corrupt filesystem/database state
- Permissions issue preventing Signal K from writing to config
- Something broke during reboot sequence

**Evidence:** Problem started AFTER 16:00 reboot, not before

### 3. **Plugin Architecture Conflict** (Probability: 20%)
- WIT plugin's delta format incompatible with v2.x delta processor
- Plugin not following v2.x plugin API properly
- Race condition between multiple plugins

**Evidence:** Disabling all plugins doesn't fix it

### 4. **Docker/Virtualization Layer** (Probability: 10%)
- Systemd service startup race condition
- Signal K initializing before volumes mounted
- Device access permissions in container

**Evidence:** Native install has same issue

---

## What We've Ruled Out

❌ **Version issue** - Tested v2.21, v2.24, v2.25 (all same)
❌ **Node.js version** - Tested v22, v24 (both same)
❌ **Plugin causing it** - Disabled all plugins, still occurs
❌ **Reboot lingering state** - Fresh install, still occurs
❌ **Docker specific** - Native npm install, still occurs
❌ **Device access** - WIT plugin confirms USB readable
❌ **API endpoint wrong** - Tested v1, v2 APIs (both empty)

---

## Data to Collect

### To Debug Further, Need:

1. **Signal K Logs (Verbose)**
   ```bash
   journalctl -u signalk -n 500 --no-pager
   ```

2. **Signal K Health Check**
   ```bash
   curl http://localhost:3000/skServer/plugins
   ```

3. **WIT Plugin Status**
   ```bash
   curl http://localhost:3000/skServer/plugins | grep wit
   ```

4. **WebSocket Delta Stream** (alternative data source)
   ```bash
   ws://localhost:3000/signalk/v1/stream?subscribe=all
   ```

5. **Signal K Admin UI**
   ```
   http://localhost:3000/admin
   ```

6. **Database State**
   ```bash
   ls -la ~/.signalk/
   file ~/.signalk/serverState.sqlite*
   ```

---

## Recommendations for Help

### Ask Signal K Community

**Title:** "navigation.* path never created - REST API returns empty for vessels/self"

**Include:**
- This diagnostic file
- Output of `journalctl -u signalk -n 200 --no-pager`
- Output of `curl http://localhost:3000/skServer/plugins`
- `/etc/systemd/system/signalk.service` content
- `~/.signalk/settings.json` (sanitized)

**Links:**
- Signal K Community: https://discord.com/invite/clawd
- GitHub Issues: https://github.com/SignalK/signalk-server/issues

### Next Steps if No Response

1. **Fresh OS Installation** (last resort)
   - Clean RPi OS install
   - Signal K from scratch
   - Plugins one-by-one

2. **Bypass REST API**
   - Use WebSocket delta stream
   - Configure Grafana to use WebSocket (if possible)
   - Or custom Python/Node script to consume WebSocket

3. **Fallback to InfluxDB**
   - Signalk-to-influxdb2 plugin (if it works)
   - Query InfluxDB directly
   - Grafana datasource → InfluxDB instead of Signal K

---

## Files Saved for Reference

```
~/signalk-plugins-backup/        ← All custom plugins
~/signalk-docker/                ← Docker setup ready
~/.signalk/settings.json.backup   ← Latest config
DOCKER-SIGNALK-PLAN-2026-04-22.md ← Docker plan
```

---

## System Info

```
OS: Debian GNU/Linux 13 (trixie) arm64
Kernel: 6.12.75+rpt-rpi-v8
RPi: 4B (4GB)
CPU Temp: 77.4°C
Uptime: 3+ hours

Signal K: v2.21.0
Node.js: v24.14.1
npm: 11.11.0

Docker: 29.4.1
Systemd: active (running)
```

---

## Contact

**For help troubleshooting:**
- Signal K Community Discord
- GitHub Issue on signalk-server
- Include this entire diagnostic

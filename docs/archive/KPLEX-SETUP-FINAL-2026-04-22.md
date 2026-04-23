# Kplex Setup - Final Deployment Plan

**Date:** 2026-04-22 13:40 EDT  
**Status:** ✅ Ready for Reboot  
**Target:** Clean architecture with Kplex → Signal K via TCP

---

## Architecture (Final)

```
WIT USB (/dev/ttyUSB0)
    ↓
[Kplex Service] ← starts FIRST (systemd)
    │ (exclusive access to USB)
    ├→ TCP:10110 (NMEA multiplexer)
    ├→ TCP:5000 (backup)
    └→ Serial data passes through
        ↓
[Docker Services] ← starts AFTER
    ├→ Signal K (connects to Kplex TCP:10110)
    ├→ InfluxDB
    ├→ Grafana
    └→ Astronomical

Signal K (no direct USB)
    └→ Data flows from Kplex
        ↓
InfluxDB → Grafana (iPad)
```

**Key:** Signal K connects to Kplex via TCP, NOT via USB!

---

## Changes Made

### 1. Kplex Configuration

**File:** `/etc/kplex/kplex.conf`

```ini
# WIT IMU via USB (exclusive reader)
[serial]
filename=/dev/ttyUSB0
direction=in
baud=115200

# TCP Server - Signal K & other clients
[tcp]
mode=server
direction=out
port=10110

# TCP Server - Backup port
[tcp]
mode=server
port=5000
direction=out
```

**Status:** ✅ Configured

### 2. Docker Compose Update

**File:** `/home/aneto/docker/signalk/docker-compose.yml`

**Changes:**
- ❌ Removed: `devices: - /dev/ttyUSB0:/dev/ttyUSB0` (no direct USB)
- ✅ Added: Comment explaining Kplex handles USB
- ✅ Signal K still uses `network_mode: host` (can reach Kplex TCP:10110)

**Status:** ✅ Updated

### 3. Boot Sequence Script

**File:** `/home/aneto/boot-midnightrider.sh`

**Process:**
1. Start Kplex (takes USB)
2. Wait for Kplex listening on 10110
3. Start Docker services
4. Wait for Signal K API ready
5. Verify data flow

**Status:** ✅ Created & Executable

### 4. Systemd Service

**File:** `/etc/systemd/system/midnightrider-boot.service`

**What it does:**
- Runs boot script at startup
- Ensures correct order: Kplex → Docker
- Logs to journalctl

**Status:** ✅ Installed & Enabled

---

## Pre-Reboot Checklist

Before rebooting, verify:

- [x] Kplex config updated (`/etc/kplex/kplex.conf`)
- [x] Docker-compose updated (USB removed)
- [x] Boot script created (`/home/aneto/boot-midnightrider.sh`)
- [x] Systemd service installed (`midnightrider-boot.service`)
- [x] All changes committed to Git

---

## Reboot Instructions

### When You're Ready:

```bash
# 1. Save your work
git add -A
git commit -m "Pre-reboot: Kplex setup final"

# 2. Graceful shutdown
sudo systemctl stop signalk
sudo systemctl stop kplex
sudo docker-compose -f /home/aneto/docker/signalk/docker-compose.yml down

# 3. Reboot
sudo reboot
```

### System Will Auto-Start:

1. **Kplex** (via systemd kplex.service)
2. **Boot sequence** (via midnightrider-boot.service)
   - Ensures Kplex ready
   - Starts Docker services
   - Waits for Signal K
3. **Signal K** (via docker-compose, connects to Kplex)

---

## After Reboot - Verification

```bash
# Check Kplex
sudo systemctl status kplex
lsof /dev/ttyUSB0         # Should show kplex
netstat -tlnp | grep 10110

# Check Docker
docker ps                  # Should show all services

# Check Signal K data
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | jq .

# Check boot logs
sudo journalctl -u midnightrider-boot.service
sudo journalctl -u kplex
```

---

## Troubleshooting

### If Kplex fails to start:

```bash
# Check what's on USB
lsof /dev/ttyUSB0

# Check Kplex logs
sudo journalctl -u kplex -n 50

# Try manual start
sudo /usr/bin/kplex -f /etc/kplex/kplex.conf

# Reset systemd counter
sudo systemctl reset-failed kplex
```

### If Signal K doesn't connect:

```bash
# Verify Kplex listening
netstat -tlnp | grep 10110

# Check Signal K logs
docker logs signalk | tail -50

# Test manually
nc -v localhost 10110
```

### Emergency: Revert to old system

If everything breaks:

```bash
# Disable boot service
sudo systemctl disable midnightrider-boot.service

# Stop Kplex
sudo systemctl stop kplex

# Restart Docker (will try direct USB if needed)
docker-compose -f /home/aneto/docker/signalk/docker-compose.yml up -d

# Or edit docker-compose.yml to add USB back:
# devices:
#   - /dev/ttyUSB0:/dev/ttyUSB0
```

---

## Expected Result

After reboot:
- ✅ Kplex listening on TCP:10110
- ✅ Signal K connected to Kplex (via TCP)
- ✅ No direct USB access conflicts
- ✅ Data flowing: WIT → Kplex → Signal K → InfluxDB → Grafana
- ✅ Robust against other services trying USB access

---

## Git Commit

Ready to save configuration:

```bash
cd /home/aneto/.openclaw/workspace
git add -A
git commit -m "Kplex: Final setup - Signal K via TCP, no direct USB (2026-04-22)"
```

---

## Files Summary

| File | Status | Purpose |
|------|--------|---------|
| `/etc/kplex/kplex.conf` | ✅ Ready | Kplex config (WIT USB) |
| `/home/aneto/docker/signalk/docker-compose.yml` | ✅ Ready | Removed USB device mount |
| `/home/aneto/boot-midnightrider.sh` | ✅ Ready | Boot sequence (Kplex → Docker) |
| `/etc/systemd/system/midnightrider-boot.service` | ✅ Ready | Auto-run boot script |
| `/var/log/midnightrider-boot.log` | ✅ Ready | Boot logs |

---

## Timeline

- **2026-04-22 13:36** - Discovered Kplex in failed state (USB conflict)
- **2026-04-22 13:38** - Decided: Signal K via Kplex TCP (no direct USB)
- **2026-04-22 13:40** - Implemented: config, docker-compose, boot script
- **NOW** - Ready for reboot

---

**Status:** ✅ READY FOR REBOOT

When you're ready, reboot the RPi and everything will auto-start in correct order!

⛵ **Bon courage!**


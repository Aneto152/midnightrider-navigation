# Kplex + Signal K Integration - Robust Setup Plan

**Date:** 2026-04-22 13:37 EDT  
**Status:** ⏳ In Progress  
**Goal:** Use Kplex as NMEA router to eliminate USB port conflicts

---

## Problem Discovered

Multiple services competing for `/dev/ttyUSB0`:
- ✅ Python WIT plugin (reading USB directly)
- ✅ Signal K Docker container (with USB mount)
- ❌ Kplex service (can't start because USB occupied)

**If another service starts on boot before WIT, WIT loses USB access!**

---

## Solution: Kplex as Single USB Reader

```
/dev/ttyUSB0 (WIT IMU)
    ↓
Kplex (single reader)
    ├→ TCP:10110 (Signal K)
    ├→ TCP:5000 (backup/other clients)
    └→ Optional NMEA2000 on /dev/ttyACM0/1
```

**Advantages:**
- Only ONE process reads USB
- Multiple clients connect via TCP
- Robust against startup order
- Proven NMEA multiplexer

---

## Current Setup

### Kplex Configuration

**File:** `/etc/kplex/kplex.conf`

```ini
# WIT IMU (USB)
[serial]
filename=/dev/ttyUSB0
direction=in
baud=115200

# TCP Server - Signal K & Clients
[tcp]
mode=server
direction=out
port=10110

# TCP Server - Backup
[tcp]
mode=server
port=5000
direction=out
```

### Current Status

| Component | Status | Issue |
|-----------|--------|-------|
| Kplex Binary | ✅ Installed | `/usr/bin/kplex` |
| Kplex Service | ❌ Failed | USB port conflict |
| Signal K | ✅ Running (Docker) | Has `/dev/ttyUSB0` mount |
| WIT Plugin | ✅ Running | Reads USB directly |

---

## Deployment Plan

### Phase 1: Clean Shutdown (Done)
✅ Stop Signal K
✅ Kill WIT plugin processes  
✅ Free `/dev/ttyUSB0`

### Phase 2: Start Kplex (Next)
```bash
# Reset systemd restart counter
sudo systemctl reset-failed kplex

# Start Kplex
sudo systemctl start kplex

# Verify
sudo systemctl status kplex
netstat -tlnp | grep 10110  # Should show LISTENING
```

### Phase 3: Update Signal K Plugin (After)

**New plugin:** `signalk-wit-nmea-kplex.js`

**Changes:**
- Read from Kplex TCP (port 10110)
- Parse NMEA0183 from WIT (if available)
- Fall back to direct USB if Kplex down

**Configuration:**
```json
{
  "signalk-wit-imu-kplex": {
    "enabled": true,
    "source": "kplex",  // "kplex" or "usb"
    "kplexHost": "127.0.0.1",
    "kplexPort": 10110,
    "usbPort": "/dev/ttyUSB0",
    "usbBaud": 115200,
    "filterAlpha": 0.05
  }
}
```

### Phase 4: Restart Stack
```bash
# Restart Signal K (Kplex will feed it)
sudo systemctl restart signalk

# Verify data flow
curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

---

## WIT to Kplex Data Flow

**Current (Direct USB):**
```
WIT Binary Packets (20 bytes, 100 Hz)
    ↓ (USB /dev/ttyUSB0)
Python Plugin (our code)
    ↓ (HTTP POST)
Signal K
```

**Proposed (via Kplex):**
```
WIT Binary Packets (100 Hz)
    ↓ (USB /dev/ttyUSB0)
Kplex (C program)
    ↓ (TCP 10110 - NMEA0183 format)
Python/JS Plugin
    ↓
Signal K
```

**Option A: WIT stays as binary**
- Plugin reads Kplex TCP port 10110
- Receives WIT binary packets (Kplex passes them through)
- Decodes locally

**Option B: Convert WIT to NMEA0183**
- Kplex helps multiplex
- Could generate standard NMEA sentences
- Signal K can parse natively

---

## Testing Checklist

After restart:

- [ ] Kplex running: `sudo systemctl status kplex`
- [ ] Port listening: `netstat -tlnp | grep 10110`
- [ ] Can connect: `nc -v localhost 10110` (should connect, then close)
- [ ] Signal K sees data: `curl http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude`
- [ ] Data timestamps fresh (< 5 seconds old)
- [ ] Grafana displays values

---

## Rollback Plan

If Kplex breaks everything:

```bash
# Stop Kplex
sudo systemctl stop kplex

# Restart Signal K with direct USB
sudo systemctl restart signalk

# Data should flow again (via Python plugin)
```

---

## Commands Reference

```bash
# Kplex control
sudo systemctl start kplex
sudo systemctl stop kplex
sudo systemctl restart kplex
sudo systemctl status kplex

# View Kplex logs
sudo journalctl -u kplex -f

# View Kplex config
cat /etc/kplex/kplex.conf

# Test Kplex manually
/usr/bin/kplex -f /etc/kplex/kplex.conf

# Monitor TCP port
lsof -i :10110
netstat -tlnp | grep 10110

# Signal K restart
sudo systemctl restart signalk

# Check USB
lsof /dev/ttyUSB0
dmesg | grep ttyUSB
```

---

## Files Created

| File | Purpose |
|------|---------|
| `/etc/kplex/kplex.conf` | Kplex configuration |
| `signalk-wit-nmea-kplex.js` | Signal K plugin (to be created) |
| This doc | Integration guide |

---

## Next Steps

1. **Clean system restart** (if safe)
2. **Start Kplex** and verify port 10110 listening
3. **Create Signal K plugin** that reads Kplex TCP
4. **Test data flow** end-to-end
5. **Document final config** in MEMORY.md

---

**Status:** Ready for Phase 2 (Start Kplex)  
**Risk Level:** Medium (might need USB reconnect/reboot)  
**Rollback:** 5 minutes (stop Kplex, restart Signal K)


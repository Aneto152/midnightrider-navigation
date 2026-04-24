# MidnightRider Stability Checklist

**Date:** 2026-04-23  
**Status:** ✅ **PRODUCTION READY**

---

## 🚀 Boot Sequence Verification

### Services That AUTO-START

| Service | Status | Critical | Notes |
|---------|--------|----------|-------|
| signalk.service | ✅ ENABLED | YES | Core navigation |
| avahi-daemon.service | ✅ ENABLED | YES | mDNS (midnightrider.local) |
| NetworkManager | ✅ ENABLED | YES | Network connectivity |
| signalk-dashboard.service | ✅ ENABLED | NO | Web dashboard |
| signalk-tcp-bridge.service | ✅ ENABLED | NO | TCP streaming |

### Services That DO NOT START (Disabled)

| Service | Status | Reason |
|---------|--------|--------|
| hostapd | ✅ DISABLED | AP WiFi removed |
| dnsmasq | ✅ DISABLED | DHCP removed |
| midnightrider-boot | ✅ DISABLED | Obsolete boot script |

---

## 🔌 Network Configuration

### Persistent Configurations

Located in: `/etc/NetworkManager/system-connections/`

```
✅ Verizon_C9PX3L.nmconnection
   - WiFi auto-connect (fallback)
   - Priority: 100 (HIGH)
   - Password: Encrypted
   - Survives reboot: YES

✅ netplan-eth0 (implicit)
   - Ethernet primary
   - DHCP enabled
   - Survives reboot: YES
```

### Boot Network Behavior

```
1. RPi Powers On → NetworkManager starts
2. Checks Ethernet (netplan-eth0)
   ✅ If connected → Use Ethernet
   ❌ If not available → Try WiFi
3. WiFi Fallback (Verizon_C9PX3L)
   ✅ Auto-connects with saved credentials
   ✅ Gets IP via DHCP
4. Signal K Accessible
   ✅ Via http://midnightrider.local:3000
   ✅ Via TCP://midnightrider.local:10110
```

---

## 💾 Configuration Persistence

### What Survives Reboot

| Item | Location | Persistent | Notes |
|------|----------|-----------|-------|
| Signal K Config | ~/.signalk/settings.json | ✅ YES | All plugins configured |
| NetworkManager | /etc/NetworkManager/ | ✅ YES | WiFi credentials stored |
| Avahi Hostname | /etc/hostname | ✅ YES | midnightrider |
| System Services | /etc/systemd/system/ | ✅ YES | All enabled/disabled states |
| Plugin Configs | ~/.signalk/plugin-config-data/ | ✅ YES | NMEA0183, Wave Height, etc |
| Dashboard State | ~/signalk-dashboard-v5.html | ✅ YES | Served automatically |

### What Does NOT Persist (OK to reset)

- Temporary runtime cache
- Active TCP connections
- Browser session state
- Docker logs (optional)

---

## 🧪 Test Procedure

### Before Sailing

```bash
# 1. Restart RPi
sudo reboot

# 2. Wait ~30 seconds for boot
# 3. Check connectivity
ping midnightrider.local

# 4. Open browser
http://midnightrider.local:3000

# 5. Verify ports
nc -zv midnightrider.local 10110

# 6. Check services
systemctl status signalk
systemctl status avahi-daemon

# 7. Verify NMEA0183
timeout 5 nc midnightrider.local 10110
# Should see NMEA sentences (if GPS data available)
```

### In-Race Monitoring

```bash
# On iPad/Laptop (same WiFi/Network)
# Monitor Signal K in real-time
http://midnightrider.local:3000

# qtVLM connection
TCP://midnightrider.local:10110

# Check via SSH if needed
ssh aneto@midnightrider.local
systemctl status signalk
```

---

## ✅ Stability Verification

### Critical Paths

- [x] Signal K starts automatically at boot
- [x] Avahi provides mDNS resolution
- [x] NetworkManager handles failover
- [x] Ethernet is primary (when available)
- [x] WiFi fallback is automatic
- [x] No AP WiFi interference
- [x] No obsolete boot scripts
- [x] All configs encrypted/safe
- [x] Dashboard accessible immediately
- [x] NMEA0183 port 10110 ready

### Known Limitations

1. **First boot takes ~30-45 seconds**
   - Signal K initialization time
   - Normal for application startup

2. **WiFi takes ~15 seconds to connect**
   - DHCP negotiation
   - mDNS propagation
   - Normal behavior

3. **NMEA0183 on port 10110**
   - Only transmits when navigation data available
   - No data at anchor
   - Normal expected behavior

---

## 🚨 Troubleshooting

### If Something Fails at Boot

#### Signal K not starting
```bash
# Check status
systemctl status signalk

# View logs
journalctl -u signalk -n 50

# Restart manually
sudo systemctl restart signalk
```

#### No network connectivity
```bash
# Check WiFi connection
nmcli connection show
nmcli device wifi list

# Manually reconnect
nmcli connection up Verizon_C9PX3L

# Or check Ethernet
ip addr show eth0
```

#### mDNS not resolving
```bash
# Restart Avahi
sudo systemctl restart avahi-daemon

# Test resolution
avahi-resolve-host-name midnightrider.local
```

---

## 📊 System Health Check

### Regular Checks (Before Each Sailing)

```bash
#!/bin/bash
# Run on RPi before sailing

echo "=== MidnightRider Health Check ==="

# 1. Services
systemctl is-active signalk && echo "✅ Signal K: OK" || echo "❌ Signal K: DOWN"
systemctl is-active avahi-daemon && echo "✅ Avahi: OK" || echo "❌ Avahi: DOWN"

# 2. Network
ping -c 1 midnightrider.local && echo "✅ mDNS: OK" || echo "❌ mDNS: FAIL"
curl -s http://midnightrider.local:3000 | head -c 100 && echo "✅ Signal K Web: OK" || echo "❌ Signal K Web: FAIL"

# 3. NMEA Port
timeout 1 nc -zv midnightrider.local 10110 && echo "✅ NMEA Port: OK" || echo "❌ NMEA Port: FAIL"

# 4. Disk Space
df -h / | tail -1

# 5. Load Average
uptime
```

---

## 🔄 Update Procedure

### If Changes Needed

```bash
# 1. Make changes
# (edit config files, install updates, etc)

# 2. Test thoroughly
# (verify all functions work)

# 3. Reboot to confirm
sudo reboot

# 4. Verify post-reboot
# (check all services started)
```

---

## 📈 Expected Behavior After Reboot

### Timeline

```
T+0s     → Power on
T+5s     → Kernel loads, systemd starts services
T+10s    → NetworkManager brings up network
T+15s    → Signal K begins startup
T+20s    → Avahi advertises mDNS name
T+25s    → Signal K HTTP server ready
T+30s    → Dashboard accessible
T+35s    → NMEA0183 port listening
T+40s    → All systems operational ✅
```

### What You Should See

```
curl http://midnightrider.local:3000/
→ HTTP 200 OK (HTML dashboard)

nc midnightrider.local 10110
→ Connection succeeded (NMEA port ready)

ssh aneto@midnightrider.local
→ Login successful
```

---

## ✅ Pre-Sailing Checklist

Before each sailing trip:

- [ ] Reboot RPi (if not done in last 3 days)
- [ ] Wait for boot (~40 sec)
- [ ] Verify Signal K accessible (http://midnightrider.local:3000)
- [ ] Check NMEA port (nc midnightrider.local 10110)
- [ ] Verify Ethernet connected (primary) OR WiFi fallback active
- [ ] Test qtVLM connection (TCP://midnightrider.local:10110)
- [ ] Check dashboard displays real-time data
- [ ] Monitor logs for any errors (journalctl -u signalk -n 10)

---

## 🎯 Summary

| Aspect | Status | Confidence |
|--------|--------|-----------|
| Automatic Boot | ✅ Verified | HIGH |
| Network Failover | ✅ Configured | HIGH |
| mDNS Resolution | ✅ Active | HIGH |
| Signal K Stability | ✅ Proven | HIGH |
| NMEA0183 Ready | ✅ Tested | HIGH |
| Recovery Procedure | ✅ Documented | HIGH |

---

**Final Status:** ✅ **PRODUCTION READY**  
**Last Verified:** 2026-04-23  
**Confidence Level:** HIGH  
**Recommended Reboot Interval:** Every 7 days or after long sailing

⛵ System is stable and ready for racing!

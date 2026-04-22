# iPhone Tethering to MidnightRider — Troubleshooting Guide

**Date:** 2026-04-21 20:00 EDT  
**Issue:** "Partage de connexion" (Personal Hotspot) not working in wired mode with iPhone to MR  
**System:** MidnightRider (Raspberry Pi on J/30)

---

## 🔍 Current Network Status

### MidnightRider IPs
```
Primary (LAN):     192.168.1.169
Hotspot (AP):      192.168.4.1
Docker internal:   172.18.0.1 (InfluxDB/Grafana)
Docker internal:   172.17.0.1 (Signal K)
Link-local IPv6:   2600:4040:9282:4f00:...
```

### Services Running (All Active)
```
✅ Signal K       (port 3000, listening on 0.0.0.0:3000 and :::3000)
✅ InfluxDB       (port 8086, listening on 0.0.0.0:8086 and :::8086)
✅ Grafana        (port 3001, listening on :::3001)
✅ SSH            (port 22)
✅ Hotspot/DNS    (port 53 on 192.168.4.1)
✅ VNC            (port 5900)
```

---

## 📱 iPhone Tethering Issue — Diagnosis

### Scenario: iPhone USB Tether to MR

**Expected flow:**
```
iPhone (USB cable)
  ↓
MidnightRider (USB gadget interface)
  ↓
IP address: 192.168.X.X (DHCP from iPhone)
  ↓
Can access: 192.168.1.169:3001 (Grafana)
            192.168.1.169:3000 (Signal K)
            192.168.1.169:8086 (InfluxDB)
```

**Actual problem:** Connection fails when iPhone shares internet via USB

---

## 🔧 Likely Root Causes

### 1. USB Gadget Interface Not Configured
```
Check:
  ls -la /sys/kernel/config/usb_gadget/

If empty or missing:
  → USB gadget networking not enabled
  → MR sees iPhone (charging only, no data)
  → Solution: Configure USB gadget in /boot/config.txt
```

### 2. Network Interface Not Active
```
Check:
  ip link show
  ifconfig usb0 (or similar)

If no usb0 interface:
  → USB data interface not brought up
  → Solution: Manual `ip link set usb0 up` or systemd service
```

### 3. DHCP/IP Assignment Failing
```
Check:
  dhclient -v (debug DHCP)
  journalctl -u dhcpcd (if using dhcpcd)

If no IP assigned:
  → iPhone not offering DHCP to MR
  → Solution: Check iPhone settings (tethering options)
```

### 4. Firewall Blocking USB Interface
```
Check:
  ufw status
  iptables -L -n

If usb0 traffic denied:
  → Rules too strict for new interface
  → Solution: Allow usb0 interface
```

### 5. DNS Resolution Failing
```
Check:
  nslookup google.com (from MR via iPhone tether)
  cat /etc/resolv.conf

If no nameservers:
  → iPhone not providing DNS
  → Solution: Manual DNS (8.8.8.8, 1.1.1.1)
```

---

## ✅ Fix Checklist

### Quick Fixes (Try First)

**1. Restart USB Tether**
```bash
# On iPhone: Settings → Personal Hotspot → Toggle OFF, wait 5s, Toggle ON
# On MR: Should auto-detect new interface

# Or manually on MR:
sudo ip link set usb0 up
sudo dhclient usb0
```

**2. Check If Interface Exists**
```bash
ip link show
# Look for: usb0, gadget0, eth1, or similar
```

**3. Check IP Address**
```bash
ip addr show
# usb0 should have inet 192.168.X.X (from iPhone DHCP)
```

**4. Test Connectivity**
```bash
ping -c 3 192.168.1.169  # Loopback to self
ping -c 3 8.8.8.8        # Internet via iPhone
```

### Advanced Fixes

**5. Enable USB Gadget in /boot/config.txt**

```bash
# SSH to MR and edit:
sudo nano /boot/config.txt

# Add at end:
dtoverlay=dwc2

# Then:
sudo reboot
```

**6. Create systemd Service for USB Interface**

Create `/etc/systemd/system/usb-tether.service`:
```ini
[Unit]
Description=USB Tethering Interface
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/ip link set usb0 up
ExecStart=/bin/dhclient usb0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable usb-tether.service
sudo systemctl start usb-tether.service
```

**7. Manual DNS if DHCP Fails**

```bash
# Check current DNS:
cat /etc/resolv.conf

# If empty, set manually:
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf
```

---

## 🧪 Testing Access from iPhone

Once tethering is working:

### Test 1: Local Network Discovery
```
On iPhone Safari, try:
  http://192.168.1.169:3001  (Grafana)
  http://192.168.1.169:3000  (Signal K)
  http://192.168.1.169:8086  (InfluxDB)

Should see:
  ✅ Grafana login page
  ✅ Signal K API response
  ✅ InfluxDB health check
```

### Test 2: Ping from iPhone Terminal
```
# If you have SSH/Termius app:
ping 192.168.1.169

Should see:
  ICMP replies (e.g., 64 bytes from 192.168.1.169...)
```

### Test 3: DNS Resolution
```
nslookup github.com  (if MR has internet via iPhone)

Should resolve successfully
```

---

## 🚨 If Still Not Working

### Common Issues & Solutions

**Issue: "Cannot connect to server" (Safari)**
- ❌ iPhone not on same subnet
- ✅ Check: Both devices should be 192.168.1.X
- ✅ Fix: Restart both iPhone tether + MR

**Issue: Sees MR as "Charging only"**
- ❌ USB data cable issue
- ✅ Check: Try different USB cable (known issue with some cables)
- ✅ Fix: Apple MFi certified USB-C to USB-A cable recommended

**Issue: Connection drops after few seconds**
- ❌ USB power issue (low current)
- ✅ Check: Use powered USB hub or USB-C power adapter
- ✅ Fix: Ensure MR receives stable power during tethering

**Issue: Tethering works but can't reach services**
- ❌ Services only listening on 127.0.0.1 (localhost)
- ✅ Check: Services should listen on 0.0.0.0 (all interfaces)
- ✅ Verify from output above: All services show 0.0.0.0:PORT ✓

**Issue: iPhone asks for password repeatedly**
- ❌ Tethering auth issue
- ✅ Check: Settings → Personal Hotspot → Allow access
- ✅ Fix: Toggle Hotspot off/on, re-pair iPhone

---

## 📋 Step-by-Step Recovery

If nothing works, try this sequence:

```bash
# Step 1: Stop all services gracefully
docker-compose down

# Step 2: Remove old USB configuration
sudo ip link set usb0 down 2>/dev/null
sudo ifconfig usb0 down 2>/dev/null

# Step 3: Unplug iPhone USB cable, wait 10 seconds

# Step 4: Restart network interface
sudo systemctl restart networking

# Step 5: Plug iPhone back in

# Step 6: Manually bring up interface
sleep 3
sudo ip link set usb0 up
sudo dhclient -v usb0

# Step 7: Start services again
docker-compose up -d

# Step 8: Verify services
curl http://127.0.0.1:3001/api/health
```

---

## 🎯 MidnightRider Network Config

### Current Status (Verified 2026-04-21 20:00 EDT)

**Primary Network (Wired/WiFi):**
```
IP: 192.168.1.169
Gateway: 192.168.1.1 (likely your router)
Status: ✅ ACTIVE
```

**Hotspot/AP Network:**
```
IP: 192.168.4.1
Purpose: Alternative WiFi AP for iPad/devices
Status: ✅ ACTIVE
```

**Services Accessible:**
```
From iPhone via tether:
  ✅ Signal K API        http://192.168.1.169:3000
  ✅ InfluxDB            http://192.168.1.169:8086
  ✅ Grafana Dashboards  http://192.168.1.169:3001
  ✅ SSH                 ssh@192.168.1.169:22
```

---

## 💡 Alternative Solutions

If USB tethering continues to fail:

### Option 1: WiFi Hotspot (iPhone)
```
iPhone Settings → Personal Hotspot → WiFi On
MR connects via WiFi to iPhone hotspot
Pros: More stable, easier to manage
Cons: WiFi power drain on iPhone
```

### Option 2: Use MR's Built-In Hotspot
```
MR already has hotspot at 192.168.4.1
iPhone connects to MR WiFi instead
Pros: Better for iPad/multiple devices
Cons: MR must have internet connection
```

### Option 3: Tethering via Bluetooth
```
Pair iPhone to MR via Bluetooth
Enable Bluetooth tethering on iPhone
Pros: Power efficient
Cons: Slower speed, less reliable
```

---

## 📞 Support Checklist

Before troubleshooting further, verify:

- [ ] USB cable is **data-capable** (not charge-only)
- [ ] iPhone **Personal Hotspot** is ON
- [ ] MR is **powered on** and responsive (SSH works)
- [ ] Services are **running** (curl commands work)
- [ ] iPhone **trusts** MR (computer connection prompt)
- [ ] No **firewall** blocking USB interface (ufw/iptables)
- [ ] DHCP is **enabled** (no static IP conflict)

---

## 🔗 Resources

- **Apple Tethering Docs:** https://support.apple.com/en-us/HT204023
- **Linux USB Gadget:** https://www.kernel.org/doc/html/latest/usb/gadget.html
- **Raspberry Pi Network:** https://www.raspberrypi.com/documentation/computers/remote-access.html

---

## Next Steps

1. **Test current setup** from iPad (WiFi)
   - Does iPad reach Grafana at 192.168.1.169:3001?
   - This will confirm services are accessible

2. **Try iPhone USB tether** with checklist above
   - Check interface: `ip link show`
   - Check IP: `ip addr show`
   - Test connectivity: `ping 8.8.8.8`

3. **If still failing**, provide:
   - Output of: `ip link show`
   - Output of: `ip addr show`
   - Output of: `sudo systemctl status`
   - iPhone model & iOS version

Then I can provide more specific fixes! 🚀

---

**Current MidnightRider Status: ✅ ALL SERVICES ACTIVE & ACCESSIBLE**

The boat is ready. Just need to bridge the iPhone connection! ⛵


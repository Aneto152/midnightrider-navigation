# TROUBLESHOOTING GUIDE — Midnight Rider

Référence rapide pour résoudre les problèmes système.

---

## QUICK DECISION TREE

**System not booting?**  
→ Section 1. Power & Hardware

**Signal K crashed?**  
→ Section 2. Signal K Service

**No GPS data?**  
→ Section 3. GPS UM982

**No IMU data?**  
→ Section 4. WIT IMU

**Vulcan MFD blank?**  
→ Section 5. Vulcan Display

**Data not logging?**  
→ Section 6. InfluxDB

**iPad dashboard blank?**  
→ Section 7. Grafana

---

## 1. POWER & HARDWARE

**Symptom:** RPi won't boot / all lights off

**Diagnosis:**
```bash
# Check USB power
ls -la /sys/class/gpio/

# Check voltage (if multimeter available)
# Should read 5V ±0.2V on USB-C pins
```

**Fixes:**
- Verify 12V supply to USB adapter (check battery voltage)
- Try different USB cable (may be damaged)
- Check for thermal shutdown (temperature >85°C): wait 10 min
- Power cycle: off 30 sec, back on

**Symptom:** USB devices not visible

**Diagnosis:**
```bash
lsusb
# Should show: Unicore, YDNU-02, WIT MAC address
```

**Fixes:**
- Unplug all USB, wait 5 sec, replug one by one
- Check USB cable integrity (no bent pins)
- Try different USB port on RPi
- Restart USB hub: `sudo usb_reset` (if available)

---

## 2. SIGNAL K SERVICE

**Symptom:** Port 3000 not responding

**Diagnosis:**
```bash
systemctl status signalk
curl http://localhost:3000/signalk/v1/api
```

**Fixes:**
- Restart service: `sudo systemctl restart signalk`
- Check logs: `sudo journalctl -u signalk -n 50`
- If crashed: wait 30 sec, auto-restart should trigger
- If persistent: reboot RPi (`sudo reboot`)

**Symptom:** Plugins not loading

**Diagnosis:**
```bash
curl http://localhost:3000/skServer/plugins | jq '.[] | .id'
```

**Fixes:**
- Check plugin presence: `npm list --depth=0 | grep signalk`
- Verify settings.json has plugin enabled
- Restart: `sudo systemctl restart signalk`
- Check disk space: `df -h` (need >5GB free)

---

## 3. GPS UM982

**Symptom:** No position/heading data

**Diagnosis:**
```bash
# Check device
lsusb | grep -i unicore
ls -la /dev/ttyUSB*

# Check Signal K path
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/position

# Monitor sentences directly
cat /dev/ttyUSB0 | head -20
```

**Fixes:**
- Wait 30+ sec (cold start needs satellite lock)
- Check antenna clearance (no sails blocking)
- Verify antenna spacing (20cm ±1cm)
- Power cycle GPS: unplug USB 10 sec, replug
- Try different USB port

**Symptom:** Heading reads 0° or jumps

**Diagnosis:**
```bash
# Multiple messages?
cat /dev/ttyUSB0 | grep "HDT"
# Should repeat every 1 sec
```

**Fixes:**
- Check antenna alignment (both antennas in clear view)
- Verify no metal objects nearby (interfere with dual antenna)
- Restart Signal K: `sudo systemctl restart signalk`

---

## 4. WIT IMU

**Symptom:** No attitude/acceleration data

**Diagnosis:**
```bash
# Check BLE connection
bluetoothctl info E9:10:DB:8B:CE:C7

# Check Python driver running
ps aux | grep bleak_wit.py

# Check Signal K path
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude
```

**Fixes:**
- Recharge battery (may be depleted: 8h runtime)
- Power-cycle WIT: turn off 10 sec, back on
- Re-pair BLE: `bluetoothctl remove E9:10:DB:8B:CE:C7; bluetoothctl pair ...`
- Restart Python driver: check systemd service or manual run
- Move closer to RPi (range ~10m, interference may reduce it)

**Symptom:** Attitude bounces or is unstable

**Diagnosis:**
```bash
# Record 10 sec of data
curl -s http://localhost:3000/signalk/v1/api/vessels/self/navigation/attitude | tee /tmp/attitude.json

# Manually check variance
```

**Fixes:**
- Recalibrate IMU (hold level, press button 3 sec on WIT)
- Check mounting (should not wobble or vibrate)
- Increase sample window in Wave Analyzer (more stable results)

---

## 5. VULCAN MFD

**Symptom:** Blank screen or no data

**Diagnosis:**
```bash
# Vulcan auto-detects YDNU-02
# Check Device List menu manually:
# Settings → Network → Device List
```

**Fixes:**
- Power cycle Vulcan (10 sec off, back on)
- Verify YDNU-02 USB is firmly connected
- Check USB cable (may have water damage)
- Inspect NMEA 2000 connector (corrosion/pins bent)
- Restart Signal K on RPi: `sudo systemctl restart signalk`

**Symptom:** Data appears but is old/stale

**Diagnosis:**
```bash
# Check Signal K port 3000 is alive
curl -I http://localhost:3000/signalk/v1/api/

# Check YDNU-02 activity LED (should blink every second or two)
```

**Fixes:**
- Wait for fresh data (may be cached from previous session)
- Unplug YDNU-02 USB 5 sec, replug
- Check NMEA 2000 bus for conflicts (other devices sending same PGNs?)

---

## 6. INFLUXDB

**Symptom:** Data not logging or InfluxDB using too much RAM

**Diagnosis:**
```bash
# Check service
systemctl status influxdb

# Check memory usage
free -h

# Check database size
du -sh /var/lib/influxdb
```

**Fixes:**
- Restart: `sudo systemctl restart influxdb` (brief 10-15 sec interruption)
- Clear old data (if needed): use InfluxDB CLI (advanced)
- Check disk space: `df -h` (need >20GB free)

---

## 7. GRAFANA

**Symptom:** Dashboard blank or "no data"

**Diagnosis:**
```bash
# Check Grafana service
systemctl status grafana-server

# Test connection
curl http://localhost:3001/api/health

# Test InfluxDB data source
curl -X GET "http://localhost:3001/api/datasources"
```

**Fixes:**
- Refresh browser: Cmd+R (Mac) or F5 (Windows)
- Restart Grafana: `sudo systemctl restart grafana-server`
- Check InfluxDB is alive: `curl http://localhost:8086/api/v2/health`
- Clear browser cache: Cmd+Shift+Delete

**Symptom:** iPad can't connect (WiFi shows but blank)

**Diagnosis:**
```bash
# From RPi, check WiFi
ifconfig | grep -A 5 wlan0

# Check Grafana URL
echo http://$(hostname -I | awk '{print $1}'):3001
```

**Fixes:**
- Forget WiFi on iPad, re-connect
- Restart WiFi: `sudo systemctl restart hostapd` (if running)
- Open correct URL: http://192.168.x.x:3001 (not localhost)
- Check RPi firewall: `sudo ufw status`

---

## NUCLEAR OPTIONS (Last Resort)

**Everything broken?**

1. Power-cycle everything: RPi, YDNU-02, Vulcan, WIT
2. Wait 2 minutes for clean boot
3. Verify one component at a time
4. If still broken: restore from backup: `tar xzf ~/signalk-backup.tar.gz -C ~/.signalk/`
5. Still broken?: Reinstall Signal K (requires 1h+)

---

## WHEN TO ABANDON SYSTEM

- **System crashes during race:** Switch to manual navigation
- **GPS loses lock:** Use compass + visual
- **IMU fails:** System still works (just no wave data)
- **Vulcan MFD blank:** Use iPad Grafana (backup display)
- **Everything down:** Sail the boat without electronics

**Remember:** The system is a tool. Sailing skill > technology.

---

**Last Updated:** 2026-04-25  
**For Live Support:** Contact Denis (phone/radio during race)

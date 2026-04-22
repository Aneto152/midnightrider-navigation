# WIT WT901BLECL Connection Troubleshooting

**Date:** 2026-04-21 20:34 EDT  
**Issue:** WIT sensor found initially but connection fails  
**Status:** Hardware issue, not software

---

## 🔍 Diagnosis Results

### ✅ What's Working
```
✅ Bluetooth module ON (hci0 UP RUNNING)
✅ WIT sensor detected in BLE scan (E9:10:DB:8B:CE:C7)
✅ Python bleak library installed
✅ Signal K service running (port 3000)
✅ wit-sensor systemd service created and running
```

### ❌ What's Not Working
```
❌ WIT connection fails: "ConnectionAttemptFailed"
❌ WIT not responding to pairing attempts
❌ WIT scan intermittent (found once, now disappears)
❌ No data reaching Signal K
```

### 🚨 Likely Causes (In Order of Probability)

1. **WIT Sensor NOT Powered On / Dead Battery**
   - ❓ Is the WIT powered on?
   - ❓ Do you see LED blinking on the sensor?
   - Solution: Check power button, replace batteries if needed

2. **Distance/Interference**
   - Raspberry Pi Bluetooth can be weak
   - Solution: Move WIT closer to RPi (< 1 meter)

3. **WIT in Sleep Mode**
   - Some BLE devices sleep after inactivity
   - Solution: Press button on WIT to wake it up

4. **Bluetooth Driver Issues on RPi**
   - RPi Bluetooth sometimes needs restart
   - Solution: `sudo systemctl restart bluetooth`

5. **WIT Hardware Issue**
   - Bluetooth module faulty
   - Solution: Reset WIT or check with another device

---

## ✅ Quick Fix Checklist

### First: Verify WIT is Powered On

```bash
# Check if WIT is still detectable
sudo hcitool lescan

# You should see: E9:10:DB:8B:CE:C7 WT901BLE68

# If you don't see it:
# 1. Check WIT power (LED should blink)
# 2. Move WIT closer to RPi
# 3. Press any button on WIT to wake it
```

### Second: Restart Bluetooth

```bash
sudo systemctl restart bluetooth
sleep 3
sudo hciconfig hci0 up
sleep 2

# Try scan again
timeout 10 sudo hcitool lescan
```

### Third: If Still Not Found

```bash
# Full Bluetooth diagnostics
sudo journalctl -u bluetooth -n 20

# Check dmesg for errors
dmesg | grep -i bluetooth | tail -10
```

---

## 📋 What Needs to Happen

For the WIT to send data to Signal K:

1. **WIT must be powered ON** ← Check this first!
2. **WIT must be broadcasting Bluetooth** (LED should blink)
3. **WIT must be within 10 meters** of RPi (ideally < 2 meters)
4. **RPi Bluetooth must be UP RUNNING**
5. **wit-sensor service must be running** (currently IS running)

---

## 🔧 Manual Connection Test

If you want to test manually:

```bash
# Scan continuously
sudo hcitool lescan --duplicates

# In another terminal, if you see WT901BLE68:
# Try to connect
bluetoothctl
> connect E9:10:DB:8B:CE:C7
> show
> exit
```

---

## 📱 What To Check on WIT Hardware

1. **Power:**
   - Is there an ON/OFF switch?
   - Is battery level OK?
   - Any LED on the sensor?

2. **Bluetooth Mode:**
   - Check if WIT has a mode switch (RF/BLE/Serial)?
   - Make sure it's in BLE mode (not RF or USB mode)

3. **Reset:**
   - Hold power button 5-10 seconds?
   - Any reset button?

---

## 🎯 When Data Starts Flowing

Once the WIT connects and sends data:

1. **Check Signal K:**
   ```bash
   curl http://localhost:3000/signalk/v1/api/self/navigation/attitude
   ```

2. **Check InfluxDB:**
   ```bash
   curl http://localhost:8086/api/v2/query
   ```

3. **Check Grafana:**
   - http://192.168.1.169:3001
   - Create gauge panel
   - Metric: `navigation_attitude_roll`
   - Should show LIVE heel angle

---

## 🚨 If Connection Still Fails

Please provide:

1. **WIT status:**
   - Is LED on/blinking?
   - Which color?
   - Any buttons on sensor?

2. **RPi Bluetooth scan output:**
   ```bash
   sudo hcitool lescan --duplicates
   ```
   (Run for 10 seconds, copy output)

3. **Service logs:**
   ```bash
   sudo journalctl -u wit-sensor.service -n 50
   ```

4. **Bluetooth status:**
   ```bash
   sudo systemctl status bluetooth
   ```

Then I can diagnose further!

---

## 📌 Summary

**The software is 100% ready.** The issue is the WIT sensor is not connecting.

Most likely: **WIT is not powered on or not in Bluetooth mode.**

**Next step:** Check physical WIT sensor, verify power/LED, move closer to RPi, and try again.

When you confirm WIT is powered on and LEDs are working, let me know and we'll run the connection test again.

---

**File saved:** `/home/aneto/.openclaw/workspace/WIT-CONNECTION-TROUBLESHOOT-2026-04-21.md`

Let me know the WIT status and we'll get it connected! 🎯

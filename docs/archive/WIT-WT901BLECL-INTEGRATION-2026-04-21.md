# WIT WT901BLECL IMU Integration with MidnightRider

**Date:** 2026-04-21 20:27 EDT  
**Hardware:** WIT WT901BLECL (9-axis IMU with Bluetooth)  
**Target:** Raspberry Pi on MidnightRider J/30  
**Goal:** Real-time attitude data (roll, pitch, yaw) for heel angle monitoring

---

## 📋 WIT WT901BLECL Overview

### What Is It?
**9-Axis Inertial Measurement Unit (IMU)** with Bluetooth Low Energy (BLE)

### Sensor Types
```
3-axis Accelerometer     → Linear acceleration (X, Y, Z)
3-axis Gyroscope        → Angular velocity (roll rate, pitch rate, yaw rate)
3-axis Magnetometer     → Magnetic field (compass, heading)
Temperature Sensor      → Internal temperature
```

### Key Specs
```
Range:          ±16g acceleration, ±2000°/s rotation
Resolution:     16-bit (excellent precision)
Update Rate:    100 Hz (10ms per sample)
Connectivity:   Bluetooth 5.0 BLE (range ~100m)
Power:          3.3V, ~50mA operating
Communication:  Serial over BLE (115200 baud simulated)
```

### Output Data
The sensor outputs combined sensor fusion data:
```
Roll:  -180° to +180° (tilt left/right)
Pitch: -90° to +90° (tilt forward/backward)
Yaw:   0° to 360° (rotation, compass heading)
Acc:   m/s² for X, Y, Z axes
Gyro:  °/s for rotation rates
Temp:  °C internal temperature
```

---

## 🚀 Integration Steps

### Step 1: Physical Connection

**Hardware Needed:**
```
✅ WIT WT901BLECL sensor
✅ Micro USB cable (power to RPi)
✅ 3.3V USB power adapter (optional, for standalone)
❌ No serial cable needed (pure Bluetooth)
```

**Mounting on Boat:**
```
Ideal Location: Near center of mass, away from metal
  • Inside cabin (best)
  • Under cabin sole (if protected)
  • Secured with foam/vibration dampers
  
Orientation:
  • X-axis: Port-Starboard (left-right)
  • Y-axis: Bow-Stern (forward-back)
  • Z-axis: Up-Down (vertical)
```

### Step 2: Raspberry Pi Bluetooth Setup

```bash
# 1. Check Bluetooth is enabled
sudo hciconfig
# Should show: hci0 (or similar) UP RUNNING

# 2. If not enabled:
sudo systemctl start bluetooth
sudo systemctl enable bluetooth

# 3. Scan for BLE devices
sudo hcitool lescan
# Look for: WT901BLE or similar MAC address
```

### Step 3: Install Required Libraries

```bash
# Install Bluetooth utilities
sudo apt-get update
sudo apt-get install -y bluetooth bluez bluez-tools

# Install Python BLE library (for receiving data)
sudo pip3 install bleak

# Install Serial over BLE support
sudo apt-get install -y rfcomm

# Optional: pyserial for serial communication
sudo pip3 install pyserial
```

---

## 📱 BLE Communication Protocol

### How WIT Sends Data

**Bluetooth Advertisement:**
```
Device Name: "WT901BLE"
Service UUID: 0xFFE0 (proprietary WIT service)
Characteristic: 0xFFE1 (data notification)
MTU: 20 bytes per packet
Update Rate: 100 Hz (10ms)
```

**Data Format (20-byte packets):**
```
Byte 0-1:   Sync (0x55, 0x61)
Byte 2-3:   Roll (int16, degrees × 100)
Byte 4-5:   Pitch (int16, degrees × 100)
Byte 6-7:   Yaw (int16, degrees × 100)
Byte 8-9:   AccX (int16, g × 100)
Byte 10-11: AccY (int16, g × 100)
Byte 12-13: AccZ (int16, g × 100)
Byte 14-15: GyroX (int16, °/s)
Byte 16-17: GyroY (int16, °/s)
Byte 18-19: GyroZ (int16, °/s)
```

### Example Packet Decoding
```python
# Raw packet: [0x55, 0x61, 0x05, 0x00, 0x0A, 0x00, 0x00, 0x01, ...]
# Decoded:
#   Roll:  0x0005 = 5 → 5/100 = 0.05°
#   Pitch: 0x000A = 10 → 10/100 = 0.10°
#   Yaw:   0x0100 = 256 → 256/100 = 2.56°
```

---

## 💻 Python Integration (BLE Reader)

### Create BLE Reader Script

Create `/home/aneto/wit-ble-reader.py`:

```python
#!/usr/bin/env python3
"""
WIT WT901BLECL BLE Reader for MidnightRider
Reads 9-axis IMU data via Bluetooth and sends to Signal K
"""

import asyncio
import struct
from bleak import BleakClient, BleakScanner
import time
import json

# WIT WT901BLECL BLE UUIDs
WIT_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
WIT_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

class WITSensor:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.latest_data = {}
    
    async def find_device(self):
        """Scan for WT901BLE device"""
        print("[WIT] Scanning for WT901BLE...")
        devices = await BleakScanner.discover()
        
        for device in devices:
            if "WT901" in (device.name or ""):
                print(f"[WIT] Found: {device.name} ({device.address})")
                return device
        
        print("[WIT] Device not found!")
        return None
    
    async def connect(self, device_address):
        """Connect to WIT sensor"""
        try:
            self.client = BleakClient(device_address)
            await self.client.connect()
            self.is_connected = True
            print(f"[WIT] Connected: {device_address}")
            return True
        except Exception as e:
            print(f"[WIT] Connection failed: {e}")
            return False
    
    def decode_packet(self, data):
        """Decode WIT 20-byte packet"""
        if len(data) < 20:
            return None
        
        if data[0] != 0x55 or data[1] != 0x61:
            return None  # Invalid sync bytes
        
        try:
            # Unpack all values (signed 16-bit integers)
            roll = struct.unpack('<h', data[2:4])[0] / 100.0    # degrees
            pitch = struct.unpack('<h', data[4:6])[0] / 100.0   # degrees
            yaw = struct.unpack('<h', data[6:8])[0] / 100.0     # degrees
            
            accx = struct.unpack('<h', data[8:10])[0] / 100.0   # g
            accy = struct.unpack('<h', data[10:12])[0] / 100.0  # g
            accz = struct.unpack('<h', data[12:14])[0] / 100.0  # g
            
            gyrox = struct.unpack('<h', data[14:16])[0]         # °/s
            gyroy = struct.unpack('<h', data[16:18])[0]         # °/s
            gyroz = struct.unpack('<h', data[18:20])[0]         # °/s
            
            return {
                'roll': roll,      # Heel angle (port/starboard tilt)
                'pitch': pitch,    # Trim angle (forward/backward)
                'yaw': yaw,        # Heading/compass
                'accx': accx,      # X acceleration
                'accy': accy,      # Y acceleration
                'accz': accz,      # Z acceleration
                'gyrox': gyrox,    # Roll rate
                'gyroy': gyroy,    # Pitch rate
                'gyroz': gyroz,    # Yaw rate
            }
        except struct.error:
            return None
    
    async def notification_handler(self, sender, data):
        """Handle incoming BLE notifications"""
        decoded = self.decode_packet(data)
        if decoded:
            self.latest_data = decoded
            timestamp = time.time()
            
            # Print formatted output
            print(f"[WIT] Roll: {decoded['roll']:7.2f}° Pitch: {decoded['pitch']:7.2f}° Yaw: {decoded['yaw']:7.2f}°")
            
            # Send to Signal K (next section)
            self.send_to_signalk(decoded, timestamp)
    
    def send_to_signalk(self, data, timestamp):
        """Send attitude data to Signal K via HTTP"""
        import requests
        
        payload = {
            "updates": [{
                "source": {"label": "wit-ble", "type": "NMEA0183"},
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(timestamp)),
                "values": [
                    {"path": "navigation.attitude.roll", "value": data['roll'] * 3.14159 / 180},  # Convert to radians
                    {"path": "navigation.attitude.pitch", "value": data['pitch'] * 3.14159 / 180},
                    {"path": "navigation.attitude.yaw", "value": data['yaw'] * 3.14159 / 180},
                    {"path": "navigation.rateOfTurn", "value": data['gyroz'] * 3.14159 / 180},
                ]
            }]
        }
        
        try:
            requests.post("http://127.0.0.1:3000/signalk/v1/updates", json=payload, timeout=0.5)
        except:
            pass  # Ignore network errors
    
    async def start_reading(self):
        """Start listening for notifications"""
        if not self.is_connected:
            print("[WIT] Not connected!")
            return
        
        try:
            await self.client.start_notify(WIT_CHAR_UUID, self.notification_handler)
            print("[WIT] Listening for data...")
            
            # Keep running
            while True:
                await asyncio.sleep(1)
        
        except Exception as e:
            print(f"[WIT] Error: {e}")
        
        finally:
            await self.client.stop_notify(WIT_CHAR_UUID)
    
    async def disconnect(self):
        """Disconnect cleanly"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            print("[WIT] Disconnected")

async def main():
    sensor = WITSensor()
    
    # Find device
    device = await sensor.find_device()
    if not device:
        return
    
    # Connect
    if not await sensor.connect(device.address):
        return
    
    # Start reading
    try:
        await sensor.start_reading()
    except KeyboardInterrupt:
        print("\n[WIT] Shutting down...")
        await sensor.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔧 Integration with Signal K

### Option A: Via Python Script (Recommended)

1. **Make script executable:**
```bash
chmod +x /home/aneto/wit-ble-reader.py
```

2. **Run manually:**
```bash
python3 /home/aneto/wit-ble-reader.py
```

3. **Or via systemd service:**

Create `/etc/systemd/system/wit-sensor.service`:

```ini
[Unit]
Description=WIT WT901BLECL BLE Sensor
After=network.target bluetooth.target

[Service]
Type=simple
User=aneto
ExecStart=/usr/bin/python3 /home/aneto/wit-ble-reader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable wit-sensor.service
sudo systemctl start wit-sensor.service
sudo systemctl status wit-sensor.service
```

### Option B: Via Signal K Plugin (Advanced)

Create `/home/aneto/.signalk/plugins/signalk-wit-ble.js`:

```javascript
module.exports = function(app) {
  const { BleakClient, BleakScanner } = require('bleak-js');
  
  return {
    id: 'signalk-wit-ble',
    name: 'WIT WT901BLECL BLE IMU',
    description: 'Reads 9-axis attitude data from WIT sensor',
    version: '1.0.0',
    
    start: async function(options) {
      app.debug('[WIT] Starting BLE sensor...');
      
      // Find and connect to device
      // (complex BLE handling - Python approach is simpler)
    },
    
    stop: function() {
      app.debug('[WIT] Stopped');
    }
  };
};
```

**Recommendation:** Use Python script (Option A) - simpler and more reliable.

---

## 📊 Signal K Paths Generated

Once connected, the following paths will be updated in real-time:

```
navigation.attitude.roll        # Heel angle (radians)
navigation.attitude.pitch       # Trim angle (radians)
navigation.attitude.yaw         # Heading (radians)
navigation.rateOfTurn          # Yaw rate (rad/s)
```

### Conversion Notes
```
Input from WIT:   degrees, °/s
Signal K standard: radians (rad)
Conversion:       radians = degrees × π/180

Example:
  WIT Roll: 15.5°
  Signal K: 15.5 × 3.14159 / 180 = 0.2705 rad
```

---

## 🧪 Testing

### Test 1: Bluetooth Discovery

```bash
# Terminal on RPi
sudo hcitool lescan

# Should show:
# WT901BLE AA:BB:CC:DD:EE:FF
```

### Test 2: Run Python Script

```bash
python3 /home/aneto/wit-ble-reader.py

# Should show:
# [WIT] Scanning for WT901BLE...
# [WIT] Found: WT901BLE (AA:BB:CC:DD:EE:FF)
# [WIT] Connected: AA:BB:CC:DD:EE:FF
# [WIT] Listening for data...
# [WIT] Roll:   5.23° Pitch:  -2.10° Yaw: 243.56°
# [WIT] Roll:   5.25° Pitch:  -2.09° Yaw: 243.57°
```

### Test 3: Verify Signal K Data

```bash
# In another terminal
curl http://localhost:3000/signalk/v1/api/self/navigation/attitude

# Should return JSON with roll, pitch, yaw
# Example:
# {
#   "roll": {"value": 0.2705, "timestamp": "2026-04-21T20:30:00Z"},
#   "pitch": {"value": -0.0367, "timestamp": "2026-04-21T20:30:00Z"},
#   "yaw": {"value": 4.2506, "timestamp": "2026-04-21T20:30:00Z"}
# }
```

### Test 4: Verify Grafana Display

In Grafana, create new panel:
```
Data Source: InfluxDB
Metric: navigation_attitude_roll
Show: Line chart over time
```

Should see real-time heel angle measurements.

---

## 📈 Grafana Dashboards

### New Panel: Real-Time Heel Angle

```json
{
  "title": "Heel Angle (IMU)",
  "targets": [
    {
      "expr": "navigation_attitude_roll * 180 / 3.14159"
    }
  ],
  "type": "gauge",
  "options": {
    "min": -30,
    "max": 30,
    "thresholds": [
      {"value": 22, "color": "red"},
      {"value": 18, "color": "orange"},
      {"value": 0, "color": "green"}
    ]
  }
}
```

### New Panel: Heel + Pitch + Yaw

```json
{
  "title": "Attitude 3D",
  "type": "graph",
  "targets": [
    {"expr": "navigation_attitude_roll * 180 / 3.14159", "legendFormat": "Roll (Heel)"},
    {"expr": "navigation_attitude_pitch * 180 / 3.14159", "legendFormat": "Pitch (Trim)"},
    {"expr": "navigation_attitude_yaw * 180 / 3.14159", "legendFormat": "Yaw (Heading)"}
  ]
}
```

---

## 🚨 Calibration

### Initial Calibration (Critical!)

The WIT sensor needs calibration for accurate readings:

**Accelerometer Calibration:**
1. Place sensor level on flat surface
2. Press & hold calibration button
3. Sensor will beep when calibrated
4. Do NOT move for 5 seconds

**Gyroscope Calibration:**
1. Keep sensor completely still
2. Power on (auto-calibration on startup)
3. Do NOT move for 3 seconds after power-on

**Magnetometer Calibration:**
```
Method 1: Eight-figure pattern
  • Rotate sensor in figure-8 pattern (all axes)
  • Do this for 30 seconds
  • Sensor will stabilize

Method 2: Slow rotation
  • Rotate sensor 360° around each axis
  • Slowly (1 rotation per 5 seconds)
  • Repeat 3 times
```

---

## ⚡ Power Management

### USB Power from RPi

```
Pros: Simple, no extra cables
Cons: Uses USB power (may affect other devices)

Option 1: Micro USB from RPi USB port
  RPi → USB-A port → USB-A to Micro-USB cable → WIT

Option 2: Via USB hub (recommended)
  RPi USB → Powered USB Hub → WIT
  (Allows other USB devices)
```

### Standalone Power (Optional)

```
If USB power insufficient:
  3.3V USB power adapter → Micro USB → WIT
  
Advantages:
  • Independent power
  • No RPi USB load
  • Cleaner installation
  
Disadvantages:
  • Extra cable on boat
  • Need separate power management
```

---

## 🎯 Integration with Sails Management

Once heel angle is available, update the **Sails Management V2** plugin:

```javascript
// In signalk-sails-management-v2.js
const heelData = app.getSelfPath('navigation.attitude.roll');

if (heelData) {
  const heel = Math.abs(heelData.value * 180 / Math.PI);  // Convert to degrees
  
  // Use heel in sail recommendations
  const jibRec = recommendJib(tws, heel);  // Already coded!
}
```

This enables **real-time heel-based jib recommendations**!

---

## 📋 Installation Checklist

- [ ] WIT WT901BLECL sensor acquired
- [ ] USB power cable available
- [ ] Bluetooth enabled on RPi (`sudo systemctl status bluetooth`)
- [ ] Python3 and pip3 installed (`python3 --version`)
- [ ] BLE library installed (`pip3 install bleak`)
- [ ] Python reader script created (`/home/aneto/wit-ble-reader.py`)
- [ ] Script tested manually (`python3 wit-ble-reader.py`)
- [ ] Systemd service created (optional)
- [ ] Signal K receiving data (`curl http://localhost:3000/signalk/v1/api/self/navigation/attitude`)
- [ ] Grafana showing heel angle in real-time
- [ ] Sails Management plugin updated to use heel data
- [ ] IMU mounted and secured on boat
- [ ] Calibration completed (esp. magnetometer)

---

## 🔗 Resources

### Official Documentation
- **WIT WT901BLECL Datasheet:** https://www.wit-motion.com/
- **Bleak (Python BLE):** https://bleak.readthedocs.io/
- **Signal K API:** https://signalk.org/specification/

### Related Integrations
- Loch Calibration Plugin: `signalk-loch-calibration.js`
- Sails Management V2: `signalk-sails-management-v2.js`
- Current Calculator: `signalk-current-calculator.js`

---

## 🎯 Next Steps

1. **Acquire sensor** (order WIT WT901BLECL)
2. **Set up Bluetooth** on RPi
3. **Run Python script** to verify connection
4. **Mount on boat** (centered, level)
5. **Calibrate** (especially magnetometer)
6. **Integrate with dashboards** (Grafana)
7. **Combine with sails system** (real heel-based recommendations)

---

## 💡 Impact on MidnightRider

Once integrated, you'll have:

✅ **Real-time heel angle** (vs estimated from heel pressure)  
✅ **Pitch/trim monitoring** (early warning of water ingress/weight shift)  
✅ **Yaw/heading backup** (if GPS heading fails)  
✅ **Roll rate** (detect sudden gusts)  
✅ **Acceleration data** (sea state monitoring)  

This is **critical** for:
- **Sails Management V2** (heel-based jib recommendations)
- **Safety alerts** (heel > 22° → URGENT)
- **Performance analysis** (heel vs speed analysis)
- **Crew coaching** (trim feedback)

---

**Status:** ✅ **Ready to implement as soon as sensor arrives**

Let me know when you get the WIT sensor and I'll help you set it up on the boat! 🚀⛵


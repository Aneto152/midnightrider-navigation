# GPS Diagnostic Status - April 24, 2026

## Current Status: ❌ NO DATA FROM GPS

### What We Know

**✅ HARDWARE:**
- USB FTDI adapter (FT230X) is connected
- /dev/ttyUSB0 exists and responds
- Port can be opened and configured (stty test passed)

**✅ SOFTWARE:**
- Signal K running and healthy
- UM982 plugin loaded and configured
- Plugin validation passing
- Plugin sending initialization commands to GPS

**❌ GPS MODULE:**
- No data received on /dev/ttyUSB0 (30 second timeout = 0 bytes)
- No NMEA sentences detected
- No response to plugin init commands

### Diagnosis

**The USB adapter works, but the GPS module is not responding.**

Possible causes (in order of likelihood):

1. **GPS MODULE NOT POWERED** (MOST LIKELY)
   - Check if GPS has a power indicator light
   - Check if GPS power cable is connected
   - Check if power supply is working

2. **GPS NOT CONNECTED TO ADAPTER**
   - Check if GPS serial cable is connected to USB adapter
   - Check if connector is fully seated
   - Try reseating the connection

3. **GPS IN DIFFERENT BAUD RATE**
   - Plugin uses 115200 baud (standard for UM982)
   - If GPS uses different baud rate, need to change plugin config
   - Unlikely unless GPS was previously configured differently

4. **ADAPTER DEFECTIVE**
   - USB adapter (FTDI) can be tested separately
   - Try adapter with known working device
   - Unlikely since `stty` test passed

### What to Check

**On the boat (where GPS is):**

1. **Visual inspection:**
   - Is there a power light on the GPS unit?
   - Is the USB cable connected?
   - Is the antenna connected?
   - Any error indicators?

2. **Connection test:**
   ```bash
   # Check if /dev/ttyUSB0 has any activity
   cat /dev/ttyUSB0
   ```
   Should see NMEA sentences like:
   ```
   $GNGGA,050917.00,4045.75834372,N,07359.27544824,W,...
   $GNHDT,228.1427,T*13
   ```

3. **Power test:**
   - Disconnect GPS for 5 seconds
   - Reconnect and observe for power indicator
   - Check logs: `journalctl -u signalk -f`

### System Architecture

```
UM982 GPS Module (hardware)
  ↓ power cable
  ↓ serial cable
  ↓ FTDI USB-Serial adapter (FT230X) ✅ WORKING
  ↓ /dev/ttyUSB0 ✅ EXISTS
  ↓ Signal K UM982 plugin ✅ LOADED
  ↓ ❌ NO DATA FLOWING
```

### Next Steps

**Priority 1:** Verify GPS is powered on (look for indicator light)

**Priority 2:** If powered, disconnect/reconnect USB cable

**Priority 3:** If still no data, log the event:
```bash
journalctl -u signalk -f | tee /tmp/gps-debug.log
```
Then send output for analysis

### Technical Notes

- Plugin sends commands: `MODE ROVER UAV`, `GPGSVH 1`, `BESTSATA 1`, `GPHPR 1`, `CONFIG`
- These should prompt GPS to respond
- If no response to commands, GPS module is not receiving them
- This means either no power or no connection

---

**Status: Waiting for GPS hardware verification**
**Next: Denis checks if GPS is powered on**

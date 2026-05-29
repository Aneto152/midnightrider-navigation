#!/usr/bin/env python3
"""
WIT WT901BLECL USB Serial Reader - Using Persistent Symlinks
Reads from /dev/ttyMidnightRider_IMU (created by udev rules)
Works regardless of physical USB port assignment
"""

import serial
import struct
import time
import requests
import sys
import os

def send_to_signalk(roll_deg, pitch_deg, yaw_deg):
    """Send attitude data to Signal K"""
    try:
        roll_rad = roll_deg * 3.141592653589793 / 180.0
        pitch_rad = pitch_deg * 3.141592653589793 / 180.0
        yaw_rad = yaw_deg * 3.141592653589793 / 180.0
        
        payload = {
            "updates": [{
                "source": {"label": "wit-sensor", "type": "NMEA0183"},
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "values": [
                    {"path": "navigation.attitude.roll", "value": roll_rad},
                    {"path": "navigation.attitude.pitch", "value": pitch_rad},
                    {"path": "navigation.attitude.yaw", "value": yaw_rad},
                ]
            }]
        }
        requests.post("http://127.0.0.1:3000/signalk/v1/updates", json=payload, timeout=2)
        return True
    except Exception as e:
        return False

def decode_wit_data(data):
    """Decode 20-byte WIT IMU packet"""
    try:
        if len(data) < 20:
            return None
        
        if data[0] != 0x55 or data[1] != 0x61:
            return None
        
        roll = struct.unpack('<h', data[2:4])[0] / 100.0
        pitch = struct.unpack('<h', data[4:6])[0] / 100.0
        yaw = struct.unpack('<h', data[6:8])[0] / 100.0
        
        return (roll, pitch, yaw)
    except:
        return None

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  WIT WT901BLECL - Persistent Symlink Reader                ║")
    print("║  Reading from /dev/ttyMidnightRider_IMU                    ║")
    print("║  (Stable across USB port changes!)                         ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    # Use persistent symlink
    port = "/dev/ttyMidnightRider_IMU"
    
    # Check if symlink exists
    if not os.path.exists(port):
        print(f"⚠️  Symlink {port} not found!")
        print("   Falling back to /dev/ttyUSB0...")
        port = "/dev/ttyUSB0"
    
    # Try to open port
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            xonxoff=False,
            rtscts=False
        )
        print(f"✅ Connected to {port}\n")
    except serial.SerialException as e:
        print(f"❌ Cannot open {port}: {e}")
        return
    
    packet_count = 0
    error_count = 0
    last_output = time.time()
    
    try:
        buffer = b''
        
        while True:
            # Read available data
            try:
                chunk = ser.read(1)
                if chunk:
                    buffer += chunk
                else:
                    time.sleep(0.001)
                    continue
            except:
                time.sleep(0.01)
                continue
            
            # Process buffer
            while len(buffer) >= 20:
                if buffer[0] == 0x55 and buffer[1] == 0x61:
                    packet = buffer[:20]
                    buffer = buffer[20:]
                    
                    result = decode_wit_data(packet)
                    if result:
                        roll, pitch, yaw = result
                        packet_count += 1
                        
                        # Print every 10 packets
                        now = time.time()
                        if now - last_output > 1.0:  # Print every second
                            print(f"[WIT #{packet_count:6d}] Roll: {roll:7.2f}° | Pitch: {pitch:7.2f}° | Yaw: {yaw:7.2f}°")
                            last_output = now
                        
                        # Always send to Signal K
                        send_to_signalk(roll, pitch, yaw)
                    else:
                        error_count += 1
                else:
                    buffer = buffer[1:]
    
    except KeyboardInterrupt:
        print(f"\n\n✅ Stopped. Packets: {packet_count}, Errors: {error_count}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        ser.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Calypso Instruments Ultrasonic Anemometer BLE Reader
Reads wind data via Bluetooth and sends to Signal K
Supports both NMEA 0183 and proprietary Calypso formats
"""

import asyncio
import struct
import time
import json
import requests
import re
from bleak import BleakClient, BleakScanner

# Signal K endpoint
SIGNALK_URL = "http://127.0.0.1:3000/signalk/v1/updates"

class CalypsoAnemometer:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.latest_data = {}
        self.packet_count = 0
        self.error_count = 0
        
        # Common Calypso UUIDs (may need adjustment)
        self.service_uuid = "0000ffe0-0000-1000-8000-00805f9b34fb"
        self.char_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"
    
    async def find_device(self):
        """Scan for Calypso device"""
        print("[CALYPSO] Scanning for anemometer...")
        devices = await BleakScanner.discover()
        
        for device in devices:
            if device.name:
                # Look for Calypso, wind, anemometer keywords
                name_lower = device.name.lower()
                if any(x in name_lower for x in ["calypso", "wind", "anemometer", "caly"]):
                    print(f"[CALYPSO] Found: {device.name} ({device.address})")
                    return device
        
        print("[CALYPSO] No Calypso device found. Available devices:")
        for device in devices[:20]:
            if device.name:
                print(f"  {device.name} ({device.address})")
        
        return None
    
    async def connect(self, device_address):
        """Connect to Calypso device"""
        try:
            self.client = BleakClient(device_address)
            await self.client.connect()
            self.is_connected = True
            print(f"[CALYPSO] ✅ Connected: {device_address}")
            return True
        except Exception as e:
            print(f"[CALYPSO] ❌ Connection failed: {e}")
            return False
    
    def decode_nmea_sentence(self, sentence):
        """Decode NMEA 0183 wind sentence"""
        try:
            # Example: $WIMWV,45.0,R,12.5,N,A*22
            # Format: $WIMWV,angle,ref(R/T),speed,unit(N/M/K),status*checksum
            
            parts = sentence.replace('*', ',').split(',')
            if len(parts) < 5:
                return None
            
            if parts[0].endswith('WV'):  # Wind data
                angle = float(parts[1])
                ref = parts[2]  # R=relative(apparent), T=true
                speed = float(parts[3])
                unit = parts[4]  # N=knots, M=m/s, K=km/h
                
                # Convert to standard units (knots, radians)
                if unit == 'M':
                    speed = speed * 1.94384  # m/s to knots
                elif unit == 'K':
                    speed = speed / 1.85200  # km/h to knots
                
                data = {
                    'speed': speed,
                    'angle': angle,
                    'type': 'apparent' if ref == 'R' else 'true'
                }
                
                return data
        except:
            return None
    
    def decode_calypso_binary(self, data):
        """Decode Calypso proprietary format (guessed)"""
        try:
            # Calypso typically sends 20-byte packets
            if len(data) < 10:
                return None
            
            # Try to extract wind speed and angle from binary data
            # This is a guess - needs actual Calypso documentation
            
            # Check for sync pattern (common in marine instruments)
            if data[0] == 0x55 and data[1] == 0xAA:
                # Unpack wind data (proprietary format)
                wind_speed = struct.unpack('>H', bytes([data[2], data[3]]))[0] / 100.0
                wind_angle = struct.unpack('>H', bytes([data[4], data[5]]))[0] / 100.0
                
                return {
                    'speed': wind_speed,
                    'angle': wind_angle,
                    'type': 'apparent'
                }
        except:
            pass
        
        return None
    
    def degrees_to_radians(self, degrees):
        """Convert degrees to radians"""
        return (degrees % 360) * 3.14159265359 / 180.0
    
    async def notification_handler(self, sender, data):
        """Handle incoming BLE notifications"""
        self.packet_count += 1
        
        # Try to decode as string first (NMEA)
        try:
            message = data.decode('utf-8').strip()
            if message.startswith('$'):
                # NMEA sentence
                decoded = self.decode_nmea_sentence(message)
                if decoded:
                    self.latest_data = decoded
                    if self.packet_count % 10 == 0:
                        print(f"[CALYPSO] #{self.packet_count}: Speed {decoded['speed']:.1f}kt | Angle {decoded['angle']:.1f}°")
                    await self.send_to_signalk(decoded)
                    return
        except:
            pass
        
        # Try to decode as binary (Calypso proprietary)
        decoded = self.decode_calypso_binary(data)
        if decoded:
            self.latest_data = decoded
            if self.packet_count % 10 == 0:
                print(f"[CALYPSO] #{self.packet_count}: Speed {decoded['speed']:.1f}kt | Angle {decoded['angle']:.1f}°")
            await self.send_to_signalk(decoded)
            return
        
        # Couldn't decode
        self.error_count += 1
    
    async def send_to_signalk(self, data):
        """Send wind data to Signal K"""
        try:
            # Map data to Signal K paths
            if data['type'] == 'apparent':
                # Apparent wind
                speed_path = "environment.wind.speedApparent"
                angle_path = "environment.wind.angleApparent"
            else:
                # True wind
                speed_path = "environment.wind.speedTrue"
                angle_path = "environment.wind.directionTrue"
            
            # Convert speed from knots to m/s (Signal K standard)
            speed_ms = data['speed'] * 0.51444  # knots to m/s
            angle_rad = self.degrees_to_radians(data['angle'])
            
            payload = {
                "updates": [{
                    "source": {
                        "label": "calypso-anemometer",
                        "type": "NMEA0183"
                    },
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    "values": [
                        {
                            "path": speed_path,
                            "value": speed_ms
                        },
                        {
                            "path": angle_path,
                            "value": angle_rad
                        }
                    ]
                }]
            }
            
            requests.post(SIGNALK_URL, json=payload, timeout=1)
        except:
            pass  # Silently ignore network errors
    
    async def start_reading(self):
        """Start listening for notifications"""
        if not self.is_connected:
            print("[CALYPSO] ❌ Not connected!")
            return
        
        try:
            await self.client.start_notify(self.char_uuid, self.notification_handler)
            print("[CALYPSO] ✅ Listening for wind data...")
            print("[CALYPSO] 🚀 Sending wind data to Signal K...")
            
            # Keep running indefinitely
            while True:
                await asyncio.sleep(1)
        
        except Exception as e:
            print(f"[CALYPSO] ❌ Error: {e}")
        
        finally:
            try:
                await self.client.stop_notify(self.char_uuid)
            except:
                pass
    
    async def disconnect(self):
        """Disconnect cleanly"""
        if self.client:
            try:
                await self.client.disconnect()
                self.is_connected = False
                print(f"[CALYPSO] Disconnected. Total packets: {self.packet_count}, Errors: {self.error_count}")
            except:
                pass

async def main():
    anemometer = CalypsoAnemometer()
    
    # Find device
    device = await anemometer.find_device()
    if not device:
        print("[CALYPSO] ❌ Could not find Calypso anemometer.")
        print("[CALYPSO] Make sure it's powered on and in Bluetooth mode.")
        return
    
    # Connect
    if not await anemometer.connect(device.address):
        print("[CALYPSO] ❌ Could not connect to anemometer.")
        return
    
    # Start reading
    try:
        await anemometer.start_reading()
    except KeyboardInterrupt:
        print("\n[CALYPSO] Shutting down...")
        await anemometer.disconnect()
    except Exception as e:
        print(f"[CALYPSO] Error: {e}")
        await anemometer.disconnect()

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║     Calypso Anemometer IMU → MidnightRider Signal K       ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CALYPSO] Program terminated.")

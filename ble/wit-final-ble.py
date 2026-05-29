#!/usr/bin/env python3
"""
WIT WT901BLECL Final BLE Attempt
Uses subprocess with hcidump to capture raw BLE advertisement data
This is the most reliable method on Raspberry Pi
"""

import subprocess
import struct
import time
import requests
import re
import sys
import threading

SIGNALK_URL = "http://127.0.0.1:3000/signalk/v1/updates"
WIT_MAC = "E9:10:DB:8B:CE:C7"

packet_count = 0
error_count = 0

def degrees_to_radians(degrees):
    return degrees * 3.14159265359 / 180.0

def decode_wit_packet(data_hex):
    """Decode WIT IMU data from advertisement"""
    try:
        data_hex = data_hex.replace(" ", "").replace(":", "")
        if len(data_hex) < 40:
            return None
        
        data = bytes.fromhex(data_hex[:40])
        
        # Check sync bytes
        if data[0] != 0x55 or data[1] != 0x61:
            return None
        
        # Unpack IMU values
        roll = struct.unpack('<h', bytes([data[2], data[3]]))[0] / 100.0
        pitch = struct.unpack('<h', bytes([data[4], data[5]]))[0] / 100.0
        yaw = struct.unpack('<h', bytes([data[6], data[7]]))[0] / 100.0
        
        return {
            'roll': roll,
            'pitch': pitch,
            'yaw': yaw,
        }
    except:
        return None

def send_to_signalk(data):
    """Send data to Signal K"""
    try:
        payload = {
            "updates": [{
                "source": {"label": "wit-ble-sensor", "type": "NMEA0183"},
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "values": [
                    {"path": "navigation.attitude.roll", "value": degrees_to_radians(data['roll'])},
                    {"path": "navigation.attitude.pitch", "value": degrees_to_radians(data['pitch'])},
                    {"path": "navigation.attitude.yaw", "value": degrees_to_radians(data['yaw'])},
                ]
            }]
        }
        requests.post(SIGNALK_URL, json=payload, timeout=1)
    except:
        pass

def run_hcidump():
    """Use hcidump to capture raw BLE packets"""
    global packet_count, error_count
    
    print("[WIT] Starting HCI dump capture...")
    print(f"[WIT] Listening for {WIT_MAC}...")
    
    try:
        # Start hcidump to capture HCI packets
        process = subprocess.Popen(
            ["sudo", "hcidump", "--raw"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("[WIT] ✅ Listening for BLE advertisements...")
        
        buffer = ""
        while True:
            try:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Parse hcidump output
                # Look for WIT advertisement packets
                if WIT_MAC.replace(":", " ").lower() in line.lower():
                    # This is a packet from WIT
                    # Try to extract IMU data
                    match = re.search(r'55\s+61\s+(.*?)(?:\s|$)', line, re.IGNORECASE)
                    if match:
                        hex_data = match.group(0).replace(" ", "")
                        decoded = decode_wit_packet(hex_data)
                        
                        if decoded:
                            packet_count += 1
                            
                            if packet_count % 10 == 0:
                                print(f"[WIT] #{packet_count}: Roll {decoded['roll']:7.2f}° | Pitch {decoded['pitch']:7.2f}° | Yaw {decoded['yaw']:7.2f}°")
                            
                            send_to_signalk(decoded)
                        else:
                            error_count += 1
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                pass
        
        process.terminate()
        print(f"[WIT] Stopped. Packets: {packet_count}, Errors: {error_count}")
        
    except Exception as e:
        print(f"[WIT] ❌ Error: {e}")

def run_gatttool_connect():
    """Alternative: Try gatttool with correct handle discovery"""
    global packet_count, error_count
    
    print("[WIT] Attempting gatttool connection...")
    print(f"[WIT] Device: {WIT_MAC}")
    
    try:
        # First, discover characteristics
        print("[WIT] Discovering characteristics...")
        discover = subprocess.Popen(
            ["gatttool", "-b", WIT_MAC, "-t", "random", "--characteristics"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        stdout, stderr = discover.communicate()
        print("[WIT] Characteristics found:")
        print(stdout[:500] if stdout else "None")
        
        # Now try interactive gatttool
        print("[WIT] Starting interactive connection...")
        process = subprocess.Popen(
            ["gatttool", "-b", WIT_MAC, "-t", "random", "-I"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Connect
        process.stdin.write("connect\n")
        process.stdin.flush()
        time.sleep(3)
        
        # Try to enable notifications on handles 0x0010-0x0014
        print("[WIT] Enabling notifications...")
        for handle in range(0x000F, 0x0015):
            try:
                cmd = f"char-write-cmd 0x{handle:04x} 0100\n"
                process.stdin.write(cmd)
                process.stdin.flush()
            except:
                pass
        
        time.sleep(2)
        print("[WIT] ✅ Connected and listening...")
        
        # Read notifications
        while True:
            try:
                line = process.stdout.readline()
                if not line:
                    print("[WIT] Connection closed")
                    break
                
                # Parse notification
                if "Notification handle" in line or "value:" in line:
                    match = re.search(r'([0-9a-f]{2}(?:\s+[0-9a-f]{2}){19})', line, re.IGNORECASE)
                    if match:
                        hex_data = match.group(1)
                        decoded = decode_wit_packet(hex_data)
                        
                        if decoded:
                            packet_count += 1
                            
                            if packet_count % 10 == 0:
                                print(f"[WIT] #{packet_count}: Roll {decoded['roll']:7.2f}° | Pitch {decoded['pitch']:7.2f}° | Yaw {decoded['yaw']:7.2f}°")
                            
                            send_to_signalk(decoded)
                        else:
                            error_count += 1
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                pass
        
        process.stdin.write("disconnect\n")
        process.stdin.flush()
        process.terminate()
        
    except Exception as e:
        print(f"[WIT] ❌ Error: {e}")

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║     WIT WT901BLECL - Final Bluetooth Attempt              ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    
    try:
        # Try gatttool first (more direct)
        run_gatttool_connect()
    except KeyboardInterrupt:
        print("\n[WIT] Program terminated.")

#!/usr/bin/env python3
"""
Send UM982 control commands via serial to enable #HEADINGA sentences
"""

import serial
import time
import sys

PORT = '/dev/ttyUM982'
BAUD = 115200

def send_command(ser, cmd):
    """Send a command and wait for response"""
    print(f"[SEND] {cmd}")
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(0.5)
    
    # Read response
    response = ""
    while ser.in_waiting:
        try:
            response += ser.read().decode(errors='ignore')
        except:
            break
    
    if response:
        lines = response.split('\n')
        for line in lines[:5]:  # Show first 5 lines
            if line.strip():
                print(f"[RECV] {line.strip()}")
    time.sleep(1)

def main():
    try:
        print(f"🔌 Opening {PORT} @ {BAUD} baud...")
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(1)
        
        # Clear buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        print("✅ Connected!")
        print("")
        
        # Send commands
        print("=" * 50)
        print("DISABLING ALL OUTPUT")
        print("=" * 50)
        send_command(ser, "unlog")
        
        print("")
        print("=" * 50)
        print("ENABLING #HEADINGA SENTENCES (on change)")
        print("=" * 50)
        send_command(ser, "headinga onchanged")
        
        print("")
        print("=" * 50)
        print("ENABLING GNGGA (position every 1s)")
        print("=" * 50)
        send_command(ser, "gngga 1")
        
        print("")
        print("=" * 50)
        print("SAVING CONFIGURATION")
        print("=" * 50)
        send_command(ser, "saveconfig")
        
        print("")
        print("=" * 50)
        print("✅ COMMANDS SENT! Now listening for #HEADINGA...")
        print("=" * 50)
        print("")
        
        # Listen for 15 seconds
        print("Waiting 15 seconds for sentences to arrive...")
        start = time.time()
        headinga_count = 0
        
        while time.time() - start < 15:
            if ser.in_waiting:
                line = ser.readline().decode(errors='ignore').strip()
                if line:
                    if '#HEADINGA' in line:
                        headinga_count += 1
                        print(f"[✅ HEADINGA] {line[:100]}")
                    elif '$' in line:
                        print(f"[NMEA] {line[:100]}")
        
        print("")
        print("=" * 50)
        if headinga_count > 0:
            print(f"🎉 SUCCESS! Received {headinga_count} #HEADINGA sentences")
        else:
            print("⚠️  No #HEADINGA sentences found")
            print("   Try: 'headinga 10' (every 10s) instead of 'onchanged'")
        print("=" * 50)
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
        ser.close()
        sys.exit(0)

if __name__ == '__main__':
    main()

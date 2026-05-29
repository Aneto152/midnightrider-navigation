#!/usr/bin/env python3
"""
WIT WT901BLECL IMU → Signal K Direct (v9 - Ultra Simple)

Zero TCP. Zero InfluxDB. Just read USB, POST to Signal K API.

Packet structure (0x55 0x61):
  Bytes 0-1:    0x55 0x61 (Header)
  Bytes 2-3:    Accel X (int16, /32768 × 16g)
  Bytes 4-5:    Accel Y (int16, /32768 × 16g)
  Bytes 6-7:    Accel Z (int16, /32768 × 16g)
  Bytes 8-9:    Gyro X (int16, /32768 × 2000 °/s)
  Bytes 10-11:  Gyro Y (int16, /32768 × 2000 °/s)
  Bytes 12-13:  Gyro Z (int16, /32768 × 2000 °/s)
  Bytes 14-15:  Roll (int16, /32768 × 180°)
  Bytes 16-17:  Pitch (int16, /32768 × 180°)
  Bytes 18-19:  Yaw (int16, /32768 × 180°)
"""

import serial
import struct
import requests
import time
import sys
import json
from datetime import datetime

class WITtoSignalK:
    def __init__(self):
        self.serial_port = "/dev/ttyMidnightRider_IMU"
        self.baudrate = 115200
        self.signalk_url = "http://localhost:3000/signalk/v1/api"
        
        self.ser = None
        self.packet_count = 0
        
        # Low-pass filter state (smooth out noise)
        self.alpha = 0.1  # 0.1 = strong smoothing
        self.filtered_roll = 0.0
        self.filtered_pitch = 0.0
        self.filtered_yaw = 0.0
        self.filter_initialized = False
    
    def connect_serial(self):
        """Open serial connection to WIT IMU"""
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            sys.stderr.write(f"✅ WIT IMU connected: {self.serial_port}\n")
            sys.stderr.flush()
            return True
        except Exception as e:
            sys.stderr.write(f"❌ Cannot open {self.serial_port}: {e}\n")
            sys.stderr.flush()
            return False
    
    def low_pass_filter(self, new_value, previous_value):
        """Apply low-pass filter for smoother values"""
        if not self.filter_initialized:
            return new_value
        return self.alpha * new_value + (1.0 - self.alpha) * previous_value
    
    def decode_wit_packet(self, data):
        """Decode 20-byte WIT packet (0x55 0x61 format) with CORRECT FORMULAS"""
        try:
            if len(data) < 20 or data[0] != 0x55 or data[1] != 0x61:
                return None
            
            # ACCELERATION (int16, /32768 × 16g)
            accel_x_raw = struct.unpack('<h', data[2:4])[0]
            accel_y_raw = struct.unpack('<h', data[4:6])[0]
            accel_z_raw = struct.unpack('<h', data[6:8])[0]
            
            accel_x = accel_x_raw / 32768.0 * 16.0
            accel_y = accel_y_raw / 32768.0 * 16.0
            accel_z = accel_z_raw / 32768.0 * 16.0
            
            # GYROSCOPE (int16, /32768 × 2000 °/s)
            gyro_x_raw = struct.unpack('<h', data[8:10])[0]
            gyro_y_raw = struct.unpack('<h', data[10:12])[0]
            gyro_z_raw = struct.unpack('<h', data[12:14])[0]
            
            gyro_x = gyro_x_raw / 32768.0 * 2000.0
            gyro_y = gyro_y_raw / 32768.0 * 2000.0
            gyro_z = gyro_z_raw / 32768.0 * 2000.0
            
            # ATTITUDE/ANGLES (int16, /32768 × 180°)
            roll_raw = struct.unpack('<h', data[14:16])[0]
            pitch_raw = struct.unpack('<h', data[16:18])[0]
            yaw_raw = struct.unpack('<h', data[18:20])[0]
            
            roll_deg = roll_raw / 32768.0 * 180.0
            pitch_deg = pitch_raw / 32768.0 * 180.0
            yaw_deg = yaw_raw / 32768.0 * 180.0
            
            return (accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, roll_deg, pitch_deg, yaw_deg)
        except:
            return None
    
    def post_to_signalk(self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, roll_deg, pitch_deg, yaw_deg):
        """POST IMU data to Signal K via HTTP"""
        try:
            # Apply low-pass filter to angles
            self.filtered_roll = self.low_pass_filter(roll_deg, self.filtered_roll)
            self.filtered_pitch = self.low_pass_filter(pitch_deg, self.filtered_pitch)
            self.filtered_yaw = self.low_pass_filter(yaw_deg, self.filtered_yaw)
            self.filter_initialized = True
            
            # Convert to radians for Signal K
            roll_rad = (self.filtered_roll * 3.14159265) / 180.0
            pitch_rad = (self.filtered_pitch * 3.14159265) / 180.0
            yaw_rad = (self.filtered_yaw * 3.14159265) / 180.0
            
            # Convert gyro to rad/s
            gyro_x_rad = (gyro_x * 3.14159265) / 180.0
            gyro_y_rad = (gyro_y * 3.14159265) / 180.0
            gyro_z_rad = (gyro_z * 3.14159265) / 180.0
            
            # Build delta message (Signal K format)
            delta = {
                "context": "vessels.self",
                "source": {
                    "label": "wit-imu-v9",
                    "type": "IMU"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "updates": [
                    {
                        "source": {"label": "wit-imu-v9"},
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "values": [
                            # Attitude (in radians)
                            {"path": "navigation.attitude.roll", "value": roll_rad},
                            {"path": "navigation.attitude.pitch", "value": pitch_rad},
                            {"path": "navigation.attitude.yaw", "value": yaw_rad},
                            
                            # Angular velocity / Rate of turn (in rad/s)
                            {"path": "navigation.rateOfTurn", "value": gyro_z_rad},
                            {"path": "navigation.rotation.x", "value": gyro_x_rad},
                            {"path": "navigation.rotation.y", "value": gyro_y_rad},
                            {"path": "navigation.rotation.z", "value": gyro_z_rad},
                            
                            # Acceleration (in m/s²)
                            {"path": "navigation.acceleration.x", "value": accel_x * 9.81},
                            {"path": "navigation.acceleration.y", "value": accel_y * 9.81},
                            {"path": "navigation.acceleration.z", "value": accel_z * 9.81}
                        ]
                    }
                ]
            }
            
            # POST to Signal K
            response = requests.post(
                f"{self.signalk_url}/vessels/self",
                json=delta,
                timeout=2
            )
            
            return response.status_code == 200
        
        except Exception as e:
            return False
    
    def run(self):
        """Main loop: read WIT packets, POST to Signal K"""
        sys.stderr.write("╔════════════════════════════════════════════════════════════╗\n")
        sys.stderr.write("║  WIT WT901BLECL IMU → Signal K Direct (v9)               ║\n")
        sys.stderr.write("║  Zero TCP. Zero InfluxDB. HTTP POST to Signal K API.     ║\n")
        sys.stderr.write("╚════════════════════════════════════════════════════════════╝\n\n")
        sys.stderr.flush()
        
        if not self.connect_serial():
            return
        
        buffer = b''
        last_log = time.time()
        
        try:
            while True:
                try:
                    chunk = self.ser.read(512)
                    if not chunk:
                        time.sleep(0.001)
                        continue
                    
                    buffer += chunk
                    
                    # Process complete packets (20 bytes each)
                    while len(buffer) >= 20:
                        if buffer[0] == 0x55 and buffer[1] == 0x61:
                            packet = buffer[:20]
                            buffer = buffer[20:]
                            
                            decoded = self.decode_wit_packet(packet)
                            if decoded:
                                accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, roll_deg, pitch_deg, yaw_deg = decoded
                                self.packet_count += 1
                                
                                # POST to Signal K
                                success = self.post_to_signalk(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, roll_deg, pitch_deg, yaw_deg)
                                
                                # Log every 30 packets
                                if self.packet_count % 30 == 0:
                                    status = "✅" if success else "⚠️"
                                    sys.stderr.write(
                                        f"[{self.packet_count:6d}] {status} "
                                        f"Accel:({accel_x:+6.2f},{accel_y:+6.2f},{accel_z:+6.2f})g | "
                                        f"Roll:{self.filtered_roll:7.2f}° Pitch:{self.filtered_pitch:7.2f}° Yaw:{self.filtered_yaw:7.2f}°\n"
                                    )
                                    sys.stderr.flush()
                        else:
                            buffer = buffer[1:]
                
                except Exception as e:
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            sys.stderr.write(f"\n\n✅ Stopped. Total packets: {self.packet_count}\n")
            sys.stderr.flush()
        finally:
            if self.ser:
                self.ser.close()

if __name__ == "__main__":
    reader = WITtoSignalK()
    reader.run()

#!/usr/bin/env python3
"""
WIT IMU → Signal K Bridge (Direct TCP passthrough + InfluxDB)
Reads WIT data and sends BOTH:
1. NMEA sentences to Signal K via TCP (so kflex provider can parse)
2. Data directly to InfluxDB
"""

import serial
import struct
import socket
import time
import urllib.request
import urllib.parse
import sys
import os

class WITSignalKBridge:
    def __init__(self):
        self.wit_port = "/dev/ttyMidnightRider_IMU"
        self.wit_baudrate = 115200
        
        self.tcp_host = "localhost"
        self.tcp_port = 10112
        self.tcp_socket = None
        
        # InfluxDB
        self.influx_url = "http://localhost:8086/api/v2/write"
        self.influx_org = "MidnightRider"
        self.influx_bucket = "signalk"
        self.influx_token = os.environ.get('INFLUXDB_TOKEN', '')
        if not self.influx_token:
            print("⚠️ WARNING: INFLUXDB_TOKEN not set. InfluxDB writes will fail.")
            print("Set INFLUXDB_TOKEN environment variable before running.")
        
        self.wit_ser = None
        self.packet_count = 0
        self.clients = []
    
    def connect_serial(self):
        try:
            self.wit_ser = serial.Serial(
                port=self.wit_port,
                baudrate=self.wit_baudrate,
                timeout=0.1
            )
            sys.stderr.write(f"✅ WIT Serial: {self.wit_port}\n")
            sys.stderr.flush()
            return True
        except Exception as e:
            sys.stderr.write(f"❌ WIT Serial: {e}\n")
            sys.stderr.flush()
            return False
    
    def start_tcp_server(self):
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((self.tcp_host, self.tcp_port))
            self.tcp_socket.listen(5)
            self.tcp_socket.setblocking(False)
            sys.stderr.write(f"✅ TCP Server: {self.tcp_host}:{self.tcp_port}\n")
            sys.stderr.flush()
            return True
        except Exception as e:
            sys.stderr.write(f"❌ TCP Server: {e}\n")
            sys.stderr.flush()
            return False
    
    def decode_wit(self, data):
        try:
            if len(data) < 20 or data[0] != 0x55 or data[1] != 0x61:
                return None
            roll = struct.unpack('<h', data[2:4])[0] / 100.0
            pitch = struct.unpack('<h', data[4:6])[0] / 100.0
            yaw = struct.unpack('<h', data[6:8])[0] / 100.0
            return (roll, pitch, yaw)
        except:
            return None
    
    def format_nmea_sentences(self, roll, pitch, yaw):
        """Format standard NMEA sentences"""
        sentences = []
        
        # HEHDT - Heading True
        hdt = f"$HEHDT,{yaw:.2f},T"
        checksum = 0
        for c in hdt[1:]:
            checksum ^= ord(c)
        sentences.append(f"{hdt}*{checksum:02X}\n")
        
        # HEATT - Attitude
        att = f"$HEATT,{roll:.2f},{pitch:.2f},{yaw:.2f}"
        checksum = 0
        for c in att[1:]:
            checksum ^= ord(c)
        sentences.append(f"{att}*{checksum:02X}\n")
        
        return sentences
    
    def broadcast_to_clients(self, sentences):
        """Send NMEA sentences to all connected TCP clients"""
        dead_clients = []
        for client in self.clients:
            try:
                for sentence in sentences:
                    client.sendall(sentence.encode())
            except:
                dead_clients.append(client)
        
        for client in dead_clients:
            try:
                client.close()
            except:
                pass
            self.clients.remove(client)
    
    def write_to_influxdb(self, roll, pitch, yaw):
        """Write attitude data to InfluxDB"""
        try:
            line = f"wit_attitude,source=imu roll={roll},pitch={pitch},yaw={yaw}"
            
            params = {
                'org': self.influx_org,
                'bucket': self.influx_bucket
            }
            
            url = f"{self.influx_url}?{urllib.parse.urlencode(params)}"
            
            req = urllib.request.Request(
                url,
                data=line.encode('utf-8'),
                headers={
                    'Authorization': f'Token {self.influx_token}',
                    'Content-Type': 'text/plain; charset=utf-8'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=1) as response:
                return response.status == 204
        except:
            return False
    
    def accept_tcp_connections(self):
        """Accept new TCP connections (non-blocking)"""
        try:
            client, addr = self.tcp_socket.accept()
            self.clients.append(client)
            sys.stderr.write(f"   → TCP Client: {addr[0]}:{addr[1]}\n")
            sys.stderr.flush()
        except BlockingIOError:
            pass
        except Exception as e:
            sys.stderr.write(f"   ⚠️  Accept error: {e}\n")
            sys.stderr.flush()
    
    def run(self):
        sys.stderr.write("╔════════════════════════════════════════════════════════════╗\n")
        sys.stderr.write("║  WIT IMU → Signal K Bridge (Direct + InfluxDB)             ║\n")
        sys.stderr.write("║  NMEA sentences via TCP + Data to InfluxDB                 ║\n")
        sys.stderr.write("╚════════════════════════════════════════════════════════════╝\n\n")
        sys.stderr.flush()
        
        if not self.connect_serial():
            return
        
        if not self.start_tcp_server():
            return
        
        sys.stderr.write("[Listening for Signal K kflex provider...]\n\n")
        sys.stderr.flush()
        
        buffer = b''
        
        try:
            while True:
                try:
                    # Check for new TCP connections
                    self.accept_tcp_connections()
                    
                    # Read WIT data
                    chunk = self.wit_ser.read(512)
                    if not chunk:
                        time.sleep(0.001)
                        continue
                    
                    buffer += chunk
                    
                    # Process complete packets
                    while len(buffer) >= 20:
                        if buffer[0] == 0x55 and buffer[1] == 0x61:
                            packet = buffer[:20]
                            buffer = buffer[20:]
                            
                            decoded = self.decode_wit(packet)
                            if decoded:
                                roll, pitch, yaw = decoded
                                self.packet_count += 1
                                
                                # Format NMEA sentences
                                sentences = self.format_nmea_sentences(roll, pitch, yaw)
                                
                                # Broadcast to Signal K kflex provider
                                self.broadcast_to_clients(sentences)
                                
                                # Write to InfluxDB
                                self.write_to_influxdb(roll, pitch, yaw)
                                
                                if self.packet_count % 20 == 0:
                                    sys.stderr.write(f"[{self.packet_count}] Roll: {roll:7.2f}° | Pitch: {pitch:7.2f}° | Yaw: {yaw:7.2f}° → Signal K + InfluxDB\n")
                                    sys.stderr.flush()
                        else:
                            buffer = buffer[1:]
                
                except Exception as e:
                    sys.stderr.write(f"Error: {e}\n")
                    sys.stderr.flush()
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            sys.stderr.write(f"\n\nStopped. Total packets: {self.packet_count}\n")
            sys.stderr.flush()
        finally:
            if self.wit_ser:
                self.wit_ser.close()
            if self.tcp_socket:
                self.tcp_socket.close()
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass

if __name__ == "__main__":
    bridge = WITSignalKBridge()
    bridge.run()

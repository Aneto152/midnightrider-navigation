#!/usr/bin/env python3
"""
Signal K to NMEA 0183 Converter
Converts Signal K TCP delta stream to NMEA 0183 sentences
For use with qtVLM and other marine navigation software

Usage:
    python3 signalk-to-nmea0183.py
"""

import socket
import json
import math
import time
import threading
from datetime import datetime

# Configuration
SIGNALK_HOST = "localhost"
SIGNALK_TCP_PORT = 8375
NMEA_SERVER_PORT = 10110

class SignalKToNMEA:
    def __init__(self):
        self.running = True
        self.sk_socket = None
        self.clients = []
        self.lock = threading.Lock()
        
        # Latest values for NMEA generation
        self.values = {
            'roll': None,           # rad
            'pitch': None,          # rad
            'yaw': None,            # rad (heading true)
            'sog': None,            # m/s
            'cog': None,            # rad
            'lat': None,            # degrees
            'lon': None,            # degrees
            'stw': None,            # m/s
            'wind_angle': None,     # rad (apparent)
            'wind_speed': None,     # m/s (apparent)
        }
    
    def connect_signalk(self):
        """Connect to Signal K TCP stream"""
        print(f"🔌 Connecting to Signal K {SIGNALK_HOST}:{SIGNALK_TCP_PORT}...")
        
        self.sk_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sk_socket.settimeout(30)
        
        try:
            self.sk_socket.connect((SIGNALK_HOST, SIGNALK_TCP_PORT))
            print("✅ Connected to Signal K")
            
            # Read hello
            hello = self.sk_socket.recv(4096)
            print(f"📨 Hello received")
            
            # Subscribe to relevant paths
            sub = {
                "context": "vessels.self",
                "subscribe": [
                    {"path": "navigation.attitude.*", "minInterval": 100},
                    {"path": "navigation.speedOverGround", "minInterval": 500},
                    {"path": "navigation.courseOverGround", "minInterval": 500},
                    {"path": "navigation.speedThroughWater", "minInterval": 500},
                    {"path": "navigation.position", "minInterval": 5000},
                    {"path": "environment.wind.*", "minInterval": 500},
                ]
            }
            
            sub_msg = json.dumps(sub) + "\r\n"
            self.sk_socket.send(sub_msg.encode())
            print("📤 Subscription sent")
            
            return True
        except Exception as e:
            print(f"❌ Error connecting: {e}")
            return False
    
    def stream_signalk(self):
        """Read Signal K deltas and update values"""
        buffer = ""
        
        while self.running:
            try:
                data = self.sk_socket.recv(4096)
                if not data:
                    print("⚠️ Connection closed by server")
                    break
                
                buffer += data.decode('utf-8', errors='ignore')
                
                # Process complete lines
                while '\r\n' in buffer:
                    line, buffer = buffer.split('\r\n', 1)
                    
                    if not line.strip():
                        continue
                    
                    try:
                        delta = json.loads(line)
                        self.process_delta(delta)
                    except json.JSONDecodeError:
                        pass
            
            except socket.timeout:
                print("⚠️ TCP timeout, reconnecting...")
                break
            except Exception as e:
                print(f"❌ Stream error: {e}")
                break
        
        print("🔌 Signal K stream stopped")
    
    def process_delta(self, delta):
        """Process Signal K delta and extract values"""
        if not delta.get('updates'):
            return
        
        with self.lock:
            for update in delta.get('updates', []):
                for val in update.get('values', []):
                    path = val.get('path')
                    value = val.get('value')
                    
                    if path == 'navigation.attitude.roll':
                        self.values['roll'] = value
                    elif path == 'navigation.attitude.pitch':
                        self.values['pitch'] = value
                    elif path == 'navigation.attitude.yaw':
                        self.values['yaw'] = value
                    elif path == 'navigation.speedOverGround':
                        self.values['sog'] = value
                    elif path == 'navigation.courseOverGround':
                        self.values['cog'] = value
                    elif path == 'navigation.speedThroughWater':
                        self.values['stw'] = value
                    elif path == 'navigation.position':
                        if isinstance(value, dict):
                            self.values['lat'] = value.get('latitude')
                            self.values['lon'] = value.get('longitude')
                    elif path == 'environment.wind.angleApparent':
                        self.values['wind_angle'] = value
                    elif path == 'environment.wind.speedApparent':
                        self.values['wind_speed'] = value
    
    def generate_nmea(self):
        """Generate NMEA 0183 sentences from current values"""
        sentences = []
        
        with self.lock:
            # HDT - Heading True
            if self.values['yaw'] is not None:
                hdg = math.degrees(self.values['yaw'])
                hdg = hdg % 360
                sentences.append(f"$IIHDT,{hdg:.1f},T*00")
            
            # MWV - Wind
            if self.values['wind_angle'] is not None and self.values['wind_speed'] is not None:
                wind_angle = math.degrees(self.values['wind_angle'])
                wind_angle = wind_angle % 360
                wind_knots = self.values['wind_speed'] * 1.94384  # m/s to knots
                sentences.append(f"$IIMWV,{wind_angle:.1f},R,{wind_knots:.1f},N*00")
            
            # SOG/COG via RMC-like sentences
            if self.values['sog'] is not None:
                sog_knots = self.values['sog'] * 1.94384
                sentences.append(f"$IIVHW,,T,,,M,{sog_knots:.2f},N,,K*00")
        
        return sentences
    
    def broadcast_nmea(self):
        """Broadcast NMEA sentences to connected clients"""
        while self.running:
            sentences = self.generate_nmea()
            
            if sentences:
                for sentence in sentences:
                    with self.lock:
                        dead_clients = []
                        for client in self.clients:
                            try:
                                client.sendall((sentence + "\r\n").encode())
                            except:
                                dead_clients.append(client)
                        
                        # Remove dead clients
                        for client in dead_clients:
                            self.clients.remove(client)
            
            time.sleep(0.1)  # 10 Hz
    
    def accept_clients(self):
        """Accept incoming NMEA client connections"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', NMEA_SERVER_PORT))
        server.listen(5)
        
        print(f"🌐 NMEA server listening on port {NMEA_SERVER_PORT}")
        
        while self.running:
            try:
                client, addr = server.accept()
                print(f"✅ Client connected: {addr}")
                
                with self.lock:
                    self.clients.append(client)
            except:
                pass
        
        server.close()
    
    def run(self):
        """Main run loop"""
        print("╔════════════════════════════════════════════╗")
        print("║  Signal K → NMEA 0183 Converter v1.0       ║")
        print("╚════════════════════════════════════════════╝")
        print()
        
        # Connect to Signal K
        if not self.connect_signalk():
            return
        
        # Start threads
        sk_thread = threading.Thread(target=self.stream_signalk, daemon=True)
        nmea_thread = threading.Thread(target=self.broadcast_nmea, daemon=True)
        server_thread = threading.Thread(target=self.accept_clients, daemon=True)
        
        sk_thread.start()
        nmea_thread.start()
        server_thread.start()
        
        print()
        print("📊 Running...")
        print("   Receiving Signal K deltas")
        print("   Broadcasting NMEA 0183 to clients")
        print()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️ Stopping...")
            self.running = False
            time.sleep(1)

if __name__ == '__main__':
    converter = SignalKToNMEA()
    converter.run()

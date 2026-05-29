#!/usr/bin/env python3
"""
WIT TCP Bridge — Reads v7 data from InfluxDB and sends HEATT sentences to TCP:10111
"""

import socket
import time
import threading
import sys
from collections import deque

class WITTCPBridge:
    def __init__(self):
        self.server_socket = None
        self.client_connections = []
        self.port = 10111
        
        # Current IMU values (in degrees)
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
    
    def start_tcp_server(self):
        """Start TCP server on port 10111"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            sys.stderr.write(f"✅ TCP server listening on port {self.port}\n")
            sys.stderr.flush()
            
            # Accept connections in background
            threading.Thread(target=self.accept_connections, daemon=True).start()
            
        except Exception as e:
            sys.stderr.write(f"❌ Cannot start TCP server: {e}\n")
            sys.stderr.flush()
    
    def accept_connections(self):
        """Accept TCP connections"""
        while True:
            try:
                client, addr = self.server_socket.accept()
                sys.stderr.write(f"✅ Client connected: {addr}\n")
                sys.stderr.flush()
                self.client_connections.append(client)
            except:
                time.sleep(0.1)
    
    def broadcast_heatt(self):
        """Broadcast HEATT sentence to all connected clients"""
        sentence = f"$HEATT,{self.roll:.2f},{self.pitch:.2f},{self.yaw:.2f}*00\n"
        
        # Remove closed connections
        self.client_connections = [c for c in self.client_connections if c.fileno() != -1]
        
        # Send to all clients
        for client in self.client_connections:
            try:
                client.sendall(sentence.encode())
            except:
                try:
                    client.close()
                except:
                    pass
    
    def update_imu_data(self, roll, pitch, yaw):
        """Update IMU values and broadcast"""
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.broadcast_heatt()
    
    def run(self):
        """Main loop"""
        sys.stderr.write("╔════════════════════════════════════════════════════════════╗\n")
        sys.stderr.write("║  WIT TCP Bridge — v7 HEATT Sentences to TCP:10111          ║\n")
        sys.stderr.write("╚════════════════════════════════════════════════════════════╝\n\n")
        sys.stderr.flush()
        
        self.start_tcp_server()
        
        # Simulate data for testing (in real use, this gets called from Signal K or InfluxDB reader)
        try:
            while True:
                # This is just a test loop
                # In production, v7 or another service would call update_imu_data()
                time.sleep(0.1)
        except KeyboardInterrupt:
            sys.stderr.write("\n✅ Stopped\n")
            sys.stderr.flush()

if __name__ == "__main__":
    bridge = WITTCPBridge()
    bridge.run()

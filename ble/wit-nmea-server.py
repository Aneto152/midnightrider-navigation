#!/usr/bin/env python3
"""
WIT IMU → NMEA0183 TCP Server
Converts IMU data to proper NMEA0183 format for Signal K
"""

import serial
import struct
import socket
import threading
import time

class WITNMEAServer:
    def __init__(self, serial_port="/dev/ttyMidnightRider_IMU", tcp_port=10110):
        self.serial_port = serial_port
        self.tcp_port = tcp_port
        self.ser = None
        self.server = None
        self.running = True
        self.clients = []
        self.packet_count = 0
    
    def connect_serial(self):
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=115200,
                timeout=0.1
            )
            print(f"✅ Serial: {self.serial_port}")
            return True
        except Exception as e:
            print(f"❌ Serial: {e}")
            return False
    
    def decode_wit_packet(self, data):
        try:
            if len(data) < 20 or data[0] != 0x55 or data[1] != 0x61:
                return None
            
            roll_deg = struct.unpack('<h', data[2:4])[0] / 100.0
            pitch_deg = struct.unpack('<h', data[4:6])[0] / 100.0
            yaw_deg = struct.unpack('<h', data[6:8])[0] / 100.0
            
            return (roll_deg, pitch_deg, yaw_deg)
        except:
            return None
    
    def format_nmea(self, roll, pitch, yaw):
        """
        Format as NMEA0183-compatible sentences
        Using standard XDR (Transducer) messages that Signal K understands
        """
        sentences = []
        
        # XDR sentences for attitude (Transducer Results)
        # $--XDR,a,roll,r,pitch,p,yaw,y*hh
        
        # Roll (heel angle) - standard NMEA XDR format
        roll_xdr = f"$WIXDR,A,{roll:.2f},D,ROLL"
        checksum = 0
        for c in roll_xdr[1:]:
            checksum ^= ord(c)
        sentences.append(f"{roll_xdr}*{checksum:02X}\n")
        
        # Pitch (trim)
        pitch_xdr = f"$WIXDR,A,{pitch:.2f},D,PITCH"
        checksum = 0
        for c in pitch_xdr[1:]:
            checksum ^= ord(c)
        sentences.append(f"{pitch_xdr}*{checksum:02X}\n")
        
        # Yaw/Heading
        yaw_xdr = f"$WIXDR,A,{yaw:.2f},D,HEADING"
        checksum = 0
        for c in yaw_xdr[1:]:
            checksum ^= ord(c)
        sentences.append(f"{yaw_xdr}*{checksum:02X}\n")
        
        return sentences
    
    def serial_reader_thread(self):
        buffer = b''
        
        while self.running:
            try:
                if not self.ser or not self.ser.is_open:
                    if not self.connect_serial():
                        time.sleep(5)
                        continue
                
                chunk = self.ser.read(1)
                if not chunk:
                    time.sleep(0.001)
                    continue
                
                buffer += chunk
                
                while len(buffer) >= 20:
                    if buffer[0] == 0x55 and buffer[1] == 0x61:
                        packet = buffer[:20]
                        buffer = buffer[20:]
                        
                        decoded = self.decode_wit_packet(packet)
                        if decoded:
                            self.packet_count += 1
                            
                            if self.packet_count % 10 == 0:
                                roll, pitch, yaw = decoded
                                print(f"[WIT #{self.packet_count}] Roll: {roll:7.2f}° | Pitch: {pitch:7.2f}° | Yaw: {yaw:7.2f}°")
                            
                            self.broadcast_to_clients(decoded)
                    else:
                        buffer = buffer[1:]
            
            except Exception as e:
                print(f"Serial error: {e}")
                time.sleep(1)
    
    def broadcast_to_clients(self, decoded):
        roll, pitch, yaw = decoded
        sentences = self.format_nmea(roll, pitch, yaw)
        
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
    
    def tcp_server_thread(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', self.tcp_port))
        self.server.listen(5)
        
        print(f"✅ TCP Server: 0.0.0.0:{self.tcp_port}")
        print(f"   (Signal K kflex provider listening here)\n")
        
        while self.running:
            try:
                client, addr = self.server.accept()
                print(f"   → Client: {addr[0]}:{addr[1]}")
                self.clients.append(client)
            except:
                pass
    
    def start(self):
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  WIT IMU → NMEA0183 TCP Server (for Signal K kflex)       ║")
        print("╚════════════════════════════════════════════════════════════╝\n")
        
        threading.Thread(target=self.serial_reader_thread, daemon=True).start()
        threading.Thread(target=self.tcp_server_thread, daemon=True).start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
            if self.server:
                self.server.close()
            if self.ser:
                self.ser.close()

if __name__ == "__main__":
    server = WITNMEAServer()
    server.start()

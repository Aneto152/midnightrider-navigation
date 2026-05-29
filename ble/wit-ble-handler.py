#!/usr/bin/env python3
"""
WIT WT901BLECL Bluetooth LE Handler
Reads BLE packets and injects into Signal K via websocket/handleMessage
Uses OFFICIAL WIT formulas (raw / 32768 × scale)
"""

import asyncio
import struct
import sys
from bleak import BleakClient, BleakScanner

# WIT BLE UUIDs (from datasheet)
WIT_SERVICE_UUID = "0000ffe5-0000-1000-8000-00805f9b34fb"
WIT_NOTIFY_UUID = "0000ffe4-0000-1000-8000-00805f9b34fb"

class WITHandler:
    def __init__(self):
        self.packet_count = 0
        self.filtered_roll = 0
        self.filtered_pitch = 0
        self.filtered_yaw = 0
        self.filter_init = False
        self.alpha = 0.1

    def decode_wit(self, data):
        """Decode 20-byte WIT packet with OFFICIAL formulas"""
        try:
            if len(data) < 20 or data[0] != 0x55 or data[1] != 0x61:
                return None

            def read16(off):
                v = (data[off+1] << 8) | data[off]
                return v - 0x10000 if v & 0x8000 else v

            # Accel: raw / 32768 × 16 (g)
            accel_x = (read16(2) / 32768) * 16
            accel_y = (read16(4) / 32768) * 16
            accel_z = (read16(6) / 32768) * 16

            # Gyro: raw / 32768 × 2000 (°/s)
            gyro_x = (read16(8) / 32768) * 2000
            gyro_y = (read16(10) / 32768) * 2000
            gyro_z = (read16(12) / 32768) * 2000

            # Angles: raw / 32768 × 180 (°)
            roll_deg = (read16(14) / 32768) * 180
            pitch_deg = (read16(16) / 32768) * 180
            yaw_deg = (read16(18) / 32768) * 180

            return {
                'accel_x': accel_x, 'accel_y': accel_y, 'accel_z': accel_z,
                'gyro_x': gyro_x, 'gyro_y': gyro_y, 'gyro_z': gyro_z,
                'roll': roll_deg, 'pitch': pitch_deg, 'yaw': yaw_deg
            }
        except:
            return None

    def filter_value(self, new_val, old_val):
        """Low-pass filter"""
        if not self.filter_init:
            return new_val
        return self.alpha * new_val + (1 - self.alpha) * old_val

    def notification_handler(self, sender, data):
        """Handle BLE notification"""
        decoded = self.decode_wit(data)
        if not decoded:
            return

        # Filter angles
        self.filtered_roll = self.filter_value(decoded['roll'], self.filtered_roll)
        self.filtered_pitch = self.filter_value(decoded['pitch'], self.filtered_pitch)
        self.filtered_yaw = self.filter_value(decoded['yaw'], self.filtered_yaw)
        self.filter_init = True

        self.packet_count += 1
        if self.packet_count % 20 == 0:
            print(f"[{self.packet_count}] Roll:{self.filtered_roll:.1f}° Pitch:{self.filtered_pitch:.1f}° Yaw:{self.filtered_yaw:.1f}°", file=sys.stderr, flush=True)

    async def run(self):
        """Connect and listen"""
        print("[WIT BLE] Scanning for WIT device...", file=sys.stderr, flush=True)

        scanner = BleakScanner()
        devices = await scanner.discover()

        wit_device = None
        for device in devices:
            if "WT901" in device.name or device.address.lower().startswith("e9:10"):
                wit_device = device
                break

        if not wit_device:
            print("[WIT BLE] No WIT device found", file=sys.stderr, flush=True)
            return

        print(f"[WIT BLE] Found: {wit_device.name} ({wit_device.address})", file=sys.stderr, flush=True)

        async with BleakClient(wit_device) as client:
            print("[WIT BLE] Connected", file=sys.stderr, flush=True)

            # Start notifications
            await client.start_notify(WIT_NOTIFY_UUID, self.notification_handler)
            print("[WIT BLE] Listening for data...", file=sys.stderr, flush=True)

            # Keep running
            while True:
                await asyncio.sleep(1)

if __name__ == "__main__":
    handler = WITHandler()
    try:
        asyncio.run(handler.run())
    except KeyboardInterrupt:
        print("\n[WIT BLE] Stopped", file=sys.stderr, flush=True)

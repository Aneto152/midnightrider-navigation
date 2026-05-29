#!/usr/bin/env python3
"""bleak_wit.py - WIT BLE Driver (bleak backend, no gatttool)"""
import asyncio, struct, json, sys, signal, time
from bleak import BleakClient

MAC = "E9:10:DB:8B:CE:C7"
# Caractéristique de notification: 0xffe4 du service 0xffe5
NOTIFY_UUIDS = ["0000ffe4-0000-1000-8000-00805f9a34fb", "0000ffe4-0000-1000-8000-00805f9b34fb", "0000ffe1-0000-1000-8000-00805f9b34fb"]
buffer = bytearray()
running = True

def decode_packet(packet):
    if len(packet) < 20 or packet[0] != 0x55 or packet[1] != 0x61:
        return None
    import math
    return {
        "accel_x": (struct.unpack_from('<h', packet, 2)[0] / 32768) * 16 * 9.81,
        "accel_y": (struct.unpack_from('<h', packet, 4)[0] / 32768) * 16 * 9.81,
        "accel_z": (struct.unpack_from('<h', packet, 6)[0] / 32768) * 16 * 9.81,
        "gyro_z": (struct.unpack_from('<h', packet, 12)[0] / 32768) * (2000 * math.pi / 180),
        "roll": (struct.unpack_from('<h', packet, 14)[0] / 32768) * math.pi,
        "pitch": (struct.unpack_from('<h', packet, 16)[0] / 32768) * math.pi,
        "yaw": (struct.unpack_from('<h', packet, 18)[0] / 32768) * math.pi,
    }

def on_notify(sender, data):
    global buffer
    buffer.extend(data)
    if len(buffer) > 1024:
        buffer = bytearray()
        return
    while len(buffer) >= 20:
        if buffer[0] == 0x55 and buffer[1] == 0x61:
            decoded = decode_packet(bytes(buffer[:20]))
            if decoded:
                print(json.dumps(decoded), flush=True)
            buffer = buffer[20:]
        else:
            buffer = buffer[1:]

async def run():
    global running
    reconnect_delay = 5
    while running:
        try:
            async with BleakClient(MAC, timeout=20) as client:
                for service in client.services:
                    for char in service.characteristics:
                        if "notify" in char.properties:
                            for uuid in NOTIFY_UUIDS:
                                if str(char.uuid).lower() == uuid.lower():
                                    await client.start_notify(uuid, on_notify)
                                    while client.is_connected and running:
                                        await asyncio.sleep(1)
                                    return
        except Exception as e:
            pass
        if running:
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)

signal.signal(signal.SIGTERM, lambda s, f: setattr(sys.modules[__name__], 'running', False))
signal.signal(signal.SIGINT, lambda s, f: setattr(sys.modules[__name__], 'running', False))
asyncio.run(run())

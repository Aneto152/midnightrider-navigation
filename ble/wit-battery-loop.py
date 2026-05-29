#!/usr/bin/env python3
"""
WIT IMU BLE Battery Monitor (Loop Version)
Attempts to read battery level every 60 seconds
Sends to Signal K electrical.batteries.wit.capacity.stateOfCharge
"""

import asyncio
import json
import socket
import time
import logging
from datetime import datetime
from bleak import BleakClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

WIT_MAC = "E9:10:DB:8B:CE:C7"
BATTERY_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
SK_UDP_PORT = 4123
INTERVAL_SEC = 60

def send_to_signalk(soc, battery_pct):
    """Send battery to Signal K"""
    delta = {
        "updates": [{
            "source": {"label": "wit-battery", "type": "BLE"},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "values": [
                {
                    "path": "electrical.batteries.wit.capacity.stateOfCharge",
                    "value": round(soc, 2)
                },
                {
                    "path": "electrical.batteries.wit.name",
                    "value": "WIT IMU BLE"
                }
            ]
        }]
    }
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(delta).encode(), ('localhost', SK_UDP_PORT))
        logger.info(f"[WIT] {battery_pct}% → Signal K")
    except Exception as e:
        logger.error(f"[WIT] Send error: {e}")

async def read_battery():
    """Try to read WIT battery"""
    try:
        async with BleakClient(WIT_MAC, timeout=12) as client:
            logger.info("[WIT] Connected")
            raw = await client.read_gatt_char(BATTERY_UUID)
            pct = int(raw[0])
            soc = pct / 100.0
            logger.info(f"[WIT] Battery: {pct}%")
            send_to_signalk(soc, pct)
            return True
    except Exception as e:
        logger.debug(f"[WIT] Read failed (device may be off): {e}")
        return False

async def main():
    logger.info("=" * 60)
    logger.info("WIT IMU BLE BATTERY MONITOR (LOOP)")
    logger.info("=" * 60)
    logger.info(f"Device: {WIT_MAC}")
    logger.info(f"Interval: {INTERVAL_SEC}s")
    logger.info(f"Target: electrical.batteries.wit")
    logger.info("=" * 60)
    
    while True:
        try:
            await read_battery()
        except Exception as e:
            logger.error(f"[WIT] Unexpected error: {e}")
        
        await asyncio.sleep(INTERVAL_SEC)

if __name__ == '__main__':
    asyncio.run(main())

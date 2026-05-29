#!/usr/bin/env python3
"""
Calypso UDP Filter Proxy — 2026-05-21
Known bug: calypso-anemometer v0.6.0 sends zero-valued sentinel data
for eCompass (roll=-90°, pitch=-90°, heading=360°) and temperature (0°C).
This proxy strips those broken paths before injecting to Signal K.

Architecture:
 calypso-anemometer → UDP:4122 (raw) → this proxy → UDP:4123 (clean) → SK

WHITELIST (only these paths reach Signal K):
 environment.wind.* — wind speed and angle (working correctly)
 electrical.batteries.* — battery state (working correctly)
"""
import socket, json, sys, logging

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [calypso-filter] %(message)s')
log = logging.getLogger(__name__)

IN_PORT = 4122
OUT_PORT = 4123
OUT_HOST = "127.0.0.1"

ALLOWED_PREFIXES = (
    "environment.wind.",
    "electrical.batteries.",
)

def is_allowed(path):
    return any(path.startswith(p) for p in ALLOWED_PREFIXES)

def filter_delta(raw_delta):
    filtered_updates = []
    blocked = []
    for update in raw_delta.get("updates", []):
        good = [v for v in update.get("values", []) if is_allowed(v.get("path", ""))]
        bad = [v.get("path") for v in update.get("values", []) if not is_allowed(v.get("path", ""))]
        if bad:
            blocked.extend(bad)
        if good:
            filtered_update = dict(update)
            filtered_update["values"] = good
            filtered_updates.append(filtered_update)
    if blocked:
        log.debug(f"Blocked paths (known broken): {blocked}")
    if filtered_updates:
        result = dict(raw_delta)
        result["updates"] = filtered_updates
        return result
    return None

in_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
in_sock.bind(("0.0.0.0", IN_PORT))
out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

log.info(f"Filter proxy started — UDP:{IN_PORT} → UDP:{OUT_PORT}")
log.info(f"Whitelist: {ALLOWED_PREFIXES}")
log.info("Blocking: roll, pitch, yaw, headingMagnetic, temperature (known zeros)")

while True:
    try:
        data, _ = in_sock.recvfrom(65535)
        delta = json.loads(data)
        filtered = filter_delta(delta)
        if filtered:
            out_sock.sendto(json.dumps(filtered).encode(), (OUT_HOST, OUT_PORT))
    except json.JSONDecodeError:
        pass
    except Exception as e:
        log.error(f"Error: {e}")

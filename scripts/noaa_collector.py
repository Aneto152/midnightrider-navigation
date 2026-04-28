#!/usr/bin/env python3
"""
NOAA NDBC Collector — Midnight Rider Navigation

Architecture:
 - Loop A (NOAA fetch) : every FETCH_INTERVAL seconds (default: 1800 = 30 min)
 - Loop B (Signal K inject): every INJECT_INTERVAL seconds (default: 120 = 2 min)

Loop A fetches fresh data from NOAA NDBC and updates the local cache.
Loop B injects the cached values into Signal K via WebSocket delta.
This keeps Signal K "alive" (no data gaps in Grafana) even between NOAA updates.

Signal K → signalk-to-influxdb2 → InfluxDB (automatic, no direct write here)

Stations:
 44017 — Montauk Point (wind, pressure, air temp)
 44025 — LIS Central (water temp)
 BLTM3 — Block Island (wind, pressure, air temp — race day)

Usage:
 python3 scripts/noaa_collector.py # daemon mode (default)
 python3 scripts/noaa_collector.py --once # run one fetch+inject cycle, then exit
 python3 scripts/noaa_collector.py --debug # verbose logging

Author: OC (Open Claw) + Denis Lafarge — Midnight Rider Navigation
"""

import requests
import websocket
import json
import math
import logging
import time
import threading
import argparse
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# ─── Configuration ────────────────────────────────────────────────────────────

load_dotenv()

SIGNALK_WS_URL = os.getenv("SIGNALK_WS_URL", "ws://localhost:3000/signalk/v1/stream?subscribe=none")
SIGNALK_TOKEN = os.getenv("SIGNALK_TOKEN", "")
NDBC_BASE_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"
REQUEST_TIMEOUT = 30
FETCH_INTERVAL = 1800
INJECT_INTERVAL = 120

STATIONS = {
    "44017": {
        "name": "Montauk Point",
        "collect": ["wind", "pressure", "air_temp"],
    },
    "44025": {
        "name": "LIS Central",
        "collect": ["water_temp"],
    },
    "BLTM3": {
        "name": "Block Island",
        "collect": ["wind", "pressure", "air_temp"],
    },
}

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NOAA] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/noaa_collector.log", mode="a"),
    ]
)
log = logging.getLogger(__name__)

# ─── Shared cache (thread-safe via lock) ──────────────────────────────────────

cache_lock = threading.Lock()
value_cache = {}

# ─── NDBC Fetcher ─────────────────────────────────────────────────────────────

def parse_float(value):
    """Return float or None if missing (99, 999, MM, etc.)."""
    try:
        v = float(value)
        return None if v in (99.0, 999.0, 9999.0) else v
    except (ValueError, TypeError):
        return None


def fetch_station(station_id):
    """Fetch latest observation from NDBC buoy. Returns raw field dict."""
    url = NDBC_BASE_URL.format(station=station_id)
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"[{station_id}] HTTP fetch failed: {e}")
        return None

    header, data = None, None
    for line in resp.text.splitlines():
        if line.startswith("#YY"):
            header = line.lstrip("#").split()
        elif header and not line.startswith("#"):
            data = line.split()
            break

    if not header or not data:
        log.error(f"[{station_id}] Could not parse NDBC response")
        return None

    raw = dict(zip(header, data))
    log.debug(f"[{station_id}] Raw: {raw}")
    return raw


def extract_signalk_values(station_id, raw, collect):
    """Convert raw NDBC fields to Signal K path/value pairs (SI units)."""
    source = f"noaa.ndbc.{station_id}"
    values = []

    if "wind" in collect:
        wspd = parse_float(raw.get("WSPD"))
        gst = parse_float(raw.get("GST"))
        wdir = parse_float(raw.get("WDIR"))
        if wspd is not None:
            values.append({"path": "environment.wind.speedTrue", "value": wspd, "source": source})
        if gst is not None:
            values.append({"path": "environment.wind.gust", "value": gst, "source": source})
        if wdir is not None:
            values.append({"path": "environment.wind.directionTrue", "value": math.radians(wdir), "source": source})

    if "pressure" in collect:
        pres = parse_float(raw.get("PRES"))
        if pres is not None:
            values.append({"path": "environment.outside.pressure", "value": pres * 100.0, "source": source})

    if "air_temp" in collect:
        atmp = parse_float(raw.get("ATMP"))
        if atmp is not None:
            values.append({"path": "environment.outside.temperature", "value": atmp + 273.15, "source": source})

    if "water_temp" in collect:
        wtmp = parse_float(raw.get("WTMP"))
        if wtmp is not None:
            values.append({"path": "environment.water.temperature", "value": wtmp + 273.15, "source": source})

    log.info(f"[{station_id}] Extracted {len(values)} values")
    return values


def fetch_all_stations():
    """Fetch all stations and update the shared cache."""
    log.info("── NOAA fetch cycle starting ──")
    new_cache = {}
    for station_id, config in STATIONS.items():
        raw = fetch_station(station_id)
        if raw is None:
            log.warning(f"[{station_id}] Skipped — no data")
            continue
        values = extract_signalk_values(station_id, raw, config["collect"])
        if values:
            new_cache[station_id] = values

    with cache_lock:
        value_cache.update(new_cache)

    total = sum(len(v) for v in new_cache.values())
    log.info(f"── NOAA fetch done: {total} values cached from {len(new_cache)} stations ──")


# ─── Signal K WebSocket Injector ─────────────────────────────────────────────

def build_delta(values):
    """Build a Signal K delta message from a list of {path, value, source} dicts."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {
        "context": "vessels.self",
        "updates": [
            {
                "source": {
                    "label": v["source"],
                    "type": "sensor",
                },
                "timestamp": timestamp,
                "values": [
                    {"path": v["path"], "value": v["value"]}
                ],
            }
            for v in values
        ],
    }


def inject_to_signalk(all_values):
    """Connect to Signal K WebSocket and send a delta with all cached values."""
    if not all_values:
        log.warning("Nothing to inject — cache empty")
        return False

    delta = build_delta(all_values)
    delta_json = json.dumps(delta)

    try:
        ws_url = SIGNALK_WS_URL
        headers = {}
        if SIGNALK_TOKEN:
            headers["Authorization"] = f"Bearer {SIGNALK_TOKEN}"

        ws = websocket.create_connection(ws_url, timeout=10, header=headers)
        ws.send(delta_json)
        ws.close()
        log.info(f"✅ Injected {len(all_values)} values into Signal K")
        return True

    except Exception as e:
        log.error(f"Signal K WebSocket injection failed: {e}")
        return False


def get_all_cached_values():
    """Flatten all cached values from all stations."""
    with cache_lock:
        return [v for values in value_cache.values() for v in values]


# ─── Main loops ───────────────────────────────────────────────────────────────

def fetch_loop():
    """Loop A — Fetch new NOAA data every FETCH_INTERVAL seconds."""
    while True:
        fetch_all_stations()
        log.info(f"Next NOAA fetch in {FETCH_INTERVAL // 60} min")
        time.sleep(FETCH_INTERVAL)


def inject_loop():
    """Loop B — Inject cached values into Signal K every INJECT_INTERVAL seconds."""
    log.info(f"Inject loop: waiting {INJECT_INTERVAL}s for initial fetch...")
    time.sleep(INJECT_INTERVAL)

    while True:
        values = get_all_cached_values()
        if values:
            inject_to_signalk(values)
        else:
            log.warning("Inject loop: cache empty, skipping")
        time.sleep(INJECT_INTERVAL)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NOAA NDBC Collector → Signal K")
    parser.add_argument("--once", action="store_true", help="Run one fetch+inject cycle, then exit")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.once:
        fetch_all_stations()
        values = get_all_cached_values()
        success = inject_to_signalk(values)
        sys.exit(0 if success else 1)

    log.info(f"Starting NOAA collector daemon")
    log.info(f" Fetch interval : {FETCH_INTERVAL // 60} min (NOAA update rate)")
    log.info(f" Inject interval: {INJECT_INTERVAL // 60} min (Signal K heartbeat)")

    t_fetch = threading.Thread(target=fetch_loop, daemon=True, name="noaa-fetch")
    t_inject = threading.Thread(target=inject_loop, daemon=True, name="signalk-inject")

    t_fetch.start()
    t_inject.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Interrupted — shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()

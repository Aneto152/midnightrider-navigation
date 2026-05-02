#!/usr/bin/env python3
"""
RPi Resource Monitor — Midnight Rider Navigation

Collect CPU, memory, disk, temperature and write to InfluxDB.

Usage:
  python3 scripts/monitor_resources.py          # run once
  python3 scripts/monitor_resources.py --daemon # loop every 30s
"""

import psutil
import os
import json
import logging
import time
import argparse
import sys
from datetime import datetime

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUX_AVAILABLE = True
except ImportError:
    INFLUX_AVAILABLE = False

INFLUX_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "MidnightRider")
INFLUX_BUCKET = "midnight_rider"
INTERVAL_SEC = 30

LOG_FILE = "/tmp/monitor_resources.log"
REPORT_FILE = "/tmp/rpi_resources.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RPi Monitor] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ]
)
log = logging.getLogger(__name__)

def get_temperature():
    """Return CPU temperature in Celsius (RPi only)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_millideg = int(f.read().strip())
            return temp_millideg / 1000.0
    except Exception:
        return None

def collect_metrics():
    """Collect all system metrics."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_temp_celsius": get_temperature(),
        "memory_percent": mem.percent,
        "memory_used_mb": mem.used // (1024 * 1024),
        "memory_total_mb": mem.total // (1024 * 1024),
        "disk_percent": disk.percent,
        "disk_used_gb": disk.used // (1024 ** 3),
        "disk_total_gb": disk.total // (1024 ** 3),
    }

def write_to_influxdb(metrics):
    """Write system metrics to InfluxDB."""
    if not INFLUX_AVAILABLE:
        log.warning("influxdb-client not installed")
        return False
    
    if not INFLUX_TOKEN:
        log.warning("INFLUX_TOKEN not set in .env")
        return False
    
    try:
        with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            
            point = (Point("system")
                .field("cpu_percent", float(metrics["cpu_percent"]))
                .field("memory_percent", float(metrics["memory_percent"]))
                .field("disk_percent", float(metrics["disk_percent"]))
                .field("memory_used_mb", float(metrics["memory_used_mb"]))
                .field("disk_used_gb", float(metrics["disk_used_gb"])))
            
            if metrics["cpu_temp_celsius"] is not None:
                point = point.field("cpu_temp_celsius", float(metrics["cpu_temp_celsius"]))
            
            write_api.write(bucket=INFLUX_BUCKET, record=point)
            return True
    
    except Exception as e:
        log.error(f"InfluxDB write error: {e}")
        return False

def save_json_report(metrics):
    """Save metrics to JSON file."""
    try:
        with open(REPORT_FILE, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
    except Exception as e:
        log.error(f"JSON save error: {e}")

def run_once(verbose=False):
    """Collect metrics and write to InfluxDB + JSON."""
    metrics = collect_metrics()
    influx_ok = write_to_influxdb(metrics)
    save_json_report(metrics)
    
    if verbose or not influx_ok:
        temp_str = f"{metrics['cpu_temp_celsius']:.1f}°C" if metrics['cpu_temp_celsius'] else "N/A"
        log.info(
            f"CPU: {metrics['cpu_percent']:.1f}% | "
            f"Temp: {temp_str} | "
            f"RAM: {metrics['memory_percent']:.1f}% | "
            f"Disk: {metrics['disk_percent']:.1f}% | "
            f"InfluxDB: {'✅' if influx_ok else '❌'}"
        )
    
    return metrics, influx_ok

def main():
    parser = argparse.ArgumentParser(description="RPi Resource Monitor")
    parser.add_argument("--daemon", action="store_true", 
                       help=f"Loop every {INTERVAL_SEC}s")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not INFLUX_AVAILABLE:
        log.error("influxdb-client missing. Run: pip3 install influxdb-client")
        sys.exit(1)
    
    if args.daemon:
        log.info(f"Daemon mode — writing to InfluxDB every {INTERVAL_SEC}s")
        while True:
            try:
                run_once()
            except Exception as e:
                log.error(f"Loop error: {e}")
            time.sleep(INTERVAL_SEC)
    else:
        metrics, ok = run_once(verbose=True)
        print(json.dumps(metrics, indent=2, default=str))
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

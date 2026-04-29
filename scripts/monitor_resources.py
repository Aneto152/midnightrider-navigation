#!/usr/bin/env python3
"""
RPi Resource Monitor — Midnight Rider Navigation

Monitor CPU, memory, disk, temperature, and process usage.
Logs to /tmp/rpi_resources.log and alerts if thresholds exceeded.

Usage:
  python3 scripts/monitor_resources.py # run once
  python3 scripts/monitor_resources.py --daemon # run forever (every 60s)
  python3 scripts/monitor_resources.py --debug # verbose output
"""

import psutil
import os
import subprocess
import json
import logging
import time
import argparse
import sys
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

THRESHOLDS = {
    "cpu_percent": 80,        # Alert if CPU > 80%
    "memory_percent": 85,     # Alert if RAM > 85%
    "disk_percent": 90,       # Alert if disk > 90%
    "temp_celsius": 75,       # Alert if temp > 75°C
}

LOG_FILE = "/tmp/rpi_resources.log"
REPORT_FILE = "/tmp/rpi_resources.json"

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RPi Monitor] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ]
)
log = logging.getLogger(__name__)


# ─── Collectors ───────────────────────────────────────────────────────────────

def get_cpu_info():
    """Return CPU usage %."""
    return psutil.cpu_percent(interval=1)


def get_memory_info():
    """Return memory usage %."""
    mem = psutil.virtual_memory()
    return {
        "percent": mem.percent,
        "used_mb": mem.used // (1024 * 1024),
        "total_mb": mem.total // (1024 * 1024),
    }


def get_disk_info():
    """Return disk usage %."""
    disk = psutil.disk_usage("/")
    return {
        "percent": disk.percent,
        "used_gb": disk.used // (1024 * 1024 * 1024),
        "total_gb": disk.total // (1024 * 1024 * 1024),
    }


def get_temperature():
    """Return CPU temperature in Celsius (RPi only)."""
    try:
        # RPi temperature: /sys/class/thermal/thermal_zone0/temp (millidegrees)
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_millideg = int(f.read().strip())
            return temp_millideg / 1000.0
    except (FileNotFoundError, ValueError):
        return None


def get_process_info(process_names=None):
    """Return top processes by CPU + memory."""
    if process_names is None:
        process_names = ["signalk", "grafana", "influxd", "python3", "node", "chromium"]
    
    processes = {}
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            for pname in process_names:
                if pname.lower() in proc.info["name"].lower():
                    key = f"{proc.info['name']}_{proc.info['pid']}"
                    processes[key] = {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "cpu_percent": proc.info["cpu_percent"],
                        "memory_percent": proc.info["memory_percent"],
                    }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Return top 5 by memory
    return dict(sorted(processes.items(), key=lambda x: x[1]["memory_percent"], reverse=True)[:5])


def get_uptime():
    """Return system uptime in days."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
            return uptime_seconds / (24 * 3600)  # days
    except:
        return None


# ─── Alerting ─────────────────────────────────────────────────────────────────

def check_thresholds(metrics):
    """Check if any metrics exceed thresholds and log alerts."""
    alerts = []
    
    if metrics["cpu"] > THRESHOLDS["cpu_percent"]:
        msg = f"⚠️ HIGH CPU: {metrics['cpu']:.1f}% (threshold: {THRESHOLDS['cpu_percent']}%)"
        alerts.append(msg)
        log.warning(msg)
    
    if metrics["memory"]["percent"] > THRESHOLDS["memory_percent"]:
        msg = f"⚠️ HIGH MEMORY: {metrics['memory']['percent']:.1f}% ({metrics['memory']['used_mb']}MB/{metrics['memory']['total_mb']}MB)"
        alerts.append(msg)
        log.warning(msg)
    
    if metrics["disk"]["percent"] > THRESHOLDS["disk_percent"]:
        msg = f"⚠️ LOW DISK SPACE: {metrics['disk']['percent']:.1f}% used ({metrics['disk']['used_gb']}GB/{metrics['disk']['total_gb']}GB)"
        alerts.append(msg)
        log.warning(msg)
    
    if metrics["temperature"] and metrics["temperature"] > THRESHOLDS["temp_celsius"]:
        msg = f"⚠️ HIGH TEMPERATURE: {metrics['temperature']:.1f}°C (threshold: {THRESHOLDS['temp_celsius']}°C)"
        alerts.append(msg)
        log.warning(msg)
    
    return alerts


# ─── Main ─────────────────────────────────────────────────────────────────────

def collect_metrics():
    """Collect all metrics and return as dict."""
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "temperature": get_temperature(),
        "uptime_days": get_uptime(),
        "top_processes": get_process_info(),
    }


def report_metrics(metrics):
    """Log metrics and save to JSON."""
    log.info(f"CPU: {metrics['cpu']:.1f}% | "
             f"Memory: {metrics['memory']['percent']:.1f}% ({metrics['memory']['used_mb']}MB) | "
             f"Disk: {metrics['disk']['percent']:.1f}% ({metrics['disk']['used_gb']}GB) | "
             f"Temp: {metrics['temperature']:.1f}°C | "
             f"Uptime: {metrics['uptime_days']:.1f}d")
    
    # Save JSON report
    with open(REPORT_FILE, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    
    # Check thresholds
    check_thresholds(metrics)


def main():
    parser = argparse.ArgumentParser(description="RPi Resource Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run forever (every 60s)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.daemon:
        log.info("Starting daemon mode (60s intervals)")
        while True:
            try:
                metrics = collect_metrics()
                report_metrics(metrics)
            except Exception as e:
                log.error(f"Error collecting metrics: {e}")
            time.sleep(60)
    else:
        metrics = collect_metrics()
        report_metrics(metrics)
        print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()

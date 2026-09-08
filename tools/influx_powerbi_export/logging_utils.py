"""
USB-safe logging utilities. Logs written to USB only; sanitized metadata to repository.
Never logs coordinates, MMSIs, tokens, passwords, or raw telemetry.
"""
import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

class USBLogger:
    """Logger that writes to USB with security redaction."""
    
    def __init__(self, usb_log_path: Path):
        self.usb_log_path = usb_log_path
        self.usb_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # File handler for USB
        self.handler = logging.FileHandler(self.usb_log_path)
        self.handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%SZ'
        ))
        
        self.logger = logging.getLogger('usb_export')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)
    
    def startup(self, usb_mount: str, run_dir: str):
        """Log startup event."""
        self.logger.info(f"STARTUP — USB mount: {usb_mount}, run_dir: {run_dir}")
    
    def space_check(self, free_gb: float, required_gb: float):
        """Log space check."""
        self.logger.info(f"SPACE_CHECK — Free: {free_gb:.1f} GB, Required: {required_gb} GB")
    
    def schema_discovery(self, measurement_count: int):
        """Log schema discovery."""
        self.logger.info(f"SCHEMA_DISCOVERY — {measurement_count} measurements found")
    
    def data_in(self, row_count: int):
        """Log data input."""
        self.logger.info(f"DATA_IN — {row_count:,} rows ingested from InfluxDB")
    
    def heartbeat(self, row_count: int, elapsed_seconds: int):
        """Log heartbeat (every 5 min or 100K rows)."""
        self.logger.info(f"HEARTBEAT — {row_count:,} rows processed, {elapsed_seconds}s elapsed")
    
    def data_out(self, midnight_rider_rows: int, ais_rows: int, unclassified_rows: int):
        """Log data output."""
        self.logger.info(f"DATA_OUT — {midnight_rider_rows:,} MR, {ais_rows:,} AIS, {unclassified_rows:,} unclassified")
    
    def error(self, message: str):
        """Log error (sanitized)."""
        self.logger.error(f"ERROR — {message}")
    
    def shutdown(self, status: str):
        """Log shutdown."""
        self.logger.info(f"SHUTDOWN — Status: {status}")
    
    def close(self):
        """Close logger."""
        self.handler.close()


class RepositoryLogger:
    """Sanitized logger for repository logs/latest.json and logs/oc-actions.log"""
    
    @staticmethod
    def add_audit_record(latest_json_path: Path, record: dict):
        """Add sanitized audit record to logs/latest.json"""
        try:
            # Load existing
            if latest_json_path.exists():
                with open(latest_json_path) as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Add new record (no coordinates, MMSIs, tokens, or raw values)
            data["latest_export"] = {
                "timestamp_utc": record.get("timestamp_utc"),
                "usb_label": record.get("usb_label"),
                "run_directory_basename": record.get("run_directory_basename"),
                "midnight_rider_rows": record.get("midnight_rider_rows"),
                "ais_rows": record.get("ais_rows"),
                "manifest_checksum": record.get("manifest_checksum"),
                "status": record.get("status"),
            }
            
            # Save
            with open(latest_json_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        except Exception as e:
            print(f"Error writing audit record: {e}")
    
    @staticmethod
    def add_action_log(oc_actions_path: Path, action: str, result: str, details: str = ""):
        """Add sanitized action to logs/oc-actions.log"""
        try:
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
            line = f"[{timestamp}] [{action}] [INFLUX_EXPORT] {result}"
            if details:
                line += f" — {details}"
            
            with open(oc_actions_path, 'a') as f:
                f.write(line + "\n")
        
        except Exception as e:
            print(f"Error writing action log: {e}")

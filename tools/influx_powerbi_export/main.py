"""
Main orchestration for USB-first InfluxDB Power BI exporter.
"""
import os
import sys
from pathlib import Path
from datetime import datetime

from . import cli, schema
from .influx_client import InfluxClient
from .annotated_csv import AnnotatedCSVParser
from .classifier import Classifier
from .normalizer import Normalizer
from .writers import CSVWriter, ManifestWriter
from .logging_utils import USBLogger, RepositoryLogger

def main(args=None):
    """Main exporter entry point."""
    try:
        # Parse arguments
        args = cli.parse_args(args)
        
        # Discover and validate USB
        usb_mount = discover_usb(args.usb_label)
        if not usb_mount:
            print("FAIL: USB not found and unavailable. Failing closed.")
            return 1
        
        # Validate output directory
        output_dir = cli.validate_output_dir(args.output_dir, str(usb_mount))
        
        # Create run directory
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        run_dir = output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "output").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        (run_dir / "diagnostics").mkdir(exist_ok=True)
        
        # Initialize USB logger
        usb_logger = USBLogger(run_dir / "logs" / "exporter.log")
        usb_logger.startup(str(usb_mount), str(run_dir))
        
        # Check free space
        free_gb = get_free_space(usb_mount) / (1024**3)
        usb_logger.space_check(free_gb, 15)
        
        if free_gb < 15:
            usb_logger.error("Insufficient free space")
            usb_logger.shutdown("FAILED")
            return 1
        
        # Initialize InfluxDB client
        try:
            client = InfluxClient()
        except ValueError as e:
            usb_logger.error(str(e))
            usb_logger.shutdown("FAILED")
            return 1
        
        # Query InfluxDB
        usb_logger.schema_discovery(0)  # Will update after schema query
        
        if args.dry_run:
            print(f"DRY RUN: Would export to {run_dir}")
            usb_logger.shutdown("DRY_RUN")
            return 0
        
        # Main processing pipeline
        classifier = Classifier()
        normalizer = Normalizer()
        
        midnight_rider_rows = 0
        ais_rows = 0
        unclassified_rows = 0
        duplicates_removed = 0
        
        # Stream data from InfluxDB
        try:
            parser = AnnotatedCSVParser()
            data_generator = client.query_range(args.start, args.stop)
            
            for record in parser.parse_stream(data_generator):
                classification = classifier.classify(record)
                
                if classification == "midnight_rider":
                    midnight_rider_rows += 1
                    # Process for 10-second aggregation
                    timestamp = record.get("_time")
                    field = record.get("_field")
                    value = parser.safe_float(record.get("_value"))
                    normalizer.add_point(timestamp, field, value)
                
                elif classification == "ais":
                    ais_rows += 1
                
                else:
                    unclassified_rows += 1
                
                # Heartbeat logging
                total_rows = midnight_rider_rows + ais_rows + unclassified_rows
                if total_rows % 100000 == 0:
                    usb_logger.heartbeat(total_rows, 0)
        
        except Exception as e:
            usb_logger.error(str(e))
            usb_logger.shutdown("FAILED")
            return 1
        
        usb_logger.data_in(midnight_rider_rows + ais_rows + unclassified_rows)
        
        # Aggregate Midnight Rider windows
        mr_windows = normalizer.aggregate_windows()
        
        # Write output CSVs
        mr_writer = CSVWriter(run_dir / "output" / "MIDNIGHT_RIDER_10S_AGGREGATES.csv")
        mr_count = mr_writer.write_csv(mr_windows, schema.get_midnight_rider_headers())
        
        # TODO: AIS processing and output
        
        usb_logger.data_out(mr_count, ais_rows, unclassified_rows)
        
        # Write manifest
        manifest_writer = ManifestWriter(run_dir / "output" / "EXPORT_MANIFEST.json")
        manifest_writer.add_metadata("export_id", f"midnight_rider_powerbi_{run_id}")
        manifest_writer.add_metadata("export_timestamp_utc", datetime.utcnow().isoformat() + "Z")
        manifest_writer.add_metadata("data_window_start_utc", args.start)
        manifest_writer.add_metadata("data_window_end_utc", args.stop)
        manifest_writer.add_counts(mr_count, ais_rows, unclassified_rows, duplicates_removed)
        checksum = manifest_writer.write()
        
        # Update repository logs
        RepositoryLogger.add_audit_record(
            Path("/home/aneto/midnightrider-navigation/logs/latest.json"),
            {
                "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                "usb_label": args.usb_label,
                "run_directory_basename": run_id,
                "midnight_rider_rows": mr_count,
                "ais_rows": ais_rows,
                "manifest_checksum": checksum,
                "status": "SUCCESS",
            }
        )
        
        usb_logger.shutdown("SUCCESS")
        print(f"✓ Export complete: {run_dir}")
        return 0
    
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        return 1

def discover_usb(label: str = "Lexar") -> Path:
    """Discover USB by filesystem label.
    
    Searches findmnt JSON output for a filesystem matching:
    - fstype == "exfat"
    - label == requested label
    
    Returns the target mount path, or None if not found.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["findmnt", "-J", "-o", "FSTYPE,LABEL,TARGET"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            import json
            mounts = json.loads(result.stdout)
            # Search for matching mount in JSON tree
            def find_mount(node):
                if isinstance(node, dict):
                    # Check if this node matches the criteria
                    if node.get("fstype") == "exfat" and node.get("label") == label:
                        return node.get("target")
                    # Recursively search top-level "filesystems" array
                    if "filesystems" in node:
                        for item in node["filesystems"]:
                            result = find_mount(item)
                            if result:
                                return result
                    # Recursively search nested "children" arrays
                    if "children" in node:
                        for child in node["children"]:
                            result = find_mount(child)
                            if result:
                                return result
                elif isinstance(node, list):
                    for item in node:
                        result = find_mount(item)
                        if result:
                            return result
                return None
            
            mount = find_mount(mounts)
            return Path(mount) if mount else None
    except Exception:
        pass
    return None

def get_free_space(path: Path) -> int:
    """Get free space in bytes."""
    import os
    stat = os.statvfs(str(path))
    return stat.f_bavail * stat.f_frsize

if __name__ == "__main__":
    sys.exit(main())

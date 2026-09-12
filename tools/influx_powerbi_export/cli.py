"""
Command-line interface for InfluxDB Power BI exporter.
"""
import argparse
import sys
from pathlib import Path

def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.influx_powerbi_export",
        description="USB-first InfluxDB Power BI exporter"
    )
    
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start time (ISO 8601, e.g., 2026-08-31T19:43:24Z)"
    )
    
    parser.add_argument(
        "--stop",
        type=str,
        required=True,
        help="Stop time (ISO 8601, e.g., 2026-09-07T19:43:24Z)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory on USB (validated; defaults to USB auto-detected)"
    )
    
    parser.add_argument(
        "--usb-label",
        type=str,
        default="Lexar",
        help="USB filesystem label (default: Lexar)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview export without writing to USB"
    )
    
    parser.add_argument(
        "--schema-report",
        action="store_true",
        help="Generate schema discovery report only"
    )
    
    parser.add_argument(
        "--include-unclassified",
        action="store_true",
        help="Include unclassified records in output"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--query-timeout-seconds",
        type=int,
        default=1200,
        help="Query execution timeout per chunk in seconds (default: 1200s / 20 min). "
             "Covers InfluxDB query startup and execution. Must be positive."
    )
    
    parser.add_argument(
        "--stream-idle-timeout-seconds",
        type=int,
        default=60,
        help="Stream idle timeout in seconds (default: 60s). "
             "If no data arrives for this duration, stream reading times out."
    )
    
    parser.add_argument(
        "--chunk-hours",
        type=float,
        default=6.0,
        help="Duration of each chunk in hours (default: 6.0). "
             "Smaller chunks = more restarts but quicker recovery. "
             "Larger chunks = fewer restarts but longer per-chunk processing."
    )
    
    parser.add_argument(
        "--max-chunk-retries",
        type=int,
        default=3,
        help="Maximum number of retries per failed chunk (default: 3). "
             "After this many failures, the chunk is marked as permanently failed."
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (if one exists in output directory). "
             "Completed chunks are skipped; failed chunks can be retried."
    )
    
    parser.add_argument(
        "--checkpoint-path",
        type=str,
        help="Explicit path to checkpoint manifest (CHECKPOINT.json). "
             "If not provided, defaults to <output_dir>/CHECKPOINT.json"
    )
    
    parser.add_argument(
        "--window-mode",
        type=str,
        choices=["fixed", "rolling"],
        default="fixed",
        help="Windowing mode for aggregation: 'fixed' (non-overlapping 10s windows) "
             "or 'rolling' (overlapping 1-second step). Default: fixed."
    )
    return parser

def validate_output_dir(output_dir: str, usb_mount: str) -> Path:
    """Validate output directory is on USB mount."""
    if not output_dir:
        return Path(usb_mount) / "MidnightRider_Influx_Export"
    
    path = Path(output_dir)
    usb_path = Path(usb_mount)
    
    try:
        path.resolve().relative_to(usb_path.resolve())
    except ValueError:
        raise ValueError(f"Output directory {output_dir} is not on USB mount {usb_mount}")
    
    if ".." in str(path):
        raise ValueError("Output directory contains .. (symlink escape)")
    
    for forbidden in ["/tmp", "/home/aneto", "/var/tmp", "/root"]:
        if str(path).startswith(forbidden):
            raise ValueError(f"Output directory cannot be under {forbidden}")
    
    return path

def parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_parser()
    return parser.parse_args(args)

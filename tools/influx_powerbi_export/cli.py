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

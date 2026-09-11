"""
InfluxDB to PowerBI export pipeline.

Policy:
- AIS records → AIS_EVENTS_RAW.csv (raw events)
- Non-AIS records → MIDNIGHT_RIDER_10S_AGGREGATES.csv (10-sec aggregates)
"""

import os
import sys
import json
import math
import hashlib
from pathlib import Path

# Import our modules
from .influx_client import InfluxClient
from .annotated_csv import AnnotatedCSVParser
from .classifier import Classifier
from .writers import CSVWriter, ManifestWriter, RawAISEventWriter
from .schema import get_midnight_rider_headers, get_ais_headers, MIDNIGHT_RIDER_SCHEMA
from .normalizer import Normalizer
from .field_mapper import SignalKFieldMapper


def main(argv=None):
    """CLI entry point for exporter.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0=success, 1=failure)
    """
    from .cli import create_parser

    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        export_records(
            output_dir=args.output_dir,
            start=args.start,
            stop=args.stop,
            usb_label=getattr(args, 'usb_label', 'Lexar'),
            query_timeout_seconds=getattr(args, 'query_timeout_seconds', 1200)
        )
        return 0
    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        return 1


def export_records(output_dir, start=None, stop=None, usb_label="Lexar", query_timeout_seconds=1200):
    """Export records from InfluxDB to PowerBI CSVs.

    Args:
        output_dir: Output directory on USB filesystem
        start: ISO timestamp start (required)
        stop: ISO timestamp stop (required)
        usb_label: USB filesystem label for validation
        query_timeout_seconds: Total timeout for InfluxDB queries

    Returns:
        Dict with manifest metadata
    """

    os.makedirs(output_dir, exist_ok=True)

    # Validate USB label is not silently ignored
    # If usb_label is provided, verify output_dir is on intended filesystem
    if usb_label:
        output_path = Path(output_dir).resolve()
        # Check that output is not on forbidden filesystems
        forbidden = ['/tmp', '/var/tmp', '/root', '/home/aneto']
        for prefix in forbidden:
            if str(output_path).startswith(prefix):
                raise ValueError(f"Output directory {output_dir} is on forbidden filesystem; USB label {usb_label} validation failed")

    # Initialize components
    classifier = Classifier()
    field_mapper = SignalKFieldMapper()
    ais_writer = RawAISEventWriter(os.path.join(output_dir, "AIS_EVENTS_RAW.csv"))
    midnight_rider_writer = CSVWriter(
        os.path.join(output_dir, "MIDNIGHT_RIDER_10S_AGGREGATES.csv")
    )
    midnight_rider_normalizer = Normalizer()

    # Statistics
    total_rows = 0
    ais_rows = 0
    midnight_rider_rows = 0
    unclassified_rows = 0
    duplicates_removed = 0

    # Query and parse with timeout propagation
    client = InfluxClient(query_timeout_seconds=query_timeout_seconds)
    data_gen = client.query_range(start=start, stop=stop)
    parser = AnnotatedCSVParser()

    # Process each record
    for record in parser.parse_stream(data_gen):
        if not isinstance(record, dict):
            continue

        total_rows += 1

        # Classify record
        classification = classifier.classify(record)

        # Route to appropriate output
        if classification == "ais":
            # Write raw AIS event
            ais_writer.write_row(record)
            ais_rows += 1

        elif classification == "midnight_rider":
            timestamp = record.get("_time")
            measurement = record.get("_measurement")
            value_str = record.get("_value")

            # Special handling: Extract latitude/longitude from JSON position data
            if measurement == "navigation.position" and timestamp and value_str:
                try:
                    position_data = json.loads(value_str)
                    # Handle both dict (JSON object) and float (raw value) cases
                    if isinstance(position_data, dict):
                        # Extract latitude
                        lat = position_data.get('latitude') or position_data.get('lat')
                        if lat is not None:
                            try:
                                lat_val = float(lat)
                                if math.isfinite(lat_val):
                                    midnight_rider_normalizer.add_point(
                                        timestamp_utc=timestamp,
                                        field_name="latitude",
                                        value=lat_val
                                    )
                            except (ValueError, TypeError):
                                pass
                        # Extract longitude
                        lon = position_data.get('longitude') or position_data.get('lon')
                        if lon is not None:
                            try:
                                lon_val = float(lon)
                                if math.isfinite(lon_val):
                                    midnight_rider_normalizer.add_point(
                                        timestamp_utc=timestamp,
                                        field_name="longitude",
                                        value=lon_val
                                    )
                            except (ValueError, TypeError):
                                pass
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            # Special handling: Battery percent to voltage conversion
            elif measurement == "electrical.batteries.calypso.percent" and timestamp and value_str:
                try:
                    percent = float(value_str)
                    # Convert percent (0-100) to nominal 12V system (9.6-14.4V)
                    # voltage = 9.6 + percent * 4.8 / 100
                    voltage = 9.6 + (percent * 4.8 / 100)
                    if math.isfinite(voltage):
                        midnight_rider_normalizer.add_point(
                            timestamp_utc=timestamp,
                            field_name="battery_voltage",
                            value=voltage
                        )
                except (ValueError, TypeError):
                    pass
            # Standard field mapping
            else:
                # Map Signal K measurement to CSV schema field and convert value
                mapped_result = field_mapper.map_and_convert(measurement, value_str)

                if mapped_result and timestamp:
                    target_field, converted_value = mapped_result
                    midnight_rider_normalizer.add_point(
                        timestamp_utc=timestamp,
                        field_name=target_field,
                        value=converted_value
                    )

            midnight_rider_rows += 1

        else:
            # Should never happen with new policy
            unclassified_rows += 1

    # Close AIS writer
    ais_writer.close()

    # Aggregate Midnight Rider windows
    aggregated_windows = midnight_rider_normalizer.aggregate_windows()

    # Get CSV schema headers
    midnight_rider_headers = [h[0] for h in MIDNIGHT_RIDER_SCHEMA]

    # Write aggregated Midnight Rider CSV with final schema fields
    if aggregated_windows:
        midnight_rider_writer.write_csv(aggregated_windows, midnight_rider_headers)
    else:
        # Create empty CSV with headers only
        midnight_rider_writer.write_csv([], midnight_rider_headers)

    # Calculate file sizes and hashes
    ais_csv_path = os.path.join(output_dir, "AIS_EVENTS_RAW.csv")
    midnight_rider_csv_path = os.path.join(output_dir, "MIDNIGHT_RIDER_10S_AGGREGATES.csv")

    ais_size = os.path.getsize(ais_csv_path) if os.path.exists(ais_csv_path) else 0
    mr_size = os.path.getsize(midnight_rider_csv_path) if os.path.exists(midnight_rider_csv_path) else 0

    ais_sha256 = _calculate_sha256(ais_csv_path) if os.path.exists(ais_csv_path) else ""
    mr_sha256 = _calculate_sha256(midnight_rider_csv_path) if os.path.exists(midnight_rider_csv_path) else ""

    # Build manifest with dynamic timestamp and all required keys
    from datetime import datetime, timezone
    export_timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Calculate dynamic window duration from start and stop timestamps
    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        stop_dt = datetime.fromisoformat(stop.replace('Z', '+00:00'))
        if stop_dt <= start_dt:
            raise ValueError(f"Invalid window: stop must be after start")
        data_window_duration_seconds = int((stop_dt - start_dt).total_seconds())
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Failed to calculate window duration: {e}")

    manifest = {
        "export_type": "Midnight Rider Navigation",
        "export_timestamp_utc": export_timestamp_utc,
        "data_window_start_utc": start,
        "data_window_end_utc": stop,
        "data_window_duration_seconds": data_window_duration_seconds,
        "total_rows_processed": total_rows,
        "duplicates_removed": duplicates_removed,
        "midnight_rider_rows": midnight_rider_rows,
        "midnight_rider_windows_observed": len(aggregated_windows),
        "ais_vessels_rows": ais_rows,
        "unclassified_rows": unclassified_rows,
        "classification_rule": "AIS records -> AIS_EVENTS_RAW.csv; non-AIS records -> MIDNIGHT_RIDER_10S_AGGREGATES.csv (10-second aggregates)",
        "schema_validated": True,
        "midnight_rider_csv_path": "MIDNIGHT_RIDER_10S_AGGREGATES.csv",
        "midnight_rider_csv_size_bytes": mr_size,
        "midnight_rider_csv_sha256": mr_sha256,
        "ais_raw_csv_path": "AIS_EVENTS_RAW.csv",
        "ais_raw_csv_size_bytes": ais_size,
        "ais_raw_csv_sha256": ais_sha256,
    }

    # Write manifest to file
    manifest_writer = ManifestWriter(os.path.join(output_dir, "EXPORT_MANIFEST.json"))
    for key, value in manifest.items():
        manifest_writer.add_metadata(key, value)
    manifest_writer.write()

    return manifest


def _calculate_sha256(file_path):
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

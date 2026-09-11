"""
InfluxDB to PowerBI export pipeline.

Policy:
- AIS records → AIS_EVENTS_RAW.csv (raw events)
- Non-AIS records → MIDNIGHT_RIDER_10S_AGGREGATES.csv (10-sec aggregates)
"""

import os
import sys
import hashlib
from pathlib import Path

# Import our modules
from .influx_client import InfluxClient
from .annotated_csv import AnnotatedCSVParser
from .classifier import Classifier
from .writers import CSVWriter, ManifestWriter, RawAISEventWriter
from .schema import get_midnight_rider_headers, get_ais_headers
from .normalizer import Normalizer


def export_records(output_dir, start=None, stop=None):
    """Export records from InfluxDB to PowerBI CSVs.
    
    Args:
        output_dir: Output directory
        start: ISO timestamp start (optional)
        stop: ISO timestamp stop (optional)
    
    Returns:
        Dict with manifest metadata
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    classifier = Classifier()
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
    
    # Query and parse
    client = InfluxClient()
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
            # Send to normalizer for aggregation
            # Use _measurement (Signal K path) as field name, _value as numeric payload, _time as timestamp
            timestamp = record.get("_time")
            measurement = record.get("_measurement")
            value_str = record.get("_value")
            
            # Convert value to float
            try:
                value = float(value_str) if value_str else None
            except (ValueError, TypeError):
                value = None
            
            # Add to normalizer if we have a valid measurement and value
            if timestamp and measurement and value is not None:
                midnight_rider_normalizer.add_point(
                    timestamp_utc=timestamp,
                    field_name=measurement,
                    value=value
                )
            
            midnight_rider_rows += 1
        
        else:
            # Should never happen with new policy
            unclassified_rows += 1
    
    # Close AIS writer
    ais_writer.close()
    
    # Aggregate Midnight Rider windows
    aggregated_windows = midnight_rider_normalizer.aggregate_windows()
    
    # Get headers from schema
    from .schema import MIDNIGHT_RIDER_SCHEMA
    midnight_rider_headers = [h[0] for h in MIDNIGHT_RIDER_SCHEMA]
    
    # Write aggregated Midnight Rider CSV
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
    
    # Build manifest
    manifest = {
        "export_type": "Midnight Rider Navigation",
        "export_timestamp": "2026-09-10T17:23:00Z",
        "total_rows_processed": total_rows,
        "duplicates_removed": duplicates_removed,
        "midnight_rider_rows": midnight_rider_rows,
        "ais_vessels_rows": ais_rows,
        "unclassified_rows": unclassified_rows,
        "classification_rule": "AIS records written as raw events to AIS_EVENTS_RAW.csv; all non-AIS records exported as 10-second Midnight Rider onboard aggregates",
        "midnight_rider_csv_path": midnight_rider_csv_path,
        "midnight_rider_csv_size_bytes": mr_size,
        "midnight_rider_csv_sha256": mr_sha256,
        "ais_raw_csv_path": ais_csv_path,
        "ais_raw_csv_size_bytes": ais_size,
        "ais_raw_csv_sha256": ais_sha256,
    }
    
    return manifest


def _calculate_sha256(file_path):
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

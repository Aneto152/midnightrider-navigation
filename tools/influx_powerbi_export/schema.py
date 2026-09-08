"""
Output schema definitions for Midnight Rider and AIS datasets.
"""
from typing import Dict, List, Tuple

# Midnight Rider 10-second aggregates schema
MIDNIGHT_RIDER_SCHEMA = [
    ("timestamp_utc", "datetime", "Center of 10-second window"),
    ("window_start_utc", "datetime", "Window start (UTC)"),
    ("window_end_utc", "datetime", "Window end (UTC)"),
    ("sample_count", "int", "Number of data points in window"),
    ("source_count", "int", "Number of distinct sources"),
    ("completeness_ratio", "float", "Observed samples / expected samples"),
    ("sog_knots", "float", "Speed over ground (arithmetic mean)"),
    ("cog_deg", "float", "Course over ground (circular mean)"),
    ("latitude", "float", "Latitude (latest or mean) — DO NOT LOG"),
    ("longitude", "float", "Longitude (latest or mean) — DO NOT LOG"),
    ("awa_deg", "float", "Apparent wind angle (circular mean)"),
    ("aws_knots", "float", "Apparent wind speed (arithmetic mean)"),
    ("twa_deg", "float", "True wind angle (circular mean)"),
    ("tws_knots", "float", "True wind speed (arithmetic mean)"),
    ("true_heading_deg", "float", "True heading (circular mean)"),
    ("tide_set_deg", "float", "Tide set (circular mean)"),
    ("tide_rate_knots", "float", "Tide rate (arithmetic mean)"),
    ("roll_deg", "float", "Roll angle (arithmetic mean)"),
    ("pitch_deg", "float", "Pitch angle (arithmetic mean)"),
    ("depth_m", "float", "Depth below transducer (arithmetic mean)"),
    ("stw_knots", "float", "Speed through water (arithmetic mean)"),
    ("battery_voltage", "float", "Battery voltage (arithmetic mean)"),
    ("quality_flag", "string", "GOOD|POOR|MISSING based on completeness"),
]

# AIS vessels events schema
AIS_SCHEMA = [
    ("timestamp_utc", "datetime", "Event timestamp"),
    ("mmsi", "string", "Maritime Mobile Service Identity — DO NOT LOG"),
    ("vessel_name", "string", "Vessel name — DO NOT LOG"),
    ("latitude", "float", "AIS position latitude — DO NOT LOG"),
    ("longitude", "float", "AIS position longitude — DO NOT LOG"),
    ("sog_knots", "float", "Speed over ground from AIS"),
    ("cog_deg", "float", "Course over ground from AIS"),
    ("true_heading_deg", "float", "True heading from AIS"),
    ("rate_of_turn_deg_min", "float", "Rate of turn from AIS"),
    ("navigation_status", "string", "AIS navigation status"),
    ("vessel_type", "string", "AIS vessel type classification"),
    ("source_count", "int", "Number of sources reporting this event"),
    ("field_count", "int", "Number of fields in aggregated event"),
    ("conflict_count", "int", "Number of conflicting values"),
    ("quality_flag", "string", "VALID|OFF_POSITION|SYNTHETIC_DATA|CONFLICT"),
]

# Manifest metadata schema
MANIFEST_SCHEMA = {
    "export_id": "str",
    "export_timestamp_utc": "str",
    "data_window_start_utc": "str",
    "data_window_end_utc": "str",
    "data_window_days": "int",
    "source_database": "str (InfluxDB)",
    "source_bucket": "str (midnight_rider)",
    "source_organization": "str (MidnightRider)",
    "midnight_rider_rows": "int",
    "midnight_rider_windows_expected": "int (60480 for 7 days)",
    "midnight_rider_windows_observed": "int",
    "midnight_rider_windows_empty": "int",
    "ais_vessels_rows": "int",
    "ais_distinct_vessels": "int",
    "unclassified_rows": "int",
    "total_rows_processed": "int",
    "duplicates_removed": "int",
    "exact_duplicate_key": "str (_time, _measurement, _field, tags, source)",
    "midnight_rider_classification_rule": "str (self=true OR self=empty AND navigation/sensors)",
    "ais_classification_rule": "str (context contains MMSI URN OR sensors.ais)",
    "measurements_count": "int",
    "sources_count": "int",
    "s2_cells_count": "int",
    "completeness_ratio": "float (observed_windows / possible_windows)",
    "data_gaps_gt_30min": "int",
    "coordinate_redaction_applied": "bool (always true in logs; present in CSV)",
    "mmsi_redaction_applied": "bool (always true in logs; present in CSV)",
    "pii_handling": "str (MASKED_IN_LOGS_ONLY_CSV_CONTAINS_DATA)",
    "circular_mean_fields": ["cog_deg", "true_heading_deg", "awa_deg", "twa_deg", "tide_set_deg"],
    "quality_checks": {
        "no_tokens_in_logs": "bool",
        "no_credentials_in_logs": "bool",
        "no_raw_coordinates_in_logs": "bool",
        "no_raw_mmsi_in_logs": "bool",
        "gitignore_enforced": "bool",
        "no_export_on_local_disk": "bool",
        "schema_validated": "bool",
    },
}

def get_midnight_rider_headers() -> List[str]:
    """Return CSV headers for Midnight Rider 10-second aggregates."""
    return [name for name, _, _ in MIDNIGHT_RIDER_SCHEMA]

def get_ais_headers() -> List[str]:
    """Return CSV headers for AIS vessel events."""
    return [name for name, _, _ in AIS_SCHEMA]

def describe_schema() -> Dict:
    """Return schema documentation."""
    return {
        "midnight_rider": {
            "description": "One logical row per observed 10-second UTC window",
            "fields": {name: desc for name, _, desc in MIDNIGHT_RIDER_SCHEMA},
            "aggregations": {
                "linear": ["sog_knots", "aws_knots", "tide_rate_knots", "roll_deg", "pitch_deg", "depth_m", "stw_knots", "battery_voltage"],
                "circular": ["cog_deg", "awa_deg", "twa_deg", "true_heading_deg", "tide_set_deg"],
                "latest": ["latitude", "longitude", "quality_flag"],
            },
        },
        "ais_vessels": {
            "description": "One logical row per AIS event (message or update)",
            "fields": {name: desc for name, _, desc in AIS_SCHEMA},
            "event_key": "(_time, context, source) with deduplication",
            "pii_present_in_csv": ["mmsi", "vessel_name", "latitude", "longitude"],
            "redacted_from_logs": True,
        },
    }

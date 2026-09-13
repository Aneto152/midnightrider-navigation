#!/usr/bin/env python3
"""Pure source URL helpers — no external dependencies."""

def ndbc_source_url(station_id):
    """Generate NDBC realtime2 source URL."""
    station_id = str(station_id).strip().upper()
    return f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"

def asos_source_url(station_id):
    """Generate NOAA Weather.gov observations latest URL."""
    station_id = str(station_id).strip().upper()
    return f"https://api.weather.gov/stations/{station_id}/observations/latest"

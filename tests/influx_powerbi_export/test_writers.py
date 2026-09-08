"""
Unit tests for CSV and manifest writers.
"""
import pytest
import tempfile
import json
from pathlib import Path
from tools.influx_powerbi_export.writers import CSVWriter, ManifestWriter

@pytest.fixture
def temp_output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

def test_csv_writer_creates_file(temp_output_dir):
    """CSV writer creates output file."""
    csv_path = temp_output_dir / "test.csv"
    writer = CSVWriter(csv_path)
    
    rows = [
        {"field1": "value1", "field2": "1.5"},
        {"field1": "value2", "field2": "2.5"},
    ]
    headers = ["field1", "field2"]
    
    count = writer.write_csv(rows, headers)
    
    assert csv_path.exists()
    assert count == 2
    
    with open(csv_path) as f:
        lines = f.readlines()
        assert len(lines) == 3  # Header + 2 data rows

def test_csv_writer_handles_null_values(temp_output_dir):
    """CSV writer handles None values."""
    csv_path = temp_output_dir / "test.csv"
    writer = CSVWriter(csv_path)
    
    rows = [
        {"field1": "value1", "field2": None},
        {"field1": None, "field2": "2.5"},
    ]
    headers = ["field1", "field2"]
    
    count = writer.write_csv(rows, headers)
    assert count == 2

def test_manifest_writer_creates_json(temp_output_dir):
    """Manifest writer creates valid JSON."""
    manifest_path = temp_output_dir / "manifest.json"
    writer = ManifestWriter(manifest_path)
    
    writer.add_metadata("export_id", "test_export_123")
    writer.add_metadata("source_bucket", "midnight_rider")
    writer.add_counts(1000, 500, 10, 5)
    
    checksum = writer.write()
    
    assert manifest_path.exists()
    assert len(checksum) == 64  # SHA-256 hex length
    
    with open(manifest_path) as f:
        data = json.load(f)
        assert data["export_id"] == "test_export_123"
        assert data["midnight_rider_rows"] == 1000
        assert data["ais_vessels_rows"] == 500
        assert data["unclassified_rows"] == 10
        assert data["duplicates_removed"] == 5

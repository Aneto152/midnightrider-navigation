"""
Unit tests for InfluxDB annotated CSV parsing.
"""
import pytest
from io import StringIO
from tools.influx_powerbi_export.annotated_csv import AnnotatedCSVParser

@pytest.fixture
def parser():
    return AnnotatedCSVParser()

def test_parse_simple_csv(parser):
    """Parse simple annotated CSV."""
    csv_data = """#group,false,false,true,true,false,true
#datatype,string,long,dateTime:RFC3339,dateTime:RFC3339,long,string
#default,_result,,,,,
,result,table,_start,_stop,_value,_measurement
,,0,2026-09-08T12:34:10Z,2026-09-08T12:34:20Z,8.5,navigation.speedOverGround
,,0,2026-09-08T12:34:15Z,2026-09-08T12:34:20Z,8.6,navigation.speedOverGround
"""
    lines = StringIO(csv_data).readlines()
    rows = list(parser.parse_stream(iter(lines)))
    
    assert len(rows) == 2
    assert rows[0]["_value"] == "8.5"
    assert rows[0]["_measurement"] == "navigation.speedOverGround"

def test_safe_float_conversion(parser):
    """Safe float conversion with None handling."""
    assert parser.safe_float("8.5") == 8.5
    assert parser.safe_float("") is None
    assert parser.safe_float(None) is None
    assert parser.safe_float("invalid") is None

def test_safe_int_conversion(parser):
    """Safe int conversion with None handling."""
    assert parser.safe_int("42") == 42
    assert parser.safe_int("") is None
    assert parser.safe_int(None) is None
    assert parser.safe_int("invalid") is None

def test_iso8601_to_seconds(parser):
    """Convert ISO8601 timestamp to Unix seconds."""
    seconds = parser.iso8601_to_seconds("2026-09-08T12:34:42Z")
    assert isinstance(seconds, float)
    assert seconds > 1000000000  # After year 2001

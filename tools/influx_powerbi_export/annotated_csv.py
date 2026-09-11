"""
InfluxDB annotated CSV parser — handles multiple Flux result tables.
Safely parses streaming CSV with annotation headers.
"""
from typing import Iterator, Dict, List, Optional
import csv

class AnnotatedCSVParser:
    """Parse InfluxDB annotated CSV format from streaming input."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset parser state."""
        self.group_headers = []
        self.datatype_headers = []
        self.current_table = 0
        self.row_number = 0
    
    def parse_stream(self, lines: Iterator[str]) -> Iterator[Dict]:
        """
        Parse annotated CSV stream, yield data rows as dicts.
        Skips annotation headers, handles multiple tables.
        
        Correctly detects Flux table boundaries:
        - csv.reader() splits on commas, so "result" marker row becomes:
          ["", "result", "table", "_start", "_stop", "_time", "_value", "_field", ...]
        - When detected, install this row as the active headers
        - Do NOT skip the row; it is the new header row for the next table
        - The following row will be the first actual data row
        """
        reader = csv.reader(lines)
        headers = None
        table_count = 0
        
        for row in reader:
            if not row:
                continue
            
            # Parse annotation headers
            if row[0] == '#group':
                self.group_headers = row[1:]
                continue
            
            if row[0] == '#datatype':
                self.datatype_headers = row[1:]
                continue
            
            if row[0] == '#default':
                # Skip default row
                continue
            
            # Check for table boundary (Flux result marker)
            # After csv.reader(), a row starting with ",result" becomes:
            # ["", "result", "table", "_start", "_stop", "_time", "_value", "_field", ...]
            is_table_header = (
                len(row) > 1 
                and row[0] == "" 
                and row[1] == "result"
            )
            
            if is_table_header:
                # New Flux table: install this row as the active headers
                table_count += 1
                headers = row
                self.group_headers = []
                self.datatype_headers = []
                # Do NOT skip; this row IS the header row for the next table
                # The following row will be the first actual data row
                continue
            
            # First data row (non-header, non-annotation) sets headers
            if headers is None:
                headers = row
                continue
            
            # Data row: convert to dict
            if len(row) == len(headers):
                data_dict = {}
                for i, header in enumerate(headers):
                    value = row[i]
                    # Preserve empty strings, convert None-like strings
                    if value in ['', None]:
                        data_dict[header] = None
                    else:
                        data_dict[header] = value
                
                self.row_number += 1
                yield data_dict
    
    def safe_float(self, value: Optional[str]) -> Optional[float]:
        """Safely convert string to float."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except ValueError:
            return None
    
    def safe_int(self, value: Optional[str]) -> Optional[int]:
        """Safely convert string to int."""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except ValueError:
            return None
    
    def iso8601_to_seconds(self, iso_timestamp: str) -> Optional[float]:
        """Convert ISO8601 timestamp to Unix seconds (float)."""
        if not iso_timestamp:
            return None
        try:
            # Simple parser for ISO8601: 2026-09-07T23:04:42.123456789Z
            from datetime import datetime
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.timestamp()
        except:
            return None

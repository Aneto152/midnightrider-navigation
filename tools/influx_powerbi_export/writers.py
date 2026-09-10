"""
USB CSV output writers for Midnight Rider and AIS datasets.
"""
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

class CSVWriter:
    """Write CSV output to USB with proper quoting and escaping."""
    
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.row_count = 0
    
    def write_csv(self, rows: List[Dict], headers: List[str]) -> int:
        """Write CSV file, return row count."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            
            for row in rows:
                # Ensure all headers present (fill missing with None)
                complete_row = {h: row.get(h) for h in headers}
                writer.writerow(complete_row)
                self.row_count += 1
        
        return self.row_count

class ManifestWriter:
    """Write export manifest JSON to USB."""
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.data = {}
    
    def add_metadata(self, key: str, value):
        """Add metadata to manifest."""
        self.data[key] = value
    
    def add_counts(self, midnight_rider_rows: int, ais_rows: int, 
                   unclassified_rows: int, duplicates_removed: int):
        """Add row counts to manifest."""
        self.data.update({
            "midnight_rider_rows": midnight_rider_rows,
            "ais_vessels_rows": ais_rows,
            "unclassified_rows": unclassified_rows,
            "duplicates_removed": duplicates_removed,
            "total_rows_processed": midnight_rider_rows + ais_rows + unclassified_rows + duplicates_removed,
        })
    
    def write(self) -> str:
        """Write manifest, return checksum."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.manifest_path, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
        
        # Compute checksum (sha256)
        import hashlib
        with open(self.manifest_path, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        return checksum


"""
Raw AIS event streaming writer.
"""
import csv
import os
import tempfile
from pathlib import Path


class RawAISEventWriter:
    """Write raw AIS events to CSV without aggregation."""
    
    COLUMNS = ["_time", "_measurement", "_field", "_value", "context", "source"]
    
    def __init__(self, output_path):
        """Initialize writer.
        
        Args:
            output_path: Final output file path
        """
        self.output_path = output_path
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.csv', text=True)
        self.temp_file = os.fdopen(self.temp_fd, 'w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.temp_file, fieldnames=self.COLUMNS)
        self.row_count = 0
        self._header_written = False
    
    def write_header(self):
        """Write CSV header once."""
        if not self._header_written:
            self.writer.writeheader()
            self._header_written = True
    
    def write_row(self, record):
        """Write a single raw AIS event.
        
        Args:
            record: Dict with parsed record data
        """
        if not self._header_written:
            self.write_header()
        
        # Extract and preserve raw values
        row = {
            "_time": record.get("_time", ""),
            "_measurement": record.get("_measurement", ""),
            "_field": record.get("_field", ""),
            "_value": record.get("_value", ""),
            "context": record.get("context", ""),
            "source": record.get("source", ""),
        }
        
        self.writer.writerow(row)
        self.row_count += 1
    
    def close(self):
        """Close file and atomically rename to final location."""
        self.temp_file.flush()
        self.temp_file.close()
        
        # Atomic rename
        os.replace(self.temp_path, self.output_path)
        return self.output_path
    
    def abort(self):
        """Close file without renaming (failure cleanup)."""
        self.temp_file.close()
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)
    
    def get_row_count(self):
        """Return number of rows written."""
        return self.row_count

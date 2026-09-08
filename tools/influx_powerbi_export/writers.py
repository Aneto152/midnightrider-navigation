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

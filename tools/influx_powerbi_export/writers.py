"""
USB CSV output writers for Midnight Rider and AIS datasets.
"""
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

class CSVWriter:
    """Write CSV output to USB with proper quoting and escaping."""
    
    def __init__(self, output_path):
        # Convert string to Path if needed
        self.output_path = Path(output_path) if isinstance(output_path, str) else output_path
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
    
    def __init__(self, manifest_path):
        # Convert string to Path if needed
        self.manifest_path = Path(manifest_path) if isinstance(manifest_path, str) else manifest_path
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
    """Write raw AIS events to CSV without aggregation (same-filesystem atomic output)."""
    
    COLUMNS = ["_time", "_measurement", "_field", "_value", "context", "source"]
    
    def __init__(self, output_path):
        """Initialize writer.
        
        Args:
            output_path: Final output file path (on target filesystem)
        """
        self.output_path = Path(output_path)
        
        # Ensure parent directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file in SAME DIRECTORY as final output
        # This ensures os.replace() works atomically (same filesystem)
        output_name = self.output_path.name
        temp_prefix = f".{output_name}."
        temp_suffix = ".tmp"
        
        try:
            # Create temp file in same directory as final output
            self.temp_fd, self.temp_path = tempfile.mkstemp(
                prefix=temp_prefix,
                suffix=temp_suffix,
                dir=str(self.output_path.parent)
            )
            
            self.temp_file = os.fdopen(self.temp_fd, 'w', newline='', encoding='utf-8')
            self.writer = csv.DictWriter(self.temp_file, fieldnames=self.COLUMNS)
            self.row_count = 0
            self._header_written = False
            self._closed = False
            
        except Exception as e:
            raise RuntimeError(f"Failed to create temporary file in {self.output_path.parent}: {e}")
    
    def write_header(self):
        """Write CSV header once."""
        if not self._header_written and not self._closed:
            self.writer.writeheader()
            self._header_written = True
    
    def write_row(self, record):
        """Write a single raw AIS event.
        
        Args:
            record: Dict with parsed record data
        """
        if self._closed:
            raise RuntimeError("Cannot write to closed AIS writer")
        
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
        """Close file and atomically rename to final location (same filesystem only)."""
        if self._closed:
            return self.output_path
        
        try:
            # Flush file to disk
            self.temp_file.flush()
            
            # Sync to disk for atomicity
            os.fsync(self.temp_fd)
            
            # Close file
            self.temp_file.close()
            self._closed = True
            
            # Verify same filesystem
            try:
                temp_stat = os.stat(self.temp_path)
                output_parent_stat = os.stat(self.output_path.parent)
                
                temp_device = temp_stat.st_dev
                output_device = output_parent_stat.st_dev
                
                if temp_device != output_device:
                    raise OSError(
                        f"Cross-device link: temp on device {temp_device}, "
                        f"output on device {output_device}"
                    )
            except OSError as e:
                # Device mismatch - clean up temp file
                if os.path.exists(self.temp_path):
                    os.remove(self.temp_path)
                raise RuntimeError(f"Cannot write across filesystems: {e}")
            
            # Atomic rename (same filesystem only)
            os.replace(self.temp_path, self.output_path)
            
            return self.output_path
        
        except Exception as e:
            # Cleanup on failure
            self.abort()
            raise
    
    def abort(self):
        """Close file without renaming (failure cleanup)."""
        if not self._closed:
            try:
                self.temp_file.close()
            except:
                pass
            
            self._closed = True
        
        # Remove temporary file only
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except:
                pass
    
    def get_row_count(self):
        """Return number of rows written."""
        return self.row_count

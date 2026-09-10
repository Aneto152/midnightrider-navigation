"""
Tests for same-filesystem atomic output finalization.
"""
import pytest
import os
import tempfile
from pathlib import Path
from tools.influx_powerbi_export.writers import RawAISEventWriter


class TestSameFilesystemAtomicity:
    """Test atomic file finalization on same filesystem."""
    
    def test_temp_file_in_output_directory(self):
        """Temporary file created in same directory as final output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.csv")
            writer = RawAISEventWriter(output_path)
            
            # Verify temp file is in same directory
            temp_parent = os.path.dirname(writer.temp_path)
            output_parent = os.path.dirname(output_path)
            
            assert temp_parent == output_parent
            
            writer.abort()
    
    def test_same_device_number(self):
        """Temp and output have same device number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.csv")
            writer = RawAISEventWriter(output_path)
            
            temp_stat = os.stat(writer.temp_path)
            output_parent_stat = os.stat(os.path.dirname(output_path))
            
            assert temp_stat.st_dev == output_parent_stat.st_dev
            
            writer.abort()
    
    def test_os_replace_succeeds(self):
        """os.replace() succeeds on same filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.csv")
            writer = RawAISEventWriter(output_path)
            
            writer.write_row({"_time": "2026-09-04T16:00:00Z", "_measurement": "test",
                             "_field": "value", "_value": "1", "context": "test", "source": "test"})
            
            writer.close()
            
            assert os.path.exists(output_path)
            assert not os.path.exists(writer.temp_path)
    
    def test_failed_cleanup_removes_temp_only(self):
        """Failed writer removes only temporary file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.csv")
            writer = RawAISEventWriter(output_path)
            
            temp_path = writer.temp_path
            
            writer.abort()
            
            assert not os.path.exists(temp_path)
            assert not os.path.exists(output_path)
    
    def test_successful_close_creates_final_file(self):
        """Successful close creates final AIS file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "AIS_EVENTS_RAW.csv")
            writer = RawAISEventWriter(output_path)
            
            writer.write_row({"_time": "2026-09-04T16:00:00Z", "_measurement": "ais",
                             "_field": "mmsi", "_value": "123456", "context": "ais", "source": "ais"})
            
            writer.close()
            
            assert os.path.exists(output_path)
            with open(output_path, "r") as f:
                lines = f.readlines()
            assert len(lines) == 2  # header + 1 row
    
    def test_no_partial_file_on_success(self):
        """No partial output file remains after successful completion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_output.csv")
            writer = RawAISEventWriter(output_path)
            
            writer.write_row({"_time": "2026-09-04T16:00:00Z", "_measurement": "test",
                             "_field": "value", "_value": "1", "context": "test", "source": "test"})
            
            writer.close()
            
            # Count files in directory
            files = os.listdir(tmpdir)
            assert len(files) == 1
            assert files[0] == "test_output.csv"

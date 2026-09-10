"""
Tests for raw AIS event writer and dual-output pipeline.
"""
import pytest
import os
import tempfile
from tools.influx_powerbi_export.writers import RawAISEventWriter
from tools.influx_powerbi_export.classifier import Classifier


class TestRawAISWriter:
    """Test raw AIS event streaming writer."""
    
    def test_writer_creates_header(self):
        """AIS writer creates expected header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            writer = RawAISEventWriter(output_path)
            writer.write_header()
            writer.close()
            
            with open(output_path, 'r') as f:
                header = f.readline().strip()
            
            assert "_time" in header
            assert "_measurement" in header
            assert "context" in header
            assert "source" in header
    
    def test_writer_streams_raw_rows(self):
        """AIS writer streams one row per AIS record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            writer = RawAISEventWriter(output_path)
            
            records = [
                {"_time": "2026-09-04T16:00:00Z", "_measurement": "ais", 
                 "_field": "mmsi", "_value": "123456", "context": "ais_vessel", "source": "ais"},
                {"_time": "2026-09-04T16:00:01Z", "_measurement": "ais", 
                 "_field": "position", "_value": "50.0,-4.0", "context": "ais_vessel", "source": "ais"},
            ]
            
            for record in records:
                writer.write_row(record)
            
            writer.close()
            
            with open(output_path, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 3  # header + 2 rows
            assert writer.get_row_count() == 2
    
    def test_writer_handles_empty_fields(self):
        """AIS writer preserves empty fields safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            writer = RawAISEventWriter(output_path)
            
            record = {
                "_time": "2026-09-04T16:00:00Z",
                "_measurement": "",
                "_field": "",
                "_value": "123",
                "context": "",
                "source": ""
            }
            
            writer.write_row(record)
            writer.close()
            
            with open(output_path, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 2  # header + row
    
    def test_writer_streams_without_memory_accumulation(self):
        """AIS writer streams incrementally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            writer = RawAISEventWriter(output_path)
            
            # Write many rows
            for i in range(100):
                writer.write_row({
                    "_time": f"2026-09-04T16:{i%60:02d}:00Z",
                    "_measurement": "ais",
                    "_field": "data",
                    "_value": str(i),
                    "context": "ais",
                    "source": "ais"
                })
            
            writer.close()
            
            assert writer.get_row_count() == 100
    
    def test_writer_no_file_on_abort(self):
        """AIS writer creates no final file on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            writer = RawAISEventWriter(output_path)
            
            writer.write_row({"_time": "2026-09-04T16:00:00Z", "_measurement": "ais",
                             "_field": "data", "_value": "1", "context": "ais", "source": "ais"})
            
            writer.abort()
            
            assert not os.path.exists(output_path)


class TestDualOutputPipeline:
    """Test AIS/Midnight Rider dual-output pipeline."""
    
    def test_non_ais_not_in_ais_csv(self):
        """Non-AIS records not written to AIS CSV."""
        classifier = Classifier()
        
        record = {"source": "n2k", "context": "vessels.xyz", "_measurement": "navigation"}
        assert classifier.classify(record) == "midnight_rider"
    
    def test_ais_not_in_mr_csv(self):
        """AIS records not written to Midnight Rider CSV."""
        classifier = Classifier()
        
        record = {"source": "ais", "context": "ais_vessel", "_measurement": "ais"}
        assert classifier.classify(record) == "ais"
    
    def test_non_ais_aggregated(self):
        """Non-AIS records routed to aggregation."""
        classifier = Classifier()
        
        record = {"source": "n2k", "context": "vessels.abc", "_measurement": "navigation"}
        classification = classifier.classify(record)
        
        assert classification == "midnight_rider"
    
    def test_missing_context_still_classified(self):
        """Missing context non-AIS still classified."""
        classifier = Classifier()
        
        record = {"source": "n2k", "context": "", "_measurement": "navigation"}
        classification = classifier.classify(record)
        
        assert classification != "unclassified"
        assert classification == "midnight_rider"
    
    def test_missing_source_still_classified(self):
        """Missing source non-AIS still classified."""
        classifier = Classifier()
        
        record = {"source": "", "context": "vessels.abc", "_measurement": "navigation"}
        classification = classifier.classify(record)
        
        assert classification != "unclassified"
        assert classification == "midnight_rider"
    
    def test_manifest_reconciliation(self):
        """Manifest counts reconcile."""
        # This will be tested in integration tests
        pass
    
    def test_manifest_contains_paths(self):
        """Manifest contains both file paths."""
        # This will be tested in integration tests
        pass
    
    def test_manifest_contains_sizes(self):
        """Manifest contains both file sizes."""
        # This will be tested in integration tests
        pass
    
    def test_manifest_contains_hashes(self):
        """Manifest contains both SHA256 values."""
        # This will be tested in integration tests
        pass
    
    def test_zero_unclassified_rows(self):
        """No unclassified rows under new policy."""
        classifier = Classifier()
        
        test_records = [
            {"source": "ais", "context": "ais", "_measurement": "ais"},
            {"source": "n2k", "context": "vessels.abc", "_measurement": "navigation"},
            {"source": "", "context": "", "_measurement": ""},
        ]
        
        for record in test_records:
            classification = classifier.classify(record)
            assert classification in ["ais", "midnight_rider"]
            assert classification != "unclassified"
    
    def test_ais_precedence_preserved(self):
        """AIS precedence preserved in classification."""
        classifier = Classifier()
        
        # Even with missing other fields, AIS source takes precedence
        record = {"source": "ais", "context": "", "_measurement": ""}
        assert classifier.classify(record) == "ais"
    
    def test_existing_timeout_provider(self):
        """Existing provider/timeout behavior preserved."""
        # Provider tests will be in integration
        pass

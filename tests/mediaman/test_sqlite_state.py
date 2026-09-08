"""Tests for SQLite-backed delivery state."""

import unittest
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mediaman.sqlite_state import SQLiteStateStore


class TestSQLiteStateStore(unittest.TestCase):
    """Test SQLite delivery state store."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = f"{self.temp_dir}/test.sqlite3"
        self.store = SQLiteStateStore(self.db_path)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_schema_creation(self):
        """Schema must be created on init."""
        self.assertTrue(Path(self.db_path).exists())
    
    def test_pending_reservation(self):
        """First reservation must succeed."""
        result = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertTrue(result)
    
    def test_duplicate_pending_rejected(self):
        """Duplicate reservation must be rejected."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        result = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertFalse(result)
    
    def test_pending_to_sending(self):
        """PENDING → SENDING transition."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        state = self.store.get_state("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertEqual(state, "SENDING")
    
    def test_sending_to_sent(self):
        """SENDING → SENT transition."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sent("race1", "2026-08-26T19:00:00Z", "-123456789", "msg123")
        state = self.store.get_state("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertEqual(state, "SENT")
    
    def test_sending_to_failed(self):
        """SENDING → FAILED transition."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_failed("race1", "2026-08-26T19:00:00Z", "-123456789", "Network error")
        state = self.store.get_state("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertEqual(state, "FAILED")
    
    def test_sent_not_retryable(self):
        """SENT must never be retryable."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sent("race1", "2026-08-26T19:00:00Z", "-123456789")
        result = self.store.can_retry("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertFalse(result)
    
    def test_failed_retryable(self):
        """FAILED must be retryable."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_failed("race1", "2026-08-26T19:00:00Z", "-123456789", "Error")
        result = self.store.can_retry("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertTrue(result)
    
    def test_recent_sending_not_retryable(self):
        """Recent SENDING must not be retryable."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        result = self.store.can_retry("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertFalse(result)
    
    def test_stale_sending_retryable(self):
        """Stale SENDING must be retryable."""
        import sqlite3
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_sending("race1", "2026-08-26T19:00:00Z", "-123456789")
        
        # Manually set updated_at to stale
        conn = sqlite3.connect(self.db_path)
        old_time = int(time.time()) - (3600 + 60)  # 1+ hours ago
        conn.execute(
            "UPDATE deliveries SET updated_at=? WHERE race_id=?",
            (old_time, "race1")
        )
        conn.commit()
        conn.close()
        
        result = self.store.can_retry("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertTrue(result)
    
    def test_different_race_ids(self):
        """Different race IDs must not conflict."""
        r1 = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        r2 = self.store.record_pending("race2", "2026-08-26T19:00:00Z", "-123456789")
        self.assertTrue(r1)
        self.assertTrue(r2)
    
    def test_different_cycle_ids(self):
        """Different cycle IDs must not conflict."""
        r1 = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        r2 = self.store.record_pending("race1", "2026-08-26T19:15:00Z", "-123456789")
        self.assertTrue(r1)
        self.assertTrue(r2)
    
    def test_different_target_ids(self):
        """Different target IDs must not conflict."""
        r1 = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        r2 = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-987654321")
        self.assertTrue(r1)
        self.assertTrue(r2)
    
    def test_get_stats(self):
        """Statistics must be returned correctly."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.record_pending("race2", "2026-08-26T19:00:00Z", "-123456789")
        
        stats = self.store.get_stats()
        self.assertEqual(stats["total_records"], 2)
        self.assertEqual(stats["states"].get("PENDING"), 2)
    
    def test_clear_for_testing(self):
        """clear_for_testing must remove all data."""
        self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.store.clear_for_testing()
        
        result = self.store.record_pending("race1", "2026-08-26T19:00:00Z", "-123456789")
        self.assertTrue(result)  # Should succeed again


if __name__ == '__main__':
    unittest.main()

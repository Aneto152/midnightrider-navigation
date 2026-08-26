"""Tests for idempotency tracking."""

import unittest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mediaman.idempotency import IdempotencyKey, IdempotencyStore


class TestIdempotencyKey(unittest.TestCase):
    """Test idempotency key generation."""
    
    def test_key_deterministic(self):
        """Same inputs must produce same hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
        key2 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
        
        self.assertEqual(key1.hash(), key2.hash())
    
    def test_different_race_id_different_hash(self):
        """Different race_id must produce different hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
        key2 = IdempotencyKey("race2", "2026-08-26T18:00:00", "-123456789")
        
        self.assertNotEqual(key1.hash(), key2.hash())
    
    def test_different_cycle_different_hash(self):
        """Different cycle_timestamp must produce different hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
        key2 = IdempotencyKey("race1", "2026-08-26T18:15:00", "-123456789")
        
        self.assertNotEqual(key1.hash(), key2.hash())
    
    def test_different_chat_id_different_hash(self):
        """Different chat_id must produce different hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
        key2 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-987654321")
        
        self.assertNotEqual(key1.hash(), key2.hash())


class TestIdempotencyStore(unittest.TestCase):
    """Test idempotency state store."""
    
    def test_first_send_allowed(self):
        """First send of a cycle must be allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            
            self.assertTrue(store.check_and_record(key))
    
    def test_duplicate_send_blocked(self):
        """Duplicate send of same cycle must be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            
            # First send
            self.assertTrue(store.check_and_record(key))
            # Duplicate send
            self.assertFalse(store.check_and_record(key))
    
    def test_different_cycle_allowed(self):
        """Different cycle of same race must be allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key1 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            key2 = IdempotencyKey("race1", "2026-08-26T18:15:00", "-123456789")
            
            self.assertTrue(store.check_and_record(key1))
            self.assertTrue(store.check_and_record(key2))
    
    def test_different_race_allowed(self):
        """Different race same time must be allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key1 = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            key2 = IdempotencyKey("race2", "2026-08-26T18:00:00", "-123456789")
            
            self.assertTrue(store.check_and_record(key1))
            self.assertTrue(store.check_and_record(key2))
    
    def test_state_persists(self):
        """State must persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First store instance
            store1 = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            self.assertTrue(store1.check_and_record(key))
            
            # Second store instance (reload from disk)
            store2 = IdempotencyStore(tmpdir)
            self.assertFalse(store2.check_and_record(key))
    
    def test_clear_for_testing(self):
        """clear_for_testing must remove all state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            
            self.assertTrue(store.check_and_record(key))
            self.assertFalse(store.check_and_record(key))
            
            store.clear_for_testing()
            self.assertTrue(store.check_and_record(key))
    
    def test_get_stats(self):
        """get_stats must return store information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T18:00:00", "-123456789")
            store.check_and_record(key)
            
            stats = store.get_stats()
            self.assertIn("total_records", stats)
            self.assertEqual(stats["total_records"], 1)
            self.assertIn("state_file", stats)


if __name__ == '__main__':
    unittest.main()

"""Tests for idempotency tracking with explicit delivery states."""

import unittest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mediaman.idempotency import (
    IdempotencyKey, IdempotencyStore, normalize_to_15min_bucket,
    DeliveryRecord
)
from datetime import datetime, timezone


class TestIdempotencyKey(unittest.TestCase):
    """Test idempotency key generation."""
    
    def test_key_deterministic(self):
        """Same inputs must produce same hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
        key2 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
        
        self.assertEqual(key1.hash(), key2.hash())
    
    def test_different_race_id_different_hash(self):
        """Different race_id must produce different hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
        key2 = IdempotencyKey("race2", "2026-08-26T19:00:00Z", "-123456789")
        
        self.assertNotEqual(key1.hash(), key2.hash())
    
    def test_different_cycle_different_hash(self):
        """Different cycle_timestamp must produce different hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
        key2 = IdempotencyKey("race1", "2026-08-26T19:15:00Z", "-123456789")
        
        self.assertNotEqual(key1.hash(), key2.hash())
    
    def test_different_chat_id_different_hash(self):
        """Different chat_id must produce different hash."""
        key1 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
        key2 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-987654321")
        
        self.assertNotEqual(key1.hash(), key2.hash())


class TestNormalize15minBucket(unittest.TestCase):
    """Test 15-minute cycle normalization."""
    
    def test_same_bucket(self):
        """Times within same 15-min bucket must normalize to same value."""
        dt1 = datetime(2026, 8, 26, 19, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 8, 26, 19, 7, 30, tzinfo=timezone.utc)
        dt3 = datetime(2026, 8, 26, 19, 14, 59, tzinfo=timezone.utc)
        
        norm1 = normalize_to_15min_bucket(dt1)
        norm2 = normalize_to_15min_bucket(dt2)
        norm3 = normalize_to_15min_bucket(dt3)
        
        self.assertEqual(norm1, norm2)
        self.assertEqual(norm2, norm3)
        self.assertIn("19:00:00", norm1)
    
    def test_different_bucket(self):
        """Times in different 15-min buckets must normalize differently."""
        dt1 = datetime(2026, 8, 26, 19, 14, 59, tzinfo=timezone.utc)
        dt2 = datetime(2026, 8, 26, 19, 15, 0, tzinfo=timezone.utc)
        
        norm1 = normalize_to_15min_bucket(dt1)
        norm2 = normalize_to_15min_bucket(dt2)
        
        self.assertNotEqual(norm1, norm2)
        self.assertIn("19:00:00", norm1)
        self.assertIn("19:15:00", norm2)


class TestIdempotencyStore(unittest.TestCase):
    """Test idempotency state store with explicit delivery states."""
    
    def test_first_send_pending(self):
        """First cycle must be recorded as PENDING."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            is_new = store.record_pending(key)
            self.assertTrue(is_new)
            self.assertEqual(store.get_state(key), DeliveryRecord.PENDING)
    
    def test_duplicate_pending_rejected(self):
        """Duplicate cycle in PENDING state must be rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            # First record
            is_new1 = store.record_pending(key)
            self.assertTrue(is_new1)
            # Duplicate record
            is_new2 = store.record_pending(key)
            self.assertFalse(is_new2)
    
    def test_send_state_transitions(self):
        """State transitions: PENDING → SENDING → SENT."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            # Start PENDING
            store.record_pending(key)
            self.assertEqual(store.get_state(key), DeliveryRecord.PENDING)
            
            # Move to SENDING
            store.record_sending(key)
            self.assertEqual(store.get_state(key), DeliveryRecord.SENDING)
            
            # Mark SENT
            store.record_sent(key)
            self.assertEqual(store.get_state(key), DeliveryRecord.SENT)
    
    def test_failed_delivery_retryable(self):
        """FAILED delivery must be retryable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            store.record_pending(key)
            store.record_sending(key)
            store.record_failed(key, "NETWORK_ERROR")
            
            self.assertEqual(store.get_state(key), DeliveryRecord.FAILED)
            self.assertTrue(store.can_retry(key))
    
    def test_sent_delivery_not_retryable(self):
        """SENT delivery must not be retried."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            store.record_pending(key)
            store.record_sending(key)
            store.record_sent(key)
            
            self.assertEqual(store.get_state(key), DeliveryRecord.SENT)
            self.assertFalse(store.can_retry(key))
    
    def test_stale_sending_recovery(self):
        """Stale SENDING records must be recoverable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            store.record_pending(key)
            store.record_sending(key)
            
            # Process restart - check if retryable
            self.assertTrue(store.can_retry(key))
            
            # Can transition again
            store.record_sending(key)
            self.assertEqual(store.get_state(key), DeliveryRecord.SENDING)
    
    def test_state_persists(self):
        """State must persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First store instance
            store1 = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            store1.record_pending(key)
            store1.record_sending(key)
            store1.record_sent(key)
            
            # Second store instance (reload from disk)
            store2 = IdempotencyStore(tmpdir)
            self.assertEqual(store2.get_state(key), DeliveryRecord.SENT)
            self.assertFalse(store2.can_retry(key))
    
    def test_clear_for_testing(self):
        """clear_for_testing must remove all state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            
            store.record_pending(key)
            self.assertFalse(store.record_pending(key))
            
            store.clear_for_testing()
            self.assertTrue(store.record_pending(key))
    
    def test_get_stats(self):
        """get_stats must return store information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IdempotencyStore(tmpdir)
            key1 = IdempotencyKey("race1", "2026-08-26T19:00:00Z", "-123456789")
            key2 = IdempotencyKey("race1", "2026-08-26T19:15:00Z", "-123456789")
            
            store.record_pending(key1)
            store.record_pending(key2)
            store.record_sent(key1)
            
            stats = store.get_stats()
            self.assertEqual(stats["total_records"], 2)
            self.assertIn("state_file", stats)
            self.assertEqual(stats["states"].get("PENDING"), 1)
            self.assertEqual(stats["states"].get("SENT"), 1)


if __name__ == '__main__':
    unittest.main()

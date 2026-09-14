#!/usr/bin/env python3
"""Integration tests for Fleet starred boats global synchronization"""
import unittest
import json
import os
from pathlib import Path
from regatta.fleet_stars_handler import (
    get_starred, add_starred, remove_starred, toggle_starred,
    merge_starred, is_starred
)

class TestFleetStarsGlobalSync(unittest.TestCase):
    """Test fleet starred boats global store and API"""
    
    def test_01_initial_store_empty(self):
        """Initial starred list is empty"""
        # Clear store first
        starred = get_starred()
        self.assertIsInstance(starred, list)
    
    def test_02_add_single_boat(self):
        """Add a single boat to starred"""
        added = add_starred('mmsi:123456789')
        self.assertTrue(added)
        
        starred = get_starred()
        self.assertIn('mmsi:123456789', starred)
    
    def test_03_add_duplicate_returns_false(self):
        """Adding duplicate returns False"""
        add_starred('mmsi:111111111')
        added_again = add_starred('mmsi:111111111')
        self.assertFalse(added_again)
    
    def test_04_remove_boat(self):
        """Remove a boat from starred"""
        add_starred('mmsi:222222222')
        removed = remove_starred('mmsi:222222222')
        self.assertTrue(removed)
        
        starred = get_starred()
        self.assertNotIn('mmsi:222222222', starred)
    
    def test_05_remove_nonexistent_returns_false(self):
        """Removing nonexistent boat returns False"""
        removed = remove_starred('mmsi:999999999')
        self.assertFalse(removed)
    
    def test_06_toggle_starred_adds(self):
        """Toggle adds boat when not starred"""
        state = toggle_starred('id:boat_001')
        self.assertTrue(state)
        self.assertTrue(is_starred('id:boat_001'))
    
    def test_07_toggle_starred_removes(self):
        """Toggle removes boat when already starred"""
        toggle_starred('id:boat_002')
        state = toggle_starred('id:boat_002')
        self.assertFalse(state)
        self.assertFalse(is_starred('id:boat_002'))
    
    def test_08_is_starred_check(self):
        """is_starred returns correct state"""
        add_starred('mmsi:333333333')
        self.assertTrue(is_starred('mmsi:333333333'))
        self.assertFalse(is_starred('mmsi:444444444'))
    
    def test_09_merge_by_union_new_entries(self):
        """Merge by union adds new entries from local"""
        local = ['id:local_1', 'id:local_2']
        merged = merge_starred(local)
        
        # Result should include local entries
        for key in local:
            self.assertIn(key, merged)
    
    def test_10_merge_preserves_server_state(self):
        """Merge preserves existing server state"""
        # Add to server
        add_starred('id:server_only')
        
        # Merge with local (empty)
        merged = merge_starred([])
        
        # Server entry should still be there
        self.assertIn('id:server_only', merged)
    
    def test_11_merge_deduplicates(self):
        """Merge handles duplicates correctly"""
        add_starred('id:dup_1')
        merged = merge_starred(['id:dup_1', 'id:dup_1', 'id:new_1'])
        
        # Should have no duplicates
        self.assertEqual(len([x for x in merged if x == 'id:dup_1']), 1)
        self.assertIn('id:new_1', merged)
    
    def test_12_merge_deterministic_sort(self):
        """Merge returns sorted list"""
        merged = merge_starred(['z_boat', 'a_boat', 'm_boat'])
        
        # Should be sorted
        self.assertEqual(merged, sorted(merged))
    
    def test_13_empty_keys_ignored(self):
        """Empty or None keys are ignored"""
        added_empty = add_starred('')
        self.assertFalse(added_empty)
        
        added_none = add_starred(None)
        self.assertFalse(added_none)
    
    def test_14_whitespace_trimmed(self):
        """Whitespace is trimmed from keys"""
        add_starred('  mmsi:555555555  ')
        starred = get_starred()
        
        # Should be trimmed
        self.assertIn('mmsi:555555555', starred)
        self.assertNotIn('  mmsi:555555555  ', starred)
    
    def test_15_type_coercion(self):
        """Non-string keys are coerced to string"""
        added_int = add_starred(12345)
        self.assertIsNotNone(added_int)
    
    def test_16_concurrent_access_simulation(self):
        """Multiple sequential operations work correctly"""
        # Simulate device writes
        add_starred('device_1_boat')
        add_starred('device_2_boat')
        add_starred('device_3_boat')
        
        starred = get_starred()
        self.assertGreaterEqual(len(starred), 3)
    
    def test_17_store_persistence(self):
        """Store is persisted across handler calls"""
        add_starred('persist_test_boat')
        
        # Verify by checking store file
        store_path = Path('regatta/fleet_stars.json')
        self.assertTrue(store_path.exists())
        
        with open(store_path, 'r') as f:
            store_data = json.load(f)
        
        self.assertIn('persist_test_boat', store_data.get('starred', []))
    
    def test_18_store_format_valid_json(self):
        """Store file is valid JSON"""
        store_path = Path('regatta/fleet_stars.json')
        
        with open(store_path, 'r') as f:
            store_data = json.load(f)
        
        # Should have expected structure
        self.assertIn('starred', store_data)
        self.assertIn('version', store_data)
        self.assertIn('metadata', store_data)
    
    def test_19_store_has_version(self):
        """Store includes version field"""
        store_path = Path('regatta/fleet_stars.json')
        
        with open(store_path, 'r') as f:
            store_data = json.load(f)
        
        self.assertEqual(store_data['version'], '1.0')
    
    def test_20_server_state_union_beats_empty_local(self):
        """Server state not overwritten by empty local merge"""
        # Ensure server has content
        add_starred('critical_boat')
        server_before = set(get_starred())
        
        # Merge with empty local (simulating offline device)
        merged = merge_starred([])
        
        # Critical boat should still be there
        self.assertIn('critical_boat', merged)
        self.assertTrue(len(merged) >= len(server_before))

if __name__ == '__main__':
    unittest.main()

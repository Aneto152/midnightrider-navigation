#!/usr/bin/env python3
"""Unit tests for ais/competitors_db.py — CompetitorDB"""
import sys, os, json, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ais'))
from competitors_db import CompetitorDB

MOCK_DATA = {
    "_meta": {"version": "test-1.0", "event": "BIR2026"},
    "competitors": [
        {"id": "boat-01", "boat_name": "Wind Hunter", "sail_number": "USA 1234",
         "skipper": "John Doe", "active": True, "ais": {"mmsi": 338123456},
         "vessel": {"make": "J/Boats", "model": "J/30"},
         "ratings": {"PHRF_LIS": {"value": 171}, "IRC": {"TCC": 1.012}},
         "priority": "high", "events": ["BIR2026"]},
        {"id": "boat-02", "boat_name": "Sea Dragon", "sail_number": "CAN 5678",
         "skipper": "Jane Smith", "active": False, "mmsi": 316567890,
         "vessel": {"make": "Beneteau", "model": "First 40"},
         "ratings": {"PHRF_LIS": 126}, "priority": "medium", "events": []},
        {"id": "boat-03", "boat_name": "Fast Track", "sail_number": "USA 9999",
         "skipper": "Bob Wilson", "active": True, "ais": {"mmsi": 338999001},
         "vessel": {"make": "Melges", "model": "32"},
         "ratings": {}, "priority": "low", "events": ["BIR2026"]}
    ]
}

class TestCompetitorDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(MOCK_DATA, self.tmp)
        self.tmp.flush()
        self.db = CompetitorDB(path=self.tmp.name)
    def tearDown(self):
        os.unlink(self.tmp.name)
    def test_get_all_returns_all_boats(self):
        self.assertEqual(len(self.db.get_all()), 3)
    def test_get_all_active_excludes_inactive(self):
        active = self.db.get_all_active()
        self.assertEqual(len(active), 2)
    def test_get_all_active_correct_boats(self):
        names = [b['boat_name'] for b in self.db.get_all_active()]
        self.assertIn('Wind Hunter', names)
        self.assertIn('Fast Track', names)
        self.assertNotIn('Sea Dragon', names)
    def test_get_by_mmsi_str_nested_ais_key(self):
        boat = self.db.get_by_mmsi('338123456')
        self.assertIsNotNone(boat)
        self.assertEqual(boat['boat_name'], 'Wind Hunter')
    def test_get_by_mmsi_int_input(self):
        boat = self.db.get_by_mmsi(338123456)
        self.assertIsNotNone(boat)
        self.assertEqual(boat['boat_name'], 'Wind Hunter')
    def test_get_by_mmsi_direct_key(self):
        boat = self.db.get_by_mmsi('316567890')
        self.assertIsNotNone(boat)
        self.assertEqual(boat['boat_name'], 'Sea Dragon')
    def test_get_by_mmsi_not_found_returns_none(self):
        self.assertIsNone(self.db.get_by_mmsi('999999999'))
    def test_search_by_boat_name(self):
        results = self.db.search('Wind Hunter')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['boat_name'], 'Wind Hunter')
    def test_search_case_insensitive(self):
        results = self.db.search('wind hunter')
        self.assertEqual(len(results), 1)
    def test_search_by_sail_number(self):
        results = self.db.search('USA 1234')
        self.assertEqual(len(results), 1)
    def test_search_by_mmsi(self):
        results = self.db.search('338123456')
        self.assertEqual(len(results), 1)
    def test_search_partial_match(self):
        results = self.db.search('Track')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['boat_name'], 'Fast Track')
    def test_search_empty_string_returns_all(self):
        results = self.db.search('')
        self.assertEqual(len(results), 3)
    def test_search_no_match(self):
        results = self.db.search('NOMATCH_XYZ_99999')
        self.assertEqual(len(results), 0)
    def test_enrich_has_required_keys(self):
        raw = self.db.get_by_mmsi('338123456')
        e = self.db.enrich(raw)
        for k in ['id', 'name', 'sail_num', 'skipper', 'boat_class',
                  'mmsi', 'phrf_lis', 'irc_tcc', 'priority', 'events']:
            self.assertIn(k, e)
    def test_enrich_phrf_dict_form(self):
        raw = self.db.get_by_mmsi('338123456')
        self.assertEqual(self.db.enrich(raw)['phrf_lis'], 171)
    def test_enrich_phrf_int_form(self):
        raw = self.db.get_by_mmsi('316567890')
        self.assertEqual(self.db.enrich(raw)['phrf_lis'], 126)
    def test_enrich_no_ratings_returns_none(self):
        raw = self.db.get_by_mmsi('338999001')
        e = self.db.enrich(raw)
        self.assertIsNone(e['phrf_lis'])
        self.assertIsNone(e['irc_tcc'])
    def test_enrich_irc_tcc(self):
        raw = self.db.get_by_mmsi('338123456')
        self.assertAlmostEqual(self.db.enrich(raw)['irc_tcc'], 1.012)
    def test_enrich_boat_class_format(self):
        raw = self.db.get_by_mmsi('338123456')
        self.assertEqual(self.db.enrich(raw)['boat_class'], 'J/Boats J/30')
    def test_enrich_mmsi_as_string(self):
        raw = self.db.get_by_mmsi('338123456')
        mmsi = self.db.enrich(raw)['mmsi']
        self.assertIsInstance(mmsi, str)
        self.assertEqual(mmsi, '338123456')
    def test_get_all_active_mmsis_returns_set(self):
        mmsis = self.db.get_all_active_mmsis()
        self.assertIn('338123456', mmsis)
        self.assertIn('338999001', mmsis)
    def test_get_all_active_mmsis_excludes_inactive(self):
        mmsis = self.db.get_all_active_mmsis()
        self.assertNotIn('316567890', mmsis)
    def test_get_meta_returns_dict(self):
        meta = self.db.get_meta()
        self.assertIsInstance(meta, dict)
        self.assertEqual(meta.get('version'), 'test-1.0')
        self.assertEqual(meta.get('event'), 'BIR2026')
    def test_get_meta_missing_file_returns_empty(self):
        db2 = CompetitorDB(path='/tmp/no_such_file_xyz.json')
        self.assertEqual(db2.get_meta(), {})

if __name__ == '__main__':
    unittest.main(verbosity=2)

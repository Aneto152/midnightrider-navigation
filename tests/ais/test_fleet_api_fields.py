#!/usr/bin/env python3
"""CompetitorDB.enrich() must transport the reimported fields, and keep the old ones.

Until 2026-09-14 enrich() exposed 12 keys. The lossless Excel reimport recovered
roughly 10000 values (yacht club, home port, ratings, rating history, vessel
model and length, AIS metadata, MMSI confidence, provenance) which sat in
competitors.json without ever reaching the browser. Denis asked for complete
boat information, so this contract test pins both halves:

  - LEGACY keys must never disappear: the Fleet list and the modal read them,
    and a silent rename is exactly how the 'saveStarred' defect shipped.
  - ADDED keys must be present, so a future refactor of enrich() cannot quietly
    drop the enrichment again.

field_sources and fleet_groups are intentionally absent: audit trail and
duplicated strings, not worth 379 times their weight on a phone link.
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'ais'))

from competitors_db import CompetitorDB  # noqa: E402

DB_PATH = os.path.join(ROOT, 'regatta', 'competitors.json')

LEGACY = ('id', 'active', 'name', 'sail_num', 'skipper', 'boat_class',
          'mmsi', 'phrf_lis', 'irc_tcc', 'priority', 'events', 'palmares')

ADDED = ('vessel', 'length_ft', 'race_class', 'yacht_club', 'home_port',
         'ratings', 'phrf_history', 'sail_numbers', 'racing_circles',
         'mmsi_confidence', 'mmsi_candidates', 'mmsi_review', 'mmsi_conflict',
         'ais', 'notes', 'provenance')

EXCLUDED = ('field_sources', 'fleet_groups')


class TestFleetApiFields(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(DB_PATH, encoding='utf-8') as handle:
            cls.raw = json.load(handle)
        cls.db = CompetitorDB(DB_PATH)
        cls.boats = cls.raw['competitors']

    def enriched(self, boat_id):
        boat = next(b for b in self.boats if b.get('id') == boat_id)
        return self.db.enrich(boat)

    def test_legacy_keys_never_disappear(self):
        out = self.enriched('hist-condor')
        for key in LEGACY:
            self.assertIn(key, out, 'legacy key {} dropped by enrich()'.format(key))

    def test_reimported_keys_are_transported(self):
        out = self.enriched('hist-condor')
        for key in ADDED:
            self.assertIn(key, out, 'reimported key {} not exposed'.format(key))

    def test_heavy_internal_fields_stay_server_side(self):
        out = self.enriched('hist-condor')
        for key in EXCLUDED:
            self.assertNotIn(key, out)
        self.assertNotIn('field_sources', out.get('provenance', {}))

    def test_values_actually_arrive(self):
        out = self.enriched('hist-condor')
        self.assertEqual(out['yacht_club'], 'Milford Yacht Club')
        self.assertEqual(out['home_port'], 'Milford, CT, USA')
        self.assertEqual(out['vessel'].get('model'), 'Bowman Corsair')
        self.assertEqual(out['ratings'].get('PHRF_LIS'), 126.0)
        self.assertEqual(len(out['phrf_history']), 3)
        self.assertEqual(out['mmsi_confidence'], 'High')
        self.assertEqual(out['ais'].get('observation_count'), 6204)

    def test_every_boat_survives_enrichment(self):
        for boat in self.boats:
            out = self.db.enrich(boat)
            self.assertEqual(out['id'], boat['id'])
            self.assertIsNotNone(out['name'], 'boat {} has no name'.format(boat['id']))


if __name__ == '__main__':
    unittest.main()

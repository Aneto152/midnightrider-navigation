#!/usr/bin/env python3
"""
Regression test for Fleet DB star identity fix.

Verifies that boats without MMSI have unique star identities using boat.id.
Does NOT access: InfluxDB, Docker, USB storage, Signal K, or running services.
"""

import unittest
import json
from pathlib import Path


class TestFleetDBStarIdentity(unittest.TestCase):
    """Regression tests for Fleet DB star identity fix (unique boat keys)"""

    @classmethod
    def setUpClass(cls):
        """Load competitors.json and fleet_db.html for static analysis"""
        cls.base_dir = Path(__file__).parent.parent.parent
        cls.competitors_path = cls.base_dir / 'regatta' / 'competitors.json'
        cls.fleet_db_path = cls.base_dir / 'ais' / 'fleet_db.html'
        cls.fleet_stars_path = cls.base_dir / 'ais' / 'fleet_stars.js'

    def test_actaea_no_mmsi(self):
        """Verify ACTAEA (c093) has no MMSI"""
        with open(self.competitors_path) as f:
            data = json.load(f)
        competitors = data.get('competitors', [])
        actaea = next((b for b in competitors if b.get('id') == 'c093'), None)
        self.assertIsNotNone(actaea)
        self.assertIn('ACTAEA', actaea.get('boat_name', ''))
        mmsi = actaea.get('mmsi')
        self.assertTrue(mmsi is None or str(mmsi).strip() == '')

    def test_avalanche_no_mmsi(self):
        """Verify Avalanche (c094) has no MMSI"""
        with open(self.competitors_path) as f:
            data = json.load(f)
        competitors = data.get('competitors', [])
        avalanche = next((b for b in competitors if b.get('id') == 'c094'), None)
        self.assertIsNotNone(avalanche)
        self.assertIn('Avalanche', avalanche.get('boat_name', ''))
        mmsi = avalanche.get('mmsi')
        self.assertTrue(mmsi is None or str(mmsi).strip() == '')

    def test_avatar_no_mmsi(self):
        """Verify Avatar (c095) has no MMSI"""
        with open(self.competitors_path) as f:
            data = json.load(f)
        competitors = data.get('competitors', [])
        avatar = next((b for b in competitors if b.get('id') == 'c095'), None)
        self.assertIsNotNone(avatar)
        self.assertIn('Avatar', avatar.get('boat_name', ''))
        mmsi = avatar.get('mmsi')
        self.assertTrue(mmsi is None or str(mmsi).strip() == '')

    def test_getboatstarkeyhelper_exists(self):
        """Verify getBoatStarKey() helper is defined"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('function getBoatStarKey(boat)', html)

    def test_getboatstarkeyuses_boat_id(self):
        """Verify getBoatStarKey checks boat.id as primary identity"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn("boat.id !== undefined", html)
        self.assertIn("id:${String(boat.id)}", html)

    def test_storage_key_owned_by_fleet_stars_js(self):
        """The localStorage key must be declared in exactly one place.

        Was: assert fleet_db.html contains 'fleet_db_starred_v2'. That very
        declaration was the defect. fleet_db.html declared
        `const STORAGE_KEY = 'fleet_db_starred_v2'` while fleet_stars.js
        declared `const STORAGE_KEY = 'fleet_stars_local'`. Both are global:
        the duplicate `const` threw a SyntaxError that annulled an entire
        script block and left the page without a boat list. fleet_stars.js is
        now the single owner of the key.
        """
        with open(self.fleet_db_path) as f:
            html = f.read()
        with open(self.fleet_stars_path) as f:
            js = f.read()
        self.assertIn("STORAGE_KEY = 'fleet_stars_local'", js)
        self.assertNotIn('const STORAGE_KEY', html)

    def test_filter_uses_getboatstarkey(self):
        """Verify starred filter uses getBoatStarKey()"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn("getBoatStarKey(b)", html)

    def test_star_click_adapter_receives_boat_object(self):
        """The inline handler still receives the full boat object.

        Was: assert fleet_db.html contains 'toggleFleetStar(boat, event)'.
        That was a second definition of a global already defined in
        fleet_stars.js with the incompatible signature (boatKey). The inline
        entry point is now onStarClick(boat, event), which derives the key with
        getBoatStarKey(boat) and delegates to the async toggleFleetStar(boatKey).
        """
        with open(self.fleet_db_path) as f:
            html = f.read()
        with open(self.fleet_stars_path) as f:
            js = f.read()
        self.assertIn('function onStarClick(boat, event)', html)
        self.assertIn('getBoatStarKey(boat)', html)
        self.assertIn('async function toggleFleetStar(boatKey)', js)


if __name__ == '__main__':
    unittest.main()

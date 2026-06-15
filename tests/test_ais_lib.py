#!/usr/bin/env python3
"""Unit tests for ais/ais_lib.py — AIS math library"""
import sys, os, math, time, collections, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ais'))
from ais_lib import (haversine_ll, bearing_ll, compute_twa, compute_vmg_wind,
                     compute_vmg_mark, is_gaining_ground, make_history_store,
                     record_position, compute_delta)

class TestHaversine(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(haversine_ll(40.0, -73.0, 40.0, -73.0), 0, places=2)
    def test_one_degree_latitude(self):
        d = haversine_ll(40.0, -73.0, 41.0, -73.0)
        self.assertAlmostEqual(d / 1852, 60.0, delta=0.5)
    def test_larchmont_to_block_island(self):
        d = haversine_ll(40.921, -73.751, 41.167, -71.583)
        self.assertAlmostEqual(d / 1852, 101, delta=3)
    def test_always_positive(self):
        d = haversine_ll(51.5, -0.1, 48.85, 2.35)
        self.assertGreater(d, 0)
    def test_symmetry(self):
        d1 = haversine_ll(40.0, -73.0, 41.0, -74.0)
        d2 = haversine_ll(41.0, -74.0, 40.0, -73.0)
        self.assertAlmostEqual(d1, d2, places=1)

class TestBearing(unittest.TestCase):
    def test_due_north(self):
        b = bearing_ll(40.0, -73.0, 41.0, -73.0)
        self.assertAlmostEqual(b, 0.0, delta=0.5)
    def test_due_south(self):
        b = bearing_ll(41.0, -73.0, 40.0, -73.0)
        self.assertAlmostEqual(b, 180.0, delta=0.5)
    def test_due_east(self):
        b = bearing_ll(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(b, 90.0, delta=0.5)
    def test_due_west(self):
        b = bearing_ll(0.0, 1.0, 0.0, 0.0)
        self.assertAlmostEqual(b, 270.0, delta=0.5)

class TestComputeTwa(unittest.TestCase):
    def test_head_to_wind(self):
        self.assertAlmostEqual(compute_twa(180.0, 180.0), 0.0, places=5)
    def test_starboard_tack(self):
        self.assertAlmostEqual(compute_twa(45.0, 0.0), 45.0, places=5)
    def test_port_tack(self):
        self.assertAlmostEqual(compute_twa(315.0, 0.0), -45.0, places=5)
    def test_dead_downwind(self):
        twa = compute_twa(180.0, 0.0)
        self.assertAlmostEqual(abs(twa), 180.0, places=4)
    def test_range_check(self):
        for cog in range(0, 360, 30):
            for twd in range(0, 360, 30):
                twa = compute_twa(cog, twd)
                self.assertGreaterEqual(twa, -180)
                self.assertLessEqual(twa, 180)

class TestComputeVmgWind(unittest.TestCase):
    def test_perfect_upwind(self):
        self.assertAlmostEqual(compute_vmg_wind(6.0, 0.0), 6.0, places=5)
    def test_perfect_downwind(self):
        self.assertAlmostEqual(compute_vmg_wind(6.0, 180.0), -6.0, places=4)
    def test_reaching(self):
        self.assertAlmostEqual(compute_vmg_wind(6.0, 90.0), 0.0, places=5)

class TestComputeVmgMark(unittest.TestCase):
    def test_direct_to_mark(self):
        self.assertAlmostEqual(compute_vmg_mark(6.0, 90.0, 90.0), 6.0, places=5)
    def test_perpendicular_to_mark(self):
        vmg = compute_vmg_mark(6.0, 90.0, 0.0)
        self.assertAlmostEqual(vmg, 0.0, places=4)
    def test_away_from_mark(self):
        self.assertAlmostEqual(compute_vmg_mark(6.0, 180.0, 0.0), -6.0, places=4)

class TestIsGainingGround(unittest.TestCase):
    def test_gaining_green(self):
        self.assertEqual(is_gaining_ground(5.1, 5.0), 'green')
    def test_losing_red(self):
        self.assertEqual(is_gaining_ground(4.9, 5.0), 'red')
    def test_neutral_within_threshold(self):
        self.assertEqual(is_gaining_ground(5.0, 5.0), 'neutral')
    def test_none_handling(self):
        self.assertEqual(is_gaining_ground(None, 5.0), 'neutral')
        self.assertEqual(is_gaining_ground(5.0, None), 'neutral')

if __name__ == '__main__':
    unittest.main(verbosity=2)

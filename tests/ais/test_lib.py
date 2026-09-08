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
    def test_antipodal_points(self):
        d = haversine_ll(0, 0, 0, 180)
        self.assertAlmostEqual(d / 1e6, 20.0, delta=0.5)

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
    def test_always_in_range_0_360(self):
        for (la1,lo1,la2,lo2) in [(40,-73,41,-74),(51,-0.1,48,2.3),(0,0,0,1),(-10,20,10,-20)]:
            b = bearing_ll(la1, lo1, la2, lo2)
            self.assertGreaterEqual(b, 0)
            self.assertLess(b, 360)
    def test_ne_quadrant(self):
        b = bearing_ll(40.0, -73.0, 41.0, -72.0)
        self.assertGreater(b, 0)
        self.assertLess(b, 90)

class TestComputeTwa(unittest.TestCase):
    def test_head_to_wind_twa_zero(self):
        self.assertAlmostEqual(compute_twa(180.0, 180.0), 0.0, places=5)
    def test_starboard_tack_positive(self):
        self.assertAlmostEqual(compute_twa(45.0, 0.0), 45.0, places=5)
    def test_port_tack_negative(self):
        self.assertAlmostEqual(compute_twa(315.0, 0.0), -45.0, places=5)
    def test_dead_downwind_abs_180(self):
        twa = compute_twa(180.0, 0.0)
        self.assertAlmostEqual(abs(twa), 180.0, places=4)
    def test_wrap_around_negative(self):
        self.assertAlmostEqual(compute_twa(350.0, 10.0), -20.0, places=5)
    def test_wrap_around_positive(self):
        self.assertAlmostEqual(compute_twa(10.0, 350.0), 20.0, places=5)
    def test_output_always_between_minus180_plus180(self):
        for cog in range(0, 360, 10):
            for twd in range(0, 360, 10):
                twa = compute_twa(cog, twd)
                self.assertGreaterEqual(twa, -180)
                self.assertLessEqual(twa, 180)
    def test_symmetric_port_stbd(self):
        twa_stbd = compute_twa(45.0, 0.0)
        twa_port = compute_twa(315.0, 0.0)
        self.assertAlmostEqual(abs(twa_stbd), abs(twa_port), places=5)

class TestComputeVmgWind(unittest.TestCase):
    def test_perfect_upwind_vmg_equals_sog(self):
        self.assertAlmostEqual(compute_vmg_wind(6.0, 0.0), 6.0, places=5)
    def test_perfect_downwind_vmg_negative_sog(self):
        self.assertAlmostEqual(compute_vmg_wind(6.0, 180.0), -6.0, places=4)
    def test_reaching_vmg_near_zero(self):
        self.assertAlmostEqual(compute_vmg_wind(6.0, 90.0), 0.0, places=5)
    def test_close_hauled_45deg(self):
        expected = 7.0 * math.cos(math.radians(45.0))
        self.assertAlmostEqual(compute_vmg_wind(7.0, 45.0), expected, places=5)
    def test_zero_sog(self):
        self.assertAlmostEqual(compute_vmg_wind(0.0, 30.0), 0.0, places=5)
    def test_j30_upwind_typical(self):
        vmg = compute_vmg_wind(6.5, 40.0)
        self.assertAlmostEqual(vmg, 6.5 * math.cos(math.radians(40.0)), places=5)

class TestComputeVmgMark(unittest.TestCase):
    def test_direct_to_mark_vmg_equals_sog(self):
        self.assertAlmostEqual(compute_vmg_mark(6.0, 90.0, 90.0), 6.0, places=5)
    def test_perpendicular_to_mark_vmg_zero(self):
        vmg = compute_vmg_mark(6.0, 90.0, 0.0)
        self.assertAlmostEqual(vmg, 0.0, places=4)
    def test_away_from_mark_vmg_negative(self):
        self.assertAlmostEqual(compute_vmg_mark(6.0, 180.0, 0.0), -6.0, places=4)
    def test_partial_angle(self):
        expected = 6.0 * math.cos(math.radians(30.0))
        self.assertAlmostEqual(compute_vmg_mark(6.0, 330.0, 0.0), expected, places=4)
    def test_wrap_around_bearing(self):
        expected = 5.0 * math.cos(math.radians(20.0))
        self.assertAlmostEqual(compute_vmg_mark(5.0, 10.0, 350.0), expected, places=4)

class TestIsGainingGround(unittest.TestCase):
    def test_gaining_green(self):
        self.assertEqual(is_gaining_ground(5.0, 4.9), 'green')
        self.assertEqual(is_gaining_ground(5.0, 4.0), 'green')
        self.assertEqual(is_gaining_ground(5.1, 5.0), 'green')
    def test_losing_red(self):
        self.assertEqual(is_gaining_ground(4.9, 5.0), 'red')
        self.assertEqual(is_gaining_ground(4.0, 5.0), 'red')
    def test_neutral_within_threshold(self):
        self.assertEqual(is_gaining_ground(5.0, 5.0), 'neutral')
        self.assertEqual(is_gaining_ground(5.04, 5.0), 'neutral')
        self.assertEqual(is_gaining_ground(5.0, 5.04), 'neutral')
    def test_threshold_boundary_exactly_0_05(self):
        self.assertEqual(is_gaining_ground(5.05, 5.0), 'neutral')
        self.assertEqual(is_gaining_ground(5.051, 5.0), 'green')
    def test_none_mr_is_neutral(self):
        self.assertEqual(is_gaining_ground(None, 5.0), 'neutral')
    def test_none_comp_is_neutral(self):
        self.assertEqual(is_gaining_ground(5.0, None), 'neutral')
    def test_both_none_is_neutral(self):
        self.assertEqual(is_gaining_ground(None, None), 'neutral')
    def test_negative_vmg_values(self):
        self.assertEqual(is_gaining_ground(-3.0, -3.2), 'green')
        self.assertEqual(is_gaining_ground(-3.2, -3.0), 'red')

class TestHistoryStore(unittest.TestCase):
    def test_make_history_store_is_defaultdict(self):
        h = make_history_store()
        self.assertIsInstance(h, collections.defaultdict)
    def test_new_key_creates_deque_maxlen_80(self):
        h = make_history_store()
        q = h['338123456']
        self.assertIsInstance(q, collections.deque)
        self.assertEqual(q.maxlen, 80)
    def test_delta_empty_history_returns_none(self):
        h = make_history_store()
        d1, d2, d3 = compute_delta(h, '338123456')
        self.assertIsNone(d1)
        self.assertIsNone(d2)
        self.assertIsNone(d3)
    def test_delta_single_entry_returns_none(self):
        h = make_history_store()
        record_position(h, '338123456', 1000.0, 45.0)
        d1, d2, d3 = compute_delta(h, '338123456')
        self.assertIsNone(d1)
    def test_record_position_appends(self):
        h = make_history_store()
        record_position(h, '338123456', 1000.0, 45.0)
        record_position(h, '338123456', 950.0, 48.0)
        self.assertEqual(len(h['338123456']), 2)
    def test_record_position_accepts_int_mmsi(self):
        h = make_history_store()
        record_position(h, 338123456, 1000.0, 45.0)
        self.assertEqual(len(h['338123456']), 1)
    def test_delta_closing_gap(self):
        h = make_history_store()
        mmsi = '338123456'
        h[mmsi].append((time.time() - 1860, 5000.0, 45.0))
        record_position(h, mmsi, 3000.0, 50.0)
        dd, db, age = compute_delta(h, mmsi)
        self.assertIsNotNone(dd)
        self.assertAlmostEqual(dd, -2000.0, delta=1.0)
    def test_delta_opening_gap(self):
        h = make_history_store()
        mmsi = '338999001'
        h[mmsi].append((time.time() - 1860, 2000.0, 90.0))
        record_position(h, mmsi, 5000.0, 92.0)
        dd, db, age = compute_delta(h, mmsi)
        self.assertIsNotNone(dd)
        self.assertAlmostEqual(dd, 3000.0, delta=1.0)
    def test_delta_age_returned_in_minutes(self):
        h = make_history_store()
        mmsi = '338123456'
        age_s = 1860
        h[mmsi].append((time.time() - age_s, 5000.0, 45.0))
        record_position(h, mmsi, 4000.0, 46.0)
        dd, db, age = compute_delta(h, mmsi)
        self.assertAlmostEqual(age, age_s / 60, delta=0.2)
    def test_different_mmsi_isolated(self):
        h = make_history_store()
        record_position(h, '111111111', 1000.0, 45.0)
        record_position(h, '222222222', 2000.0, 90.0)
        self.assertEqual(len(h['111111111']), 1)
        self.assertEqual(len(h['222222222']), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)

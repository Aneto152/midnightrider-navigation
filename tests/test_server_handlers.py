#!/usr/bin/env python3
"""Unit tests for ais/server_handlers.py — API handlers"""
import sys, os, math, json, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ais'))

def make_sk_fn(vessels=None, own_nav=None, wind_twd_rad=None, wind_tws_ms=None, mark_pos=None):
    def sk_fn(path):
        if path == 'vessels':
            return vessels or {}
        if path == 'vessels/self/navigation':
            return own_nav or {}
        if path == 'vessels/self/environment/wind/directionTrue':
            return {'value': wind_twd_rad} if wind_twd_rad is not None else None
        if path == 'vessels/self/environment/wind/speedTrue':
            return {'value': wind_tws_ms} if wind_tws_ms is not None else None
        for mp in ['vessels/self/navigation/courseGreatCircle/nextPoint/position',
                   'vessels/self/navigation/courseRhumbline/nextPoint/position']:
            if path == mp:
                return {'value': mark_pos} if mark_pos else None
        return None
    return sk_fn

def make_gps(lat=None, lon=None):
    return lambda: {'lat': lat, 'lon': lon}

class TestApiCompetitors(unittest.TestCase):
    def test_no_position_returns_error_key(self):
        from server_handlers import api_competitors
        sk = make_sk_fn()
        gps = make_gps(lat=None, lon=None)
        result = api_competitors(sk, gps)
        self.assertEqual(result.get('error'), 'no_position')
    def test_no_position_returns_empty_competitors(self):
        from server_handlers import api_competitors
        sk = make_sk_fn()
        gps = make_gps(lat=None, lon=None)
        result = api_competitors(sk, gps)
        self.assertEqual(result['competitors'], [])
    def test_response_has_required_top_level_keys(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(
            own_nav={'speedOverGround': {'value': 3.086}, 'courseOverGroundTrue': {'value': math.radians(45.0)}},
            wind_twd_rad=math.radians(0.0))
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        for key in ['ts', 'self', 'wind', 'mark', 'competitors']:
            self.assertIn(key, result)
    def test_self_sog_converted_to_knots(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(
            own_nav={'speedOverGround': {'value': 3.086},
                     'courseOverGroundTrue': {'value': math.radians(90.0)}})
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertAlmostEqual(result['self']['sog_kts'], 6.0, delta=0.05)
    def test_self_cog_in_degrees(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(
            own_nav={'speedOverGround': {'value': 0},
                     'courseOverGroundTrue': {'value': math.radians(135.0)}})
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertAlmostEqual(result['self']['cog'], 135.0, delta=0.5)
    def test_wind_available_when_twd_present(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(wind_twd_rad=math.radians(225.0))
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertTrue(result['wind']['available'])
        self.assertAlmostEqual(result['wind']['twd'], 225.0, delta=0.5)
    def test_wind_unavailable_when_no_twd(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(wind_twd_rad=None)
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertFalse(result['wind']['available'])
    def test_mark_available_when_position_set(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(mark_pos={'latitude': 41.0, 'longitude': -73.5})
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertTrue(result['mark']['available'])
        self.assertAlmostEqual(result['mark']['lat'], 41.0, places=5)
    def test_mark_unavailable_when_no_waypoint(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(mark_pos=None)
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertFalse(result['mark']['available'])
    def test_ts_is_integer(self):
        from server_handlers import api_competitors
        sk = make_sk_fn()
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertIsInstance(result['ts'], int)
    def test_self_twa_computed_when_wind_present(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(
            own_nav={'speedOverGround': {'value': 3.086},
                     'courseOverGroundTrue': {'value': math.radians(45.0)}},
            wind_twd_rad=math.radians(0.0))
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertAlmostEqual(result['self']['twa'], 45.0, delta=0.5)
    def test_competitor_in_radius_appears(self):
        from server_handlers import api_competitors
        vessels = {'vessels/338123456': {
            'navigation': {
                'position': {'value': {'latitude': 40.935, 'longitude': -73.75}},
                'speedOverGround': {'value': 3.086},
                'courseOverGroundTrue': {'value': math.radians(45.0)}}}}
        sk = make_sk_fn(vessels=vessels, wind_twd_rad=math.radians(0.0))
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps, radius=10.0)
        self.assertIn('competitors', result)
    def test_competitor_outside_radius_excluded(self):
        from server_handlers import api_competitors
        vessels = {'vessels/338123456': {
            'navigation': {
                'position': {'value': {'latitude': 42.0, 'longitude': -73.75}},
                'speedOverGround': {'value': 3.086},
                'courseOverGroundTrue': {'value': math.radians(45.0)}}}}
        sk = make_sk_fn(vessels=vessels)
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps, radius=5.0)
        for c in result.get('competitors', []):
            self.assertLessEqual(c['dist_nm'], 5.0)

class TestApiFleetDb(unittest.TestCase):
    def test_fleet_db_has_required_keys(self):
        from server_handlers import api_fleet_db
        result = api_fleet_db()
        for key in ['total', 'active', 'competitors']:
            self.assertIn(key, result)
    def test_fleet_db_counts_are_integers(self):
        from server_handlers import api_fleet_db
        result = api_fleet_db()
        self.assertIsInstance(result['total'], int)
        self.assertIsInstance(result['active'], int)
    def test_fleet_db_active_lte_total(self):
        from server_handlers import api_fleet_db
        result = api_fleet_db()
        self.assertLessEqual(result['active'], result['total'])
    def test_fleet_db_competitors_is_list(self):
        from server_handlers import api_fleet_db
        result = api_fleet_db()
        self.assertIsInstance(result['competitors'], list)
    def test_fleet_db_competitor_has_ais_status(self):
        from server_handlers import api_fleet_db
        result = api_fleet_db()
        for c in result['competitors']:
            self.assertIn('ais_status', c)
            self.assertIn(c['ais_status'], ['live', 'stale', 'old', 'absent'])
    def test_fleet_db_total_matches_list_length(self):
        from server_handlers import api_fleet_db
        result = api_fleet_db()
        self.assertEqual(result['total'], len(result['competitors']))

if __name__ == '__main__':
    unittest.main(verbosity=2)

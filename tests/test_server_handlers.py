#!/usr/bin/env python3
"""Unit tests for ais/server_handlers.py — API handlers"""
import sys, os, math, json, tempfile, unittest
from unittest.mock import MagicMock
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
    def test_response_has_required_keys(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(
            own_nav={'speedOverGround': {'value': 3.086},
                     'courseOverGroundTrue': {'value': math.radians(45.0)}},
            wind_twd_rad=math.radians(0.0)
        )
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        for key in ['ts', 'self', 'wind', 'mark', 'competitors']:
            self.assertIn(key, result)
    def test_self_sog_converted_to_knots(self):
        from server_handlers import api_competitors
        sk = make_sk_fn(
            own_nav={'speedOverGround': {'value': 3.086},
                     'courseOverGroundTrue': {'value': math.radians(90.0)}}
        )
        gps = make_gps(lat=40.92, lon=-73.75)
        result = api_competitors(sk, gps)
        self.assertAlmostEqual(result['self']['sog_kts'], 6.0, delta=0.05)

class TestApiFleetDb(unittest.TestCase):
    def test_fleet_db_has_required_keys(self):
        from server_handlers import api_fleet_db
        sk = make_sk_fn()
        result = api_fleet_db(sk)
        for key in ['total', 'active', 'competitors']:
            self.assertIn(key, result)
    def test_fleet_db_counts_are_integers(self):
        from server_handlers import api_fleet_db
        sk = make_sk_fn()
        result = api_fleet_db(sk)
        self.assertIsInstance(result['total'], int)
        self.assertIsInstance(result['active'], int)
    def test_fleet_db_active_lte_total(self):
        from server_handlers import api_fleet_db
        sk = make_sk_fn()
        result = api_fleet_db(sk)
        self.assertLessEqual(result['active'], result['total'])

if __name__ == '__main__':
    unittest.main(verbosity=2)

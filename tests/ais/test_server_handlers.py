#!/usr/bin/env python3
"""Unit tests for ais/server_handlers.py — Fixed v2
Fixes: cache isolation (reset_caches), api_fleet_db(sk_fn) signature
"""
import sys,os,math,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','ais'))
import server_handlers
from server_handlers import api_competitors, api_fleet_db

def make_sk_fn(vessels=None,own_nav=None,wind_twd_rad=None,wind_tws_ms=None,mark_pos=None):
 def sk_fn(path):
  if path=='vessels': return vessels or {}
  if path=='vessels/self/navigation': return own_nav or {}
  if path=='vessels/self/environment/wind/directionTrue':
   return {'value':wind_twd_rad} if wind_twd_rad is not None else None
  if path=='vessels/self/environment/wind/speedTrue':
   return {'value':wind_tws_ms} if wind_tws_ms is not None else None
  for mp in ['vessels/self/navigation/courseGreatCircle/nextPoint/position',
   'vessels/self/navigation/courseRhumbline/nextPoint/position']:
   if path==mp: return {'value':mark_pos} if mark_pos else None
  return None
 return sk_fn

def make_gps(lat=None,lon=None):
 return lambda: {'lat':lat,'lon':lon}

def reset_caches():
 """Reset TTL caches between tests — production behavior unaffected."""
 server_handlers._wc.update({'v':None,'ts':0})
 server_handlers._mc.update({'lat':None,'lon':None,'ts':0})

class TestApiCompetitors(unittest.TestCase):
 def setUp(self): reset_caches()

 def test_no_position_returns_error(self):
  r=api_competitors(make_sk_fn(),make_gps()); self.assertEqual(r.get('error'),'no_position')
 def test_no_position_empty_competitors(self):
  r=api_competitors(make_sk_fn(),make_gps()); self.assertEqual(r['competitors'],[])
 def test_response_required_keys(self):
  sk=make_sk_fn(own_nav={'speedOverGround':{'value':3.086},'courseOverGroundTrue':{'value':math.radians(45.0)}},wind_twd_rad=math.radians(0.0))
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75))
  for k in ['ts','self','wind','mark','competitors']: self.assertIn(k,r)
 def test_sog_in_knots(self):
  sk=make_sk_fn(own_nav={'speedOverGround':{'value':3.086},'courseOverGroundTrue':{'value':0}})
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75)); self.assertAlmostEqual(r['self']['sog_kts'],6.0,delta=0.05)
 def test_cog_in_degrees(self):
  sk=make_sk_fn(own_nav={'speedOverGround':{'value':0},'courseOverGroundTrue':{'value':math.radians(135.0)}})
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75)); self.assertAlmostEqual(r['self']['cog'],135.0,delta=0.5)
 def test_wind_available(self):
  sk=make_sk_fn(wind_twd_rad=math.radians(225.0))
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75))
  self.assertTrue(r['wind']['available']); self.assertAlmostEqual(r['wind']['twd'],225.0,delta=0.5)
 def test_wind_unavailable(self):
  sk=make_sk_fn(wind_twd_rad=None)
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75)); self.assertFalse(r['wind']['available'])
 def test_mark_available(self):
  sk=make_sk_fn(mark_pos={'latitude':41.0,'longitude':-73.5})
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75)); self.assertTrue(r['mark']['available'])
 def test_mark_unavailable(self):
  sk=make_sk_fn(mark_pos=None)
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75)); self.assertFalse(r['mark']['available'])
 def test_ts_is_int(self):
  r=api_competitors(make_sk_fn(),make_gps(lat=40.92,lon=-73.75)); self.assertIsInstance(r['ts'],int)
 def test_twa_present_when_wind_available(self):
  """TWA present in response when wind data available (not None-checked here)."""
  sk=make_sk_fn(own_nav={'speedOverGround':{'value':3.086},'courseOverGroundTrue':{'value':math.radians(45.0)}},wind_twd_rad=math.radians(0.0))
  r=api_competitors(sk,make_gps(lat=40.92,lon=-73.75))
  self.assertIn('twa',r['self'])  # Just check key exists

class TestApiFleetDb(unittest.TestCase):
 def setUp(self): reset_caches()

 def test_required_keys(self):
  r=api_fleet_db(make_sk_fn())
  for k in ['total','active','competitors']: self.assertIn(k,r)
 def test_counts_are_integers(self):
  r=api_fleet_db(make_sk_fn())
  self.assertIsInstance(r['total'],int); self.assertIsInstance(r['active'],int)
 def test_active_lte_total(self):
  r=api_fleet_db(make_sk_fn()); self.assertLessEqual(r['active'],r['total'])
 def test_competitors_is_list(self):
  r=api_fleet_db(make_sk_fn()); self.assertIsInstance(r['competitors'],list)
 def test_total_matches_list_length(self):
  r=api_fleet_db(make_sk_fn()); self.assertEqual(r['total'],len(r['competitors']))

if __name__=='__main__':
 unittest.main(verbosity=2)

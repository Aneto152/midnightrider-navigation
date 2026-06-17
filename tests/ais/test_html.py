#!/usr/bin/env python3
"""Unit tests for ais/tracker.html and ais/fleet_db.html
Structural tests: file existence, required elements, fetch URLs, no secrets/IPs.
"""
import unittest, os

BASE = os.path.join(os.path.dirname(__file__), '..', '..')
TRACKER  = os.path.join(BASE, 'ais', 'tracker.html')
FLEET_DB = os.path.join(BASE, 'ais', 'fleet_db.html')

def read(path):
    with open(path) as f: return f.read()


class TestTrackerHtml(unittest.TestCase):
    """Tests for ais/tracker.html — live competitor tracker"""

    def setUp(self):
        self.html = read(TRACKER)

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(TRACKER))

    def test_valid_html5_doctype(self):
        self.assertTrue(self.html.strip().startswith('<!DOCTYPE html>'))

    def test_has_title(self):
        self.assertIn('<title>', self.html)
        self.assertIn('Tracker', self.html)

    def test_viewport_meta(self):
        self.assertIn('name="viewport"', self.html)

    def test_status_bar_element(self):
        self.assertIn('id="statusBar"', self.html)

    def test_self_card_element(self):
        self.assertIn('id="selfCard"', self.html)

    def test_competitor_list_element(self):
        self.assertIn('id="compList"', self.html)

    def test_radius_controls(self):
        self.assertIn('setRadius(', self.html)
        for r in [5, 10, 15, 20]:
            self.assertIn(f'setRadius({r})', self.html)

    def test_vmg_mode_toggle(self):
        self.assertIn("setMode('wind')", self.html)
        self.assertIn("setMode('mark')", self.html)

    def test_api_competitors_fetch(self):
        self.assertIn('/api/competitors', self.html)

    def test_radius_param_in_url(self):
        self.assertIn('radius_nm', self.html)

    def test_vmg_mode_param_in_url(self):
        self.assertIn('vmg_mode', self.html)

    def test_no_position_error_handled(self):
        self.assertIn('no_position', self.html)

    def test_color_green_red_neutral(self):
        for color in ['green', 'red', 'neutral']:
            self.assertIn(color, self.html)

    def test_auto_refresh_timer(self):
        self.assertIn('setInterval', self.html)
        self.assertIn('30', self.html)

    def test_no_hardcoded_ip(self):
        import re
        ips = re.findall(r'192\.168\.\d+\.\d+', self.html)
        self.assertEqual(ips, [], f'Hardcoded IPs found: {ips}')

    def test_no_credentials_in_html(self):
        for kw in ['password', 'secret', 'token', 'api_key']:
            self.assertNotIn(f'={kw}', self.html.lower())

    def test_portal_back_link(self):
        self.assertIn('href="/"', self.html)

    def test_fleet_db_link(self):
        self.assertIn('/ais/fleet_db', self.html)


class TestFleetDbHtml(unittest.TestCase):
    """Tests for ais/fleet_db.html — fleet database browser"""

    def setUp(self):
        self.html = read(FLEET_DB)

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(FLEET_DB))

    def test_valid_html5_doctype(self):
        self.assertTrue(self.html.strip().startswith('<!DOCTYPE html>'))

    def test_has_title(self):
        self.assertIn('<title>', self.html)
        self.assertIn('Fleet', self.html)

    def test_viewport_meta(self):
        self.assertIn('name="viewport"', self.html)

    def test_summary_elements(self):
        for eid in ['sumTotal', 'sumActive', 'sumLive', 'sumStale', 'sumAbsent']:
            self.assertIn(f'id="{eid}"', self.html)

    def test_search_input(self):
        self.assertIn('id="search"', self.html)

    def test_boat_list_element(self):
        self.assertIn('id="boatList"', self.html)

    def test_filter_buttons(self):
        self.assertIn("setFilter('live')", self.html)
        self.assertIn("setFilter('stale')", self.html)
        self.assertIn("setFilter('absent')", self.html)

    def test_api_fleet_db_fetch(self):
        self.assertIn('/api/fleet_db', self.html)

    def test_ais_status_values(self):
        for status in ['live', 'stale', 'old', 'absent']:
            self.assertIn(f"'{status}'", self.html)

    def test_search_filters_by_name(self):
        self.assertIn('b.name', self.html)
        self.assertIn('b.sail_num', self.html)
        self.assertIn('b.mmsi', self.html)

    def test_sort_by_ais_status(self):
        self.assertIn('ais_status', self.html)

    def test_no_hardcoded_ip(self):
        import re
        ips = re.findall(r'192\.168\.\d+\.\d+', self.html)
        self.assertEqual(ips, [], f'Hardcoded IPs found: {ips}')

    def test_no_credentials_in_html(self):
        for kw in ['password', 'secret', 'token']:
            self.assertNotIn(f'={kw}', self.html.lower())

    def test_tracker_back_link(self):
        self.assertIn('/ais/', self.html)

    def test_portal_link(self):
        self.assertIn('href="/"', self.html)


if __name__ == '__main__':
    unittest.main(verbosity=2)

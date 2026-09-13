#!/usr/bin/env python3
"""
Responsive layout tests for Fleet DB and AIS Tracker.

Verifies mobile and responsive CSS without accessing live services.
Does NOT access: InfluxDB, Docker, USB storage, Signal K, or running services.
"""

import unittest
import re
from pathlib import Path


class TestResponsiveLayout(unittest.TestCase):
    """Tests for responsive layout improvements"""

    @classmethod
    def setUpClass(cls):
        """Load HTML files for static analysis"""
        cls.base_dir = Path(__file__).parent.parent.parent
        cls.fleet_db_path = cls.base_dir / 'ais' / 'fleet_db.html'
        cls.tracker_path = cls.base_dir / 'ais' / 'tracker.html'

    def test_fleet_db_modal_responsive_rows(self):
        """Verify Fleet DB modal uses responsive grid for label/value pairs"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('grid-template-columns:minmax(0,38%) minmax(0,62%)', html)
        self.assertIn('gap:12px', html)

    def test_fleet_db_modal_overflow_protection(self):
        """Verify modal values have overflow-wrap for long names"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('overflow-wrap:anywhere', html)
        self.assertIn('word-break:break-word', html)

    def test_fleet_db_mobile_media_query_600px(self):
        """Verify mobile media query exists for Fleet DB at 600px"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:600px)', html)

    def test_fleet_db_mobile_media_query_480px(self):
        """Verify additional mobile media query at 480px"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:480px)', html)

    def test_fleet_db_mobile_media_query_375px(self):
        """Verify narrow mobile media query at 375px"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:375px)', html)

    def test_fleet_db_mobile_media_query_320px(self):
        """Verify ultra-narrow mobile media query at 320px"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:320px)', html)

    def test_fleet_db_modal_viewport_safe(self):
        """Verify modal has viewport-safe sizing (calc 100vw)"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('calc(100vw - ', html)
        self.assertIn('calc(100dvh - ', html)

    def test_ais_tracker_mobile_media_query_768px(self):
        """Verify AIS Tracker responsive media query at 768px"""
        with open(self.tracker_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:768px)', html)

    def test_ais_tracker_mobile_media_query_480px(self):
        """Verify AIS Tracker responsive media query at 480px"""
        with open(self.tracker_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:480px)', html)

    def test_ais_tracker_mobile_media_query_375px(self):
        """Verify AIS Tracker responsive media query at 375px"""
        with open(self.tracker_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:375px)', html)

    def test_ais_tracker_mobile_media_query_320px(self):
        """Verify AIS Tracker responsive media query at 320px"""
        with open(self.tracker_path) as f:
            html = f.read()
        self.assertIn('@media(max-width:320px)', html)

    def test_ais_tracker_header_hidden_mobile(self):
        """Verify AIS Tracker hides desktop header on mobile"""
        with open(self.tracker_path) as f:
            html = f.read()
        # Check for display:none in mobile media query
        mobile_section = re.search(
            r'@media\(max-width:768px\)[^}]+\.comp-header\{display:none\}',
            html,
            re.DOTALL
        )
        self.assertIsNotNone(mobile_section, "comp-header should be hidden on mobile")

    def test_fleet_db_boat_rows_mobile_single_column(self):
        """Verify Fleet DB boat rows convert to single column on mobile"""
        with open(self.fleet_db_path) as f:
            html = f.read()
        self.assertIn('grid-template-columns:1fr', html)

    def test_ais_tracker_min_width_zero(self):
        """Verify flexible grid children have min-width: 0"""
        with open(self.tracker_path) as f:
            html = f.read()
        # Check for min-width:0 protection
        self.assertIn('min-width:0', html)

    def test_no_hardcoded_ips_in_html(self):
        """Verify no hardcoded IPs in responsive CSS"""
        with open(self.fleet_db_path) as f:
            fleet_db = f.read()
        with open(self.tracker_path) as f:
            tracker = f.read()
        
        ip_pattern = r'192\.168\.\d+\.\d+'
        fleet_ips = re.findall(ip_pattern, fleet_db)
        tracker_ips = re.findall(ip_pattern, tracker)
        
        self.assertEqual(fleet_ips, [], f"Found IPs in fleet_db: {fleet_ips}")
        self.assertEqual(tracker_ips, [], f"Found IPs in tracker: {tracker_ips}")

    def test_no_credential_patterns_in_html(self):
        """Verify no credential patterns in responsive code"""
        with open(self.fleet_db_path) as f:
            fleet_db = f.read()
        with open(self.tracker_path) as f:
            tracker = f.read()
        
        for pattern in ['token:', 'secret:', 'password:', 'api_key:']:
            self.assertNotIn(pattern, fleet_db, f"Found {pattern} in fleet_db")
            self.assertNotIn(pattern, tracker, f"Found {pattern} in tracker")


if __name__ == '__main__':
    unittest.main()

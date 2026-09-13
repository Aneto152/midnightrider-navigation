#!/usr/bin/env python3
"""Wind LIS source links and portal navigation — complete test suite (21 tests)."""

import unittest
import sys
import os

# Add repo to path
sys.path.insert(0, os.path.dirname(__file__) + '/../..')

# Import pure URL helpers (no dependencies on weather_collector or other services)
from regatta.wind_sources import ndbc_source_url, asos_source_url


class TestNDBCSourceURLHelpers(unittest.TestCase):
    """Test NDBC URL generation (Tests 1–3)."""

    def test_ndbc_url_format(self):
        """Test 1: NDBC URLs use https://www.ndbc.noaa.gov/data/realtime2/"""
        url = ndbc_source_url('44025')
        self.assertTrue(url.startswith('https://www.ndbc.noaa.gov/data/realtime2/'))
        self.assertTrue(url.endswith('.txt'))
        self.assertIn('44025', url)

    def test_ndbc_station_normalization(self):
        """Test 2: NDBC station IDs normalized to uppercase."""
        url_lower = ndbc_source_url('nwpr1')
        url_upper = ndbc_source_url('NWPR1')
        self.assertEqual(url_lower, url_upper)
        self.assertIn('NWPR1', url_lower)

    def test_ndbc_whitespace_handling(self):
        """Test 3: NDBC handles leading/trailing whitespace."""
        url = ndbc_source_url('  44025  ')
        self.assertIn('44025', url)
        self.assertNotIn(' ', url)


class TestASOS_SourceURLHelpers(unittest.TestCase):
    """Test ASOS URL generation (Tests 4–6)."""

    def test_asos_url_format(self):
        """Test 4: ASOS URLs use https://api.weather.gov/stations/"""
        url = asos_source_url('KBDR')
        self.assertTrue(url.startswith('https://api.weather.gov/stations/'))
        self.assertIn('/observations/latest', url)
        self.assertIn('KBDR', url)

    def test_asos_station_normalization(self):
        """Test 5: ASOS station IDs normalized to uppercase."""
        url_lower = asos_source_url('kbdr')
        url_upper = asos_source_url('KBDR')
        self.assertEqual(url_lower, url_upper)
        self.assertIn('KBDR', url_lower)

    def test_asos_whitespace_handling(self):
        """Test 6: ASOS handles leading/trailing whitespace."""
        url = asos_source_url('  KBDR  ')
        self.assertIn('KBDR', url)
        self.assertNotIn(' ', url)


class TestWindLISHTMLStructure(unittest.TestCase):
    """Test Wind LIS HTML features (Tests 7–15)."""

    @classmethod
    def setUpClass(cls):
        """Load wind.html for inspection."""
        wind_path = os.path.join(os.path.dirname(__file__), '../../regatta/wind.html')
        with open(wind_path, 'r') as f:
            cls.html_content = f.read()

    def test_portal_navigation_link_exists(self):
        """Test 7: Navigation contains Portal link with href=/"""
        self.assertIn('href="/"', self.html_content)
        self.assertIn('Portal', self.html_content)

    def test_navigation_element_exists(self):
        """Test 8: Navigation element with class 'nav' exists."""
        self.assertIn('class="nav"', self.html_content)

    def test_measurement_source_class_exists(self):
        """Test 9: CSS class 'measurement-source' exists for source-backed measurements."""
        self.assertIn('measurement-source', self.html_content)

    def test_double_click_handler_exists(self):
        """Test 10: JavaScript double-click event handler is attached."""
        self.assertIn('dblclick', self.html_content)
        self.assertIn('window.open', self.html_content)

    def test_noopener_noreferrer_protection(self):
        """Test 11: window.open includes noopener,noreferrer protection."""
        self.assertIn('noopener,noreferrer', self.html_content)

    def test_ndbc_allowlist_exists(self):
        """Test 12: NDBC HTTPS origin in allowlist."""
        self.assertIn('https://www.ndbc.noaa.gov/', self.html_content)

    def test_weather_gov_allowlist_exists(self):
        """Test 13: Weather.gov HTTPS origin in allowlist."""
        self.assertIn('https://api.weather.gov/', self.html_content)

    def test_url_validation_function_exists(self):
        """Test 14: URL validation function isAllowedSourceUrl exists."""
        self.assertIn('isAllowedSourceUrl', self.html_content)
        self.assertIn('ALLOWED_ORIGINS', self.html_content)

    def test_responsive_navigation_css_exists(self):
        """Test 15: Responsive navigation CSS with flex-wrap exists."""
        self.assertIn('flex-wrap', self.html_content)
        self.assertIn('.nav', self.html_content)


class TestSecurityConstraints(unittest.TestCase):
    """Test security constraints (Tests 16–21)."""

    def test_no_hardcoded_internal_ips_in_html(self):
        """Test 16: No hardcoded internal IP addresses (192.168.1.x) in wind.html."""
        wind_path = os.path.join(os.path.dirname(__file__), '../../regatta/wind.html')
        with open(wind_path, 'r') as f:
            content = f.read()
        self.assertNotIn('192.168.1.', content)

    def test_no_hardcoded_internal_ips_in_server(self):
        """Test 17: No hardcoded internal IP addresses in regatta/server.py."""
        server_path = os.path.join(os.path.dirname(__file__), '../../regatta/server.py')
        with open(server_path, 'r') as f:
            content = f.read()
        self.assertNotIn('192.168.1.', content)

    def test_no_embedded_tokens_in_html(self):
        """Test 18: No embedded token literals in wind.html."""
        wind_path = os.path.join(os.path.dirname(__file__), '../../regatta/wind.html')
        with open(wind_path, 'r') as f:
            content = f.read()
        self.assertNotIn('token="', content)
        self.assertNotIn('token=', content)

    def test_no_embedded_secrets_in_html(self):
        """Test 19: No embedded secret literals in wind.html."""
        wind_path = os.path.join(os.path.dirname(__file__), '../../regatta/wind.html')
        with open(wind_path, 'r') as f:
            content = f.read()
        self.assertNotIn('secret="', content)
        self.assertNotIn('secret=', content)

    def test_no_embedded_credentials_in_server(self):
        """Test 20: No embedded credentials in regatta/server.py."""
        server_path = os.path.join(os.path.dirname(__file__), '../../regatta/server.py')
        with open(server_path, 'r') as f:
            content = f.read()
        self.assertNotIn('password="', content)
        self.assertNotIn('api_key="', content)

    def test_pure_helpers_no_dependencies(self):
        """Test 21: Pure helpers module has no external dependencies."""
        helpers_path = os.path.join(os.path.dirname(__file__), '../../regatta/wind_sources.py')
        with open(helpers_path, 'r') as f:
            content = f.read()
        # Should not import weather_collector or any external libs
        self.assertNotIn('import weather_collector', content)
        self.assertNotIn('import requests', content)
        self.assertNotIn('import urllib', content)


if __name__ == '__main__':
    unittest.main()

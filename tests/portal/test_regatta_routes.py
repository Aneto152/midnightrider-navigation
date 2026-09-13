#!/usr/bin/env python3
"""
Regression tests for Regatta portal route resolution.

Verifies that all Regatta routes resolve correctly:
- /regatta → regatta/index.html
- /regatta/ → regatta/index.html
- /regatta/index.html → regatta/index.html
- /regatta/wind → regatta/wind.html
- /regatta/wind/ → regatta/wind.html
- /regatta/crew → regatta/crew.html
- /regatta/voiles → regatta/voiles.html
- Unknown routes return None (404 handled by portal)
- Path traversal is rejected

Does NOT access: InfluxDB, Docker, USB storage, Signal K, NOAA, or running services.
"""

import unittest
import json
from pathlib import Path
import sys

# Add portal to path so we can import the resolver
portal_dir = Path(__file__).parent.parent.parent / "portal"
sys.path.insert(0, str(portal_dir.parent))

from portal.server import resolve_regatta_path


class TestRegattaRoutes(unittest.TestCase):
    """Regression tests for Regatta route resolution."""

    @classmethod
    def setUpClass(cls):
        """Load static files for verification."""
        cls.base_dir = Path(__file__).parent.parent.parent
        cls.regatta_dir = cls.base_dir / "regatta"
        cls.portal_dir = cls.base_dir / "portal"
        cls.portal_index = cls.portal_dir / "index.html"

    def test_1_regatta_root_resolves_to_index(self):
        """Test /regatta resolves to regatta/index.html."""
        result = resolve_regatta_path("/regatta")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("index.html"))
        self.assertTrue(result.exists())

    def test_2_regatta_slash_resolves_to_index(self):
        """Test /regatta/ resolves to regatta/index.html."""
        result = resolve_regatta_path("/regatta/")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("index.html"))
        self.assertTrue(result.exists())

    def test_3_regatta_index_html_resolves(self):
        """Test /regatta/index.html resolves to regatta/index.html."""
        result = resolve_regatta_path("/regatta/index.html")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("index.html"))
        self.assertTrue(result.exists())

    def test_4_regatta_wind_resolves_to_wind_html(self):
        """Test /regatta/wind resolves to regatta/wind.html."""
        result = resolve_regatta_path("/regatta/wind")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("wind.html"))
        self.assertTrue(result.exists())

    def test_5_regatta_wind_slash_resolves_to_wind_html(self):
        """Test /regatta/wind/ resolves to regatta/wind.html."""
        result = resolve_regatta_path("/regatta/wind/")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("wind.html"))
        self.assertTrue(result.exists())

    def test_6_regatta_crew_resolves_to_crew_html(self):
        """Test /regatta/crew resolves to regatta/crew.html."""
        result = resolve_regatta_path("/regatta/crew")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("crew.html"))
        self.assertTrue(result.exists())

    def test_7_regatta_voiles_resolves_to_voiles_html(self):
        """Test /regatta/voiles resolves to regatta/voiles.html."""
        result = resolve_regatta_path("/regatta/voiles")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("voiles.html"))
        self.assertTrue(result.exists())

    def test_8_unknown_regatta_route_returns_none(self):
        """Test unknown routes return None (portal returns 404)."""
        result = resolve_regatta_path("/regatta/unknown_route")
        self.assertIsNone(result)

    def test_9_path_traversal_rejected(self):
        """Test path traversal is rejected."""
        result = resolve_regatta_path("/regatta/../portal/index.html")
        self.assertIsNone(result)

    def test_10_encoded_path_traversal_rejected(self):
        """Test encoded path traversal is rejected."""
        result = resolve_regatta_path("/regatta/%2e%2e/portal/index.html")
        self.assertIsNone(result)

    def test_11_portal_index_still_links_to_regatta(self):
        """Test that portal/index.html still contains href='/regatta'."""
        with open(self.portal_index) as f:
            html = f.read()
        self.assertIn('href="/regatta"', html, 
                      "portal/index.html must still link to /regatta")

    def test_12_portal_index_still_links_to_regatta_wind(self):
        """Test that portal/index.html still contains href='/regatta/wind'."""
        with open(self.portal_index) as f:
            html = f.read()
        self.assertIn('href="/regatta/wind"', html,
                      "portal/index.html must still link to /regatta/wind")

    def test_13_explicit_html_path_valid(self):
        """Test explicit .html paths remain valid: /regatta/wind.html."""
        result = resolve_regatta_path("/regatta/wind.html")
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("wind.html"))
        self.assertTrue(result.exists())

    def test_14_regatta_server_handles_ndbc_api(self):
        """Test that regatta/server.py handles /api/ndbc/ endpoint."""
        regatta_server = self.regatta_dir / "server.py"
        with open(regatta_server) as f:
            content = f.read()
        self.assertIn("/api/ndbc/", content,
                      "regatta/server.py must handle /api/ndbc/ endpoint")

    def test_15_regatta_server_handles_asos_api(self):
        """Test that regatta/server.py handles /api/asos/ endpoint."""
        regatta_server = self.regatta_dir / "server.py"
        with open(regatta_server) as f:
            content = f.read()
        self.assertIn("/api/asos/", content,
                      "regatta/server.py must handle /api/asos/ endpoint")


if __name__ == "__main__":
    unittest.main(verbosity=2)

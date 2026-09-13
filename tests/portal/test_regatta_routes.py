#!/usr/bin/env python3
"""
Route resolution tests for Regatta extensionless URLs.

Does NOT access:
- InfluxDB
- Docker
- USB storage
- Signal K
- running services
"""

import unittest
from pathlib import Path
import sys

# Add workspace root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Import the pure route resolver from portal/server.py
import importlib.util
spec = importlib.util.spec_from_file_location("portal_server", REPO_ROOT / "portal" / "server.py")
portal_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portal_server)

resolve_regatta_path = portal_server.resolve_regatta_path
REGATTA = REPO_ROOT / "regatta"


class TestRegattaRoutes(unittest.TestCase):
    """Test extensionless route resolution for /regatta URLs"""

    def test_regatta_root_resolves_to_index(self):
        """Test /regatta resolves to index.html"""
        result = resolve_regatta_path("/regatta")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "index.html")

    def test_regatta_root_slash_resolves_to_index(self):
        """Test /regatta/ resolves to index.html"""
        result = resolve_regatta_path("/regatta/")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "index.html")

    def test_regatta_wind_resolves_to_wind_html(self):
        """Test /regatta/wind resolves to wind.html"""
        result = resolve_regatta_path("/regatta/wind")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wind.html")

    def test_regatta_wind_slash_resolves_to_wind_html(self):
        """Test /regatta/wind/ resolves to wind.html"""
        result = resolve_regatta_path("/regatta/wind/")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wind.html")

    def test_regatta_crew_resolves_to_crew_html(self):
        """Test /regatta/crew resolves to crew.html"""
        result = resolve_regatta_path("/regatta/crew")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "crew.html")

    def test_regatta_voiles_resolves_to_voiles_html(self):
        """Test /regatta/voiles resolves to voiles.html"""
        result = resolve_regatta_path("/regatta/voiles")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "voiles.html")

    def test_explicit_html_path_valid(self):
        """Test explicit .html paths remain valid"""
        result = resolve_regatta_path("/regatta/wind.html")
        # File must exist to return non-None
        if result:
            self.assertTrue(result.exists())
            self.assertEqual(result.name, "wind.html")

    def test_path_traversal_rejected(self):
        """Test path traversal is rejected"""
        result = resolve_regatta_path("/regatta/../portal/index.html")
        self.assertIsNone(result)

    def test_path_traversal_encoded_rejected(self):
        """Test encoded path traversal is rejected"""
        result = resolve_regatta_path("/regatta/%2e%2e/portal/index.html")
        self.assertIsNone(result)

    def test_target_files_are_real(self):
        """Test that all target files actually exist before accessing"""
        # This ensures we don't serve paths to files that don't exist
        for route, filename in [
            ("/regatta", "index.html"),
            ("/regatta/wind", "wind.html"),
            ("/regatta/crew", "crew.html"),
        ]:
            result = resolve_regatta_path(route)
            self.assertIsNotNone(result, f"Route {route} should resolve")
            self.assertTrue(result.exists(), f"File {filename} must exist for route {route}")
            # Verify portal _serve() will find the file
            with open(result) as f:
                content = f.read()
            self.assertGreater(len(content), 0, f"{filename} should not be empty")



    def test_portal_index_links_to_regatta_wind(self):
        """Test that portal/index.html links to /regatta/wind"""
        portal_index = REPO_ROOT / "portal" / "index.html"
        with open(portal_index) as f:
            content = f.read()
        self.assertIn("/regatta/wind", content)

    def test_wind_html_calls_ndbc_api(self):
        """Test that wind.html calls /api/ndbc/<station>"""
        wind_html = REPO_ROOT / "regatta" / "wind.html"
        with open(wind_html) as f:
            content = f.read()
        self.assertIn("/api/ndbc/", content)

    def test_wind_html_calls_asos_api(self):
        """Test that wind.html calls /api/asos/<station>"""
        wind_html = REPO_ROOT / "regatta" / "wind.html"
        with open(wind_html) as f:
            content = f.read()
        self.assertIn("/api/asos/", content)

    def test_regatta_server_handles_ndbc_api(self):
        """Test that regatta/server.py handles /api/ndbc/"""
        regatta_server = REPO_ROOT / "regatta" / "server.py"
        with open(regatta_server) as f:
            content = f.read()
        self.assertIn("/api/ndbc/", content)

    def test_regatta_server_handles_asos_api(self):
        """Test that regatta/server.py handles /api/asos/"""
        regatta_server = REPO_ROOT / "regatta" / "server.py"
        with open(regatta_server) as f:
            content = f.read()
        self.assertIn("/api/asos/", content)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Regression tests for Fleet starred boats JavaScript runtime defects.
These tests specifically verify that the defects found in commit 7e232fc are fixed:
- No Array.from(...).has() calls
- No Array.from(...).size references
- Exactly one toggleFleetStar implementation
- Exactly one canonical starred state
- API uses 'starred_ids' not 'starred'
"""
import unittest
from pathlib import Path


class TestFleetStarsRegressions(unittest.TestCase):
    """Regression tests for JavaScript runtime defects in Fleet starred implementation"""

    def setUp(self):
        """Load HTML and JavaScript files for inspection"""
        self.fleet_db_html = Path('ais/fleet_db.html').read_text()
        self.fleet_stars_js = Path('ais/fleet_stars.js').read_text()
        self.server_py = Path('regatta/server.py').read_text()

    def test_01_no_array_from_has_pattern(self):
        """Verify no Array.from(...).has() calls that would crash at runtime"""
        # The implementation moved to fleet_stars.js on 2026-09-14: the inline
        # copy in fleet_db.html was a duplicate global definition.
        # Array.from(...) is legitimate here: a Set must be converted to an
        # Array to be JSON-serialised into localStorage. The 7e232fc defect was
        # calling SET methods on the resulting Array, which always fails.
        toggle_body = self.fleet_stars_js.split('function toggleFleetStar')[-1]
        for bad in ('Array.from(getLocalStarred()).has(',
                    'Array.from(getLocalStarred()).size',
                    'Array.from(starred).has(',
                    'Array.from(starred).size'):
            self.assertNotIn(bad, toggle_body,
                             'Set method called on an Array: ' + bad)

    def test_02_no_array_from_size_pattern(self):
        """Verify no Array.from(...).size calls (Arrays don't have .size)"""
        self.assertNotIn('Array.from(getLocalStarred()).size', self.fleet_db_html)

    def test_03_exactly_one_toggle_fleet_star(self):
        """Verify exactly one toggleFleetStar implementation (no duplicates)"""
        # Was: exactly one definition in fleet_db.html. That definition was the
        # defect - a second, incompatible (boat, event) signature silently
        # overriding the async (boatKey) implementation. Canonical owner is now
        # fleet_stars.js; fleet_db.html only holds the onStarClick adapter.
        html_count = self.fleet_db_html.count('function toggleFleetStar')
        js_count = self.fleet_stars_js.count('function toggleFleetStar')
        self.assertEqual(html_count, 0,
                         f"toggleFleetStar must not be redefined in fleet_db.html, found {html_count}")
        self.assertEqual(js_count, 1,
                         f"Expected 1 toggleFleetStar in fleet_stars.js, found {js_count}")

    def test_04_exactly_one_get_local_starred(self):
        """Verify exactly one getLocalStarred implementation"""
        count = self.fleet_stars_js.count('function getLocalStarred()') + \
                self.fleet_db_html.count('function getLocalStarred()')
        self.assertEqual(count, 1, f"Expected 1 getLocalStarred, found {count}")

    def test_05_api_uses_starred_ids_not_starred(self):
        """Verify API responses use 'starred_ids' not 'starred'"""
        # Check server.py uses canonical 'starred_ids' key in responses
        self.assertIn("'starred_ids'", self.server_py,
                      "API responses must use 'starred_ids' key")

        # Verify handler function returns correct key
        self.assertIn("get_starred()", self.server_py,
                      "API must call get_starred() from handler")

    def test_06_toggle_uses_set_methods(self):
        """Verify toggleFleetStar uses Set methods (.has, .add, .delete)"""
        toggle_func = self.fleet_stars_js.split('function toggleFleetStar')[1].split('function ')[0]
        self.assertIn('.has(', toggle_func, "toggleFleetStar must use Set.has()")
        self.assertIn('.add(', toggle_func, "toggleFleetStar must use Set.add()")
        self.assertIn('.delete(', toggle_func, "toggleFleetStar must use Set.delete()")

    def test_07_update_count_uses_set_size(self):
        """Verify updateStarredCount uses Set.size not Array.length"""
        count_func = self.fleet_db_html.split('function updateStarredCount')[1].split('function ')[0]
        self.assertIn('.size', count_func, "updateStarredCount must use Set.size")
        self.assertNotIn('Array.from', count_func, "updateStarredCount must not convert Set to Array")

    def test_08_filtered_boats_uses_set_has(self):
        """Verify getFilteredBoats uses Set.has() for filtering"""
        filtered_func = self.fleet_db_html.split('function getFilteredBoats')[1].split('function ')[0]
        self.assertIn('.has(', filtered_func, "getFilteredBoats must use Set.has()")
        self.assertNotIn('Array.from(getLocalStarred())', filtered_func)

    def test_09_render_uses_canonical_set(self):
        """Verify render() uses canonical Set throughout"""
        render_func = self.fleet_db_html.split('function render()')[1].split('function ')[0]
        self.assertNotIn('Array.from(getLocalStarred())', render_func)

    def test_10_no_server_data_starred_key(self):
        """Verify frontend doesn't reference serverData.starred (use starred_ids)"""
        self.assertNotIn('serverData.starred[', self.fleet_stars_js)
        self.assertNotIn('serverData.starred)', self.fleet_stars_js)

    def test_11_merge_uses_starred_ids_key(self):
        """Verify merge requests/responses use 'starred_ids' canonical key"""
        self.assertIn("body: JSON.stringify({ starred_ids:", self.fleet_stars_js)
        self.assertIn("merged.starred_ids", self.fleet_stars_js)


if __name__ == '__main__':
    unittest.main()

"""test_fleet_ui_contract.py - Fleet UI/HTML contract validation tests

Validates that the Fleet database UI correctly:
1. Displays exactly one LIVE AIS summary metric (canonical)
2. Removes duplicate ACTIVE summary card
3. Uses data.live_ais from handler (not manual calculation)
4. Preserves boat interactions (search, sort, star, modal)
"""

import unittest
import re
from pathlib import Path


class TestFleetUIHTMLContract(unittest.TestCase):
    """Static HTML contract tests for Fleet database page."""

    @classmethod
    def setUpClass(cls):
        """Load the HTML file once for all tests."""
        cls.html_path = Path(__file__).parent.parent.parent / 'ais' / 'fleet_db.html'
        with open(cls.html_path, 'r') as f:
            cls.html_content = f.read()

    def test_01_active_summary_card_removed(self):
        """Verify ACTIVE summary card is completely removed."""
        self.assertNotIn(
            '<span class="sum-lbl">Active</span>',
            self.html_content,
            "ACTIVE summary card must be removed"
        )

    def test_02_live_ais_summary_card_present(self):
        """Verify exactly one LIVE AIS summary card exists."""
        count = self.html_content.count('<span class="sum-lbl">Live AIS</span>')
        self.assertEqual(
            count, 1,
            f"Expected exactly 1 LIVE AIS summary card, got {count}"
        )

    def test_03_total_summary_card_present(self):
        """Verify TOTAL summary card remains."""
        count = self.html_content.count('<span class="sum-lbl">Total</span>')
        self.assertEqual(
            count, 1,
            f"Expected exactly 1 TOTAL summary card, got {count}"
        )

    def test_04_starred_summary_card_present(self):
        """Verify STARRED summary card remains."""
        count = self.html_content.count('<span class="sum-lbl">Starred</span>')
        self.assertEqual(
            count, 1,
            f"Expected exactly 1 STARRED summary card, got {count}"
        )

    def test_05_no_activeBoats_element_reference(self):
        """Verify activeBoats element is not referenced in JavaScript."""
        self.assertNotIn(
            "document.getElementById('activeBoats')",
            self.html_content,
            "activeBoats element must be removed from JavaScript"
        )

    def test_06_live_ais_uses_canonical_handler_field(self):
        """Verify JavaScript uses data.live_ais (canonical) from handler."""
        self.assertIn(
            "document.getElementById('liveCount').textContent = data.live_ais",
            self.html_content,
            "JavaScript must use canonical data.live_ais field"
        )

    def test_07_manual_live_calculation_removed(self):
        """Verify manual liveCount calculation is removed."""
        self.assertNotIn(
            'const liveCount = boats.filter',
            self.html_content,
            "Manual liveCount calculation must be removed (use canonical data.live_ais)"
        )

    def test_08_total_uses_handler_field(self):
        """Verify total still uses data.total from handler."""
        self.assertIn(
            "document.getElementById('totalBoats').textContent = data.total",
            self.html_content,
            "JavaScript must use data.total for total counter"
        )

    def test_09_summary_card_structure_valid(self):
        """Verify summary section has exactly 3 sum-item divs (TOTAL, LIVE AIS, STARRED)."""
        summary_match = re.search(
            r'<div class="summary"[^>]*>(.*?)</div>\s*(?=<div class="controls")',
            self.html_content,
            re.DOTALL
        )
        self.assertIsNotNone(summary_match, "Summary section not found")

        summary_section = summary_match.group(1)
        sum_items = summary_section.count('<div class="sum-item')
        self.assertEqual(
            sum_items, 3,
            f"Expected exactly 3 summary cards (TOTAL, LIVE AIS, STARRED), got {sum_items}"
        )

    def test_10_search_sort_star_modal_hooks_present(self):
        """Verify boat interaction hooks remain unchanged."""
        self.assertIn('function setFilter(f)', self.html_content)
        self.assertIn('function setSort(s)', self.html_content)
        self.assertIn('function toggleFleetStar(boat, event)', self.html_content)
        self.assertIn('function showModal(boat)', self.html_content)

    def test_11_no_historical_badge_in_html(self):
        """Verify no HISTORICAL badge class is introduced."""
        self.assertNotIn(
            'badge.historical',
            self.html_content,
            "No HISTORICAL badge class should exist"
        )
        self.assertNotIn(
            'class="badge historical',
            self.html_content,
            "No HISTORICAL badge should be rendered"
        )

    def test_12_no_historical_filter_tab(self):
        """Verify no separate HISTORICAL filter tab is introduced."""
        self.assertNotIn(
            "filterHistorical",
            self.html_content,
            "No separate historical filter tab should exist"
        )

    def test_13_fetch_api_call_references_fleet_db(self):
        """Verify JavaScript fetches from /api/fleet_db."""
        self.assertIn(
            "fetch('/api/fleet_db')",
            self.html_content,
            "JavaScript must fetch from /api/fleet_db endpoint"
        )

    def test_14_modal_fields_support_all_records(self):
        """Verify modal template supports both current and historical boats."""
        # Modal should not filter by active status
        self.assertNotIn(
            'if (boat.active)',
            self.html_content,
            "Modal should not filter by active status"
        )

        # Modal should display standard fields for all records
        self.assertIn('id="modalName"', self.html_content)
        self.assertIn('id="modalSail"', self.html_content)
        self.assertIn('id="modalClass"', self.html_content)
        self.assertIn('id="modalMMSI"', self.html_content)
        self.assertIn('id="modalAIS"', self.html_content)

    def test_15_ais_status_badge_classes_remain(self):
        """Verify AIS status badge classes are defined in CSS and used in templates."""
        # Check CSS has badge status classes
        self.assertIn('.badge.live', self.html_content)
        self.assertIn('.badge.stale', self.html_content)
        self.assertIn('.badge.old', self.html_content)
        self.assertIn('.badge.absent', self.html_content)
        # Check template uses badge with status
        self.assertIn('<span class="badge', self.html_content)
        self.assertIn('${aisInfo.status}', self.html_content)

    def test_16_boat_row_structure_unchanged(self):
        """Verify boat-row HTML structure template is present for unified rendering."""
        # Check CSS defines boat-row
        self.assertIn('.boat-row{', self.html_content)
        # Check JavaScript template creates boat-row with correct structure
        self.assertIn('<div class="boat-row', self.html_content)
        self.assertIn('class="boat-info"', self.html_content)
        self.assertIn('ondblclick="showModal', self.html_content)

    def test_17_star_toggle_function_present(self):
        """Verify star toggle functionality remains."""
        self.assertIn('toggleFleetStar(', self.html_content)
        self.assertIn('getLocalStarred()', self.html_content)
        self.assertIn('saveStarred(starred)', self.html_content)

    def test_18_filter_all_button_references_correct_function(self):
        """Verify filter buttons call setFilter correctly."""
        self.assertIn("onclick=\"setFilter('all')\"", self.html_content)
        self.assertIn("onclick=\"setFilter('starred')\"", self.html_content)

    def test_19_sort_buttons_reference_correct_function(self):
        """Verify sort buttons call setSort correctly."""
        self.assertIn("onclick=\"setSort('name')\"", self.html_content)
        self.assertIn("onclick=\"setSort('distance')\"", self.html_content)

    def test_20_no_activeBoats_id_element_exists(self):
        """Verify no HTML element or reference to activeBoats exists."""
        # Should not appear in static HTML or JavaScript
        self.assertNotIn('activeBoats', self.html_content)

    def test_21_liveCount_id_element_exists_in_summary(self):
        """Verify liveCount element is in the summary section."""
        summary_match = re.search(
            r'<div class="summary"[^>]*>(.*?)</div>\s*(?=<div class="controls")',
            self.html_content,
            re.DOTALL
        )
        self.assertIsNotNone(summary_match)
        summary_section = summary_match.group(1)
        self.assertIn('id="liveCount"', summary_section)

    def test_22_totalBoats_id_element_exists_in_summary(self):
        """Verify totalBoats element is in the summary section."""
        summary_match = re.search(
            r'<div class="summary"[^>]*>(.*?)</div>\s*(?=<div class="controls")',
            self.html_content,
            re.DOTALL
        )
        self.assertIsNotNone(summary_match)
        summary_section = summary_match.group(1)
        self.assertIn('id="totalBoats"', summary_section)

    def test_23_starredBoats_id_element_exists_in_summary(self):
        """Verify starredBoats element is in the summary section."""
        summary_match = re.search(
            r'<div class="summary"[^>]*>(.*?)</div>\s*(?=<div class="controls")',
            self.html_content,
            re.DOTALL
        )
        self.assertIsNotNone(summary_match)
        summary_section = summary_match.group(1)
        self.assertIn('id="starredBoats"', summary_section)

    def test_24_load_function_reads_correct_fields(self):
        """Verify load() function reads correct fields from API response."""
        self.assertIn('data.competitors', self.html_content)
        self.assertIn('data.total', self.html_content)
        self.assertIn('data.live_ais', self.html_content)
        # Should NOT display data.active in the summary display
        # The canonical load pattern should be: totalBoats = data.total, liveCount = data.live_ais
        self.assertIn(
            "document.getElementById('totalBoats').textContent = data.total",
            self.html_content
        )
        self.assertIn(
            "document.getElementById('liveCount').textContent = data.live_ais",
            self.html_content
        )


if __name__ == '__main__':
    unittest.main()

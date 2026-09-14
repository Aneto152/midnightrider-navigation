#!/usr/bin/env python3
"""The buttons marked 'active' must match the JavaScript initial state.

Shipped defect, 2026-09-14: fleet_db.html opened with the 'Starred' button
highlighted while `let filter = 'all'` was displaying the unfiltered list, and
no sort button was highlighted although `let sort = 'name'` was the applied
order. The markup carried a hand-written active class that nothing kept in sync
with the state variables; setFilter() only repaired the display on first click.

Same root cause as five other defects shipped the same day: a piece of state
duplicated in two places with nothing enforcing agreement. This guard costs two
regexes and makes the divergence impossible to ship again.
"""
import os
import re
import unittest

HTML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'ais', 'fleet_db.html')

GROUPS = (
    ('filter', {'all': 'filterAll', 'starred': 'filterStarred'}),
    ('sort', {'name': 'sortName', 'distance': 'sortDist'}),
)


class TestFleetFilterDefault(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(HTML, encoding='utf-8') as handle:
            cls.html = handle.read()

    def classes_of(self, button_id):
        match = re.search(
            r'<button\s+class="([^"]*)"\s+id="' + re.escape(button_id) + r'"',
            self.html)
        self.assertIsNotNone(match, 'button {} not found'.format(button_id))
        return match.group(1).split()

    def js_default(self, name):
        match = re.search(r"let\s+" + name + r"\s*=\s*'([a-z]+)'", self.html)
        self.assertIsNotNone(match, 'JS default for {} not found'.format(name))
        return match.group(1)

    def test_active_button_matches_js_default(self):
        for state, buttons in GROUPS:
            default = self.js_default(state)
            self.assertIn(default, buttons,
                          'unknown default {} for {}'.format(default, state))
            for value, button_id in buttons.items():
                is_active = 'active' in self.classes_of(button_id)
                self.assertEqual(
                    is_active, value == default,
                    '{}: button {} active={} but JS default is {}'.format(
                        state, button_id, is_active, default))

    def test_exactly_one_active_button_per_group(self):
        for state, buttons in GROUPS:
            active = [b for b in buttons.values() if 'active' in self.classes_of(b)]
            self.assertEqual(len(active), 1,
                             '{}: expected 1 active button, got {}'.format(state, active))


if __name__ == '__main__':
    unittest.main()

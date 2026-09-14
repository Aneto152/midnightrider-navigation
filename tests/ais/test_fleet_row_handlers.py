#!/usr/bin/env python3
"""Row handlers must resolve an id to a real boat before delegating.

Lot D3 (2026-09-14) stopped serialising the whole boat record into the
ondblclick and onclick attributes of every row: 31 keys after lot C2 meant
~3 MB of duplicated JSON inside the page HTML, measured, on top of the API
payload. Rows now carry the id only, and two resolvers rebuild the object.

That refactor created a blind spot. test_fleet_db_star_identity verifies the
delegation chain onStarClick -> getBoatStarKey -> toggleFleetStar, but nothing
verified that the inline attribute still reaches onStarClick at all. A resolver
returning null would silently kill every star and every modal while the whole
suite stayed green. That is exactly how populateRaceHistory shipped: a correct
function that nobody called.

These guards pin the full path: attribute -> resolver -> lookup -> delegate.
"""
import os
import re
import unittest

HTML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'ais', 'fleet_db.html')


class TestFleetRowHandlers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(HTML, encoding='utf-8') as handle:
            cls.html = handle.read()

    def body_of(self, signature):
        start = self.html.index(signature)
        depth, i = 0, self.html.index('{', start)
        for j in range(i, len(self.html)):
            if self.html[j] == '{':
                depth += 1
            elif self.html[j] == '}':
                depth -= 1
                if depth == 0:
                    return self.html[i:j + 1]
        self.fail('unbalanced braces after ' + signature)

    def test_row_attributes_carry_the_id(self):
        self.assertIn("ondblclick=\"showModalById('${boat.id}')\"", self.html)
        self.assertIn("onclick=\"onStarClickById('${boat.id}', event)\"", self.html)

    def test_no_full_record_left_in_any_attribute(self):
        for match in re.finditer(r'\b(on\w+)="([^"]*)"', self.html):
            self.assertNotIn('JSON.stringify', match.group(2),
                             'attribute {} still serialises a record'.format(match.group(1)))

    def test_resolvers_are_defined(self):
        for signature in ('function findBoat(id)',
                          'function showModalById(id)',
                          'function onStarClickById(id, event)'):
            self.assertIn(signature, self.html, signature + ' missing')

    def test_findboat_searches_the_loaded_array(self):
        body = self.body_of('function findBoat(id)')
        self.assertIn('boats', body, 'findBoat must look into the loaded boats array')
        self.assertIn('.id', body)

    def test_resolvers_delegate_with_a_boat_object(self):
        modal = self.body_of('function showModalById(id)')
        self.assertIn('findBoat(id)', modal)
        self.assertIn('showModal(boat)', modal)

        star = self.body_of('function onStarClickById(id, event)')
        self.assertIn('findBoat(id)', star)
        self.assertIn('onStarClick(boat, event)', star)

    def test_resolvers_guard_against_a_missing_boat(self):
        for signature in ('function showModalById(id)', 'function onStarClickById(id, event)'):
            body = self.body_of(signature)
            self.assertIn('if (boat)', body,
                          signature + ' must not call through on a null lookup')


if __name__ == '__main__':
    unittest.main()

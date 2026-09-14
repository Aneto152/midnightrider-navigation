#!/usr/bin/env python3
"""Verify that nothing the source race database knows is missing from competitors.json.

Written on 2026-09-14 after an audit showed that the 2026-09-13 enrichment had
been applied to the 114 current competitors only, leaving the 265 historical
ones without skipper, sail number, ratings, MMSI, yacht club, home port, class
fleet sizes or overall finisher counts - roughly 10 000 values silently absent.

The contract is deliberately one-directional. competitors.json may hold values
the source does not have (locally verified MMSIs, curated names). It may never
be EMPTY where the source has a value. Existing values are authoritative and
are never required to equal the source: divergences are recorded in
mmsi_conflict / mmsi_review for human review, and are asserted to be recorded.
"""
import csv
import json
import os
import re
import unicodedata
import unittest
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(REPO, 'regatta', 'sources', 'race_database_consolidated.csv')
TARGET = os.path.join(REPO, 'regatta', 'competitors.json')
FINISHED = 'FINISHED'

# Contradictions inside the source itself, acknowledged rather than hidden.
# 'deviation' carries two rows for event 50796, same division, same sail number
# USA 24, under two names ("Deviation" and "Deviation YCC") and two different
# fleet sizes (20 and 24). The fleet database holds them as two boats, c070 and
# hist-deviation. Same pattern for Valiant. Pending arbitration: merge the pairs
# or keep them distinct. Listing them here forces the decision to stay visible.
KNOWN_SOURCE_CONTRADICTIONS = {
    ('deviation', '50796', 'overall.participants'),
}


def norm(value):
    text = unicodedata.normalize('NFKD', str(value))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]', '', text.lower())


def clean(value):
    if value is None:
        return None
    text = str(value).strip().strip('\'"').strip()
    return None if text == '' or text.lower() in (
        'nan', 'none', 'nat', 'n/a', 'na', 'null', '-', 'unknown') else text


def as_int(value):
    text = clean(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


class TestNoDataLossVsSource(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(SOURCE, newline='', encoding='utf-8') as handle:
            cls.rows = list(csv.DictReader(handle))
        with open(TARGET, encoding='utf-8') as handle:
            cls.data = json.load(handle)
        cls.boats = cls.data.get('competitors', [])
        cls.by_key = {}
        for boat in cls.boats:
            boat_id = str(boat.get('id', ''))
            if boat_id.startswith('hist-'):
                cls.by_key.setdefault(boat_id[5:], boat)
            cls.by_key.setdefault(norm(boat.get('boat_name')), boat)
        cls.source_by_key = defaultdict(list)
        for row in cls.rows:
            cls.source_by_key[clean(row['Boat Key'])].append(row)

    def boat_for(self, key, rows):
        return self.by_key.get(key) or self.by_key.get(norm(rows[0]['Boat Name']))

    # ------------------------------------------------------------------ shape
    def test_single_unified_fleet(self):
        """One pool only: the current/historical split is gone."""
        self.assertNotIn('historical_competitors', self.data)
        self.assertEqual(self.data.get('schema_version'), 3)
        self.assertGreaterEqual(len(self.boats), 379)

    def test_no_boat_carries_a_historical_marker(self):
        marked = [b.get('id') for b in self.boats if 'source_status' in b]
        self.assertEqual(marked, [], 'source_status must not survive unification')

    # ----------------------------------------------------------- completeness
    def test_every_source_boat_is_present(self):
        missing = [k for k, rows in self.source_by_key.items() if self.boat_for(k, rows) is None]
        self.assertEqual(missing, [], 'source boats absent from competitors.json')

    def test_every_source_result_is_present(self):
        missing = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            # A boat can be entered in two divisions of the same event, so a
            # result is identified by (event, division), never by event alone.
            known = {(str(r.get('regatta_id')), (r.get('class') or {}).get('name'))
                     for r in (boat.get('palmares') or {}).get('results', [])}
            for row in rows:
                ident = (str(clean(row['Event ID'])), clean(row.get('Class / Division')))
                if ident not in known:
                    missing.append((key, ident))
        self.assertEqual(missing, [], 'source results absent from competitors.json')

    def test_identity_fields_never_empty_when_source_knows_them(self):
        checks = (('Owner / Skipper', 'skipper'), ('Sail Number', 'sail_number'),
                  ('Yacht Club', 'yacht_club'), ('Home Port', 'home_port'))
        empty = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            for column, field in checks:
                if any(clean(r.get(column)) for r in rows) and not clean(boat.get(field)):
                    empty.append((key, field))
        self.assertEqual(empty, [], 'fields empty although the source provides a value')

    def test_vessel_and_rating_never_empty_when_source_knows_them(self):
        empty = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            vessel = boat.get('vessel') or {}
            if any(clean(r.get('Boat Type')) for r in rows) and not vessel.get('model'):
                empty.append((key, 'vessel.model'))
            if any(clean(r.get('Length')) for r in rows) and vessel.get('length_ft') is None:
                empty.append((key, 'vessel.length_ft'))
            phrf = [r for r in rows if 'PHRF' in (clean(r.get('Rating System')) or '').upper()
                    and (clean(r.get('Published Rating')) or clean(r.get('Latest Rating')))]
            if phrf and (boat.get('ratings') or {}).get('PHRF_LIS') is None:
                empty.append((key, 'ratings.PHRF_LIS'))
        self.assertEqual(empty, [], 'vessel or rating empty although the source provides one')

    # -------------------------------------------------------------- exactness
    def test_result_numbers_match_the_source(self):
        """Values only the source provides must be reproduced exactly."""
        wrong = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            results = {(str(r.get('regatta_id')), (r.get('class') or {}).get('name')): r
                       for r in (boat.get('palmares') or {}).get('results', [])}
            for row in rows:
                got = results.get((str(clean(row['Event ID'])), clean(row.get('Class / Division'))))
                self.assertIsNotNone(got, 'missing result {} {}'.format(key, row['Event ID']))
                overall = got.get('overall') or {}
                pairs = (
                    ('overall.position', overall.get('position'), as_int(row.get('Overall Fleet Rank'))),
                    ('overall.participants', overall.get('participants'), as_int(row.get('Overall Fleet Size'))),
                    ('overall.finishers', overall.get('finishers'), as_int(row.get('Overall Fleet Finishers'))),
                    ('class.position', (got.get('class') or {}).get('position'), as_int(row.get('Class Rank'))),
                    ('status', clean(got.get('status')), clean(row.get('Result Status'))),
                    ('year', got.get('year'), as_int(row.get('Year'))),
                )
                for label, mine, theirs in pairs:
                    if theirs is None or mine == theirs:
                        continue
                    if (key, clean(row['Event ID']), label) in KNOWN_SOURCE_CONTRADICTIONS:
                        continue
                    wrong.append((key, clean(row['Event ID']), label, mine, theirs))
        self.assertEqual(wrong[:20], [], '{} result values diverge from the source'.format(len(wrong)))

    def test_class_fleet_sizes_are_derived_everywhere(self):
        """Class entrants and finishers are counted from the source, per event."""
        sizes = defaultdict(lambda: [set(), set()])
        for row in self.rows:
            division = clean(row.get('Class / Division'))
            if not division:
                continue
            slot = sizes[(clean(row['Event ID']), division)]
            slot[0].add(clean(row['Boat Key']))
            if (clean(row.get('Result Status')) or '').upper() == FINISHED:
                slot[1].add(clean(row['Boat Key']))
        wrong = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            results = {(str(r.get('regatta_id')), (r.get('class') or {}).get('name')): r
                       for r in (boat.get('palmares') or {}).get('results', [])}
            for row in rows:
                division = clean(row.get('Class / Division'))
                if not division:
                    continue
                entrants, finishers = sizes[(clean(row['Event ID']), division)]
                block = (results.get((str(clean(row['Event ID'])), division)) or {}).get('class') or {}
                if block.get('participants') != len(entrants) or block.get('finishers') != len(finishers):
                    wrong.append((key, clean(row['Event ID']), block.get('participants'), len(entrants),
                                  block.get('finishers'), len(finishers)))
        self.assertEqual(wrong[:20], [], '{} class fleet sizes are wrong or missing'.format(len(wrong)))

    def test_times_present_when_the_source_has_them(self):
        missing = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            results = {(str(r.get('regatta_id')), (r.get('class') or {}).get('name')): r
                       for r in (boat.get('palmares') or {}).get('results', [])}
            for row in rows:
                times = (results.get((str(clean(row['Event ID'])), clean(row.get('Class / Division')))) or {}).get('times') or {}
                for column, field in (('Corrected Time', 'corrected'), ('Elapsed Time', 'elapsed'),
                                      ('Finish Time', 'finish')):
                    if clean(row.get(column)) and not clean(times.get(field)):
                        missing.append((key, clean(row['Event ID']), field))
        self.assertEqual(missing[:20], [], '{} race times missing'.format(len(missing)))

    # -------------------------------------------------------------- integrity
    def test_every_mmsi_divergence_is_recorded(self):
        """An existing MMSI is never overwritten, but a divergence must be traceable."""
        unrecorded = []
        for key, rows in self.source_by_key.items():
            boat = self.boat_for(key, rows)
            raw = clean(rows[-1].get('Best Available MMSI')) or clean(rows[-1].get('AIS MMSI'))
            if not raw:
                continue
            candidates = [c.strip() for c in re.split(r'[;,]', raw) if c.strip()]
            current = clean(boat.get('mmsi'))
            if current and current not in candidates and not boat.get('mmsi_conflict'):
                unrecorded.append((key, current, candidates))
            if not current and len(candidates) > 1 and not boat.get('mmsi_review'):
                unrecorded.append((key, None, candidates))
        self.assertEqual(unrecorded, [], 'MMSI divergences not recorded for review')

    def test_ais_metadata_present_for_matched_boats(self):
        missing = []
        for key, rows in self.source_by_key.items():
            if any(clean(r.get('AIS MMSI')) for r in rows) and not self.boat_for(key, rows).get('ais'):
                missing.append(key)
        self.assertEqual(missing, [], 'AIS metadata missing for boats matched in the source')


if __name__ == '__main__':
    unittest.main()

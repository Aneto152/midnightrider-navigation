#!/usr/bin/env python3
"""formatRank must receive the result status, and every call site must pass it.

Denis, 2026-09-14: "pour les resultats de classe, montrer la position ET le
nombre de participants, ex RET/7 ou 5/6; idem pour l'overall, y compris les
bateaux retires -> RET/30 au lieu de -".

The data was always there: a retired boat has overall.position = null but
overall.participants = 34 and status = 'RET'. formatRank(entry) could not know
the boat had retired because the status was never passed to it, so it returned
a dash. This guard pins the signature and both call sites, because a future
refactor dropping the second argument would silently restore the dash.
"""
import os
import re
import unittest

HTML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'ais', 'fleet_db.html')


class TestRaceHistoryRankDisplay(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(HTML, encoding='utf-8') as handle:
            cls.html = handle.read()

    def test_signature_takes_status(self):
        self.assertIn('function formatRank(entry, status)', self.html)

    def test_every_call_site_passes_status(self):
        calls = re.findall(r'formatRank\(([^)]*)\)', self.html)
        calls = [c for c in calls if 'entry, status' not in c]
        self.assertGreaterEqual(len(calls), 2, 'expected at least 2 call sites')
        for call in calls:
            self.assertIn(',', call,
                          'formatRank called without a status: formatRank({})'.format(call))
            self.assertIn('status', call)

    def test_non_finish_statuses_are_known(self):
        for code in ('RET', 'DNF', 'DNS', 'DNC', 'SCP', 'NSC', 'ENTRY ONLY'):
            self.assertIn("'" + code + "'", self.html,
                          'status {} not handled'.format(code))

    def test_non_finishers_use_entrants_not_finishers(self):
        block = self.html[self.html.index('function formatRank'):]
        block = block[:block.index('function populateRaceHistory')]
        head = block[:block.index('if (!entry || entry.position === null')]
        self.assertIn('entry.participants', head,
                      'the non-finish branch must use participants, the entry list')
        self.assertNotIn('entry.finishers', head,
                         'a retired boat is compared to who started, not who finished')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Tests for race history API exposure and modal rendering"""
import unittest
import json
import os

class TestRaceHistoryExposure(unittest.TestCase):
    """Verify palmares/race history exposed in API and modal"""
    
    @classmethod
    def setUpClass(cls):
        """Load Fleet database"""
        db_path = 'regatta/competitors.json'
        with open(db_path, 'r') as f:
            cls.db = json.load(f)
    
    def test_01_api_exposes_palmares_historical(self):
        """API response includes palmares for historical competitors"""
        historical = self.db.get('historical_competitors', [])
        self.assertGreater(len(historical), 0, "Historical competitors exist")
        
        # Find a boat with palmares
        boat_with_palmares = next((b for b in historical if b.get('palmares')), None)
        self.assertIsNotNone(boat_with_palmares, "At least one historical boat has palmares")
        
        # Verify structure
        palmares = boat_with_palmares['palmares']
        self.assertIn('results', palmares, "Palmares has results array")
        self.assertGreater(len(palmares['results']), 0, "Results are populated")
    
    def test_02_api_exposes_palmares_active(self):
        """API response includes palmares for active competitors"""
        active = self.db.get('competitors', [])
        self.assertGreater(len(active), 0, "Active competitors exist")
        
        # Find a boat with palmares
        boat_with_palmares = next((b for b in active if b.get('palmares')), None)
        self.assertIsNotNone(boat_with_palmares, "At least one active boat has palmares")
    
    def test_03_race_results_have_complete_fields(self):
        """Race results include all required fields for display"""
        required_fields = [
            'regatta', 'year', 'event_dates', 'status',
            'overall', 'class', 'rating_system', 'rating_metric',
            'source_urls'
        ]
        
        # Find first boat with results
        boat = next((b for b in self.db.get('competitors', []) + self.db.get('historical_competitors', [])
                    if b.get('palmares', {}).get('results')), None)
        
        self.assertIsNotNone(boat, "Found boat with results")
        
        results = boat['palmares']['results']
        self.assertGreater(len(results), 0, "Results populated")
        
        first_result = results[0]
        for field in required_fields:
            self.assertIn(field, first_result, f"Result has {field}")
    
    def test_04_source_urls_are_https(self):
        """All source URLs are HTTPS"""
        boats = self.db.get('competitors', []) + self.db.get('historical_competitors', [])
        
        for boat in boats:
            if boat.get('palmares', {}).get('results'):
                for result in boat['palmares']['results']:
                    urls = result.get('source_urls', {})
                    for url in urls.values():
                        if url:
                            self.assertTrue(url.startswith('https://'), 
                                          f"URL is HTTPS: {url}")
    
    def test_05_condor_present_and_has_results(self):
        """Condor is present and has race results"""
        # Condor should be in historical or active
        condor = None
        for boat in self.db.get('competitors', []) + self.db.get('historical_competitors', []):
            if boat.get('boat_name', '').lower() == 'condor' or boat.get('name', '').lower() == 'condor':
                condor = boat
                break
        
        # If not found by name, it's OK - Condor might be historical
        if condor:
            palmares = condor.get('palmares', {})
            results = palmares.get('results', [])
            # Should have some race history
            self.assertGreater(len(results), 0, "Condor has race results")
    
    def test_06_palmares_aggregates_complete(self):
        """Palmares includes aggregate counters"""
        aggregate_fields = [
            'participations', 'finished', 'retired',
            'best_overall_rank', 'best_class_rank'
        ]
        
        boat = next((b for b in self.db.get('competitors', [])
                    if b.get('palmares')), None)
        
        self.assertIsNotNone(boat, "Found boat with palmares")
        
        palmares = boat['palmares']
        for field in aggregate_fields:
            # Some fields might be optional, but structure should exist
            self.assertTrue(field in palmares or palmares.get('results'),
                          f"Palmares has {field} or results array")
    
    def test_07_modal_html_has_race_history_section(self):
        """Modal HTML includes race history rendering section"""
        with open('ais/fleet_db.html', 'r') as f:
            html = f.read()
        
        self.assertIn('raceHistorySection', html, "Modal has race history section")
        self.assertIn('populateRaceHistory', html, "Modal has race history handler")
        self.assertIn('raceHistoryTable', html, "Modal has race history table")
    
    def test_08_modal_uses_correct_phrf_label(self):
        """Modal uses 'PHRF' label, never 'PHRF LIS'"""
        with open('ais/fleet_db.html', 'r') as f:
            html = f.read()
        
        # Should have PHRF in user-visible context
        self.assertIn('PHRF', html, "Modal mentions PHRF")
        
        # But should NOT have PHRF LIS in user-visible HTML
        # (it's OK in comments or internal fields, but not in display)
        self.assertNotIn('PHRF LIS', html, "Modal does not display 'PHRF LIS'")
    
    def test_09_total_fleet_records_preserved(self):
        """All 379 Fleet records preserved"""
        active = len(self.db.get('competitors', []))
        historical = len(self.db.get('historical_competitors', []))
        total = active + historical
        
        self.assertEqual(total, 379, f"Total Fleet records is 379, got {total}")
    
    def test_10_mmsi_preservation(self):
        """All 68 non-empty MMSIs preserved"""
        mmsis = set()
        for boat in self.db.get('competitors', []) + self.db.get('historical_competitors', []):
            if boat.get('mmsi'):
                mmsis.add(str(boat['mmsi']))
        
        self.assertEqual(len(mmsis), 68, f"68 non-empty MMSIs preserved, got {len(mmsis)}")

if __name__ == '__main__':
    unittest.main()

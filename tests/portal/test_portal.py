#!/usr/bin/env python3
"""Unit tests for the portal module."""
import unittest, os, re, json

BASE = os.path.join(os.path.dirname(__file__), '..', '..'), '..', '..')

def read(rel): 
    with open(os.path.join(BASE, rel)) as f: return f.read()

def exists(rel):
    return os.path.isfile(os.path.join(BASE, rel))


class TestNightModeCss(unittest.TestCase):
    def setUp(self): self.css = read('portal/static/css/night-mode.css')
    def test_file_exists(self):
        self.assertTrue(exists('portal/static/css/night-mode.css'))
    def test_css_variables_defined(self):
        self.assertIn(':root', self.css)
        for var in ['--bg-base', '--bg-card', '--text-primary', '--accent-cyan',
                    '--accent-green', '--accent-red', '--font-sans', '--radius-md']:
            self.assertIn(var, self.css)
    def test_shared_components_present(self):
        for cls in ['.mr-nav', '.mr-card', '.mr-btn', '.mr-badge', '.mr-spinner', '.mr-input']:
            self.assertIn(cls, self.css)


class TestViewerHtml(unittest.TestCase):
    def setUp(self): self.html = read('portal/viewer.html')
    def test_file_exists(self):
        self.assertTrue(exists('portal/viewer.html'))
    def test_html5_doctype(self):
        self.assertTrue(self.html.strip().startswith('<!DOCTYPE html>'))
    def test_lang_en(self):
        self.assertIn('lang="en"', self.html)
    def test_uses_shared_css(self):
        self.assertIn('/static/css/night-mode.css', self.html)
    def test_iframe_present(self):
        self.assertIn('<iframe', self.html)
        self.assertIn('id="grafana-frame"', self.html)
    def test_back_to_portal_link(self):
        self.assertIn('href="/"', self.html)


class TestIndexHtml(unittest.TestCase):
    def setUp(self): self.html = read('portal/index.html')
    def test_file_exists(self):
        self.assertTrue(exists('portal/index.html'))
    def test_html5_doctype(self):
        self.assertTrue(self.html.strip().startswith('<!DOCTYPE html>'))
    def test_ais_tracker_card(self):
        self.assertIn('/ais/', self.html)
    def test_fleet_db_card(self):
        self.assertIn('/ais/fleet_db', self.html)
    def test_reporter_card(self):
        self.assertIn('/reporter', self.html)


class TestReporterHtml(unittest.TestCase):
    def setUp(self): self.html = read('portal/reporter.html')
    def test_file_exists(self):
        self.assertTrue(exists('portal/reporter.html'))
    def test_lang_en(self):
        self.assertIn('lang="en"', self.html)
    def test_uses_shared_css(self):
        self.assertIn('/static/css/night-mode.css', self.html)
    def test_no_french_text(self):
        french = ['Générer', 'Derniers flashs', 'Aucun flash']
        for word in french:
            self.assertNotIn(word, self.html)


class TestServerPy(unittest.TestCase):
    def setUp(self): self.src = read('portal/server.py')
    def test_file_exists(self):
        self.assertTrue(exists('portal/server.py'))
    def test_threading_mixin(self):
        self.assertIn('ThreadingMixIn', self.src)
    def test_logging_setup(self):
        self.assertIn('RotatingFileHandler', self.src)
        self.assertIn('portal.log', self.src)
    def test_sandbox_checks(self):
        self.assertIn('ALLOWED', self.src)


class TestManifest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(BASE, 'portal/static/manifest.json')) as f:
            self.m = json.load(f)
    def test_file_exists(self):
        self.assertTrue(exists('portal/static/manifest.json'))
    def test_icon_path_correct(self):
        icons = self.m.get('icons', [])
        self.assertTrue(any('/midnight-rider-icon.svg' == i.get('src') for i in icons))
    def test_theme_color_dark(self):
        self.assertEqual(self.m.get('theme_color'), '#0a1628')


class TestGrafanaConfig(unittest.TestCase):
    def setUp(self): self.ini = read('config/grafana-custom.ini')
    def test_allow_embedding(self):
        self.assertIn('allow_embedding = true', self.ini)
    def test_min_refresh_1s(self):
        self.assertIn('min_refresh_interval = 1s', self.ini)


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""MCP module tests"""
import unittest, os, re, json

BASE = os.path.join(os.path.dirname(__file__), '..', '..'), '..', '..')
MCP = os.path.join(BASE, 'mcp')

def exists(rel): return os.path.isfile(os.path.join(BASE, rel))
def read(rel):
    with open(os.path.join(BASE, rel)) as f: return f.read()

class TestMcpStructure(unittest.TestCase):
    def test_servers_dir(self): self.assertTrue(os.path.isdir(os.path.join(MCP, 'servers')))
    def test_lib_dir(self): self.assertTrue(os.path.isdir(os.path.join(MCP, 'lib')))
    def test_all_servers(self):
        for s in ['astronomical.js', 'buoy.js', 'competitor.js', 'crew.js',
                  'electrical.js', 'imu.js', 'polar.js', 'race.js', 'racing.js', 'system.js', 'weather.js']:
            self.assertTrue(os.path.isfile(os.path.join(MCP, 'servers', s)))
    def test_no_old_servers(self):
        old = [f for f in os.listdir(MCP) if f.endswith('-server.js')]
        self.assertEqual(old, [])
    def test_no_stale_packages(self):
        stale = [f for f in os.listdir(MCP) if f.endswith('-package.json')]
        self.assertEqual(stale, [])
    def test_readme(self): self.assertTrue(exists('mcp/README.md'))
    def test_package_json(self): self.assertTrue(exists('mcp/package.json'))
    def test_dockerfile(self): self.assertTrue(exists('mcp/Dockerfile'))

class TestCompetitor(unittest.TestCase):
    def setUp(self): self.src = read('mcp/servers/competitor.js')
    def test_no_direct_influx(self): self.assertNotIn('/api/v2/query', self.src)
    def test_calls_ais_api(self): self.assertIn('/api/competitors', self.src)
    def test_tools_preserved(self):
        for t in ['get_competitor_fleet', 'get_nearest_competitor', 'get_fleet_pressure', 'get_fleet_summary', 'find_competitor']:
            self.assertIn(t, self.src)
    def test_no_hardcoded_ip(self): self.assertEqual(re.findall(r'192\.168\.\d+\.\d+', self.src), [])

class TestSharedLib(unittest.TestCase):
    def setUp(self): self.src = read('mcp/lib/influx.js')
    def test_bucket_midnight_rider(self): self.assertIn("'midnight_rider'", self.src)
    def test_exports(self): self.assertIn('queryInflux', self.src)

class TestPackage(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(MCP, 'package.json')) as f: self.pkg = json.load(f)
    def test_all_servers_listed(self):
        servers = self.pkg.get('servers', {})
        for name in ['astronomical', 'buoy', 'competitor', 'crew', 'electrical', 'imu', 'polar', 'race', 'racing', 'system', 'weather']:
            self.assertIn(name, servers)

class TestPortalMcp(unittest.TestCase):
    def test_mcp_html(self): self.assertTrue(exists('portal/mcp.html'))
    def test_mcp_uses_css(self): self.assertIn('/static/css/night-mode.css', read('portal/mcp.html'))
    def test_mcp_route(self): self.assertIn('/mcp', read('portal/server.py'))

if __name__ == '__main__':
    unittest.main(verbosity=2)

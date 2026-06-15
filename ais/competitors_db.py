#!/usr/bin/env python3
"""competitors_db.py - Competitor DB manager - Midnight Rider"""
import json, os, time, threading

_P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  '..', 'regatta', 'competitors.json')

class CompetitorDB:
    TTL = 300
    def __init__(self, path=_P):
        self._p = os.path.abspath(path)
        self._lk = threading.Lock()
        self._d = []; self._bm = {}; self._ts = 0.0
        self._load()

    def _load(self):
        try:
            with open(self._p) as f:
                raw = json.load(f)
            bm = {}
            for c in raw.get('competitors', []):
                m = c.get('ais', {}).get('mmsi') or c.get('mmsi')
                if m: bm[str(m)] = c
            with self._lk:
                self._d = raw.get('competitors', [])
                self._bm = bm
                self._ts = time.time()
        except Exception as e:
            print(f"[CompetitorDB] {e}")

    def _r(self):
        if time.time() - self._ts > self.TTL: self._load()

    def get_by_mmsi(self, mmsi):
        self._r(); return self._bm.get(str(mmsi))

    def get_all_active(self):
        self._r()
        with self._lk: return [c for c in self._d if c.get('active', True)]

    def get_all(self):
        self._r()
        with self._lk: return list(self._d)

    def get_all_active_mmsis(self):
        return {str(c.get('ais', {}).get('mmsi') or c.get('mmsi', ''))
                for c in self.get_all_active()
                if c.get('ais', {}).get('mmsi') or c.get('mmsi')}

    def search(self, q):
        self._r(); q = q.lower().strip()
        if not q: return self.get_all()
        with self._lk:
            return [c for c in self._d if any(q in str(v).lower() for v in [
                c.get('boat_name', ''), c.get('sail_number', ''),
                str(c.get('ais', {}).get('mmsi') or c.get('mmsi', '')),
                c.get('vessel', {}).get('model', ''),
                c.get('vessel', {}).get('make', '')])]

    def enrich(self, c):
        v = c.get('vessel', {}); r = c.get('ratings', {})
        pr = r.get('PHRF_LIS')
        phrf = (pr.get('value') if isinstance(pr, dict)
                else pr if isinstance(pr, (int, float)) else None)
        irc = r.get('IRC', {})
        tcc = irc.get('TCC') if isinstance(irc, dict) else None
        return {
            'id': c.get('id', ''), 'active': c.get('active', True),
            'name': c.get('boat_name', ''), 'sail_num': c.get('sail_number', ''),
            'skipper': c.get('skipper', ''),
            'boat_class': f"{v.get('make','')} {v.get('model','')}".strip(),
            'mmsi': str(c.get('ais', {}).get('mmsi') or c.get('mmsi') or ''),
            'phrf_lis': phrf, 'irc_tcc': tcc,
            'priority': c.get('priority', 'medium'),
            'events': c.get('events', []),
        }

    def get_meta(self):
        try:
            with open(self._p) as f: return json.load(f).get('_meta', {})
        except: return {}

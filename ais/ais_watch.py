#!/usr/bin/env python3
"""ais_watch.py - AIS daemon - Midnight Rider. Logs: logs/services/ais-watch.log"""
import json, math, time, os, sys, logging, urllib.request
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ais_lib import (haversine_ll, bearing_ll, compute_twa, compute_vmg_wind,
                     compute_vmg_mark, make_history_store, record_position, compute_delta)
from competitors_db import CompetitorDB

SK   = os.getenv('SIGNALK_HTTP', 'http://localhost:3000')
INF  = os.getenv('INFLUX_URL',   'http://localhost:8086')
ORG  = os.getenv('INFLUX_ORG',   'MidnightRider')
BCK  = os.getenv('INFLUX_BUCKET','midnight_rider')
POLL = int(os.getenv('AIS_POLL_S', '30'))

def _setup_logger():
    d = '/home/aneto/midnightrider-navigation/logs/services'
    os.makedirs(d, exist_ok=True)
    lg = logging.getLogger('ais-watch')
    lg.setLevel(logging.DEBUG)
    if not lg.handlers:
        h = RotatingFileHandler(f'{d}/ais-watch.log', maxBytes=5*1024*1024, backupCount=3)
        h.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S'))
        lg.addHandler(h)
        lg.addHandler(logging.StreamHandler(sys.stdout))
    return lg

log = _setup_logger()

def sk(path):
    try:
        with urllib.request.urlopen(f"{SK}/signalk/v1/api/{path}", timeout=5) as r:
            return json.loads(r.read())
    except: return None

def age_s(ts):
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except: return 999

def influx_write(lines):
    tok = os.getenv('INFLUX_TOKEN', '')
    if not tok: log.warning("INFLUX_TOKEN not set"); return
    url = f"{INF}/api/v2/write?org={ORG}&bucket={BCK}&precision=s"
    req = urllib.request.Request(url, '\n'.join(lines).encode(), method='POST')
    req.add_header('Authorization', f'Token {tok}')
    req.add_header('Content-Type', 'text/plain')
    try: urllib.request.urlopen(req, timeout=5)
    except Exception as e: log.error(f"InfluxDB: {e}")

_MPATHS = [
    'vessels/self/navigation/courseGreatCircle/nextPoint/position',
    'vessels/self/navigation/courseRhumbline/nextPoint/position',
]
_mc = {'lat': None, 'lon': None, 'ts': 0}
_wc = {'v': None, 'ts': 0}

def get_mark():
    if time.time() - _mc['ts'] < 30: return _mc
    for p in _MPATHS:
        d = sk(p)
        if d and d.get('value'):
            v = d['value']
            if v.get('latitude'):
                _mc.update({'lat': v['latitude'], 'lon': v['longitude'], 'ts': time.time()})
                return _mc
    return _mc

def get_twd():
    if time.time() - _wc['ts'] < 10 and _wc['v']: return _wc['v']
    d = sk('vessels/self/environment/wind/directionTrue')
    if d and d.get('value') is not None:
        v = math.degrees(d['value']) % 360
        _wc.update({'v': v, 'ts': time.time()})
        return v
    return _wc['v']

def main():
    log.info(f"STARTUP ais-watch poll={POLL}s SK={SK}")
    db   = CompetitorDB()
    hist = make_history_store()
    act  = db.get_all_active_mmsis()
    log.info(f"Loaded {len(act)} active MMSIs")
    i = 0
    while True:
        i += 1
        ts = int(time.time())
        if i % 10 == 0: log.info(f"HEARTBEAT i={i}")
        n0 = sk('vessels/self/navigation') or {}
        p0 = (n0.get('position') or {}).get('value', {})
        la0, lo0 = p0.get('latitude'), p0.get('longitude')
        if not la0:
            log.warning("No own position")
            time.sleep(POLL)
            continue
        s0  = ((n0.get('speedOverGround', {}).get('value') or 0)) * 1.94384
        c0  = math.degrees(n0.get('courseOverGroundTrue', {}).get('value') or 0)
        twd = get_twd()
        mk  = get_mark()
        mb0 = bearing_ll(la0, lo0, mk['lat'], mk['lon']) if mk.get('lat') else None
        ta0 = compute_twa(c0, twd) if twd else None
        v0  = compute_vmg_wind(s0, ta0) if ta0 is not None else None
        vs  = sk('vessels') or {}
        lines = []
        matched = 0
        for key, vessel in vs.items():
            if not isinstance(vessel, dict) or 'self' in key: continue
            mmsi = ''.join(filter(str.isdigit, key))
            if not mmsi or mmsi not in act: continue
            nv  = vessel.get('navigation', {})
            pd  = nv.get('position', {})
            pv  = (pd.get('value', {}) if isinstance(pd, dict) else {})
            la, lo = pv.get('latitude'), pv.get('longitude')
            if not la: continue
            sog = ((nv.get('speedOverGround', {}).get('value') or 0)) * 1.94384
            cog = math.degrees(nv.get('courseOverGroundTrue', {}).get('value') or 0)
            ag  = age_s(pd.get('timestamp', '') if isinstance(pd, dict) else '')
            dm  = haversine_ll(la0, lo0, la, lo)
            dn  = dm / 1852
            brg = bearing_ll(la0, lo0, la, lo)
            record_position(hist, mmsi, dm, brg)
            twa = compute_twa(cog, twd) if twd else None
            vw  = compute_vmg_wind(sog, twa) if twa is not None else None
            mb  = bearing_ll(la, lo, mk['lat'], mk['lon']) if mk.get('lat') else None
            vm  = compute_vmg_mark(sog, cog, mb) if mb else None
            cp  = db.get_by_mmsi(mmsi)
            e   = db.enrich(cp) if cp else {}
            cid = e.get('id', mmsi)
            cn  = (e.get('name', mmsi) or mmsi).replace(' ', '_')
            ph  = e.get('phrf_lis') or 0
            pr  = e.get('priority', 'medium')
            tags  = f"competitor_id={cid},boat_name={cn},mmsi={mmsi},priority={pr}"
            flds  = (f"dist_m={dm:.1f},dist_nm={dn:.3f},bearing_true={brg:.1f},"
                     f"lat={la},lon={lo},sog_kts={sog:.2f},cog_true={cog:.1f},"
                     f"phrf_lis={ph}i,ais_age_s={ag}i")
            if twd:                  flds += f",twd_deg={twd:.1f}"
            if twa is not None:      flds += f",twa_deg={twa:.1f}"
            if vw  is not None:      flds += f",vmg_wind_kts={vw:.3f}"
            if vm  is not None:      flds += f",vmg_mark_kts={vm:.3f}"
            if v0  is not None:      flds += f",vmg_mr_kts={v0:.3f}"
            lines.append(f"competitor_tracking,{tags} {flds} {ts}")
            matched += 1
        if lines: influx_write(lines)
        log.info(f"[{i}] {matched}/{len(act)} tracked")
        time.sleep(POLL)

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: log.info("SHUTDOWN")

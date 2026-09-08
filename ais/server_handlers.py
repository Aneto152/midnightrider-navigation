#!/usr/bin/env python3
"""server_handlers.py - /api/competitors + /api/fleet_db handlers - Midnight Rider"""
import math, time
from ais_lib import (haversine_ll, bearing_ll, compute_twa, compute_vmg_wind,
                     compute_vmg_mark, make_history_store, record_position,
                     compute_delta, is_gaining_ground)
from competitors_db import CompetitorDB

_cdb  = CompetitorDB('/repo/regatta/competitors.json')
_hist = make_history_store()
_mc   = {'lat': None, 'lon': None, 'ts': 0}
_wc   = {'v': None, 'ts': 0}
_MPATHS = [
    'vessels/self/navigation/courseGreatCircle/nextPoint/position',
    'vessels/self/navigation/courseRhumbline/nextPoint/position',
]

def _twd(sk_fn):
    """True Wind Direction with apparent wind fallback."""
    if time.time() - _wc['ts'] < 10 and _wc['v']: return _wc['v']
    d = sk_fn('vessels/self/environment/wind/directionTrue')
    if d and d.get('value') is not None:
        v = math.degrees(d['value']) % 360
        _wc.update({'v': v, 'ts': time.time()})
        return v
    return _wc['v']

def _awa_aws(sk_fn):
    """Apparent Wind Angle & Speed for fallback display."""
    awa_d = sk_fn('vessels/self/environment/wind/angleApparent')
    aws_d = sk_fn('vessels/self/environment/wind/speedApparent')
    awa = round(math.degrees(awa_d['value']), 1) if awa_d and awa_d.get('value') is not None else None
    aws = round(aws_d['value'] * 1.94384, 1) if aws_d and aws_d.get('value') is not None else None
    return awa, aws

def _mark(sk_fn):
    if time.time() - _mc['ts'] < 30: return _mc
    for p in _MPATHS:
        d = sk_fn(p)
        if d and d.get('value'):
            v = d['value']
            if v.get('latitude'):
                _mc.update({'lat': v['latitude'], 'lon': v['longitude'], 'ts': time.time()})
                return _mc
    return _mc

def api_competitors(sk_fn, gps_fn, radius=10.0, min_sog=0.0, inc_unk=False, vmode='wind'):
    pos = gps_fn()
    la0, lo0 = pos.get('lat'), pos.get('lon')
    if not la0: return {'error': 'no_position', 'competitors': []}
    n0  = sk_fn('vessels/self/navigation') or {}
    s0  = ((n0.get('speedOverGround', {}).get('value') or 0)) * 1.94384
    c0  = math.degrees(n0.get('courseOverGroundTrue', {}).get('value') or 0)
    tw  = _twd(sk_fn)
    mk  = _mark(sk_fn)
    ta0 = compute_twa(c0, tw) if tw else None
    v0  = compute_vmg_wind(s0, ta0) if ta0 is not None else None
    mb0 = bearing_ll(la0, lo0, mk['lat'], mk['lon']) if mk.get('lat') else None
    v0m = compute_vmg_mark(s0, c0, mb0) if mb0 else None
    tws_d = sk_fn('vessels/self/environment/wind/speedTrue')
    tws = (tws_d['value'] * 1.94384) if tws_d and tws_d.get('value') is not None else None
    if tws is None:  # fallback to apparent wind speed (Calypso)
        tws_ap = sk_fn('vessels/self/environment/wind/speedApparent')
        if tws_ap and tws_ap.get('value') is not None:
            tws = tws_ap['value'] * 1.94384
    act = _cdb.get_all_active_mmsis()
    vs  = sk_fn('vessels') or {}
    result = []
    for key, vessel in vs.items():
        if not isinstance(vessel, dict) or 'self' in key: continue
        mmsi = ''.join(filter(str.isdigit, key))
        if not mmsi: continue
        indb = (mmsi in act)
        # Vessel type filter: show sailing (36-39), unknown (0), or DB vessels
        _vt = vessel.get('design', {}).get('aisShipType', {}).get('value', {})
        vtype_id = (_vt.get('id', 0) if isinstance(_vt, dict) else (int(_vt) if _vt else 0))
        is_sailing = (vtype_id == 0 or 36 <= vtype_id <= 39)
        if not indb and not is_sailing:
            continue  # skip confirmed non-sailing vessels (cargo, tankers)
        nv = vessel.get('navigation', {})
        pd = nv.get('position', {})
        pv = (pd.get('value', {}) if isinstance(pd, dict) else {})
        la, lo = pv.get('latitude'), pv.get('longitude')
        if not la: continue
        sog = ((nv.get('speedOverGround', {}).get('value') or 0)) * 1.94384
        if sog < min_sog: continue
        cog = math.degrees(nv.get('courseOverGroundTrue', {}).get('value') or 0)
        dm  = haversine_ll(la0, lo0, la, lo)
        dn  = dm / 1852
        if dn > radius: continue
        brg = bearing_ll(la0, lo0, la, lo)
        record_position(_hist, mmsi, dm, brg)
        twa = compute_twa(cog, tw) if tw else None
        vw  = compute_vmg_wind(sog, twa) if twa is not None else None
        mb2 = bearing_ll(la, lo, mk['lat'], mk['lon']) if mk.get('lat') else None
        vm  = compute_vmg_mark(sog, cog, mb2) if mb2 else None
        dd, db2, dage = compute_delta(_hist, mmsi)
        vc   = vw  if vmode == 'wind' else vm
        v0c  = v0  if vmode == 'wind' else v0m
        color = is_gaining_ground(v0c, vc)
        ce = {}
        if indb:
            raw = _cdb.get_by_mmsi(mmsi)
            ce  = _cdb.enrich(raw) if raw else {}
        sn = vessel.get('name', mmsi)
        if isinstance(sn, dict): sn = sn.get('value', mmsi)
        result.append({
            'mmsi': mmsi, 'name': ce.get('name') or str(sn)[:25],
            'sail_num': ce.get('sail_num', ''), 'boat_class': ce.get('boat_class', ''),
            'phrf_lis': ce.get('phrf_lis'), 'irc_tcc': ce.get('irc_tcc'),
            'priority': ce.get('priority', 'medium'), 'in_comp_db': indb,
            'vessel_type_id': vtype_id,
            'lat': la, 'lon': lo, 'sog_kts': round(sog, 2), 'cog': round(cog, 1),
            'dist_nm': round(dn, 2), 'dist_m': round(dm, 1), 'bearing': round(brg, 1),
            'twd': round(tw, 1) if tw else None,
            'twa': round(twa, 1) if twa else None,
            'vmg_wind_kts': round(vw, 3) if vw is not None else None,
            'vmg_mark_kts': round(vm, 3) if vm is not None else None,
            'delta_dist_m': dd, 'delta_brg_deg': db2, 'delta_window_min': dage,
            'color': color,
        })
    result.sort(key=lambda c: -(c.get('vmg_wind_kts' if vmode == 'wind' else 'vmg_mark_kts') or -999))
    return {
        'ts': int(time.time()),
        'self': {
            'lat': la0, 'lon': lo0, 'sog_kts': round(s0, 2), 'cog': round(c0, 1),
            'twa': round(ta0, 1) if ta0 else None,
            'vmg_wind_kts': round(v0, 3) if v0 else None,
            'vmg_mark_kts': round(v0m, 3) if v0m else None,
        },
        'wind': dict(
            twd=round(tw, 1) if tw else None,
            tws_kts=round(tws, 1) if tws else None,
            available=tw is not None,
            **({'awa': _awa_aws(sk_fn)[0], 'aws_kts': _awa_aws(sk_fn)[1]} if tw is None else {})
        ),
        'mark': {
            'lat': mk.get('lat'), 'lon': mk.get('lon'),
            'dist_nm': round(haversine_ll(la0, lo0, mk['lat'], mk['lon']) / 1852, 2) if mk.get('lat') else None,
            'bearing_from_self': round(mb0, 1) if mb0 else None,
            'available': bool(mk.get('lat')),
        },
        'vmg_mode': vmode, 'competitors': result, 'matched': len(result),
    }

def api_fleet_db(sk_fn):
    vs   = sk_fn('vessels') or {}
    live = {}
    from datetime import datetime, timezone
    for key, v in vs.items():
        if 'self' in key or not isinstance(v, dict): continue
        mmsi = ''.join(filter(str.isdigit, key))
        if not mmsi: continue
        pd = v.get('navigation', {}).get('position', {})
        ts = (pd.get('timestamp', '') if isinstance(pd, dict) else '')
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            live[mmsi] = int((datetime.now(timezone.utc) - dt).total_seconds())
        except: live[mmsi] = 999
    result = []
    for c in _cdb.get_all():
        e    = _cdb.enrich(c)
        mmsi = e['mmsi']
        a    = live.get(mmsi)
        e['ais_status'] = ('absent' if a is None else
                           'live'   if a < 60   else
                           'stale'  if a < 300  else 'old')
        e['ais_age_s'] = a
        result.append(e)
    return {
        'ts': int(time.time()),
        'meta': _cdb.get_meta(),
        'total': len(result),
        'active': sum(1 for e in result if e.get('active')),
        'competitors': result,
    }

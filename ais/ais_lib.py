#!/usr/bin/env python3
"""ais_lib.py - AIS math library - Midnight Rider Navigation System"""
import math, collections, time

def haversine_ll(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def bearing_ll(lat1, lon1, lat2, lon2):
    """True bearing 0-360 from point1 to point2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1)*math.sin(p2) - math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def compute_twa(cog_deg, twd_deg):
    """True Wind Angle +/-180. Positive=stbd, negative=port."""
    return ((cog_deg - twd_deg + 180) % 360) - 180

def compute_vmg_wind(sog_kts, twa_deg):
    """VMG toward wind (knots). Positive=upwind."""
    return sog_kts * math.cos(math.radians(twa_deg))

def compute_vmg_mark(sog_kts, cog_deg, brg_to_mark_deg):
    """VMG toward next mark (knots)."""
    angle = ((cog_deg - brg_to_mark_deg + 180) % 360) - 180
    return sog_kts * math.cos(math.radians(angle))

def make_history_store():
    """Returns defaultdict of deques for 30-min position history."""
    return collections.defaultdict(lambda: collections.deque(maxlen=80))

def record_position(store, mmsi, dist_m, bearing_deg):
    """Append (timestamp, dist_m, bearing_deg) to MMSI history."""
    store[str(mmsi)].append((time.time(), dist_m, bearing_deg))

def compute_delta(store, mmsi, window_s=1800):
    """Delta vs ~30min ago. Returns (delta_dist_m, delta_brg_deg, age_min)."""
    hist = store.get(str(mmsi))
    if not hist or len(hist) < 2:
        return None, None, None
    now = time.time()
    ref = None
    best = float('inf')
    for e in hist:
        d = abs(e[0] - (now - window_s))
        if d < best and (now - e[0]) >= window_s * 0.6:
            best = d
            ref = e
    if ref is None:
        ref = hist[0]
    dd = round(hist[-1][1] - ref[1], 1)
    db = round(((hist[-1][2] - ref[2] + 180) % 360) - 180, 1)
    return dd, db, round((now - ref[0]) / 60, 1)

def is_gaining_ground(vmg_mr, vmg_comp):
    """
    Color logic: GREEN = gaining ground (VMG_MR > VMG_comp).
                 RED   = losing ground  (VMG_comp > VMG_MR).
    """
    if vmg_mr is None or vmg_comp is None:
        return 'neutral'
    if vmg_mr - vmg_comp > 0.05:
        return 'green'
    if vmg_comp - vmg_mr > 0.05:
        return 'red'
    return 'neutral'

#!/usr/bin/env python3
"""ais_watch.py — AIS Competitor Monitor | Midnight Rider Navigation
Polls Signal K for AIS vessels, matches competitors.json MMSIs,
calculates distance/bearing, writes to InfluxDB every 30s.
"""
import json,math,time,os,urllib.request
from datetime import datetime,timezone

SIGNALK=os.getenv("SIGNALK_HTTP","http://localhost:3000")
INFLUX_URL=os.getenv("INFLUX_URL","http://localhost:8086")
INFLUX_TOKEN=os.getenv("INFLUX_TOKEN","")
INFLUX_ORG=os.getenv("INFLUX_ORG","MidnightRider")
INFLUX_BUCKET=os.getenv("INFLUX_BUCKET","midnight_rider")
COMP_FILE=os.path.join(os.path.dirname(os.path.abspath(__file__)),"competitors.json")
POLL=30

def load_competitors():
    with open(COMP_FILE) as f: d=json.load(f)
    return {c['mmsi']:c for c in d['competitors'] if c.get('active') and c.get('mmsi')}

def sk_get(path):
    try:
        with urllib.request.urlopen(f"{SIGNALK}/signalk/v1/api/{path}",timeout=5) as r:
            return json.loads(r.read())
    except: return None

def haversine(la1,lo1,la2,lo2):
    R=6371000; p1,p2=math.radians(la1),math.radians(la2)
    dp,dl=math.radians(la2-la1),math.radians(lo2-lo1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def brg(la1,lo1,la2,lo2):
    p1,p2=math.radians(la1),math.radians(la2)
    dl=math.radians(lo2-lo1)
    x=math.sin(dl)*math.cos(p2)
    y=math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(x,y))+360)%360

def age_s(ts):
    try:
        dt=datetime.fromisoformat(ts.replace('Z','+00:00'))
        return int((datetime.now(timezone.utc)-dt).total_seconds())
    except: return 999

def influx_write(lines):
    if not INFLUX_TOKEN: print("⚠️ INFLUX_TOKEN not set"); return
    url=f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=s"
    req=urllib.request.Request(url,"\n".join(lines).encode(),method="POST")
    req.add_header("Authorization",f"Token {INFLUX_TOKEN}")
    req.add_header("Content-Type","text/plain")
    try: urllib.request.urlopen(req,timeout=5)
    except Exception as e: print(f"InfluxDB: {e}")

def main():
    print("🎯 AIS Watch — Midnight Rider | Block Island 2026")
    comps=load_competitors(); print(f" {len(comps)} active competitors loaded")
    it=0
    while True:
        it+=1; ts=int(time.time())
        nav=sk_get("vessels/self/navigation") or {}
        pos=(nav.get("position") or {}).get("value") or {}
        la0,lo0=pos.get("latitude"),pos.get("longitude")
        if not la0:
            print(f"[{it}] ⚠️ No own position from Signal K"); time.sleep(POLL); continue
        vessels=sk_get("vessels") or {}
        lines=[]; matched=0
        for mmsi,comp in comps.items():
            v=next((v for k,v in vessels.items() if mmsi in k),None)
            if not v: continue
            nv=v.get("navigation",{})
            pd=nv.get("position",{})
            pv=(pd.get("value",{}) if isinstance(pd,dict) else {})
            la,lo=pv.get("latitude"),pv.get("longitude")
            if not la: continue
            a=age_s(pd.get("timestamp","") if isinstance(pd,dict) else "")
            sog=(nv.get("speedOverGround",{}).get("value") or 0)
            cog=math.degrees(nv.get("courseOverGroundTrue",{}).get("value") or 0)
            d=haversine(la0,lo0,la,lo); b=brg(la0,lo0,la,lo)
            ph=(comp.get("ratings",{}).get("PHRF_LIS") or 0)
            ic=((comp.get("ratings",{}).get("IRC") or {}).get("TCC") or 0)
            cid=comp["id"]; nm=comp["boat_name"].replace(" ","_"); pr=comp["priority"]
            tags=f"competitor_id={cid},boat_name={nm},mmsi={mmsi},priority={pr}"
            flds=f"distance_m={d:.1f},bearing_true={b:.1f},lat={la},lon={lo},sog_ms={sog:.3f},cog_true={cog:.1f},phrf_lis={ph},irc_tcc={ic},ais_age_s={a}"
            lines.append(f"competitor_tracking,{tags} {flds} {ts}")
            matched+=1
            if a>300: print(f" ⚠️ {comp['boat_name']}: AIS stale {a}s")
        if lines: influx_write(lines)
        print(f"[{it}] {datetime.now().strftime('%H:%M:%S')} — {matched}/{len(comps)} tracked | own: {la0:.4f},{lo0:.4f}")
        time.sleep(POLL)

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: print("\n⏹️ Stopped")

"""SNOTEL 24 h precipitation windows from the NRCS AWDB REST service (same service the wsis fetchers use:
~/projects/whereshouldiski/scripts/fetch_snotel.py, read-only reference).

Element PREC, HOURLY (accumulated inches since 1 Oct; stations report in PST = UTC-8 year round, `dataTimeZone`).
Window precip = PREC(end) - PREC(end - 24 h) for the same end hours as MRMS (C+24/48/72/84); a negative difference
(gauge reset / emptying) or one above 500 mm is dropped. Sensor resolution is 0.1 in, so 24 h values are coarse
below ~5 mm. Output: obs/snotel_<case>.parquet  (station, name, state, lat, lon, elev_m, L, obs_mm).
usage: python -m verify.obs_snotel CASE [CASE ...]
"""
import sys, time
import numpy as np, pandas as pd, requests
import datetime as dt
from .common import OBS, USER_AGENT, cycle

API = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1"
S = requests.Session(); S.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
WEST = ("WA", "OR", "CA", "NV", "ID", "MT", "WY", "UT", "CO", "AZ", "NM")
ENDS = (24, 48, 72, 84)

def stations():
    f = OBS / "snotel_stations.parquet"
    if f.exists(): return pd.read_parquet(f)
    rows = []
    for st in WEST:
        r = S.get(f"{API}/stations", params={"networkCodes": "SNTL", "stationTriplets": f"*:{st}:SNTL", "activeOnly": "true"}, timeout=120)
        r.raise_for_status()
        for s in r.json():
            rows.append(dict(station=s["stationTriplet"], name=s["name"], state=st, lat=s["latitude"], lon=s["longitude"],
                             elev_m=s["elevation"] * 0.3048, begin=s["beginDate"][:10]))
        time.sleep(0.3)
    df = pd.DataFrame(rows); df.to_parquet(f); return df

def fetch(case, force=False):
    f = OBS / f"snotel_{case}.parquet"
    if f.exists() and not force: return pd.read_parquet(f)
    C = cycle(case); st = stations()
    st = st[st.begin <= (C - dt.timedelta(days=3)).strftime("%Y-%m-%d")]
    pst = lambda utc: (utc - dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    wanted = {L: (C + dt.timedelta(hours=L - 24), C + dt.timedelta(hours=L)) for L in ENDS}
    t0, t1 = C - dt.timedelta(hours=0), C + dt.timedelta(hours=84)
    vals = {}
    ids = list(st.station)
    for i in range(0, len(ids), 40):
        r = S.get(f"{API}/data", params={"stationTriplets": ",".join(ids[i:i + 40]), "elements": "PREC", "duration": "HOURLY",
                                         "beginDate": pst(t0), "endDate": pst(t1)}, timeout=300)
        r.raise_for_status()
        for rec in r.json():
            for d in rec.get("data", []):
                vals[rec["stationTriplet"]] = {x["date"]: x.get("value") for x in d["values"]}
        time.sleep(1.0)
    rows = []
    for sid, ser in vals.items():
        info = st[st.station == sid].iloc[0]
        for L, (a, b) in wanted.items():
            va, vb = ser.get(pst(a)), ser.get(pst(b))
            if va is None or vb is None: continue
            mm = (vb - va) * 25.4
            if mm < 0 or mm > 500: continue
            rows.append(dict(station=sid, name=info["name"], state=info.state, lat=info.lat, lon=info.lon, elev_m=info.elev_m, L=L, obs_mm=mm))
    df = pd.DataFrame(rows); df.to_parquet(f); return df

if __name__ == "__main__":
    for c in sys.argv[1:]:
        d = fetch(c); print(c, len(d), "station-windows,", d.station.nunique(), "stations, mean 24 h", round(d.obs_mm.mean(), 1), "mm")

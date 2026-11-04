"""Hourly ASOS/AWOS observations for CONUS from the Iowa Environmental Mesonet archive.

Per case (window C .. C+84 h) one request per state network (stations from the IEM network GeoJSON), 4 s apart, backing off on HTTP 429.
Output (cached under ~/data/nam-recast-verify/obs/): asos_<case>.parquet with one row per station-hour:
  station, valid (UTC hour), t_c, td_c, wspd (m/s), wdir, gust (m/s), wx (METAR present-weather codes), + stations table.
The observation chosen for an hour is the routine/special report closest to the top of the hour within +-20 min.
usage: python -m verify.obs_asos CASE [CASE ...]
"""
import sys, io, time, json
import numpy as np, pandas as pd, requests
import datetime as dt
from .common import OBS, STATES, STATE_REGION, USER_AGENT, cycle

IEM = "https://mesonet.agron.iastate.edu"
S = requests.Session(); S.headers["User-Agent"] = USER_AGENT

def stations():
    f = OBS / "asos_stations.parquet"
    if f.exists(): return pd.read_parquet(f)
    rows = []
    for st in STATES:
        r = S.get(f"{IEM}/geojson/network/{st}_ASOS.geojson", timeout=60); r.raise_for_status()
        for ft in r.json()["features"]:
            p, (lon, lat) = ft["properties"], ft["geometry"]["coordinates"]
            if not p.get("online", True) or p.get("elevation") is None: continue
            rows.append(dict(station=ft["id"], name=p["sname"], state=st, region=STATE_REGION[st], lat=lat, lon=lon,
                             elev=float(p["elevation"]), begin=p.get("archive_begin"), end=p.get("archive_end")))
        time.sleep(0.5)
    df = pd.DataFrame(rows); df.to_parquet(f); return df

def fetch(case, force=False):
    f = OBS / f"asos_{case}.parquet"
    if f.exists() and not force: return pd.read_parquet(f)
    C = cycle(case); t0, t1 = C - dt.timedelta(hours=1), C + dt.timedelta(hours=85)
    st = stations(); frames = []
    for state, g in st.groupby("state"):
        q = [("station", s) for s in g.station] + [(d, "") for d in ()]
        params = q + [("data", d) for d in ("tmpf", "dwpf", "sknt", "drct", "gust", "wxcodes")] + [
            ("sts", t0.strftime("%Y-%m-%dT%H:%MZ")), ("ets", t1.strftime("%Y-%m-%dT%H:%MZ")),
            ("report_type", "3"), ("report_type", "4"), ("tz", "Etc/UTC"), ("format", "onlycomma"), ("missing", "empty")]
        for attempt in range(8):      # IEM answers 429 when asked too fast: back off and retry
            r = S.post(f"{IEM}/cgi-bin/request/asos.py", data=params, timeout=600)
            if r.status_code == 200: break
            time.sleep(10 * (attempt + 1))
        r.raise_for_status()
        if r.text.count("\n") > 1: frames.append(pd.read_csv(io.StringIO(r.text), dtype={"wxcodes": str}))
        time.sleep(4.0)
    raw = pd.concat(frames, ignore_index=True)
    raw["valid"] = pd.to_datetime(raw["valid"])
    for c in ("tmpf", "dwpf", "sknt", "drct", "gust"): raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw["hour"] = raw["valid"].dt.round("h")
    raw["off"] = (raw["valid"] - raw["hour"]).abs()
    raw = raw[raw["off"] <= pd.Timedelta(minutes=20)].sort_values(["station", "hour", "off"])
    # prefer the report closest to the hour that carries the temperature
    raw["has_t"] = raw["tmpf"].notna()
    raw = raw.sort_values(["station", "hour", "has_t", "off"], ascending=[True, True, False, True])
    h = raw.drop_duplicates(["station", "hour"]).copy()
    out = pd.DataFrame(dict(station=h.station, valid=h.hour, t_c=(h.tmpf - 32) * 5 / 9, td_c=(h.dwpf - 32) * 5 / 9,
                            wspd=h.sknt * 0.514444, wdir=h.drct, gust=h.gust * 0.514444, wx=h.wxcodes.fillna("")))
    out = out[(out.valid >= C) & (out.valid <= C + dt.timedelta(hours=84))].reset_index(drop=True)
    out.to_parquet(f)
    return out

# ---- present weather -> precipitation type -------------------------------------------------------------
def ptype(wx):
    """Set of {RAIN,SNOW,FZRA,ICEP} reported in a METAR present-weather string ('' = nothing)."""
    s = set()
    for tok in wx.split():
        t = tok.lstrip("+-")
        if t.startswith("VC") or t.startswith("BL") or t.startswith("DR"): continue
        fz = "FZRA" in t or "FZDZ" in t
        if fz: s.add("FZRA")
        if "PL" in t or "PE" in t: s.add("ICEP")
        if "SN" in t or "SG" in t: s.add("SNOW")
        if ("RA" in t or "DZ" in t) and not fz: s.add("RAIN")
    return s

if __name__ == "__main__":
    for c in sys.argv[1:]:
        d = fetch(c); print(c, len(d), "station-hours,", d.station.nunique(), "stations,", d.t_c.notna().mean().round(3), "with T")

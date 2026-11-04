"""Score model fields against observations.

Stations (ASOS): each model field is sampled at the station by BILINEAR interpolation (and NEAREST grid point, kept
as a sensitivity column). T2m and Td2m are corrected to station elevation with a 6.5 K/km (T) and 2 K/km (Td) lapse
from the model's own terrain; stations whose model terrain differs by > DZMAX m in ANY compared model are dropped
for every model (common sample). Samples enter a lead's statistics only when the observation and all compared
models are valid. Wind is 10 m speed (no correction).
Precipitation (MRMS): 24 h totals as 0.25-degree box means (GFS: bilinear at the box centre; grid-218 models: mean of
the native points in the box), over boxes with MRMS valid, inside the CONUS polygon and GFS land fraction >= 0.5.
ETS / frequency bias / MAE at 2.5, 10, 25 mm per 24 h.
P-type: categorical agreement with ASOS present weather at station-hours reporting precipitation (nearest grid point).
Raw sums (n, sum d, sum |d|, sum d^2, contingency counts) are kept so cases can be pooled exactly.
"""
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from . import obs_asos, obs_mrms, obs_snotel
from .common import WORK, OBS, LEADS, CASES, cycle
from .gribio import Model

DZMAX = 400.0
LAPSE_T, LAPSE_TD = 0.0065, 0.0020
VARS = ("t2m", "td2m", "wspd")
THRESH = (2.5, 10.0, 25.0)
PT_CODE = {0: "NONE", 1: "RAIN", 2: "SNOW", 3: "FZRA", 4: "ICEP"}
WINDOWS = (24, 48, 72, 84)

def mkey(m): return f"{m.name}"

def prefetch(model, case, leads, workers=8):
    with ThreadPoolExecutor(workers) as ex: list(ex.map(lambda L: model.ensure(case, L), leads))

# ------------------------------------------------------------------------------------------ stations
def case_stations(case):
    st = obs_asos.stations()
    ob = obs_asos.fetch(case)
    st = st[st.station.isin(ob.station.unique())].reset_index(drop=True)
    return st, ob

def station_fields(model, case):
    """Per-lead values at the stations: dict var -> (nlead, nstn); cached. Includes orog and p-type code."""
    f = WORK / case / f"stn_{mkey(model)}.npz"
    st, _ = case_stations(case)
    if f.exists():
        z = np.load(f); return {k: z[k] for k in z.files}
    prefetch(model, case, LEADS)
    lat, lon = st.lat.values, st.lon.values
    out = {k: np.full((len(LEADS), len(st)), np.nan) for k in ("t2b", "d2b", "wsb", "t2n", "d2n", "wsn", "pt")}
    out["orog"] = None
    for i, L in enumerate(LEADS):
        d = model.read(case, L)
        g = model.grid
        fj, fi = g.station_index(lat, lon)
        if out["orog"] is None and "orog" in d: out["orog"] = g.sample(d["orog"], fj, fi)
        for k, key in (("t2", "t2"), ("d2", "d2")):
            out[k + "b"][i] = g.sample(d[key], fj, fi) - 273.15; out[k + "n"][i] = g.sample(d[key], fj, fi, "nearest") - 273.15
        for kind, s in (("b", "bilinear"), ("n", "nearest")):
            out["ws" + kind][i] = np.hypot(g.sample(d["u10"], fj, fi, s), g.sample(d["v10"], fj, fi, s))
        code = np.zeros(len(st))
        for c, key in ((1, "crain"), (2, "csnow"), (4, "cicep"), (3, "cfrzr")):     # later (higher priority) overwrite
            if key in d: code = np.where(g.sample(d[key], fj, fi, "nearest") > 0.5, c, code)
        out["pt"][i] = code
    f.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **out)
    return out

def _sums(d):
    d = d[np.isfinite(d)]
    return len(d), d.sum(), np.abs(d).sum(), (d ** 2).sum()

def score_stations(case, models):
    """Long DataFrame of sums: case, model, interp, region, var, lead, n, sd, sabs, ssq. Common sample across models."""
    st, ob = case_stations(case)
    C = cycle(case)
    F = {m.name: station_fields(m, case) for m in models}
    keep = np.ones(len(st), bool)
    for m in models:
        keep &= np.abs(F[m.name]["orog"] - st.elev.values) <= DZMAX
    dz = {m.name: F[m.name]["orog"] - st.elev.values for m in models}
    idx = {s: i for i, s in enumerate(st.station)}
    ob = ob[ob.station.isin(idx)].copy()
    ob["si"] = ob.station.map(idx); ob["li"] = ((ob.valid - C).dt.total_seconds() // 3600 // 3).astype(int)
    ob = ob[((ob.valid - C).dt.total_seconds() % 10800 == 0)]
    O = {v: np.full((len(LEADS), len(st)), np.nan) for v in VARS}
    O["t2m"][ob.li, ob.si] = ob.t_c.values; O["td2m"][ob.li, ob.si] = ob.td_c.values; O["wspd"][ob.li, ob.si] = ob.wspd.values
    reg = st.region.values
    rows = []
    for interp, sfx in (("bilinear", "b"), ("nearest", "n")):
        M = {}
        for m in models:
            f = F[m.name]
            M[m.name] = {"t2m": f["t2" + sfx] + LAPSE_T * dz[m.name][None, :],
                         "td2m": f["d2" + sfx] + LAPSE_TD * dz[m.name][None, :], "wspd": f["ws" + sfx]}
        for v in VARS:
            ok = np.isfinite(O[v]) & keep[None, :]
            for m in models: ok &= np.isfinite(M[m.name][v])
            for m in models:
                D = np.where(ok, M[m.name][v] - O[v], np.nan)
                for li, L in enumerate(LEADS):
                    for rn in ["CONUS"] + list(np.unique(reg)):
                        sel = np.ones(len(st), bool) if rn == "CONUS" else reg == rn
                        n, sd, sa, sq = _sums(D[li][sel])
                        rows.append((case, m.name, interp, rn, v, L, n, sd, sa, sq))
    return pd.DataFrame(rows, columns=["case", "model", "interp", "region", "var", "lead", "n", "sd", "sabs", "ssq"])

# ------------------------------------------------------------------------------------------ p-type
def obs_ptype_matrix(case, st):
    C = cycle(case); idx = {s: i for i, s in enumerate(st.station)}
    _, ob = case_stations(case)
    rec = []
    for r in ob.itertuples():
        t = obs_asos.ptype(r.wx)
        if not t or (r.valid - C).total_seconds() % 10800: continue
        rec.append((int((r.valid - C).total_seconds() // 10800), idx[r.station], t))
    return rec

def score_ptype(case, models):
    """Rows: case, model, lead_band, obs_cat, model_cat, n  and agreement counts (model type in observed set)."""
    st, _ = case_stations(case)
    rec = obs_ptype_matrix(case, st)
    F = {m.name: station_fields(m, case) for m in models}
    rows = []
    for m in models:
        pt = F[m.name]["pt"]
        for li, si, t in rec:
            L = LEADS[li]
            if L < 3: continue
            mc = PT_CODE[int(pt[li, si])] if np.isfinite(pt[li, si]) else None
            if mc is None: continue
            oc = next(iter(t)) if len(t) == 1 else "MIX"
            band = "3-36 h" if L <= 36 else "39-84 h"
            rows.append((case, m.name, band, oc, mc, 1, int(mc in t)))
    df = pd.DataFrame(rows, columns=["case", "model", "band", "obs", "mod", "n", "agree"])
    return df.groupby(["case", "model", "band", "obs", "mod"], as_index=False).sum()

# ------------------------------------------------------------------------------------------ precipitation
_mask = None
def conus_mask():
    """Boolean (140, 280) of box centres inside the US polygon (lower 48) and GFS land >= 0.5."""
    global _mask
    if _mask is not None: return _mask
    f = OBS / "conus_mask.npy"
    if f.exists(): _mask = np.load(f); return _mask
    import cartopy.io.shapereader as shp
    from shapely.ops import unary_union
    import shapely
    recs = [r for r in shp.Reader(shp.natural_earth("50m", "cultural", "admin_0_countries")).records() if r.attributes["ADM0_A3"] == "USA"]
    us = recs[0].geometry
    cl = 20.0 + 0.25 * (np.arange(140) + 0.5); co = 230.0 + 0.25 * (np.arange(280) + 0.5)
    CO, CL = np.meshgrid(co, cl)
    inside = shapely.contains_xy(us, ((CO + 180) % 360) - 180, CL)
    gfs = Model("gfs")
    d = gfs.read("2026110100", 0); lf = gfs.grid.box_mean(d["land"])
    m = inside & (lf >= 0.5) & (CL >= 24.5) & (CL <= 49.5)
    np.save(f, m); _mask = m
    return m

def box_precip(model, case):
    f = WORK / case / f"box_{mkey(model)}.npz"
    if f.exists():
        z = np.load(f); return {int(k[1:]): z[k] for k in z.files}
    ls = sorted({l for L in WINDOWS for l in (L - 24, L)})
    prefetch(model, case, ls)
    out = {}
    for L in WINDOWS:
        p = model.precip(case, L - 24, L)
        out[L] = model.grid.box_mean(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **{f"L{k}": v for k, v in out.items()})
    return out

def score_precip(case, models):
    """Rows: case, model, window, thresh, a,b,c,d (hits, false alarms, misses, correct negatives), plus n,sd,sabs,ssq."""
    obs, prod = obs_mrms.fetch(case)
    mask = conus_mask()
    P = {m.name: box_precip(m, case) for m in models}
    rows = []
    for L in WINDOWS:
        if L not in obs: continue
        ok = mask & np.isfinite(obs[L])
        for m in models: ok &= np.isfinite(P[m.name][L])
        o = obs[L][ok]
        for m in models:
            x = P[m.name][L][ok]; dd = x - o
            for t in THRESH:
                a = int(((x >= t) & (o >= t)).sum()); b = int(((x >= t) & (o < t)).sum())
                c = int(((x < t) & (o >= t)).sum()); d = int(((x < t) & (o < t)).sum())
                rows.append((case, m.name, L, t, a, b, c, d, len(o), dd.sum(), np.abs(dd).sum(), (dd ** 2).sum(), o.sum(), x.sum()))
    return pd.DataFrame(rows, columns=["case", "model", "window", "thresh", "a", "b", "c", "d", "n", "sd", "sabs", "ssq", "sobs", "smod"]), prod

def ets(a, b, c, d):
    n = a + b + c + d
    with np.errstate(invalid="ignore", divide="ignore"):
        ar = (a + b) * (a + c) / n
        return (a - ar) / (a + b + c - ar)

# ------------------------------------------------------------------------------------------ SNOTEL
def score_snotel(case, models):
    ob = obs_snotel.fetch(case)
    if ob.empty: return pd.DataFrame()
    st = ob.drop_duplicates("station")
    rows = []
    for m in models:
        prefetch(m, case, sorted({l for L in WINDOWS for l in (L - 24, L)}))
        g = None
        vals = {}
        for L in WINDOWS:
            p = m.precip(case, L - 24, L); g = m.grid
            fj, fi = g.station_index(st.lat.values, st.lon.values)
            vals[L] = dict(zip(st.station, g.sample(p, fj, fi)))
        for r in ob.itertuples():
            v = vals[r.L].get(r.station)
            if v is not None and np.isfinite(v): rows.append((case, m.name, r.station, r.state, r.elev_m, r.L, r.obs_mm, v))
    return pd.DataFrame(rows, columns=["case", "model", "station", "state", "elev_m", "window", "obs", "mod"])

"""Whole fields from the model files (byte ranges via .idx, cached) for the grid-to-grid fidelity statistics
and the feature panels. Same model names and templates as verify.gribio (nam, gfs, gfs06, fnam, fnam-anl).

    get(model, case, lead) -> dict with 2-D arrays on the model's own grid:
        mslp (hPa), z500 (dam), t850 (C), t2m (C), dpt2m (C), soilw0 (0-10 cm, m3/m3), u10, v10, wspd10 (m/s), cape (J/kg), refc (dBZ),
        csnow/cicep/cfrzr/crain (0/1), land (0/1), lat, lon (deg, lon -180..180), tp [(start, end, mm)]
    precip(model, case, l0, l1)   precipitation (mm) over product leads l0 -> l1
    snowfall(model, case, l0, l1) 10:1 snowfall (cm) from 3 h precipitation where the categorical snow flag is set
                                  at the end of each 3 h interval (the same recipe for every model; not the
                                  models' own snow accumulation, which the GFS and the NAM define differently)
    box(model, arr)               0.25 degree boxes (verify.gribio.Grid.box_mean: 20-55 N, 230-300 E)
"""
import hashlib
import numpy as np
import eccodes as ec
from .gribio import Model, Grid, _read
from .common import CACHE

ec.codes_grib_multi_support_on()

# key: (idx variable, idx level prefix, forecast-time filter)
SPEC = {
    "mslp": ("PRMSL", "mean sea level", "inst"), "z500": ("HGT", "500 mb", "inst"), "t850": ("TMP", "850 mb", "inst"),
    "t2m": ("TMP", "2 m above ground", "inst"), "u10": ("UGRD", "10 m above ground", "inst"),
    "v10": ("VGRD", "10 m above ground", "inst"), "cape": ("CAPE", "surface", "inst"),
    "refc": ("REFC", "entire atmosphere", "inst"), "csnow": ("CSNOW", "surface", "inst"),
    "cicep": ("CICEP", "surface", "inst"), "cfrzr": ("CFRZR", "surface", "inst"), "crain": ("CRAIN", "surface", "inst"),
    "land": ("LAND", "surface", "any"), "tp": ("APCP", "surface", "acc"),
    "soilw0": ("SOILW", "0-0.1 m below ground", "inst"), "dpt2m": ("DPT", "2 m above ground", "inst"),
}
WANT = tuple(SPEC)

def _ftype(fc):
    if "acc" in fc: return "acc"
    if "ave" in fc or "max" in fc or "min" in fc: return "other"
    return "inst"

def _ranges(idx_text):
    rows = []
    for ln in idx_text.strip().splitlines():
        p = ln.split(":")
        rows.append((int(p[1]), p[3], p[4], p[5] if len(p) > 5 else ""))
    offs = sorted({r[0] for r in rows}); nxt = {o: (offs[i + 1] if i + 1 < len(offs) else None) for i, o in enumerate(offs)}
    sel = set()
    for off, var, lev, fc in rows:
        for k, (v, l, t) in SPEC.items():
            if var == v and lev.startswith(l) and (t == "any" or _ftype(fc) == t):
                if var in ("UGRD", "VGRD") and lev != l: continue          # 10 m only, not "10 mb"
                if var in ("TMP", "DPT") and lev != l: continue
                sel.add(off)
    out = []
    for o in sorted(sel):
        e = nxt[o]
        if out and out[-1][1] == o: out[-1][1] = e
        else: out.append([o, e])
    return out

def _path(model, case, lead):
    h = hashlib.md5(model.template.encode()).hexdigest()[:6]
    return CACHE / f"F-{model.name}-{h}" / case / f"L{lead:03d}.grib2"

def ensure(model, case, lead):
    p = _path(model, case, lead)
    if p.exists() and p.stat().st_size: return p
    url = model.url(case, lead)
    rngs = _ranges(_read(url + ".idx").decode())
    blob = b"".join(_read(url, f"bytes={a}-{'' if b is None else b - 1}") for a, b in rngs)
    p.parent.mkdir(parents=True, exist_ok=True); t = p.with_suffix(".tmp"); t.write_bytes(blob); t.rename(p)
    return p

_mem = {}
SN = {("prmsl", "meanSea"): "mslp", ("gh", "isobaricInhPa"): "z500", ("t", "isobaricInhPa"): "t850",
      ("2t", "heightAboveGround"): "t2m", ("10u", "heightAboveGround"): "u10", ("10v", "heightAboveGround"): "v10",
      ("cape", "surface"): "cape", ("refc", "atmosphere"): "refc", ("refc", "atmosphereSingleLayer"): "refc",
      ("csnow", "surface"): "csnow", ("cicep", "surface"): "cicep", ("cfrzr", "surface"): "cfrzr",
      ("crain", "surface"): "crain", ("lsm", "surface"): "land", ("land", "surface"): "land",
      ("soilw", "depthBelowLandLayer"): "soilw0", ("vsw", "depthBelowLandLayer"): "soilw0", ("2d", "heightAboveGround"): "dpt2m"}

def get(model, case, lead):
    key = (model.name, model.template, case, lead)
    if key in _mem: return _mem[key]
    out = {"tp": []}
    with open(ensure(model, case, lead), "rb") as f:
        while True:
            g = ec.codes_grib_new_from_file(f)
            if g is None: break
            try:
                sn, tl = ec.codes_get(g, "shortName"), ec.codes_get(g, "typeOfLevel")
                if model.grid is None: model.grid = Grid(g)
                if "lat" not in out:
                    out["lat"] = model.grid.lat; out["lon"] = np.where(model.grid.lon > 180, model.grid.lon - 360, model.grid.lon)
                v = ec.codes_get_values(g).astype(float)
                v[v == ec.codes_get(g, "missingValue")] = np.nan
                v = v.reshape(model.grid.nj, model.grid.ni)
                if sn == "tp":
                    sr = ec.codes_get(g, "stepRange")
                    if "-" in sr: a, b = sr.split("-"); out["tp"].append((int(a), int(b), v))
                    continue
                if sn == "unknown":   # REFC in some eccodes tables
                    if (ec.codes_get(g, "discipline"), ec.codes_get(g, "parameterCategory"), ec.codes_get(g, "parameterNumber")) == (0, 16, 196): sn, tl = "refc", "atmosphere"
                k = SN.get((sn, tl))
                if k is None or k in out: continue
                if k == "z500" and ec.codes_get(g, "level") != 500: continue
                if k == "t850" and ec.codes_get(g, "level") != 850: continue
                if k == "mslp": v = v / 100.0
                elif k == "z500": v = v / 10.0
                elif k in ("t2m", "t850", "dpt2m"): v = v - 273.15
                out[k] = v
            finally:
                ec.codes_release(g)
    if "u10" in out and "v10" in out: out["wspd10"] = np.hypot(out["u10"], out["v10"])
    _mem[key] = out
    return out

def _cum(model, case, fh):
    """Total precipitation (mm) from the model's own start to model forecast hour fh (buckets or 0-t records)."""
    if fh <= 0: return 0.0
    d = get(model, case, fh + model.off)["tp"]
    cand = [x for x in d if x[1] == fh and x[0] < fh]
    if not cand: raise KeyError(f"{model.name} {case} fh{fh}: no APCP ending here ({[(a, b) for a, b, _ in d]})")
    a, _, v = min(cand, key=lambda x: x[0])
    return v if a == 0 else _cum(model, case, a) + v

def precip(model, case, l0, l1):
    return _cum(model, case, l1 - model.off) - _cum(model, case, l0 - model.off)

def snowfall(model, case, l0, l1):
    tot = 0.0
    for t in range(l0 + 3, l1 + 1, 3):
        p = precip(model, case, t - 3, t); s = get(model, case, t).get("csnow")
        tot = tot + np.where(s > 0.5, p, 0.0)
    return tot   # mm water x 10 = mm snow = cm snow x ... : 10:1 ratio, mm water -> cm snow is the same number

def box(model, arr):
    return model.grid.box_mean(np.asarray(arr).ravel())

#!/usr/bin/env python3
"""Seed the Noah land state of a WOOF-NAM saved initial state from a NAM-format grid-218 file (the soil seed).

The same recipe as the CPU path (docs/tm06-design.md section 2; run/recast.sh seed_prep), applied to the saved init
that `python -m namgpu.init.slab_init save` writes (woof-nam run --init-from reads it back):
  seeded, over model LAND points that grid 218 covers (masked bilinear on the seed's own land mask; the GFS value
  stays where the seed has no land point):
    STC   soil temperature, 4 layers            <- TSOIL 0-10, 10-40, 40-100, 100-200 cm
    SMC   soil moisture, 4 layers               <- SOILW
    SH2O  liquid soil water, 4 layers           <- SOILL (capped at SMC)
    SNO   snow water equivalent (mm)            <- WEASD (instantaneous record)
    TSKIN skin temperature, land only           <- TMP:surface   (SST untouched: the GFS SST survives)
  and the fields that follow from SNO: SI (snow depth, mm = 5 x SNO, the 5:1 ratio nemsinterp/WRF use when only the
  water equivalent is known) and SNOWC (0.98 where SNO > 0, else 0: init_native_sfc's own rule).
  NOT seeded, as on the CPU path: canopy water (CMC) and a snow depth of its own, sea ice, SST, 3 m soil temperature (TG).
The seed is the archived NAM awphys00 at C-6 for a hindcast, the previous cycle's own awphys06 product when live.

usage: seed_init.py <saved init dir> <seed grib2>     (numpy + eccodes only; edits the .npy files in place)
Writes <init dir>/seed-receipt.json: counts and the mean change of every seeded field.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import eccodes as ec

R_EARTH = 6371229.0            # grid 218: shape of the Earth 6, sphere
LOV, LATIN = np.deg2rad(265.0), np.deg2rad(25.0)
LAYERS = [(0.0, 0.1), (0.1, 0.4), (0.4, 1.0), (1.0, 2.0)]


def lcc_xy(lat_deg, lon_deg):
    """Spherical Lambert conformal, tangent at 25 N, LoV 265 E (grid 218): metres from the projection origin."""
    lat, lon = np.deg2rad(lat_deg), np.deg2rad(lon_deg)
    n = np.sin(LATIN)
    big_f = np.cos(LATIN) * np.tan(np.pi / 4 + LATIN / 2) ** n / n
    rho = R_EARTH * big_f / np.tan(np.pi / 4 + lat / 2) ** n
    rho0 = R_EARTH * big_f / np.tan(np.pi / 4 + LATIN / 2) ** n
    dl = (lon - LOV + np.pi) % (2 * np.pi) - np.pi
    th = n * dl
    return rho * np.sin(th), rho0 - rho * np.cos(th)


def read_seed(path):
    """{'soilw': [4 arrays], 'tsoil': [...], 'soill': [...], 'weasd', 'tskin', 'land'} (ny, nx) + the grid's x, y axes."""
    got = {"soilw": [None] * 4, "tsoil": [None] * 4, "soill": [None] * 4}
    ec.codes_grib_multi_support_on()
    with open(path, "rb") as f:
        while True:
            h = ec.codes_grib_new_from_file(f)
            if h is None:
                break
            try:
                dcp = (ec.codes_get(h, "discipline"), ec.codes_get(h, "parameterCategory"), ec.codes_get(h, "parameterNumber"))
                tl = ec.codes_get(h, "typeOfLevel")
                name = None
                if tl == "depthBelowLandLayer" and dcp in ((2, 0, 192), (2, 0, 2), (2, 3, 192)):
                    sc = lambda k: ec.codes_get(h, f"scaledValueOf{k}FixedSurface") / 10.0 ** ec.codes_get(h, f"scaleFactorOf{k}FixedSurface")
                    top, bot = sc("First"), sc("Second")
                    lay = [i for i, (a, b) in enumerate(LAYERS) if abs(a - top) < 1e-3 and abs(b - bot) < 1e-3]
                    if lay:
                        name = {(2, 0, 192): "soilw", (2, 0, 2): "tsoil", (2, 3, 192): "soill"}[dcp] + f":{lay[0]}"
                elif dcp == (0, 1, 13) and tl == "surface" and ec.codes_get(h, "stepType") == "instant":
                    name = "weasd"
                elif dcp == (0, 0, 0) and tl == "surface":
                    name = "tskin"
                elif dcp == (2, 0, 0) and tl == "surface":
                    name = "land"
                if name is None:
                    continue
                v = ec.codes_get_values(h).astype(np.float64)
                v[v == ec.codes_get(h, "missingValue")] = np.nan
                v[np.abs(v) > 1e15] = np.nan
                ni, nj = ec.codes_get(h, "Ni"), ec.codes_get(h, "Nj")
                if "lat" not in got:
                    la = ec.codes_get_array(h, "latitudes"); lo = ec.codes_get_array(h, "longitudes")
                    got["lat"], got["lon"], got["ni"], got["nj"] = la, lo, ni, nj
                v = v.reshape(nj, ni)
                if ":" in name:
                    k, i = name.split(":")
                    if got[k][int(i)] is None:
                        got[k][int(i)] = v
                elif name not in got:
                    got[name] = v
            finally:
                ec.codes_release(h)
    for k in ("soilw", "tsoil", "soill"):
        if any(x is None for x in got[k]):
            raise SystemExit(f"{path}: seed lacks {k} layers {[i for i, x in enumerate(got[k]) if x is None]}")
    for k in ("weasd", "tskin", "land"):
        if k not in got:
            raise SystemExit(f"{path}: seed lacks {k}")
    ni, nj = got["ni"], got["nj"]
    x, y = lcc_xy(got["lat"].reshape(nj, ni), got["lon"].reshape(nj, ni))
    dx, dy = x[0, 1] - x[0, 0], y[1, 0] - y[0, 0]
    # the grid must be regular in the projection (the check that the projection constants match the file)
    ex = np.abs(x - (x[0, 0] + dx * np.arange(ni)[None, :])).max()
    ey = np.abs(y - (y[0, 0] + dy * np.arange(nj)[:, None])).max()
    if max(ex, ey) > 5.0:
        raise SystemExit(f"{path}: grid 218 projection check failed (max deviation {max(ex, ey):.1f} m)")
    got["x0"], got["y0"], got["dx"], got["dy"] = x[0, 0], y[0, 0], dx, dy
    return got


def masked_bilinear(field, land, fi, fj):
    """Bilinear interpolation of field (nj, ni) to fractional indices (fj, fi), using land points only; NaN where
    no land corner has a value or the point is outside the grid."""
    nj, ni = field.shape
    ok = (fi >= 0) & (fi <= ni - 1) & (fj >= 0) & (fj <= nj - 1)
    i0 = np.clip(np.floor(np.where(ok, fi, 0)).astype(int), 0, ni - 2)
    j0 = np.clip(np.floor(np.where(ok, fj, 0)).astype(int), 0, nj - 2)
    ti, tj = np.where(ok, fi, 0) - i0, np.where(ok, fj, 0) - j0
    num = np.zeros(fi.shape); den = np.zeros(fi.shape)
    for dj, di, w in ((0, 0, (1 - ti) * (1 - tj)), (0, 1, ti * (1 - tj)), (1, 0, (1 - ti) * tj), (1, 1, ti * tj)):
        v = field[j0 + dj, i0 + di]
        m = land[j0 + dj, i0 + di] & np.isfinite(v)
        num += np.where(m, w * np.nan_to_num(v), 0.0)
        den += np.where(m, w, 0.0)
    out = np.where(ok & (den > 1e-6), num / np.maximum(den, 1e-12), np.nan)
    return out


class Init:
    """The saved init directory: arrays by state-field name, as writable views on the .npy files."""

    def __init__(self, d):
        self.d = Path(d)
        with open(self.d / "skeleton.pkl", "rb") as f:
            hdr = pickle.load(f)
        self.meta = {int(k): v for k, v in hdr["meta"].items()}
        self.st = hdr["skel"]["st"]
        self.jm, self.im = hdr["jm"], hdr["im"]
        self._own = {}

    def view(self, name):
        ref = self.st[name]
        m = self.meta[ref.k]
        o = m["owner"]
        if o not in self._own:
            self._own[o] = np.load(self.d / f"a{o}.npy", mmap_mode="r+")
        base = self._own[o]
        if o == ref.k:
            return base
        itemsize = base.itemsize
        return np.lib.stride_tricks.as_strided(base.reshape(-1)[m["off"]:], m["shape"],
                                               [s * itemsize for s in m["strides"]], writeable=True)

    def flush(self):
        for a in self._own.values():
            a.flush()


def main(init_dir, seed_path):
    ini = Init(init_dir)
    jm, im = ini.jm, ini.im
    for need in ("GLAT", "GLON", "SM", "STC", "SMC", "SH2O", "SNO", "SI", "SNOWC", "TSKIN"):
        if need not in ini.st:
            raise SystemExit(f"{init_dir}: no state field {need}; have {sorted(ini.st)[:80]}")
    glat = np.rad2deg(ini.view("GLAT").astype(np.float64)); glon = np.rad2deg(ini.view("GLON").astype(np.float64)) % 360.0
    sm = ini.view("SM")
    land = sm < 0.5
    seed = read_seed(seed_path)
    x, y = lcc_xy(glat, glon)
    fi, fj = (x - seed["x0"]) / seed["dx"], (y - seed["y0"]) / seed["dy"]
    sland = np.nan_to_num(seed["land"], nan=0.0) > 0.5
    rec = {"seed": str(seed_path), "model_land_points": int(land.sum())}

    def put(name, new, layer=None, scale=None):
        a = ini.view(name)
        tgt = a if layer is None else a[layer]
        ok = land & np.isfinite(new)
        old = tgt[ok].astype(np.float64)
        val = new[ok]
        if scale:
            val = scale(val, ok)
        tgt[ok] = val.astype(np.float32)
        key = name if layer is None else f"{name}[{layer}]"
        rec[key] = {"points": int(ok.sum()), "mean_before": float(old.mean()), "mean_after": float(val.mean()),
                    "mean_change": float((val - old).mean())}
        return ok

    sm_new = []
    for k in range(4):
        w = masked_bilinear(seed["soilw"][k], sland, fi, fj)
        put("STC", masked_bilinear(seed["tsoil"][k], sland, fi, fj), k)
        put("SMC", np.clip(w, 0.02, 0.6), k)
        sm_new.append(w)
    for k in range(4):
        liq = masked_bilinear(seed["soill"][k], sland, fi, fj)
        smc = ini.view("SMC")[k]
        liq = np.where(np.isfinite(liq), np.minimum(np.maximum(liq, 0.0), smc), np.nan)
        put("SH2O", liq, k)
    sno = masked_bilinear(np.nan_to_num(seed["weasd"], nan=0.0), sland, fi, fj)
    sno = np.where(np.isfinite(sno), np.maximum(sno, 0.0), np.nan)
    put("SNO", sno)
    put("SI", sno * 5.0)
    put("SNOWC", np.where(np.isfinite(sno), np.where(sno > 0, 0.98, 0.0), np.nan))
    put("TSKIN", masked_bilinear(seed["tskin"], sland, fi, fj))
    ini.flush()
    Path(init_dir, "seed-receipt.json").write_text(json.dumps(rec, indent=1))
    for k, v in rec.items():
        if isinstance(v, dict):
            print(f"  {k:10s} {v['points']:7d} pts  {v['mean_before']:10.4f} -> {v['mean_after']:10.4f}  (change {v['mean_change']:+.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))

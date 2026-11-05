#!/usr/bin/env python3
"""Score the WOOF-NAM GPU trial (docs/gpu-woof-trial.md) against the archived NAM, the same way as run/compare.py.

usage: score_woof.py <case dir> <out dir> [--check]
  <case dir>/woof/woof-nam.t18z.awphysHH.tm00.grib2   WOOF-NAM products from the 2026-10-31 18Z start (HH = lead + 6)
  <case dir>/woofhist/wrfout_d01_<valid>               WOOF-NAM history (RAINNC + RAINC, accumulated from 18Z)
  <case dir>/nam-archive/nam.t00z.awphysFF.tm00.grib2  archived NAM, f00 12 24 36 48 84
  <case dir>/gfs/gfs.t00z.pgrb2.0p25.f000              land mask
  <case dir>/tm06/nam.t00z.awphys24.tm00.grib2         FrankenNAM f24, for --check only
Writes <out dir>/stats.csv (field, lead, rmse_woof_vs_NAM, bias_woof_vs_NAM) on compare.py's CONUS-land 0.25 deg grid.
WOOF-NAM's products carry 6 h precipitation buckets only for the kept hours, so 24 h totals come from the history
files; the f84 history file was truncated on upload, so the 60-84 h window has no WOOF-NAM value.
--check recomputes FrankenNAM tm06 vs NAM at f24 and prints it beside docs/figs/tm06/stats.csv.
"""
import csv, os, sys, types
try:
    import matplotlib, cartopy  # noqa: F401
except ImportError:   # compare.py imports these for its maps; no maps are drawn here, so stubs will do
    for m in ("matplotlib", "matplotlib.pyplot", "cartopy", "cartopy.crs", "cartopy.feature"):
        sys.modules[m] = types.ModuleType(m)
    sys.modules["matplotlib"].use = lambda *a, **k: None
CASE, OUT = sys.argv[1], sys.argv[2]
CHECK = "--check" in sys.argv
sys.argv = [sys.argv[0], CASE, OUT]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare as C   # noqa: E402
import numpy as np    # noqa: E402
import netCDF4        # noqa: E402

_path = C.path
def path(src, fh):
    if src == "woof": return f"{CASE}/woof/woof-nam.t18z.awphys{fh + 6:02d}.tm00.grib2"
    return _path(src, fh)
C.path = path

VALID = {0: "2026-11-01_00:00:00", 24: "2026-11-02_00:00:00", 48: "2026-11-03_00:00:00"}
def woof_cum(fh):
    """Precipitation (mm) accumulated from the 18Z start to lead fh, from the history file."""
    with netCDF4.Dataset(f"{CASE}/woofhist/wrfout_d01_{VALID[fh]}") as d:
        v = (np.asarray(d["RAINNC"][0], float) + np.asarray(d["RAINC"][0], float)).ravel()
        la = np.asarray(d["XLAT"][0], float).ravel(); lo = np.asarray(d["XLONG"][0], float).ravel() % 360
    return C.regrid("woofhist", v, la, lo)

lsm = C.regrid("gfs", *C.read("gfs", 0, "lsm"))
conus = (lsm > 0.5) & (C.GLAT >= 25) & (C.GLAT <= 50) & (C.GLON >= 235) & (C.GLON <= 293)
def stats(a, ref):
    d = (a - ref)[conus & np.isfinite(a) & np.isfinite(ref)]
    return np.sqrt(np.mean(d ** 2)), np.mean(d)

rows = []
for fh in (0, 24, 48, 84):
    for kind in ("mslp", "z500", "t2m", "wspd10", "u10", "v10"):
        # NAM first: the archive packs 10u/10v in one multi-field message, and eccodes hands a pending 10v
        # sub-message to the next file read that asks for 10v (a WOOF read after a NAM 10u read got the NAM's 10v)
        n = C.field("nam", fh, kind); w = C.field("woof", fh, kind)
        assert not np.array_equal(np.nan_to_num(w), np.nan_to_num(n)), f"{kind} f{fh}: WOOF field identical to NAM (read leak)"
        r, b = stats(w, n)
        rows.append((kind, fh, r, b)); print(f"{kind:7s} f{fh:02d}  rmse {r:.3f}  bias {b:+.3f}", flush=True)
for a, b in ((0, 24), (24, 48)):
    r, bi = stats(woof_cum(b) - woof_cum(a), C.precip("nam", a, b))
    rows.append((f"precip24h_{a}-{b}", b, r, bi)); print(f"precip {a}-{b}  rmse {r:.3f}  bias {bi:+.3f}", flush=True)
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/stats.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["field", "lead", "rmse_woof_vs_NAM", "bias_woof_vs_NAM"])
    for k, fh, r, b in rows: w.writerow([k, fh, f"{r:.3f}", f"{b:.3f}"])
print("wrote", f"{OUT}/stats.csv")

if CHECK:
    ref = {(r["field"], int(r["lead"])): r for r in csv.DictReader(open(os.path.join(os.path.dirname(OUT.rstrip("/")), "tm06", "stats.csv")))}
    for kind in ("mslp", "z500", "t2m", "wspd10"):
        r, b = stats(C.field("tm06", 24, kind), C.field("nam", 24, kind))
        print(f"check tm06 f24 {kind}: here {r:.3f}/{b:+.3f}  published {float(ref[(kind, 24)]['rmse_tm06_vs_NAM']):.3f}/{float(ref[(kind, 24)]['bias_tm06_vs_NAM']):+.3f}")

#!/usr/bin/env python3
"""Score the GPU-path product against the archived NAM with run/compare.py's method (laptop; eccodes, scipy, numpy).

usage: score_gpu.py <case dir> <out dir>        env LEADS=0,24,48,84 (default)
  <case dir>/gpu/nam.t00z.awphysFF.tm00.grib2     the GPU path's product (products-gpu/)
  <case dir>/cpu/nam.t00z.awphysFF.tm00.grib2     the CPU FrankenNAM tm06 product (products/), optional
  <case dir>/nam-archive/nam.t00z.awphysFF.tm00.grib2   archived NAM (f00 and the 12 h bucket hours for precipitation)
  <case dir>/gfs/gfs.t00z.pgrb2.0p25.f000         land mask + the GFS soil at C
  <case dir>/seed/nam.t18z.awphys00.tm00.grib2    the soil seed (archived NAM at C-6)
Writes <out>/stats.csv (GPU | CPU tm06 | WOOF trial | GFS vs NAM, RMSE/bias on compare.py's CONUS-land 0.25 deg grid;
the CPU, trial and GFS columns are also read from docs/figs/tm06 and docs/figs/woof when present) and <out>/soil.md.
"""
import csv, os, sys, types
try:
    import matplotlib, cartopy  # noqa: F401
except ImportError:
    for m in ("matplotlib", "matplotlib.pyplot", "cartopy", "cartopy.crs", "cartopy.feature"):
        sys.modules[m] = types.ModuleType(m)
    sys.modules["matplotlib"].use = lambda *a, **k: None
CASE, OUT = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], CASE, OUT]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compare as C   # noqa: E402
import numpy as np    # noqa: E402

_path = C.path
def path(src, fh):
    if src == "tm06": return f"{CASE}/gpu/nam.t00z.awphys{fh:02d}.tm00.grib2"
    if src == "cpu":  return f"{CASE}/cpu/nam.t00z.awphys{fh:02d}.tm00.grib2"
    return _path(src, fh)
C.path = path
os.makedirs(OUT, exist_ok=True)
LEADS = [int(x) for x in os.environ.get("LEADS", "0,24,48,84").split(",")]

lsm = C.regrid("gfs", *C.read("gfs", 0, "lsm"))
conus = (lsm > 0.5) & (C.GLAT >= 25) & (C.GLAT <= 50) & (C.GLON >= 235) & (C.GLON <= 293)
def stats(a, ref):
    d = (a - ref)[conus & np.isfinite(a) & np.isfinite(ref)]
    return np.sqrt(np.mean(d ** 2)), np.mean(d)
have_cpu = os.path.isdir(f"{CASE}/cpu")

# ---- soil trace at f00 (docs/figs/tm06/soil.md is the CPU table)
if 0 in LEADS:
    with open(f"{OUT}/soil.md", "w") as m:
        m.write("Soil state at f00 (valid C), RMSE / bias over CONUS land points on the 0.25 deg grid; a - b.\n\n")
        cols = [("gpu", "nam"), ("gpu", "seed"), ("gpu", "gfs"), ("nam", "seed")] + ([("cpu", "nam"), ("cpu", "seed"), ("gpu", "cpu")] if have_cpu else [])
        lab = {"gpu": "GPU", "nam": "NAM", "seed": "seed", "gfs": "GFS", "cpu": "CPU tm06"}
        m.write("| Field | " + " | ".join(f"{lab[a]} vs {lab[b]}" for a, b in cols) + " |\n|---|" + "---|" * len(cols) + "\n")
        for kind, u in (("sm0", "m3/m3"), ("st0", "K"), ("sm2", "m3/m3")):
            f = {}
            for s_ in ("nam", "gpu", "seed", "gfs") + (("cpu",) if have_cpu else ()):   # NAM first (eccodes sub-message trap)
                try: f[s_] = C.field({"gpu": "tm06"}.get(s_, s_), 0, kind)
                except Exception as e: print("soil", s_, kind, "unavailable:", e)
            cell = lambda a, b: ("%.3f / %+.3f" % stats(f[a], f[b])) if a in f and b in f else "n/a"
            m.write(f"| {kind} ({u}) | " + " | ".join(cell(a, b) for a, b in cols) + " |\n")
    print(open(f"{OUT}/soil.md").read())

# ---- fidelity to the archived NAM
rows = []
for fh in LEADS:
    for kind in ("mslp", "z500", "t2m", "wspd10", "u10", "v10"):
        n = C.field("nam", fh, kind)                    # NAM first (eccodes hands a pending 10v sub-message to the next file)
        g = C.field("tm06", fh, kind)
        assert not np.array_equal(np.nan_to_num(g), np.nan_to_num(n)), f"{kind} f{fh}: GPU field identical to NAM"
        c = stats(C.field("cpu", fh, kind), n) if have_cpu else (np.nan, np.nan)
        rows.append((kind, fh, stats(g, n), c))
        print(f"{kind:7s} f{fh:02d}  GPU {rows[-1][2][0]:.3f}/{rows[-1][2][1]:+.3f}   CPU {c[0]:.3f}/{c[1]:+.3f}", flush=True)
for a, b in [(0, 24), (24, 48), (60, 84)]:
    if b not in LEADS and not (a in LEADS or b <= max(LEADS)): continue
    if b > max(LEADS): continue
    try:
        n = C.precip("nam", a, b); g = C.precip("tm06", a, b)
        c = stats(C.precip("cpu", a, b), n) if have_cpu else (np.nan, np.nan)
        rows.append((f"precip24h_{a}-{b}", b, stats(g, n), c))
        print(f"precip {a}-{b} GPU {rows[-1][2][0]:.3f}/{rows[-1][2][1]:+.3f}   CPU {c[0]:.3f}/{c[1]:+.3f}", flush=True)
    except KeyError as e:
        print("precip", a, b, "unavailable:", e)

def ref(path_, col):
    p = os.path.join(os.path.dirname(HERE), path_)
    if not os.path.exists(p): return {}
    return {(r["field"], int(r["lead"])): r for r in csv.DictReader(open(p))}
tm06 = ref("../docs/figs/tm06/stats.csv", None); woof = ref("../docs/figs/woof/stats.csv", None)
with open(f"{OUT}/stats.csv", "w", newline="") as f, open(f"{OUT}/stats.md", "w") as m:
    w = csv.writer(f)
    hdr = ["field", "lead", "rmse_gpu_vs_NAM", "bias_gpu_vs_NAM", "rmse_cpu_vs_NAM", "bias_cpu_vs_NAM", "rmse_woof_trial_vs_NAM", "bias_woof_trial_vs_NAM", "rmse_GFS_vs_NAM", "bias_GFS_vs_NAM"]
    w.writerow(hdr)
    m.write("| Field | Lead | GPU path RMSE / bias | CPU tm06 (re-scored here) | CPU tm06 (published) | WOOF trial | GFS |\n|---|---|---|---|---|---|---|\n")
    for k, fh, g, c in rows:
        t = tm06.get((k, fh)); wf = woof.get((k, fh))
        pub_cpu = (t["rmse_tm06_vs_NAM"], t["bias_tm06_vs_NAM"]) if t else ("", "")
        wt = (wf["rmse_woof_vs_NAM"], wf["bias_woof_vs_NAM"]) if wf else ("", "")
        gf = (t["rmse_GFS_vs_NAM"], t["bias_GFS_vs_NAM"]) if t else ("", "")
        w.writerow([k, fh, f"{g[0]:.3f}", f"{g[1]:.3f}", f"{c[0]:.3f}", f"{c[1]:.3f}", *wt, *gf])
        fmt = lambda r, b: f"{float(r):.2f} / {float(b):+.2f}" if r != "" and not (isinstance(r, float) and np.isnan(r)) else "n/a"
        m.write(f"| {k} | f{fh:02d} | {g[0]:.2f} / {g[1]:+.2f} | {fmt(c[0], c[1])} | {fmt(*pub_cpu)} | {fmt(*wt)} | {fmt(*gf)} |\n")
print(open(f"{OUT}/stats.md").read())

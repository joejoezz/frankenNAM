#!/usr/bin/env python3
"""Recast vs archived NAM vs GFS for one cycle, on a common 0.25 deg grid (20-60N, 130-60W).

usage: compare.py <case dir> <out dir>
  <case dir>/recast/grib2/nam.t00z.bgdawpFF.tm00.grib2   (UPP, native rotated B grid)
  <case dir>/nam-archive/nam.t00z.awphysFF.tm00.grib2   (grid 218)
  <case dir>/gfs/gfs.t00z.pgrb2.0p25.fFFF
Writes PNGs and stats.md / stats.csv to <out dir>.
"""
import sys, os, glob
import numpy as np
import eccodes as ec
from scipy.spatial import Delaunay
from scipy.interpolate import LinearNDInterpolator
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

CASE, OUT = sys.argv[1], sys.argv[2]
ec.codes_grib_multi_support_on()   # the archive packs U/V 10 m as sub-messages of one GRIB message
os.makedirs(OUT, exist_ok=True)
LAT = np.arange(20, 60.001, 0.25); LON = np.arange(230, 300.001, 0.25)
GLON, GLAT = np.meshgrid(LON, LAT)

def path(src, fh):
    if src == "recast": return f"{CASE}/recast/grib2/nam.t00z.bgdawp{fh:02d}.tm00.grib2"
    if src == "nam":    return f"{CASE}/nam-archive/nam.t00z.awphys{fh:02d}.tm00.grib2"
    return f"{CASE}/gfs/gfs.t00z.pgrb2.0p25.f{fh:03d}"

_ll = {}
def bgrid_latlon(fname):
    if "b" not in _ll:
        import subprocess, tempfile
        t = tempfile.mktemp(suffix=".txt")
        subprocess.run(["wgrib2", fname, "-d", "1", "-gridout", t], check=True, capture_output=True)
        a = np.loadtxt(t, delimiter=",")
        _ll["b"] = (a[:, 2], a[:, 3] % 360); os.remove(t)
    return _ll["b"]

def read(src, fh, short, level=None, step=None):
    """Return (values, lats, lons) for the first message matching shortName/level/stepRange."""
    with open(path(src, fh), "rb") as f:
        while True:
            g = ec.codes_grib_new_from_file(f)
            if g is None: break
            try:
                if ec.codes_get(g, "shortName") != short: continue
                if level is not None and (ec.codes_get(g, "typeOfLevel"), ec.codes_get(g, "level")) != level: continue
                if step is not None and ec.codes_get(g, "stepRange") != step: continue
                v = ec.codes_get_values(g).astype(float)
                v[v == ec.codes_get(g, "missingValue")] = np.nan
                try:
                    la = ec.codes_get_array(g, "latitudes"); lo = ec.codes_get_array(g, "longitudes") % 360
                except ec.KeyValueNotFoundError:   # UPP rotated B grid (template 32769): ask wgrib2
                    la, lo = bgrid_latlon(path(src, fh))
                return v, la, lo
            finally:
                ec.codes_release(g)
    raise KeyError(f"{src} f{fh} {short} {level} {step}")

def steps(src, fh, short="tp"):
    out = []
    with open(path(src, fh), "rb") as f:
        while True:
            g = ec.codes_grib_new_from_file(f)
            if g is None: break
            if ec.codes_get(g, "shortName") == short: out.append(ec.codes_get(g, "stepRange"))
            ec.codes_release(g)
    return out

_tri = {}
def regrid(src, v, la, lo):
    if src == "gfs":   # regular 0.25 deg global, north to south
        nlat = 721; field = v.reshape(nlat, 1440)
        i = ((90 - LAT) / 0.25).round().astype(int); j = (LON / 0.25).round().astype(int)
        return field[np.ix_(i, j)]
    key = (src, len(v))
    if key not in _tri:
        m = (la > 15) & (la < 65) & (lo > 220) & (lo < 310)
        _tri[key] = (Delaunay(np.c_[lo[m], la[m]]), m)
    tri, m = _tri[key]
    return LinearNDInterpolator(tri, v[m])(GLON, GLAT)

def field(src, fh, name):
    if name == "mslp":  v = read(src, fh, "prmsl", ("meanSea", 0)); return regrid(src, *v) / 100.0
    if name == "z500":  v = read(src, fh, "gh", ("isobaricInhPa", 500)); return regrid(src, *v) / 10.0
    if name == "t2m":   v = read(src, fh, "2t", ("heightAboveGround", 2)); return regrid(src, *v) - 273.15
    if name == "rh700": v = read(src, fh, "r", ("isobaricInhPa", 700)); return regrid(src, *v)
    if name == "wspd10":
        u = read(src, fh, "10u", ("heightAboveGround", 10)); w = read(src, fh, "10v", ("heightAboveGround", 10))
        return np.hypot(regrid(src, *u), regrid(src, *w))
    raise KeyError(name)

def cum(src, t):
    """Total precipitation (mm) from 0 to t h."""
    if t == 0: return 0.0
    st = steps(src, t)
    if f"0-{t}" in st: return regrid(src, *read(src, t, "tp", step=f"0-{t}"))
    # bucketed (NAM: 12 h buckets at 00Z): sum complete buckets + the open one
    total, start = 0.0, 0
    while start < t:
        cand = [s for s in steps(src, t if start + 12 > t else start + 12) if s.startswith(f"{start}-")]
        end = min(start + 12, t)
        if f"{start}-{end}" not in cand: raise KeyError(f"{src} tp {start}-{end} (have {cand})")
        total = total + regrid(src, *read(src, end, "tp", step=f"{start}-{end}"))
        start = end
    return total

def precip(src, a, b): return cum(src, b) - cum(src, a)

SRCS = [("recast", "Recast (NMMB cold start from GFS)"), ("nam", "Archived NAM"), ("gfs", "GFS")]
PLOTS = {
    "mslp":   dict(cmap="viridis", levels=np.arange(976, 1045, 4), units="hPa"),
    "z500":   dict(cmap="viridis", levels=np.arange(510, 600, 6), units="dam"),
    "t2m":    dict(cmap="RdYlBu_r", levels=np.arange(-30, 36, 3), units="°C"),
    "wspd10": dict(cmap="YlGnBu", levels=np.arange(0, 22, 2), units="m/s"),
    "rh700":  dict(cmap="BrBG", levels=np.arange(0, 101, 10), units="%"),
    "precip": dict(cmap="GnBu", levels=[0.25, 1, 2.5, 5, 10, 15, 20, 30, 40, 60, 80, 100], units="mm"),
}

def panel(fields, title, kind, fname):
    p = PLOTS[kind]
    fig, axs = plt.subplots(1, 3, figsize=(18, 5.2), subplot_kw=dict(projection=ccrs.LambertConformal(-100, 40)))
    for ax, (lab, f) in zip(axs, fields):
        ax.set_extent([-128, -62, 21, 56], ccrs.PlateCarree())
        ext = "max" if kind == "precip" else "both"
        cf = ax.contourf(LON, LAT, f, levels=p["levels"], cmap=p["cmap"], extend=ext, transform=ccrs.PlateCarree())
        ax.coastlines("50m", lw=0.5); ax.add_feature(cfeature.BORDERS, lw=0.4); ax.add_feature(cfeature.STATES, lw=0.2)
        ax.set_title(lab, fontsize=10)
    fig.colorbar(cf, ax=axs, shrink=0.8, label=p["units"])
    fig.suptitle(title, fontsize=12)
    fig.savefig(f"{OUT}/{fname}", dpi=90, bbox_inches="tight"); plt.close(fig)
    print("wrote", fname)

def main():
    global conus
    # CONUS land mask from GFS f000 land-sea mask
    lsm = regrid("gfs", *read("gfs", 0, "lsm"))
    conus = (lsm > 0.5) & (GLAT >= 25) & (GLAT <= 50) & (GLON >= 235) & (GLON <= 293)

    def stats(a, ref):
        d = (a - ref)[conus & np.isfinite(a) & np.isfinite(ref)]
        return np.sqrt(np.mean(d ** 2)), np.mean(d)

    rows = []
    LEADS = [int(x) for x in os.environ.get("LEADS", "24,48,84").split(",")]
    for fh in LEADS:
        for kind in ["mslp", "z500", "t2m", "wspd10", "rh700"]:
            f = {s: field(s, fh, kind) for s, _ in SRCS}
            panel([(lab, f[s]) for s, lab in SRCS], f"{kind}  f{fh:02d}  valid 2026-11-01 00Z +{fh} h", kind, f"{kind}_f{fh:02d}.png")
            if kind in ("mslp", "z500", "t2m", "wspd10"):
                rr, br = stats(f["recast"], f["nam"]); rg, bg = stats(f["gfs"], f["nam"])
                rows.append((kind, fh, rr, br, rg, bg))
    for b in [x for x in (24, 48, 72) if x <= max(LEADS)]:
        f = {s: precip(s, b - 6, b) for s, _ in SRCS}
        panel([(lab, f[s]) for s, lab in SRCS], f"6 h precipitation ending f{b:02d}", "precip", f"precip6h_f{b:02d}.png")
    for a, b in [(0, 24), (24, 48), (60, 84)]:
        if b > max(LEADS): continue
        f = {s: precip(s, a, b) for s, _ in SRCS}
        rr, br = stats(f["recast"], f["nam"]); rg, bg = stats(f["gfs"], f["nam"])
        rows.append((f"precip24h_{a}-{b}", b, rr, br, rg, bg))
    if max(LEADS) >= 84:
        f = {s: precip(s, 0, 84) for s, _ in SRCS}
        panel([(lab, f[s]) for s, lab in SRCS], "Total precipitation f00-f84", "precip", "precip_total_f84.png")

    units = dict(mslp="hPa", z500="dam", t2m="K", wspd10="m/s")
    with open(f"{OUT}/stats.csv", "w") as c, open(f"{OUT}/stats.md", "w") as m:
        c.write("field,lead,rmse_recast,bias_recast,rmse_gfs,bias_gfs\n")
        m.write("| Field | Lead | RMSE recast | bias recast | RMSE GFS | bias GFS | closer to NAM |\n|---|---|---|---|---|---|---|\n")
        for k, fh, rr, br, rg, bg in rows:
            u = units.get(k, "mm")
            c.write(f"{k},{fh},{rr:.3f},{br:.3f},{rg:.3f},{bg:.3f}\n")
            m.write(f"| {k} ({u}) | f{fh:02d} | {rr:.2f} | {br:+.2f} | {rg:.2f} | {bg:+.2f} | {'recast' if rr < rg else 'GFS'} |\n")
    print(open(f"{OUT}/stats.md").read())

if __name__ == "__main__":
    main()

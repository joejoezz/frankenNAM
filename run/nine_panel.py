#!/usr/bin/env python3
"""One 3x3 figure: rows 500 hPa height, MSLP, 6 h precipitation; columns FrankenNAM, archived NAM, GFS.

usage: nine_panel.py <case dir> <out png> [fh=48]
Reuses the readers in compare.py (same case layout, same 0.25 deg grid).
"""
import sys, os, datetime as dt
sys.argv, args = sys.argv[:1] + [sys.argv[1], os.path.dirname(os.path.abspath(sys.argv[2])) or "."], sys.argv[1:]
import compare as c
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs, cartopy.feature as cfeature

case, out = args[0], args[1]
fh = int(args[2]) if len(args) > 2 else 48
init = dt.datetime(2026, 11, 1, 0)
valid = init + dt.timedelta(hours=fh)
cols = [("recast", "FrankenNAM (NMMB, GFS cold start)"), ("nam", "Archived NAM (operational)"), ("gfs", "GFS 0.25°")]
rows = [
    ("z500",   "500 hPa height", c.PLOTS["z500"],   lambda s: c.field(s, fh, "z500"),   np.arange(510, 600, 6)),
    ("mslp",   "MSLP",           c.PLOTS["mslp"],   lambda s: c.field(s, fh, "mslp"),   np.arange(976, 1045, 4)),
    ("precip", f"6 h precip, f{fh-6:02d}-f{fh:02d}", dict(cmap="GnBu", levels=[0.5, 1, 2, 4, 6, 8, 10, 15, 20, 30, 50], units="mm"), lambda s: c.precip(s, fh - 6, fh), None),
]
fig, axs = plt.subplots(3, 3, figsize=(16, 10.2), layout="constrained", subplot_kw=dict(projection=ccrs.LambertConformal(-100, 40)))
for r, (kind, rlab, p, get, clev) in enumerate(rows):
    for j, (src, clab) in enumerate(cols):
        ax = axs[r, j]; f = get(src)
        ax.set_extent([-128, -62, 21, 56], ccrs.PlateCarree())
        ext = "max" if kind == "precip" else "both"
        cf = ax.contourf(c.LON, c.LAT, f, levels=p["levels"], cmap=p["cmap"], extend=ext, transform=ccrs.PlateCarree())
        if clev is not None:
            ax.contour(c.LON, c.LAT, f, levels=clev, colors="k", linewidths=0.4, transform=ccrs.PlateCarree())
        ax.coastlines("50m", lw=0.5); ax.add_feature(cfeature.BORDERS, lw=0.4); ax.add_feature(cfeature.STATES, lw=0.2)
        if r == 0: ax.set_title(clab, fontsize=12)
        if j == 0: ax.text(-0.02, 0.5, rlab, transform=ax.transAxes, rotation=90, va="center", ha="right", fontsize=12)
    fig.colorbar(cf, ax=axs[r, :], shrink=0.9, pad=0.01, label=p["units"])
fig.suptitle(f"FrankenNAM vs archived NAM vs GFS   init {init:%Y-%m-%d %HZ}   f{fh:02d} valid {valid:%Y-%m-%d %HZ}", fontsize=14)
fig.savefig(out, dpi=110, bbox_inches="tight"); print("wrote", out)

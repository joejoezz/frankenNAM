"""Figure layout and drawing. Style follows ensplots: white page, black MSLP isobars with labels,
discrete WeatherBell-style colour bars, DejaVu Sans, thin dark state/coast lines.
Plot text is terse on purpose (plot-labeling rules): a title, one valid-time line, the colour
bar with units. Everything explanatory lives in the viewer's "?" box."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from functools import lru_cache

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import ListedColormap, BoundaryNorm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from . import colormaps as cm  # noqa: E402
from .fields import hl_centres  # noqa: E402

BASE_DIR = os.path.join(os.path.dirname(__file__), "base")
WIDTH_PX = 1400
DPI = 100
M_SIDE, M_TOP, M_BOT = 12, 56, 78     # px

PRODUCTS = {
    "nam": ("NAM 12 km", "Archived operational NAM (reference sample, not FrankenNAM). NOAA/NCEP via AWS Open Data."),
    "frankennam": ("FrankenNAM 12 km", "Initialized from the {s}Z GFS analysis with a 6 h NAM spin-up. No observations after {s}Z. "
                                       "A community recast of the retired NAM; not affiliated with NOAA."),
}


def foot_text(product, init):
    """Footer line for a product; FrankenNAM's names the GFS analysis it starts from (cycle - 6 h)."""
    return PRODUCTS[product][1].replace("{s}", f"{(init.hour - 6) % 24:02d}")
WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MO = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def stamp(d: datetime) -> str:
    return f"{d.hour:02d}z {WD[d.weekday()]} {d.day} {MO[d.month - 1]}"


@lru_cache(maxsize=4)
def base_lines(crs_key: str, fwd):
    """Projected segments of coast, borders, states, lakes (metres on the grid plane)."""
    out = {}
    for name in ("lakes", "states", "borders", "coast"):
        with open(os.path.join(BASE_DIR, f"{name}.json")) as f:
            feats = json.load(f)["features"]
        segs = []
        for ft in feats:
            c = np.asarray(ft["geometry"]["coordinates"], dtype=float)
            if len(c) < 2:
                continue
            x, y = fwd.transform(c[:, 0], c[:, 1])
            segs.append(np.column_stack([x, y]))
        out[name] = segs
    with open(os.path.join(BASE_DIR, "cities.json")) as f:
        cities = json.load(f)["features"]
    xs, ys = fwd.transform([c["geometry"]["coordinates"][0] for c in cities],
                           [c["geometry"]["coordinates"][1] for c in cities])
    out["cities"] = [(c["properties"]["name"], c["properties"]["rank"], x, y) for c, x, y in zip(cities, xs, ys)]
    return out


def _bbox_filter(segs, ext, pad=0.0):
    x0, x1, y0, y1 = ext
    keep = []
    for s in segs:
        if s[:, 0].max() >= x0 and s[:, 0].min() <= x1 and s[:, 1].max() >= y0 and s[:, 1].min() <= y1:
            keep.append(s)
    return keep


def make_fig(ext):
    x0, x1, y0, y1 = ext
    ax_w = WIDTH_PX - 2 * M_SIDE
    ax_h = int(round(ax_w * (y1 - y0) / (x1 - x0)))
    h = ax_h + M_TOP + M_BOT
    fig = plt.figure(figsize=(WIDTH_PX / DPI, h / DPI), dpi=DPI, facecolor="white")
    ax = fig.add_axes([M_SIDE / WIDTH_PX, M_BOT / h, ax_w / WIDTH_PX, ax_h / h])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_linewidth(0.8)
        sp.set_color("#333")
    return fig, ax, h


def draw_frame(layers, *, grid, ext, base, product, title, init, fhr, period_note, out_path, region_scale):
    fig, ax, h = make_fig(ext)
    x0, x1, y0, y1 = ext
    gx0, gx1, gy0, gy1 = grid.extent
    cbar = None
    legend_patches = None
    for L in layers:
        k = L["kind"]
        if k == "fill":
            cmap, norm, bounds = cm.build(L["scale"], L["top"], L.get("clip", False))
            ax.imshow(L["data"], origin="lower", extent=(gx0, gx1, gy0, gy1), cmap=cmap, norm=norm,
                      interpolation="bilinear", interpolation_stage="data", alpha=0.9, zorder=1, aspect="auto")
            cbar = (cmap, norm, bounds, L["ticks"], L["unit"])
        elif k == "ptype":
            cols = ["#00000000"] + [c for _, c in cm.PTYPE]
            ax.imshow(L["data"], origin="lower", extent=(gx0, gx1, gy0, gy1), cmap=ListedColormap(cols),
                      norm=BoundaryNorm(np.arange(-0.5, 5), 5), interpolation="nearest", alpha=0.92, zorder=1, aspect="auto")
            legend_patches = [Patch(fc=c, ec="none", label=n) for n, c in cm.PTYPE]
    # base lines
    for name, lw, col, z in (("lakes", 0.5, "#4a4a4a", 2), ("states", 0.5, "#555555", 2),
                             ("borders", 0.8, "#333333", 3), ("coast", 0.9, "#222222", 3)):
        segs = _bbox_filter(base[name], ext)
        ax.add_collection(LineCollection(segs, colors=col, linewidths=lw, zorder=z))
    # lines
    for L in layers:
        k = L["kind"]
        if k == "contour":
            lev = [v for v in L["levels"] if np.nanmin(L["data"]) <= v <= np.nanmax(L["data"])]
            if not lev:
                continue
            ls = [(0, (4, 2.5))] if L["dashed"] else "solid"
            cs = ax.contour(grid.x, grid.y, L["data"], levels=lev, colors=L["color"], linewidths=L["width"],
                            linestyles=ls, zorder=5)
            if L["bold"] is not None and L["bold"] in lev:
                ax.contour(grid.x, grid.y, L["data"], levels=[L["bold"]], colors=L["color"],
                           linewidths=L["width"] * 1.8, linestyles=ls, zorder=5)
            if L["labels"]:
                try:
                    texts = ax.clabel(cs, fmt=L["fmt"], fontsize=7.5, inline=True, inline_spacing=3, colors=L["color"])
                    for t in texts:
                        t.set_path_effects([])
                except Exception:   # a level may have no label-able segment in this window
                    pass
        elif k == "barbs":
            s = 14 if region_scale == "wide" else 6
            xs, ys = np.meshgrid(grid.x[::s], grid.y[::s])
            u, v = L["u"][::s, ::s], L["v"][::s, ::s]
            m = (xs > x0) & (xs < x1) & (ys > y0) & (ys < y1) & np.isfinite(u) & np.isfinite(v)
            ax.barbs(xs[m], ys[m], u[m], v[m], length=5.2, linewidth=0.55, color="#202020", zorder=6,
                     barb_increments=dict(half=5, full=10, flag=50))
        elif k == "hl":
            r = 24 if region_scale == "wide" else 30
            for kind, val, i, j in hl_centres(L["data"], radius=r):
                x, y = grid.x[j], grid.y[i]
                if x0 < x < x1 and y0 < y < y1:
                    col = "#d9302c" if kind == "L" else "#1a4fd8"
                    ax.text(x, y, kind, color=col, fontsize=17, fontweight="bold", ha="center", va="center", zorder=8,
                            path_effects=_halo())
                    ax.text(x, y - (y1 - y0) * 0.032, str(val), color="#000", fontsize=8, ha="center", va="center",
                            zorder=8, path_effects=_halo())
    # cities
    rank_max = 3 if region_scale == "wide" else 6
    xr, yr = (x1 - x0), (y1 - y0)
    for name, rank, x, y in base["cities"]:
        if rank <= rank_max and x0 + 0.01 * xr < x < x1 - 0.06 * xr and y0 + 0.01 * yr < y < y1 - 0.01 * yr:
            ax.plot([x], [y], "o", ms=2.2, color="#333", zorder=7)
            ax.text(x + 0.006 * xr, y, name, fontsize=7.5, color="#222", va="center", zorder=7, path_effects=_halo())
    # title block
    pname = PRODUCTS[product][0]
    foot = foot_text(product, init)
    valid = init + timedelta(hours=fhr)
    fig.text(M_SIDE / WIDTH_PX, 1 - 16 / h, title, fontsize=13.5, fontweight="bold", va="center")
    sub = f"{pname} · init {stamp(init)} · f{fhr:03d} · valid {stamp(valid)}"
    if period_note:
        sub += f" · {period_note}"
    fig.text(M_SIDE / WIDTH_PX, 1 - 37 / h, sub, fontsize=10, color="#555", va="center")
    # colour bar
    cb_y = (M_BOT - 40) / h
    if cbar is not None:
        cmap, norm, bounds, ticks, unit = cbar
        cax = fig.add_axes([(M_SIDE + 14) / WIDTH_PX, cb_y, (WIDTH_PX - 2 * M_SIDE - 74) / WIDTH_PX, 12 / h])
        n = len(bounds) - 1
        colors = [cmap(i) for i in range(n)]
        cax.imshow(np.arange(n)[None, :], aspect="auto", cmap=ListedColormap(colors), extent=(0, n, 0, 1))
        pos = []
        labs = []
        for t in ticks:
            if t in bounds:
                pos.append(bounds.index(t))
                labs.append(f"{t:g}")
        cax.set_xticks(pos)
        cax.set_xticklabels(labs, fontsize=8.5)
        cax.set_yticks([])
        cax.tick_params(length=3, width=0.6, pad=2)
        for sp in cax.spines.values():
            sp.set_linewidth(0.5)
        fig.text((WIDTH_PX - M_SIDE) / WIDTH_PX, cb_y + 6 / h, unit, fontsize=9, ha="right", va="center", color="#333")
    elif legend_patches:
        fig.legend(handles=legend_patches, loc="lower left", bbox_to_anchor=(M_SIDE / WIDTH_PX, (M_BOT - 46) / h),
                   ncol=4, frameon=False, fontsize=9.5, handlelength=1.6, columnspacing=1.8, borderaxespad=0)
    fig.text(M_SIDE / WIDTH_PX, 9 / h, foot, fontsize=8, color="#777", va="center")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # 256-colour palette PNG: ~3x smaller than RGB, visually the same for flat discrete fills
    fig.canvas.draw()
    from PIL import Image
    im = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB")
    im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(out_path, optimize=True)
    plt.close(fig)


def _halo():
    import matplotlib.patheffects as pe
    return [pe.withStroke(linewidth=2.2, foreground="white")]

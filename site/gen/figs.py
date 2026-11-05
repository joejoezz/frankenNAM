#!/usr/bin/env python3
"""Validation-page figures (needs matplotlib and pillow: use the site venv).

    ~/data/nam-recast-site/venv/bin/python site/gen/figs.py [--frames ~/data/nam-recast-site/out/frames]

Writes into site/pages/img/:
  rmse-vs-lead.png   RMSE against the archived NAM by lead, from docs/figs/tm06/stats.csv
  soil-f00.png       f00 soil trace, from docs/figs/tm06/soil.md
  panel-*.png        FrankenNAM | archived NAM, same field, hour and scale, from the rendered frames
                     (both are renders of the 2026-11-01 00Z products by site/render)
"""
from __future__ import annotations

import argparse
import csv
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
REPO = os.path.dirname(SITE)
OUT = os.path.join(SITE, "pages", "img")
INK, FN, ANL, GFS = "#1a1a1a", "#1f3fd6", "#d9822b", "#8a8a8a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#999", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 11})

PANELS = [  # file, field, hour
    ("panel-f48-mslp-precip", "mslp_precip6", 48),
    ("panel-f24-t2m", "t2m", 24),
    ("panel-f36-ptype", "ptype", 36),
    ("panel-f72-snow", "snowku", 72),
]


def rmse_vs_lead():
    rows = list(csv.DictReader(open(os.path.join(REPO, "docs/figs/tm06/stats.csv"))))
    fields = [("mslp", "MSLP (hPa)"), ("z500", "Z500 (dam)"), ("t2m", "2 m temperature (K)"), ("wspd10", "10 m wind speed (m/s)")]
    fig, axs = plt.subplots(1, 4, figsize=(11.5, 3.1), dpi=150)
    for ax, (f, t) in zip(axs, fields):
        rs = sorted((r for r in rows if r["field"] == f), key=lambda r: int(r["lead"]))
        x = [int(r["lead"]) for r in rs]
        for col, c, lab, z in (("rmse_GFS_vs_NAM", GFS, "GFS", 1), ("rmse_anl_vs_NAM", ANL, "analysis start", 2), ("rmse_tm06_vs_NAM", FN, "FrankenNAM tm06", 3)):
            ax.plot(x, [float(r[col]) for r in rs], "-o", color=c, lw=2, ms=4.5, label=lab, zorder=z)
        ax.set_title(t); ax.set_xticks(x); ax.set_xlabel("lead (h)"); ax.set_ylim(bottom=0); ax.grid(axis="y", color="#e6e6e6")
    axs[0].set_ylabel("RMSE against archived NAM")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(os.path.join(OUT, "rmse-vs-lead.png")); plt.close(fig)


def soil():
    t = open(os.path.join(REPO, "docs/figs/tm06/soil.md")).read()
    def cell(name, col):   # col index in the table after the field name
        m = re.search(r"^\| %s \([^)]*\) \|(.*)$" % re.escape(name), t, re.M)
        return float(m.group(1).split("|")[col].split("/")[0])
    # columns: tm06 vs seed, tm06 vs NAM, tm06 vs GFS, tm06 vs anl, anl vs GFS, anl vs NAM, NAM vs seed
    spec = [("sm0", "Soil moisture 0-10 cm (m$^3$/m$^3$)", "{:.3f}"), ("st0", "Soil temperature 0-10 cm (K)", "{:.2f}")]
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.0), dpi=150)
    for ax, (n, title, fmt) in zip(axs, spec):
        vals = [cell(n, 1), cell(n, 5), cell(n, 2)]
        labs = ["FrankenNAM\nvs NAM", "analysis start\nvs NAM", "FrankenNAM\nvs GFS"]
        bars = ax.bar(labs, vals, color=[FN, ANL, GFS], width=0.62)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v), ha="center", va="bottom", fontsize=9)
        ax.set_title(title); ax.set_ylim(0, max(vals) * 1.18); ax.tick_params(axis="x", labelsize=8.5); ax.grid(axis="y", color="#e6e6e6"); ax.set_axisbelow(True)
    axs[0].set_ylabel("RMSE, CONUS land, f00")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "soil-f00.png")); plt.close(fig)


def panels(frames, cycle="2026110100", region="conus"):
    for name, field, h in PANELS:
        ims = []
        for m in ("frankennam", "nam"):
            p = os.path.join(frames, m, cycle, region, f"{h:03d}-{field}.png")
            ims.append(Image.open(p).convert("RGB"))
        w, hh = ims[0].size
        gap = 8
        canvas = Image.new("RGB", (2 * w + gap, hh), "#cccccc")
        canvas.paste(ims[0], (0, 0)); canvas.paste(ims[1], (w + gap, 0))
        canvas = canvas.resize((2000, round(hh * 2000 / (2 * w + gap))), Image.LANCZOS)
        canvas.quantize(256).save(os.path.join(OUT, name + ".png"), optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=os.path.expanduser("~/data/nam-recast-site/out/frames"))
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rmse_vs_lead(); soil(); panels(a.frames)
    print("wrote", sorted(os.listdir(OUT)))

#!/usr/bin/env python3
"""Validation-page figures (needs matplotlib and pillow: use the site venv).

    ~/data/nam-recast-site/venv/bin/python site/gen/figs.py

Writes into site/pages/img/:
  g2g-lead-wide.png, g2g-lead-narrow.png   RMS difference from the archived NAM by lead, from verify/results/phase1b/g2g.csv
"""
from __future__ import annotations

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
REPO = os.path.dirname(SITE)
OUT = os.path.join(SITE, "pages", "img")
INK, FN, OR, GFS = "#1a1a1a", "#1f3fd6", "#d9822b", "#555555"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#999", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 11})

def g2g_lead():
    """RMS difference from the archived NAM against forecast hour, five cases pooled (validation.pooled), one panel per field.
    Writes a wide 3 x 2 version and a narrow single-column version for phones."""
    sys.path.insert(0, HERE)
    import validation as V
    P = V.pooled()
    style = {"fnam": (FN, "-", "o", "FrankenNAM", 4), "gfs": (OR, "-", "s", "GFS", 2), "gfs06": (GFS, "--", "^", "GFS from 6 h earlier (FrankenNAM's start)", 3)}
    titles = {"mslp": "Sea-level pressure (hPa)", "z500": "500 hPa height (dam)", "t2m": "2 m temperature (K)", "td2m": "2 m dew point (K)",
              "wspd10": "10 m wind speed (m/s)", "precip24": "24 h precipitation (mm)"}
    for tag, (rows, cols, size) in {"wide": (2, 3, (11, 6.6)), "narrow": (6, 1, (5.2, 14.5))}.items():
        fig, axs = plt.subplots(rows, cols, figsize=size, dpi=150 if tag == "wide" else 130)
        for ax, (k, _) in zip(axs.ravel(), V.FIELDS):
            for m, (c, ls, mk, lab, z) in style.items():
                xs = sorted(l for (f, mm, l) in P if f == k and mm == m)
                ax.plot(xs, [P[(k, m, l)][0] for l in xs], ls, color=c, marker=mk, lw=2.2 if m == "fnam" else 1.8, ms=5, label=lab, zorder=z)
            ax.set_title(titles[k]); ax.set_ylim(bottom=0); ax.grid(axis="y", color="#e6e6e6"); ax.set_axisbelow(True)
            ax.set_xlabel("forecast hour" + (" (window ends)" if k == "precip24" else "")); ax.set_ylabel("RMS difference")
            ax.set_xticks([24, 48, 84] if k == "precip24" else range(0, 85, 12))
        h, l = axs.ravel()[0].get_legend_handles_labels()
        fig.suptitle("Distance from the archived NAM, five cases pooled. Lower = closer to the NAM." if tag == "wide" else "Distance from the archived NAM\nFive cases pooled. Lower = closer to the NAM.", fontsize=11 if tag == "wide" else 10, fontweight="bold")
        fig.tight_layout(rect=(0, 0.07 if tag == "wide" else 0.045, 1, 0.97 if tag == "wide" else 0.975))
        fig.legend(h, l, loc="lower center", ncol=3 if tag == "wide" else 1, frameon=False, fontsize=9.5)
        fig.savefig(os.path.join(OUT, f"g2g-lead-{tag}.png")); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    g2g_lead()   # side-by-side panels are loopers over the rendered frames (validation.py)
    print("wrote", sorted(os.listdir(OUT)))

import argparse
import os
import shutil
import sys
import time

from .api import render_cycle, render_frame, FIELDS, REGIONS


def main(argv=None):
    ap = argparse.ArgumentParser(prog="render", description="Render one cycle of grid-218 awphys GRIB2 to PNG frames.")
    ap.add_argument("--cycle", required=True, help="YYYYMMDDHH")
    ap.add_argument("--src", required=True, help="directory or URL prefix holding nam.tCCz.awphysFF.tm00.grib2 (+ .idx)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fields", default="all", help="comma list or 'all': " + ",".join(FIELDS))
    ap.add_argument("--regions", default="conus", help="comma list or 'all': " + ",".join(REGIONS))
    ap.add_argument("--fhrs", default=None, help="comma list or a:b:step; default every file present")
    ap.add_argument("--model", default="nam", help="folder name under frames/ (nam = archived sample; frankennam)")
    ap.add_argument("--product", default="nam", choices=["nam", "frankennam"], help="which footer line the PNGs carry")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--no-viewer", action="store_true", help="do not copy the viewer page into --out")
    a = ap.parse_args(argv)
    fields = list(FIELDS) if a.fields == "all" else a.fields.split(",")
    regions = list(REGIONS) if a.regions == "all" else a.regions.split(",")
    hours = None
    if a.fhrs:
        if ":" in a.fhrs:
            lo, hi, st = (int(x) for x in a.fhrs.split(":"))
            hours = list(range(lo, hi + 1, st))
        else:
            hours = [int(x) for x in a.fhrs.split(",")]
    src = os.path.expanduser(a.src) if "://" not in a.src else a.src
    out = os.path.expanduser(a.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    render_cycle(a.cycle, src, out, fields, regions, hours, a.model, a.product, a.workers)
    if not a.no_viewer:
        vdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "viewer")
        if os.path.isdir(vdir):
            for n in os.listdir(vdir):
                if os.path.isfile(os.path.join(vdir, n)):
                    shutil.copy(os.path.join(vdir, n), os.path.join(out, n))
    print(f"done in {time.time() - t0:.0f}s -> {out}")

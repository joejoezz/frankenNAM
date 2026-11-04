"""render_frame(cycle, field, region, fhr, ...) is the unit of work (one PNG), the Lambda-shaped
function. render_cycle fans it out over processes for the whole cycle and writes the index files
the viewer reads."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np

from . import acc, draw, source
from .fields import FIELDS, INSTANT, NEEDS_ACC
from .regions import REGIONS, Grid

HOURS = list(range(0, 85, 3))


def frame_path(out, model, cycle, region, fhr, field):
    return os.path.join(out, "frames", model, cycle, region, f"{fhr:03d}-{field}.png")


@lru_cache(maxsize=1)
def _grid(src, cycle):
    return Grid(source.grid_info(src, cycle))


# one decoded frame per process: all fields of an fhr share one set of byte-range reads
_FRAME = {}


def _frame(src, cycle, fhr, work):
    key = (src, cycle, fhr)
    if key not in _FRAME:
        _FRAME.clear()
        d = source.read_messages(src, cycle, fhr, INSTANT)
        c = acc.cumulative(src, cycle, fhr, work)
        t = {"apcp": c["apcp"], "weasd": c["weasd"], "kuch": c["kuch"]}
        if c["apcp"] is not None:
            if fhr >= 6:
                prev = acc.cumulative(src, cycle, fhr - 6, work)["apcp"]
                t["p6"] = None if prev is None else np.clip(c["apcp"] - prev, 0, None)
                t["p6_label"] = "6 h precip"
            elif fhr > 0:
                t["p6"] = c["apcp"]
                t["p6_label"] = f"{fhr} h precip"
        _FRAME[key] = (d, t)
    return _FRAME[key]


def render_frame(cycle, field, region, fhr, src, out, model="nam", product="nam", work=None):
    """Render one PNG. Returns its path, or None when the field has no frame at this hour
    (accumulation fields at f00)."""
    title, _tab, fn, _help = FIELDS[field]
    grid = _grid(src, cycle)
    d, t = _frame(src, cycle, fhr, work or os.path.join(out, "_work", cycle))
    if field in NEEDS_ACC and fhr == 0:
        return None
    layers, note = fn(d, t, fhr)
    if layers is None:
        return None
    ext = grid.region_extent(region)
    base = draw.base_lines(grid.crs, grid.fwd) if False else draw.base_lines(grid.crs, _Fwd(grid))
    init = datetime.strptime(cycle, "%Y%m%d%H").replace(tzinfo=timezone.utc)
    path = frame_path(out, model, cycle, region, fhr, field)
    wide = (ext[1] - ext[0]) > 2.5e6
    draw.draw_frame(layers, grid=grid, ext=ext, base=base, product=product, title=title, init=init, fhr=fhr,
                    period_note=note, out_path=path, region_scale="wide" if wide else "tight")
    return path


class _Fwd:
    """Hashable wrapper so base_lines can cache on the projection."""
    def __init__(self, g):
        self.g = g
    def __hash__(self):
        return hash(self.g.crs)
    def __eq__(self, o):
        return self.g.crs == o.g.crs
    def transform(self, x, y):
        return self.g.fwd.transform(x, y)


def _job(args):
    cycle, fhr, fields, regions, src, out, model, product = args
    n = 0
    for region in regions:
        for field in fields:
            if render_frame(cycle, field, region, fhr, src, out, model, product):
                n += 1
    return fhr, n


def available_hours(src, cycle):
    hrs = []
    for h in HOURS:
        try:
            source.idx(src, cycle, h)
            hrs.append(h)
        except (FileNotFoundError, OSError):
            pass
    return hrs


def render_cycle(cycle, src, out, fields=None, regions=("conus",), hours=None, model="nam", product="nam", workers=None,
                 log=print):
    t0 = time.time()
    fields = list(fields or FIELDS)
    hours = list(hours) if hours is not None else available_hours(src, cycle)
    work = os.path.join(out, "_work", cycle)
    # cycle totals must be sequential-safe: do them once, in order, before the pool
    t1 = time.time()
    for h in hours:
        acc.cumulative(src, cycle, h, work)
    log(f"totals: {time.time() - t1:.1f}s")
    import multiprocessing as mp
    workers = workers or min(os.cpu_count() or 2, 8)
    jobs = [(cycle, h, fields, list(regions), src, out, model, product) for h in hours]
    done = 0
    with mp.get_context("spawn").Pool(workers) as pool:
        for fhr, n in pool.imap_unordered(_job, jobs):
            done += n
            log(f"f{fhr:03d}: {n} frames")
    write_index(cycle, src, out, fields, list(regions), hours, model, product)
    log(f"{done} frames in {time.time() - t0:.0f}s")
    return done


def write_index(cycle, src, out, fields, regions, hours, model, product):
    """frames/<model>/<cycle>/index.json + .js, and runs.json + .js at the root (a .js twin of each
    so the viewer works from file:// where fetch of local JSON is blocked)."""
    grid = _grid(src, cycle)
    fdoc = {}
    for f in fields:
        title, tab, _fn, help_ = FIELDS[f]
        fdoc[f] = {"title": title, "tab": tab, "help": help_,
                   "hours": [h for h in hours if not (f in NEEDS_ACC and h == 0)]}
    rdoc = {r: {"label": REGIONS[r][0]} for r in regions}
    idx = {"model": model, "product": product, "label": draw.PRODUCTS[product][0], "foot": draw.PRODUCTS[product][1],
           "cycle": cycle, "hours": hours, "fields": fdoc, "regions": rdoc,
           "path": "frames/{model}/{cycle}/{region}/{fhr}-{field}.png",
           "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    base = os.path.join(out, "frames", model, cycle)
    os.makedirs(base, exist_ok=True)
    _write_pair(os.path.join(base, "index"), idx, f"window.__NAM_INDEX = window.__NAM_INDEX || {{}}; window.__NAM_INDEX[{json.dumps(model + '/' + cycle)}] = ")
    runs_path = os.path.join(out, "runs.json")
    runs = {"runs": {}}
    if os.path.exists(runs_path):
        runs = json.load(open(runs_path))
    runs["runs"].setdefault(model, [])
    if cycle not in runs["runs"][model]:
        runs["runs"][model] = sorted(runs["runs"][model] + [cycle], reverse=True)
    runs["labels"] = {**runs.get("labels", {}), model: draw.PRODUCTS[product][0]}
    runs["generated"] = idx["generated"]
    _write_pair(os.path.join(out, "runs"), runs, "window.__NAM_RUNS = ")


def _write_pair(stem, doc, js_prefix):
    txt = json.dumps(doc, separators=(",", ":"))
    open(stem + ".json", "w").write(txt)
    open(stem + ".js", "w").write(js_prefix + txt + ";\n")

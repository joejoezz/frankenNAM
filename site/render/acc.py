"""Cycle totals: run-total precipitation and snowfall, built from the accumulation buckets.
The NAM post writes buckets, not running totals: 0-3, 0-6, 0-9, 0-12, then 12-15 ... 12-24,
24-27 ... (12 h buckets restarting), plus 3 h pieces. Every cycle total is therefore a sum of
buckets from earlier files. Kuchera snowfall adds the 3-hourly step of liquid-equivalent snow
weighted by the mean of the ratios at the two ends of the step (the ensplots rule)."""
from __future__ import annotations

import os
import re
from functools import lru_cache

import numpy as np

from . import source
from .fields import KUCH_LEVELS, _clean

KUCHERA_T0 = 271.16   # K


def kuchera_ratio(tmax_k):
    d = KUCHERA_T0 - tmax_k
    return np.clip(np.where(d < 0, 12 + 2 * d, 12 + d), 0, None)


def column_tmax(t2, ps, tl: dict):
    """Warmest of 2 m and the levels above ground up to 500 hPa (level pressure below surface pressure)."""
    tmax = t2.copy()
    for p in KUCH_LEVELS:
        above = ps / 100.0 > p
        tmax = np.maximum(tmax, np.where(above, tl[p], -np.inf))
    return tmax


def bucket(src, cycle, fhr, var):
    """(start, array) of the longest accumulation bucket ending at fhr, or None."""
    ix = source.idx(src, cycle, fhr)
    best = None
    for r in ix.rows:
        if r[3] == var and r[4] == "surface":
            m = re.fullmatch(rf"(\d+)-{fhr} hour acc fcst", r[5])
            if m and (best is None or int(m.group(1)) < best[0]):
                best = (int(m.group(1)), r)
    if best is None:
        return None
    s, r = best
    arr = source.read_messages_row(src, cycle, fhr, r)
    return s, _clean(arr)


def cumulative(src: str, cycle: str, fhr: int, work: str | None = None) -> dict:
    """{'apcp','weasd','kuch','ratio'} totals from the start through fhr, all in mm (ratio unitless)."""
    cache = os.path.join(work, f"cum_f{fhr:03d}.npz") if work else None
    if cache and os.path.exists(cache):
        z = np.load(cache)
        return {k: z[k] for k in z.files}
    shape = (source.NY, source.NX)
    if fhr == 0:
        out = {"apcp": np.zeros(shape, np.float32), "weasd": np.zeros(shape, np.float32),
               "kuch": np.zeros(shape, np.float32), "ratio": None}
    else:
        out = {}
        for key, var in (("apcp", "APCP"), ("weasd", "WEASD")):
            b = bucket(src, cycle, fhr, var)
            if b is None:
                out[key] = None
                continue
            s, arr = b
            out[key] = cumulative(src, cycle, s, work)[key] + arr if s > 0 else arr
    # ratio at this step, then the Kuchera step
    want = {"t2": ("TMP", "2 m above ground", False), "ps": ("PRES", "surface", False)}
    want.update({f"t{p}": ("TMP", f"{p} mb", False) for p in KUCH_LEVELS})
    d = source.read_messages(src, cycle, fhr, want)
    ratio = kuchera_ratio(column_tmax(_clean(d["t2"]), _clean(d["ps"]), {p: _clean(d[f"t{p}"]) for p in KUCH_LEVELS}))
    out["ratio"] = ratio.astype(np.float32)
    if fhr > 0:
        prev = cumulative(src, cycle, fhr - 3, work)
        if out["weasd"] is None:
            out["kuch"] = None
        else:
            step = np.clip(out["weasd"] - prev["weasd"], 0, None)
            pr = prev["ratio"] if prev["ratio"] is not None else ratio
            out["kuch"] = prev["kuch"] + step * (pr + ratio) / 2
    if cache:
        os.makedirs(work, exist_ok=True)
        np.savez(cache, **{k: v for k, v in out.items() if v is not None})
    return out

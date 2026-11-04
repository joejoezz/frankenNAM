"""Reading grid-218 awphys files. Only the messages a field needs are read, located with the
.idx sidecar (byte ranges), so the same code reads a local directory or an HTTPS/S3/R2 prefix
and a Lambda fetches ~60 messages instead of a 60 MB file.

src is the directory (local) or URL prefix that holds the files, i.e. it ends in nam.YYYYMMDD.
File names are the operational NAM's: nam.tCCz.awphysFF.tm00.grib2 (+ .idx)."""
from __future__ import annotations

import os
import re
import tempfile
import urllib.request
from functools import lru_cache

import numpy as np
import eccodes as ec

NX, NY = 614, 428
ec.codes_grib_multi_support_on()   # 10 m and 850 hPa U/V share one message each


def fname(cycle: str, fhr: int) -> str:
    return f"nam.t{cycle[8:10]}z.awphys{fhr:02d}.tm00.grib2"


def _is_url(src: str) -> bool:
    return re.match(r"^https?://", src) is not None


def _read(src: str, cycle: str, fhr: int, suffix: str, rng: tuple[int, int] | None):
    name = fname(cycle, fhr) + suffix
    if _is_url(src):
        req = urllib.request.Request(f"{src.rstrip('/')}/{name}")
        if rng:
            req.add_header("Range", f"bytes={rng[0]}-{rng[1] - 1}")
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    with open(os.path.join(src, name), "rb") as f:
        if rng:
            f.seek(rng[0])
            return f.read(rng[1] - rng[0])
        return f.read()


class Idx:
    """Parsed .idx: entries (n, offset, var, level, step) with the end offset of each message."""

    def __init__(self, text: str, size: int | None):
        rows = []
        for ln in text.strip().splitlines():
            p = ln.split(":")
            rows.append((p[0], int(p[1]), p[3], p[4], p[5]))
        offs = sorted({r[1] for r in rows})
        end = {o: (offs[i + 1] if i + 1 < len(offs) else size) for i, o in enumerate(offs)}
        self.rows = [(n, o, end[o], v, lv, st) for n, o, v, lv, st in rows]

    def find(self, var: str, level: str, step: str):
        """Row whose var and level match exactly and whose step matches the regex."""
        for r in self.rows:
            if r[3] == var and r[4] == level and re.fullmatch(step, r[5]):
                return r
        return None


@lru_cache(maxsize=64)
def idx(src: str, cycle: str, fhr: int) -> Idx:
    text = _read(src, cycle, fhr, ".idx", None).decode()
    size = None
    if not _is_url(src):
        size = os.path.getsize(os.path.join(src, fname(cycle, fhr)))
    return Idx(text, size)


def step_re(fhr: int, acc: bool) -> str:
    if acc:
        return rf"0-{fhr} hour acc fcst"
    return r"anl" if fhr == 0 else rf"{fhr} hour fcst"


def read_messages(src: str, cycle: str, fhr: int, wanted: dict) -> dict[str, np.ndarray]:
    """wanted: key -> (var, level, acc). Returns key -> (NY, NX) float32, row 0 = south.
    A missing message (f00 accumulations) is simply absent from the result.
    One byte range per distinct message offset; a multi-field message (10 m U and V share one
    offset) yields one GRIB handle per field, in idx order."""
    ix = idx(src, cycle, fhr)
    by_off = {}
    for key, (var, level, acc) in wanted.items():
        r = ix.find(var, level, step_re(fhr, acc))
        if r is not None:
            by_off.setdefault((r[1], r[2]), []).append((float(r[0]), key))
    out = {}
    for rng, keys in by_off.items():
        keys.sort()
        blob = _read(src, cycle, fhr, "", rng)
        with tempfile.TemporaryFile() as tf:
            tf.write(blob)
            tf.flush()
            tf.seek(0)
            handles = []
            while True:
                g = ec.codes_grib_new_from_file(tf)
                if g is None:
                    break
                handles.append(g)
        # a multi-field offset lists all its fields in the idx; we asked for a subset of them
        allrows = sorted(float(r[0]) for r in ix.rows if (r[1], r[2]) == rng)
        for g, n in zip(handles, allrows):
            for _, key in keys:
                if _ == n:
                    out[key] = ec.codes_get_values(g).astype(np.float32).reshape(NY, NX)
            ec.codes_release(g)
    return out


def read_messages_row(src: str, cycle: str, fhr: int, row) -> np.ndarray:
    """Decode the single message of one idx row (n, start, end, var, level, step)."""
    blob = _read(src, cycle, fhr, "", (row[1], row[2]))
    g = ec.codes_new_from_message(blob)
    try:
        return ec.codes_get_values(g).astype(np.float32).reshape(NY, NX)
    finally:
        ec.codes_release(g)


@lru_cache(maxsize=1)
def grid_info(src: str, cycle: str):
    """Projection and lat/lon of grid 218 from the f00 header."""
    ix = idx(src, cycle, 0)
    r = ix.rows[0]
    blob = _read(src, cycle, 0, "", (r[1], r[2]))
    g = ec.codes_new_from_message(blob)
    keys = {k: ec.codes_get(g, k) for k in
            ("LoVInDegrees", "LaDInDegrees", "Latin1InDegrees", "Latin2InDegrees", "DxInMetres", "DyInMetres",
             "latitudeOfFirstGridPointInDegrees", "longitudeOfFirstGridPointInDegrees", "radius")}
    assert ec.codes_get(g, "scanningMode") == 64 and ec.codes_get(g, "Ni") == NX and ec.codes_get(g, "Nj") == NY
    ec.codes_release(g)
    return keys

#!/usr/bin/env python3
"""Frozen share of soil water in a NEMS initial-condition file (nemsinterp output input_domain_01_nemsio).

usage: ic_frozen.py <input_domain_01_nemsio> [more files]
Over cold land (layer-1 STC < 271 K, land = SM < 0.5 and SICE < 0.5) prints the mean frozen share
1 - sh2o/smc for the 0-10 cm and 10-40 cm layers (same definition as verify/frozen_soil.py, which
reads 1 - SOILL/SOILW from awphys GRIB2). The first file's layout is found by cmp_nemsio.nemsio_layout.
"""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cmp_nemsio import nemsio_layout

def names16(fn, hdr):
    """nemsio v2 header: three fortran-style blocks (each wrapped in 4-byte length markers), recname
    (16 chars each, starting with 'fis'), reclevtyp (16 chars each), reclev (int4)."""
    h = open(fn, "rb").read(hdr); s = h.find(b"fis             ")
    nbytes = int.from_bytes(h[s - 4:s], "big"); nrec = nbytes // 16
    rn = [h[s + 16 * k:s + 16 * k + 16].decode("latin1").strip() for k in range(nrec)]
    t0 = s + nbytes + 8; lt = [h[t0 + 16 * k:t0 + 16 * k + 16].decode("latin1").strip() for k in range(nrec)]
    l0 = t0 + nbytes + 8; lev = np.frombuffer(h[l0:l0 + 4 * nrec], dtype=">i4")
    return [f"{a}:{b}:{c}" for a, b, c in zip(rn, lt, lev)]

def load(fn):
    hdr, npts, _ = nemsio_layout(fn)
    names = names16(fn, hdr)
    a = np.fromfile(fn, dtype=">f4", offset=hdr); rec = npts + 2
    skip = a.size // rec - len(names)   # nemsinterp's file has 4 unnamed records ahead of the first named one (fis)
    return {n: a[(k + skip) * rec + 1:(k + skip + 1) * rec - 1] for k, n in enumerate(names)}

for fn in sys.argv[1:]:
    d = load(fn)
    key = lambda p, l: next(k for k in d if k.split(":")[0] == p and k.split(":")[-1] == str(l))   # first record of that name/level
    land = (d[key("sm", 1)] < 0.5) & (d[key("sice", 1)] < 0.5)
    stc1 = d[key("stc", 1)]; cold = land & (stc1 < 271)
    out = [f"{fn.split('/')[-3] if fn.count('/')>2 else fn}: cold land pts {cold.sum()} of {land.sum()}"]
    for lab, ls in (("0-10", [1]), ("10-40", [2])):
        fr = np.mean([1 - d[key("sh2o", l)][cold] / d[key("smc", l)][cold] for l in ls])
        out.append(f"frozen {lab} cm {fr:.3f}")
    out.append(f"mean STC1 {np.mean(stc1[cold]) - 273.15:.2f} C")
    print("  ".join(out))

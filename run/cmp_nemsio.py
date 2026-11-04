#!/usr/bin/env python3
"""Compare two nemsio (or any big-endian float32 record) files: bit-identical, or where they first
differ and how big the numeric differences are.

usage: cmp_nemsio.py <a> <b> [...more pairs as a b]
       cmp_nemsio.py --records [im jm] <a> <b>   per-record table for a nemsio file (bin4 records)
Prints one line per pair: IDENTICAL, or the first differing byte offset, the number of differing
4-byte words and the max absolute / relative difference of the finite float32 values that differ
(header text is compared as bytes only). Both files must have the same size. --records works out
the record size from the header (im, jm) and lists the records with the largest differences.
"""
import sys, re, numpy as np

def nemsio_layout(fname, npts=None):
    """(header bytes, nx*ny, [names]) for a nemsio bin4 file: im*jm given or guessed from the
    header ints, record names from the recname block (8-char entries), header length = what is
    left before whole records."""
    import os
    size = os.path.getsize(fname)
    head = open(fname, "rb").read(1 << 20)
    if npts is None:
        # guess im/jm: two big-endian ints in the first header record whose product divides the
        # file into whole bin4 records with a small remainder (prefer the largest such product)
        ints = np.frombuffer(head[:4096], dtype=">i4")
        cand = sorted({int(a) * int(b) for a in ints for b in ints if 100 < a < 5000 and 100 < b < 5000}, reverse=True)
        npts = next((c for c in cand if (size - size % (c * 4 + 8)) // (c * 4 + 8) > 10 and size % (c * 4 + 8) < 200000), None)
    if npts is None: return None, None, None
    rec = npts * 4 + 8; nrec = (size - 200) // rec; hdr = size - nrec * rec
    names = re.findall(rb"[a-z0-9_]{1,8}(?: {0,7})(?=[a-z0-9_ ]{8})", head[:hdr])
    toks = [head[:hdr][i:i + 8].decode("latin1") for i in range(0, hdr - 8, 1)]
    # recname block: nrec consecutive 8-byte tokens, all lowercase alnum/underscore padded with blanks
    ok = [bool(re.fullmatch(r"[a-z0-9_]+ *", t)) for t in toks]
    start = None
    for i in range(len(ok) - 8 * nrec):
        if all(ok[i + 8 * k] for k in range(nrec)): start = i; break
    recn = [toks[start + 8 * k].strip() for k in range(nrec)] if start is not None else [str(k) for k in range(nrec)]
    if start is not None:
        lt = head[start + 8 * nrec:start + 24 * nrec].decode("latin1")
        levtyp = [lt[16 * k:16 * k + 16].strip() for k in range(nrec)]
        lev = np.frombuffer(head[start + 24 * nrec:start + 28 * nrec], dtype=">i4")
        recn = [f"{n}:{t}:{l}" for n, t, l in zip(recn, levtyp, lev)]
    return hdr, npts, recn

def records(a, b, top=15, npts=None):
    hdr, npts, names = nemsio_layout(a, npts)
    if hdr is None: print("could not work out the record layout"); return
    A = np.fromfile(a, dtype=">f4", offset=hdr); B = np.fromfile(b, dtype=">f4", offset=hdr)
    rec = npts + 2; n = A.size // rec
    rows = []
    for k in range(n):
        x = A[k * rec + 1:(k + 1) * rec - 1]; y = B[k * rec + 1:(k + 1) * rec - 1]
        d = np.abs(x - y); m = np.isfinite(d)
        rows.append((float(d[m].max()) if m.any() else 0.0, float(np.sqrt(np.mean(d[m] ** 2))), int((d > 0).sum()),
                     float(np.abs(x[m]).max()) if m.any() else 0.0, names[k] if k < len(names) else str(k)))
    print(f"{n} records of {npts} points, header {hdr} bytes; records with any difference: {sum(r[2] > 0 for r in rows)}")
    print(f"{'record':32s} {'max|d|':>10s} {'rms d':>10s} {'ndiff':>8s} {'max|x|':>10s}")
    for r in sorted(rows, reverse=True)[:top]: print(f"{r[4]:32s} {r[0]:10.4g} {r[1]:10.3g} {r[2]:8d} {r[3]:10.4g}")

def cmp(a, b):
    A = np.fromfile(a, dtype=">f4"); B = np.fromfile(b, dtype=">f4")
    if A.size != B.size: return f"{a} vs {b}: SIZE DIFFERS {A.nbytes} vs {B.nbytes} bytes"
    rawdiff = (A.view(">u4") != B.view(">u4"))
    if not rawdiff.any(): return f"{a} vs {b}: IDENTICAL ({A.nbytes} bytes)"
    i0 = int(np.argmax(rawdiff)) * 4
    m = rawdiff & np.isfinite(A) & np.isfinite(B) & (np.abs(A) < 1e30) & (np.abs(B) < 1e30)
    d = np.abs(A[m] - B[m]); scale = np.maximum(np.abs(A[m]), 1e-30)
    return (f"{a} vs {b}: DIFFER first at byte {i0}; {int(rawdiff.sum())} of {A.size} words differ; "
            f"max |d| {d.max():.4g}, max rel {np.max(d / scale):.3g}, median rel {np.median(d / scale):.3g}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--records":
        if len(args) == 5: records(args[3], args[4], npts=int(args[1]) * int(args[2]))
        else: records(args[1], args[2])
        sys.exit()
    for a, b in zip(args[::2], args[1::2]): print(cmp(a, b))

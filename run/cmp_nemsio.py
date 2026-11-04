#!/usr/bin/env python3
"""Compare two nemsio (or any big-endian float32 record) files: bit-identical, or where they first
differ and how big the numeric differences are.

usage: cmp_nemsio.py <a> <b> [...more pairs as a b]
Prints one line per pair: IDENTICAL, or the first differing byte offset, the number of differing
4-byte words and the max absolute / relative difference of the finite float32 values that differ
(header text is compared as bytes only). Both files must have the same size.
"""
import sys, numpy as np

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
    for a, b in zip(args[::2], args[1::2]): print(cmp(a, b))

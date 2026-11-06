#!/usr/bin/env python3
"""Inventory diff of a GPU-path product against the CPU product for the same hour (wgrib2 .idx files).

usage: inventory_diff.py <cpu .idx> <gpu .idx>      prints OK/ORDER/DIFF counts and every record that differs.
A record is identified by VAR:level:time text without the offset and the reference date (d=); two files are the
same when the sequences of those lines are equal. Records only in one file are listed with their position.
"""
import difflib
import sys


def lines(p):
    out = []
    for l in open(p):
        f = l.rstrip("\n").split(":")
        out.append(":".join(f[3:]))
    return out


def main(cpu, gpu):
    a, b = lines(cpu), lines(gpu)
    only_a = [x for x in a if x not in set(b)]
    only_b = [x for x in b if x not in set(a)]
    common_a = [x for x in a if x in set(b)]
    common_b = [x for x in b if x in set(a)]
    order_same = common_a == common_b
    print(f"CPU {len(a)} records, GPU {len(b)} records, identical lines {len(set(a) & set(b))}, "
          f"order of the common records {'identical' if order_same else 'DIFFERS'}")
    if not order_same:
        sm = difflib.SequenceMatcher(None, common_a, common_b, autojunk=False)
        moved = sum(max(i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal")
        print(f"  order differences: {moved} records out of place")
    print(f"only in CPU ({len(only_a)}):")
    for x in only_a:
        print("  -", x)
    print(f"only in GPU ({len(only_b)}):")
    for x in only_b:
        print("  +", x)
    return 0 if not only_a and not only_b and order_same else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))

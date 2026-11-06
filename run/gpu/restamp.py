#!/usr/bin/env python3
"""Turn WOOF-NAM's awphys products (tm06 run, integration clock) into FrankenNAM's product (cycle clock).

WOOF-NAM writes woof-nam.tSSz.awphysII.tm00.grib2 with SS = the integration start (C-6 h) and II = hours since
that start. The product for cycle C is nam.tCCz.awphysFF.tm00.grib2, FF = II - 6, f00..f84 every 3 h, with
  - reference time C, forecast time FF in every record (instantaneous: II -> FF; max/min windows move 6 h);
  - the accumulation records rebuilt on the C clock the way run/products.sh builds them: APCP and ACPCP over the
    12 h bucket that began at b0 = 12*floor((FF-1)/12) (the sum of the 3 h buckets since b0, from the earlier
    files), plus the 3 h pair when the bucket is longer than 3 h; f00 carries the zero "0-0 day acc" records
    (templates/zero-acc-f00.grib2, cut from the CPU product);
  - the 1 h max/min records dropped at f00 (the CPU product has none there);
  - record order = master-order.txt (the CPU product's order), records the master does not know at the end;
  - a wgrib2 .idx.
Records WOOF-NAM does not write (WEASD 12 h snowfall, CSNOW/CRAIN/CFRZR/CICEP, BMIXL, LTNG, cloud-top VIS) are not
invented; run/gpu/inventory_diff.py lists them against the CPU file.

    restamp.py --raw DIR --out DIR --cycle 2026110100 [--hours 0,3,...,84] [--prefix woof-nam] [--lag 6]
needs: eccodes (python), wgrib2 on PATH (or --wgrib2).  Reads each source file once, prior files only for the 3 h buckets.
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import eccodes as ec

HERE = Path(__file__).resolve().parent
LAG = 6


def norm(line):
    p = line.rstrip().split(":")
    var, lev, t = p[3], p[4], p[5]
    k = "ACC" if "acc" in t else "MAX" if " max" in t else "MIN" if " min" in t else "INST"
    return f"{var}:{lev}:{k}"


def read_msgs(path):
    out = []
    with open(path, "rb") as f:
        while True:
            h = ec.codes_grib_new_from_file(f)
            if h is None:
                break
            out.append(h)
    return out


def raw_name(prefix, start, ii):
    return f"{prefix}.t{start:%H}z.awphys{ii:02d}.tm00.grib2"


def stat_of(h):
    return ec.codes_get(h, "stepType")


def short(h):
    return ec.codes_get(h, "shortName")


def bucket3(path):
    """{shortName: values} of the 3 h APCP/ACPCP records of one raw file (the narrowest accumulation window)."""
    best = {}
    for h in read_msgs(path):
        if stat_of(h) == "accum" and short(h) in ("tp", "acpcp"):
            n = ec.codes_get(h, "lengthOfTimeRange")
            if short(h) not in best or n < best[short(h)][0]:
                best[short(h)] = (n, ec.codes_get_values(h).copy())
        ec.codes_release(h)
    for k, (n, _) in best.items():
        if n != 3:
            raise RuntimeError(f"{path}: the narrowest {k} window is {n} h, expected 3")
    return {k: v for k, (n, v) in best.items()}


def set_cycle(h, cycle):
    ec.codes_set(h, "dataDate", int(f"{cycle:%Y%m%d}"))
    ec.codes_set(h, "dataTime", cycle.hour * 100)


def restamp_hour(raw_dir, out_dir, cycle, fh, prefix="woof-nam", lag=LAG, wgrib2="wgrib2"):
    """One product hour. Returns {file, records, missing, extra} (master-order bookkeeping)."""
    start = cycle - timedelta(hours=lag)
    ii = fh + lag
    src = Path(raw_dir) / raw_name(prefix, start, ii)
    if not src.is_file():
        raise FileNotFoundError(src)
    out = Path(out_dir) / f"nam.t{cycle:%H}z.awphys{fh:02d}.tm00.grib2"
    tmp = out.with_suffix(".grib2.part")
    msgs = read_msgs(src)
    keep = []                                   # (handle) restamped non-accumulation records
    carriers = {}                               # shortName -> an accumulation message to clone for the buckets
    for h in msgs:
        st = stat_of(h)
        if st == "accum":
            if short(h) in ("tp", "acpcp") and short(h) not in carriers:
                carriers[short(h)] = h
            continue
        if fh == 0 and st in ("max", "min"):
            continue                            # the CPU f00 file has no 1 h extremes
        set_cycle(h, cycle)
        ec.codes_set(h, "forecastTime", ec.codes_get(h, "forecastTime") - lag)
        keep.append(h)
    acc = []                                    # buckets, in the CPU file's order: 12 h APCP, ACPCP, then 3 h APCP, ACPCP
    if fh == 0:
        for h in read_msgs(HERE / "templates" / "zero-acc-f00.grib2"):
            set_cycle(h, cycle)
            acc.append(h)
    else:
        b0 = 12 * ((fh - 1) // 12)
        vals = {"tp": 0.0, "acpcp": 0.0}
        for s in range(b0 + 3, fh + 1, 3):                  # the 3 h buckets since b0, each from its own file
            b = bucket3(Path(raw_dir) / raw_name(prefix, start, s + lag))
            for k in vals:
                vals[k] = vals[k] + b[k]
        last = bucket3(src)                                 # this hour's own 3 h bucket (for the 3 h pair)
        def clone(kind, start_h, length, values):
            h = ec.codes_clone(carriers[kind])
            set_cycle(h, cycle)
            ec.codes_set(h, "forecastTime", start_h)
            ec.codes_set(h, "lengthOfTimeRange", length)
            ec.codes_set_values(h, values)
            return h
        for k in ("tp", "acpcp"):
            acc.append(clone(k, b0, fh - b0, vals[k]))
        if fh - b0 > 3:
            for k in ("tp", "acpcp"):
                acc.append(clone(k, fh - 3, 3, last[k]))
    allm = keep + acc
    # first pass file, to get wgrib2's names, then the master order
    with open(tmp, "wb") as f:
        for h in allm:
            ec.codes_write(h, f)
    inv = subprocess.run([wgrib2, str(tmp), "-s"], check=True, capture_output=True, text=True).stdout.splitlines()
    if len(inv) != len(allm):
        raise RuntimeError(f"{tmp}: wgrib2 sees {len(inv)} records, wrote {len(allm)}")
    pool = {}
    for i, l in enumerate(inv):
        pool.setdefault(norm(l), []).append(i)
    master = [l.strip() for l in (HERE / "master-order.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    order, missing = [], []
    for k in master:
        if pool.get(k):
            order.append(pool[k].pop(0))
        else:
            missing.append(k)
    extra = [(k, i) for k, v in pool.items() for i in v]
    order += sorted(i for _, i in extra)
    with open(out.with_suffix(".grib2.part2"), "wb") as f:
        for i in order:
            ec.codes_write(allm[i], f)
    for h in msgs + acc:
        ec.codes_release(h)
    tmp.unlink()
    p2 = out.with_suffix(".grib2.part2")
    idx = subprocess.run([wgrib2, str(p2), "-s"], check=True, capture_output=True, text=True).stdout
    Path(str(out) + ".idx.part").write_text(idx)
    os.replace(p2, out)
    os.replace(str(out) + ".idx.part", str(out) + ".idx")     # the .idx lands whole and last: its existence = file complete
    return {"file": out.name, "records": len(order), "missing": missing, "extra": [k for k, _ in extra]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cycle", required=True, help="YYYYMMDDHH of the product cycle C")
    ap.add_argument("--hours", default=",".join(str(h) for h in range(0, 85, 3)), help="product hours FF (default 0..84 by 3)")
    ap.add_argument("--prefix", default="woof-nam")
    ap.add_argument("--lag", type=int, default=LAG)
    ap.add_argument("--wgrib2", default="wgrib2")
    a = ap.parse_args()
    cycle = datetime.strptime(a.cycle, "%Y%m%d%H")
    a.out.mkdir(parents=True, exist_ok=True)
    for fh in [int(x) for x in a.hours.split(",")]:
        r = restamp_hour(a.raw, a.out, cycle, fh, a.prefix, a.lag, a.wgrib2)
        print(f"f{fh:02d} {r['records']} records, missing vs master {len(r['missing'])}, extra {len(r['extra'])}", flush=True)


if __name__ == "__main__":
    main()

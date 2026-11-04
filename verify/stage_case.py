#!/usr/bin/env python3
"""Check and stage one hindcast case: server-side copies from the public NOAA buckets into
s3://nam-recast-617711905691/cases/<C>/ (us-east-1 -> us-west-2).
usage: stage_case.py YYYYMMDDHH [--ref-arm] [--check-only]
Layout: gfs-tm06/ (P-cycle pgrb2.0p25 f000..f090 /3), nam-archive/ (awphys00..84 /3 of C + P awphys00),
        gfs/ (C-cycle pgrb2.0p25 f000..f084 /3, only with --ref-arm), MANIFEST.txt
"""
import sys, subprocess, datetime as dt, json
from concurrent.futures import ThreadPoolExecutor
OURS = "nam-recast-617711905691"
def ls(bucket, prefix):
    out = subprocess.run(["aws", "s3api", "list-objects-v2", "--bucket", bucket, "--prefix", prefix, "--no-sign-request",
                          "--region", "us-east-1", "--query", "Contents[].[Key,Size]", "--output", "json"],
                         capture_output=True, text=True)
    return {k: s for k, s in (json.loads(out.stdout) or [])} if out.stdout.strip() not in ("", "null") else {}
def plan(c, ref_arm):
    C = dt.datetime.strptime(c, "%Y%m%d%H"); P = C - dt.timedelta(hours=6)
    cd, pd, ch, ph = C.strftime("%Y%m%d"), P.strftime("%Y%m%d"), C.strftime("%H"), P.strftime("%H")
    items = []   # (src bucket, src key, dest key)
    for f in range(0, 85, 3):
        n = f"nam.t{ch}z.awphys{f:02d}.tm00.grib2"
        items += [("noaa-nam-pds", f"nam.{cd}/{n}", f"nam-archive/{n}"), ("noaa-nam-pds", f"nam.{cd}/{n}.idx", f"nam-archive/{n}.idx")]
    n = f"nam.t{ph}z.awphys00.tm00.grib2"
    items += [("noaa-nam-pds", f"nam.{pd}/{n}", f"nam-archive/{n}"), ("noaa-nam-pds", f"nam.{pd}/{n}.idx", f"nam-archive/{n}.idx")]
    for f in range(0, 91, 3):
        n = f"gfs.t{ph}z.pgrb2.0p25.f{f:03d}"
        items += [("noaa-gfs-bdp-pds", f"gfs.{pd}/{ph}/atmos/{n}", f"gfs-tm06/{n}"), ("noaa-gfs-bdp-pds", f"gfs.{pd}/{ph}/atmos/{n}.idx", f"gfs-tm06/{n}.idx")]
    if ref_arm:
        for f in range(0, 85, 3):
            n = f"gfs.t{ch}z.pgrb2.0p25.f{f:03d}"
            items += [("noaa-gfs-bdp-pds", f"gfs.{cd}/{ch}/atmos/{n}", f"gfs/{n}"), ("noaa-gfs-bdp-pds", f"gfs.{cd}/{ch}/atmos/{n}.idx", f"gfs/{n}.idx")]
    return items
def main():
    c = sys.argv[1]; ref = "--ref-arm" in sys.argv; check = "--check-only" in sys.argv
    items = plan(c, ref)
    prefixes = {(b, k.rsplit("/", 1)[0] + "/") for b, k, _ in items}
    have = {}
    for b, p in prefixes: have.update({(b, k): s for k, s in ls(b, p).items()})
    missing = [(b, k) for b, k, _ in items if (b, k) not in have]
    tot = sum(have[(b, k)] for b, k, _ in items if (b, k) in have)
    print(f"{c}: {len(items)} objects, {len(missing)} missing, {tot/1e9:.1f} GB")
    for m in missing: print("MISSING", m)
    if check or missing: return 1 if missing else 0
    def cp(it):
        b, k, d = it
        for _ in range(3):
            r = subprocess.run(["aws", "s3", "cp", f"s3://{b}/{k}", f"s3://{OURS}/cases/{c}/{d}", "--source-region", "us-east-1",
                                "--region", "us-west-2", "--only-show-errors"], capture_output=True, text=True)
            if r.returncode == 0: return None
        return (it, r.stderr)
    with ThreadPoolExecutor(8) as ex: errs = [e for e in ex.map(cp, items) if e]
    for e in errs: print("FAILED", e)
    if errs: return 2
    man = "".join(f"{d}\t{have[(b,k)]}\n" for b, k, d in items)
    subprocess.run(["aws", "s3", "cp", "-", f"s3://{OURS}/cases/{c}/MANIFEST.txt", "--region", "us-west-2"], input=man, text=True, check=True)
    print("staged", c); return 0
sys.exit(main())

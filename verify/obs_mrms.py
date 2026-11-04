"""MRMS 24 h QPE from the public noaa-mrms-pds bucket, aggregated to 0.25 degree boxes.

Product: MultiSensor_QPE_24H_Pass2 (gauge-corrected, radar + gauges; ~1 h latency, hourly files); fallback in this
order: MultiSensor_QPE_24H_Pass1, RadarOnly_QPE_24H (name recorded in the output). One file per 24 h window end.
Boxes: edges on multiples of 0.25 deg, lat 20..55 N, lon 230..300 E (140 x 280, south to north, west to east);
a box is valid when >= 80 % of its 25 x 25 MRMS pixels (0.01 deg) have data. Values in mm, missing = NaN.
usage: python -m verify.obs_mrms CASE [CASE ...]
"""
import sys, gzip, io, tempfile, os
import numpy as np
import datetime as dt
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import eccodes as ec
from .common import OBS, cycle

PRODUCTS = ["MultiSensor_QPE_24H_Pass2_00.00", "MultiSensor_QPE_24H_Pass1_00.00", "RadarOnly_QPE_24H_00.00"]
ENDS = (24, 48, 72, 84)
_s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))

def _get(end):
    """Return (product, array 140x280 mm) for the 24 h window ending at `end` (UTC datetime)."""
    for prod in PRODUCTS:
        key = f"CONUS/{prod}/{end:%Y%m%d}/MRMS_{prod.rsplit('_', 1)[0]}_00.00_{end:%Y%m%d-%H%M%S}.grib2.gz"
        try:
            blob = _s3.get_object(Bucket="noaa-mrms-pds", Key=key)["Body"].read()
        except _s3.exceptions.NoSuchKey:
            continue
        raw = gzip.decompress(blob)
        with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as t: t.write(raw)
        try:
            with open(t.name, "rb") as f:
                g = ec.codes_grib_new_from_file(f)
                v = ec.codes_get_values(g).astype(np.float32)
                ni, nj = ec.codes_get(g, "Ni"), ec.codes_get(g, "Nj")
                la1, lo1 = ec.codes_get(g, "latitudeOfFirstGridPointInDegrees"), ec.codes_get(g, "longitudeOfFirstGridPointInDegrees")
                ec.codes_release(g)
        finally:
            os.unlink(t.name)
        assert (ni, nj) == (7000, 3500) and abs(la1 - 54.995) < 1e-3 and abs(lo1 - 230.005) < 1e-3, (ni, nj, la1, lo1)
        a = v.reshape(nj, ni)[::-1]                    # south to north; lon 230.005 .. 299.995
        a = np.where(a < 0, np.nan, a)
        # pixel (0,0) centre = (20.005 N, 230.005 E) -> 25 x 25 blocks start exactly at 20.0 / 230.0
        b = a.reshape(140, 25, 280, 25)
        n = np.isfinite(b).sum(axis=(1, 3))
        with np.errstate(invalid="ignore"):
            import warnings; warnings.simplefilter("ignore"); m = np.nanmean(b, axis=(1, 3))
        return prod, np.where(n >= 0.8 * 625, m, np.nan)
    return None, None

def fetch(case, force=False):
    f = OBS / f"mrms_{case}.npz"
    if f.exists() and not force:
        z = np.load(f, allow_pickle=True); return {int(k[1:]): z[k] for k in z.files if k.startswith("L")}, str(z["product"])
    C = cycle(case); out, prods = {}, set()
    for L in ENDS:
        prod, a = _get(C + dt.timedelta(hours=L))
        if a is None: print(f"  MRMS {case} +{L}h: no file"); continue
        out[L] = a; prods.add(prod)
    np.savez_compressed(f, product=",".join(sorted(prods)), **{f"L{k}": v for k, v in out.items()})
    return out, ",".join(sorted(prods))

if __name__ == "__main__":
    for c in sys.argv[1:]:
        d, p = fetch(c)
        print(c, p, {k: (int(np.isfinite(v).sum()), round(float(np.nanmax(v)), 1)) for k, v in d.items()})

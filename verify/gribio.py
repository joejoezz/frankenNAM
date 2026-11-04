"""Byte-range access to GRIB2 files via their .idx, a small cache of the messages we score, and
interpolation from the model grid to stations / 0.25 deg boxes.

A *model* is a name plus a path template and an init offset (hours relative to the case cycle C):
    nam    archived NAM, init C            s3://noaa-nam-pds/nam.{ymd}/nam.t{hh}z.awphys{fh:02d}.tm00.grib2
    gfs    GFS of the same cycle C         s3://noaa-gfs-bdp-pds/gfs.{ymd}/{hh}/atmos/gfs.t{hh}z.pgrb2.0p25.f{fh:03d}
    gfs06  GFS of cycle C-6 (the information a tm06 FrankenNAM has), init C-6, fh = lead + 6
    fnam   FrankenNAM product (awphys names, produced later)   s3://nam-recast-.../cases/{case}/products/nam.{ymd}/...
A template may also be a local path. Placeholders: {ymd} {hh} (of the init time), {fh} (model forecast hour),
{case}. Custom models: --model name=TEMPLATE[@offset_hours].
"""
import re, os, math, hashlib
import numpy as np
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import eccodes as ec
from .common import CACHE, OURS, cycle
import datetime as dt

ec.codes_grib_multi_support_on()   # the archive packs U/V 10 m as sub-messages of one message

NAM_T = "s3://noaa-nam-pds/nam.{ymd}/nam.t{hh}z.awphys{fh:02d}.tm00.grib2"
GFS_T = "s3://noaa-gfs-bdp-pds/gfs.{ymd}/{hh}/atmos/gfs.t{hh}z.pgrb2.0p25.f{fh:03d}"
FNAM_T = f"s3://{OURS}/cases/{{case}}/products/nam.{{ymd}}/nam.t{{hh}}z.awphys{{fh:02d}}.tm00.grib2"
MODELS = {"nam": (NAM_T, 0), "gfs": (GFS_T, 0), "gfs06": (GFS_T, -6), "fnam": (FNAM_T, 0)}

# (variable, level text) as in the .idx; p-type flags only the instantaneous ones (not "ave")
WANT = [("TMP", "2 m above ground"), ("DPT", "2 m above ground"), ("UGRD", "10 m above ground"),
        ("VGRD", "10 m above ground"), ("APCP", "surface"), ("CSNOW", "surface"), ("CICEP", "surface"),
        ("CFRZR", "surface"), ("CRAIN", "surface"), ("HGT", "surface"), ("LAND", "surface")]
_S3 = {}
def s3(bucket):
    if bucket not in _S3:
        pub = bucket != OURS
        _S3[bucket] = boto3.client("s3", region_name="us-west-2" if not pub else "us-east-1",
                                   config=Config(signature_version=UNSIGNED, retries={"max_attempts": 5}) if pub
                                   else Config(retries={"max_attempts": 5}))
    return _S3[bucket]

def _read(url, rng=None):
    if url.startswith("s3://"):
        b, k = url[5:].split("/", 1)
        kw = {"Range": rng} if rng else {}
        return s3(b).get_object(Bucket=b, Key=k, **kw)["Body"].read()
    with open(url, "rb") as f:
        if rng:
            a, bnd = rng[6:].split("-"); f.seek(int(a))
            return f.read(int(bnd) - int(a) + 1 if bnd else -1)
        return f.read()

def select_ranges(idx_text):
    """Byte ranges (merged) of the wanted messages from an .idx; also returns the selected lines."""
    rows = []
    for ln in idx_text.strip().splitlines():
        p = ln.split(":")
        rows.append((int(p[1]), p[3], p[4], p[5] if len(p) > 5 else ""))
    offs = sorted({r[0] for r in rows})
    nxt = {o: (offs[i + 1] if i + 1 < len(offs) else None) for i, o in enumerate(offs)}
    sel = set()
    for off, var, lev, fc in rows:
        if (var, lev) in WANT and not (var.startswith("C") and "ave" in fc) and not (var == "APCP" and "acc" not in fc):
            sel.add(off)
    out = []
    for o in sorted(sel):
        e = nxt[o]
        if out and out[-1][1] == o: out[-1][1] = e
        else: out.append([o, e])
    return [(a, b) for a, b in out]

class Model:
    def __init__(self, name, template=None, offset=None):
        if template is None: template, offset = MODELS[name]
        self.name, self.template, self.off = name, template, offset or 0
        self.grid = None
    @classmethod
    def parse(cls, spec):
        if "=" not in spec:
            return cls(spec)
        n, t = spec.split("=", 1)
        off = 0
        m = re.search(r"@(-?\d+)$", t)
        if m: off, t = int(m.group(1)), t[:m.start()]
        return cls(n, t, off)
    def url(self, case, lead):
        init = cycle(case) + dt.timedelta(hours=self.off)
        return self.template.format(ymd=init.strftime("%Y%m%d"), hh=init.strftime("%H"), fh=lead - self.off, case=case)
    def path(self, case, lead):
        h = hashlib.md5(self.template.encode()).hexdigest()[:6]
        return CACHE / f"{self.name}-{h}" / case / f"L{lead:03d}.grib2"
    def ensure(self, case, lead, refresh=False):
        p = self.path(case, lead)
        if p.exists() and p.stat().st_size > 0 and not refresh: return p
        url = self.url(case, lead)
        rngs = select_ranges(_read(url + ".idx").decode())
        if not rngs: raise RuntimeError(f"no wanted messages in {url}.idx")
        blob = b"".join(_read(url, f"bytes={a}-{'' if b is None else b - 1}") for a, b in rngs)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp"); tmp.write_bytes(blob); tmp.rename(p)
        return p
    def read(self, case, lead):
        """dict: t2,d2,u10,v10 (K, K, m/s), csnow/cicep/cfrzr/crain, orog (m), land, tp [(start,end,vals)] ; grid in self.grid."""
        out = {"tp": []}
        with open(self.ensure(case, lead), "rb") as f:
            while True:
                g = ec.codes_grib_new_from_file(f)
                if g is None: break
                try:
                    sn, tl = ec.codes_get(g, "shortName"), ec.codes_get(g, "typeOfLevel")
                    if self.grid is None: self.grid = Grid(g)
                    v = ec.codes_get_values(g).astype(float)
                    v[v == ec.codes_get(g, "missingValue")] = np.nan
                    if sn == "tp": 
                        a, b = ec.codes_get(g, "stepRange").split("-") if "-" in ec.codes_get(g, "stepRange") else (None, None)
                        if a is not None: out["tp"].append((int(a), int(b), v))
                    elif sn in ("2t", "2d", "10u", "10v") and tl == "heightAboveGround":
                        out[{"2t": "t2", "2d": "d2", "10u": "u10", "10v": "v10"}[sn]] = v
                    elif sn in ("csnow", "cicep", "cfrzr", "crain"): out[sn] = v
                    elif sn == "lsm" or sn == "land": out["land"] = v
                    elif tl == "surface" and sn in ("orog", "gh", "z", "h"): out["orog"] = v
                finally:
                    ec.codes_release(g)
        return out
    def cum_precip(self, case, lead):
        """Total precipitation (mm) from the start of the forecast to product lead `lead`. Handles 0-t
        accumulations (GFS) and bucketed ones (NAM: 12 h buckets): the message ending at t with the earliest
        start a, plus the total to a."""
        return self._cum(case, lead - self.off)
    def _cum(self, case, fh):
        if fh <= 0: return 0.0
        d = self.read(case, fh + self.off)["tp"]
        cand = [x for x in d if x[1] == fh and x[0] < fh]
        if not cand: raise KeyError(f"{self.name} {case} fh{fh}: no APCP ending at this hour (have {[(a, b) for a, b, _ in d]})")
        a, _, v = min(cand, key=lambda x: x[0])
        return v if a == 0 else self._cum(case, a) + v
    def precip(self, case, l0, l1):
        """Precipitation (mm) over product leads l0 -> l1 (cumulative differences)."""
        return self.cum_precip(case, l1) - self.cum_precip(case, l0)

class Grid:
    """Bilinear / nearest sampling and 0.25-degree box means for a regular lat/lon or Lambert grid."""
    def __init__(self, g):
        self.type = ec.codes_get(g, "gridType")
        self.ni, self.nj = ec.codes_get(g, "Ni"), ec.codes_get(g, "Nj")
        lat = ec.codes_get_array(g, "latitudes").reshape(self.nj, self.ni)
        lon = ec.codes_get_array(g, "longitudes").reshape(self.nj, self.ni) % 360
        self.lat, self.lon = lat, lon
        if self.type == "regular_ll":
            self.y, self.x = lat[:, 0], lon[0, :]          # lat(deg), lon(0..360)
            self.proj = None
        elif self.type == "lambert":
            from pyproj import Proj
            la = ec.codes_get(g, "LaDInDegrees"); lov = ec.codes_get(g, "LoVInDegrees")
            l1, l2 = ec.codes_get(g, "Latin1InDegrees"), ec.codes_get(g, "Latin2InDegrees")
            self.proj = Proj(f"+proj=lcc +lat_1={l1} +lat_2={l2} +lat_0={la} +lon_0={lov} +a=6371229 +b=6371229")
            X, Y = self.proj(lon, lat)
            self.x, self.y = X[0, :], Y[:, 0]
            # check the grid really is axis-aligned and regular in projected space
            assert np.abs(X - X[0:1, :]).max() < 1, "Lambert grid not axis aligned"
            assert np.abs(Y - Y[:, 0:1]).max() < 1, "Lambert grid not axis aligned"
        else:
            raise NotImplementedError(self.type)
        self._box = None
    def _frac(self, lat, lon):
        lon = np.asarray(lon) % 360
        if self.proj is None: x, y = lon, np.asarray(lat)
        else: x, y = self.proj(lon, lat)
        fi = np.interp(x, self.x if self.x[1] > self.x[0] else self.x[::-1], np.arange(self.ni) if self.x[1] > self.x[0] else np.arange(self.ni)[::-1])
        fj = np.interp(y, self.y if self.y[1] > self.y[0] else self.y[::-1], np.arange(self.nj) if self.y[1] > self.y[0] else np.arange(self.nj)[::-1])
        # outside the grid -> NaN
        xs, ys = (self.x, self.y)
        out = (x < xs.min()) | (x > xs.max()) | (y < ys.min()) | (y > ys.max())
        return np.where(out, np.nan, fj), np.where(out, np.nan, fi)
    def station_index(self, lat, lon):
        return self._frac(lat, lon)
    def sample(self, v, fj, fi, kind="bilinear"):
        a = v.reshape(self.nj, self.ni)
        if kind == "nearest":
            j, i = np.rint(fj), np.rint(fi); ok = np.isfinite(j) & np.isfinite(i)
            r = np.full(fj.shape, np.nan); r[ok] = a[j[ok].astype(int), i[ok].astype(int)]; return r
        j0, i0 = np.floor(fj), np.floor(fi); ok = np.isfinite(j0) & np.isfinite(i0)
        r = np.full(fj.shape, np.nan)
        j0o, i0o = j0[ok].astype(int), i0[ok].astype(int)
        j1o, i1o = np.minimum(j0o + 1, self.nj - 1), np.minimum(i0o + 1, self.ni - 1)
        wj, wi = (fj[ok] - j0[ok]), (fi[ok] - i0[ok])
        r[ok] = (a[j0o, i0o] * (1 - wj) * (1 - wi) + a[j0o, i1o] * (1 - wj) * wi
                 + a[j1o, i0o] * wj * (1 - wi) + a[j1o, i1o] * wj * wi)
        return r
    # ---- 0.25 deg boxes: lat 20..55 (140), lon 230..300 (280), edges on multiples of 0.25 ----
    def box_mean(self, v, lat0=20.0, lon0=230.0, n=(140, 280)):
        if self._box is None:
            if self.type == "regular_ll":      # bilinear at the box centres = mean of the 4 surrounding points
                cl = lat0 + 0.25 * (np.arange(n[0]) + 0.5); co = lon0 + 0.25 * (np.arange(n[1]) + 0.5)
                CO, CL = np.meshgrid(co, cl); self._box = ("interp", self._frac(CL.ravel(), CO.ravel()))
            else:                              # mean of the native points inside each box
                bi = np.floor((self.lat - lat0) / 0.25).astype(int) * n[1] + np.floor((self.lon - lon0) / 0.25).astype(int)
                ok = (self.lat >= lat0) & (self.lat < lat0 + 0.25 * n[0]) & (self.lon >= lon0) & (self.lon < lon0 + 0.25 * n[1])
                self._box = ("bin", bi[ok], ok.ravel(), np.bincount(bi[ok], minlength=n[0] * n[1]))
        if self._box[0] == "interp":
            fj, fi = self._box[1]
            return self.sample(v, fj, fi).reshape(n)
        _, bi, ok, cnt = self._box
        s = np.bincount(bi, weights=v[ok], minlength=n[0] * n[1])
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(cnt > 0, s / cnt, np.nan).reshape(n)

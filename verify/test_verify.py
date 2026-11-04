"""Fast self-checks (no network): python -m verify.test_verify"""
import numpy as np
from .obs_asos import ptype
from .score import ets
from .gribio import select_ranges, Model

def test_ptype():
    assert ptype("-RA BR") == {"RAIN"} and ptype("FZRA") == {"FZRA"} and ptype("-SN BLSN") == {"SNOW"}
    assert ptype("-RASN") == {"RAIN", "SNOW"} and ptype("+TSRA") == {"RAIN"} and ptype("-FZRAPL") == {"FZRA", "ICEP"}
    assert ptype("PL") == {"ICEP"} and ptype("VCSH BR") == set() and ptype("") == set()

def test_ets():
    assert abs(ets(10, 0, 0, 90) - 1.0) < 1e-9 and abs(ets(0, 10, 10, 80)) < 0.06

def test_idx():
    idx = "1:0:d=2025:TMP:2 m above ground:12 hour fcst:\n2:100:d=2025:RH:2 m above ground:12 hour fcst:\n3:250:d=2025:DPT:2 m above ground:12 hour fcst:\n"
    assert select_ranges(idx) == [(0, 100), (250, None)]

def test_model_spec():
    m = Model.parse("x=/data/nam.{ymd}/f{fh}@-6")
    assert m.off == -6 and m.url("2025010512", 3) == "/data/nam.20250105/f9" and Model("gfs06").url("2025010512", 0).endswith("gfs.t06z.pgrb2.0p25.f006")

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); print("ok", k)

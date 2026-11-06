"""Frozen share of soil water (1 - SOILL/SOILW) over cold land points (0-10 cm TSOIL < -2 C) in awphys files.

    python -m verify.frozen_soil CASE MODELS LEADS     e.g. python -m verify.frozen_soil 2025010512 nam,fnam,fnam-anl 0,24,48
Found in the Phase 1 hindcast: FrankenNAM (both arms) starts with almost no soil ice; see docs/phase1-scorecard.md.
"""
import sys, numpy as np, eccodes as ec
from .gribio import Model, _read
case=sys.argv[1]; models=sys.argv[2].split(","); leads=[int(x) for x in sys.argv[3].split(",")]
def grab(m, lead, pats):
    url=m.url(case,lead); idx=_read(url+".idx").decode().splitlines()
    offs=[int(l.split(":")[1]) for l in idx]; out={}
    for i,l in enumerate(idx):
        key=":".join(l.split(":")[3:5])
        if key in pats and key not in out:
            b=offs[i+1]-1 if i+1<len(offs) else ""
            g=ec.codes_new_from_message(_read(url,f"bytes={offs[i]}-{b}")); v=ec.codes_get_values(g); ec.codes_release(g)
            out[key]=np.where(v>9e20,np.nan,v)
    return out
pats=["SOILL:0-0.1 m below ground","SOILW:0-0.1 m below ground","SOILL:0.1-0.4 m below ground","SOILW:0.1-0.4 m below ground","TSOIL:0-0.1 m below ground","LAND:surface"]
for lead in leads:
  for n in models:
    o=grab(Model(n),lead,pats); land=o["LAND:surface"]>0.5; ts=o["TSOIL:0-0.1 m below ground"]; cold=land&(ts<271)
    fr=1-o["SOILL:0-0.1 m below ground"]/o["SOILW:0-0.1 m below ground"]; fr2=1-o["SOILL:0.1-0.4 m below ground"]/o["SOILW:0.1-0.4 m below ground"]
    print(f"{case} {n:9s} f{lead:02d} cold pts {cold.sum():6d} frozen frac 0-10 {np.nanmean(fr[cold]):.3f} 10-40 {np.nanmean(fr2[cold]):.3f} TSOIL(cold) {np.nanmean(ts[cold])-273.15:.2f} C", flush=True)

import sys, numpy as np, eccodes as ec
sys.path.insert(0, "/Users/josephboomgard-zagrodnik/projects/nam-recast")
from verify.gribio import Model, _read, OURS
case="2026012312"
T=f"s3://{OURS}/cases/{{case}}/check-ice/products/nam.{{ymd}}/nam.t{{hh}}z.awphys{{fh:02d}}.tm00.grib2"
models={"nam":Model("nam"),"new":Model("new",T,0),"old":Model("fnam")}
pats=["SOILL:0-0.1 m below ground","SOILW:0-0.1 m below ground","SOILL:0.1-0.4 m below ground","SOILW:0.1-0.4 m below ground","TSOIL:0-0.1 m below ground","LAND:surface","TMP:2 m above ground"]
def grab(m,lead):
    url=m.url(case,lead); idx=_read(url+".idx").decode().splitlines(); offs=[int(l.split(":")[1]) for l in idx]; out={}
    for i,l in enumerate(idx):
        key=":".join(l.split(":")[3:5])
        if key in pats and key not in out:
            b=offs[i+1]-1 if i+1<len(offs) else ""
            g=ec.codes_new_from_message(_read(url,f"bytes={offs[i]}-{b}")); v=ec.codes_get_values(g); ec.codes_release(g)
            out[key]=np.where(v>9e20,np.nan,v)
    return out
for lead in (0,3,6):
    d={}
    for n,m in models.items():
        try: d[n]=grab(m,lead)
        except Exception as e: print(n,lead,"missing",str(e)[:60]); 
    if "nam" not in d: continue
    land=d["nam"]["LAND:surface"]>0.5; cold=land&(d["nam"]["TSOIL:0-0.1 m below ground"]<271)
    for n,o in d.items():
        c=land&(o["TSOIL:0-0.1 m below ground"]<271) if n!="nam" else cold
        f1=1-o["SOILL:0-0.1 m below ground"]/o["SOILW:0-0.1 m below ground"]; f2=1-o["SOILL:0.1-0.4 m below ground"]/o["SOILW:0.1-0.4 m below ground"]
        s=f"f{lead:02d} {n:4s} cold(own) {c.sum():6d} frozen 0-10 {np.nanmean(f1[c]):.3f} 10-40 {np.nanmean(f2[c]):.3f}"
        if n!="nam":
            ts=o["TSOIL:0-0.1 m below ground"]-d["nam"]["TSOIL:0-0.1 m below ground"]; t2=o["TMP:2 m above ground"]-d["nam"]["TMP:2 m above ground"]
            s+=f" | vs NAM: TSOIL bias land {np.nanmean(ts[land]):+.2f} cold(NAM) {np.nanmean(ts[cold]):+.2f}; T2m bias land {np.nanmean(t2[land]):+.2f} cold {np.nanmean(t2[cold]):+.2f} (rmse land {np.sqrt(np.nanmean(t2[land]**2)):.2f})"
        print(s,flush=True)

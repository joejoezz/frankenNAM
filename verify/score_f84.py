import sys, numpy as np, pandas as pd, eccodes as ec
sys.path.insert(0, "/Users/josephboomgard-zagrodnik/projects/nam-recast")
from verify import fields as F, score
from verify.gribio import Model, _read, OURS
case="2026012312"
mk=lambda sub: f"s3://{OURS}/cases/{{case}}/{sub}/products/nam.{{ymd}}/nam.t{{hh}}z.awphys{{fh:02d}}.tm00.grib2"
M={"nam":Model("nam"),"new":Model("new",mk("check-ice-f84"),0),"old":Model("fnam")}
LEADS=[12,24,36,48,60,72,84]; ALL=list(range(12,85,3))
out=[]
def P(s=""): print(s,flush=True); out.append(s)
# A stations
S=pd.read_csv("/Users/josephboomgard-zagrodnik/projects/nam-recast/verify/results/check-ice-f84/station_sums.csv")
S=S[(S.interp=="bilinear")&(S.region=="CONUS")].replace({"fnam":"old","fnew":"new"})
P("## A. Stations (CONUS ASOS, bilinear): RMSE / bias, model-minus-obs. old | new | NAM")
def st(d): n=d.n.sum(); return f"{np.sqrt(d.ssq.sum()/n):.2f}/{d.sd.sum()/n:+.2f}"
for v in ("t2m","td2m","wspd"):
    P(f"\n{v}\n| lead | old | new | NAM |\n|---|---|---|---|")
    for L in LEADS: P(f"| f{L} | "+" | ".join(st(S[(S['var']==v)&(S.lead==L)&(S.model==m)]) for m in ("old","new","nam"))+" |")
    P("| pooled 12-84 | "+" | ".join(st(S[(S['var']==v)&(S.lead>=12)&(S.lead<=84)&(S.model==m)]) for m in ("old","new","nam"))+" |")
# B grid to grid
mask=score.conus_mask()
KEYS={"t2m":"t2m","td2m":"dpt2m","wspd":"wspd10"}
acc={v:{m:[0,0,0] for m in ("old","new")} for v in KEYS}; per={}
G={}
for L in ALL:
    G[L]={n:F.get(m,case,L) for n,m in M.items()}
    for v,k in KEYS.items():
        r=F.box(M["nam"],G[L]["nam"][k])
        for m in ("old","new"):
            x=F.box(M[m],G[L][m][k]); ok=mask&np.isfinite(x)&np.isfinite(r); d=(x-r)[ok]
            a=acc[v][m]; a[0]+=d.size; a[1]+=d.sum(); a[2]+=(d**2).sum()
            if L in LEADS: per[(v,L,m)]=(np.sqrt((d**2).mean()),d.mean())
P("\n## B. Grid-to-grid vs archived NAM (0.25 deg boxes, CONUS mask): RMSE / bias, old | new")
for v in KEYS:
    P(f"\n{v}\n| lead | old | new |\n|---|---|---|")
    for L in LEADS: P(f"| f{L} | "+" | ".join(f"{per[(v,L,m)][0]:.2f}/{per[(v,L,m)][1]:+.2f}" for m in ("old","new"))+" |")
    P("| pooled 12-84 (3-hourly) | "+" | ".join(f"{np.sqrt(acc[v][m][2]/acc[v][m][0]):.2f}/{acc[v][m][1]/acc[v][m][0]:+.2f}" for m in ("old","new"))+" |")
# C frozen + TSOIL
pats=["SOILL:0-0.1 m below ground","SOILW:0-0.1 m below ground","SOILL:0.1-0.4 m below ground","SOILW:0.1-0.4 m below ground","TSOIL:0-0.1 m below ground"]
def grab(m,lead):
    url=m.url(case,lead); idx=_read(url+".idx").decode().splitlines(); offs=[int(l.split(":")[1]) for l in idx]; o={}
    for i,l in enumerate(idx):
        key=":".join(l.split(":")[3:5])
        if key in pats and key not in o:
            b=offs[i+1]-1 if i+1<len(offs) else ""
            g=ec.codes_new_from_message(_read(url,f"bytes={offs[i]}-{b}")); v=ec.codes_get_values(g); ec.codes_release(g); o[key]=np.where(v>9e20,np.nan,v)
    return o
P("\n## C. Frozen share (cold land, own TSOIL<271K) and 0-10 cm TSOIL bias vs NAM; 2 m T bias vs NAM split by NAM-cold land / other land (native grid 218, CONUS box)\n| lead | model | frozen 0-10 | frozen 10-40 | TSOIL bias land | TSOIL bias NAM-cold | T2m bias cold | T2m bias other land | n cold / other |\n|---|---|---|---|---|---|---|---|---|")
for L in (0,12,24,48,72,84):
    g=G[L] if L in G else {n:F.get(m,case,L) for n,m in M.items()}
    S3={n:{k:v.reshape(g['nam']['land'].shape) for k,v in grab(m,L).items()} for n,m in M.items()}
    nm=g["nam"]; land=nm["land"]>0.5; lat,lon=nm["lat"],nm["lon"]
    us=land&(lat>24)&(lat<50)&(lon>-125)&(lon<-66)
    cold=us&(S3["nam"]["TSOIL:0-0.1 m below ground"]<271); oth=us&~cold
    for n in ("nam","old","new"):
        o=S3[n]; ts=o["TSOIL:0-0.1 m below ground"]; c=us&(ts<271)
        f1=1-o["SOILL:0-0.1 m below ground"]/o["SOILW:0-0.1 m below ground"]; f2=1-o["SOILL:0.1-0.4 m below ground"]/o["SOILW:0.1-0.4 m below ground"]
        s=f"| f{L:02d} | {n} | {np.nanmean(f1[c]):.3f} | {np.nanmean(f2[c]):.3f} |"
        if n!="nam":
            dt=ts-S3["nam"]["TSOIL:0-0.1 m below ground"]; d2=g[n]["t2m"]-nm["t2m"]
            s+=f" {np.nanmean(dt[us]):+.2f} | {np.nanmean(dt[cold]):+.2f} | {np.nanmean(d2[cold]):+.2f} | {np.nanmean(d2[oth]):+.2f} | {cold.sum()} / {oth.sum()} |"
        else: s+=" | | | | |"
        P(s)
# D spatial f00
P("\n## D. Where is the early warm 2 m T? (new minus NAM, old minus NAM, new minus old; K; US land, native grid)")
for L in (0,6,12):
    g=G[L] if L in G else {n:F.get(m,case,L) for n,m in M.items()}
    nm=g["nam"]; land=nm["land"]>0.5; lat,lon=nm["lat"],nm["lon"]; us=land&(lat>24)&(lat<50)&(lon>-125)&(lon<-66)
    dn=g["new"]["t2m"]-nm["t2m"]; do=g["old"]["t2m"]-nm["t2m"]; dd=g["new"]["t2m"]-g["old"]["t2m"]
    P(f"\nf{L:02d}: US land mean new-NAM {np.nanmean(dn[us]):+.2f}, old-NAM {np.nanmean(do[us]):+.2f}, new-old {np.nanmean(dd[us]):+.2f}; ocean/other new-NAM {np.nanmean(dn[~land]):+.2f}")
    P("| region (lon range, lat range) | new-NAM | old-NAM | new-old | n |\n|---|---|---|---|---|")
    for nme,(l0,l1,a0,a1) in {"West (-125,-105)":(-125,-105,24,50),"Plains (-105,-95)":(-105,-95,24,50),"Midwest/Lakes (-95,-80) N of 38":(-95,-80,38,50),"Mid-South (-95,-80) S of 38":(-95,-80,24,38),"Southeast (-85,-75) S of 36":(-85,-75,24,36),"Appalachians/Mid-Atl (-85,-66) N of 36":(-85,-66,36,50)}.items():
        r=us&(lon>=l0)&(lon<l1)&(lat>=a0)&(lat<a1)
        P(f"| {nme} | {np.nanmean(dn[r]):+.2f} | {np.nanmean(do[r]):+.2f} | {np.nanmean(dd[r]):+.2f} | {r.sum()} |")
    P("by NAM 2 m T tercile: "+", ".join(f"[{lo:.0f},{hi:.0f}) C new-NAM {np.nanmean(dn[us&(nm['t2m']>=lo)&(nm['t2m']<hi)]):+.2f}" for lo,hi in ((-40,-5),(-5,5),(5,40))))
    P("by NAM 2 m T tercile (old-NAM): "+", ".join(f"{np.nanmean(do[us&(nm['t2m']>=lo)&(nm['t2m']<hi)]):+.2f}" for lo,hi in ((-40,-5),(-5,5),(5,40))))
    P(f"std of new-NAM over US land {np.nanstd(dn[us]):.2f}; share of points with new-NAM>+1 K: {np.nanmean(dn[us]>1):.2f}; <-1 K: {np.nanmean(dn[us]<-1):.2f}")
open("/tmp/claude-501/scr/score_f84.md","w").write("\n".join(out))

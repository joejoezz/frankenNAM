"""Phase 1 hindcast: fidelity of FrankenNAM to the archived NAM (gate tables), grid-to-grid statistics and the
feature panels.

    python -m verify.hindcast gate  --obs-tag phase1-obs [--ref-tag phase1-ref]   # statistical fidelity tables
    python -m verify.hindcast g2g   --case 2026012312,... --models fnam,fnam-anl,gfs,gfs06   # grid-to-grid vs the NAM
    python -m verify.hindcast features --case 2026012312,...                    # 9-panels + MRMS reflectivity panels

Outputs go to verify/results/phase1/ (csv), docs/figs/hindcast/ (png) and stdout (markdown).

Grid-to-grid: every field as 0.25 degree box means (verify.fields.box: grid-218 points binned, GFS bilinear at the box
centre) over the CONUS mask of verify.score (US polygon, land >= 0.5), model minus archived NAM, RMSE and bias.

Features: per case the two valid times are chosen from the ARCHIVED NAM alone (the event's metric in the event box,
the peak and the best other time >= 12 h away), so the choice is not tuned to make FrankenNAM look good.
"""
import argparse, gzip, os, tempfile, datetime as dt
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs, cartopy.feature as cfeature
from . import fields as F, score
from .common import CASES, cycle, OBS
from .gribio import Model

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "verify" / "results" / "phase1"; RES.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "docs" / "figs" / "hindcast"; FIG.mkdir(parents=True, exist_ok=True)
LAB = {"fnam": "FrankenNAM (tm06)", "fnam-anl": "FrankenNAM anl start", "nam": "Archived NAM", "gfs": "GFS (same cycle)",
       "gfs06": "GFS (6 h older)"}

# ------------------------------------------------------------------------------------------------ gate
MARGIN = {"t2m": 0.1, "td2m": 0.1, "wspd": 0.1}     # pooled 12-84 h CONUS RMSE margins (K, K, m/s)
ETS_MARGIN = 0.03

def _stat(df):
    g = df.groupby("model")[["n", "sd", "ssq"]].sum()
    return pd.DataFrame({"rmse": np.sqrt(g.ssq / g.n), "bias": g.sd / g.n, "n": g.n})

def gate(obs_tag, ref_tag=None):
    out = []
    S = pd.read_csv(ROOT / "verify" / "results" / obs_tag / "station_sums.csv")
    P = pd.read_csv(ROOT / "verify" / "results" / obs_tag / "precip_sums.csv")
    B = S[(S.interp == "bilinear") & (S.region == "CONUS") & (S.lead >= 12) & (S.lead <= 84)]
    models = [m for m in ("fnam", "nam", "gfs06", "gfs") if m in set(S.model)]
    rows, verdict = [], {}
    for v, u in (("t2m", "K"), ("td2m", "K"), ("wspd", "m/s")):
        st = _stat(B[B["var"] == v])
        d = st.rmse["fnam"] - st.rmse["nam"]; d6 = st.rmse["fnam"] - st.rmse["gfs06"]
        same = np.sign(st.bias["fnam"]) == np.sign(st.bias["nam"])
        ok = (d <= MARGIN[v]) and same and (d6 <= MARGIN[v])
        verdict[v] = ok
        rows.append([f"{v} ({u})", int(st.n["nam"])] + [f"{st.rmse[m]:.3f} / {st.bias[m]:+.3f}" for m in models]
                    + [f"{d:+.3f}", "yes" if same else "NO", f"{d6:+.3f}", "PASS" if ok else "FAIL"])
    out.append("| variable | n | " + " | ".join(f"{LAB[m]} RMSE / bias" for m in models)
               + " | FrankenNAM - NAM RMSE | same-sign bias | FrankenNAM - GFS 6 h older | within 0.1 |")
    out.append("|" + "---|" * (len(models) + 6)); out += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    out.append("")
    sums = P.groupby(["model", "thresh"])[["a", "b", "c", "d"]].sum()
    rows = []
    for t in score.THRESH:
        e = {m: float(score.ets(*sums.loc[(m, t)].values)) for m in models}
        fbi = {m: float((sums.loc[(m, t)].a + sums.loc[(m, t)].b) / (sums.loc[(m, t)].a + sums.loc[(m, t)].c)) for m in models}
        d = e["fnam"] - e["nam"]; d6 = e["fnam"] - e["gfs06"]
        ok = d >= -ETS_MARGIN and d6 >= -ETS_MARGIN
        verdict[f"ets{t}"] = ok
        rows.append([f">= {t} mm"] + [f"{e[m]:.3f} ({fbi[m]:.2f})" for m in models] + [f"{d:+.3f}", f"{d6:+.3f}", "PASS" if ok else "FAIL"])
    out.append("| 24 h precip | " + " | ".join(f"{LAB[m]} ETS (FBI)" for m in models) + " | FrankenNAM - NAM | FrankenNAM - GFS 6 h older | within 0.03 |")
    out.append("|" + "---|" * (len(models) + 4)); out += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    out.append("")
    # per case, 12-84 h RMSE difference FrankenNAM - NAM
    rows = []
    for c in sorted(set(B.case), key=lambda c: list(CASES).index(str(c)) if str(c) in CASES else 99):
        r = [f"`{c}`"]
        for v in ("t2m", "td2m", "wspd"):
            st = _stat(B[(B["var"] == v) & (B.case == c)])
            r.append(f"{st.rmse['fnam'] - st.rmse['nam']:+.3f} ({st.bias['fnam']:+.2f} vs {st.bias['nam']:+.2f})")
        pc = P[P.case == c].groupby(["model", "thresh"])[["a", "b", "c", "d"]].sum()
        r.append(" / ".join(f"{float(score.ets(*pc.loc[('fnam', t)].values) - score.ets(*pc.loc[('nam', t)].values)):+.2f}" for t in score.THRESH))
        rows.append(r)
    out.append("| case | T2m RMSE diff (bias F vs N) | Td2m | wind | ETS diff 2.5 / 10 / 25 mm |")
    out.append("|---|---|---|---|---|"); out += ["| " + " | ".join(r) + " |" for r in rows]
    out.append("")
    # by lead band (to see where any difference comes from)
    rows = []
    for lo, hi in ((3, 24), (27, 48), (51, 84)):
        r = [f"{lo}-{hi} h"]
        for v in ("t2m", "td2m", "wspd"):
            st = _stat(S[(S.interp == "bilinear") & (S.region == "CONUS") & (S.lead >= lo) & (S.lead <= hi) & (S["var"] == v)])
            r.append(f"{st.rmse['fnam']:.2f} / {st.rmse['nam']:.2f} ({st.rmse['fnam'] - st.rmse['nam']:+.2f})")
        rows.append(r)
    out.append("| lead band | T2m RMSE F / N (diff) | Td2m | wind |"); out.append("|---|---|---|---|")
    out += ["| " + " | ".join(r) + " |" for r in rows]; out.append("")
    if ref_tag:
        S2 = pd.read_csv(ROOT / "verify" / "results" / ref_tag / "station_sums.csv")
        P2 = pd.read_csv(ROOT / "verify" / "results" / ref_tag / "precip_sums.csv")
        ms = [m for m in ("fnam", "fnam-anl", "nam", "gfs", "gfs06") if m in set(S2.model)]
        rows = []
        for c in sorted(set(S2.case)):
            B2 = S2[(S2.interp == "bilinear") & (S2.region == "CONUS") & (S2.lead >= 12) & (S2.lead <= 84) & (S2.case == c)]
            for v in ("t2m", "td2m", "wspd"):
                st = _stat(B2[B2["var"] == v])
                rows.append([f"`{c}`", v] + [f"{st.rmse[m]:.3f} / {st.bias[m]:+.2f}" for m in ms])
            pc = P2[P2.case == c].groupby(["model", "thresh"])[["a", "b", "c", "d"]].sum()
            rows.append([f"`{c}`", "ETS 2.5/10/25"] + [" / ".join(f"{float(score.ets(*pc.loc[(m, t)].values)):.2f}" for t in score.THRESH) for m in ms])
        out.append("| case | variable | " + " | ".join(LAB[m] for m in ms) + " |"); out.append("|" + "---|" * (len(ms) + 2))
        out += ["| " + " | ".join(r) + " |" for r in rows]; out.append("")
    out.append("verdict: " + ", ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in verdict.items()))
    text = "\n".join(out); (RES / "gate.md").write_text(text); print(text)

# ------------------------------------------------------------------------------------------------ grid to grid
G2G_FIELDS = ("mslp", "z500", "t2m", "wspd10")
def g2g(cases, models):
    mask = score.conus_mask()
    nam = Model("nam"); rows = []
    for c in cases:
        ms = [Model.parse(m) for m in models]
        for L in (24, 48, 84):
            ref = F.get(nam, c, L)
            for k in G2G_FIELDS:
                r = F.box(nam, ref[k])
                for m in ms:
                    try: x = F.box(m, F.get(m, c, L)[k])
                    except Exception as e: print("skip", m.name, c, L, k, e); continue
                    d = (x - r)[mask & np.isfinite(x) & np.isfinite(r)]
                    rows.append(dict(case=c, model=m.name, field=k, lead=L, rmse=float(np.sqrt(np.mean(d ** 2))), bias=float(np.mean(d))))
        for a, b in ((0, 24), (24, 48), (60, 84)):
            r = F.box(nam, F.precip(nam, c, a, b))
            for m in ms:
                try: x = F.box(m, F.precip(m, c, a, b))
                except Exception as e: print("skip", m.name, c, a, b, e); continue
                d = (x - r)[mask & np.isfinite(x) & np.isfinite(r)]
                rows.append(dict(case=c, model=m.name, field="precip24", lead=b, rmse=float(np.sqrt(np.mean(d ** 2))), bias=float(np.mean(d))))
        print("g2g", c, flush=True)
    df = pd.DataFrame(rows)
    f = RES / "g2g.csv"
    if f.exists():
        old = pd.read_csv(f, dtype={"case": str}); old = old[~old.set_index(["case", "model"]).index.isin(df.set_index(["case", "model"]).index)]
        df = pd.concat([old, df])
    df.to_csv(f, index=False); print(df.to_string())

# ------------------------------------------------------------------------------------------------ reference arms
def ref(cases):
    """tm06 vs anl start against the archived NAM, by lead (grid to grid, CONUS land boxes), and a soil diagnostic:
    the 0-10 cm soil moisture difference to the NAM, and how much of each run's 2 m T / Td departure from the NAM
    lines up with its soil-moisture departure (spatial correlation over land boxes, by lead)."""
    mask = score.conus_mask(); nam = Model("nam"); rows = []
    for c in cases:
        ms = {k: Model(k) for k in ("fnam", "fnam-anl", "gfs")}
        sm_n0 = F.box(nam, F.get(nam, c, 0)["soilw0"])
        for L in range(0, 85, 6):
            dn = F.get(nam, c, L)
            for k, m in ms.items():
                d = F.get(m, c, L)
                r = dict(case=c, model=k, lead=L)
                for f in ("t2m", "dpt2m", "wspd10", "mslp", "soilw0"):
                    x, y = F.box(m, d[f]), F.box(nam, dn[f]); ok = mask & np.isfinite(x) & np.isfinite(y)
                    r[f + "_rmse"] = float(np.sqrt(np.mean((x - y)[ok] ** 2))); r[f + "_bias"] = float(np.mean((x - y)[ok]))
                    if f == "soilw0": dsm = np.where(ok, x - y, np.nan)
                    if f in ("t2m", "dpt2m"): r[f + "_d"] = np.where(ok, x - y, np.nan)
                for f in ("t2m", "dpt2m"):
                    ok = np.isfinite(r[f + "_d"]) & np.isfinite(dsm)
                    r[f + "_corr_sm"] = float(np.corrcoef(r[f + "_d"][ok], dsm[ok])[0, 1]) if ok.sum() > 50 and np.nanstd(dsm[ok]) > 0 else np.nan
                    del r[f + "_d"]
                rows.append(r)
        print("ref", c, flush=True)
    df = pd.DataFrame(rows); df.to_csv(RES / "ref.csv", index=False)
    pd.set_option("display.width", 250); print(df.round(3).to_string())
    fig, axs = plt.subplots(len(cases), 3, figsize=(15, 3.6 * len(cases)), squeeze=False)
    col = {"fnam": "#009E73", "fnam-anl": "#56B4E9", "gfs": "#D55E00"}
    for i, c in enumerate(cases):
        for j, (f, u) in enumerate((("t2m", "K"), ("dpt2m", "K"), ("soilw0", "m3/m3"))):
            ax = axs[i, j]
            for k in ("fnam", "fnam-anl", "gfs"):
                x = df[(df.case == c) & (df.model == k)]
                ax.plot(x.lead, x[f + "_rmse"], color=col[k], label=LAB[k], lw=1.8)
                ax.plot(x.lead, x[f + "_bias"], color=col[k], lw=1, ls="--")
            ax.axhline(0, color="k", lw=.5); ax.set_xticks(range(0, 85, 12)); ax.grid(alpha=.3)
            ax.set_title(f"{c}: {f} vs archived NAM ({u}); solid RMSE, dashed bias", fontsize=9)
        axs[i, 0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "ref_arms.png", dpi=90); plt.close(fig); print("wrote", FIG / "ref_arms.png")

# ------------------------------------------------------------------------------------------------ features
PT_CMAP = ListedColormap(["#ffffff", "#7fbf7b", "#4575b4", "#d73027", "#9e5fbf"])   # none, rain, snow, fzra, sleet
PT_NORM = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], 5)

def ptype(d):
    c = np.zeros_like(d["crain"])
    for code, k in ((1, "crain"), (2, "csnow"), (4, "cicep"), (3, "cfrzr")):   # FZRA > ICEP > SNOW > RAIN
        c = np.where(d[k] > 0.5, code, c)
    return c

def inbox(d, b):
    return (d["lat"] >= b[0]) & (d["lat"] <= b[1]) & (d["lon"] >= b[2]) & (d["lon"] <= b[3])

# each case: event box (lat0, lat1, lon0, lon1), plot extent (lon0, lon1, lat0, lat1), NAM metric for the valid times,
# panel rows, whether an MRMS reflectivity panel is drawn
def _m_ice(m, c, L): d = F.get(m, c, L); return float(((d["cfrzr"] > .5) | (d["cicep"] > .5))[inbox(d, CASE_CFG[c]["box"])].sum())
def _m_snow3(m, c, L):
    d = F.get(m, c, L); return float(F.snowfall(m, c, L - 3, L)[inbox(d, CASE_CFG[c]["box"])].sum()) if L >= 3 else 0.0
def _m_snow24(m, c, L):
    d = F.get(m, c, L); return float(F.snowfall(m, c, L - 24, L)[inbox(d, CASE_CFG[c]["box"])].sum()) if L >= 24 else -1.0
def _m_sleet_or_snow(m, c, L): d = F.get(m, c, L); return float(((d["cicep"] > .5) | (d["csnow"] > .5))[inbox(d, CASE_CFG[c]["box"])].sum())
def _m_lowp(m, c, L): d = F.get(m, c, L); return -float(np.nanmin(d["mslp"][inbox(d, CASE_CFG[c]["box"])]))
def _m_refl(m, c, L): d = F.get(m, c, L); return float((d["refc"] > 35)[inbox(d, CASE_CFG[c]["box"])].sum())

CASE_CFG = {
    "2026012312": dict(box=(31.0, 37.5, -87.0, -77.0), ext=(-91, -73, 28.5, 40.5), metric=_m_ice, rows=("t2m", "ptype", "mslp"), mrms=True, mslp=(1004, 1046, 2)),
    "2025010512": dict(box=(36.0, 41.0, -80.0, -74.0), ext=(-87, -70, 33.5, 43.5), metric=_m_sleet_or_snow, rows=("ptype", "t850", "mslp"), mrms=False, mslp=(996, 1046, 2)),
    "2025012100": dict(box=(27.0, 33.0, -98.0, -82.0), ext=(-100, -78, 25, 36.5), metric=_m_snow24, rows=("snow24", "ptype", "mslp"), mrms=False, mslp=(1000, 1046, 2)),
    "2024111912": dict(box=(38.0, 56.0, -140.0, -120.0), ext=(-142, -110, 35, 56), metric=_m_lowp, rows=("mslp", "precip24", "wspd10"), mrms=False, mslp=(940, 1032, 4)),
    "2025031412": dict(box=(30.0, 45.0, -100.0, -82.0), ext=(-106, -78, 27, 48), metric=_m_refl, rows=("cape", "mslp", "refc"), mrms=True, mslp=(970, 1036, 2)),
    "2025122912": dict(box=(41.0, 45.5, -82.0, -74.5), ext=(-90, -71, 38.5, 47.5), metric=_m_snow24, rows=("snow24", "t850", "mslp"), mrms=True, mslp=(984, 1046, 2)),
}

def pick_times(c):
    nam = Model("nam")
    cand = list(range(12, 85, 3))
    s = {L: CASE_CFG[c]["metric"](nam, c, L) for L in cand}
    a = max(s, key=s.get)
    b = max((L for L in cand if abs(L - a) >= 12), key=s.get)
    return sorted((a, b)), a, s

def _field(m, c, L, kind):
    d = F.get(m, c, L)
    if kind == "ptype": return ptype(d)
    if kind == "snow24": return F.snowfall(m, c, max(L - 24, 0), L) if L >= 3 else None
    if kind == "precip24": return F.precip(m, c, max(L - 24, 0), L)
    return d[kind]

STYLE = {
    "t2m": dict(cmap="RdYlBu_r", levels=np.arange(-12, 22, 2), units="2 m T (°C)", zero=True),
    "t850": dict(cmap="RdYlBu_r", levels=np.arange(-24, 16, 2), units="850 hPa T (°C)", zero=True),
    "mslp": dict(cmap="viridis", levels=np.arange(940, 1052, 4), units="MSLP (hPa)", contour=True),
    "cape": dict(cmap="magma_r", levels=[100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000], units="surface CAPE (J/kg)"),
    "refc": dict(cmap="turbo", levels=np.arange(5, 71, 5), units="composite reflectivity (dBZ)"),
    "precip24": dict(cmap="GnBu", levels=[1, 2.5, 5, 10, 15, 20, 30, 40, 60, 80, 100, 150], units="24 h precip (mm)"),
    "snow24": dict(cmap="cool", levels=[1, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 40, 50], units="24 h snowfall, 10:1 from 3 h precip x CSNOW (cm)"),
    "wspd10": dict(cmap="YlOrRd", levels=np.arange(4, 32, 2), units="10 m wind (m/s)"),
    "ptype": dict(units="p-type (rain / snow / freezing rain / sleet)"),
}

def _draw(ax, d, f, kind, ext, mslp=None, mlev=None):
    st = dict(STYLE[kind])
    if kind == "mslp" and mlev is not None: st["levels"] = np.arange(*mlev)
    ax.set_extent(ext, ccrs.PlateCarree())
    lon, lat = d["lon"], d["lat"]
    sel = (lat >= ext[2] - 3) & (lat <= ext[3] + 3) & (lon >= ext[0] - 3) & (lon <= ext[1] + 3)
    jj, ii = np.where(sel); j0, j1, i0, i1 = jj.min(), jj.max() + 1, ii.min(), ii.max() + 1
    X, Y, Z = lon[j0:j1, i0:i1], lat[j0:j1, i0:i1], f[j0:j1, i0:i1]
    tr = ccrs.PlateCarree()
    if kind == "ptype":
        cf = ax.pcolormesh(X, Y, np.where(Z > 0, Z, np.nan), cmap=PT_CMAP, norm=PT_NORM, transform=tr, shading="auto")
    else:
        cf = ax.contourf(X, Y, Z, levels=st["levels"], cmap="Spectral_r" if kind == "mslp" else st["cmap"], extend="both" if kind in ("t2m", "t850", "mslp") else "max", transform=tr)
        if st.get("zero"): ax.contour(X, Y, Z, levels=[0], colors="k", linewidths=1.4, transform=tr)
        if st.get("contour"): ax.contour(X, Y, Z, levels=st["levels"], colors="k", linewidths=0.4, transform=tr)
    if mslp is not None:
        M = mslp[j0:j1, i0:i1]
        cs = ax.contour(X, Y, M, levels=np.arange(*(mlev or (940, 1052, 4))), colors="k", linewidths=0.5, transform=tr)
    ax.coastlines("50m", lw=0.6); ax.add_feature(cfeature.STATES, lw=0.3); ax.add_feature(cfeature.BORDERS, lw=0.4)
    ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="none", edgecolor="k", lw=0.4)
    return cf

COLS = ("fnam", "nam", "gfs")
def features(cases):
    log = []
    for c in cases:
        cfg = CASE_CFG[c]; C = cycle(c)
        times, peak, s = pick_times(c)
        log.append(f"{c}: valid leads {times} (NAM metric peak f{peak:02d})")
        print(log[-1], flush=True)
        for L in times:
            ms = [Model(m) for m in COLS]
            nr = len(cfg["rows"])
            fig, axs = plt.subplots(nr, 3, figsize=(15, 3.9 * nr + 0.6), layout="constrained",
                                    subplot_kw=dict(projection=ccrs.LambertConformal((cfg["ext"][0] + cfg["ext"][1]) / 2, 40)))
            for r, kind in enumerate(cfg["rows"]):
                cf = None
                for j, m in enumerate(ms):
                    ax = axs[r, j]; d = F.get(m, c, L)
                    f = _field(m, c, L, kind)
                    if f is None: ax.set_visible(False); continue
                    over = d["mslp"] if kind in ("ptype", "t2m", "snow24") and "mslp" not in cfg["rows"] else None
                    cf = _draw(ax, d, f, kind, cfg["ext"], mslp=over, mlev=cfg.get("mslp"))
                    if r == 0: ax.set_title(LAB[m.name], fontsize=12)
                if cf is not None:
                    if kind == "ptype":
                        cb = fig.colorbar(cf, ax=axs[r, :], shrink=0.85, pad=0.01, ticks=[1, 2, 3, 4])
                        cb.ax.set_yticklabels(["rain", "snow", "fzra", "sleet"])
                    else: fig.colorbar(cf, ax=axs[r, :], shrink=0.85, pad=0.01, label=STYLE[kind]["units"])
            v = C + dt.timedelta(hours=L)
            fig.suptitle(f"{c} {CASES[c]}: init {C:%Y-%m-%d %HZ}, f{L:02d} valid {v:%Y-%m-%d %HZ}", fontsize=13)
            fn = FIG / f"features_{c}_f{L:02d}.png"; fig.savefig(fn, dpi=85); plt.close(fig); print("wrote", fn)
        if cfg["mrms"]:
            L = peak; v = C + dt.timedelta(hours=L)
            lat, lon, refl = mrms_refc(v)
            fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), layout="constrained",
                                    subplot_kw=dict(projection=ccrs.LambertConformal((cfg["ext"][0] + cfg["ext"][1]) / 2, 40)))
            st = STYLE["refc"]; tr = ccrs.PlateCarree()
            ax = axs[0]; ax.set_extent(cfg["ext"], tr)
            cf = ax.pcolormesh(lon, lat, np.where(refl >= 5, refl, np.nan), cmap=st["cmap"], vmin=5, vmax=70, transform=tr, shading="auto")
            ax.coastlines("50m", lw=0.6); ax.add_feature(cfeature.STATES, lw=0.3); ax.set_title(f"MRMS composite {v:%H%MZ}", fontsize=12)
            ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="none", edgecolor="k", lw=0.4)
            for ax, mn in zip(axs[1:], COLS[:2]):
                m = Model(mn); d = F.get(m, c, L)
                lo, la = d["lon"], d["lat"]
                ax.set_extent(cfg["ext"], tr)
                ax.pcolormesh(lo, la, np.where(d["refc"] >= 5, d["refc"], np.nan), cmap=st["cmap"], vmin=5, vmax=70, transform=tr, shading="auto")
                ax.coastlines("50m", lw=0.6); ax.add_feature(cfeature.STATES, lw=0.3); ax.set_title(f"{LAB[mn]} f{L:02d}", fontsize=12)
                ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="none", edgecolor="k", lw=0.4)
            fig.colorbar(cf, ax=axs, shrink=0.85, pad=0.01, label="composite reflectivity (dBZ)")
            fig.suptitle(f"{c} {CASES[c]}: reflectivity at the NAM's peak hour, valid {v:%Y-%m-%d %HZ}", fontsize=13)
            fn = FIG / f"mrms_{c}_f{L:02d}.png"; fig.savefig(fn, dpi=85); plt.close(fig); print("wrote", fn)
    (RES / "feature_times.txt").open("a").write("\n".join(log) + "\n")

def mrms_refc(v):
    """MRMS MergedReflectivityQCComposite nearest after the hour v (noaa-mrms-pds), subsampled to 0.03 deg."""
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    import eccodes as ec
    cache = OBS / f"mrms_refc_{v:%Y%m%d%H}.npz"
    if cache.exists():
        z = np.load(cache); return z["lat"], z["lon"], z["refl"]
    s3 = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    pre = f"CONUS/MergedReflectivityQCComposite_00.50/{v:%Y%m%d}/MRMS_MergedReflectivityQCComposite_00.50_{v:%Y%m%d-%H}"
    keys = sorted(o["Key"] for o in s3.list_objects_v2(Bucket="noaa-mrms-pds", Prefix=pre).get("Contents", []))
    if not keys: raise FileNotFoundError(pre)
    raw = gzip.decompress(s3.get_object(Bucket="noaa-mrms-pds", Key=keys[0])["Body"].read())
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as t: t.write(raw)
    try:
        with open(t.name, "rb") as f:
            g = ec.codes_grib_new_from_file(f)
            a = ec.codes_get_values(g).astype(np.float32).reshape(3500, 7000); ec.codes_release(g)
    finally: os.unlink(t.name)
    a = np.where(a < -50, np.nan, a)[::3, ::3]
    lat = 54.995 - 0.03 * np.arange(a.shape[0]); lon = -129.995 + 0.03 * np.arange(a.shape[1])
    np.savez_compressed(cache, lat=lat, lon=lon, refl=a, key=keys[0])
    return lat, lon, a

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["gate", "g2g", "features", "ref"])
    ap.add_argument("--case", default=",".join(c for c in CASES if c != "2026110100"))
    ap.add_argument("--models", default="fnam,fnam-anl,gfs,gfs06")
    ap.add_argument("--obs-tag", default="phase1-obs"); ap.add_argument("--ref-tag", default=None)
    a = ap.parse_args(argv)
    if a.what == "gate": gate(a.obs_tag, a.ref_tag)
    elif a.what == "g2g": g2g(a.case.split(","), a.models.split(","))
    elif a.what == "ref": ref(a.case.split(","))
    else: features(a.case.split(","))

if __name__ == "__main__":
    main()

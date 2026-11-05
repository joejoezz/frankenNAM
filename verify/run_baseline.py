"""Run the observation-based verification end to end and write the scorecard.

    python -m verify.run_baseline --case 2026110100 --models nam,gfs          # one case
    python -m verify.run_baseline --all --models nam,gfs,gfs06                # all seven cases -> docs/baseline-scorecard.md
    python -m verify.run_baseline --all --models nam,gfs,fnam                 # later: FrankenNAM products drop in as "fnam"
    python -m verify.run_baseline --case X --models "nam,fr=s3://bucket/path/nam.{ymd}/nam.t{hh}z.awphys{fh:02d}.tm00.grib2@0"

Models are names from verify.gribio.MODELS or name=TEMPLATE[@init_offset_hours]. Results (sums) go to
verify/results/<tag>/*.csv, figures to docs/figs/<tag>/, tables to docs/<tag>-scorecard.md (--tag, default baseline).
"""
import argparse, sys
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from . import score
from .common import CASES, PTYPE_CASES, PTYPE_BOX, SNOTEL_CASES, LEADS
from .gribio import Model

ROOT = Path(__file__).resolve().parents[1]
LABEL = {"nam": "NAM (archived)", "gfs": "GFS (same cycle)", "gfs06": "GFS (6 h older cycle)", "fnam": "FrankenNAM", "fnam-anl": "FrankenNAM anl start"}
COLOR = {"nam": "#0072B2", "gfs": "#D55E00", "gfs06": "#CC79A7", "fnam": "#009E73", "fnam-anl": "#56B4E9"}
UNIT = {"t2m": "K", "td2m": "K", "wspd": "m/s"}
NAME = {"t2m": "2 m temperature", "td2m": "2 m dew point", "wspd": "10 m wind speed"}
BANDS = {"3-24 h": (3, 24), "27-48 h": (27, 48), "51-84 h": (51, 84), "12-84 h": (12, 84)}
REGIONS = ["CONUS", "NE", "SE", "Midwest", "Plains", "West"]

def lab(m): return LABEL.get(m, m)
def col(m, i=0): return COLOR.get(m, ["#CC79A7", "#56B4E9", "#000000"][i % 3])

def stat(df, by):
    g = df.groupby(by, as_index=False)[["n", "sd", "sabs", "ssq"]].sum()
    g["bias"], g["mae"], g["rmse"] = g.sd / g.n, g.sabs / g.n, np.sqrt(g.ssq / g.n)
    return g

def band(df, lo, hi): return df[(df.lead >= lo) & (df.lead <= hi)]

def md_table(rows, head):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])

def best_mark(vals, fmt="{:.2f}", low=True):
    b = (min if low else max)(vals); return [("**" + fmt.format(v) + "**") if v == b else fmt.format(v) for v in vals]

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None, help="comma list of case ids")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--models", default="nam,gfs")
    ap.add_argument("--tag", default="baseline")
    ap.add_argument("--no-fig", action="store_true")
    a = ap.parse_args(argv)
    cases = list(CASES) if a.all else a.case.split(",")
    models = [Model.parse(s) for s in a.models.split(",") if s]
    names = [m.name for m in models]
    res = ROOT / "verify" / "results" / a.tag; res.mkdir(parents=True, exist_ok=True)
    figs = ROOT / "docs" / "figs" / a.tag; figs.mkdir(parents=True, exist_ok=True)

    S, P, T, N, prods = [], [], [], [], {}
    for c in cases:
        print("case", c, CASES.get(c, ""), flush=True)
        S.append(score.score_stations(c, models))
        p, prod = score.score_precip(c, models); P.append(p); prods[c] = prod
        if c in PTYPE_CASES: T.append(score.score_ptype(c, models))
        if c in SNOTEL_CASES: N.append(score.score_snotel(c, models))
    S, P = pd.concat(S), pd.concat(P)
    T = pd.concat(T) if T else pd.DataFrame(); N = pd.concat(N) if N else pd.DataFrame()
    S.to_csv(res / "station_sums.csv", index=False); P.to_csv(res / "precip_sums.csv", index=False)
    if len(T): T.to_csv(res / "ptype_counts.csv", index=False)
    if len(N): N.to_csv(res / "snotel_pairs.csv", index=False)
    stat(S[S.interp == "bilinear"], ["case", "model", "region", "var", "lead"]).to_csv(res / "station_stats_by_case.csv", index=False)

    out = [f"# Scorecard: {', '.join(lab(m) for m in names)} against observations\n",
           f"Cases ({len(cases)}): " + "; ".join(f"`{c}` {CASES.get(c, '')}" for c in cases) + ".\n"]
    B = S[S.interp == "bilinear"]
    # ---------- 1. station stats by lead band, CONUS, pooled over cases
    out.append("## 1. Surface stations, all cases pooled (CONUS ASOS/AWOS)\n")
    out.append("Model minus observation; bias, MAE, RMSE. Bold = lowest MAE or RMSE in the row. "
               "Bilinear interpolation; T and Td corrected to station elevation (6.5 and 2 K/km); common sample across models.\n")
    for v in score.VARS:
        rows = []
        for bn, (lo, hi) in BANDS.items():
            g = stat(band(B[(B.region == "CONUS") & (B["var"] == v)], lo, hi), ["model"]).set_index("model").loc[names]
            bi = g.bias.abs().values
            rows.append([bn, int(g.n.iloc[0])] + [f"{b:+.2f}" for b in g.bias] + best_mark(list(g.mae), low=True) + best_mark(list(g.rmse), low=True))
        out.append(f"**{NAME[v]} ({UNIT[v]})**\n")
        out.append(md_table(rows, ["lead", "n"] + [f"bias {lab(m)}" for m in names] + [f"MAE {lab(m)}" for m in names] + [f"RMSE {lab(m)}" for m in names]) + "\n")
    # ---------- 2. by region, 12-84 h
    out.append("## 2. By region, 12-84 h, all cases pooled (RMSE / bias)\n")
    for v in score.VARS:
        rows = []
        for r in REGIONS:
            g = stat(band(B[(B.region == r) & (B["var"] == v)], 12, 84), ["model"]).set_index("model").loc[names]
            rows.append([r, int(g.n.iloc[0])] + [f"{x:.2f} / {b:+.2f}" for x, b in zip(g.rmse, g.bias)])
        out.append(f"**{NAME[v]} ({UNIT[v]})**\n")
        out.append(md_table(rows, ["region", "n"] + [lab(m) for m in names]) + "\n")
    # ---------- 3. per case RMSE, 12-84
    out.append("## 3. By case, 12-84 h, CONUS RMSE (lowest in bold)\n")
    for v in score.VARS:
        rows = []
        for c in cases:
            g = stat(band(B[(B.region == "CONUS") & (B["var"] == v) & (B.case == c)], 12, 84), ["model"]).set_index("model").loc[names]
            rows.append([f"`{c}` {CASES[c]}"] + best_mark(list(g.rmse)))
        out.append(f"**{NAME[v]} ({UNIT[v]})**\n"); out.append(md_table(rows, ["case"] + [lab(m) for m in names]) + "\n")
    # ---------- 3b interpolation sensitivity
    rows = []
    for interp in ("bilinear", "nearest"):
        for v in score.VARS:
            g = stat(band(S[(S.interp == interp) & (S.region == "CONUS") & (S["var"] == v)], 12, 84), ["model"]).set_index("model").loc[names]
            rows.append([interp, NAME[v]] + [f"{x:.3f}" for x in g.rmse])
    out.append("**Interpolation sensitivity, RMSE 12-84 h, CONUS, all cases**\n"); out.append(md_table(rows, ["interp", "variable"] + [lab(m) for m in names]) + "\n")

    # ---------- 4. precipitation
    out.append("## 4. 24 h precipitation against MRMS (0.25 degree boxes over the lower 48)\n")
    out.append("MRMS product per case: " + "; ".join(f"`{c}` {p}" for c, p in prods.items()) + ". Windows ending C+24/48/72/84 h (the last is 60-84 h). "
               "ETS and frequency bias (FBI) from contingency counts summed over cases and windows; MAE in mm over all valid boxes.\n")
    sums = P.groupby(["model", "thresh"], as_index=False)[["a", "b", "c", "d", "n", "sabs", "sd", "sobs", "smod"]].sum()
    rows = []
    for t in score.THRESH:
        g = sums[sums.thresh == t].set_index("model").loc[names]
        e = score.ets(g.a, g.b, g.c, g.d).values; fbi = ((g.a + g.b) / (g.a + g.c)).values
        rows.append([f">= {t} mm"] + best_mark(list(e), "{:.3f}", low=False) + [f"{x:.2f}" for x in fbi])
    out.append(md_table(rows, ["threshold"] + [f"ETS {lab(m)}" for m in names] + [f"FBI {lab(m)}" for m in names]) + "\n")
    g = P[P.thresh == score.THRESH[0]].groupby("model", as_index=False)[["n", "sabs", "sd", "sobs", "smod"]].sum().set_index("model").loc[names]
    out.append(md_table([["MAE (mm / 24 h)"] + best_mark(list(g.sabs / g.n)), ["mean bias (mm / 24 h)"] + [f"{x:+.2f}" for x in g.sd / g.n],
                         ["mean observed (mm / 24 h)", f"{(g.sobs / g.n).iloc[0]:.2f}"] + [""] * (len(names) - 1)], ["", *[lab(m) for m in names]]) + "\n")
    rows = []
    for c in cases:
        r = [f"`{c}`"]
        for t in score.THRESH:
            g = P[(P.case == c) & (P.thresh == t)].groupby("model", as_index=False)[["a", "b", "c", "d"]].sum().set_index("model").loc[names]
            e = score.ets(g.a, g.b, g.c, g.d).values
            r += [" / ".join(f"{x:.2f}" for x in e)]
        rows.append(r)
    out.append("**ETS by case** (" + " / ".join(lab(m) for m in names) + ")\n")
    out.append(md_table(rows, ["case"] + [f">= {t} mm" for t in score.THRESH]) + "\n")
    rows = []
    for w in score.WINDOWS:
        r = [f"C+{w} h"]
        for t in (2.5, 10):
            g = P[(P.window == w) & (P.thresh == t)].groupby("model", as_index=False)[["a", "b", "c", "d"]].sum().set_index("model").loc[names]
            r.append(" / ".join(f"{x:.2f}" for x in score.ets(g.a, g.b, g.c, g.d).values))
        rows.append(r)
    out.append("**ETS by window** (" + " / ".join(lab(m) for m in names) + ")\n"); out.append(md_table(rows, ["window", ">= 2.5 mm", ">= 10 mm"]) + "\n")

    # ---------- 5. ptype
    if len(T):
        out.append("## 5. Precipitation type against ASOS present weather\n")
        out.append("Station-hours (3-hourly) where the station reports precipitation of a known type. The model type is the categorical flag "
                   "(CRAIN/CSNOW/CFRZR/CICEP) at the nearest grid point; priority FZRA > ICEP > SNOW > RAIN; NONE = no flag set. "
                   "Agreement = the model type is among the observed types (a mixed report such as RASN accepts either). "
                   "Recall by observed type is the share of those hours the model got right.\n")
        rows = []
        for c in PTYPE_CASES:
            if c not in set(T.case): continue
            for area in ("event region", "CONUS"):
                for bnd in ("3-36 h", "39-84 h"):
                    t = T[(T.case == c) & (T.area == area) & (T.band == bnd)].groupby("model")[["n", "agree"]].sum().reindex(names)
                    if not t.n.iloc[0]: continue
                    rows.append([f"`{c}`", area, bnd, int(t.n.iloc[0])] + best_mark(list(100 * t.agree / t.n), "{:.1f}%", low=False))
        out.append(md_table(rows, ["case", "area", "lead", "n obs-hours"] + [lab(m) for m in names]) + "\n")
        out.append("Event regions (lat, lon boxes): " + "; ".join(f"`{c}` {b[0]}-{b[1]} N, {-b[2]}-{-b[3]} W" for c, b in PTYPE_BOX.items()) + ".\n")
        for c in PTYPE_CASES:
            if c not in set(T.case): continue
            for m in names:
                t = T[(T.case == c) & (T.model == m) & (T.area == "event region")].groupby(["obs", "mod"], as_index=False)[["n", "agree"]].sum()
                cats = ["RAIN", "SNOW", "FZRA", "ICEP", "MIX"]; mc = ["RAIN", "SNOW", "FZRA", "ICEP", "NONE"]
                rows = []
                for o in cats:
                    x = t[t.obs == o]; tot = int(x.n.sum())
                    if not tot: continue
                    rows.append([o, tot] + [int(x[x["mod"] == k].n.sum()) for k in mc])
                out.append(f"`{c}` event region, {lab(m)}: rows = observed, columns = model\n"); out.append(md_table(rows, ["obs", "n"] + mc) + "\n")
    # ---------- 6. SNOTEL
    if len(N):
        out.append("## 6. SNOTEL 24 h precipitation (western mountain stations)\n")
        out.append("Gauge resolution 0.1 in; model sampled bilinearly at the station location without terrain adjustment, so ratios mix model "
                   "skill with the 12 km / 0.25 degree terrain smoothing. Ratio = sum(model)/sum(obs) over station-windows.\n")
        rows = []
        for c in SNOTEL_CASES:
            for m in names:
                x = N[(N.case == c) & (N.model == m)]
                if x.empty: continue
                r = np.corrcoef(x.obs, x["mod"])[0, 1]
                rows.append([f"`{c}`", lab(m), len(x), x.station.nunique(), f"{x.obs.mean():.1f}", f"{x['mod'].mean():.1f}",
                             f"{x['mod'].sum() / x.obs.sum():.2f}", f"{(x['mod'] - x.obs).abs().mean():.1f}", f"{r:.2f}"])
        out.append(md_table(rows, ["case", "model", "n", "stations", "obs mean mm", "model mean mm", "ratio", "MAE mm", "corr"]) + "\n")

    if not a.no_fig:
        out.append("## Figures\n")
        # bias and RMSE by lead
        for kind in ("bias", "rmse"):
            fig, axs = plt.subplots(1, 3, figsize=(14, 3.8))
            for ax, v in zip(axs, score.VARS):
                for i, m in enumerate(names):
                    g = stat(B[(B.region == "CONUS") & (B["var"] == v) & (B.model == m)], ["lead"])
                    ax.plot(g.lead, g[kind], color=col(m, i), label=lab(m), lw=1.8)
                ax.set_title(f"{NAME[v]} ({UNIT[v]})", fontsize=10); ax.set_xlabel("lead (h)"); ax.grid(alpha=.3)
                if kind == "bias": ax.axhline(0, color="k", lw=.6)
                ax.set_xticks(range(0, 85, 12))
            axs[0].set_ylabel(kind + " (model - obs)" if kind == "bias" else "RMSE"); axs[0].legend(fontsize=8)
            fig.suptitle(f"{kind.upper() if kind == 'rmse' else 'Bias'} by lead, CONUS stations, {len(cases)} case(s) pooled", fontsize=11)
            fig.tight_layout(); fig.savefig(figs / f"{kind}_by_lead.png", dpi=100); plt.close(fig)
            out.append(f"![{kind} by lead](figs/{a.tag}/{kind}_by_lead.png)\n")
        fig, ax = plt.subplots(figsize=(6.5, 3.8)); w = 0.8 / len(names)
        for i, m in enumerate(names):
            e = [score.ets(*sums[(sums.model == m) & (sums.thresh == t)][["a", "b", "c", "d"]].iloc[0].values) for t in score.THRESH]
            ax.bar(np.arange(3) + i * w, e, w, color=col(m, i), label=lab(m))
        ax.set_xticks(np.arange(3) + w * (len(names) - 1) / 2); ax.set_xticklabels([f">= {t} mm / 24 h" for t in score.THRESH])
        ax.set_ylabel("ETS"); ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3); ax.set_title("24 h precipitation ETS vs MRMS, pooled", fontsize=10)
        fig.tight_layout(); fig.savefig(figs / "ets_bars.png", dpi=100); plt.close(fig); out.append(f"![ETS](figs/{a.tag}/ets_bars.png)\n")
        fig, axs = plt.subplots(1, 3, figsize=(14, 3.6))
        for ax, v in zip(axs, score.VARS):
            for i, m in enumerate(names):
                vals = [stat(band(B[(B.region == r) & (B["var"] == v) & (B.model == m)], 12, 84), ["model"]).rmse.iloc[0] for r in REGIONS]
                ax.bar(np.arange(len(REGIONS)) + i * w, vals, w, color=col(m, i), label=lab(m))
            ax.set_xticks(np.arange(len(REGIONS)) + w * (len(names) - 1) / 2); ax.set_xticklabels(REGIONS, fontsize=8)
            ax.set_title(f"{NAME[v]} RMSE ({UNIT[v]}), 12-84 h", fontsize=10); ax.grid(axis="y", alpha=.3)
        axs[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(figs / "rmse_by_region.png", dpi=100); plt.close(fig)
        out.append(f"![RMSE by region](figs/{a.tag}/rmse_by_region.png)\n")
        for c in PTYPE_CASES:
            if not len(T) or c not in set(T.case): continue
            cats, mc = ["RAIN", "SNOW", "FZRA", "ICEP", "MIX"], ["RAIN", "SNOW", "FZRA", "ICEP", "NONE"]
            fig, axs = plt.subplots(1, len(names), figsize=(4.6 * len(names), 4))
            for ax, m in zip(np.atleast_1d(axs), names):
                t = T[(T.case == c) & (T.model == m) & (T.area == "event region")].groupby(["obs", "mod"], as_index=False).n.sum()
                M = np.array([[t[(t.obs == o) & (t["mod"] == k)].n.sum() for k in mc] for o in cats], float)
                R = M / np.maximum(M.sum(1, keepdims=True), 1)
                ax.imshow(R, vmin=0, vmax=1, cmap="Blues")
                for i in range(5):
                    for j in range(5):
                        if M[i, j]: ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=8, color="w" if R[i, j] > .5 else "k")
                ax.set_xticks(range(5)); ax.set_xticklabels(mc, fontsize=8); ax.set_yticks(range(5)); ax.set_yticklabels(cats, fontsize=8)
                ax.set_xlabel("model"); ax.set_ylabel("observed"); ax.set_title(lab(m), fontsize=10)
            fig.suptitle(f"P-type confusion, event region (counts; shading = row share), {c} {CASES[c]}", fontsize=10)
            fig.tight_layout(); fig.savefig(figs / f"ptype_{c}.png", dpi=100); plt.close(fig)
            out.append(f"![p-type {c}](figs/{a.tag}/ptype_{c}.png)\n")
    text = "\n".join(out)
    reading = ROOT / "verify" / f"reading_{a.tag}.md"
    if reading.exists(): text = text.replace("\n", "\n", 1) + "\n"; head, rest = text.split("\n", 1); text = head + "\n\n" + reading.read_text() + "\n" + rest
    md = ROOT / "docs" / (f"{a.tag}-scorecard.md" if len(cases) > 1 or a.all else f"{a.tag}-scorecard-{cases[0]}.md")
    md.write_text(text); print("wrote", md)

if __name__ == "__main__":
    main()

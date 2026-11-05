#!/usr/bin/env python3
"""Scorecard page from verify/results/<tag>/ (the sums the verification package writes).

    python site/gen/scorecard.py                                   # baseline results -> site/pages/scorecard.html
    python site/gen/scorecard.py --results verify/results/baseline verify/results/hindcast --out /tmp/scorecard.html

Reads station_sums.csv, precip_sums.csv, ptype_counts.csv, snotel_pairs.csv from every --results directory and
concatenates them, so a later `run_baseline --models fnam --tag hindcast` run adds the FrankenNAM column
without touching the baseline. Models: fnam (FrankenNAM), nam (archived NAM), gfs (same cycle), gfs06 (6 h older GFS).
A model column with no rows prints dashes. When fnam exists, every column is restricted to the cases fnam was run on,
so the columns always share one sample; the page says which cases. Pure standard library; numbers are computed from
the sums exactly as verify/run_baseline.py does (bias = sum(d)/n, RMSE = sqrt(sum(d^2)/n), ETS from pooled counts)."""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from common import esc, shell  # noqa: E402

ORDER = ["fnam", "nam", "gfs", "gfs06"]
LABEL = {"fnam": "FrankenNAM", "nam": "NAM (archived)", "gfs": "GFS (same cycle)", "gfs06": "GFS (6 h older cycle)"}
VARS = [("t2m", "2 m temperature", "K"), ("td2m", "2 m dew point", "K"), ("wspd", "10 m wind speed", "m/s")]
BANDS = [("3-24 h", 3, 24), ("27-48 h", 27, 48), ("51-84 h", 51, 84), ("12-84 h", 12, 84)]
REGIONS = ["CONUS", "NE", "SE", "Midwest", "Plains", "West"]
THRESH = [2.5, 10.0, 25.0]
# the Phase 1 gate (docs/phase1-plan.md, rewritten 4 Nov 2026): FrankenNAM within these of the archived NAM
GATE = {"t2m": 0.1, "td2m": 0.1, "wspd": 0.1, "ets": 0.03}
DASH = "&ndash;"


def read(dirs, name):
    rows = []
    for d in dirs:
        p = os.path.join(d, name)
        if os.path.exists(p):
            rows += list(csv.DictReader(open(p)))
    return rows


def case_names():
    """Case id -> description, read from verify/common.py (plain text, so no pandas import)."""
    names = {}
    try:
        src = open(os.path.join(ROOT, "verify", "common.py")).read()
        for m in re.finditer(r'"(\d{10})":\s*"([^"]*)"', src):
            names[m.group(1)] = m.group(2)
    except OSError:
        pass
    return names


class Sums:
    def __init__(self):
        self.n = 0
        self.sd = 0.0
        self.sabs = 0.0
        self.ssq = 0.0

    def add(self, r):
        self.n += int(float(r["n"]))
        self.sd += float(r["sd"])
        self.sabs += float(r["sabs"])
        self.ssq += float(r["ssq"])

    bias = property(lambda s: s.sd / s.n if s.n else None)
    mae = property(lambda s: s.sabs / s.n if s.n else None)
    rmse = property(lambda s: math.sqrt(s.ssq / s.n) if s.n else None)


def ets(a, b, c, d):
    n = a + b + c + d
    if not n:
        return None
    ar = (a + b) * (a + c) / n
    den = a + b + c - ar
    return (a - ar) / den if den else None


def f(x, fmt="{:.2f}"):
    return DASH if x is None else fmt.format(x)


class Data:
    def __init__(self, dirs):
        st = [r for r in read(dirs, "station_sums.csv") if r["interp"] == "bilinear"]
        self.pr = read(dirs, "precip_sums.csv")
        self.pt = read(dirs, "ptype_counts.csv")
        self.sn = read(dirs, "snotel_pairs.csv")
        self.models = [m for m in ORDER if any(r["model"] == m for r in st)]
        self.have_fnam = "fnam" in self.models
        cases_by_model = {m: {r["case"] for r in st if r["model"] == m} for m in self.models}
        # one shared sample: the cases every present model has (with fnam present, the cases fnam was run on)
        self.cases = sorted(set.intersection(*cases_by_model.values())) if self.models else []
        self.st = [r for r in st if r["case"] in self.cases]
        self.pr = [r for r in self.pr if r["case"] in self.cases]
        self.pt = [r for r in self.pt if r["case"] in self.cases]
        self.sn = [r for r in self.sn if r["case"] in self.cases]
        self.cols = ORDER[:]          # FrankenNAM column always shown; empty until fnam results exist

    def stat(self, model, var, lo, hi, region="CONUS", case=None):
        s = Sums()
        for r in self.st:
            if r["model"] == model and r["var"] == var and r["region"] == region and lo <= int(r["lead"]) <= hi \
                    and (case is None or r["case"] == case):
                s.add(r)
        return s if s.n else None

    def ets_mae(self, model, thr):
        a = b = c = d = 0
        sabs = n = 0
        for r in self.pr:
            if r["model"] == model and float(r["thresh"]) == thr:
                a += int(float(r["a"])); b += int(float(r["b"])); c += int(float(r["c"])); d += int(float(r["d"]))
                sabs += float(r["sabs"]); n += int(float(r["n"]))
        if not (a + b + c + d):
            return None
        return {"ets": ets(a, b, c, d), "fbi": (a + b) / (a + c) if a + c else None, "mae": sabs / n if n else None}


def th(label, cls=""):
    return f'<th class="n {cls}">{label}</th>' if cls != "x" else f"<th>{label}</th>"


def head(first, cols):
    return "<tr><th>" + first + "</th>" + "".join(f'<th class="n{" fn" if m == "fnam" else ""}">{esc(LABEL[m])}</th>' for m in cols) + "</tr>"


def cell(txt, m):
    return f'<td class="n{" fn" if m == "fnam" else ""}">{txt}</td>'


def q(text, label="?"):
    return f'<details class="q"><summary>{label}</summary><div>{text}</div></details>'


def station_tables(D):
    out = []
    for v, name, unit in VARS:
        out.append(f"<h3>{name} ({unit})</h3>")
        out.append("<table>" + head("Lead", D.cols).replace("<th>Lead</th>", "<th>Lead &middot; RMSE (bias)</th>"))
        for bn, lo, hi in BANDS:
            row = f"<tr><td>{bn}</td>"
            for m in D.cols:
                s = D.stat(m, v, lo, hi)
                row += cell(DASH if s is None else f"{s.rmse:.2f} ({s.bias:+.2f})", m)
            out.append(row + "</tr>")
        out.append("</table>")
    return "\n".join(out)


def region_table(D, v):
    out = ["<table>" + head("Region, 12-84 h", D.cols)]
    for r in REGIONS:
        row = f"<tr><td>{r}</td>"
        for m in D.cols:
            s = D.stat(m, v, 12, 84, region=r)
            row += cell(DASH if s is None else f"{s.rmse:.2f} ({s.bias:+.2f})", m)
        out.append(row + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def case_table(D, v, names):
    out = ["<table>" + head("Case, 12-84 h CONUS RMSE", D.cols)]
    for c in D.cases:
        row = f"<tr><td><code>{c}</code> {esc(names.get(c, ''))}</td>"
        for m in D.cols:
            s = D.stat(m, v, 12, 84, case=c)
            row += cell(f(s.rmse) if s else DASH, m)
        out.append(row + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def precip_tables(D):
    out = ["<table>" + head("24 h precipitation, equitable threat score", D.cols)]
    for t in THRESH:
        row = f"<tr><td>&ge; {t:g} mm</td>"
        for m in D.cols:
            e = D.ets_mae(m, t)
            row += cell(f(e["ets"], "{:.3f}") if e else DASH, m)
        out.append(row + "</tr>")
    out.append("</table>")
    out.append("<table>" + head("Frequency bias and error", D.cols))
    for t in THRESH:
        row = f"<tr><td>Frequency bias, &ge; {t:g} mm</td>"
        for m in D.cols:
            e = D.ets_mae(m, t)
            row += cell(f(e["fbi"]) if e else DASH, m)
        out.append(row + "</tr>")
    row = "<tr><td>Mean absolute error (mm per 24 h)</td>"
    for m in D.cols:
        e = D.ets_mae(m, 2.5)
        row += cell(f(e["mae"]) if e else DASH, m)
    out.append(row + "</tr></table>")
    return "\n".join(out)


def ptype_table(D):
    agg = defaultdict(lambda: [0, 0])
    for r in D.pt:
        k = (r["area"], r["band"], r["model"])
        agg[k][0] += int(float(r["n"])); agg[k][1] += int(float(r["agree"]))
    keys = sorted({(a, b) for a, b, _ in agg}, key=lambda k: (k[0] != "CONUS", k[0], k[1]))
    if not keys:
        return ""
    out = ["<table>" + head("Area, lead &middot; share of observed precipitation hours with the model's type among the observed", D.cols)]
    for a, b in keys:
        row = f"<tr><td>{a}, {b}</td>"
        for m in D.cols:
            n, ag = agg.get((a, b, m), (0, 0))
            row += cell(f"{100 * ag / n:.1f}%" if n else DASH, m)
        out.append(row + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def snotel_table(D):
    agg = defaultdict(lambda: defaultdict(list))
    for r in D.sn:
        agg[r["case"]][r["model"]].append((float(r["obs"]), float(r["mod"])))
    if not agg:
        return ""
    out = ["<table>" + head("SNOTEL 24 h precipitation, model / observed (correlation)", D.cols)]
    for c in sorted(agg):
        row = f"<tr><td><code>{c}</code></td>"
        for m in D.cols:
            p = agg[c].get(m)
            if not p:
                row += cell(DASH, m); continue
            so, sm = sum(o for o, _ in p), sum(x for _, x in p)
            n = len(p)
            mo, mm = so / n, sm / n
            cov = sum((o - mo) * (x - mm) for o, x in p)
            vo, vm = sum((o - mo) ** 2 for o, _ in p), sum((x - mm) ** 2 for _, x in p)
            corr = cov / math.sqrt(vo * vm) if vo and vm else None
            row += cell(f"{sm / so:.2f} ({f(corr)})" if so else DASH, m)
        out.append(row + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def fidelity(D):
    """FrankenNAM minus archived NAM against the gate margins. Empty-state text until fnam results exist."""
    if not D.have_fnam:
        return ('<p>No FrankenNAM hindcast has been scored against observations yet, so this table is empty. '
                "It fills from the same verification runs as every other table here.</p>")
    rows = ["<table><tr><th>Measure (12-84 h, CONUS, pooled)</th><th class=\"n\">FrankenNAM</th><th class=\"n\">NAM (archived)</th>"
            "<th class=\"n\">Difference</th><th class=\"n\">Margin</th><th>Within margin</th></tr>"]
    for v, name, unit in VARS:
        a, b = D.stat("fnam", v, 12, 84), D.stat("nam", v, 12, 84)
        if a and b:
            d = a.rmse - b.rmse
            rows.append(f"<tr><td>{name} RMSE ({unit})</td>{cell(f'{a.rmse:.2f}', '')}{cell(f'{b.rmse:.2f}', '')}"
                        f"{cell(f'{d:+.2f}', '')}{cell(f'{GATE[v]:.2f}', '')}<td>{'yes' if abs(d) <= GATE[v] else 'no'}</td></tr>")
    for t in THRESH:
        a, b = D.ets_mae("fnam", t), D.ets_mae("nam", t)
        if a and b and a["ets"] is not None and b["ets"] is not None:
            d = a["ets"] - b["ets"]
            ea, eb, lim = a["ets"], b["ets"], GATE["ets"]
            rows.append(f"<tr><td>24 h precipitation ETS, &ge; {t:g} mm</td>{cell(format(ea, '.3f'), '')}{cell(format(eb, '.3f'), '')}"
                        f"{cell(format(d, '+.3f'), '')}{cell(format(lim, '.2f'), '')}<td>{'yes' if abs(d) <= lim else 'no'}</td></tr>")
    rows.append("</table>")
    return "\n".join(rows)


def build(D, names, tag_note=""):
    ncase = len(D.cases)
    cl = "; ".join(f"<code>{c}</code> {esc(names.get(c, ''))}" for c in D.cases)
    body = f"""<h1>Scorecard</h1>
<p class="lede">FrankenNAM is the NAM&rsquo;s physics started from a GFS analysis. It is scored for <em>fidelity</em> to the archived operational NAM and, for context, against observations next to the GFS. It is not offered as a GFS-beater.</p>
<p class="draft"><b>Draft.</b> Highlighted boxes like <span class="ph">[PLACEHOLDER: this]</span> mark items that need a number, a decision or a tested snippet before launch.</p>
<div class="honest"><p><b>{'No FrankenNAM scores yet.' if not D.have_fnam else 'Scores are from archived cases, not live cycles.'}</b> {'The FrankenNAM column is empty and fills from the hindcast verification runs. The other columns are the baseline the hindcast is judged against.' if not D.have_fnam else 'Cases were picked for weather and are not independent samples. Differences of a few hundredths are noise.'}</p>
<p>The archived NAM did not beat the same-cycle GFS against observations on these cases, so the bar for FrankenNAM is closeness to the NAM, not to the GFS. Read the tables with that in mind.</p></div>

<h2>The sample</h2>
<p>{ncase} case{'s' if ncase != 1 else ''}, 12-84 h, all against observations: ASOS/AWOS stations, MRMS 24 h precipitation (gauge-corrected) and SNOTEL. {cl}.</p>
{q("Cases were chosen for weather, not at random, and they overlap in time and space, so the pooled numbers are not independent samples of anything. No significance tests are applied. Temperatures use a lapse-rate correction to station height and a 400 m terrain filter, so mountain stations are only partly represented. MRMS under-catches snow in the mountain West. SNOTEL values are coarse (0.1 in per reading) and not terrain-adjusted. Precipitation boxes are 0.25 degrees; the GFS is sampled bilinearly and the NAM by box mean.", "? how to read")}

<h2>Fidelity to the archived NAM</h2>
<p>The Phase 1 measure: pooled 12-84 h CONUS RMSE of 2 m temperature, dew point and 10 m wind within 0.1 K, 0.1 K and 0.1 m/s of the archived NAM, and 24 h precipitation ETS within 0.03 at 2.5, 10 and 25 mm.</p>
{fidelity(D)}

<h2>Surface stations, CONUS, pooled</h2>
<p class="small">RMSE (bias), model minus observation, units as shown. Same stations and times for every column.</p>
{station_tables(D)}

<h2>By region, 12-84 h</h2>
{''.join(f'<h3>{n} ({u})</h3>' + region_table(D, v) for v, n, u in VARS)}

<h2>By case, 12-84 h</h2>
{''.join(f'<h3>{n} ({u})</h3>' + case_table(D, v, names) for v, n, u in VARS)}

<h2>Precipitation against MRMS</h2>
<p class="small">24 h totals in 0.25 degree boxes over the lower 48, windows ending 24, 48, 72 and 84 h.</p>
{precip_tables(D)}

<h2>Precipitation type</h2>
<p class="small">Categorical flag at the nearest grid point against ASOS present weather, on the three cases with a type event.</p>
{ptype_table(D) or '<p>No type results in the data.</p>'}

<h2>SNOTEL</h2>
{snotel_table(D) or '<p>No SNOTEL results in the data.</p>'}

<h2>Live cycles</h2>
<p>Once cycles run daily, each is scored against observations and the GFS and added here as a running record. None has been scored yet. <span class="ph">[PLACEHOLDER: running record table (cycles scored, first scored cycle, cycles missed or late) from the live verification job]</span></p>
"""
    return shell("FrankenNAM scorecard", body, current="scorecard.html", desc="FrankenNAM verification against observations, next to the archived NAM and the GFS.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results", nargs="+", default=[os.path.join(ROOT, "verify", "results", "baseline")])
    ap.add_argument("--out", default=os.path.join(ROOT, "site", "pages", "scorecard.html"))
    a = ap.parse_args(argv)
    D = Data([os.path.expanduser(d) for d in a.results])
    open(a.out, "w").write(build(D, case_names()))
    print(f"models {D.models}, cases {len(D.cases)} -> {a.out}")


if __name__ == "__main__":
    main()

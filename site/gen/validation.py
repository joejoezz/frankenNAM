"""Validation page body (standard library only): fidelity table from docs/figs/tm06/stats.csv, the figures made by
figs.py, the baseline framing, the double-panel plots and the hindcast placeholders from hindcast.json."""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

FIELDS = [("mslp", "MSLP (hPa)"), ("z500", "Z500 (dam)"), ("t2m", "2 m temperature (K)"), ("wspd10", "10 m wind speed (m/s)")]
LEADS = [0, 24, 48, 84]
PRECIP = [("precip24h_0-24", "24 h precip, 0-24 h (mm)"), ("precip24h_24-48", "24 h precip, 24-48 h (mm)"), ("precip24h_60-84", "24 h precip, 60-84 h (mm)")]
PANELS = [
    ("panel-f48-mslp-precip.png", "f48: MSLP and 6 h precipitation", "Low-pressure centre, its track and the precipitation shield."),
    ("panel-f24-t2m.png", "f24: 2 m temperature", "Same scale; the cold pools and the warm sector."),
    ("panel-f36-ptype.png", "f36: precipitation type", "Rain, snow, sleet and freezing rain flags, as the NAM's own fields give them."),
    ("panel-f72-snow.png", "f72: snowfall, Kuchera ratio", "Snowfall computed from the model's liquid-equivalent snow and the Kuchera ratio."),
]


def q(label, text):
    return f'<details class="q"><summary>? {label}</summary><div>{text}</div></details>'


def fidelity_table() -> str:
    rows = {(r["field"], int(r["lead"])): r for r in csv.DictReader(open(os.path.join(REPO, "docs/figs/tm06/stats.csv")))}
    out = ['<div class="tblwrap"><table><tr><th>Field</th><th>Lead</th><th class="n">FrankenNAM tm06</th><th class="n">Analysis start</th><th class="n">GFS</th></tr>']
    def row(name, key, lead):
        r = rows[(key, lead)]
        v = [(float(r[f"rmse_{m}_vs_NAM"]), float(r[f"bias_{m}_vs_NAM"])) for m in ("tm06", "anl", "GFS")]
        best = min(x[0] for x in v)
        cells = "".join(f'<td class="n{" win" if x[0] == best else ""}">{x[0]:.2f} / {x[1]:+.2f}</td>' for x in v)
        out.append(f'<tr><td>{name}</td><td>f{lead:02d}</td>{cells}</tr>')
    for k, n in FIELDS:
        for ld in LEADS:
            row(n, k, ld)
    for k, n in PRECIP:
        row(n, k, int(k.split("-")[1]))
    out.append("</table></div>")
    return "\n".join(out)


def baseline_table() -> str:
    # pooled 12-84 h, CONUS, seven cases (docs/baseline-scorecard.md)
    r = [("2 m temperature RMSE (K)", "2.72", "2.72", "2.77"), ("2 m dew point RMSE (K)", "3.06", "3.07", "3.12"),
         ("10 m wind speed RMSE (m/s)", "2.13", "2.12", "2.13"), ("24 h precipitation ETS, 2.5 mm", "0.536", "0.567", "0.553"),
         ("24 h precipitation ETS, 10 mm", "0.496", "0.545", "0.525"), ("24 h precipitation ETS, 25 mm", "0.353", "0.391", "0.374")]
    t = ['<div class="tblwrap"><table><tr><th>Against observations, 12-84 h, CONUS</th><th class="n">NAM (archived)</th><th class="n">GFS (same cycle)</th><th class="n">GFS (6 h older)</th></tr>']
    for n, a, b, c in r:
        t.append(f'<tr><td>{n}</td><td class="n">{a}</td><td class="n">{b}</td><td class="n">{c}</td></tr>')
    t.append("</table></div>")
    return "\n".join(t)


def figure(src, cap, alt):
    return f'<figure class="full"><img src="{src}" alt="{alt}" loading="lazy"><figcaption>{cap}</figcaption></figure>'


def hindcast() -> str:
    d = json.load(open(os.path.join(HERE, "hindcast.json")))
    cards = []
    for c in d["cases"]:
        img = (f'<img src="{c["image"]}" alt="FrankenNAM beside the archived NAM, {c["title"]}">' if c["image"]
               else '<div class="slot">[PLACEHOLDER: double-panel image, FrankenNAM | archived NAM, same field, time and scale]</div>')
        lines = c["text"] or ["[PLACEHOLDER: what the case is, in one line]", "[PLACEHOLDER: what the NAM did that forecasters used it for, and what FrankenNAM did]"]
        li = "".join(f'<li>{"<span class=ph>" + x + "</span>" if x.startswith("[PLACEHOLDER") else x}</li>' for x in lines)
        cards.append(f'<div class="card"><h3>{c["title"]}</h3><p class="when">{c["when"]}</p>{img}<ul>{li}</ul></div>')
    res = d["results"]
    t = ['<div class="tblwrap"><table><tr>' + "".join(f"<th{' class=n' if i else ''}>{h}</th>" for i, h in enumerate(res["columns"])) + "</tr>"]
    for r in res["rows"]:
        t.append("<tr>" + f"<td>{r[0]}</td>" + "".join(f'<td class="n">{x if x is not None else "<span class=ph>pending</span>"}</td>' for x in r[1:]) + "</tr>")
    t.append("</table></div>")
    return (f'<div class="cards">{"".join(cards)}</div>\n<h3>Results across the six cases</h3>\n' + "\n".join(t))


def body() -> str:
    return f'''<h1>Validation</h1>
<p class="lede">How closely FrankenNAM follows the archived operational NAM, with the GFS alongside for context.</p>
<p>The question here is <b>fidelity to the NAM</b>: does FrankenNAM look and behave like the model forecasters relied on? It is not a claim that FrankenNAM beats any other model. Every number below says which case it comes from; one case is one case.</p>

<h2>Fidelity to the archived NAM</h2>
<p>RMSE / bias of each run against the archived NAM, over CONUS land on a 0.25&deg; grid, for the 2026-11-01 00Z cycle. &ldquo;FrankenNAM tm06&rdquo; is the product configuration (the GFS analysis 6&nbsp;h earlier, then 6&nbsp;h of NAM spin-up). &ldquo;Analysis start&rdquo; starts from the same-cycle GFS analysis. Lowest RMSE in each row is shaded.</p>
{fidelity_table()}
{q("how to read this", "Each row compares one run with the archived NAM at the same forecast hour; a smaller RMSE means closer to the NAM, and a bias near zero means no systematic offset. The GFS column is context: it is a different model and was never meant to match the NAM. f00 shows the cost of the 6&nbsp;h lag (a small warm bias in 2 m temperature that is gone by f24). Wind components and the full table are in the repository (<code>docs/figs/tm06/stats.md</code>). One case.")}

{figure("img/rmse-vs-lead.png", "RMSE against the archived NAM by lead. 2026-11-01 00Z.", "RMSE against the archived NAM by lead for FrankenNAM, the analysis start and the GFS")}
{q("what this shows", "Lower is closer to the archived NAM. From f24 on the tm06 line sits at or below the analysis start in most panels, and the GFS is furthest away at f24 and f48. By f84 all three have drifted apart, and for Z500 the GFS is closest. One case: the six hindcast cases below are the larger test.")}

<h2>Land state: the soil trace</h2>
{figure("img/soil-f00.png", "Soil at f00, RMSE over CONUS land. 2026-11-01 00Z.", "Soil moisture and temperature at f00: FrankenNAM is close to the NAM and far from the GFS")}
{q("what this shows", "The soil is seeded from the NAM's land state, so at f00 FrankenNAM's soil moisture is 0.012&nbsp;m<sup>3</sup>/m<sup>3</sup> from the archived NAM; the analysis start, which takes the GFS soil, is 0.072 away. The GFS is about 0.05&nbsp;m<sup>3</sup>/m<sup>3</sup> wetter than the NAM over CONUS. Soil temperature has moved 6&nbsp;h of diurnal cycle from the seed and sits 0.9&nbsp;K from the NAM.")}

<h2>What the NAM itself scored</h2>
<p>For scale: the operational NAM against observations (ASOS/AWOS stations, MRMS 24&nbsp;h precipitation), with the GFS beside it, over seven cases chosen for weather. The NAM and the same-cycle GFS are tied on temperature and wind, and the GFS has the higher precipitation score. The fidelity target for FrankenNAM is the NAM's column, not the GFS's.</p>
{baseline_table()}
{q("how this was made", "Seven cases, 12-84 h, about 390,000 station-hours per variable; model minus observation, bilinear interpolation, temperatures corrected to station elevation. Cases are picked for weather, not a random sample, and no significance tests are made. The 6&nbsp;h older GFS is the information a tm06 FrankenNAM starts from. Full tables: <a href='scorecard.html'>baseline scorecard</a>.")}
<p><a href="scorecard.html">Full baseline scorecard</a></p>

<h2>Side by side with the archived NAM</h2>
<p>FrankenNAM (left) and the archived NAM (right): same field, forecast hour and colour scale. Cycle 2026-11-01 00Z.</p>
{"".join(figure("img/" + f, c, t) + q("what this shows", e) for f, t, e in [(p[0], p[1], p[2]) for p in PANELS] for c in [t])}

<h2>Hindcast highlights</h2>
<p>Six cases forecasters know, run as hindcasts with FrankenNAM, the archived NAM and the GFS. Each card will carry a double-panel image and a few lines; the table below it pools the cases.</p>
{hindcast()}
'''

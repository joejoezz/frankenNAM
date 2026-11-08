"""Validation page body (standard library only): grid-to-grid distance from the archived NAM (verify/results/phase1b/g2g.csv, one
source for every number on the site), the chart made by figs.py, the dew-point note, the feature cards from hindcast.json and the
side-by-side loopers. No observations."""
from __future__ import annotations

import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
G2G = os.path.join(REPO, "verify/results/phase1b/g2g.csv")

MODELS = [("fnam", "FrankenNAM"), ("gfs", "GFS"), ("gfs06", "GFS from 6&nbsp;h earlier")]
FIELDS = [("mslp", "Sea-level pressure (hPa)"), ("z500", "500 hPa height (dam)"), ("t2m", "2 m temperature (K)"),
          ("td2m", "2 m dew point (K)"), ("wspd10", "10 m wind speed (m/s)"), ("precip24", "24 h precipitation (mm)")]
TABLE_LEADS = [24, 48, 84]
PRECIP_WINDOW = {24: "0&ndash;24 h", 48: "24&ndash;48 h", 84: "60&ndash;84 h"}
LOOP_CYCLE, LOOP_REGION = "2026110100", "conus"
LOOPS = [  # field key in the rendered frames, first hour shown, title
    ("mslp_precip6", 48, "MSLP and 6 h precipitation"),
    ("t2m", 24, "2 m temperature"),
    ("ptype", 36, "Precipitation type"),
    ("snowku", 72, "Snowfall, Kuchera ratio"),
]
NO_F00 = {"precip6", "precip_total", "snow10", "snowku"}  # accumulations start at f03


def q(label, text):
    return f'<details class="q"><summary>? {label}</summary><div>{text}</div></details>'


def pooled():
    """(field, model, lead) -> (RMSE, bias) pooled over the five cases: RMSE is the root of the mean squared RMSE (every case has the
    same number of grid boxes), bias the mean of the case biases."""
    acc = {}
    for r in csv.DictReader(open(G2G)):
        acc.setdefault((r["field"], r["model"], int(r["lead"])), []).append((float(r["rmse"]), float(r["bias"])))
    return {k: (math.sqrt(sum(a * a for a, _ in v) / len(v)), sum(b for _, b in v) / len(v)) for k, v in acc.items()}


def distance_table(P) -> str:
    out = ['<div class="tblwrap"><table class="narrow"><tr><th>Field</th><th>Lead</th>'
           + "".join(f'<th class="n">{n}</th>' for _, n in MODELS) + "</tr>"]
    for k, name in FIELDS:
        for ld in TABLE_LEADS:
            v = [P[(k, m, ld)][0] for m, _ in MODELS]
            best = min(v)
            lead = f"{PRECIP_WINDOW[ld]}" if k == "precip24" else f"f{ld:02d}"
            cells = "".join(f'<td class="n{" win" if x == best else ""}">{x:.2f}</td>' for x in v)
            out.append(f"<tr><td>{name}</td><td>{lead}</td>{cells}</tr>")
    out.append("</table></div>")
    return "\n".join(out)


def dewpoint_table(P) -> str:
    out = ['<div class="tblwrap"><table class="narrow"><tr><th>Lead</th>' + "".join(f'<th class="n">{n}</th>' for _, n in MODELS) + "</tr>"]
    for ld in (0, 12, 24, 48, 84):
        out.append(f"<tr><td>f{ld:02d}</td>" + "".join(f'<td class="n">{P[("td2m", m, ld)][1]:+.2f}</td>' for m, _ in MODELS) + "</tr>")
    out.append("</table></div>")
    return "\n".join(out)


def how_close(P) -> str:
    """The two or three lines on the home page, from the same numbers."""
    f = lambda k, m, ld: P[(k, m, ld)][0]
    day = sum(P[("td2m", "fnam", ld)][1] for ld in (0, 12, 24)) / 3
    return (f"Over five hindcast cases, at 24&nbsp;h FrankenNAM is about half as far from the archived NAM as the GFS is: "
            f"{f('t2m', 'fnam', 24):.1f}&nbsp;K against {f('t2m', 'gfs', 24):.1f}&nbsp;K in 2&nbsp;m temperature, "
            f"{f('mslp', 'fnam', 24):.1f} against {f('mslp', 'gfs', 24):.1f}&nbsp;hPa in sea-level pressure (RMS difference). "
            f"Near the surface it runs drier than the NAM, by about {abs(day):.1f}&nbsp;K in 2&nbsp;m dew point over the first day; "
            f"the cause is not yet found. Details on the <a href=\"validation.html\">Validation page</a>.")


def figure(src, cap, alt):
    return f'<figure class="full"><img src="{src}" alt="{alt}" loading="lazy"><figcaption>{cap}</figcaption></figure>'


def chart(cap, alt) -> str:
    return (f'<figure class="full"><picture><source media="(min-width: 760px)" srcset="img/g2g-lead-wide.png">'
            f'<img src="img/g2g-lead-narrow.png" alt="{alt}" loading="lazy"></picture><figcaption>{cap}</figcaption></figure>')


def looper(field, start, title) -> str:
    hours = [h for h in range(0, 85, 3) if not (h == 0 and field in NO_F00)]
    base = f"maps/frames/{{m}}/{LOOP_CYCLE}/{LOOP_REGION}/"
    img = lambda m, lab: (f'<div class="lp-pane"><div class="lp-lab">{lab}</div>'
                          f'<img data-m="{m}" src="{base.format(m=m)}{start:03d}-{field}.png" alt="{lab}, {title}, f{start:02d}" loading="lazy"></div>')
    return (f'<figure class="looper" data-base="{base}" data-field="{field}" data-hours="{",".join(map(str, hours))}" data-start="{start}">'
            f'<figcaption><b>{title}</b> <span class="lp-hr">f{start:02d}</span></figcaption>'
            f'<div class="lp-panes">{img("frankennam", "FrankenNAM")}{img("nam", "Archived NAM")}</div>'
            f'<div class="lp-ctl"><button type="button" class="lp-play" aria-label="Play">&#9654;</button>'
            f'<input type="range" class="lp-slider" min="0" max="{len(hours) - 1}" value="{hours.index(start)}" aria-label="Forecast hour"></div></figure>')


def hindcast() -> str:
    d = json.load(open(os.path.join(HERE, "hindcast.json")))
    cards = []
    for c in d["cases"]:
        img = f'<img src="{c["image"]}" alt="FrankenNAM beside the archived NAM and the GFS, {c["title"]}" loading="lazy">'
        li = "".join(f"<li>{x}</li>" for x in c["text"])
        cards.append(f'<div class="card"><h3>{c["title"]}</h3><p class="when">{c["when"]}</p>{img}<ul>{li}</ul></div>')
    return f'''<p>Four cases, each judged on the event forecasters used the NAM for. Each figure shows FrankenNAM, the archived NAM and the GFS at one hour, on the same colour scale; the scales differ from case to case. The cards say how FrankenNAM compares with the NAM.</p>
<div class="cards">{"".join(cards)}</div>'''


def body() -> str:
    P = pooled()
    return f'''<h1>Validation</h1>
<p class="lede">Is FrankenNAM consistent with the archived NAM, and distinct from the GFS?</p>
<p>Five cases chosen for their weather (an autumn case and four winter or storm cases forecasters know); no significance tests.</p>

<h2>Distance from the archived NAM</h2>
<p>Each run is compared with the archived NAM at the same forecast hour, grid to grid: 0.25&deg; boxes over land in the lower 48 states, model minus archived NAM, pooled over the five cases. <b>Lower means closer to the NAM.</b> The closest in each row is shaded.</p>
<p>FrankenNAM starts from the GFS analysis 6&nbsp;h before the cycle time, so we show the GFS from 6&nbsp;h earlier (FrankenNAM&rsquo;s start) as well: it holds the same information FrankenNAM starts with. The GFS column is the run for the cycle itself.</p>
{distance_table(P)}
{chart("RMS difference from the archived NAM by forecast hour, five cases pooled. Lower = closer to the NAM.", "Lines of RMS difference from the archived NAM against forecast hour for FrankenNAM and the GFS, one panel per field")}
{q("how this was scored", "Every field is averaged into 0.25&deg; boxes (the NAM&rsquo;s grid-218 points binned; the GFS interpolated to the box centres), over boxes whose centre is inside the lower 48 states and on land. RMS is the root of the mean squared difference. Pooled values combine the five cases with equal weight. The analysis (f00) is about 0.4&nbsp;K warm in 2&nbsp;m temperature against the NAM&rsquo;s, and that is gone by f12. Per-case numbers: <code>verify/results/phase1b/g2g.csv</code>.")}

<h3>2&nbsp;m dew point</h3>
<div class="honest"><p>FrankenNAM runs drier than the NAM near the surface: its 2&nbsp;m dew point is {abs(sum(P[("td2m", "fnam", l)][1] for l in (0, 12, 24)) / 3):.1f}&nbsp;K lower on average over the first day, and {abs(P[("td2m", "fnam", 84)][1]):.1f}&nbsp;K lower by f84. The cause is not yet known.</p></div>
<p class="small">Bias, model minus archived NAM, K, pooled over the five cases. Negative = drier than the NAM. The GFS is also drier than the NAM, and FrankenNAM starts from the GFS.</p>
{dewpoint_table(P)}

<p>The four feature cases (cold-air damming, Snowcrete, Gulf Coast snow, the PNW bomb cyclone) are on the <a href="index.html#features">home page</a>.</p>

<h2>Side by side with the archived NAM</h2>
<p>FrankenNAM (left) and the archived NAM (right): same field, forecast hour and colour scale, for the 2026-11-01 00Z cycle. Drag the slider or press play to step through f00 to f84. <a href="maps/index.html?single=1&amp;sample=1#frankennam/2026110100/conus/mslp_precip6/48">Open the full viewer</a>.</p>
{"".join(looper(*x) for x in LOOPS)}
'''

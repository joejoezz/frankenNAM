#!/usr/bin/env python3
"""Costs page from a small JSON.

    python site/gen/costs.py                                   # site/gen/costs.json -> site/pages/costs.html
    python site/gen/costs.py --data /path/costs.json --out /tmp/costs.html

The page is how the project ran the NAM on AWS, given away: what one run costs, the Spot and on-demand price table, the
GPU path, what a run-it-yourself setup costs a month, what it cost to get here, and a walkthrough. Per-run dollars are
computed here from the prices and seconds per forecast hour in costs.json (prices come from refresh_prices.py), never typed in."""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import esc, shell  # noqa: E402

DASH = "&ndash;"
KIND = {"measured": "measured", "estimate": "estimate", "target": "target"}


def usd(x, places=2):
    return DASH if x is None else f"${x:,.{places}f}"


def rng(a, b, places=2):
    return usd(a, places) if round(a, places) == round(b, places) else f"{usd(a, places)}{DASH}{usd(b, places)}"


def run_hours(r, p):
    return r["sfh"] * p["integ_h"] / 3600 + p["prep_h"]


def pricing_table(d):
    p = d["pricing"]
    rows = []
    for r in p["rows"]:
        h = run_hours(r, p)
        mid = (r["spot_min"] + r["spot_max"]) / 2
        r["_h"], r["_mid"] = h, mid
        basis = ("measured run" if r["basis"] == "measured" else "scaled from a measured s/fh")
        rows.append(f'<tr><td>{r["type"]}</td><td>{r["chip"]}</td><td class="n">{r["ram"]}</td>'
                    f'<td class="n">{r["sfh"]}</td><td>{basis}</td>'
                    f'<td class="n">{usd(r["od"])}</td><td class="n">{rng(r["spot_min"], r["spot_max"])}</td>'
                    f'<td class="n">{h:.2f}</td><td class="n">{usd(r["od"] * h)}</td>'
                    f'<td class="n">{rng(r["spot_min"] * h, r["spot_max"] * h)}</td></tr>')
    return rows


def build(d):
    p = d["pricing"]
    m = d["measured"]
    prow = pricing_table(d)
    by = {r["type"]: r for r in p["rows"]}
    c8g, r7a = by["c8g.8xlarge"], by["r7a.8xlarge"]
    cheaper = 100 * (1 - m[0]["price"] * m[0]["hours"] / (m[1]["price"] * m[1]["hours"]))
    meas = "".join(f'<tr><td>{esc(x["what"])}</td><td class="n">{usd(x["price"], 3)}</td><td class="n">{x["hours"]:.2f}</td>'
                   f'<td class="n"><b>{usd(x["price"] * x["hours"])}</b></td><td class="n">{x["sfh"]}</td><td>{esc(x["note"])}</td></tr>' for x in m)
    g = d["gpu"]
    o = d["ongoing"]
    gpu_lo, gpu_hi = g["min_per_run"]

    def month(runs, dl):
        h = c8g["_h"]
        compute = runs * (c8g["_mid"] + o["ebs_per_h"]) * h
        store = (o["bundle_gb"] + runs * o["products_gb_per_run"]) * o["s3_gb_month"]
        egress = dl * o["cloudfront_gb"]
        return compute, store, egress

    oc, dy = o["occasional"], o["daily"]
    mo, md = month(oc["runs"], oc["download_gb"]), month(dy["runs"], dy["download_gb"])
    month_rows = (
        f'<tr><td>Compute, one c8g.8xlarge Spot node per run, plus its disk</td><td class="n">{usd(mo[0], 0)}</td><td class="n">{usd(md[0], 0)}</td>'
        f'<td>Mid-point Spot price in the table above plus {usd(o["ebs_per_h"], 3)} an hour of EBS, {c8g["_h"]:.2f} h per run</td></tr>'
        f'<tr><td>Storage: runner bundle and products</td><td class="n">{usd(mo[1])}</td><td class="n">{usd(md[1])}</td>'
        f'<td>{o["bundle_gb"]} GB bundle plus {o["products_gb_per_run"]} GB of grids per run kept for the month, S3 Standard at {usd(o["s3_gb_month"], 3)} per GB-month</td></tr>'
        f'<tr><td>Downloads through CloudFront</td><td class="n">{usd(mo[2])}</td><td class="n">{usd(md[2], 0)}</td>'
        f'<td>{oc["download_gb"]} GB and {dy["download_gb"]} GB a month at {usd(o["cloudfront_gb"], 3)} per GB, the first 10 TB tier (the free allowance is not counted)</td></tr>'
        f'<tr><td><b>Total per month</b></td><td class="n"><b>{usd(sum(mo), 0)}</b></td><td class="n"><b>{usd(sum(md), 0)}</b></td><td>&nbsp;</td></tr>')
    st_rows, st_total = [], 0.0
    for r in d["startup"]:
        if r["usd"] is not None:
            st_total += r["usd"]
        note = esc(r.get("note", ""))
        st_rows.append(f"<tr><td>{esc(r['stage'])}</td><td class=\"n\">{usd(r['usd'])}</td><td>{KIND.get(r['kind'], esc(r['kind']))}"
                       f"{(' &middot; ' + note) if note else ''}</td></tr>")
    body = f"""<h1>Costs</h1>
<p class="lede">How we ran the NAM on AWS, given away: what a run costs, what it ran on, and how to build your own.</p>
<p class="draft"><b>Draft.</b> Highlighted boxes like <span class="ph">[PLACEHOLDER: this]</span> mark items that need a number, a decision or a link before launch.</p>

<h2>What one 84&nbsp;h run costs</h2>
<table>
<tr><th>Measured run</th><th class="n">Spot $/h</th><th class="n">Hours</th><th class="n">Compute</th><th class="n">s per forecast hour</th><th>Notes</th></tr>
{meas}
</table>
<p>The same model on Graviton costs about {cheaper:.0f}&nbsp;% less per run than on x86, on Spot. The patched f84 check run (the soil fix, below) took 5&nbsp;h 25&nbsp;min on a c8g Spot node. A run also pays for its disk: a 300&nbsp;GB gp3 volume is about {usd(o['ebs_per_h'], 3)} an hour, so about $0.40 more per run.</p>
<details class="q"><summary>? why 200 s per forecast hour</summary><div>Each figure is the forecast wall time divided by the 84 forecast hours (12,096 time steps of 25&nbsp;s), restarts, history output and the digital filter included. Both runs used 32 cores. Post-processing came after the forecast: 785&nbsp;s on Graviton, 634&nbsp;s on x86. Sources: <code>docs/graviton-port.md</code>, <code>docs/run-notes.md</code>. One measurement each, on different node classes.</div></details>

<h2>Pricing: x86 against Graviton, on-demand against Spot</h2>
<p>us-west-2, Linux, 32 vCPU nodes. On-demand from the AWS Pricing API; Spot is the minimum to maximum across the four zones over the last 24&nbsp;hours. Prices as of <b>{esc(p['as_of'])}</b>. Per run is computed: seconds per forecast hour &times; {p['integ_h']}&nbsp;h of integration (a product run starts 6&nbsp;h early), plus {p['prep_h'] * 60:.0f}&nbsp;min of prep and post-processing, times the price.</p>
<div class="tblwrap"><table>
<tr><th>Instance</th><th>Chip</th><th class="n">RAM (GB)</th><th class="n">s per fh</th><th>Basis</th><th class="n">On-demand $/h</th><th class="n">Spot $/h</th><th class="n">Hours per run</th><th class="n">On-demand per run</th><th class="n">Spot per run</th></tr>
{chr(10).join(prow)}
</table></div>
<ul class="small">
<li>Measured: c8g (200&nbsp;s) and r7a (189&nbsp;s). Scaled: m8g is the same Graviton4 chip as c8g, so it uses 200&nbsp;s. c7g is Graviton3, which ran 39&nbsp;% slower per forecast hour than Graviton4 in our test, so 278&nbsp;s. c7a is the same AMD chip as r7a, so 189&nbsp;s. A scaled row is arithmetic, not a run.</li>
<li>c7a.8xlarge (64&nbsp;GB) was killed by the out-of-memory killer at forecast hour 12 with restarts on, so the x86 run used r7a (256&nbsp;GB). Restarts are off by default in our runner. That is what lets a 64&nbsp;GB Graviton node do the job (43&nbsp;GB peak). A c7a row assumes restarts off and has not been run.</li>
<li>The measured runs above ran at slightly different Spot prices from today&rsquo;s. Spot prices move by the hour and by zone.</li>
</ul>

<h2>For context: the GPU path</h2>
<p>WOOF-NAM, the GPU rewrite of the NAM by Recast Systems, ran on a {g['type']} at {usd(g['od'], 2)} an hour on-demand. A run took {gpu_lo}{DASH}{gpu_hi}&nbsp;minutes, about {usd(g['trial_run_usd'])} for the run alone in our trial. The GPU Spot quota read zero, so there is no Spot figure. The GPU work is backlogged: WOOF-NAM&rsquo;s grids are currently free, and its output lacks the snowfall and precipitation-type records (see <a href="about.html#strategies">Strategies we tried</a>). Sources: <code>docs/gpu-path.md</code>, <code>docs/gpu-woof-trial.md</code>.</p>

<h2>What a run-it-yourself setup costs per month</h2>
<p>Two cases. <b>Occasional:</b> {oc['runs']} runs a month and {oc['download_gb']}&nbsp;GB of downloads. <b>If you ran it daily:</b> twice a day, about {dy['runs']} runs a month and {dy['download_gb']}&nbsp;GB of downloads. The second is arithmetic, not a promise: nothing here runs daily.</p>
<table>
<tr><th>Item</th><th class="n">Occasional</th><th class="n">If you ran it daily</th><th>Basis</th></tr>
{month_rows}
</table>
<p class="small">Inputs come from the AWS Open Data buckets in us-west-2 (<code>noaa-gfs-bdp-pds</code>, <code>noaa-nam-pds</code>) and cost nothing to read from a node in the same region. Spot capacity is a lottery: a reclaimed run is still billed and has to restart (see below).</p>

<h2>What it cost to get here</h2>
<table>
<tr><th>Stage</th><th class="n">AWS cost</th><th>Kind</th></tr>
{chr(10).join(st_rows)}
<tr><td><b>Spent so far (stages with a figure)</b></td><td class="n"><b>{usd(st_total)}</b></td><td>&nbsp;</td></tr>
</table>
<p class="small">{esc(d['startup_scope'])}</p>
<p>{esc(d['engineering_time'])} <span class="ph">[DECISION NEEDED: {esc(d['engineering_time_decision'])}]</span></p>

<h2 id="how">How we run it on AWS</h2>
<p>A short, reproducible walkthrough. Paths are in the repository; the repository link is on the footer once it is public. <span class="ph">[PLACEHOLDER: repository URL]</span></p>

<h3>1. Build the model</h3>
<p>The model is NMMB/NEMS, the preprocessor NPS and the post-processor UPP, from the NAM v4.2 source, with ESMF 7.1.0r underneath. The first build used Intel oneAPI on x86. The Graviton port uses gfortran and OpenMPI from apt on stock Ubuntu 24.04 arm64. The build scripts are in <code>build/</code> (<code>build_all.sh</code>, <code>libs.sh</code>, <code>build_nems.sh</code>, <code>build_nps.sh</code>, <code>build_upp.sh</code>), the source patches in <code>build/patches/</code>, and the story in <code>docs/build-notes.md</code> and <code>docs/graviton-port.md</code>. Thirteen patches; most are ESMF and compiler portability. Build on an EC2 node of the target architecture, not on a laptop.</p>

<h3>2. Bundle it into S3</h3>
<p><code>run/bundle.sh</code> packs the executables, libraries, static tables and run scripts into one tar (9.3&nbsp;GB for arm64) in the bucket. A runner is a stock Ubuntu AMI that downloads the bundle at boot, so there is no custom AMI to keep up to date.</p>

<h3>3. Inputs</h3>
<p>The GFS analysis and forecasts come from the AWS Open Data GFS bucket, and the NAM land state seed from the NAM archive bucket. <code>run/recast.sh</code> copies them server-side, runs ungrib, metgrid and nemsinterp, then the forecast and UPP, and <code>run/products.sh</code> writes the grid-218 <code>awphys</code> files and their <code>.idx</code> files.</p>

<h3>4. A self-chaining Spot runner</h3>
<p><code>run/launch.sh</code> starts one Spot instance with the bundle in its user data. <code>run/runner.sh</code> runs the case, uploads results and terminates the instance. When it finishes it calls <code>launch.sh --next</code> to start the next job. Jobs sit in a plain text queue in S3. A job is claimed by a conditional put (<code>If-None-Match: *</code>) of a claim object, so two runners cannot take the same line, and the queue file is never rewritten. For occasional runs you can skip the queue and call <code>deploy/04-run-case.sh</code>.</p>

<h3>5. Restarts off, and what a reclaim costs</h3>
<p>With restarts off, a Spot reclaim loses the run and you start over: about $2.50 on a c8g node. With restarts on, writing a restart needed up to 77&nbsp;GB of memory on x86, so you want a 128&nbsp;GB node (m8g) at about $0.30 more per run. In one 16-hour stretch we lost nine runners to reclaims; the scorecard counts about $7 spent on runs that never finished.</p>

<h3>6. Products and UPP</h3>
<p>UPP runs alongside the forecast on each history file, and <code>run/products.sh</code> turns each into one grid-218 file in NOAA&rsquo;s layout (454 records at f24). Post-processing needs about 21.6&nbsp;GB of memory on top of the forecast. The design is in <code>docs/tm06-design.md</code>.</p>

<h3>7. Permissions, and no alarms</h3>
<p>One instance role (<code>deploy/07-runner-policy.sh</code>) lets a runner read and write the run bucket, launch the next runner and terminate itself, all scoped to a project tag. The launcher sets terminate-on-shutdown. For occasional runs we run no alarms. If you chain runs unattended, add a billing alarm and a check that no runner has been up for more than about eight hours.</p>

<h3>Lessons that save money</h3>
<ul>
<li><b>Check Spot placement scores before you pick a node.</b> In us-west-2 the m8g score was 1 of 10 and c8g, c7g and m7g were 3, and we still lost m8g runners (four) and c8g runners (five) in 16 hours. Keep an ordered list of types and zones, fall through, and run the long job on demand if Spot keeps taking it.</li>
<li><b>Disk is not free.</b> A 300&nbsp;GB gp3 volume with extra IOPS cost about $0.40 per run, which the early per-run estimates left out. Size the volume to the run and delete the history files when you are done.</li>
<li><b>Frozen soil.</b> NOAA&rsquo;s own <code>nemsinterp</code> wrote total soil water into the initial condition&rsquo;s liquid-water records, so every cold start began with no ice in the soil. Over cold ground that showed up as a warm bias. Patch <code>nps-02-nemsinterp-write-sh2o.patch</code> fixes it. If you build the model, apply it.</li>
<li><b>Read the NAM file first.</b> The archived NAM packs the 10&nbsp;m wind components in one multi-field GRIB2 message. If you read it with ecCodes, a pending 10v message can be handed to your next read. Open the NAM file before the other model&rsquo;s (<code>run/score_woof.py</code> has the note).</li>
<li><b>Restart interval.</b> It must be a multiple of the 25&nbsp;s time step. 99999 minutes is not, and the model dies at start.</li>
<li><b>A terminated Spot request counts against your quota</b> for a minute or two, so a launch straight after a termination can be refused.</li>
</ul>
"""
    return shell("Costs", body, current="costs.html",
                 desc="What one NAM run costs on AWS, x86 and Graviton on-demand and Spot, and how to run it yourself.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=os.path.join(HERE, "costs.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "pages", "costs.html"))
    a = ap.parse_args(argv)
    d = json.load(open(a.data))
    open(a.out, "w").write(build(d))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()

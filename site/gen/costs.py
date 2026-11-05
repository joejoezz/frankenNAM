#!/usr/bin/env python3
"""Cost page from a small JSON.

    python site/gen/costs.py                                   # site/gen/costs.json -> site/pages/costs.html
    python site/gen/costs.py --data /path/costs.json --out /tmp/costs.html

The JSON schema is the file costs.json next to this script. Rows marked kind = "measured" come from the AWS cost
allocation tag project=nam-recast (see costs_from_aws.py); "estimate" and "target" rows are shown as such. Income and
Stripe fees are computed here from the subscriber counts and prices in the JSON, never typed in."""
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


def income(p, stripe):
    n, cap, price, fprice, target = p["paying"], p["founding_cap"], p["price"], p["founding_price"], p["target"]
    founders = min(p["founding"], cap)
    others = n - founders
    f_rate = fprice if n >= target else price            # founders drop only once the pledge is filled
    gross = founders * f_rate + others * price
    fees = gross * stripe["percent"] / 100 + stripe["fixed_usd"] * n
    return gross, fees


def at_pledge(p, stripe):
    q = dict(p, paying=p["target"], founding=p["founding_cap"])
    g, f = income(q, stripe)
    return g, f


def build(d):
    p, stripe = d["pledge"], d["stripe"]
    pct = 100 * min(p["paying"] / p["target"], 1)
    rows = []
    total = 0.0
    for r in d["monthly"]:
        total += r["per_month"]
        rows.append(f"<tr><td>{esc(r['item'])}</td><td class=\"n\">{usd(r.get('per_cycle'))}</td><td class=\"n\">{usd(r['per_month'], 0)}</td>"
                    f"<td>{KIND.get(r['kind'], esc(r['kind']))}</td><td>{esc(r['basis'])}</td></tr>")
    gross, fees = income(p, stripe)
    pg, pf = at_pledge(p, stripe)
    st_rows = []
    st_total = 0.0
    for r in d["startup"]:
        if r["usd"] is not None:
            st_total += r["usd"]
        note = esc(r.get("note", ""))
        st_rows.append(f"<tr><td>{esc(r['stage'])}</td><td class=\"n\">{usd(r['usd'])}</td><td>{esc(r['status'])}{(' &middot; ' + note) if note else ''}</td></tr>")
    body = f"""<h1>What it costs to run</h1>
<p class="lede">Prices are set to cover the computers and the time it takes to keep this running. The numbers are public, and each is marked as measured or as an estimate.</p>
<p class="draft"><b>Draft.</b> Highlighted boxes like <span class="ph">[PLACEHOLDER: this]</span> mark items that need a number, a decision or a tested snippet before launch.</p>

<h2>Subscribers against the pledge</h2>
<p>Once <b>{p['target']} paying subscribers</b> are reached, the founding members (the first {p['founding_cap']}) drop to {usd(p['founding_price'])} a month for as long as they stay subscribed.</p>
<div class="pledge" aria-label="subscribers toward the pledge"><i style="width:{pct:.0f}%"></i></div>
<p>Paying subscribers: <b>{p['paying']}</b> of {p['target']}. Founding members: <b>{p['founding']}</b> of {p['founding_cap']}. As of {esc(d['as_of'])}.</p>

<h2>Running costs per month</h2>
<table>
<tr><th>Item</th><th class="n">Per cycle</th><th class="n">Per month</th><th>Kind</th><th>Basis</th></tr>
{chr(10).join(rows)}
<tr><td><b>Total</b></td><td class="n">&nbsp;</td><td class="n"><b>{usd(total, 0)}</b></td><td colspan="2">Sum of the rows above, before payment fees</td></tr>
</table>
<details class="q"><summary>? where these come from</summary><div>Rows marked estimate come from design arithmetic and a few measurements, and are replaced by figures from the AWS cost-allocation tag <code>project=nam-recast</code> after a month of live cycles. The page is rebuilt from a data file, not edited by hand.</div></details>

<h2>Subscription income</h2>
<table>
<tr><th>Item</th><th class="n">Monthly</th></tr>
<tr><td>Subscriptions now ({p['paying']} paying)</td><td class="n">{usd(gross)}</td></tr>
<tr><td>Payment fees on those ({stripe['percent']}% + {usd(stripe['fixed_usd'])} each)</td><td class="n">{usd(fees)}</td></tr>
<tr><td>Net after payment fees</td><td class="n">{usd(gross - fees)}</td></tr>
<tr><td>At the pledge ({p['target']} paying, {p['founding_cap']} of them founding at {usd(p['founding_price'])})</td><td class="n">{usd(pg)} gross, {usd(pg - pf)} net</td></tr>
</table>
<p class="small">The payment-fee rate is an assumption: {esc(stripe['note'])}</p>

<h2>What it cost to get here</h2>
<table>
<tr><th>Stage</th><th class="n">AWS cost</th><th>Status</th></tr>
{chr(10).join(st_rows)}
<tr><td><b>Spent so far (stages with a figure)</b></td><td class="n"><b>{usd(st_total)}</b></td><td>&nbsp;</td></tr>
</table>
<p class="small">{esc(d['startup_scope'])}</p>
<p>{esc(d['engineering_time'])} <span class="ph">[DECISION NEEDED: {esc(d['engineering_time_decision'])}]</span></p>
"""
    return shell("What FrankenNAM costs to run", body, current="costs.html",
                 desc="Running costs, subscriber count and startup costs of FrankenNAM, published openly.")


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

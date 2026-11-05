#!/usr/bin/env python3
"""STUB: fill costs.json from AWS Cost Explorer by the cost allocation tag project=nam-recast. NOT RUN YET.

Written for the day cycles run daily; nothing here has been executed. Needs:
  * the tag `project` activated as a cost allocation tag in Billing (it takes up to 24 h to appear),
  * ce:GetCostAndUsage on the caller (each Cost Explorer API request is billed, about $0.01),
  * the cycle count for the month (from the grid index status.json), to turn totals into per-cycle figures,
  * the subscriber counts from Stripe (a separate step; pass them as --paying/--founding for now).

    python site/gen/costs_from_aws.py --month 2026-12 --cycles 62 --paying 0 --founding 0 [--dry-run]

It only touches the rows it can measure (compute, post-processing, transfer, storage) and the pledge counts; the
startup rows, the stripe assumptions and the engineering text stay as written."""
from __future__ import annotations

import argparse
import calendar
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# Cost Explorer SERVICE name -> costs.json row. Anything else lands in "Other" and is printed, never dropped.
SERVICE_ROW = {
    "Amazon Elastic Compute Cloud - Compute": "Compute: forecast",
    "EC2 - Other": "Compute: forecast",                 # EBS volumes and snapshots of the runner
    "AWS Lambda": "Compute: post-processing and maps",
    "Amazon Simple Storage Service": "Storage",
    "Amazon CloudFront": "Transfer",
}
# Data transfer out of AWS appears under the service that sent it (usage type contains DataTransfer-Out): group by
# USAGE_TYPE as well and route those to "Transfer". TODO: first real month will show which usage types occur.


def ce(month, group_by):
    y, m = map(int, month.split("-"))
    start, end = f"{y}-{m:02d}-01", f"{y + (m == 12)}-{(m % 12) + 1:02d}-01"
    cmd = ["aws", "ce", "get-cost-and-usage", "--region", "us-east-1",
           "--time-period", f"Start={start},End={end}", "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
           "--filter", json.dumps({"Tags": {"Key": "project", "Values": ["nam-recast"]}}),
           "--group-by", f"Type=DIMENSION,Key={group_by}", "--output", "json"]
    return cmd


def parse(out):
    rows = {}
    for period in json.loads(out)["ResultsByTime"]:
        for g in period["Groups"]:
            rows[g["Keys"][0]] = rows.get(g["Keys"][0], 0.0) + float(g["Metrics"]["UnblendedCost"]["Amount"])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--cycles", type=int, required=True, help="cycles run that month (status.json)")
    ap.add_argument("--paying", type=int, default=None)
    ap.add_argument("--founding", type=int, default=None)
    ap.add_argument("--data", default=os.path.join(HERE, "costs.json"))
    ap.add_argument("--dry-run", action="store_true", help="print the Cost Explorer commands and exit")
    a = ap.parse_args(argv)
    cmds = {"service": ce(a.month, "SERVICE"), "usage": ce(a.month, "USAGE_TYPE")}
    if a.dry_run:
        for k, c in cmds.items():
            print(" ".join(c))
        return
    by_service = parse(subprocess.run(cmds["service"], check=True, capture_output=True, text=True).stdout)
    by_usage = parse(subprocess.run(cmds["usage"], check=True, capture_output=True, text=True).stdout)
    transfer = sum(v for k, v in by_usage.items() if "DataTransfer-Out" in k)
    d = json.load(open(a.data))
    totals = {}
    for svc, v in by_service.items():
        row = SERVICE_ROW.get(svc, "Other")
        totals[row] = totals.get(row, 0.0) + v
    totals["Transfer"] = transfer                      # replaces whatever the service split put there
    other = totals.pop("Other", 0.0)
    for r in d["monthly"]:
        if r["item"] in totals:
            r["per_month"] = round(totals[r["item"]], 2)
            r["per_cycle"] = round(totals[r["item"]] / a.cycles, 2) if r["item"].startswith("Compute") else None
            r["kind"] = "measured"
            r["basis"] = f"AWS Cost Explorer, tag project=nam-recast, {a.month}, {a.cycles} cycles"
    if other:
        print(f"unmapped services total ${other:.2f}: add them to SERVICE_ROW", by_service)
    if a.paying is not None:
        d["pledge"]["paying"] = a.paying
    if a.founding is not None:
        d["pledge"]["founding"] = a.founding
    d["as_of"] = f"{a.month}-{calendar.monthrange(*map(int, a.month.split('-')))[1]:02d}"
    json.dump(d, open(a.data, "w"), indent=2)
    print("updated", a.data)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Refresh the pricing block of costs.json from AWS (on-demand: Pricing API; Spot: last 24 h of price history).

    python3 site/gen/refresh_prices.py          # needs the aws CLI and read access to pricing and ec2

Writes only pricing.as_of, pricing.rows[*].od / spot_min / spot_max. Everything else in the table (per-hour and per-run
dollars) is computed by costs.py. Spot min/max are across the four us-west-2 zones over the last 24 hours."""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "costs.json")
REGION = "us-west-2"


def aws(*a):
    return json.loads(subprocess.run(["aws", *a, "--output", "json"], check=True, capture_output=True, text=True).stdout)


def on_demand(t):
    f = [("instanceType", t), ("regionCode", REGION), ("operatingSystem", "Linux"), ("tenancy", "Shared"),
         ("preInstalledSw", "NA"), ("capacitystatus", "Used")]
    d = aws("pricing", "get-products", "--region", "us-east-1", "--service-code", "AmazonEC2",
            "--filters", *[f"Type=TERM_MATCH,Field={k},Value={v}" for k, v in f])
    p = json.loads(d["PriceList"][0])
    return float(next(iter(next(iter(p["terms"]["OnDemand"].values()))["priceDimensions"].values()))["pricePerUnit"]["USD"])


def main():
    d = json.load(open(PATH))
    rows = d["pricing"]["rows"]
    now = datetime.now(timezone.utc)
    h = aws("ec2", "describe-spot-price-history", "--region", REGION, "--instance-types", *[r["type"] for r in rows],
            "--product-descriptions", "Linux/UNIX", "--start-time", (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    for r in rows:
        p = [float(x["SpotPrice"]) for x in h["SpotPriceHistory"] if x["InstanceType"] == r["type"]]
        r["od"], r["spot_min"], r["spot_max"] = on_demand(r["type"]), min(p), max(p)
    d["pricing"]["as_of"] = now.strftime("%Y-%m-%d %H:%MZ")
    json.dump(d, open(PATH, "w"), indent=1)
    print("updated", PATH, d["pricing"]["as_of"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build every page of the mockup into site/pages/ (standard library only).

    python3 site/gen/build_pages.py            # home, about, validation, data, terms, then costs and scorecard

Bodies: gen/body/{index,about,data,terms}.html; validation.py (figures from figs.py, drop-ins from hindcast.json);
costs.py and scorecard.py as before. Edit those, not the generated HTML."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(os.path.dirname(HERE), "pages")
sys.path.insert(0, HERE)
from common import shell  # noqa: E402
import validation  # noqa: E402

BODY = lambda n: open(os.path.join(HERE, "body", n + ".html")).read()  # noqa: E731
SPEC = [
    ("index", "FrankenNAM: an open source project to keep the NAM model alive", "", BODY("index"),
     "Why FrankenNAM exists, and the latest maps."),
    ("about", "About FrankenNAM", "about.html", BODY("about"), "Design, the FrankenNAM analysis, delivery clock, cost and the comparison with the operational NAM."),
    ("validation", "Validation", "validation.html", validation.body(), "Fidelity to the archived NAM, the baseline scorecard, side-by-side plots and hindcast highlights."),
    ("data", "Get Operational Data", "data.html", BODY("data"), "NOAA-identical grid-218 files, swap-in examples and subscription."),
    ("terms", "Terms", "terms.html", BODY("terms"), "Plain-language terms for the paid grids."),
]
for name, title, cur, body, desc in SPEC:
    open(os.path.join(PAGES, name + ".html"), "w").write(shell(title, body, current=cur, desc=desc))
    print("wrote", name + ".html")
for script in ("costs.py", "scorecard.py"):
    subprocess.run([sys.executable, os.path.join(HERE, script)], check=True)

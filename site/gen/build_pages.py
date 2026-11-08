#!/usr/bin/env python3
"""Build every page of the mockup into site/pages/ (standard library only).

    python3 site/gen/build_pages.py            # home, about, validation, grids, redirects (data, scorecard), terms, then costs

Bodies: gen/body/{index,about,grids,terms}.html; cases.json (the grids table); validation.py (figures from figs.py, drop-ins from hindcast.json);
costs.py as before. Edit those, not the generated HTML."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(os.path.dirname(HERE), "pages")
sys.path.insert(0, HERE)
from common import shell  # noqa: E402
import validation  # noqa: E402
from common import esc, human_bytes  # noqa: E402
import json  # noqa: E402


def cases_table() -> str:
    d = json.load(open(os.path.join(HERE, "cases.json")))
    rows = []
    for c in d["cases"]:
        if c["status"] == "available":
            idx = f"grids/nam.{c['date']}/index.html"
            rows.append(f'<tr><td>{c["cycle"]}</td><td>{esc(c["event"])}<br><span class="small">{esc(c.get("note", ""))}</span></td>'
                        f'<td><a href="{idx}">Index</a></td><td class="n">{human_bytes(c["bytes"])}</td></tr>')
        else:
            rows.append(f'<tr><td>{c["cycle"]}</td><td>{esc(c["event"])}</td><td>&ndash;</td><td class="n">&ndash;</td></tr>')
    return ('<div class="tblwrap"><table><tr><th>Cycle</th><th>Event</th><th>Files</th><th class="n">Total size</th></tr>'
            + "".join(rows) + "</table></div>")


BODY = lambda n: open(os.path.join(HERE, "body", n + ".html")).read()  # noqa: E731
SPEC = [
    ("index", "FrankenNAM: an open source project to keep the NAM model alive", "", BODY("index").replace("{{HOW_CLOSE}}", validation.how_close(validation.pooled())),
     "A community service explaining how the retired NAM can be brought back, with a case viewer."),
    ("about", "About FrankenNAM", "about.html", BODY("about"), "The design, how a run starts, the strategies we tried for bringing the NAM back, what a live cycle would take, and the comparison with the operational NAM."),
    ("validation", "Validation", "validation.html", validation.body(), "How close FrankenNAM is to the archived NAM and how far from the GFS: grid-to-grid distances, dew point, feature cases and side-by-side maps."),
    ("grids", "Grids", "grids.html", BODY("grids").replace("{{CASES_TABLE}}", cases_table()),
     "Free NOAA-named grid-218 files for the re-run cases, with swap-in examples."),
    ("data", "Moved: Grids", "", '<h1>Moved</h1><p>This page is now <a href="grids.html">Grids</a>.</p>', "Moved to the Grids page."),
    ("scorecard", "Moved: Validation", "", '<h1>Moved</h1><p>This page is now <a href="validation.html">Validation</a>.</p>', "Moved to the Validation page."),
    ("terms", "Terms", "terms.html", BODY("terms"), "Short terms of use for the free data."),
    ("404", "Page not found", "", '<h1>Page not found</h1><p>That page is not here. Try the <a href="/">home page</a> or the <a href="/maps/">maps</a>.</p>', "Not found."),
]
for name, title, cur, body, desc in SPEC:
    root = "/" if name == "404" else ""   # served for any missing path, so its links must be absolute
    dest = {"data": "grids.html", "scorecard": "validation.html"}.get(name)
    head = f'<meta http-equiv="refresh" content="0; url={dest}">\n<link rel="canonical" href="{dest}">\n' if dest else ""
    open(os.path.join(PAGES, name + ".html"), "w").write(shell(title, body, current=cur, desc=desc, root=root, extra_head=head))
    print("wrote", name + ".html")
for script in ("costs.py",):
    subprocess.run([sys.executable, os.path.join(HERE, script)], check=True)

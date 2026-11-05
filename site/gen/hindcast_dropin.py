#!/usr/bin/env python3
"""Drop the six-case hindcast highlights into the Validation page (standard library only).

    python site/gen/hindcast_dropin.py --figs docs/figs/hindcast [--table docs/figs/hindcast/results.csv] \
                                       [--text text.json] [--dry-run]
    python site/gen/build_pages.py            # rebuilds validation.html (and the other pages)

--figs   folder of double-panel images; each image goes to the case whose key (date, case id or short name,
         see hindcast.json) appears in the file name. If several match, the first by name is used; a case
         may also be given explicitly as  --image CASEID=path.png  (repeatable). Images are copied to
         site/pages/img/hindcast/ and recorded in hindcast.json.
--table  CSV with the header  metric,fnam,nam,gfs,gfs06,gate  replaces the results rows (empty cell = pending).
--text   JSON {"CASEID": ["line", "line"]} sets the 2-3 lines of text per case.
Nothing here reads the hindcast outputs unless you point it at them."""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(os.path.dirname(HERE), "pages")
JS = os.path.join(HERE, "hindcast.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--figs"); ap.add_argument("--table"); ap.add_argument("--text")
    ap.add_argument("--image", action="append", default=[], metavar="CASEID=FILE")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    d = json.load(open(JS))
    cases = {c["id"]: c for c in d["cases"]}
    found = {}
    if a.figs:
        for fn in sorted(os.listdir(a.figs)):
            if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue
            for c in d["cases"]:
                if c["id"] not in found and any(k.lower() in fn.lower() for k in c["keys"]):
                    found[c["id"]] = os.path.join(a.figs, fn)
    for kv in a.image:
        k, v = kv.split("=", 1); found[k] = v
    dest = os.path.join(PAGES, "img", "hindcast")
    for cid, src in found.items():
        name = f"{cid}{os.path.splitext(src)[1].lower()}"
        print(f"{cid}: {src} -> img/hindcast/{name}")
        if not a.dry_run:
            os.makedirs(dest, exist_ok=True); shutil.copyfile(src, os.path.join(dest, name))
            cases[cid]["image"] = f"img/hindcast/{name}"
    for c in d["cases"]:
        if c["id"] not in found:
            print(f"{c['id']}: no image (placeholder stays)" if not c["image"] else f"{c['id']}: keeps {c['image']}")
    if a.text:
        for cid, lines in json.load(open(a.text)).items():
            cases[cid]["text"] = lines
    if a.table:
        rows = []
        for r in csv.DictReader(open(a.table)):
            rows.append([r["metric"]] + [(r[k] or None) for k in ("fnam", "nam", "gfs", "gfs06", "gate")])
        d["results"]["rows"] = rows
    if not a.dry_run:
        json.dump(d, open(JS, "w"), indent=2); open(JS, "a").write("\n")


if __name__ == "__main__":
    main()

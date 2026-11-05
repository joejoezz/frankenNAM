#!/usr/bin/env python3
"""Status and index pages for the grid host, written from a products prefix.

    python site/gen/grid_index.py --src ~/data/nam-recast-site/frank --out /tmp/grid
    python site/gen/grid_index.py --src s3://nam-recast-617711905691/products --region us-west-2 --out /tmp/grid

--src is a directory or an S3 prefix holding nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2 (+ .idx), the layout NOMADS
used. S3 is read through the aws CLI (no boto3 needed); only listings and, for the SHA-256, a streamed read of each
new object. Hashes are cached in <out>/sha256.json by (size, etag-or-mtime), so a rerun hashes only new files.

Writes into --out (put it next to the files, or copy it there):
  status.json                              one record per cycle in the window, newest first
  index.html                               the cycles, newest first, with state and link
  nam.YYYYMMDD/index.html                  every file of the date's cycles with size and SHA-256
  nam.YYYYMMDD/nam.tCCz.cycle.json         the same per cycle, machine readable

A cycle is 'complete' when all 29 hours (f00..f84 by 3) have a GRIB2 and an .idx; 'running' when it is not complete
and a file was written within --stale-minutes of now; 'incomplete' when it is not complete and nothing has arrived for
longer than that. The idx is the signal that an hour is ready (it is written after its GRIB2)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HONESTY, esc, human_bytes, shell  # noqa: E402

HOURS = list(range(0, 85, 3))
NAME = re.compile(r"^nam\.(\d{8})/nam\.t(\d\d)z\.awphys(\d\d)\.tm00\.grib2(\.idx)?$")
UTC = timezone.utc


# ---------------------------------------------------------------- stores
class LocalStore:
    def __init__(self, root):
        self.root = os.path.expanduser(root)

    def list(self):
        """[(key, size, modified datetime, token)] for every file under nam.YYYYMMDD/."""
        out = []
        for d in sorted(os.listdir(self.root)):
            if not re.fullmatch(r"nam\.\d{8}", d):
                continue
            for f in sorted(os.listdir(os.path.join(self.root, d))):
                p = os.path.join(self.root, d, f)
                st = os.stat(p)
                out.append((f"{d}/{f}", st.st_size, datetime.fromtimestamp(st.st_mtime, UTC), str(int(st.st_mtime))))
        return out

    def sha256(self, key):
        h = hashlib.sha256()
        with open(os.path.join(self.root, key), "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()


class S3Store:
    def __init__(self, uri, region):
        m = re.match(r"^s3://([^/]+)/?(.*)$", uri)
        self.bucket, self.prefix = m.group(1), m.group(2).strip("/")
        self.region = region

    def _aws(self, *a, text=True):
        return subprocess.run(["aws", "--region", self.region, *a], check=True, capture_output=True, text=text).stdout

    def list(self):
        out, token = [], None
        while True:
            a = ["s3api", "list-objects-v2", "--bucket", self.bucket, "--prefix", self.prefix + "/", "--output", "json"]
            if token:
                a += ["--starting-token", token]
            d = json.loads(self._aws(*a) or "{}")
            for o in d.get("Contents", []):
                key = o["Key"][len(self.prefix) + 1:]
                if re.fullmatch(r"nam\.\d{8}/.+", key):
                    out.append((key, o["Size"], datetime.fromisoformat(o["LastModified"].replace("Z", "+00:00")), o["ETag"].strip('"')))
            token = d.get("NextToken")
            if not token:
                return sorted(out)

    def sha256(self, key):
        p = subprocess.Popen(["aws", "--region", self.region, "s3", "cp", f"s3://{self.bucket}/{self.prefix}/{key}", "-"],
                             stdout=subprocess.PIPE)
        h = hashlib.sha256()
        for b in iter(lambda: p.stdout.read(1 << 20), b""):
            h.update(b)
        if p.wait():
            raise RuntimeError(f"aws s3 cp failed for {key}")
        return h.hexdigest()


# ---------------------------------------------------------------- model
def scan(store, now, window_days, stale_min, hashes, log=print):
    """Group the listing into cycles; hash files lazily (cache in `hashes`)."""
    cyc = {}
    for key, size, mod, tok in store.list():
        m = NAME.match(key)
        if not m:
            continue
        ymd, hh, fh, idx = m.group(1), m.group(2), int(m.group(3)), bool(m.group(4))
        cyc.setdefault(ymd + hh, {})[(fh, idx)] = (key, size, mod, tok)
    newest = max(cyc) if cyc else None
    cutoff = now - timedelta(days=window_days)
    out = []
    for c in sorted(cyc, reverse=True):
        init = datetime.strptime(c, "%Y%m%d%H").replace(tzinfo=UTC)
        if init < cutoff:
            continue
        files = cyc[c]
        ready = [h for h in HOURS if (h, True) in files and (h, False) in files]
        rows = []
        for (fh, idx), (key, size, mod, tok) in sorted(files.items()):
            ck = hashes.get(key)
            if not ck or ck["token"] != tok or ck["size"] != size:
                log(f"sha256 {key}")
                ck = hashes[key] = {"token": tok, "size": size, "sha256": store.sha256(key)}
            rows.append({"name": key.split("/", 1)[1], "path": key, "hour": fh, "kind": "idx" if idx else "grib2",
                         "size": size, "modified": mod.strftime("%Y-%m-%dT%H:%M:%SZ"), "sha256": ck["sha256"]})
        last_mod = max(f[2] for f in files.values())
        complete = len(ready) == len(HOURS)
        state = "complete" if complete else ("running" if now - last_mod <= timedelta(minutes=stale_min) else "incomplete")
        done_at = max(files[(h, True)][2] for h in HOURS) if complete else None
        first = min(f[2] for f in files.values())
        out.append({"cycle": c, "date": c[:8], "hour": c[8:], "state": state, "expected_hours": len(HOURS),
                    "hours_ready": ready, "last_hour_ready": ready[-1] if ready else None,
                    "first_file_at": first.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "completed_at": done_at.strftime("%Y-%m-%dT%H:%M:%SZ") if done_at else None,
                    "last_file_at": last_mod.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "minutes_after_cycle_time_at_completion": (lambda m: m if 0 <= m <= 1440 else None)(round((done_at - init).total_seconds() / 60)) if done_at else None,
                    "file_count": len(rows), "bytes": sum(r["size"] for r in rows), "files": rows})
    return out


# ---------------------------------------------------------------- output
def stamp(iso):
    return iso.replace("T", " ").replace("Z", "Z") if iso else "&ndash;"


def date_page(date, cycles):
    body = [f"<h1>nam.{date}</h1>",
            '<p class="lede">File names here are the operational NAM&rsquo;s, on purpose, so existing tools work with a changed base URL only. '
            "The contents are not the NAM&rsquo;s.</p>",
            f'<div class="honest"><p><b>FrankenNAM.</b> {HONESTY}</p></div>',
            '<p class="small"><a href="../index.html">All cycles</a></p>']
    for cy in cycles:
        body.append(f"<h2>t{cy['hour']}z &middot; {cy['state']}</h2>")
        body.append(f'<p class="small">{len(cy["hours_ready"])} of {cy["expected_hours"]} hours ready'
                    + (f"; last hour f{cy['last_hour_ready']:02d}" if cy["last_hour_ready"] is not None else "")
                    + (f"; completed {stamp(cy['completed_at'])}" if cy["completed_at"] else "")
                    + f' &middot; {cy["file_count"]} files, {human_bytes(cy["bytes"])} &middot; '
                      f'<a href="nam.t{cy["hour"]}z.cycle.json">cycle.json</a></p>')
        body.append('<table><tr><th>File</th><th class="n">Size</th><th>Written (UTC)</th><th>SHA-256</th></tr>')
        for r in cy["files"]:
            body.append(f'<tr><td><a href="{esc(r["name"])}">{esc(r["name"])}</a></td><td class="n">{human_bytes(r["size"])}</td>'
                        f'<td>{stamp(r["modified"])}</td><td><code style="font-size:11px;word-break:break-all">{r["sha256"]}</code></td></tr>')
        body.append("</table>")
    return shell(f"FrankenNAM nam.{date}", "\n".join(body), root="../", desc="Files of one date, with sizes and SHA-256.")


def root_page(cycles, now, window_days):
    body = ["<h1>FrankenNAM grids</h1>",
            '<p class="lede">Every FrankenNAM cycle of the last %d days, newest first. File names follow NOMADS: '
            "<code>nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2</code> and its <code>.idx</code>. "
            "The names are NOAA-identical on purpose so that wgrib2, Herbie and curl scripts work unchanged; the files are not NOAA&rsquo;s.</p>" % window_days,
            f'<div class="honest"><p><b>What these files are.</b> {HONESTY}</p></div>',
            '<p class="small">Machine-readable: <a href="status.json">status.json</a>. Updated %s.</p>' % stamp(now.strftime("%Y-%m-%dT%H:%M:%SZ")),
            '<table><tr><th>Cycle</th><th>State</th><th class="n">Hours ready</th><th>Last hour</th><th>Completed (UTC)</th><th class="n">Files</th><th class="n">Size</th></tr>']
    for cy in cycles:
        body.append(f'<tr><td><a href="nam.{cy["date"]}/index.html#t{cy["hour"]}z">{cy["date"]} {cy["hour"]}Z</a></td><td>{cy["state"]}</td>'
                    f'<td class="n">{len(cy["hours_ready"])} / {cy["expected_hours"]}</td>'
                    f'<td>{("f%02d" % cy["last_hour_ready"]) if cy["last_hour_ready"] is not None else "&ndash;"}</td>'
                    f'<td>{stamp(cy["completed_at"])}</td><td class="n">{cy["file_count"]}</td><td class="n">{human_bytes(cy["bytes"])}</td></tr>')
    if not cycles:
        body.append('<tr><td colspan="7">No cycles in the window.</td></tr>')
    body.append("</table>")
    return shell("FrankenNAM grids", "\n".join(body), root="", desc="FrankenNAM cycle status and file index.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--region", default="us-west-2")
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--stale-minutes", type=int, default=90)
    ap.add_argument("--now", default=None, help="ISO UTC time for the window (default: now); the sample cycle is old")
    a = ap.parse_args(argv)
    now = datetime.fromisoformat(a.now.replace("Z", "+00:00")).astimezone(UTC) if a.now else datetime.now(UTC)
    store = S3Store(a.src, a.region) if a.src.startswith("s3://") else LocalStore(a.src)
    out = os.path.expanduser(a.out)
    os.makedirs(out, exist_ok=True)
    hp = os.path.join(out, "sha256.json")
    hashes = json.load(open(hp)) if os.path.exists(hp) else {}
    cycles = scan(store, now, a.window_days, a.stale_minutes, hashes)
    json.dump(hashes, open(hp, "w"), indent=0)
    status = {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "window_days": a.window_days, "note": HONESTY.replace("&minus;", "-").replace("&nbsp;", " "),
              "cycles": [{k: v for k, v in c.items() if k != "files"} for c in cycles]}
    json.dump(status, open(os.path.join(out, "status.json"), "w"), indent=1)
    open(os.path.join(out, "index.html"), "w").write(root_page(cycles, now, a.window_days))
    bydate = {}
    for c in cycles:
        bydate.setdefault(c["date"], []).append(c)
        d = os.path.join(out, f"nam.{c['date']}")
        os.makedirs(d, exist_ok=True)
        json.dump(c, open(os.path.join(d, f"nam.t{c['hour']}z.cycle.json"), "w"), indent=1)
    for date, cs in bydate.items():
        open(os.path.join(out, f"nam.{date}", "index.html"), "w").write(date_page(date, cs))
    print(f"{len(cycles)} cycles, {sum(c['file_count'] for c in cycles)} files -> {out}")


if __name__ == "__main__":
    main()

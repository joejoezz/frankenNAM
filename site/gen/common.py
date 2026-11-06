"""Shared bits of the page generators: the HTML shell (same header, footer and style.css as site/pages),
the honesty line, and small formatters. Plain strings, no template engine."""
from __future__ import annotations

import html

NAV = [("about.html", "About FrankenNAM"), ("validation.html", "Validation"), ("grids.html", "Grids"), ("costs.html", "Costs"),
       ("https://theconvergencezone.com/contact/", "Contact")]

TAGLINE = "an open source project to keep the NAM model alive"
NOT_AFFILIATED = "A community project. Not affiliated with or endorsed by NOAA or the National Weather Service."

HONESTY_SHORT = ("Initialized from the (C&minus;6)Z GFS analysis with a 6&nbsp;h NAM spin-up. "
                 "No observations after (C&minus;6)Z.")
HONESTY = HONESTY_SHORT + " Not produced by NOAA and not affiliated with NOAA."

# The footer links resolve against the page root; config.js (one config spot) fills the GitHub link.
FOOT = ('<p><b>{h}</b></p><p>{n} Operated by Joe Boomgard-Zagrodnik.</p>'
        '<p><a href="{r}costs.html">Costs</a> &middot; <a href="{r}grids.html">Grids</a> &middot; <a href="{r}terms.html">Terms</a> &middot; '
        '<a href="{r}scorecard.html">Baseline scorecard</a> &middot; '
        '<a data-cfg-href="GITHUB_URL" href="#">GitHub</a> <span class="ph">[PLACEHOLDER: repository URL]</span> &middot; '
        '<a href="https://theconvergencezone.com/contact/">Contact</a></p>')

def esc(s) -> str:
    return html.escape(str(s), quote=True)


def shell(title: str, body: str, current: str = "", desc: str = "", root: str = "", extra_head: str = "") -> str:
    """root is the relative path back to the pages (e.g. '' or '../'). current is the nav href of the page."""
    nav = "".join(f'<a href="{h if h.startswith("http") else root + h}"' + (' aria-current="page"' if h == current else "") + f">{t}</a>"
                  for h, t in NAV)
    d = f'<meta name="description" content="{esc(desc)}">\n' if desc else ""
    head = (f'<header class="top"><div class="bar"><a class="logo" href="{root}index.html"><img src="{root}assets/nam-logo.png" '
            f'alt="NAM: the North American Mesoscale Forecast System" width="96" height="64"></a>'
            f'<div class="id"><a class="brand" href="{root}index.html">FrankenNAM</a><span class="tag">{TAGLINE}</span>'
            f'<span class="na">{NOT_AFFILIATED}</span></div></div><nav>{nav}</nav></header>')
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{esc(title)}</title>\n{d}'
            f'<link rel="stylesheet" href="{root}style.css">\n<script src="{root}config.js"></script>\n{extra_head}</head>\n<body>\n'
            f'{head}\n<main>\n\n{body}\n</main>\n<footer class="bot">{FOOT.format(r=root, h=HONESTY_SHORT, n=NOT_AFFILIATED)}</footer>\n'
            f'<script src="{root}site.js"></script>\n</body>\n</html>\n')


def human_bytes(n: int) -> str:
    x = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or u == "TB":
            return f"{int(x)} {u}" if u == "B" else f"{x:.1f} {u}"
        x /= 1024

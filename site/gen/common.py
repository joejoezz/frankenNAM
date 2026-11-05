"""Shared bits of the page generators: the HTML shell (same header, footer and style.css as site/pages),
the honesty line, and small formatters. Plain strings, no template engine."""
from __future__ import annotations

import html

NAV = [("index.html", "Home"), ("maps/", "Maps"), ("scorecard.html", "Scorecard"), ("costs.html", "Costs"),
       ("subscribe.html", "Subscribe"), ("terms.html", "Terms")]

HONESTY = ("Initialized from the (C&minus;6)Z GFS analysis with a 6&nbsp;h NAM spin-up. "
           "No observations after (C&minus;6)Z. Not produced by NOAA and not affiliated with NOAA.")

FOOT = ('FrankenNAM is a community recast of the retired NAM, run by <span class="ph">[PLACEHOLDER: LLC name]</span>. '
        '<a href="{r}terms.html">Terms</a> &middot; <a href="{r}costs.html">What it costs</a> &middot; '
        '<a href="https://theconvergencezone.com">The Convergence Zone</a>')


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def shell(title: str, body: str, current: str = "", desc: str = "", root: str = "", extra_head: str = "") -> str:
    """root is the relative path back to the pages (e.g. '' or '../')."""
    nav = "".join(f'<a href="{root}{h}"' + (' aria-current="page"' if h == current else "") + f">{t}</a>" for h, t in NAV)
    d = f'<meta name="description" content="{esc(desc)}">\n' if desc else ""
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{esc(title)}</title>\n{d}'
            f'<link rel="stylesheet" href="{root}style.css">\n{extra_head}</head>\n<body>\n'
            f'<header class="top"><a class="brand" href="{root}index.html">FrankenNAM</a><nav>{nav}</nav></header>\n'
            f'<main>\n\n{body}\n</main>\n<footer class="bot">{FOOT.format(r=root)}</footer>\n</body>\n</html>\n')


def human_bytes(n: int) -> str:
    x = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or u == "TB":
            return f"{int(x)} {u}" if u == "B" else f"{x:.1f} {u}"
        x /= 1024

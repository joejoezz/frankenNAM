#!/usr/bin/env python3
"""Full-page screenshots of the assembled mockup, desktop (1280 wide) and phone (390 wide), into site/samples/.
Needs Playwright with Chromium (not in the site venv; any venv that has it):
    python site/gen/screenshots.py [MOCKUP_DIR]"""
import os
import sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "samples")
M = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/data/nam-recast-site/mockup"))
PAGES = ["index", "about", "validation", "data", "costs", "terms", "scorecard"]
with sync_playwright() as p:
    b = p.chromium.launch()
    for tag, w, h in (("desktop", 1280, 900), ("phone", 390, 800)):
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1 if tag == "desktop" else 2)
        for n in PAGES:
            pg.goto(f"file://{M}/{n}.html"); pg.wait_for_load_state("load")
            if n == "index":
                pg.locator(".viewer").scroll_into_view_if_needed()
                pg.frame_locator("iframe").locator("#img").wait_for(state="visible"); pg.wait_for_timeout(2500)
            pg.evaluate("document.querySelectorAll('img').forEach(i=>{i.loading='eager'})"); pg.wait_for_timeout(600)
            pg.screenshot(path=os.path.join(OUT, f"mockup-{n}-{tag}.png"), full_page=True)
            print("wrote", f"mockup-{n}-{tag}.png")
    b.close()

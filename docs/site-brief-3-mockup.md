# Site brief 3: the public site mockup (Joe's layout, 5 Nov 2026)

Build a complete static mockup of nam.theconvergencezone.com under `site/pages/` (rework the
existing drafts; keep the generators in `site/gen/` working and wire their output in). Nothing is
deployed. Read first: `site/README.md`, `docs/product-plan.md`, `docs/tm06-design.md` (sections 1,
5, 7, 9), `docs/baseline-scorecard.md`, `docs/scoping.md`, `docs/related-work-woof-nam.md`.

## Joe's layout (follow it exactly)
**Header on every page:** title "FrankenNAM" with the tagline "an open source project to keep the
NAM model alive", and the logo `site/assets/nam-logo.png` (provided by Joe; it is the NAM project
graphic, a US-government work). Directly under the logo or in the header, one small line: "A
community project. Not affiliated with or endorsed by NOAA or the National Weather Service."
**Nav links:** "About FrankenNAM" · "Validation" · "Get Operational Data" · "Contact" (Contact goes to
https://theconvergencezone.com/contact/, opens in the same tab).

**Home page, below the nav:**
1. **"Why?"**: the 12 km NAM ran for over two decades and forecasters still rely on it (wedge/CAD,
   soundings, p-type, mesoscale structure); NOAA retired it on 3 Nov 2026; one run costs under $3
   on cloud hardware (measured: ≈ $2.60 per cycle); keeping it running is an inexpensive project that
   keeps providing value to the community. Short, plain, no hype.
2. **"Latest fNAM"** (fNAM = shorthand for FrankenNAM; introduce it once): the existing single-panel
   viewer embedded (iframe or inline), **no compare mode on this page** (hide/disable it via a URL
   parameter or a build flag; the compare code can stay for later). Uses the rendered tm06 run of
   2026-11-01 00Z as the sample, labelled as a sample until live cycles exist.

**About FrankenNAM:** the design of the project: the NAM's own code (NMMB/NEMS, NPS, UPP from the
operational source), built on AWS Graviton; the tm06 cycle (GFS analysis 6 h before the cycle +
6 h NAM spin-up; NAM-seeded soil; no data assimilation) and the honesty line; delivery clock
(measured/projected from tm06-design section 5); cost per run. **The comparison table FrankenNAM vs
the operational NAM** (rows: code, grid/levels/time step, physics, initial conditions, data
assimilation, land state, boundaries, nests, cycles per day, products/file names, delivery time,
who runs it). Brief history of the resurrection (source recovered from GitHub mirrors and the
Wayback Machine after the NCO tree was removed). Factual, sourced from the docs.

**Validation:** statistical results plus a few highlight plots.
- Statistics: the Phase 0 / tm06 acceptance fidelity table (tm06 vs archived NAM, with the
  analysis-start run and the GFS as context, from tm06-design section 7) and the baseline scorecard
  framing (what the operational NAM itself scored against observations, with the GFS alongside).
  The framing is fidelity to the NAM, never "beats the GFS" (see the gate in docs/phase1-plan.md).
- **A few graphs**: e.g. RMSE vs NAM by lead for tm06 / analysis start / GFS (from the stats CSVs
  in `docs/figs/tm06/` and `docs/figs/case-2026110100*/`), and one soil-trace bar chart.
- **A few double-panel comparison plots** (fNAM | archived NAM, same field/time/scale) capturing
  highlights: render them from the 2026-11-01 products now (e.g. f48 MSLP+precip, f24 2 m T).
- **Hindcast highlights section with placeholders**: the six-case hindcast (CAD ice storm 23 Jan
  2026, Snowcrete 5 Jan 2025, Gulf snow 21 Jan 2025, PNW bomb cyclone 19 Nov 2024, Plains
  14 Mar 2025, lake effect 29 Dec 2025) is running right now in another agent and will write
  `docs/phase1-scorecard.md` and `docs/figs/hindcast/`. Do NOT read or wait for those; lay out
  one card per case with a placeholder box for a double-panel image and 2-3 lines of text, plus a
  placeholder results table, so they can be dropped in later. Make the drop-in a small script or
  a clearly documented step.

**Get Operational Data:**
- What is available: a full mirror of the NAM's grid-218 awphys product with **NOAA-identical file
  names and paths** (`nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2` + `.idx`), f00-f84 every 3 h, 00Z and
  12Z, so existing tools work by swapping the base URL; plus an **Icechunk/Zarr** store of the same
  fields for Python users (mark it "coming soon").
- Swap-in examples (from `site/products/README.md`).
- **Subscribe**: $14.99/month, monthly only, cancel any time. Founding members (first 15
  subscribers) drop to $9.99/month once 20 paying subscribers are reached. Say plainly the goal is
  to cover running costs, link the cost page, show the pledge counter (placeholder "0 of 20").
  A "Subscribe" button wired to a placeholder Stripe Payment Link URL (`STRIPE_PAYMENT_LINK` in one
  config spot). Free maps stay free. Terms link.
- Keep the existing costs and terms pages, reachable from this page and the footer.

**Footer:** honesty line, not-affiliated line, links to costs, terms, GitHub repo (placeholder URL),
Contact.

## Style and rules
Plain HTML/CSS/JS, no frameworks, the look of the existing site pages; mobile-friendly; logo
sized sensibly. Plot text terse, explanations in "?" boxes; no time-bound wording ("this fall");
no claims not in the docs (no "verified" beyond what the tables show). Take full-page screenshots
of every page (desktop and phone width) into `site/samples/mockup-*.png`. Touch only `site/`; the
hindcast agent owns `run/`, `deploy/`, `verify/`, `docs/`, S3 and EC2: do not touch those. Data you
may read: `~/data/nam-recast-site/` (already rendered products and archive), the repo's docs and
figs. Commit small with named paths, never `git add -A`, end commits with
`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Report what you built, the
screenshots' paths, and open questions.

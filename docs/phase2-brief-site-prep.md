# Brief: site and map-viewer preparation (no deployment)

Runs in parallel with briefs A and B-prep. **Touches only `site/` in this repo**; creates no AWS
resources, no DNS, no Cloudflare, no instances; spends $0 on AWS. Develops against the archived
operational NAM (`s3://noaa-nam-pds`, public, free egress), whose grid-218 `awphys` files are
identical in form to what FrankenNAM will produce.

Read first: `docs/product-plan.md` (the agreed site design, field list, pricing, transparency
page), `docs/scoping.md` (what FrankenNAM is), `docs/phase1-plan.md` ("Decisions taken" sections).
Then read, **read-only**, `~/projects/ensplots` (the maps.theconvergencezone.com renderer, Lambda
and image-loop viewer) and follow its conventions for the viewer UX and the rendering style. Also
read `~/projects/enso-dashboard/.claude/skills/plot-labeling` (read-only) for Joe's plot-text
rules: terse labels on the plot, explanations in a "?" box.

## Deliverables (all under `site/`)
1. `site/render/`: Python renderer that takes one cycle of grid-218 `awphys` GRIB2 files
   (f00-f84, 3-hourly) and renders the product-plan field list to PNGs: MSLP + 6 h precip,
   500 hPa height + vorticity, 700 hPa RH + omega, 850 hPa T + wind, 2 m T, 2 m Td, 10 m wind,
   simulated composite reflectivity, p-type (CSNOW/CICEP/CFRZR/CRAIN), 6 h precip, run-total precip,
   snowfall (10:1 and Kuchera from the column temperatures), CAPE/CIN, PWAT. Regions: CONUS plus the
   regional cutouts maps.theconvergencezone.com uses. Same map style, fonts, colour conventions and
   file-naming scheme as ensplots so the two sites feel like one. Must run as a function of
   (cycle, field, region, fhr) so it fits the ensplots Lambda pattern later. Time it.
2. `site/viewer/`: a static viewer page with the maps.tcz UX (field/region selectors, forecast-hour
   loop, keyboard stepping) wired to the rendered PNGs via the same naming scheme, plus a "?" box
   per field. Must work from a local directory and from an S3/R2 prefix with no code change.
3. `site/pages/`: static homepage draft per `docs/product-plan.md`: the resurrection story (short,
   factual, drawn from `docs/scoping.md`), the honesty line, "what it is / is not", the delivery
   clock, a scorecard page skeleton (tables to be fed by `verify/` later), the running-cost page
   skeleton (compute, transfer, storage, subscriber count vs the 20 pledge, startup costs), the
   subscribe page copy (monthly only $14.99, founding 15 → $9.99 at the pledge, swap-in instructions
   for wgrib2, Herbie and BUFKIT with the key-in-URL pattern), and a plain-language terms page
   (monthly, cancel any time, service may wind down with a month's notice). Not affiliated with
   NOAA, stated once, clearly. No external JS frameworks; plain HTML/CSS/JS like the other sites.
4. `site/README.md`: how to render a cycle and view it locally, and the **deployment plan** as a
   document only: Lambda + S3 + CloudFront for the maps (ensplots pattern) vs Cloudflare R2 +
   Worker for grids and key validation, with costs; nothing deployed.
5. A rendered sample: the archived NAM 2026-11-01 00Z cycle (pull the 29 `awphys` files from
   `noaa-nam-pds` to `~/data/nam-recast-site/`, ~1.8 GB, free), all fields, CONUS + one region, and
   a screenshot of the viewer showing it. Commit the viewer and the pages; commit only a handful of
   sample PNGs (not the whole set).

## Acceptance
- `python -m site.render --cycle 2026110100 --src ~/data/nam-recast-site/nam.20261101 --out /tmp/x`
  renders every field for CONUS in under 10 min on the laptop; the viewer opens from `/tmp/x`.
- The homepage, subscribe and terms pages read as finished copy a forecaster would trust, with no
  claims the project has not earned yet (no "verified", no skill numbers; placeholders are marked).

## Rules
- $0 AWS; nothing created outside `site/`; ensplots, enso-dashboard, wsis and PPS are read-only.
- Plot text terse, explanations in the "?" box; no "this fall" style time-bound wording anywhere.
- Commit small with named paths (no `git add -A`), author is Joe (configured), end commit messages
  with the Co-Authored-By line set for this session. Report in plain text with timings and commits.

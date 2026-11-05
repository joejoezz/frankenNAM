# Site brief 2: real FrankenNAM output in the viewer, status/index pages, scorecard and cost generators

Continues `docs/phase2-brief-site-prep.md`; read it and `site/README.md` first, plus
`docs/product-plan.md`, `docs/tm06-design.md` (sections 1, 3, 7) and `docs/baseline-scorecard.md`.
Touch only `site/` (and add `LICENSE` + `NOTICE` at the repo root, item 6). Deploy nothing; no AWS
resources, no DNS, no Cloudflare. Allowed AWS use: read-only downloads from
`s3://nam-recast-617711905691/products/nam.20261101/` (~1.8 GB, ~$0.16) and the public NOAA buckets.

1. **FrankenNAM in the viewer.** Render the real tm06 products for 2026-11-01 00Z with
   `--product frankennam` (honesty footer). Add a **compare mode** to the viewer: FrankenNAM and the
   archived NAM side by side (or a toggle) for the same field/region/hour, synced scrubbing. Keep it
   working from a local folder and an S3/R2 prefix. Commit only a few sample PNGs + a screenshot.
2. **Run status and grid index pages** (the grid host's face): a generator that, from a products
   prefix, writes `status.json` (per cycle: state, last hour ready, completion time, file count,
   bytes) and a plain `index.html` per cycle listing every GRIB2/.idx with size and SHA-256
   (`cycle.json` too), newest cycle first, 7-day window. Paths mirror NOMADS
   (`nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2`). Text states the file names are NOAA-identical on
   purpose and carries the honesty line.
3. **Scorecard page generator** from `verify/results/` (CSV/sums): renders the baseline tables now
   (NAM, GFS, 6 h older GFS) with an empty FrankenNAM column that fills when `fnam` results exist;
   fidelity framing per the rewritten gate (`docs/phase1-plan.md`). No skill claims beyond the data.
4. **Cost page generator** fed by a small JSON (compute per cycle, monthly compute/transfer/storage,
   subscriber count vs the 20 pledge, startup costs by phase: Phase 0 $10.6, Graviton port $9.4,
   brief A $7.0, staging $2.9; engineering time stated in words). Include a script stub that would
   fill the JSON from AWS Cost Explorer by the `project=nam-recast` tag (write it, do NOT run it).
5. **Products README** for the grid host (what FrankenNAM is, honesty line, tm06 explained, NOAA-
   identical names, swap-in snippets for wgrib2/Herbie/curl byte-range with the key-in-URL pattern,
   retention, contact placeholder), consistent with the site pages.
6. **LICENSE + NOTICE** at the repo root as drafts marked `[DECISION NEEDED: Joe]` for the licence
   choice (recommend Apache-2.0 for our code), with the NOTICE covering NOAA/NCEP public-domain
   source, AER RRTM/RRTMG (BSD-3), NCEPLIBS, ESMF (its licence), WRF-derived tables. Read
   `docs/related-work-woof-nam.md` for how WOOF-NAM worded theirs; write our own.
Rules: plot text terse, explanations in "?" boxes, no time-bound wording; no claims we have not
earned (no "verified", no skill numbers outside the scorecard). Commit small with named paths,
author is Joe, end commits with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
Report what you built, timings, open questions, commits.

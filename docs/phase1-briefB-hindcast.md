# Brief B: the six-case hindcast and the fidelity scorecard

Read first: `docs/phase1-plan.md` ("Gate to Phase 2", rewritten for fidelity), `docs/tm06-design.md`
(how the tm06 product, chaining and products work; section 8 = traps), `docs/cases.md`,
`docs/baseline-scorecard.md`, `verify/README.md`, `run/README.md`.

## Runs (8 runner jobs, arm64, product config = tm06; ~$2.60 each)
| Case C | Arms |
|---|---|
| 2026012312 CAD ice storm | tm06 + anl (reference) |
| 2025010512 Snowcrete | tm06 + anl (reference) |
| 2025012100 Gulf snow | tm06 |
| 2024111912 PNW bomb cyclone | tm06 |
| 2025031412 Plains severe + blizzard | tm06 |
| 2025122912 Lake effect | tm06 |
Inputs are staged under `s3://nam-recast-617711905691/cases/<C>/` (gfs-tm06/, nam-archive/ incl.
the P-cycle awphys00 seed, gfs/ for the two anl cases). tm06 products go to
`cases/<C>/products/nam.YYYYMMDD/` (NOT the top-level products/ prefix); anl output to
`cases/<C>/recast-anl/`. The anl arm must also produce grid-218 products so verify/ can read it;
if `MODE=anl` lacks the products step, add it (same products.sh, no clock shift), document it.

**Use the new capacity:** the Spot quota is 64 vCPU = two 8xlarge runners at once. Put all 8 jobs
in the queue and start TWO chains (two runners launched from the laptop, each popping the queue
when done), CAD tm06 and Snowcrete tm06 first. Make the queue pop safe for two consumers (e.g. a
lock object with S3 conditional writes `--if-none-match`, or one queue file per job claimed by a
conditional put); test it with two short jobs before relying on it. A job line stays claimed-but-
not-done until its DONE marker exists; if a runner vanishes (Spot reclaim) or writes FAILED /
POST_FAILED, relaunch that job once, then report. Watch with ONE background watcher loop that
wakes you on markers; no foreground polling, no build box running while waiting.

## Scoring (laptop, verify/)
- Run `verify.run_baseline` with models nam, gfs, gfs06, fnam (tm06) and fnam-anl on all seven
  cases (the Phase 0 case's tm06 products are in `products/nam.20261101/`).
- Add a fidelity section: FrankenNAM vs archived NAM against observations (the gate margins in
  the plan: T/Td within 0.1 K, wind within 0.1 m/s, ETS within 0.03, same-sign bias) and the
  grid-to-grid tm06-vs-NAM stats from run/compare.py per case at f24/f48/f84.
- Feature fidelity: per case, 9-panels (FrankenNAM | NAM | GFS) at two event-relevant valid times
  with the fields that define the event (CAD: 2 m T + p-type + MSLP; Snowcrete: p-type + 850 T;
  Gulf: snowfall + p-type; PNW: MSLP + 24 h precip + 10 m wind; Plains: CAPE + MSLP + reflectivity;
  lake effect: 24 h snowfall + 850 T). Also MRMS composite reflectivity | FrankenNAM | NAM at the
  peak hour for CAD, Plains and lake effect (MRMS `MergedReflectivityQCComposite` on
  noaa-mrms-pds), the convention WOOF-NAM uses.
- Write `docs/phase1-scorecard.md`: tables, figures under `docs/figs/hindcast/`, the two-reference-
  case analysis (does tm06 track the NAM better than anl, and why: spin-up vs soil), and a plain
  one-page summary against the gate. Honest about seven cases and no significance tests.

## Rules
Budget **$25** (8 runs ≈ $21 + retries/staging); report spend. Terminate every runner; no open Spot
requests; never the x86 box; arm box only if you must rebuild, stopped when idle. Touch only this
repo (not `site/`) and this bucket; never other projects. Commit small with named paths, author is
Joe, end commits with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Report in plain
text with the gate verdict, numbers, cost and commits.

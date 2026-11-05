# Brief: a GPU engine for FrankenNAM (WOOF-NAM behind our product)

Written 5 Nov 2026 for a Sonnet agent. Owner: Joe Boomgard-Zagrodnik. Supervisor: the main session.

## Goal
Add an optional GPU engine to FrankenNAM: WOOF-NAM (github.com/recastsystems/woof-nam, Apache-2.0) runs the
forecast on one AWS GPU, and our pipeline turns its output into **the same product the CPU path makes**:
`nam.tCCz.awphysFF.tm00.grib2` + `.idx` for f00-f84 every 3 h, on grid 218, valid for cycle C, uploaded to the same
S3 product layout. The CPU path (NOAA Fortran on Graviton) stays the default. The GPU engine is switched on per run.
It is not used for the public product until a six-case fidelity check passes (docs/phase1-plan.md, last section).

## Read first
- docs/gpu-woof-trial.md: the trial (g7e.2xlarge, 36.5 s/forecast hour, $3.30/run, commit 49f2742, CLI flags used,
  "what else would have to run" list). deploy/10-gpu-trial.sh: the launch script and the `nam-recast-gpu` role.
- docs/related-work-woof-nam.md: what WOOF-NAM is, sections 3-5 especially.
- docs/tm06-design.md: our design: start at C-6 from the GFS analysis, boundaries from that same GFS cycle
  (f006-f090 in our naming), 6 h spin-up, f00 at C, Noah soil seeded.
- run/recast.sh, run/products.sh, run/runner.sh, run/launch.sh: the CPU path. Read them; do not edit them (below).
- A CPU product to match: s3://nam-recast-617711905691/products/nam.20261101/ (the tm06 run of 2026-11-01 00Z,
  454-record awphysFF files). The GPU trial's products are in s3://nam-recast-617711905691/gpu-trial/products/.
- run/score_woof.py and run/compare.py: scoring. Note the eccodes trap in score_woof.py (read the NAM first).

## What to build (new files only)
1. `run/gpu/` scripts for the GPU runner, following the shape of run/runner.sh:
   - **Install** WOOF-NAM pinned to a commit. Use 49f2742 unless a newer commit is needed for `--boco-age`; record
     the reason. Bootstrap at boot (pip took 47 s), no AMI.
   - **tm06 start:** start C-6 from the GFS analysis, run 90 h, with boundaries from that same GFS cycle
     (`--boco-age 0`, untested in the trial; verify it does what we want).
   - **Soil seeding,** matching our CPU path: Noah soil moisture, soil temperature, liquid soil water and snow water
     equivalent come from the seed (archived NAM awphys at C-6 for a hindcast, our previous cycle's product when
     live). Canopy water and snow depth are not seeded, the same as the CPU path; check recast.sh and tm06-design.md
     for the exact field list. Use their `--keep-init` / `--init-from` extension point to edit the saved init state.
     Do not patch their package source unless there is no other way, and if so keep it as a patch file in run/gpu/.
   - **Products:** drop integration hours 0-5, then re-stamp each kept file. The reference time becomes C, the
     forecast hour becomes h-6, and the accumulation windows shift by 6 h. Rename to the NOAA names and regenerate
     `.idx` with wgrib2. Match the CPU product's inventory, record order and accumulation windows. List every
     remaining record difference against the CPU file for the same hour.
   - **Upload** each product as soon as it is complete. The trial lost its f84 history to an upload that fired before
     the file was finished, so wait for their completion signal. Write DONE/FAILED markers like runner.sh does.
   - Use Spot when the quota allows. A Spot G-and-VT quota request for 16 vCPU is PENDING (5 Nov). On-demand is
     8 vCPU = one g7e.2xlarge. Fall back to on-demand if Spot is refused or the quota is 0, and say which ran.
2. `deploy/11-gpu-runner.sh`: launcher (instance types, subnets falling through like deploy/10, tags project=nam-recast,
   terminate on shutdown, a shutdown failsafe), using a `nam-recast-gpu` role. You may widen that role to read
   `cases/` and `products/` and to write `cases/*/gpu/` and `products-gpu/` in s3://nam-recast-617711905691. Nothing
   else.
3. `docs/gpu-path.md`: how it works, how to switch it on, timings, the record diff, open gaps, and how to merge it
   into run/launch.sh and the queue later (`ENGINE=gpu`). Write it as a proposal; do not do the merge.

## Acceptance (one case, 2026-11-01 00Z)
- One full GPU run through the new path. Products go to `s3://nam-recast-617711905691/products-gpu/nam.20261101/`
  (not `products/`, which holds the CPU run).
- Products open in wgrib2. Names, reference times, forecast hours and accumulation windows match the CPU product;
  show the inventory diff.
- Soil seeding works: at f00, the GPU product's 0-10 cm soil moisture is close to the archived NAM and far from the
  GFS, like the CPU product's (docs/figs/tm06/soil.md has the CPU numbers). Report the same table.
- Score the GPU products against the archived NAM with the compare.py method, beside the CPU FrankenNAM numbers
  (docs/figs/tm06/stats.csv) and the trial's (docs/figs/woof/stats.csv). This run differs from the trial in two
  ways: boundaries from the same cycle, and soil seeding.
- Timing per stage, boot to last product, and $ for the run.

## Limits
- **Budget $10** for all AWS spend in this task (Joe's GPU cap). Use short runs (6-12 h) while developing, then
  one full 90 h run. Track spend. Kill and terminate at the cap.
- **Terminate** every instance you start, and verify. Leave no volumes.
- **The six-case hindcast is running right now** on Graviton Spot runners from run/launch.sh with the S3 queue.
  Do NOT edit run/recast.sh, run/runner.sh, run/launch.sh, run/products.sh or anything under site/. Do NOT rebuild
  or replace anything in s3://.../runner/. Do not touch queue/, cases/*/tm06|recast*/ or products/. Do not start or
  stop CPU instances. The Graviton build box i-018d84ae6b2bd2a76 stays stopped.
- WOOF-NAM code runs only on EC2, never on the laptop. Don't vendor their code into our repo; pin and install it.
- Hands off every other project (paleo-planet-simulator / PPS especially).
- Do not request quotas, open issues or PRs, or contact anyone.
- **Git:** commit only your own paths (run/gpu/, deploy/11-gpu-runner.sh, docs/gpu-path.md, docs/figs/gpu/) with
  explicit `git add <paths>`, never -A. Other agents' untracked files are in the tree. The local identity is Joe's.
  End commit messages with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Final reply
Timing and $ for the full run, the inventory diff summary, the soil table, the fidelity numbers beside the CPU
column, total spend, confirmation that every instance is terminated, and the open gaps before ENGINE=gpu could go live.

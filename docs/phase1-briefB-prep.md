# Brief B-prep: hindcast case staging and the observation-based verification package

Runs in parallel with brief A (`docs/phase1-briefA-tm06.md`), which owns `run/`, `deploy/`, `build/`,
the arm build box, Spot runners and `cases/2026110100/`. **This brief touches none of those.** It
creates `verify/`, `docs/cases.md`, `docs/baseline-scorecard.md`, and stages inputs for the six
new cases under `s3://nam-recast-617711905691/cases/<C>/`. No EC2 instances at all; work on the
laptop with small, subset downloads from the public buckets (free egress).

Read first: `docs/phase1-plan.md` (sections "Next: Phase 1 step 2" B, "Hindcast cases"),
`docs/phase0-case-2026110100.md`, `run/compare.py` (read only, for the field conventions).

## Cases (product cycle C; GFS cycle P = C − 6 h)
| Case | C | Why |
|---|---|---|
| CAD ice storm, GA/Carolinas | 2026-01-23 12Z | the wedge case; Georgia's first ice-storm warning in a decade |
| "Snowcrete", DC | 2025-01-05 12Z | p-type (snow→sleet); NAM publicly credited |
| Gulf Coast snow | 2025-01-21 00Z | p-type, rare snow |
| PNW bomb cyclone + AR | 2024-11-19 12Z | Pacific NW wind/rain, orographic precip |
| Plains severe + blizzard | 2025-03-14 12Z | convection and a blizzard in one domain |
| Lake-effect / arctic outbreak | pick one from winter 2025-26 | justify from NWS write-ups; state the date |
| Phase 0 case | 2026-11-01 00Z | already staged by others; do not touch |

Before staging, confirm for each C that `noaa-nam-pds` has `nam.tCCz.awphysFF.tm00.grib2` for
f00-f84 (3-hourly) and `noaa-gfs-bdp-pds` has the P-cycle `pgrb2.0p25` f000-f090; if a case is
missing data, substitute a nearby cycle and say so in `docs/cases.md`.

## Staging (server-side S3 copies, us-east-1 → us-west-2, ~$0.02/GB; `pgrb2.0p25` only, no `pgrb2b`)
- `cases/<C>/gfs-tm06/gfs.tPPz.pgrb2.0p25.f{000..090 step 3}` (31 files, ~16 GB)
- `cases/<C>/nam-archive/nam.tCCz.awphysFF.tm00.grib2` for FF = 00..84 step 3, **plus**
  `nam.tPPz.awphys00.tm00.grib2` of the P cycle (the soil seed; its name does not clash)
- For the two reference-arm cases (CAD and Snowcrete): also `cases/<C>/gfs/gfs.tCCz.pgrb2.0p25.f{000..084 step 3}`
- Write `cases/<C>/MANIFEST.txt` (file, size). Total ≈ 130 GB, ≈ $3 of transfer; it stays until
  the hindcast is done.

## Verification package `verify/` (Python, tested on the archived NAM and the GFS, so it is ready
   before any FrankenNAM output exists)
Inputs are grid-218 `awphys`-style GRIB2 files (ours will be identical in form) and GFS 0.25°.
Use `.idx` byte-range reads (Herbie or your own) so laptop downloads stay small; never pull whole
GFS files to the laptop.
- `verify/obs_asos.py`: hourly ASOS (2 m T, Td, 10 m wind, present weather) from the Iowa
  Environmental Mesonet archive for CONUS stations, for each case window (C to C+84 h).
- `verify/obs_mrms.py`: MRMS `MultiSensor_QPE_24H_Pass2` from `noaa-mrms-pds` at the 24 h windows
  ending C+24/48/72/84 (check availability per date; fall back to `GaugeCorr_QPE_24H` and say so),
  aggregated to grid 218 box means (or to 0.25°, state which, use the same for all models).
- `verify/obs_snotel.py`: SNOTEL daily precipitation for the PNW and Plains cases; the wsis repo
  (`~/projects/whereshouldiski`) has fetchers you may read and copy from, **read-only, do not
  modify that repo**.
- `verify/score.py`: station verification (nearest grid point and bilinear, report which) for
  T2m/Td2m/wind: bias, MAE, RMSE by lead (every 3 h to 84), CONUS and by region (NE, SE, Midwest,
  Plains, West). Precipitation: ETS, frequency bias, and MAE at 2.5/10/25 mm per 24 h vs MRMS.
  P-type: categorical agreement of CSNOW/CICEP/CFRZR/CRAIN with ASOS present weather at stations
  reporting precipitation, for the CAD, Snowcrete and Gulf cases. Output CSV + Markdown tables and
  a few figures (bias-by-lead curves, ETS bars, p-type confusion tables).
- `verify/run_baseline.py`: runs the whole thing for the archived NAM and the GFS on all seven
  cases → `docs/baseline-scorecard.md`: "what the operational NAM and the GFS scored against
  observations on these cases". This is the frame FrankenNAM drops into later, and it is useful
  on its own for the site.
- Keep the code tolerant of our files appearing later under `cases/<C>/products/nam.YYYYMMDD/`
  with the same names: a `--model` switch with a path template, nothing hard-coded to the archive.

## Acceptance
- Six cases staged with manifests; `docs/cases.md` lists C, P, the event, the data checks and
  anything substituted.
- `python -m verify.run_baseline --case 2026110100 --models nam,gfs` runs end to end on the laptop
  from a clean checkout (document the venv/requirements) and produces the tables; then all seven.
- `docs/baseline-scorecard.md` written with the tables, figures under `docs/figs/baseline/`, and a
  short honest reading (where the old NAM beat the GFS against obs and where it did not).

## Rules
- Budget: **$5 AWS** (transfer + requests). No EC2. Report spend.
- Do not touch `run/`, `deploy/`, `build/`, `cases/2026110100/`, `products/`, `queue/`, any instance,
  the arm or x86 boxes, or other projects (wsis read-only for the SNOTEL fetcher; PPS/enso never).
- Downloaded data goes under `~/data/nam-recast-verify/` (not in the repo). No user-agent spoofing;
  respect the IEM and MRMS access conventions (IEM asks for modest request rates).
- Commit small with named paths (no `git add -A`), author is Joe (configured), end commit messages
  with the Co-Authored-By line set for this session. Report in plain text with numbers and commits.

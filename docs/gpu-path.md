# GPU path: WOOF-NAM behind the FrankenNAM product (proposal, 5 Nov 2026)

Status: built and run once (2026-11-01 00Z, `RUNTAG=accept`); NOT merged into `run/launch.sh` or the queue, NOT used for
the public product. The CPU path (NOAA Fortran on Graviton) stays the default. Numbers are filled in from that one run.

## What it is

An optional engine: WOOF-NAM (recastsystems/woof-nam, Apache-2.0, pinned to commit `49f2742` = 0.1.3, the newest
at build time; `--boco-age` is available there, so no newer commit was needed) runs the tm06 forecast on one AWS GPU
and `run/gpu/` turns its output into **the same product as the CPU path**: `nam.tCCz.awphysFF.tm00.grib2` + `.idx`,
f00-f84 every 3 h, grid 218, reference time C. Third-party code runs only on the instance, never on the laptop.

| file | role |
|---|---|
| `deploy/11-gpu-runner.sh` | launcher: g7e.2xlarge, Spot if the G Spot quota allows else on-demand (it prints which), zones fall through, tags `project=nam-recast`, Name `nam-recast-gpu-run` (not `nam-recast-runner`, which the CPU relay counts), terminate-on-shutdown + `shutdown -h +MAXMIN` failsafe, `terminate` and `status` subcommands, widens role `nam-recast-gpu` (read `cases/`, `products/`; write `cases/*/gpu/`, `products-gpu/`) |
| `run/gpu/gpu_runner.sh` | on-box driver (the analogue of `run/runner.sh`) |
| `run/gpu/seed_init.py` | Noah soil seed edited into the saved init |
| `run/gpu/restamp.py`, `master-order.txt`, `templates/` | integration clock -> cycle clock, NOAA names, `.idx` |
| `run/gpu/inventory_diff.py`, `score_gpu.py` | inventory diff against the CPU file; fidelity + soil scoring (laptop) |

## Pipeline (all stages measured in the acceptance run, `docs/figs/gpu/timeline.txt`)

1. **Install** at boot, no AMI (DLAMI Base OSS Nvidia, Ubuntu 24.04): clone + `pip install ./src eccodes`, 30 s GMTED2010
   terrain (`gpuwm fetch-geog`: `init-gwd-orog` refuses to run without it), micromamba `wgrib2` 3.8 in the background.
2. **Fetch** GFS 0.25 deg from `noaa-gfs-bdp-pds`: f000 of cycle S = C-6 plus boundaries f000..f096 **of the same cycle**
   (`--boco-age 0`; `NAMGPU_BOCO_AGE_H=0` for the init). Verified in `init.log`: `boco.0000 (+0 h -> +3 h)` from
   `gfs.t18z.f000`. Static fields build themselves from an archived NAM analysis (12 s).
3. **Init without TDFI**: `python -m namgpu.init.slab_init save` (86 s, 13 GB state on disk).
4. **Soil seed** (2 s) edits the saved init (`seed_init.py`, their documented `--init-from` extension point; no patch to
   their source). Same list as the CPU path (docs/tm06-design.md section 2): STC, SMC, SH2O (from SOILL, capped at SMC),
   SNO (instantaneous WEASD) and land skin temperature, on model land points the seed covers (masked bilinear on the seed's
   land mask, spherical Lambert 218), GFS values elsewhere (SST untouched). Derived: SI = 5 x SNO, SNOWC = 0.98 where SNO > 0.
   Not seeded, as on the CPU path: canopy water, a snow depth of its own, sea ice, SST, TG. Seed = archived NAM awphys00
   at C-6 (hindcast; `SEED_S3` overrides), live = our previous cycle's `awphys06`.
5. **Run** `woof-nam run --init-from` (TDFI 71 s, then 12960 steps), `--no-maps --no-columns`, with a
   `woof-nam products --follow --hours 6,9,...,90` process writing the 29 needed hours alongside.
6. **Ship**: for each hour, when its raw file's `.idx` exists (their completion signal: the `.idx` lands whole and last),
   `restamp.py` re-stamps it and the product + `.idx` go to S3 at once. DONE/FAILED markers in `cases/C/gpu/<RUNTAG>/`.

### Re-stamping (`restamp.py`)
Reference time C; forecast time minus 6 h in every record (instantaneous, max/min windows); the 1 h max/min records dropped
at f00; the accumulation records rebuilt on the C clock as `run/products.sh` does (12 h bucket since `12*floor((FF-1)/12)` =
sum of the 3 h buckets of the earlier files, 3 h pair when the bucket is longer than 3 h; f00 = the CPU file's zero
"0-0 day acc" records, `templates/zero-acc-f00.grib2`); record order = the CPU product's (`master-order.txt`); `.idx` by wgrib2.

## Acceptance run: 2026-11-01 00Z (C), start 2026-10-31 18Z

On-demand g7e.2xlarge (RTX PRO 6000 Blackwell 96 GB), us-west-2b. **Spot was not used: the G Spot quota reads 0** (the
16 vCPU request is still pending at build time; the launcher takes Spot automatically once it reads >= 8).

| Stage | Time |
|---|---|
| boot to runner start | ~50 s (launch 23:23:00Z, runner 23:24:03Z) |
| install (pip + geog) | 60 s |
| fetch 33 GFS files + static | 33 s |
| init (no TDFI) + save | 86 s |
| seed | 2 s |
| TDFI | 71 s |
| integration 12960 steps | 2990 s = 49.8 min total run incl. TDFI (222.8 ms/step, 30.2 s per forecast hour; faster than the trial's 36.5 s because no maps/columns and the init is cached) |
| last product shipped | 29 s after the model ended (products ship ~2 model hours behind real time) |
| **boot to last product** | **54 min** (23:23:00 to 00:17:31Z) |

Cost: about 1.2 instance-hours across the dev runs and this one. The full run alone: 0.92 h x $3.363 = **$3.1 on-demand**
(plus ~$0.1 EBS for 600 GB gp3). At the 2b Spot price seen on 5 Nov (~$2.1/h) it would be about $2.

### Record differences against the CPU file (all 29 hours, `inventory_diff.py`)
For every hour f00..f84: **446 / 444 / 439 lines identical (name, level, time text) and in the same order as the CPU
file**; the only differences are records WOOF-NAM does not write:
`WEASD` 12 h snowfall accumulation (all hours but f00, where the zero template is used), `CSNOW`, `CRAIN`, `CFRZR`,
`CICEP` (precipitation-type flags), `BMIXL`, `LTNG`, `VIS` at cloud top (7 records at f00, 8 later: 439/444/446 against
446/452/454). Other differences that the inventory does not show: process id 254 (WOOF) instead of 84 in section 4 (kept
as provenance); 3 h precipitation values quantised like NOAA's (1/16 mm; same as the CPU file).

### Soil seeding (f00; `docs/figs/gpu/soil.md`, CPU numbers from `docs/figs/tm06/soil.md`)
| Field | GPU vs NAM | GPU vs seed | GPU vs GFS | CPU tm06 vs NAM | CPU tm06 vs GFS |
|---|---|---|---|---|---|
| SOILW 0-10 cm (m3/m3) | 0.012 / -0.001 | 0.012 / -0.001 | 0.088 / +0.051 | 0.012 / -0.002 | 0.087 / +0.050 |
| TSOIL 0-10 cm (K) | 0.92 / -0.27 | 2.86 / +1.95 | 1.98 / +0.31 | 0.90 / +0.11 | 2.11 / +0.68 |
| SOILW 40-100 cm (m3/m3) | 0.011 / +0.000 | 0.011 / +0.000 | 0.091 / +0.051 | 0.010 / +0.000 | 0.091 / +0.051 |

Close to the archived NAM, far from the GFS, like the CPU product.

### Fidelity to the archived NAM (RMSE / bias, CONUS land, 0.25 deg; `docs/figs/gpu/stats.md`, full table incl. U/V)
| Field | Lead | GPU path | CPU FrankenNAM tm06 | WOOF trial (6 h older boundaries, GFS soil) | GFS |
|---|---|---|---|---|---|
| MSLP (hPa) | f00 | 1.01 / -0.65 | 0.99 / -0.67 | 1.14 / -0.79 | 0.86 / -0.56 |
| Z500 (dam) | f00 | 0.61 / -0.49 | 0.49 / -0.36 | 0.62 / -0.51 | 0.52 / -0.38 |
| T2m (K) | f00 | 1.38 / +0.58 | 1.49 / +0.88 | 1.59 / +0.87 | 1.36 / -0.31 |
| 10 m speed (m/s) | f00 | 1.02 / +0.60 | 0.96 / +0.55 | 1.05 / +0.63 | 1.22 / +0.58 |
| MSLP | f24 | 0.93 / +0.31 | 0.97 / +0.17 | 0.95 / +0.09 | 1.72 / -0.89 |
| Z500 | f24 | 0.56 / -0.09 | 0.53 / -0.16 | 0.54 / -0.05 | 1.47 / -0.76 |
| T2m | f24 | 1.31 / -0.14 | 1.44 / +0.12 | 1.48 / +0.32 | 1.88 / -0.11 |
| 10 m speed | f24 | 0.91 / -0.00 | 0.93 / +0.02 | 0.96 / +0.08 | 1.77 / +0.31 |
| MSLP | f48 | 1.00 / +0.43 | 1.05 / +0.41 | 1.00 / +0.12 | 1.73 / -0.51 |
| Z500 | f48 | 1.04 / -0.11 | 0.87 / -0.15 | 1.00 / -0.11 | 1.62 / -0.12 |
| T2m | f48 | 1.26 / -0.18 | 1.26 / +0.02 | 1.40 / +0.29 | 1.99 / +0.15 |
| 10 m speed | f48 | 0.86 / -0.03 | 0.80 / +0.02 | 0.87 / -0.02 | 1.80 / +0.50 |
| MSLP | f84 | 2.08 / +0.82 | 3.45 / +1.15 | 2.44 / +0.65 | 3.60 / -1.72 |
| Z500 | f84 | 1.99 / +0.15 | 3.82 / -0.18 | 2.42 / +0.21 | 3.29 / +0.01 |
| T2m | f84 | 1.98 / -0.18 | 2.42 / -0.41 | 2.08 / +0.01 | 3.52 / +1.50 |
| 10 m speed | f84 | 0.94 / -0.07 | 1.16 / -0.07 | 1.00 / -0.05 | 1.35 / -0.29 |
| precip 0-24 (mm) | f24 | 6.56 / -0.30 | 6.68 / -0.35 | 6.66 / -0.35 | 6.61 / -0.59 |
| precip 24-48 | f48 | 5.10 / -0.15 | 4.90 / -0.23 | 5.96 / -0.13 | 6.77 / +0.09 |
| precip 60-84 | f84 | 8.79 / -0.28 | 9.12 / -0.55 | n/a (f84 history truncated) | 9.72 / -0.25 |

One case. The GPU path is about as close to the NAM as the CPU path through f48 (slightly looser on Z500 and the wind
components at f48, tighter on T2m and the 2 m bias at f24) and much closer at f84 (MSLP 2.1 vs 3.5 hPa, Z500 2.0 vs 3.8 dam).
Same-cycle boundaries and the soil seed (the two changes from the trial) lowered the f24 T2m bias from +0.32 to -0.14 K and
the f48 MSLP bias from +0.12 to +0.43 hPa (worse); f00-f48 RMSE is within noise of the trial. Not a six-case result:
the fidelity gate (docs/phase1-plan.md) is not met by one case, so nothing from this path goes into the public product.

## How to switch it on (today, by hand)
```
deploy/11-gpu-runner.sh 2026110100 RUNTAG=accept S3PROD=s3://nam-recast-617711905691/products-gpu/nam.20261101
deploy/11-gpu-runner.sh status | terminate
```
Short test: `HOURS=12 RUNTAG=dev1 HOLD_ON_FAIL=1 MAXMIN=60` (3 products, ~13 min, ~$0.8). Without `S3PROD` products go under
`cases/C/gpu/<RUNTAG>/products`. Use a fresh `RUNTAG` per run (the role can overwrite but the stale-marker removal at start did not
take effect once: use new tags). Score on the laptop: `run/gpu/score_gpu.py <case dir> <out>`.

## Proposal: ENGINE=gpu in run/launch.sh and the queue (not done)
- A queue line gets an `ENGINE=gpu` token (`CYCLE tm06 arm64 ENGINE=gpu`); `launch.sh` hands such a line to the body of
  `deploy/11-gpu-runner.sh` (factor its launch function out) and the on-box script writes `cases/C/tm06/DONE` + products to
  `products/` or `products-gpu/` according to a flag, so `site/` and the dashboards see one marker layout.
- Chaining: `gpu_runner.sh` ends with `launch.sh --next` as `runner.sh` does. The on-demand G quota is 8 vCPU = **one GPU box at
  a time**; the GPU Name tag differs from `nam-recast-runner`, so the CPU relay's runner count is unaffected and CPU and
  GPU jobs can overlap. Add a GPU-relay (t4g.nano) like the CPU one for the one-at-a-time case.
- Live seed: previous cycle's `products/nam.YYYYMMDD/nam.tPPz.awphys06` (set `SEED_S3`); the first GPU cycle needs one CPU cycle first.
- Live clock: GFS C-6 f090 lands about C-2:03; boot to last product is 54 min, so f84 would be ready about C-1:05 (the CPU
  path's f84 is at about C+3:05).

## Open gaps before ENGINE=gpu could go live
1. **Six-case fidelity check** (one case only so far) and the decision rule in docs/phase1-plan.md.
2. **Missing records:** WEASD 12 h snowfall (important for a ski product), CSNOW/CRAIN/CFRZR/CICEP, BMIXL, LTNG, cloud-top VIS.
   WOOF-NAM's history carries no snowfall accumulation or precipitation-type fields (the device keeps `ACSNOW` but resets it every 3 h and
   writes nothing); needs an upstream change, or a post step from the T profile and precipitation rate (not built).
3. **Spot:** quota 0 today (request pending); on-demand $3.363/h. Spot GPU capacity is thin; a reclaim loses the run (restarts
   exist in WOOF-NAM, `--restart-every`, not wired in). `deploy/11` takes Spot automatically when the quota reads >= 8.
4. **Third-party stability:** v0.1.x moved three versions in a day; the pin and the downloaded `rw_rrfs_upp` bridge (pinned by SHA in their
   package) are the risk; GFS/NAM-archive fetches use their network paths, not our S3 copies (a GFS mirror in S3 like the CPU path's would remove that).
5. **Seeding approximations:** SI = 5 x SNO (no snow depth analysis); CPU path leaves the same fields unseeded; seam at the grid-218 edge as on the CPU path.
6. **Not bit-reproducible** (float32, atomics in their init): a rerun differs; no restart/resume wired.
7. Process id 254 in section 4, and 600 GB / 13 GB init scratch per run (114 GB history) could be trimmed with `--history-fields`.
8. Startup is not automated by cron/EventBridge; no alarms yet like the CPU jobs.

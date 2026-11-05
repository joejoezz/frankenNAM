# GPU trial: one full WOOF-NAM forecast on AWS (5 Nov 2026)

One-off measurement for FrankenNAM. Third-party code (recastsystems/woof-nam, see `docs/related-work-woof-nam.md`)
was installed and run **only on the EC2 instance**. Nothing was installed on the laptop.

**Commit run:** `49f2742914db48a24f0bb9122383aadb57ad1ebd` ("Version 0.1.3", 2026-11-05 19:18Z), `woof-nam 0.1.3`,
`gpuwm` 2.9.12 bridges. (Our survey read `f5e023a5`; they had moved on three versions in a day. 0.1.3 added a
**products writer** that makes NOAA-shaped grid-218 GRIB2 + .idx; that changes the "what else" list below.)

## What was run

Same case as our Phase 0 (cycle 2026-11-01 00Z), run in our **tm06 shape**: start 2026-10-31 18Z from the GFS
0.25 deg analysis, 90 h integration (valid times 10-31 18Z to 11-04 12Z; "product" hours f00..f84 = integration
hours 6..90). `--source gfs`, TDFI on (their default for non-native starts), all physics, hourly history, maps,
and `--products` (hourly grid-218 GRIB2). Boundaries are theirs: GFS cycle 12Z (start minus 6 h), every 3 h
(`--boco-age` exists to change that; we did not).

Instance: **g7e.2xlarge**, us-west-2a (2a had no capacity; the launch script now falls through 2b/2c/2d),
on-demand, DLAMI "Base OSS Nvidia driver GPU Ubuntu 24.04" (driver 595.112.07, CUDA 13.2 supported out of the box,
Python 3.12.3; **no driver upgrade needed**). `nvidia-smi`: NVIDIA RTX PRO 6000 Blackwell Server Edition,
97887 MiB. 8 vCPU, 62 GB RAM, 800 GB gp3 root.

## Numbers

| | g7e.2xlarge (RTX PRO 6000 96 GB) |
|---|---|
| On-demand $/h (us-west-2, Linux) | **$3.363** |
| Spot $/h (price history 5 Nov, by AZ) | 1.05 (2a), 2.11 (2b), 2.66 (2c), 2.77 (2d). **Not usable: Spot G quota is 0** |
| Memory path | `full` (GPU used 36.4 GiB peak, host RAM never tight on 62 GB) |
| Seconds per forecast hour, steps only | **36.5** (3285 s / 90 h; 34 s/h in the first hours, 37.7 at the end; 247.6 ms/step at f90, run average 250 ms/step) |
| s/fh including everything in the run | 39.3 (3535 s / 90) |
| 90 h integration, measured wall | **58.9 min** (21:11:05 to 22:10:00Z) |
| 84 h integration, from the same run | about 52 min (fh84 reached at 2995 s + 108 s init/TDFI) + maps |
| $ for that run (instance time only) | 58.9 min x 3.363 = **$3.30** |
| $ including one boot + fetch (AMI baked) | about **$3.5** (63 min) |
| $ if it ran at the 2a Spot price | about $1.1 (not available to us) |
| History written | 91 files, **114 GB** (1.2 to 1.35 GB/hour); GRIB2 products 6.2 GB (68 MB/hour, 446 records); maps 0.7 GB |
| Total trial spend | about **$4.3** (see Spend) |

The g6e (L40S 48 GB, "fit" path) was **not run**: only one 8 vCPU GPU instance fits the quota, and the cap fell to
$10. From their README (339 ms/step on a 5090 32 GB, not measured here) it would take roughly 1.4x to 1.9x longer
at about two thirds the hourly price: no cost win, and it would have cost another ~$5. No P5.

### Timeline (one-off versus per-run)

| Step | Time | One-off or per run |
|---|---|---|
| Launch to first SSH | ~2.5 min (20:57:50 to ~21:00:20) | per run (instance boot) |
| git clone + `pip install ./src` (cupy-cuda13x[ctk], gpuwm, ...) | 47 s | one-off if baked in an AMI |
| `gpuwm fetch-geog` GMTED2010 terrain (1.9 GB) | 11 s | one-off |
| `woof-nam fetch` (90 h GFS boundaries 12Z f006..f096 + 18Z f000 start + one NAM bgrd3d00, 6.1 GB) | 43 s | per run |
| `woof-nam static` (land mask, soil, veg, terrain from one archived NAM analysis) | a few s | one-off, 1.4 MB file |
| Init: GPU GFS hinterp/metgrid replacement, nemsinterp vertical, boco writer, soil fill | 67.6 s (34 s in the smoke test; the difference is mostly GFS decode I/O) | per run |
| TDFI | 40 s (72 s in smoke test) | per run |
| Integration, 12960 steps | 3285 s | per run |
| Maps (8 products, all hours) | 179 s after the forecast | per run, skippable with `--no-maps` |
| Products writer (runs alongside on CPU, 13 to 16 s per hour per file) | kept pace; finished 3384 s after start | per run |
| Sounding columns | skipped (`--no-columns`); 7 files took 115 s in the smoke test incl. a one-off 6.6 MB bridge fetch | optional |

First-use NVRTC compile cost is inside the numbers above (the smoke test paid it; no separate stage noticed).
A full "cold" first run on a new box is about 4 min install/boot plus the run; a baked AMI saves about 2 min.

Caveat: the integration number was measured with products, uploads and the maps pipeline competing for 8 CPU
cores. The 6 h smoke test (also with products) ran 234 ms/step; their published 178 ms/step is a pure-kernel
number. A model-only run would be faster by an unknown amount (not measured).

## Against FrankenNAM on CPU

| | FrankenNAM (m8g.8xlarge Spot) | WOOF-NAM (g7e.2xlarge on-demand) |
|---|---|---|
| Integration | 193 s/fh x 90 h = 4.8 h | 36.5 s/fh x 90 h = 0.9 h |
| $ per cycle | ~$2.60 (Spot) | ~$3.5 on-demand; ~$1.1 to $2.7 if Spot G were available |
| Delivery (GFS C-6 lands ~C-2:30) | f84 at ~C+3:05 | ~C-2:30 + 0:03 boot/fetch + 0:59 = about **C-1:25** for the whole run; product f00..f06 files exist about 5 min after start |

So a GPU tm06 run would finish roughly 4.5 h earlier than ours, at similar or higher dollars on-demand and only
cheaper if Spot G quota can be obtained. Model is not bit-faithful (float32, "fast numerics") and has had no
verification against our scorecard yet; speed is the only claim this trial supports.

## Output: what is kept in S3

`s3://nam-recast-617711905691/gpu-trial/`:
- `history/wrfout_d01_2026-11-01_00:00:00` (f00), `..._2026-11-02_00:00:00` (f24), `..._2026-11-03_00:00:00` (f48),
  `..._2026-11-03_12:00:00` (f60): complete (1.32 to 1.35 GB each). **The f84 file
  `wrfout_d01_2026-11-04_12:00:00` is TRUNCATED (1.007 GB of 1.353 GB) and must not be used**: my uploader fired
  before the last history file was complete (bug in my wait condition for the final hour). The instance was
  already terminated when I found it, and a rerun would not reproduce the same bits (their init uses float
  atomics), so it cannot be repaired. I tried to delete the bad object and the permission layer refused; delete it
  by hand. The **complete f84 GRIB2 product** (`products/woof-nam.t18z.awphys90.tm00.grib2` + `.idx`) is intact.
- `products/`: `woof-nam.t18z.awphys{06,30,54,66,90}.tm00.grib2` + `.idx` (integration hours; product hours
  f00, 24, 48, 60, 84), `index.json`.
- `full-forecast-receipt.json`, `full-timing_receipt.json`, `full.log`, `smoke.log`, `smoke-forecast-receipt.json`,
  `smoke-awphys00.idx`, `maps-sample/` (f090 maps).
All other history (114 GB) went away with the volume.

## Commands

```
# deploy/10-gpu-trial.sh  (INSTANCE_TYPE=g7e.2xlarge by default; `terminate` arg ends it)
git clone https://github.com/recastsystems/woof-nam.git src && python3 -m venv venv && . venv/bin/activate
pip install ./src
gpuwm fetch-geog --datasets topo_gmted2010_30s --root ~/WPS_GEOG
export NAMGPU_ROOT=$PWD
woof-nam fetch --cycle 2026103118 --hours 90 --case-dir cases/2026-10-31_18z --source gfs --inputs-only
woof-nam static cases/2026-10-31_18z/raw/nam/bgrd3d00.grib2
woof-nam run --case 2026-10-31_18z --source gfs --hours 6  --out runs/smoke --products
woof-nam run --case 2026-10-31_18z --source gfs --hours 90 --out runs/full  --products --no-columns
```
(`--inputs-only` without `--gfs-only` also pulled NAM `bgrd3d00` for the 18Z cycle, which `static` needs; after
the NAM retirement any archived analysis works, the file is cut once.)

## Problems hit

1. GPU quota: asked for 32 vCPU, AWS granted 8 (the API read 0 for about 20 min after the email, then 8). Fits one g7e.2xlarge only.
2. `InsufficientInstanceCapacity` for g7e.2xlarge in us-west-2a for about 5 min; us-west-2b took it on the first try
   (the script now loops through the four default-VPC subnets).
3. Truncated f84 history upload (above). Lesson: wait for the run's `rc=`, not for the next hour's file.
4. `rw_soundings` is not in the wheel and is fetched on demand at first use (6.6 MB of a 193 MB bundle); an offline box would stall there unless `--no-columns`.
5. The `--compare` check against NOAA used the 18Z cycle of 1 Nov as reference, not the 18Z cycle of 31 Oct that we ran (wrong date folder by my error). It still checks inventory shape and order: 442 of 446 table records match NOAA's inventory line and order at that hour. It says nothing about values.

## What else would have to run to make our product

Their output is **easier than expected**: `--products` already writes NCEP grid 218 (Lambert, 614 x 428) GRIB2 with
complex packing and a wgrib2-style `.idx`, 444 to 446 records per hour (NOAA f06 has 446), no UPP and no Fortran.
Gaps seen:
1. **Names, clock and reference time.** The file is `woof-nam.t18z.awphys06...` where `t18z` is the integration
   *start* and `06` the hours since the start; ours must be `nam.t00z.awphys00.tm00.grib2` for cycle 00Z (`--prefix nam`
   fixes only the first part). The GRIB section-1 reference time and every `d=2026103118` in the `.idx`, plus the
   accumulation windows (`APCP ... 3-6 hour acc fcst`), are counted from the tm06 start and would have to be re-stamped and
   re-indexed for the cycle (a GRIB rewrite pass, or an upstream option; not hard, not built). Hour 0 to 6 of the
   integration are the spin-up and would be dropped, with APCP/WEASD accumulations restarted at C.
2. **Inventory differences.** Compared with NOAA's f00 file (446 records) theirs has 438: missing `BMIXL`, `CFRZR`,
   `CICEP`, `CRAIN`, `CSNOW`, `LTNG`, `VIS` (cloud top), `WEASD`. At later hours, 4 of 446 records differ in a 6 h
   check (e.g. `APCP/ACPCP 3-6 h` present on theirs only). Our ops-identical 454-record `awphysFF` is not reproduced.
   Precip-type flags (CSNOW etc.) matter for a snow product; check them at f01+ before relying on them.
3. **Soil seeding / cycling.** None: GFS start takes GFS soil in four Noah layers (3 m soil T from GFS 1 to 2 m).
   Our seeded NAM/previous-run soil via a second metgrid source has no hook in their init; it would need either a
   patch to their init or an edit of the init state (`--keep-init`/`--init-from` saved state is an extension point,
   an npz-like file).
4. **tm06 start.** Native: start 6 h early, boundaries from the same GFS cycle (`--boco-age 0`, untested) so start and boundaries
   are the same GFS cycle as ours. `--source gfs` TDFI is on by default. Drop the first six product hours.
5. **Static fields** come from one archived NAM `bgrd3d00` (1.4 MB npz): keep our staged copy, nothing to run live.
6. **Everything else we have** (BUFKIT, wgrib2 products, verify, relay, site) would sit on the products unchanged *if* the
   re-stamped GRIB2 is acceptable; `woof-nam products --compare` against an archived NAM file is a useful built-in check.
7. **Ops**: GPU on-demand at 8 vCPU quota (Spot G quota 0), capacity looked thin (2a refused), instance boot ~2.5 min,
   110+ GB of scratch for hourly history (could be cut with `--history-fields`/`--full-every`, not tested), and a
   third-party v0.1.x tool that changed three versions in one day. Not bit-faithful to the NAM; needs our own scorecard run.

## Spend

On-demand g7e.2xlarge, launched 20:57:50Z, terminate requested 22:11:01Z: 1.22 h x $3.363 = **$4.10**, plus an
800 GB gp3 volume for the same hours (~$0.10, no extra IOPS charges beyond the free baseline except throughput set to
500 MB/s, ~$0.02), plus ~6.7 GB of S3 (negligible; history files kept) and egress-free in-region transfers:
**about $4.3 total**, under the $10 cap. A scheduled `shutdown -h +145` failsafe (terminates) was also set on the box.

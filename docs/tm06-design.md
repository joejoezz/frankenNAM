# FrankenNAM tm06 product configuration: design as built (Brief A, 4-5 Nov 2026)

Status: see "Acceptance run" at the end for what was measured. Everything here runs on arm64
(c8g.8xlarge Spot, restarts off); scripts: `run/recast.sh` (MODE=tm06), `run/products.sh`,
`run/runner.sh`, `run/launch.sh`, `deploy/07-runner-policy.sh`, `run/compare.py`.

## 1. The cycle

Product cycle C (00Z or 12Z) is a 90 h NMMB integration that starts at START = C−6 h from the
GFS cycle START: `gfs.tSSz.pgrb2.0p25.f000` is the initial condition, `f003…f090` the 3-hourly
boundaries (31 files, 17 GB, server-side copied from `noaa-gfs-bdp-pds` into
`cases/<C>/gfs-tm06/`; the NOAA buckets allow GetObject but not GetObjectTagging, so the copy
runs with `--copy-props none`). Integration hour 6 is product f00, hour 90 is f84. TDFI at the
start, 3-hourly history, `nhrs_prec 3` (3 h precipitation buckets so the product's 12 h
buckets can be rebuilt on the C clock), the other buckets 6 h as ops (a 6 h bucket on the START
clock is also aligned on the C clock), no restart files (`NO_RESTART=1`), history kept on the
node, UPP on integration hours 6..90 with the forecast control file for every hour (the `_00h`
analysis control is only right for a true analysis). `MODE=anl` keeps the Phase 0 analysis
start (84 h from GFS cycle C, 12 h buckets) for the reference arm.

Honesty line (products README and every public page): *"Initialized from the (C−6)Z GFS
analysis with a 6 h NAM spin-up. No observations after (C−6)Z."*

The brief wrote the acceptance case as "P = GFS 2025-10-31 18Z, C = 2026-11-01 00Z"; the case
is the Phase 0 cycle 2026-11-01 00Z (the archived awphys files carry `d=2026110100`), so START
is 2026-10-31 18Z and the seed is `nam.20261031/nam.t18z.awphys00.tm00.grib2`. The 2025 files
I staged first were deleted again.

## 2. Soil seeding through metgrid

### What is seeded and from where
A second ungrib source, prefix `SEED`, Vtable `run/parm/Vtable.SEED` (rows copied column-exact
from `parm/nam_Vtable.NAM`: the Vtable parser is fixed-format and a one-character change in a
description gives "Read error 3 in PARSE_TABLE"): the four Noah layers SM/ST 0-10/10-40/40-100/
100-200 cm, LANDSEA (needed as the interpolation mask of that source), SKINTEMP, SNOW (water
equivalent) and CANWAT, read from a grid-218 NAM-format GRIB2 file valid at START: in hindcasts
the archived `nam.tSSz.awphys00.tm00.grib2`, live our own `awphys06` of the previous cycle (same
format, same Vtable). `seed_prep` in `recast.sh` extracts those records with wgrib2 (only the
instantaneous WEASD: the file also carries an accumulated-snowfall WEASD record of the same
discipline/parameter/level, which ungrib would otherwise take) and **blanks TMP:surface over
water** (`-rpn rcl_1:mask` with the LAND field) so that the skin temperature is seeded over land
only and the GFS SST survives everywhere. wgrib2 writes those undefined points through
the complex-packing missing-value management (not a bitmap), so g2/ungrib expand them as
9.999e20, and a `from_input=SEED` METGRID.TBL entry for SKINTEMP (`run/parm/METGRID.TBL.seed`,
appended to `nam_METGRID.TBL.NMM_gfsgrib2`) declares `missing_value=9.999e+20` (the value the
NAM's own soil entries use) so those points are missing for the interpolator and the GFS value
underneath survives.

### metgrid precedence finding (NPS `metgrid/src/process_domain_module.F90`)
`fg_name` sources are processed in list order. For every field of a later source, metgrid
fetches the field already in storage (with its `valid_mask` of points set so far), interpolates
the new source point by point and **overwrites every model point where the new source yields a
valid value**; where it yields missing (outside the source grid, or masked away, or equal to the
entry's `missing_value`) and the point was valid before, the earlier value stays; where neither,
`fill_missing` is used. The WPS guard "if this grid point was already given a value from
higher-priority source data, there is nothing to do" is **commented out** in NPS
(`accum_continuous`, the `processed_pts` tests) and absent from the per-point loop of
`interp_met_field`, so NPS metgrid is **last source wins, point-wise**, the reverse of WPS's
documented first-source priority. Hence `fg_name = 'FILE','SEED'`: the GFS everywhere, the seed
on top wherever grid 218 has land. Masked interpolation of the seed's soil fields uses the seed's
own LANDSEA (`get_interp_masks` stores `<field>.mask` per source); model water points get the
table's `fill_missing` from both sources alike. The seam at the grid-218 boundary (NAM soil
inside, GFS soil outside, through Canada, Mexico and the oceans) is a hard edge; it is where the
NAM's own cycled soil also ended.

### What cannot be seeded as written (honest list)
- **Canopy water:** `nemsinterp/src/ingest_metgrid.F90` sets `CANWAT = 0` unconditionally
  ("setting CANWAT to ZERO"), for the GFS as for the seed. It travels through metgrid but the
  model starts with zero canopy water. The operational cold start did the same.
- **Snow depth:** nemsinterp reads `SNOW` (water equivalent) only; there is no SNOWH input. The
  model derives depth from the water equivalent. Only the water equivalent is seeded.
- **Sea ice and SST** stay GFS by design (not in the seed Vtable; SST protected by the blanking).
- The seed's LANDSEA also overwrites the GFS LANDSEA inside grid 218; nemsinterp uses geogrid's
  LANDMASK, not that field, so it is inert.

Acceptance of the seeding is the soil table in `run/compare.py` (`soil.md`): f00 soil moisture
and temperature of the tm06 product against the seed, the archived NAM at C, the GFS at C and
the anl run (GFS soil). Numbers in section 7.

## 3. Products identical in form to the operational awphys (grid 218)

### wgrib2 and the rotated B grid
The arm box already had a wgrib2 3.1.3 with IPOLATES, built with `USE_IPOLATES=3` (ip2lib_d).
`-new_grid` from UPP's native output (GDT 32769, the NMMB rotated lat-lon B grid) dies in
IPOLATES with "unrecognized input grid": wgrib2 translates 32769 only on the GRIB1-iplib path
(`mk_kgds.c`, kgds(1)=205 "Rotated Lat/Lon Non-E Stagger"), `USE_IPOLATES=3` hands the template
through to ip2lib, which does not know it. The honest fix is the build the makefile documents
for exactly this case: **`USE_IPOLATES=1`** (bundled `iplib.v3.0.0`, `gdswzd05` for kgds 205), so
the Phase 0 "silent -new_grid" was a missing *grid*, not a missing library. Rebuilt in
`/opt/nam/work/wgrib2/grib2-ip1` (`make USE_IPOLATES=1 USE_SPECTRAL=0 USE_NETCDF3=0
USE_NETCDF4=0 USE_PROJ4=0 USE_OPENMP=1 FC=gfortran CC=gcc`; proj-4.8.0's config.guess predates
aarch64, hence no PROJ4; libaec's stale cmake cache had to be removed from the copied tree). The
binary is in the runner bundle (`exec/wgrib2`, installed to `/usr/local/bin` by the user-data).
All UPP records, scalar and wind, carry the same sec3 (scan mode 0x40, no stagger bits), i.e.
UPP wrote everything on the H points; the regridded 10 m wind statistics match the archive's
(means, extremes) and the component RMSEs in section 7 confirm the rotation.

### The recipe (`run/products.sh`, mirrors `ush/nam_prdgen5.sh`)
`gridspecs = lambert:265:25:25 226.541:614:12191 12.190:428:12191` (614 x 428, LoV 265, Latin
25/25, first point 12.19N 226.541E, 12.191 km) taken from the ops script and confirmed with
`wgrib2 -grid` on the archive (winds(grid), complex packing c3). Field selection with the ops
lists `parm/wgrib2.txtlists/nam_awphys.txt` and `nam_awphys_inst.txt` (instantaneous TCDC and
fluxes), U/V paired with `-submsg_uv`, `-new_grid_winds grid`, bilinear with the ops neighbour set
(the intersection of `neighbor_interp.parm` and the awphys list, as `wgrib2_parm_filter.py`
derives it) and budget for APCP/ACPCP/SNOD/WEASD.

Accumulations: the run carries 3 h buckets; the archive carries on the C clock the 12 h bucket
(APCP, ACPCP and the snowfall WEASD) and, except at the first hour of a bucket, a 3 h APCP/ACPCP
pair (`nam_makeprecip`). products.sh keeps every hour's 3 h bucket aside and sums (wgrib2
`-import_bin` + `-rpn`) the buckets since the bucket start b0 = 12·floor((h−1)/12) on grid 218
(sums commute with the budget interpolation). At f00 the archive has zero-length `0-0 day acc`
records with zeros; ours are the same.

The clock: `-set_date C` plus one `-set_ftime2` per distinct forecast-time string shifted by
−6 h ("N hour fcst" → "N−6 hour fcst" or "anl"; "a-b hour max/min/acc" → "(a−6)-(b−6)"), so
verification times are unchanged; a final check refuses any record whose reference time is not C
or whose verification time is not START+h. The max/min records are 1 h windows ("23-24 hour
max") in the model regardless of the history interval, exactly as the archive. At f00 the
instantaneous fields become `anl` and the 1 h max/min records are dropped (the archive's f00 has
none).

### Inventory match (ours vs `nam.t00z.awphys24.tm00.grib2`)
Mock run on the Phase 0 arm64 f24 file (CYCLE shifted so it plays integration hour 24): **454
records vs 454**, and the inventory normalised to variable:level:time-kind differs in **zero
lines**. Time kinds, ours: 443 "N hour fcst", 4 "a-b hour max", 2 "min", 3 x 12 h acc (APCP,
ACPCP, WEASD), 2 x 3 h acc (APCP, ACPCP); archive: identical. f00: 446 = 443 anl + 3 "0-0 day
acc". Records we cannot produce identically:
- none missing; one difference of *order*: the archive has the 12 h bucket records at their
  list position (~332) and the 3 h records appended; ours puts all accumulations at the end of
  the file. `.idx` consumers do not care; byte-identical record order was not attempted.
- the packing is complex c3 as the archive (a first version re-encoded with simple packing,
  154 MB instead of 62 MB; every `-grib_out` now carries `-set_grib_type c3`).
Per-record table: `docs/figs/tm06/inventory-f24.txt` (to be written by the acceptance run).

Time per file: 29 s wall (2 m 39 s CPU with OpenMP) on the build box for 454 records.

### Names
`products/nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2` and `.idx` in
`s3://nam-recast-617711905691/products/`; the FrankenNAM name and the honesty line only in
`products/README.md` (`run/products-README.md`).

## 4. Runner, post overlap and self-chaining

`run/runner.sh`: stage → NPS → forecast, with UPP + products running **alongside the forecast
on the write ranks' cores 28-31** (4 UPP ranks, `OMPI_MCA_mpi_yield_when_idle=1` for the model so
the write ranks, idle between history writes, give those cores up) instead of after the forecast
as in Phase 0 (`POST_AFTER=1` restores that). Measured on the box with the model idle: UPP
40 s per file on 4 ranks, products 12-15 s per file, and **UPP + products need 21.6 GB** on top
of the model's 43.2 GB, so the overlap does not fit a 64 GB c8g.8xlarge; the acceptance chain
runs on **m8g.8xlarge (128 GB, Spot $0.52/h in us-west-2d against c8g's $0.47)**, which also
leaves room for restart files later. On a c8g, set `POST_AFTER=1` (UPP with 16 ranks after the
forecast: 29 x 27 s + 29 x 12 s ≈ 19 min to the last product). The model's pace with UPP
alongside is measured in the acceptance run (section 6). Timeline of every
stage in `timeline.txt` (uploaded with the logs).

`run/launch.sh` builds the user-data for a runner (the same from the laptop via
`deploy/04-run-case.sh` and from a finished runner); `--next` pops the first line
`CYCLE MODE ARCH [KEY=VAL ...]` of `s3://nam-recast-617711905691/queue/hindcast.txt` (read,
rewrite without that line, launch). `deploy/07-runner-policy.sh` adds the inline policy
`nam-recast-chain` to `nam-recast-ec2`: RunInstances on instances/volumes only with
`aws:RequestTag/project = nam-recast`, CreateTags only with `ec2:CreateAction = RunInstances`,
TerminateInstances only on `aws:ResourceTag/project = nam-recast`, the Describe calls, PassRole
of the role to EC2, and GetParameter on the public Canonical AMI parameter (applied 4 Nov 2026).

**What cannot work as written:** with the account's Spot quota of 32 vCPU (= one c8g.8xlarge),
a runner cannot launch its successor while it is itself alive: RunInstances is refused
(`MaxSpotInstanceCountExceeded`). `launch.sh` therefore hands over to a **relay**: a t4g.nano
on-demand instance (~$0.004/h, same role and tags) that waits until no `nam-recast-runner` is
running, launches the queued runner (retrying zones and Spot capacity), uploads its log and
terminates. Once the pending raise to 64 vCPU lands the direct launch succeeds and the relay is
never used. Node choice: the launcher tries an ordered type list, `m8g.8xlarge, m7g.8xlarge`
(128 GB, UPP alongside the model) then `c8g.8xlarge` with `POST_AFTER=1` (64 GB), each across
all four zones, so a queue cannot stall on one type (m8g Spot capacity ran out in two zones on
5 Nov 2026 and the first chain-a ran on m7g).

**Spot interruption leaves the chain dead (open, Phase 2):** the queue line is popped before the
job runs and the chain fires only from a finished runner, so a reclaimed runner (chain-a,
m8g in us-west-2d, reclaimed 14 min in on 5 Nov 2026) ends the chain with nothing relaunched and
the job lost from the queue. Phase 2 fix: leave the job line in the queue (mark it "running
<instance>") until DONE is written, and have the relay, or the EventBridge/Lambda scheduler of
the dress rehearsal, re-launch any job whose runner is gone without DONE; with restarts back on
(128 GB nodes allow them) the relaunch resumes from the last restart instead of starting over. The relay is on-demand (2 of the 32 on-demand vCPU), so the arm build box (32 vCPU
on-demand) must be stopped while a chain can fire; it is, during runs. Zones are tried in the order 2d, 2a, 2c, 2b (2d had the cheapest c8g Spot,
$0.466/h, on 4 Nov 2026).

**Chain test (5 Nov 2026):** queue = chain-a (6 h), chain-b (6 h), acceptance (90 h). The first
chain-a (m8g, 2d) was Spot-reclaimed 14 min in (see the open item above) and was relaunched by
hand on m7g in 2a (no m8g capacity in two zones at that moment). It ran stage → NPS → 6 h →
UPP f06 → product f00 → DONE at 01:39:25 (1 min 33 s after the model's end), popped chain-b
from the queue and launched it **directly** as m8g.8xlarge in 2d at 01:40:01 while chain-a was
still alive: the Spot vCPU raise to 64 (L-34B43A08) had been approved in the meantime, so the
relay path was never exercised and stays untested; it remains the fallback should the quota
shrink again. chain-b then popped the acceptance run (section 6).

## 5. Stage clock (measured) and projected live clock

Build box (c8g.8xlarge on-demand, 150 GB gp3 raised to 500 MB/s mid-way) for the 90 h NPS:
stage (server-side copy of 31 GFS files + seed, download) 226 s; ungrib 31 files + seed ~570 s
(disk-bound at the 125 MB/s gp3 baseline, 16 ungribs writing at once; the runner's volume has
500 MB/s); metgrid IC 11 s + bocos 135 s; nemsinterp 157 s. NPS total ≈ 16 min on the box, about
12 min on a runner volume.

Runner clock and the projection for a live 12Z cycle (GFS 06Z f090 on AWS by ~09:57Z = C−2:03,
f000 by ~C−2:15): filled in from the acceptance run, section 6.

## 6. Acceptance run (tm06, C = 2026-11-01 00Z, START = 2026-10-31 18Z, seed = archived NAM 18Z)

Box test first (9 h, same configuration, build box c8g.8xlarge): init + TDFI 4 min 14 s, then
569 / 571 / 572 s per 3 h = **190.7 s per forecast hour** with nothing else on the node (the 84 h
Graviton validation averaged 200), node peak 43.2 GB; f00/f03 products 446/452 records as the
archive, PRMSL f00 988.1-1032.8 hPa, no undefined points, 58.1 / 59.3 MB against the archive's
57.1 / 59.7 MB.

(acceptance runner: to be filled: runner id/zone/price, timeline, model pace with concurrent
UPP, products completion after the model end, PRMSL sanity per file, cost)

## 7. Comparison: fidelity to the archived NAM (tm06 | anl | GFS)

The Phase 1 gate (rewritten 4 Nov 2026 after the baseline scorecard) is fidelity to the
archived NAM, with the GFS alongside for context, not "beat the GFS". The table therefore
leads with tm06 vs the archived NAM; the anl column (the Phase 0 analysis start from the same-
cycle GFS, Graviton run) and the GFS column are context: anl shows what the 6 h information lag
costs and the spin-up gains, GFS shows the independent model the NAM was never meant to beat.

### Soil trace at f00 (the seeding acceptance), from the 9 h box test
RMSE / bias over CONUS land, 0.25 deg grid (`soil.md`):

| Field | tm06 vs seed | tm06 vs NAM (C) | tm06 vs GFS (C) | tm06 vs anl | anl vs GFS | anl vs NAM | NAM vs seed |
|---|---|---|---|---|---|---|---|
| SOILW 0-10 cm (m3/m3) | 0.011 / -0.003 | 0.012 / -0.002 | 0.087 / +0.050 | 0.070 / +0.045 | 0.048 / +0.005 | 0.072 / -0.047 | 0.009 / -0.001 |
| TSOIL 0-10 cm (K) | 3.18 / +2.33 | 0.90 / +0.11 | 2.11 / +0.68 | 1.77 / +0.78 | 1.12 / -0.10 | 1.75 / -0.67 | 3.05 / +2.22 |
| SOILW 40-100 cm (m3/m3) | 0.010 / +0.000 | 0.010 / +0.000 | 0.091 / +0.051 | 0.075 / +0.046 | 0.048 / +0.005 | 0.076 / -0.045 | 0.001 / +0.000 |

The f00 soil moisture of the product is the NAM's (0.011 m3/m3 from the seed and 0.012 from
the archived NAM at C, against 0.087 from the GFS and 0.070 from the GFS-soil anl run; the GFS
is 0.05 m3/m3 wetter than the NAM over CONUS). The 0-10 cm soil temperature has moved 6 h of
diurnal cycle away from the seed (3.2 K, the same 3.1 K the archived NAM itself moved) and sits
0.9 K from the archived NAM at C, half the anl run's 1.75 K. The seeding works as designed.

### f00 from the 9 h box test (same run as the acceptance, hours 0-6)
| Field | tm06 vs NAM | anl vs NAM | GFS vs NAM | tm06 vs anl |
|---|---|---|---|---|
| MSLP (hPa) | 0.99 / -0.67 | 0.82 / -0.53 | 0.86 / -0.56 | 0.55 / -0.13 |
| Z500 (dam) | 0.49 / -0.36 | 0.67 / -0.58 | 0.52 / -0.38 | 0.38 / +0.22 |
| T2m (K) | 1.49 / +0.88 | 1.15 / -0.14 | 1.36 / -0.31 | 1.42 / +1.02 |
| 10 m speed (m/s) | 0.96 / +0.55 | 1.10 / +0.45 | 1.22 / +0.58 | 0.88 / +0.10 |
| U10 (m/s) | 1.00 / -0.22 | 1.05 / -0.10 | 1.23 / -0.16 | 0.86 / -0.12 |
| V10 (m/s) | 0.92 / +0.23 | 1.00 / +0.11 | 1.21 / +0.21 | 0.89 / +0.12 |

Read plainly: at f00 the 6 h lag costs 0.17 hPa of MSLP fidelity against the analysis start
and the spin-up adds a +0.9 K 2 m warm bias at 00Z over CONUS that the analysis start does not
have; Z500 and the 10 m wind are closer to the archived NAM than either the anl start or the
GFS. The U/V component RMSEs are the size of the speed RMSE, so the grid-218 wind rotation is
right. The later leads come from the acceptance run below.

(f24/f48/f84 and 24 h precipitation: to be filled from the acceptance run)

## 8. What broke

- Vtable column widths (PARSE_TABLE read error 3) — see section 2.
- The wrong year staged (brief typo) — section 1.
- `aws s3 cp` server-side copies from the NOAA buckets fail on GetObjectTagging from the runner
  role; `--copy-props none`.
- `pkill -f "recast.sh"` from an ssh session kills the session itself (the pattern matches the
  remote shell's command line); anchored patterns.
- The build box root volume (gp3 default 125 MB/s) throttled 16 parallel ungribs to ~9.5 min;
  raised to 500 MB/s / 6000 IOPS ($0.02/h).
- The first 9 h test aborted (SIGABRT) 2 min into the init: nemsinterp had printed
  `min,max for TSK 233.9 9.999E+20`. The blanked water points of the seed's skin temperature had
  come through as 9.999e20 (complex-packing missing values, not a bitmap with zeros as I had
  assumed), and a `missing_value=0.` table entry did not catch them. Fixed with
  `missing_value=9.999e+20`; the IC extremes are now checked and printed by `recast.sh nemsinterp`.
- **Acceptance run, 02:55 UTC:** the concurrent post loop died at product hour 06 (the first
  12 h bucket sum): the earlier 3 h bucket was written with `-no_header -bin` but read back with a
  plain `-import_bin`, which expects Fortran record headers ("import_bin: header record size
  wrong"). f00/f03 need no sum, so the box test never reached it. One-token fix (`-no_header` on
  the import). Worse than the bug: the failure stayed silent for three hours while the model ran
  on; runner.sh now uploads post.log/products.log/timeline.txt at once and writes a
  `POST_FAILED` marker next to DONE/FAILED so a watcher sees it. The post was restarted alongside
  the model at 06:0x UTC from the node (the coordinator had kept the node from shutting down).
- wgrib2 `-match` with alternations needs care: `:APCP:surface:12-24` does not match
  `:APCP:surface:12-24 hour acc fcst:` with a trailing `:` in the pattern.

## 9. Cost

(to be filled)

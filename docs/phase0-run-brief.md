# Phase 0 run brief: one cold-start 12 km recast, compared with the archived NAM

Goal: with the executables from `docs/phase0-build-brief.md`, run the 12 km NAM parent domain
as a cold start from the GFS analysis for **2026-11-01 00Z**, 84 h, post it to GRIB2, and put
it beside the real NAM run of that cycle. This closes Phase 0; after it we stop and re-evaluate.

## Inputs (all already staged)

- GFS 0.25° GRIB2, `pgrb2.0p25` and `pgrb2b.0p25`, f000..f084 every 3 h:
  `s3://nam-recast-617711905691/cases/2026110100/gfs/`
- Archived operational NAM for the same cycle (awphys grid 218, f00..f84):
  `s3://nam-recast-617711905691/cases/2026110100/nam-archive/`
- Fix files recovered from Wayback (1,031 files, 6 GB): `s3://nam-recast-617711905691/fix/wayback/`
  → sync to `/opt/nam/fix`. Includes the parent geogrid output `nam_geo_nmb.d01.dio`, so
  geogrid.exe should not be needed. `nam_co2historicaldata_2026.txt` is missing: copy 2025 to
  2026 (the forecast script wants the start year and the year before).
- Executables: `/opt/nam/work/exec/` on the build box.

## Use the operational scripts as the spec, not as the driver

Read, in this order, in `/opt/nam/work/src` (upstream = MatthewPyle-NOAA/NAM):
`jobs/JNAM_COLDSTART_PREP`, `scripts/exnam_coldstart_prep.sh` (ungrib → metgrid → nemsinterp
for the initial condition; it uses `parm/nam_Vtable.GFS.bocos`, `nam_METGRID.TBL.NMM_gfsgrib2`,
`nam_namelist.nps*`), `scripts/exnam_ungrib_boco.sh`, `exnam_metgrid_boco.sh`,
`exnam_nemsinterp_boco1.sh` (lateral boundaries), `jobs/JNAM_FORECAST`, `scripts/exnam_fcst.sh`
(how `configure_file_01` is assembled from `parm/nam_configfile`, which fix files are linked,
`solver_state.txt`, how NEMS.x is launched), `parm/nam_node_decomposition*` (inpes/jnpes and
write tasks), `scripts/exnam_post.sh` + `parm/nam_post_avblflds.xml` + `postxconfig-NT-NMM.txt*`
(UPP control), `ush/` helpers they call. `versions/run.ver` names the WCOSS2 module versions.
Then write our own driver `run/recast.sh` (plus small helpers) that does the same steps with
plain paths, `mpirun` from Intel MPI, no `module`, no `compath.py`, no `prod_util` unless you
build the tiny pieces it needs (`ndate` is easy to replace with `date -u -d`).

Deviations from ops, on purpose:
- Start at the cycle time from GFS f000 (ops started 6 h earlier from GDAS and ran a catch-up
  with data assimilation). Boundaries from GFS f003..f084 every 3 h.
- Parent domain only: `num_domains_total 1`, `n_children 0`, no nests, no fire-weather domain,
  no TC relocation, `radar_init` off, lightning off. Keep the 60 levels, dt 25⅓ s, the physics
  exactly as in `nam_configfile`. Use the digital-filter setting the ops **tm00 free forecast**
  used (read `exnam_fcst.sh`); if it used none, use none.
- Output: history files 3-hourly (ops cadence for the parent) to 84 h; whatever restart
  frequency keeps Spot recovery possible (every 12 h is fine).

## Where to run

1. **Smoke test on the build box** (32 vCPU): 3 h forecast, decomposition like
   `inpes 4 × jnpes 7` compute + 1 write group of 4 tasks = 32 MPI tasks. Goal: NEMS.x runs,
   history files appear, UPP converts one to GRIB2, `wgrib2` reads it (`apt install wgrib2`).
   Measure seconds per forecast hour. Expect ~1 h of wall per 3-4 forecast hours on this box.
2. **Full 84 h on a bigger node.** Make an AMI of the build box (`aws ec2 create-image`),
   launch **one** `c7a.48xlarge` (96 physical cores, 192 vCPU) as **Spot** from it
   (`--instance-market-options MarketType=spot`, one-time, same subnet/SG/role/key), run
   detached with `nohup`, sync history + GRIB2 + logs to
   `s3://nam-recast-617711905691/cases/2026110100/recast/` every hour, and **terminate it
   when done** (self-terminate from the script, with the box's role allowed to call
   `ec2:TerminateInstances` on itself only if you add that, otherwise terminate it from the
   laptop). Decomposition for 96 cores: compute ~84-88 tasks (e.g. 8 × 11) + 1 write group of
   8; do not hyperthread (use physical cores, `-ppn 96` on a 192-vCPU box is wrong). If Spot
   capacity is refused, fall back to on-demand `c7a.48xlarge` (≈ $9.8/h) and keep it under 10 h.
   While the big node runs, **stop the build box** (`deploy/02-stop.sh`) and start it again
   only when you need it.
3. If the 84 h run blows up (NaN, CFL abort), capture the log, try once with the digital
   filter on (if it was off) or vice versa, and report. Do not iterate more than twice.

## Comparison (keep it modest)

Python on the laptop or the box (`xarray` + `cfgrib`, or `pygrib`; `wgrib2 -new_grid` to put
everything on one 0.25° lat-lon grid covering 20-60N, 130-60W):
- Fields: MSLP, 500 hPa height, 2 m temperature, 10 m wind speed, 6 h precipitation ending at
  f24/f48/f72, total precipitation to f84, and composite reflectivity or 700 hPa RH if easy.
- Three columns per field: recast, archived NAM, GFS (the staged pgrb2 files), at f24, f48, f84.
- A small table: RMSE and bias of recast vs archived NAM, and of GFS vs archived NAM, over
  CONUS land, for 2 m T, MSLP, 500 hPa Z, 24 h precip. The question it answers is "is the recast
  closer to the NAM than the GFS is?"
- Deliverables: PNGs + the table in `docs/phase0-case-2026110100.md`, PNGs also in
  `s3://nam-recast-617711905691/cases/2026110100/figs/`.

## Deliverables

- `run/recast.sh` and helpers, `run/README.md` (inputs, how to launch, decomposition, wall time).
- `deploy/03-runner-ami.sh` (make AMI) and `deploy/04-run-case.sh` (launch Spot runner) if you
  script them; otherwise the exact commands in `run/README.md`.
- `docs/run-notes.md`: what broke, timings (NPS steps, seconds per forecast hour on 32 and 96
  cores, UPP per file), memory high-water mark, and the cost of the run.
- `docs/phase0-case-2026110100.md` with the figures and table.
- Commits at milestones (smoke test runs; 84 h done; comparison done), explicit `git add`.

## Acceptance

```
aws s3 ls s3://nam-recast-617711905691/cases/2026110100/recast/grib2/ | wc -l   # 29 (f000..f084 every 3 h)
wgrib2 <f084 file> -match ':PRMSL:' -stats                                         # sane range, no NaN
ls docs/phase0-case-2026110100.md run/recast.sh docs/run-notes.md
```

## Rules

- Budget for this brief: about $60 of compute. The build box is $1.64/h; the Spot runner
  ≈ $2.5-4/h for ≈ 8 h. Stop the build box whenever you are waiting on the runner.
- One runner instance at a time; terminate it when the run is done or has failed twice.
- Do not touch any other bucket, instance or project. Do not modify `/opt/nam/upstream`.
- Report: commits, timings, cost, the comparison table, and the three biggest surprises.
  If the run fails, say exactly how, with the log excerpt.

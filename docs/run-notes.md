# Phase 0 run notes: cold-start recast of 2026-11-01 00Z

Driver: `run/recast.sh` (+ `run/runner.sh`, `run/compare.py`, `deploy/04-run-case.sh`); see
`run/README.md` for the stages and the deliberate deviations from ops.

## What broke and what was changed

1. **NEMS.x never exited and never wrote its last history file.** The 3 h smoke run integrated
   to the end, then all 28 forecast ranks sat in `MPI_Finalize` while the 4 quilt (write) ranks
   waited in `MPI_RECV` for the f03 history data (gdb stacks). The forecast ranks `MPI_ISEND`
   history/restart data and only `MPI_WAIT` at the next output time; after the last output there is
   no next time. Cray MPICH evidently delivered those sends anyway; Intel MPI does not progress
   them from inside `MPI_Finalize`. A first fix (waiting on the ISend handles in `WRITE_DESTROY`)
   did not help; the write ranks still stalled on the next sender. The fix that works:
   `MPI_BARRIER(MPI_COMM_WORLD)` before `ESMF_Finalize` in `MAIN_NEMS.F90`
   (`build/patches/nems-01-barrier-before-finalize.patch`). Verified with a 1 h run (hourly history,
   no filter) and the 3 h smoke run (TDFI): clean exit 0, f01/f03 history written. This matters
   beyond the end of the run: any run that stops at an output time would lose its last file.
2. **No big runner within the account's quotas.** Both "Running On-Demand Standard" and "All
   Standard Spot Instance Requests" are 32 vCPU in us-west-2, so a c7a.48xlarge (192 vCPU) is
   refused (`MaxSpotInstanceCountExceeded`; before that, `InsufficientInstanceCapacity` in 2a/2b/2c).
   I did not file a quota increase (an account change outside this brief), so the 84 h ran on a
   32-core node with the smoke-test layout (28 compute + 4 write) while the build box was stopped.
   **Attempt 1, c7a.8xlarge Spot (64 GB, $0.59/h): killed by the OOM killer at forecast hour
   12.05.** All ranks got `SIGKILL` while the 12 h history and the first restart were being
   written. No restart survived; the partial f12 history and its logs are in
   `s3://.../cases/2026110100/recast/attempt1-oom/`.
   **Attempt 2, r7a.8xlarge Spot (256 GB, $0.82/h), same layout, from scratch: completed.**
   `mem.log` shows why attempt 1 died: memory in use is flat at 48 GB through f09, jumps to
   70 GB at the first restart write (8.9 GB restart file gathered on 4 write ranks), stays at
   ~68 GB afterwards, and peaks at 77 GB (11:57, the 72 h history + restart). A 64 GB node cannot
   run this configuration with restarts on. On a 32-core node use r7a/m7a (m7a.8xlarge, 128 GB,
   is enough at $0.62-0.69/h), or more write ranks so the gather is spread.
3. **The AMI route was too slow.** The first snapshot of the build box's 300 GB volume ran at
   ~1 %/min (>1.5 h). Replaced by a 12.5 GB tar bundle in `s3://.../runner/bundle-20261104.tar`
   (oneAPI runtime + `/opt/nam/libs` + exec + fix + parm + run scripts + IC + bocos) unpacked onto
   stock Ubuntu 24.04 by user-data: the runner was computing 45 s after boot. The AMI was
   deregistered and its snapshot deleted.
4. Smaller items: GNU `date -d "20261101 00:00 +27 hours"` reads `+27` as a time-zone offset
   (needs `UTC` before the offset); UPP names its output `BGDAWP.GrbFnn`, not `BGDAWPnn.tm00`;
   Ubuntu 24.04 has no `wgrib2` package (built v3.1.3 from the CPC tarball with gcc/gfortran);
   eccodes cannot geolocate UPP's rotated B grid (template 32769), `wgrib2 -gridout` can, and
   `wgrib2 -new_grid` silently produces nothing for it, so `compare.py` interpolates itself; the
   archived awphys files pack 10 m U/V as sub-messages (`codes_grib_multi_support_on`).
5. c7a has SMT off: `lscpu` shows 1 thread per core, so a c7a.48xlarge is 192 physical cores, not
   96 as the brief assumed. `runner.sh` would use 12 x 14 + 2 x 8 tasks there.

## Timings

| Step | Where | Time |
|---|---|---|
| ungrib, 29 GFS files, 16 serial ungribs in parallel | build box, 32 cores | 380 s |
| metgrid IC (dmpar 14) + 15 serial boco streams | build box | 380 s (IC alone 10 s; serial boco metgrid ~4 min per time) |
| nemsinterp IC + 7 boco streams (4 tasks each) | build box | 479 s |
| **NPS total** | | **~21 min** |
| 3 h smoke forecast, 28 compute + 4 write, TDFI | build box | 969 s wall (TDFI + init ~5.5 min) |
| 1 h, no filter | build box | 258 s wall |
| UPP per history file (16 tasks / 8 tasks) | build box | 21 s / 35 s |
| 84 h forecast (attempt 2), 28 compute + 4 write, TDFI, 3-hourly history, 12-hourly restart | r7a.8xlarge Spot | 15,905 s = 4 h 25 min |
| UPP, 29 files, 16 tasks, after the forecast | r7a.8xlarge Spot | 634 s (20-31 s per file) |
| runner boot to computing (bundle from S3) | | ~45 s |
| `compare.py` (21 figures + table) | build box | ~5 min |

Seconds per forecast hour on 32 cores: **189 s** over the whole 84 h run (filter, I/O and restarts included), so a run takes about 4.4 h on 32 cores. Not measured on 96+ cores (quota). Integration profile from the smoke run (28 compute
ranks): radiation 14 %, turbulence 11 %, halo exchanges 22 %. A radiation step costs ~14-17 s
versus ~0.55 s for a dynamics step (`nrads = nradl = 48`).

Memory high-water mark: 77.4 GB in use on the node (attempt 2, `free`, sampled each minute);
per rank 2.2 GB in the 3 h smoke run and 3.7 GB max RSS in attempt 1. History files are 4.9 GB
each (nemsio; 29 files = 141 GB in S3), restart files 8.9 GB.

## Cost

| Item | Hours | Rate | Cost |
|---|---|---|---|
| Build box c7a.8xlarge on-demand, this brief (04:57-07:21 NPS + smoke; 12:00-13:10 comparison) | ~3.6 | $1.64 | ~$5.9 |
| Runner attempt 1, c7a.8xlarge Spot (07:20-08:05, OOM) | 0.74 | $0.59 | $0.44 |
| Runner attempt 2, r7a.8xlarge Spot (08:08-12:47) | 4.65 | $0.82 | $3.80 |
| EBS (2 x 300 GB gp3 for runner hours), S3 PUTs | | | <$0.50 |
| **Compute total** | | | **~$10.6** (budget ~$60) |

Ongoing storage: about 141 GB of history and 15 GB of GRIB2 under `cases/2026110100/recast/`,
plus the 12.5 GB runner bundle, roughly $4 a month in S3 Standard. Delete `recast/history/`
when it is no longer needed.

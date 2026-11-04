# run/: the NAM 12 km parent-domain recast driver

`recast.sh` replaces the WCOSS2 job chain for a cold start from GFS. Stages, each following one
operational script (the scripts in `sorc/../scripts` are the spec):

| Stage | Ops script it mirrors | What it does here |
|---|---|---|
| `ungrib` | `exnam_coldstart_prep.sh`, `exnam_ungrib_boco.sh` | one serial `ungribs.exe` per GFS `pgrb2.0p25` file f000..f084 (ops used pgrb2 only, via `getges pg2cur`), 16 in parallel, `nam_Vtable.GFS.bocos` |
| `metgrid` | `exnam_coldstart_prep.sh`, `nam_boco_metgrid_gen.sh` | IC: dmpar `metgrid.exe` with `nam_METGRID.TBL.NMM_gfsgrib2`; bocos: serial `metgrid_serial.exe` with `nam.METGRID.TBL.bocos`, two times per stream as ops |
| `nemsinterp` | `exnam_coldstart_prep.sh`, `exnam_nemsinterp_boco1..7.sh` | IC `input_domain_01_nemsio`; boundary files `boco.0000..0081` from 12 h streams of 5 met files |
| `fcst` | `exnam_fcst.sh` | `configure_file_01` from `parm/nam_configfile` with the sed chain of ops, fix/parm links as ops, `mpirun NEMS.x` |
| `post` | `exnam_post.sh` | `ncep_post` per history file with `nam_cntrl_cmaq_flatfile.txt` (`_00h` at f00), outputs BGDAWP/BGRDSF/BGRD3D GRIB2 |
| `sync` | - | GRIB2, history, restarts and logs to `s3://nam-recast-617711905691/cases/<cycle>/recast/` |

Deliberate deviations from ops (see `docs/phase0-run-brief.md`): start at the cycle time from
GFS f000 (no GDAS tm06 start, no catch-up/DA), parent only (`num_domains_total 1`, `n_children 0`),
`radar_init 0` (filter variables `nam_filt_vars_norad.txt`), no precipitation assimilation
(`pcpflg false`), history every 3 h (ops: hourly), restart every 12 h. `restart false` with
`input_domain_01_nemsio` (the ops GDAS-guess path). `filter_method 3` (TDFI): what `exnam_fcst.sh`
sets for a tm00 forecast that is not restarting. Physics, dt (25 1/3 s), 60 levels and the 00Z
accumulation buckets (precip 12 h, others 6 h) are untouched.

## Inputs

- `/opt/nam/cases/<cycle>/gfs/gfs.t00z.pgrb2.0p25.fFFF` (from `s3://.../cases/<cycle>/gfs/`)
- `/opt/nam/fix` (from `s3://.../fix/wayback/`; copy `nam_co2historicaldata_2025.txt` to `_2026.txt`)
- `/opt/nam/work/src` (upstream tree, `parm/`) and `/opt/nam/work/exec` from `build/build_all.sh`

## How to run

```
# build box (32 cores): NPS for the whole 84 h, then a 3 h smoke forecast + post
CYCLE=2026110100 FHMAX=84 run/recast.sh nps
RUNDIR=/opt/nam/runs/smoke3h FHMAX=3 run/recast.sh fcst post     # after linking nemsinterp_ic and bocos into it

# big node: AMI of the build box, then one Spot c7a.48xlarge that runs run/runner.sh and terminates
deploy/03-runner-ami.sh
TYPE=r7a.8xlarge SUBNET=<subnet with capacity> deploy/04-run-case.sh   # 'ondemand' as the argument if Spot is refused
```

`runner.sh` pulls any restart already in S3 (Spot recovery), runs `fcst` in the background,
`post` alongside it (waiting for each `fcstdone` file), syncs to S3 every 50 min, writes
`DONE` or `FAILED` to the S3 case prefix, and the user-data shuts the instance down (shutdown =
terminate).

Decomposition: smoke test 4 x 7 compute + 1 x 4 write = 32 tasks; the 2026110100 84 h run used
the same layout on an r7a.8xlarge (the account's EC2 vCPU quotas are 32 for both Spot and
on-demand; a 64 GB c7a.8xlarge runs out of memory at the first restart write, see
`docs/run-notes.md`). 84 h took 4 h 25 min (189 s per forecast hour) plus 11 min of UPP. On a c7a.48xlarge (192
physical cores; c7a has no SMT, `lscpu` shows 1 thread per core) 12 x 14 = 168 compute + 2 x 8
write = 184 tasks pinned to cores 0-183, UPP on cores 184-191.

`compare.py <case dir> <out dir>` puts recast(s), archived NAM and GFS on a 0.25 deg grid and
writes the figures and the RMSE/bias table (needs `wgrib2` for the B-grid coordinates and a
venv with numpy, scipy, eccodes, matplotlib, cartopy). If `<case dir>/recast-arm64/grib2`
exists it is added as a source: panels become arm | x86 | NAM | GFS and the table carries
arm vs x86, arm vs NAM, x86 vs NAM and GFS vs NAM.

## arm64 (Graviton) runs

The same scripts drive the gfortran/OpenMPI build (`docs/graviton-port.md`): `recast.sh` picks
Intel MPI or OpenMPI by what is installed (`mpi_cmd` adds `--bind-to core` / `--cpu-set` for
OpenMPI, whose default is socket binding), `runner.sh` takes `S3SUB=recast-arm64 NO_RESTART=1`
(no restart files at all so the run fits 64 GB) and `SYNC_HISTORY=0`. `run/bundle.sh` packs
the runner tar (`runner/bundle-<date>-arm64.tar`), `deploy/04-run-case.sh ARCH=arm64` launches a
c8g.8xlarge Spot runner from it, `run/smoke.sh` runs the build-box acceptance set (two 3 h
smokes + cmp, UPP, PRMSL stats, 1 h trap build), `run/cmp_nemsio.py` compares nemsio files.

# Phase 0 build brief: port NPS + NMMB + UPP off WCOSS2

Goal: on the x86 build box, compile the NAM v4.2 preprocessor (NPS), the NMMB forecast
model (NEMS) and the post-processor (UPP) from the recovered source, and leave behind a
reproducible build script so the result can become a Docker image. No forecast yet; that is
the next task once binaries exist. See `docs/scoping.md` for why.

## Environment

- Instance: see `deploy/.build-box` (instance id, public IP). `ssh -i ~/.ssh/nam-recast.pem ubuntu@<IP>`.
  Ubuntu 24.04, c7a.8xlarge (32 vCPU AMD Genoa, 64 GB), 300 GB disk. Cloud-init writes
  `/opt/nam/READY` when done; its log is `/var/log/nam-recast-init.log`.
- Source: `/opt/nam/upstream/MatthewPyle-NOAA-NAM` (branch `main`, NAM v4.2.11 re-release,
  **primary**) and `/opt/nam/upstream/EricRogers-NOAA-nam_wcoss2_rocoto` (2022; reference
  only, it has WCOSS2 build logs and compiled artifacts that show what the real build did).
- Work in `/opt/nam/work`, install libraries under `/opt/nam/libs/<name>-<ver>`.
- The box has an instance role: `aws s3 cp` to `s3://nam-recast-617711905691/` works. Put
  build logs there under `build/<date>/`.
- Case-sensitive filesystem matters: the trees hold both `foo.F90` and preprocessed `foo.f90`.
  Never copy the tree through a Mac.

## What the real build used (`versions/build.ver`, `modulefiles/wcoss2/build/v4.0.0_build`)

Intel 19.1.3 classic `ifort` + Cray MPICH 8.1.9; ESMF 7.1.0r; netCDF 4.7.4 / HDF5 1.10.6;
NCEPLIBS: bacio 2.4.1, sp 2.3.3, ip 3.3.3, w3emc 2.9.1, w3nco 2.4.1, g2 3.4.5, g2c 1.6.4,
g2tmpl 1.10.0, sigio 2.3.2, sfcio 1.4.1, gfsio 1.4.1, nemsio 2.5.2, bufr 11.5.0, crtm 2.3.0,
wrf_io 1.2.0, landsfcutil 2.4.1; jasper 2.0.25, libpng 1.6.37, zlib 1.2.11.
All NCEPLIBS are on GitHub under `NOAA-EMC/NCEPLIBS-<name>` with those tags (CMake).
CRTM 2.3.0 source: `JCSDA/crtm` tag `v2.3.0` (or the NCEPLIBS-crtm wrapper).
ESMF 7.1.0r: `esmf-org/esmf` tag `ESMF_7_1_0r`.

## Compiler strategy

1. **First choice: Intel oneAPI 2024.2 classic `ifort` + Intel MPI** (`apt` repo
   `intel-oneapi`, packages `intel-oneapi-compiler-fortran-2024.2.*`,
   `intel-oneapi-compiler-dpcpp-cpp-2024.2.*`, `intel-oneapi-mpi-devel-2021.13.*`). 2025
   toolkits dropped classic ifort; `ifx` is a different compiler and the NEMS code has never
   been built with it. Use `mpiifort`/`mpiicc` with `I_MPI_F90=ifort I_MPI_CC=icc` (or
   `icx` if `icc` is gone; the C side is small).
2. Fallback: gfortran 13 via `conf/configure.nems.Linux.gnu` (expect
   `-fallow-argument-mismatch -fallow-invalid-boz`, real*8 promotion flags, and MPICH or
   OpenMPI from apt). Only go here if Intel is blocked after a serious attempt.

## Build order and the files to read first

1. **Libraries** (script them in `build/libs.sh`): zlib, libpng, jasper 2.0.25, HDF5 1.10.6,
   netCDF-C 4.7.4 + netCDF-Fortran 4.5.x, then NCEPLIBS at the pinned tags, then ESMF 7.1.0r
   (`ESMF_COMM=intelmpi`, `ESMF_COMPILER=intel`, `ESMF_NETCDF=split`). If 7.1.0r will not
   compile with the 2024 compiler, try ESMF 8.0.1 or 8.1.1: the NEMS tree carries
   `src/ESMFVersionDefine_ESMF_8.h`, so 8.x was anticipated.
2. **NMMB / NEMS**: `sorc/nam_nems_nmmb.fd/src/`. Read `build.sh`, `build.esmf7.1r`,
   `conf/configure.nems.wcoss2` and `conf/configure.nems.Linux.intel`, `conf/modules.nems`,
   `conf/externals.nems`, and the real compile lines in `sorc/build_fcst.log` (Pyle) and
   `src/build.log.wcoss2`. Make a new `conf/configure.nems.awsx86.intel` modelled on
   wcoss2 but with paths under `/opt/nam/libs`. Target executable: `exe/NEMS.x` (NMM core
   only; GSM/FIM/GEN are stubs). The `Makefile` in `sorc/` shows which targets production
   built.
3. **NPS**: `sorc/nam_nps.fd/sorc/NMMB_init/NPS/`. Read `README_NPS`, `configure`,
   `configure.nps_wcoss2_dmpara`, `configure.nps_wcoss2_serial`, `arch/configure.defaults`,
   `arch/preamble.linux`, `compile`, `build.scr`, and `sorc/build_nps.log`. Needed
   executables: `geogrid.exe`, `ungrib.exe` (+ `ungribs`/`ungribp` if the scripts use
   them), `metgrid.exe`, `nemsinterp.exe`, plus the `dio`/`ncio` libraries they link.
   Production built a serial and a dmpar flavour; dmpar is what `exnam_*` scripts run.
4. **UPP**: `sorc/nam_nceppost.fd/sorc/` (`build_ncep_post.sh`, `sorc/build_post.log`),
   then `sorc/nam_post0.fd` (`build_post0.sh`). Needs CRTM 2.3.0 and wrf_io.
5. Skip for Phase 0: GSI, land utilities (`nam_land_utilities.fd`), ref2nemsio, sndp,
   everything under `util/`. Note anything the forecast scripts call that lives there.

## Deliverables

- `build/libs.sh`, `build/build_nems.sh`, `build/build_nps.sh`, `build/build_upp.sh` (or one
  `build/build_all.sh`) in the `nam-recast` repo, runnable from a clean Ubuntu 24.04 box,
  idempotent, each echoing the versions it built. Patches to upstream source go in
  `build/patches/*.patch` with a one-line reason each, applied by the scripts, never hand
  edits lost on the box.
- `docs/build-notes.md`: what broke, what was changed and why, compiler/library versions
  that worked, wall time per stage, anything that will matter for a Dockerfile.
- The executables copied to `s3://nam-recast-617711905691/build/<date>/exec/` with a
  `MANIFEST` listing name, size, `ldd` output and the commit hash of upstream.

## Acceptance

```
ls -l /opt/nam/work/exec/   # NEMS.x geogrid.exe ungrib.exe metgrid.exe nemsinterp.exe ncep_post
/opt/nam/work/exec/NEMS.x </dev/null; echo $?   # starts, fails on missing configure_file, no link/loader error
ldd /opt/nam/work/exec/NEMS.x | grep -c 'not found'   # 0
```

A compiled `NEMS.x` that aborts cleanly asking for its configure file is the stop signal for
this task. Running a forecast is the next brief.

## Rules

- Budget: the box is ~$1.64/h on-demand. If the Intel route is still failing after ~6 h of
  wall time, stop, write up where it is stuck in `docs/build-notes.md`, and report.
- Do not modify anything under `/opt/nam/upstream/*` in place; copy the tree to
  `/opt/nam/work/src` and patch there, keeping patches in the repo.
- Commit to `~/projects/nam-recast` on the laptop (the repo is not on the box): `scp` the
  scripts/notes back, `git add <explicit paths>`, never `git add -A`; no stash/reset/rebase.
  Commit as the repo's local identity (already configured).
- Do not touch any other project, bucket or instance in the account.
- Do not start Spot fleets or additional instances; one box is the budget.
- Report at the end: commits, which executables exist, the acceptance output, wall time per
  stage, and the three biggest surprises.

# Brief: Graviton (arm64, gfortran) port of NPS + NEMS.x + UPP, and the validation run

Read first: `docs/phase1-plan.md` (the "Revision 4 Nov 2026 (evening)" section), `docs/build-notes.md`,
`docs/run-notes.md`, `run/README.md`. Phase 0 built everything with Intel oneAPI on x86
(`build/*.sh`, `build/nems/configure.nems.awsx86.intel`) and ran the 2026-11-01 00Z case. This
brief ports the same stack to Graviton with gfortran + OpenMPI, validates it on the same case,
and measures speed, memory and cost. The x86 build box (`i-0ab3bbee9ba7068e7`, stopped) stays as
it is: do not start, modify or terminate it.

## Deliverables
1. `deploy/05-graviton-box.sh`: idempotent like `deploy/01-build-box.sh`, same bucket/role/key/SG,
   tag `Name=nam-recast-build-arm`, **c8g.8xlarge on-demand** (32 Graviton4 cores, 64 GB; the
   on-demand quota is 32 vCPU and the x86 box is stopped so it does not count), Ubuntu 24.04 arm64
   AMI from the SSM parameter (`.../arm64/hvm/ebs-gp3/ami-id`), **150 GB** gp3, user-data as in 01
   (bundles from `s3://tcz-backups-617711905691/nam-recast/upstream/`). Writes `deploy/.build-box-arm`
   (add to .gitignore). A matching `deploy/06-stop-arm.sh`.
2. The build scripts made arch-aware (an `ARCH`/`TOOLCHAIN` switch in `build/env.sh` or a parallel
   `build/toolchain.gnu.sh`; your choice, keep the x86 path working and untouched in behaviour):
   gfortran 13 + OpenMPI from apt (or MPICH if OpenMPI misbehaves; say why), same NCEPLIBS pins,
   netCDF/HDF5, jasper, ESMF. New `build/nems/configure.nems.awsarm.gnu` derived from the tree's
   `src/conf/configure.nems.Linux.gnu` plus: `-finit-local-zero` (Intel had `-init=zero`; the code
   relies on it), `-fallow-argument-mismatch`, `-fallow-invalid-boz` if needed, `-O2` or `-O3` but
   **no `-ffast-math`** (Intel used `-fp-model precise`), `-mcpu=neoverse-v1` so the binaries run on
   Graviton3 (c7g/m7g) as well as Graviton4. Record every flag change and every source patch under
   `build/patches/` with a one-paragraph why, as in Phase 0.
3. **ESMF:** try 7.1.0r first (with the Phase 0 patches). If it does not build on aarch64 after
   ~2 h of honest effort, move to the oldest ESMF 8.x that builds cleanly and patch NEMS to it;
   document the API changes touched. Keep `nems-01-barrier-before-finalize.patch` either way.
4. Acceptance on the build box:
   - 1 h run with hourly history (as in Phase 0) under a **debug build** (`-O0 -g -fcheck=all
     -finit-real=snan -ffpe-trap=invalid,zero,overflow`) of NEMS.x: report whether it traps and
     where. Do not paper over traps; if one is in code that ifort also executes benignly (e.g. a
     masked-out NaN), say so with the line.
   - 3 h smoke run (TDFI, 4x7 compute + 1x4 write) with the optimised build, **run twice**; the two
     runs' history files must be bit-identical (`cmp`). Report wall time next to the x86 969 s.
   - UPP on the smoke output; `wgrib2 -stats` on PRMSL sane.
5. **Validation run:** the 2026-11-01 00Z case, 84 h, on **one c8g.8xlarge Spot runner** from an
   arm64 bundle (`s3://nam-recast-617711905691/runner/bundle-<date>-arm64.tar`), **restarts off**
   (`RESTMIN` beyond the run length and no f00 restart) so it fits 64 GB; log memory as in Phase 0.
   If it OOMs anyway, rerun on m8g.8xlarge Spot and say so. Output to
   `s3://nam-recast-617711905691/cases/2026110100/recast-arm64/{grib2,logs}/` (history only while
   posting, then delete). Inputs (GFS, bocos, IC) already exist in S3 and in the x86 bundle; NPS may
   be rerun on arm64 so that the whole chain is arm64, in which case say whether the nemsinterp
   output matches the x86 one.
6. `run/compare.py`: add a source `arm` (`<case>/recast-arm64/grib2/...`) and emit, for the same
   fields and leads as Phase 0, RMSE/bias of **arm vs x86**, **arm vs archived NAM**, and **x86 vs
   archived NAM** (the last from Phase 0, recomputed). Figures as 4-panel rows (arm | x86 | NAM | GFS)
   for MSLP/Z500/T2m at f24/f48/f84. Expect roundoff differences at f00 growing to tenths of hPa/K
   by f84, within the x86-vs-NAM error. If arm-vs-x86 is as large as x86-vs-NAM, something is
   wrong (endianness, kinds, uninitialised variable): find it before reporting.
7. `docs/graviton-port.md`: what changed, what broke, the ESMF outcome, the debug-build result, the
   bit-reproducibility result, timing (s per forecast hour arm vs x86, NPS and UPP times), peak
   memory, Spot price paid and cost per 84 h run on c8g vs the Phase 0 r7a, the comparison table,
   and your recommendation (port good enough to make arm64 the default runner, or not, and why).
8. Binaries + MANIFEST to `s3://nam-recast-617711905691/build/<date>-arm64/exec/`; bundle to
   `runner/`; `deploy/04-run-case.sh` gains an `ARCH=arm64` path (default stays x86).
9. Commits in `~/projects/nam-recast` as you go, small, each explaining why. Author is already
   configured (Joe). Never `git add -A`; add named paths. Append the Co-Authored-By line as set
   for this session.

## Rules
- Budget: **$15** for this brief (box time + Spot run + S3). Phase 0 costs are in `docs/run-notes.md`
  for reference. If you are about to exceed it, stop and report.
- **Stop the arm build box whenever you wait on something longer than ~20 min** (Spot run,
  thinking); the stop script is yours to write first. Terminate every Spot runner you launch when
  it is done or dead; leave no open Spot requests.
- Time: if ESMF + NEMS do not build on arm64 after ~6 h of box time in total, stop, commit what you
  have, write the doc with the blocker, and report. Do not bail silently.
- Do not touch anything outside `~/projects/nam-recast`, the `nam-recast-617711905691` bucket and
  the `nam-recast*` instances. Never the x86 box, never other projects' buckets or instances.
- Do not spoof user agents or work around access controls anywhere.
- Report in plain text: what works, what does not, the numbers, the surprises, the cost.

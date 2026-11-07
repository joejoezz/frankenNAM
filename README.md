# FrankenNAM (nam-recast)

The retired 12 km NAM, re-run from its own code on AWS. Site, maps and free grids for the re-run cases:
https://nam.theconvergencezone.com. Not produced by NOAA and not affiliated with NOAA. Code written for this
project is Apache-2.0 (LICENSE); everything else keeps its own terms (NOTICE).

Re-running the retired 12 km NAM (NMMB core, NAM v4.2 physics) as a cold-start recast on
AWS. Scoping, costs and hurdles: [docs/scoping.md](docs/scoping.md). Phase 0 (approved
3 Nov 2026): obtain the source, build NPS + NMMB + UPP on x86, run one archived case.

## Where the source is

NCO removed `nwprod/nam.v4.2.14/` on 3 Nov 2026, the day the model was retired. The
complete tree (minus `fix/`) survives in two public GitHub repos by the NAM developers:
`MatthewPyle-NOAA/NAM` (v4.2.11 re-release, Feb 2025; primary) and
`EricRogers-NOAA/nam_wcoss2_rocoto` (2022, with WCOSS2 build logs and Rocoto XML).
Git bundles of both: `s3://tcz-backups-617711905691/nam-recast/upstream/`.
`fix/` files were recovered from Wayback captures of nam.v4.2.9-11.

Build on Linux only: the trees contain both `foo.F90` and preprocessed `foo.f90`, which
collide on macOS.

## Layout

- `deploy/01-build-box.sh` creates/starts the x86 build instance; `deploy/02-stop.sh` stops it;
  `deploy/05-graviton-box.sh` / `deploy/06-stop-arm.sh` do the same for the arm64 (c8g) box;
  `deploy/04-run-case.sh` launches a Spot runner for a case (`ARCH=arm64` for Graviton).
- `build/` the toolchain, library and model build scripts (Intel oneAPI on x86, gfortran +
  OpenMPI on arm64, picked by `TOOLCHAIN` in `build/versions.sh`); patches in `build/patches/`.
- `run/` the recast driver (NPS, NEMS.x, UPP), runner, bundle, acceptance and comparison scripts.
- `docs/` scoping, build notes (`build-notes.md` x86, `graviton-port.md` arm64), run notes,
  briefs and the case comparison.

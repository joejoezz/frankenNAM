# nam-recast

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

- `deploy/01-build-box.sh` creates/starts the x86 build instance; `deploy/02-stop.sh` stops it.
- `docs/` scoping and build notes.

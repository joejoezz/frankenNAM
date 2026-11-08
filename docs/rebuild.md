# Rebuilding the model binaries (arm64)

You only need this to change model code, flags or patches. Running a case does not need a build
box: `deploy/04-run-case.sh` starts a Spot runner from the newest `runner/bundle-*-arm64.tar`.

The build box (`nam-recast-build-arm`) was terminated on 21 Nov 2026 to stop paying for its disk.
Everything needed to recreate it is in S3 and in this repository.

## What a rebuild depends on

| Item | Where | Note |
|---|---|---|
| NAM source (MatthewPyle-NOAA/NAM @ 83df4e1) and the Rocoto workflow | `s3://tcz-backups-617711905691/nam-recast/upstream/*.bundle` | git bundles; NCEP's copy is gone |
| Compiled library stack (22 libraries incl. ESMF 7.1.0r) and static files | `/opt/nam/libs` and `/opt/nam/fix` inside the newest `s3://nam-recast-617711905691/runner/bundle-*-arm64.tar` | **Keep at least one arm64 bundle.** It is the seed and the runner image |
| Static files recovered from web archives | `s3://nam-recast-617711905691/fix/wayback/` | the source the bundle's `/opt/nam/fix` was built from |
| Build scripts and patches | this repository (`build/`), cloned on the box from GitHub | library sources are fetched from GitHub at the tags in `build/versions.sh` |

## Fast path (about 25 min, about $0.60)

From the laptop:

```bash
deploy/05-graviton-box.sh          # c8g.8xlarge on-demand; SEED=1 is the default
```

The user-data installs packages, restores the NAM source, clones this repository to `~/frankenNAM`,
and unpacks `/opt/nam/libs` and `/opt/nam/fix` from the newest arm64 bundle
(`build/seed_from_bundle.sh`). It is done when `/opt/nam/READY` exists. Then on the box:

```bash
cd ~/frankenNAM
build/build_all.sh                 # gnu on arm64; libs.sh finds the .built stamps and skips every library
build/manifest.sh "$(git rev-parse --short HEAD)"   # binaries, logs, MANIFEST -> s3://.../build/<date>-arm64/
BUNDLE_TAG=tm06 run/bundle.sh      # -> runner/bundle-<date>-tm06-arm64.tar (launch.sh picks the newest)
```

Back on the laptop: `deploy/06-stop-arm.sh`, then a short check run, for example
`run/launch.sh 2026110100 tm06 arm64 FHMAX=12 S3SUB=rebuild-check`, before trusting the new
bundle for a full case. The runner copies any missing GFS and NAM-archive inputs from the NOAA
buckets itself, so no staging is needed (the case folders were deleted on 7 Nov 2026). Terminate the box when done (its 150 GB disk costs $12 a month even when stopped).

Expected times on c8g.8xlarge:
- boot, apt and source restore: about 5 min;
- seeding from the bundle: about 3 min;
- NPS, NEMS and UPP: about 10 min;
- bundle upload: about 3 min.

## Full path (libraries from source, about 35 min)

Use this when a library version, compiler or flag changes, or no arm64 bundle exists:

```bash
SEED=0 deploy/05-graviton-box.sh   # unpacks /opt/nam/fix only
```

Then the same commands on the box. `libs.sh` clones each library at its pinned tag and applies
`build/patches/esmf-*`, `bufr-*` (ESMF 7.1 alone is about 3 min on 32 Graviton cores). Wall times
for the x86 equivalent are in `docs/build-notes.md`; arm64 porting notes are in
`docs/graviton-port.md`.

If there is no bundle at all, build `/opt/nam/fix` by syncing `s3://nam-recast-617711905691/fix/wayback/`
into `/opt/nam/fix` and check it against the file list in `docs/build-notes.md`. This path has not
been rehearsed.

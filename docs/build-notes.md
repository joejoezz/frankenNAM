# Phase 0 build notes: NPS + NMMB (NEMS) + UPP on AWS x86

Status, 4 Nov 2026: **all target executables build and link on Ubuntu 24.04 x86_64 with Intel
oneAPI 2024.2 classic `ifort` + Intel MPI.** `NEMS.x` starts and aborts asking for its
configure file (`model_configure`); no executable has an unresolved shared library from a
plain shell. No forecast has been run (next brief).

Build box: c7a.8xlarge (32 vCPU AMD Genoa, 64 GB), Ubuntu 24.04. Upstream:
MatthewPyle-NOAA/NAM `main` @ `83df4e13c115d197db67b972cb3befec8511291a` (NAM v4.2.11 re-release).

## How to build

```
# on a clean Ubuntu 24.04 x86_64 box with the upstream tree at /opt/nam/upstream/MatthewPyle-NOAA-NAM
build/build_all.sh        # toolchain.sh (sudo apt), libs.sh, build_nps.sh, build_nems.sh, build_upp.sh, acceptance.sh
build/manifest.sh <commit> # MANIFEST + executables + logs -> s3://nam-recast-617711905691/build/<date>/
```

Every stage is idempotent (libraries carry a `.built` stamp in their prefix; source patches
are skipped if already applied). The upstream tree is copied once to `/opt/nam/work/src`
(`rsync`, no `.git`) and only that copy is patched/built. Binaries land in `/opt/nam/work/exec`,
logs in `/opt/nam/work/logs`.

| Script | What it does |
|---|---|
| `build/versions.sh` | every pinned version and path |
| `build/env.sh` | sources oneAPI, sets `CC=icx FC=ifort`, `I_MPI_F90=ifort I_MPI_CC=icx I_MPI_CXX=icpx`, and exports hpc-stack style variables (`G2_LIB4`, `W3NCO_LIBd`, `NEMSIO_INC`, `ESMFMKFILE`, ...) that the upstream makefiles expect from WCOSS2 `module load` |
| `build/toolchain.sh` | apt packages + oneAPI 2024.2 + an `ld.so.conf.d` entry for the Intel runtime/MPI |
| `build/libs.sh` | the library stack under `/opt/nam/libs/<name>-<ver>` |
| `build/build_nps.sh` | NPS dmpar (geogrid, ungrib, metgrid, nemsinterp) + serial metgrid/ungrib, as upstream `nam_nps.fd/sorc/build.sh` |
| `build/build_nems.sh` | NEMS.x via `gmake nmm` with `build/nems/configure.nems.awsx86.intel` |
| `build/build_upp.sh` | `ncep_post` (makefile_module) and `nam_post0` |
| `build/patches/*.patch` | patches, first line of each is the reason |

## Wall time (clean rebuild from the committed scripts, 32 vCPU)

| Stage | Time |
|---|---|
| toolchain (apt, oneAPI already cached on this box; a cold install took ~2 min) | 2 s |
| libraries, all 22 incl. ESMF | 550 s (ESMF alone 289 s) |
| NPS (dmpar + serial passes) | 136 s |
| NEMS.x (`gmake nmm J=-j8`) | 160 s |
| UPP (`ncep_post` + `nam_post0`, serial make) | 199 s |
| **total** | **1047 s (17.5 min)** |

Whole session including the debugging described below: about 1.2 h of box time (03:46-04:56 UTC), roughly $2.

## Toolchain and libraries that worked

- Intel oneAPI apt packages `intel-oneapi-compiler-fortran-2024.2` (2024.2.3-35, reports
  `ifort (IFORT) 2021.13.3`), `intel-oneapi-compiler-dpcpp-cpp-2024.2` (icx/icpx 2024.2.1),
  `intel-oneapi-mpi-devel-2021.13` (2021.13.1-767). The 2024 C/C++ packages have **no
  `icc`/`icpc`**; C and C++ go through clang-based `icx`/`icpx` (`mpiicc`/`mpiicpc` with
  `I_MPI_CC=icx I_MPI_CXX=icpx`). `mpiifort` calls `ifort` (its `-v` banner says "mpiifx", ignore it).
- Libraries, all at the `versions/build.ver` pins, from GitHub:

| Library | Version | Source / notes |
|---|---|---|
| zlib | 1.2.11 | madler/zlib |
| libpng | 1.6.37 | glennrp/libpng, static |
| jasper | 2.0.25 | jasper-software/jasper, static, no libjpeg |
| HDF5 | 1.10.6 | serial, `--enable-hl`, no Fortran (WCOSS2 had a parallel build; nothing here needs it) |
| netCDF-C / netCDF-Fortran | 4.7.4 / 4.5.3 | serial, no DAP |
| bacio, sp, ip, w3nco, w3emc | 2.4.1, 2.3.3, 3.3.3, 2.4.1, 2.9.1 | NOAA-EMC/NCEPLIBS-* |
| g2, g2c, g2tmpl | 3.4.5, 1.6.4, 1.10.0 | NCEPLIBS |
| sigio, sfcio, gfsio, nemsio | 2.3.2, 1.4.1, 1.4.1, 2.5.2 | NCEPLIBS (nemsio with `mpiifort`) |
| bufr | 11.5.0 | NCEPLIBS-bufr tag `bufr_v11.5.0`, patched (tests) |
| crtm | 2.3.0 | NOAA-EMC/EMC_crtm `v2.3.0` |
| wrf_io, landsfcutil | 1.2.0, 2.4.1 | NCEPLIBS |
| ESMF | **7.1.0r** | esmf-org/esmf `ESMF_7_1_0r`, `ESMF_COMM=intelmpi ESMF_COMPILER=intel ESMF_NETCDF=split`, two patches + C++ flags |

ESMF 7.1.0r was kept (no need for 8.x), so NEMS uses the same `ESMFVersionDefine_ESMF_630rAPI.h`
as WCOSS2.

## What broke and what was changed

### ESMF 7.1.0r (the only component that needed real porting)
All four problems come from `icpc` being gone: `icpx` is clang with C++17 default and uses the
system GCC 13 libstdc++.
1. `register` storage class is an error in C++17 (Zoltan `dr_util.c`, compiled as C++);
   C++11 narrowing in brace initialisers is an error in clang (`ESMCI_Mesh_Regrid_Glue.C` etc.).
   Fix: `ESMF_CXXCOMPILEOPTS="-std=gnu++11 -Wno-c++11-narrowing -Wno-register"` (flags only).
2. The bundled Trilinos Sacado headers re-export their templated `min`/`max` into `namespace
   std`; GCC 13's `<unordered_map>` calls `std::min<size_t>(...)`, which then instantiates
   `Sacado::Fad::Expr<unsigned long>` and fails hard. Patch
   `esmf-01-sacado-std-minmax.patch` keeps min/max inside Sacado (atan2/pow re-exports kept).
3. Link: `libesmf.so` had an undefined `MeshObjConn::common_objs<vector iterator>`; its
   explicit instantiation is behind `#ifdef __INTEL_COMPILER`, which icpx does not define
   (it defines `__INTEL_LLVM_COMPILER`). Patch `esmf-02-icx-explicit-instantiation.patch`.
4. `ESMF_XERCES=OFF` *enables* XML support (any value turns it on) and then fails on missing
   xerces headers; the variable must be unset.

Runtime caveat to keep in mind: clang warns that ESMF's `if (this == NULL)` defensive checks may
be folded away. They only matter for calls on invalid objects (error paths), not for a correct run.

### NEMS / NMMB
**No source changes.** `build/nems/configure.nems.awsx86.intel` is `configure.nems.wcoss2` with
`ftn` replaced by `mpiifort` and `-diag-disable=10448` (ifort deprecation remark) added; same
`-O3 -march=core-avx2 -mtune=core-avx2 -fp-model precise -convert big_endian -init=zero -qopenmp`.
`-march=core-avx2` (unlike `-xCORE-AVX2`) has no GenuineIntel runtime check, so it runs on Genoa.
`build_nems.sh` does what `./configure wcoss2` does (copy conf, touch externals, copy the 6.3.0r
API version header) and runs `gmake nmm`. Warnings are only the usual long-name / deprecated
directive ones. GSM/FIM/GEN are compiled as stubs exactly as on WCOSS2.

### NPS
No source changes. The Makefiles link `-L$(NETCDF_LIB) -lnetcdf`, relying on the Cray `ftn`
wrapper to add `-lnetcdff`; `build_nps.sh` sets `NETCDF_LIB="<dir> -Wl,-rpath,... -lnetcdff"` so the
existing link line expands correctly. `COMP_MP=mpiifort COMPILER=ifort C_COMP=icx C_COMP_MP=mpiicc`
replace the Cray wrappers. Note the NPS `make` runs with `-i` (errors ignored); the script checks
that each `.exe` exists rather than trusting make's exit status.

### UPP
No source changes. `makefile_module` and the `nam_post0` makefile hardcode `FC=ftn`; the scripts
override `FC` on the make command line with the flags from `modulefiles/post/v7.0.0-wcoss2`, use
`/lib/cpp -P -traditional` for the `.F` preprocessing, and override `NETCDF_LDFLAGS` to add rpaths.

### Library-stack issues
- `bufr` 11.5.0 always builds `test/`, which downloads data from a URL that now returns 404.
  Patch `bufr-01-optional-tests.patch` puts it behind `ENABLE_TESTS` (off).
- icx is strict about pre-C99 code; library C builds get
  `-Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=int-conversion
  -Wno-error=incompatible-function-pointer-types`.
- A scripting trap worth remembering: `( set -e; f ) || handler` does **not** stop on errors
  inside `f` (bash disables `set -e` in a `||` context). The first library pass "succeeded" with
  ESMF and bufr broken. `libs.sh` now runs each stage as a background subshell and checks `wait`.

## Things that matter for the Dockerfile

- Base `ubuntu:24.04` (x86_64). Install exactly the three oneAPI 2024.2 / MPI 2021.13 packages
  above; 2025+ toolkits have no `ifort`. Pin the apt versions; Intel's repo still serves 2024.2.
- Add `/etc/ld.so.conf.d/nam-intel-oneapi.conf` with `/opt/intel/oneapi/compiler/2024.2/lib`,
  `/opt/intel/oneapi/mpi/2021.13/lib`, `/opt/intel/oneapi/mpi/2021.13/opt/mpi/libfabric/lib`
  and run `ldconfig`. Without it `libesmf.so`/`libnetcdf.so` cannot find `libimf`, `libsvml`,
  `libiomp5`, `libintlc`, `libifcoremt` (RUNPATH is not inherited by a library's own deps).
  `toolchain.sh` does this.
- A runtime image only needs: the Intel compiler runtime + Intel MPI runtime (`intel-oneapi-runtime-*`
  packages or the two lib dirs copied), `/opt/nam/libs/{esmf,netcdf,hdf5}` shared libs, and
  `/opt/nam/work/exec`. Everything else (NCEPLIBS, jasper, png, zlib) is linked statically.
- Multi-stage build: compile stage ~15 min on 32 vCPU from source; layer the library stack
  separately from the NAM tree so code changes do not rebuild ESMF.
- The upstream tree must be copied on a case-sensitive filesystem (it holds both `foo.F90` and
  `foo.f90`); `docker build` from a macOS checkout would corrupt it. Clone/rsync inside Linux.
- The Intel MPI runtime will need `I_MPI_FABRICS=shm:ofi` / `FI_PROVIDER=tcp` (or `efa`) settings
  when the forecast runs; not exercised yet.

## Executables

| Built here | Upstream `exec/` name | Used by |
|---|---|---|
| `NEMS.x` | `nam_nems_nmmb_fcst` | `exnam_fcst.sh` |
| `geogrid.exe` | `nam_geogrid` | `exnam_coldstart_prep*` |
| `ungrib.exe` (dmpar build) | `nam_ungrib` | `exnam_coldstart_prep*` |
| `metgrid.exe` (dmpar) | `nam_metgrid` | `exnam_coldstart_prep*` |
| `nemsinterp.exe` (dmpar) | `nam_nemsinterp` | coldstart prep, `exnam_nemsinterp_boco*` |
| `metgrid_serial.exe` | `nam_metgrid_boco` | `exnam_metgrid_boco.sh` |
| `ungribs.exe` | `nam_ungrib_boco` | `exnam_ungrib_boco.sh` |
| `ncep_post` | `nam_ncep_post` | `exnam_post*.sh` |
| `nam_post0` | `nam_post0` | `exnam_post*.sh` (BUFR profile prep) |

No `ungribp` exists in this NPS tree; the scripts only use `nam_ungrib` and `nam_ungrib_boco`.

## Not built (Phase 0 skip list) but called by the workflow

- `nam_land_utilities.fd` (`emcsfc_*`): `emcsfc_coldstart` is called by
  `exnam_coldstart_partialcyc*`, `emcsfc_sst2mdl/snow2mdl/ice2mdl/sfcupdate` by
  `exnam_sfcupdate*`, `emcsfc_gridgen_sfc` by the nest prep. The parent-only cold start
  (`exnam_coldstart_prep.sh`) does not call them, but land-state cycling (Phase 1) does.
- `nam_sndp`, `nam_stnmlist` (BUFR soundings, `exnam_postsnd/profile`), `nam_makeprecip`,
  `nam_icwf` (prdgen) and the rest of `sorc/Makefile`'s SUBDIRS0.
- `util/exec/` ships prebuilt WCOSS2 binaries only (`wgrib2`, `cwordsh`, `tocsbufr`,
  `fbwndtrx`, `bulls_fdwndtrx`, `nam32tx`, `grb_to_bin.x`, `grid_to_grb.x`, `setfirewx`);
  `cwordsh`/`tocsbufr` sit on the BUFR-sounding path and need rebuilding from NCEPLIBS-bufr /
  prod_util sources; `wgrib2` can come from apt/source.

## Artifacts

`s3://nam-recast-617711905691/build/2026-11-04/exec/` holds the executables and `MANIFEST`
(name, size, sha256, `ldd`, upstream commit, build-script commit); `.../logs/` holds every build log.

## x86 build box retired (5 Nov 2026)

The Phase 0 x86 box (i-0ab3bbee9ba7068e7) was terminated with its 300 GB disk to save $24/month; arm64 is the default runner. The x86 fallback is kept as artifacts: `s3://nam-recast-617711905691/build/2026-11-04/` (binaries, logs, MANIFEST) and `runner/bundle-20261104.tar` (11.6 GB). To rebuild: `deploy/01-build-box.sh`, then `build/build_all.sh` (about 18 min clean).

## nemsinterp wrote total soil water into the IC's sh2o (found 6 Nov 2026, patch nps-02)

`output_nemsinit.F90` (SH2O loop, line 1773) copied `grid%smc` instead of `grid%sh2o`, so the IC's
liquid soil water equalled total soil water everywhere and the Flerchinger split that `NMM_SH2O`
(module_assorted_definitions.F90:824) computes from STC+SMC was thrown away. NMMB reads `sh2o` from the IC,
so every cold start began with zero soil ice (Phase 1 frozen-soil defect). `build/patches/nps-02-nemsinterp-write-sh2o.patch`
fixes it; the seed needs no SOILL. IC check, case 2026012312, cold land (layer-1 STC < 271 K) frozen share
1 - sh2o/smc, 0-10 / 10-40 cm (`run/ic_frozen.py`): unpatched 0.000 / 0.000; patched tm06 (NAM seed) 0.673 / 0.590
against the archived NAM analysis 0.669 / 0.593 (grid 218, SOILL/SOILW); patched anl (GFS only) 0.656 / 0.524.

Check run (6 Nov 2026, `verify/check_ice.py`; bundle `runner/bundle-20261106-tm06-arm64.tar`, c8g Spot, FHMAX=12, prefix `cases/2026012312/check-ice/`): NMMB keeps the ice.
Frozen share over cold land (0-10 / 10-40 cm), NAM / patched / old: f00 0.664/0.576, 0.671/0.578, 0.047/0.006; f03 0.661/0.568, 0.666/0.568, 0.074/0.010; f06 0.656/0.569, 0.658/0.563, 0.087/0.013.
Versus the archived NAM, patched (old) f00/f06: 0-10 cm TSOIL bias land +0.29/+0.27 C (+0.99/+0.99); 2 m T bias land +0.93/+0.34 K (+0.58/+0.21). Soil temperature is fixed; the 2 m T bias did not improve (slightly warmer) in the first hours.

f84 check (6 Nov 2026, case 2026012312, prefix `cases/2026012312/check-ice-f84/`, c8g Spot, 5 h 25 min, no reclaim): with nps-02 the pooled 12-84 h CONUS station 2 m T RMSE/bias is 3.04/+1.12 K (old 3.42/+1.60, NAM 3.01/+1.14), Td 3.47/+0.59 (old 3.69/+1.13, NAM 3.21/+0.85), wind 2.07/+0.49 (old 2.08/+0.51, NAM 2.05/+0.47). Grid to grid against the NAM 2 m T RMSE 1.02 K (old 1.34), bias 0.00 (old +0.52). Frozen share stays at the NAM's through f84 (0.582 vs 0.582; old 0.459). Tables: `verify/results/check-ice-f84/score_f84.md`, script `verify/score_f84.py`.

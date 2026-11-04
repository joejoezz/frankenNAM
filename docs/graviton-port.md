# Graviton (arm64, gfortran + OpenMPI) port of NPS + NEMS.x + UPP

Status, 4 Nov 2026: **the whole FrankenNAM stack builds and runs on AWS Graviton (aarch64) with
gfortran 13.3 + OpenMPI 4.1.6 from Ubuntu 24.04 apt**, with the same library pins as Phase 0 and
ESMF 7.1.0r (no move to 8.x). The sections below record what changed, what broke, the acceptance
results, timing/memory/cost against the x86 Phase 0 numbers, the arm-vs-x86-vs-NAM comparison and
the recommendation. Build box: c8g.8xlarge on-demand (32 Graviton4 / Neoverse-V2 cores, 64 GB),
`deploy/05-graviton-box.sh`; binaries are compiled with `-mcpu=neoverse-v1` so they also run on
Graviton3 (c7g/m7g).

## How to build / run (what is new)

- `build/versions.sh` picks `TOOLCHAIN=gnu` on aarch64 (`intel` on x86_64; override with
  `TOOLCHAIN=gnu` on x86 to test the GNU path). `build/env.sh` exports `CC/FC/MPIFC`, the
  GCC >= 10 relaxations (`GNU_LEGACY_FFLAGS`) and `ARCH_FLAGS=-mcpu=neoverse-v1` for it.
- `build/toolchain.gnu.sh` (apt: gfortran-13, openmpi-bin, libopenmpi-dev, ...) replaces
  `toolchain.sh` on the GNU path; `build/build_all.sh` chooses.
- `build/nems/configure.nems.awsarm.gnu`, `build/nps/configure.nps_awsarm_gnu_{dmpar,serial}`:
  the GNU configure files; `build_upp.sh` passes the GNU flags on the make command line.
- `run/recast.sh` picks Intel MPI or OpenMPI by what is installed (`mpi_cmd`), `run/runner.sh`
  has `NO_RESTART=1` (RESTMIN past the run, no f00 restart, no last restart) and `S3SUB`,
  `run/bundle.sh` makes the runner tar, `deploy/04-run-case.sh ARCH=arm64` launches a c8g Spot
  runner from it.

## Flag mapping (WCOSS2 Intel -> gfortran)

| Intel (WCOSS2 / Phase 0) | gfortran | Note |
|---|---|---|
| `-init=zero` | `-finit-local-zero` | NEMS relies on zeroed locals; also added to NPS (see ungrib below) |
| `-fp-model precise` / `strict` / `source` | nothing (`-O3`/`-O2`, **no `-ffast-math`**) | gfortran never reassociates or flushes denormals without -ffast-math; FMA contraction is on by default on both compilers |
| `-r8` | `-fdefault-real-8 -fdefault-double-8` | keeps DOUBLE PRECISION at 8 bytes, as `-r8` does |
| `-convert big_endian` | `-fconvert=big-endian` | |
| `-assume byterecl` | default | RECL in bytes |
| `-fpp` / `-free` / `-fixed` / `-FR` | `-cpp` / `-ffree-form` / `-ffixed-form` | UPP's makefile hardcodes `FREE=-FR`, overridden |
| `-qopenmp -auto` | `-fopenmp` | |
| `-traceback -g` | `-fbacktrace -g` | |
| `-march=core-avx2 -mtune=core-avx2` | `-mcpu=neoverse-v1` | Graviton3 ISA (SVE); runs on c7g/m7g/c8g/m8g |
| (none) | `-fallow-argument-mismatch -fallow-invalid-boz -fno-range-check -ffree-line-length-none` | GCC >= 10 rejects the MPI buffer type/rank mismatches a 2017 code is full of |
| debug: `-ftrapuv -fpe0 -check all` | `-O0 -g -fcheck=all,no-array-temps -finit-real=snan -ffpe-trap=invalid,zero,overflow` | `DEBUG=on` in the NEMS configure; `array-temps` only prints warnings |

## What broke and how it was fixed (every patch is in `build/patches/`, first line = why)

### ESMF 7.1.0r (kept; no 8.x needed)
Three new patches on top of the Phase 0 ones (`esmf-01` Sacado std::min/max and `esmf-02`
Intel-only explicit instantiation still apply/are harmless):
1. `esmf-03-gfortran-conf-stddef.patch`: `build_config/Linux.gfortran.default/ESMC_Conf.h`
   typedefs `size_t` without `<stddef.h>`; GCC 13's libstdc++ no longer includes it
   transitively, so every C++ file failed.
2. `esmf-04-aarch64-pointer-size.patch`: `ESMC_POINTER_SIZE` is derived from the ABI string
   macro (`Sx86_64_small`, `Sia64_64`, ...); on aarch64 `common.mk` leaves the plain `S64`, which
   the header does not know, and `ESMF_FortranWordsize` fails. Defined for `S64` (8 bytes).
3. `esmf-05-mpi3-removed-functions.patch`: OpenMPI 4.x no longer declares the MPI-1 functions
   removed in MPI-3.0 (`MPI_Address`, `MPI_Type_struct`, `MPI_UB`, `MPI_Attr_get`); Intel MPI still
   does, which is why Phase 0 never saw it. Only two compiled files use them: Zoltan's
   `par_bisect.c` (bisector struct type, rewritten with `MPI_Get_address` /
   `MPI_Type_create_struct` / `MPI_Type_create_resized`, same extent) and `ESMCI_VMKernel.C`
   (`MPI_Attr_get` -> `MPI_Comm_get_attr`). MPICH 4.2 from apt was checked as the alternative the
   brief allows: its `mpi.h` lacks the same symbols, so the patch is needed either way and OpenMPI
   stays.
Flags: `ESMF_COMPILER=gfortran ESMF_COMM=openmpi ESMF_ABI=64`,
`ESMF_CXXCOMPILEOPTS="-std=gnu++11 -Wno-narrowing -Wno-register"` (same two C++17 problems as
icpx in Phase 0), `ESMF_F90COMPILEOPTS` = the GCC relaxations. Build time 173 s on 32 cores
(x86 oneAPI: 289 s).

### NEMS / NMMB
- `nems-01-barrier-before-finalize.patch` kept (Phase 0; harmless under OpenMPI).
- `nems-02-co2hc-parameter-array-section.patch`: `co2hc.f` (IDEA/WAM physics, compiled into
  libphys but never called by the NMM core) passes `xvic0(51)`, an element of a PARAMETER array,
  to `splin2`'s explicit-shape dummy through an INTERFACE block; gfortran treats an element of a
  named constant as a scalar constant and rejects the rank mismatch even with
  `-fallow-argument-mismatch`. `xvic0(51:)` is the same sequence.
- Configure: `F77 = mpif90 ...` had to be defined. `atmos/nmm/makefile` compiles the
  `n_*.f` GFS-definition modules with `$(F77)`, which no WCOSS2 configure defines;
  `n_module_gfs_mpi_def.f` includes `mpif.h`, and ifort found it through setvars' `CPATH`.
- Everything else compiled with warnings only (type/rank mismatches downgraded by
  `-fallow-argument-mismatch`). NEMS.x links in about 4 min of wall time on 32 cores (x86: 160 s).

### NPS
- `nps-01-edition-num-g2-gbytec.patch`: ungrib's `edition_num` read the GRIB discipline and
  edition bytes with `gbyte()`, which resolves to **w3nco's integer-word unpacker**; that routine
  assumes big-endian word layout and returns the reserved bytes (0) on this little-endian
  machine, so every GFS file was treated as neither GRIB1 nor GRIB2 and ungrib wrote nothing. g2's
  `g2_gbytec` is byte based and endian independent (WPS made the same change). Open question:
  the x86 binary links the same `gbyte_` and worked; not investigated further because the fix is
  right regardless, and the x86 box stays stopped.
- `-finit-local-zero` added to all NPS compiles (Intel's NPS flags did not have `-init=zero`):
  with the edition fixed, ungrib found all 696 fields of a GFS file, matched them against the
  Vtable, stored them, and still wrote no intermediate file ("Data not found"). `-O0` does not
  change that; `-finit-local-zero` does, so an uninitialised local in the ungrib output path is
  involved (ifort's stack happened to hold zero). `-Wmaybe-uninitialized` points only at
  `earth_radius` (rd_grib2), `iskip` and `gribsize` (GRIB1 code); the exact variable was not
  pinned down within this brief.
- Serial `ungribs`/`metgrid_serial`, dmpar `geogrid/ungrib/metgrid/nemsinterp` otherwise build
  unchanged (150 s).

### UPP
- `uppgnu-01-timef.patch` (GNU path only): `WRFPOST.f` times its phases with `timef()`, an Intel
  libifport portability routine gfortran lacks; a `system_clock` replacement with the same
  semantics (seconds since the first call, REAL(8)). `ncep_post` and `nam_post0` then link
  (97 s).

### Libraries
All 21 NCEPLIBS/netCDF/HDF5/jasper/png/zlib builds went through with gfortran unchanged apart
from the generic GNU flags (`-fcommon` for the C, the mismatch relaxations for the Fortran);
the stack without ESMF took about 4 min.

### UPP, second problem (found by the smoke-test post)
- `uppgnu-02-null-pointer-size.patch`: `gengrb2msg` takes `size()` of the POINTER components
  `level2`, `scale_fact_fixed_sfc2`, ... of `param_t`, which are `=> null()` for parameters whose
  `post_avblflds.xml` entry lacks them. `size()` of a disassociated pointer is undefined; ifort's
  zeroed descriptor returns 0 and the code relies on it, gfortran dereferences it and `ncep_post`
  segfaults (`grib2_module.f:704`, rank 13, after the CIN/PLPL/LTNG fields). A null-safe
  `psize()` generic replaces the calls (GNU path only).

## Acceptance on the build box (c8g.8xlarge, 32 cores, `run/smoke.sh`)

| Check | arm64 result | x86 Phase 0 |
|---|---|---|
| NPS, 84 h of GFS: ungrib / metgrid / nemsinterp | 351 / 467 / 511 s | 380 / 380 / 479 s |
| nemsinterp IC and bocos vs the x86 files | not bit-identical: median relative difference 1e-7 (IC) to 1e-6 (bocos); the largest absolute differences are 0.52 Pa in the pressure records (~1e5 Pa) and 3.6 in one boco.0000 record; 305 of 488 IC records differ (`run/cmp_nemsio.py`) | - |
| 3 h smoke, TDFI, 4x7 + 1x4, run 1 / run 2 | **829 s / 844 s** (exit 0) | 969 s |
| history files run 1 vs run 2 (`cmp`) | **bit-identical** (f00 and f03, 4.86 GB each, and the .ctl files) | not tested |
| node memory peak during the smoke (`free`, 30 s) | 43.1 GB used | ~48 GB flat (84 h run) |
| max RSS of a rank (time -v, mpirun tree) | 1.65 GB | 2.2 GB |
| UPP on the smoke output | first attempt segfault (above); after `uppgnu-02` see below | 21 s / file (16 tasks) |
| `wgrib2 -stats` PRMSL f00/f03 | see below | f84 range 969.7-1062.1 hPa |
| 1 h run, hourly history, no filter, **trap build** (`-O0 -g -fcheck=all -finit-real=snan -ffpe-trap=invalid,zero,overflow`) | no floating-point trap; the run aborts 17 s in, while the write (quilt) tasks write the f00 history: `NEMSIO_WRITEREC` returns an error on a 2-D integer record and `module_WRITE_GRID_COMP.F90:4100` prints "Failed to write output to file! Aborting!" (504 MB of the 4.86 GB file written). Nothing in the dynamics/physics had run yet. The write path therefore relies on zero-initialised locals (the brief's trap flags leave integers/logicals uninitialised); a second variant with integers zeroed (`DEBUG_EXTRA=-finit-local-zero`, reals still sNaN) is reported below. | 258 s (optimised) |

Note on the smoke timing: gfortran on Graviton4 is **13 % faster** than ifort on the c7a
(Genoa) build box for this run, the opposite of the 10-25 % slowdown the plan assumed.

## Validation run (84 h, c8g.8xlarge Spot, restarts off)

(filled in below)

## arm vs x86 vs archived NAM

(filled in below)

## Cost

(filled in below)

## Recommendation

(filled in below)

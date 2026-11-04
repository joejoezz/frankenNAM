# NEMS/NMMB configure for AWS arm64 (Ubuntu 24.04, gfortran 13 + OpenMPI 4.1), Graviton port.
# Derived from the tree's conf/configure.nems.Linux.gnu with the WCOSS2 Intel flags mapped:
#   -init=zero            -> -finit-local-zero (the code relies on zeroed locals)
#   -fp-model precise     -> plain -O3 (gfortran never reassociates without -ffast-math)
#   -convert big_endian   -> -fconvert=big-endian
#   -assume byterecl      -> gfortran default (RECL in bytes)
#   -r8                   -> -fdefault-real-8 -fdefault-double-8 (keeps DOUBLE PRECISION at 8 bytes, as -r8)
#   -fpp                  -> -cpp;  -qopenmp -> -fopenmp;  -traceback -> -fbacktrace
#   -march=core-avx2      -> -mcpu=neoverse-v1 (Graviton3 ISA; runs on c7g/m7g and c8g/m8g)
# Added for GCC >= 10: -fallow-argument-mismatch (MPI buffer type/rank mismatches),
# -fallow-invalid-boz, -fno-range-check, -ffree-line-length-none.
# Library paths come from build/env.sh (hpc-stack style variables pointing at /opt/nam/libs).
# DEBUG=on gives the brief's trap build: -O0 -g -fcheck=all -finit-real=snan -ffpe-trap=...
SHELL       = /bin/bash

include       $(ESMFMKFILE)

ESMF_INC    = $(ESMF_F90COMPILEPATHS)
ESMF_LIB    = $(ESMF_F90LINKPATHS) $(ESMF_F90LINKRPATHS) $(ESMF_F90ESMFLINKLIBS)

gfs=gsm
gfsdir=atmos/$(gfs)

NETCDF_INC  = $(NETCDF_INCLUDE)
NETCDF_LIB  = $(NETCDF_LDFLAGS)

W3_LIB      = ${W3NCO_LIBd} ${W3EMC_LIBd}
BACIO_LIB   = ${BACIO_LIB4}
SP_LIB      = ${SP_LIBd}

EXTLIBS     = $(NEMSIO_LIB) \
              $(W3_LIB) \
              $(BACIO_LIB) \
              $(SP_LIB) \
              $(ESMF_LIB) \
              $(NETCDF_LIB)

ARCH_OPT   ?= -mcpu=neoverse-v1
GNU_LEGACY  = -fallow-argument-mismatch -fallow-invalid-boz -fno-range-check -ffree-line-length-none

FC          = mpif90 -g -fbacktrace -fopenmp $(ARCH_OPT) $(GNU_LEGACY)
# atmos/nmm/makefile compiles the n_*.f GFS-definition modules with $(F77) (undefined on WCOSS2,
# where the environment supplied it); give it the same compiler and flags explicitly.
F77         = gfortran -g -fbacktrace -fopenmp $(ARCH_OPT) $(GNU_LEGACY) -fconvert=big-endian

FREE        = -ffree-form
FIXED       = -ffixed-form
R8          = -fdefault-real-8 -fdefault-double-8

FINCS       = $(ESMF_INC) -I$(NEMSIO_INC) $(NETCDF_INC)

ifeq ($(DEBUG),on)
  # no -finit-local-zero here on purpose: reals start as signalling NaN so that any reliance
  # on Intel's -init=zero traps. array-temps is a warning printer, not a check; it is left out.
  TRAPS     = -fcheck=all,no-array-temps -finit-real=snan -ffpe-trap=invalid,zero,overflow
  OPTS_NMM  = -O0
  OPTS_GFS  = -O0
  OPTS_GEN  = -O0
  OPTS_FIM  = -O0
else
  TRAPS     = -finit-local-zero
  OPTS_NMM  = -O3
  OPTS_GFS  = -O3
  OPTS_GEN  = -O2
  OPTS_FIM  = -O2
endif

FFLAGS      = $(TRAPS) $(FINCS) -fconvert=big-endian

FFLAGS_NMM  = $(OPTS_NMM) $(FFLAGS)
FFLAGS_GFS  = $(OPTS_GFS) $(FFLAGS) $(FREE)
FFLAGS_GFSF = $(OPTS_GFS) $(FFLAGS) $(FIXED)
FFLAGS_GEN  = $(OPTS_GEN) $(FFLAGS)
FFLAGS_FIM  = $(OPTS_FIM) $(FFLAGS)

FPP         = -cpp
CPP         = /lib/cpp -P -traditional
CPPFLAGS    = -DENABLE_SMP -DCHNK_RRTM=8

AR          = ar
ARFLAGS     = -r

RM          = rm

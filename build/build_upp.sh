#!/bin/bash
# Build UPP (ncep_post, sorc/nam_nceppost.fd) and nam_post0 (sorc/nam_post0.fd).
# Mirrors upstream build_ncep_post.sh (makefile_module) and build_post0.sh; the makefiles
# hardcode FC=ftn, so the compiler is overridden on the make command line; NETCDF_LDFLAGS is
# overridden to carry rpaths (the makefile's version has none, Cray modules set LD paths).
set -euo pipefail
BUILD_DIR=$(cd "$(dirname "$0")" && pwd)
source "$BUILD_DIR/env.sh"; source "$BUILD_DIR/common.sh"
stage_src
apply_src_patches upp
LOG=$NAM_WORK/logs; t0=$SECONDS

cd "$NAM_SRC/sorc/nam_nceppost.fd/sorc/ncep_post.fd"
make -f makefile_module clean > /dev/null 2>&1 || true
# same flags as modulefiles/post/v7.0.0-wcoss2 (myFCFLAGS), ftn -> mpiifort, cc -> icx; on the
# GNU path -fp-model source -> plain -O3, -FR -> -ffree-form (FREE is hardcoded in the makefile)
if [ "$TOOLCHAIN" = gnu ]; then
  UPP_FC="mpif90 -O3 -fconvert=big-endian -fbacktrace -g -fopenmp -cpp -ffree-line-length-none $GNU_LEGACY_FFLAGS $ARCH_FLAGS"
  UPP_EXTRA=(FREE=-ffree-form CC="gcc -fcommon $ARCH_FLAGS")
  P0_FC="gfortran $GNU_LEGACY_FFLAGS $ARCH_FLAGS"
  P0_EXTRA=(FREE=-ffree-form DEBUG="-g -fbacktrace -fconvert=big-endian")
else
  UPP_FC="mpiifort -O3 -convert big_endian -traceback -g -fp-model source -qopenmp -fpp -diag-disable=10448"
  UPP_EXTRA=(CC=icx)
  P0_FC="ifort -diag-disable=10448"
  P0_EXTRA=()
fi
make -f makefile_module -j"${UPP_J:-1}" \
  FC="$UPP_FC" "${UPP_EXTRA[@]}" myCPP=/lib/cpp myCPPFLAGS="-P -traditional" \
  NETCDF_LDFLAGS="$NETCDF_LDFLAGS" > "$LOG/upp_build.log" 2>&1 || true
[ -x ncep_post ] || { echo "ncep_post NOT BUILT"; grep -nE "error|undefined reference" "$LOG/upp_build.log" | head -40; exit 1; }
cp ncep_post "$NAM_EXEC/ncep_post"

cd "$NAM_SRC/sorc/nam_post0.fd"
make clean > /dev/null 2>&1 || true
make FC="$P0_FC" "${P0_EXTRA[@]}" > "$LOG/post0_build.log" 2>&1 || true
[ -x nam_post0 ] || { echo "nam_post0 NOT BUILT"; grep -nE "error|undefined reference" "$LOG/post0_build.log" | head -40; exit 1; }
cp nam_post0 "$NAM_EXEC/nam_post0"
echo "UPP built in $((SECONDS - t0)) s"
print_versions

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
# same flags as modulefiles/post/v7.0.0-wcoss2 (myFCFLAGS), ftn -> mpiifort, cc -> icx
make -f makefile_module -j"${UPP_J:-1}" \
  FC="mpiifort -O3 -convert big_endian -traceback -g -fp-model source -qopenmp -fpp -diag-disable=10448" \
  CC=icx myCPP=/lib/cpp myCPPFLAGS="-P -traditional" \
  NETCDF_LDFLAGS="$NETCDF_LDFLAGS" > "$LOG/upp_build.log" 2>&1 || true
[ -x ncep_post ] || { echo "ncep_post NOT BUILT"; grep -nE "error|undefined reference" "$LOG/upp_build.log" | head -40; exit 1; }
cp ncep_post "$NAM_EXEC/ncep_post"

cd "$NAM_SRC/sorc/nam_post0.fd"
make clean > /dev/null 2>&1 || true
make FC="ifort -diag-disable=10448" > "$LOG/post0_build.log" 2>&1 || true
[ -x nam_post0 ] || { echo "nam_post0 NOT BUILT"; grep -nE "error|undefined reference" "$LOG/post0_build.log" | head -40; exit 1; }
cp nam_post0 "$NAM_EXEC/nam_post0"
echo "UPP built in $((SECONDS - t0)) s"
print_versions

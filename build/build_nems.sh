#!/bin/bash
# Build the NMMB forecast model (NEMS.x, NMM core only) from sorc/nam_nems_nmmb.fd.
# Mirrors upstream build.sh -> configure wcoss2 -> compile.sh_pll (gmake nmm).
set -euo pipefail
BUILD_DIR=$(cd "$(dirname "$0")" && pwd)
source "$BUILD_DIR/env.sh"; source "$BUILD_DIR/common.sh"
stage_src
apply_src_patches nems

cd "$NAM_SRC/sorc/nam_nems_nmmb.fd/src"
cp "$BUILD_DIR/nems/configure.nems.awsx86.intel" conf/configure.nems.awsx86.intel
# what "./configure wcoss2" does, with our conf file
cp conf/configure.nems.awsx86.intel conf/configure.nems
touch conf/externals.nems
cp ESMFVersionDefine_ESMF_630rAPI.h ESMFVersionDefine.h

if [ "${CLEAN:-1}" = 1 ]; then gmake clean > "$NAM_WORK/logs/nems_clean.log" 2>&1 || true; fi
t0=$SECONDS
gmake nmm J=-j${NEMS_J:-8} 2>&1 | tee "$NAM_WORK/logs/nems_build.log" | grep -E "Error|error #|is created" || true
[ -x ../exe/NEMS.x ] || { echo "NEMS.x NOT BUILT"; exit 1; }
cp ../exe/NEMS.x "$NAM_EXEC/NEMS.x"
echo "NEMS.x built in $((SECONDS - t0)) s"
print_versions

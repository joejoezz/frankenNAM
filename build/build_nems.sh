#!/bin/bash
# Build the NMMB forecast model (NEMS.x, NMM core only) from sorc/nam_nems_nmmb.fd.
# Mirrors upstream build.sh -> configure wcoss2 -> compile.sh_pll (gmake nmm).
set -euo pipefail
BUILD_DIR=$(cd "$(dirname "$0")" && pwd)
source "$BUILD_DIR/env.sh"; source "$BUILD_DIR/common.sh"
stage_src
apply_src_patches nems

cd "$NAM_SRC/sorc/nam_nems_nmmb.fd/src"
if [ "$TOOLCHAIN" = gnu ]; then CONF=configure.nems.awsarm.gnu; else CONF=configure.nems.awsx86.intel; fi
cp "$BUILD_DIR/nems/$CONF" conf/$CONF
# what "./configure wcoss2" does, with our conf file
cp conf/$CONF conf/configure.nems
touch conf/externals.nems
cp ESMFVersionDefine_ESMF_630rAPI.h ESMFVersionDefine.h

if [ "${CLEAN:-1}" = 1 ]; then gmake clean > "$NAM_WORK/logs/nems_clean.log" 2>&1 || true; fi
t0=$SECONDS
# DEBUG=on selects the conf file's trap build (gfortran: -O0 -fcheck=all -finit-real=snan
# -ffpe-trap=...); the result is kept apart as NEMS_debug.x. Always clean when switching.
OUT=NEMS.x; [ "${DEBUG:-off}" = on ] && OUT=NEMS_debug.x
gmake nmm J=-j${NEMS_J:-8} DEBUG=${DEBUG:-off} 2>&1 | tee "$NAM_WORK/logs/nems_build${DEBUG:+_debug}.log" | grep -E "Error|error #|is created" || true
[ -x ../exe/NEMS.x ] || { echo "NEMS.x NOT BUILT"; grep -nE "Error|error" "$NAM_WORK/logs/nems_build${DEBUG:+_debug}.log" | head -30; exit 1; }
cp ../exe/NEMS.x "$NAM_EXEC/$OUT"
echo "$OUT built in $((SECONDS - t0)) s"
print_versions

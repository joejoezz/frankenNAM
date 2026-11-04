#!/bin/bash
# Build NPS (geogrid, ungrib, metgrid, nemsinterp + dio/ncio) from sorc/nam_nps.fd.
# Mirrors upstream nam_nps.fd/sorc/build.sh: a dmpar pass (what exnam_* runs) and a serial
# pass for metgrid/ungrib (nam_metgrid_boco, nam_ungrib_boco).
set -euo pipefail
BUILD_DIR=$(cd "$(dirname "$0")" && pwd)
source "$BUILD_DIR/env.sh"; source "$BUILD_DIR/common.sh"
stage_src
apply_src_patches nps

# what modulefiles/wcoss2/v4.1.0_build exports, with Intel MPI wrappers in place of Cray ftn/cc
export COMP_MP=mpiifort COMPILER=ifort C_COMP=icx C_COMP_MP=mpiicc
# NPS Makefiles link "-L$(NETCDF_LIB) -lnetcdf" and relied on the Cray ftn wrapper to add
# -lnetcdff; put -lnetcdff (and rpaths) into NETCDF_LIB instead of patching four Makefiles.
export NETCDF_LIB="$NETCDF/lib -Wl,-rpath,$NETCDF/lib -Wl,-rpath,$HDF5/lib -lnetcdff"
LOG=$NAM_WORK/logs; t0=$SECONDS
cd "$NAM_SRC/sorc/nam_nps.fd/sorc/NMMB_init/NPS"
./clean -a > "$LOG/nps_clean.log" 2>&1 || ./clean > "$LOG/nps_clean.log" 2>&1 || true
./conf wcoss2 > /dev/null

need() { [ -e "$1" ] || { echo "MISSING $1 (see $2)"; grep -nE "rror|undefined reference" "$2" | head -40; exit 1; }; }

cp configure.nps_wcoss2_dmpara configure.nps
for t in geogrid metgrid ungrib nemsinterp; do
  ./compile $t > "$LOG/nps_dmpar_$t.log" 2>&1 || true
  need $t.exe "$LOG/nps_dmpar_$t.log"
  cp -L $t.exe "$NAM_EXEC/$t.exe"
done
./clean > /dev/null 2>&1 || true

cp configure.nps_wcoss2_serial configure.nps
./compile metgrid > "$LOG/nps_serial_metgrid.log" 2>&1 || true
need metgrid.exe "$LOG/nps_serial_metgrid.log"; cp -L metgrid.exe "$NAM_EXEC/metgrid_serial.exe"
./compile ungrib > "$LOG/nps_serial_ungrib.log" 2>&1 || true
need ungrib/src/ungribs.exe "$LOG/nps_serial_ungrib.log"; cp -L ungrib/src/ungribs.exe "$NAM_EXEC/ungribs.exe"
echo "NPS built in $((SECONDS - t0)) s"
ls -l "$NAM_EXEC"
print_versions

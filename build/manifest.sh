#!/bin/bash
# Write /opt/nam/work/exec/MANIFEST and copy executables, MANIFEST and build logs to
# s3://nam-recast-617711905691/build/<date>/. Usage: manifest.sh [<nam-recast commit>]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/versions.sh"
DATE=$(date -u +%F); DEST=s3://nam-recast-617711905691/build/$DATE
case $ARCH in aarch64|arm64) DEST=$DEST-arm64 ;; esac
M=$NAM_EXEC/MANIFEST
{
  echo "# NAM recast executables, built $(date -u +%FT%TZ) on $(hostname) ($(. /etc/os-release; echo $PRETTY_NAME), $(uname -m))"
  echo "upstream: MatthewPyle-NOAA/NAM main @ $(cat $NAM_SRC/.staged)"
  echo "nam-recast build scripts: ${1:-unknown}"
  if [ "$TOOLCHAIN" = gnu ]; then
    echo "toolchain: $(gfortran --version | head -1), $(gcc --version | head -1), $(mpirun --version 2>&1 | head -1 | tr -s ' ')"
  else
    echo "toolchain: Intel oneAPI $ONEAPI_FORTRAN_VER (ifort classic 2021.13), icx/icpx $ONEAPI_CPP_VER, Intel MPI $IMPI_VER"
  fi
  echo "libraries:"; sed 's/^/  /' "$LIBS_ROOT"/*/.built
  echo "upstream exec name map: NEMS.x=nam_nems_nmmb_fcst geogrid.exe=nam_geogrid ungrib.exe=nam_ungrib metgrid.exe=nam_metgrid nemsinterp.exe=nam_nemsinterp metgrid_serial.exe=nam_metgrid_boco ungribs.exe=nam_ungrib_boco ncep_post=nam_ncep_post nam_post0=nam_post0"
  for e in "$NAM_EXEC"/*; do
    [ "$(basename "$e")" = MANIFEST ] && continue
    echo; echo "== $(basename "$e")  $(stat -c %s "$e") bytes  sha256 $(sha256sum "$e" | cut -c1-64)"
    ldd "$e" | sed 's/^\s*/  /'
  done
} > "$M"
aws s3 cp --only-show-errors --recursive "$NAM_EXEC" "$DEST/exec/"
aws s3 cp --only-show-errors --recursive "$NAM_WORK/logs" "$DEST/logs/"
echo "uploaded to $DEST"

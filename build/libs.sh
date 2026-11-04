#!/bin/bash
# Build the NAM library stack under /opt/nam/libs/<name>-<ver> with Intel oneAPI 2024.2.
# Idempotent: a library whose prefix holds .built is skipped. Usage: libs.sh [name ...]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/env.sh"
mkdir -p "$LIBSRC" "$LIBS_ROOT" "$NAM_WORK/logs/libs"

# Clang-based icx is strict about pre-C99 code that old configure scripts and libraries use.
export CFLAGS="-O2 -fPIC -Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=int-conversion -Wno-error=incompatible-function-pointer-types"
export FFLAGS="-O2 -fPIC" FCFLAGS="-O2 -fPIC" CXXFLAGS="-O2 -fPIC"

fetch() { # fetch <dir> <repo> <tag>
  local d=$LIBSRC/$1
  [ -d "$d/.git" ] || git clone -q --depth 1 --recurse-submodules --shallow-submodules -b "$3" "https://github.com/$2" "$d"
  echo "$d"
}
done_() { [ -f "$1/.built" ]; }
stamp() { echo "$(date -u +%FT%TZ) $2" > "$1/.built"; echo "== built $2 -> $1"; }
apply_patches() { # apply_patches <srcdir> <prefix>; patches named <prefix>-*.patch, idempotent
  local f
  for f in "$HERE"/patches/"$2"-*.patch; do
    [ -e "$f" ] || continue
    if patch -d "$1" -p1 -N --dry-run -s < "$f" >/dev/null 2>&1; then patch -d "$1" -p1 -N -s < "$f"; echo "patched $(basename "$f")"; fi
  done
}

cmake_lib() { # cmake_lib <name> <ver> <repo> <tag> [cmake args...]
  local n=$1 v=$2 repo=$3 tag=$4; shift 4
  local pre=$LIBS_ROOT/$n-$v
  done_ "$pre" && { echo "skip $n-$v"; return; }
  local s; s=$(fetch "$n-$v" "$repo" "$tag")
  apply_patches "$s" "$n"
  rm -rf "$s/_build"; mkdir -p "$s/_build"; cd "$s/_build"
  cmake .. -DCMAKE_INSTALL_PREFIX="$pre" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=icx -DCMAKE_Fortran_COMPILER=ifort -DCMAKE_CXX_COMPILER=icpx \
    -DCMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH:-}" -DCMAKE_INSTALL_LIBDIR=lib \
    -DENABLE_TESTS=OFF -DBUILD_TESTING=OFF "$@"
  make -j"$NPROC"; make install
  stamp "$pre" "$n $v ($repo $tag)"
  source "$HERE/env.sh"
}

b_zlib() {
  local pre=$LIBS_ROOT/zlib-$zlib_ver; done_ "$pre" && { echo "skip zlib"; return; }
  local s; s=$(fetch zlib-$zlib_ver madler/zlib v$zlib_ver); cd "$s"
  ./configure --prefix="$pre"; make -j"$NPROC"; make install; stamp "$pre" "zlib $zlib_ver"
}
b_libpng() {
  local pre=$LIBS_ROOT/libpng-$libpng_ver; done_ "$pre" && { echo "skip libpng"; return; }
  local s; s=$(fetch libpng-$libpng_ver glennrp/libpng v$libpng_ver); cd "$s"
  CPPFLAGS="-I$ZLIB_ROOT/include" LDFLAGS="-L$ZLIB_ROOT/lib" ./configure --prefix="$pre" --disable-shared
  make -j"$NPROC"; make install; stamp "$pre" "libpng $libpng_ver"
}
b_jasper() {
  local pre=$LIBS_ROOT/jasper-$jasper_ver; done_ "$pre" && { echo "skip jasper"; return; }
  local s; s=$(fetch jasper-$jasper_ver jasper-software/jasper version-$jasper_ver)
  rm -rf "$s/_b"; mkdir "$s/_b"; cd "$s/_b"
  cmake .. -DCMAKE_INSTALL_PREFIX="$pre" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=icx \
    -DJAS_ENABLE_SHARED=OFF -DJAS_ENABLE_LIBJPEG=OFF -DJAS_ENABLE_OPENGL=OFF -DJAS_ENABLE_DOC=OFF \
    -DJAS_ENABLE_PROGRAMS=OFF -DCMAKE_INSTALL_LIBDIR=lib
  make -j"$NPROC"; make install; stamp "$pre" "jasper $jasper_ver"
}
b_hdf5() {
  local pre=$LIBS_ROOT/hdf5-$hdf5_ver; done_ "$pre" && { echo "skip hdf5"; return; }
  local s; s=$(fetch hdf5-$hdf5_ver HDFGroup/hdf5 hdf5-${hdf5_ver//./_}); cd "$s"
  ./configure --prefix="$pre" --enable-hl --disable-fortran --disable-cxx --with-zlib="$ZLIB_ROOT" --enable-build-mode=production
  make -j"$NPROC"; make install; stamp "$pre" "hdf5 $hdf5_ver (serial)"
}
b_netcdf() {
  local pre=$LIBS_ROOT/netcdf-$netcdf_ver; done_ "$pre" && { echo "skip netcdf"; return; }
  local s; s=$(fetch netcdf-c-$netcdf_ver Unidata/netcdf-c v$netcdf_ver); cd "$s"
  CPPFLAGS="-I$HDF5/include -I$ZLIB_ROOT/include" LDFLAGS="-L$HDF5/lib -L$ZLIB_ROOT/lib -Wl,-rpath,$HDF5/lib" \
    ./configure --prefix="$pre" --disable-dap --disable-byterange --enable-netcdf-4 --disable-testsets
  make -j"$NPROC"; make install
  local f; f=$(fetch netcdf-fortran-$netcdf_fortran_ver Unidata/netcdf-fortran v$netcdf_fortran_ver); cd "$f"
  CPPFLAGS="-I$pre/include" LDFLAGS="-L$pre/lib -Wl,-rpath,$pre/lib" LIBS="-lnetcdf" \
    ./configure --prefix="$pre"
  make -j"$NPROC"; make install
  stamp "$pre" "netcdf-c $netcdf_ver + netcdf-fortran $netcdf_fortran_ver"
}
b_esmf() {
  local pre=$LIBS_ROOT/esmf-$esmf_ver; done_ "$pre" && { echo "skip esmf"; return; }
  local tag=ESMF_${esmf_ver//./_}
  local s; s=$(fetch esmf-$esmf_ver esmf-org/esmf "$tag")
  apply_patches "$s" esmf
  cd "$s"
  export ESMF_DIR=$s ESMF_COMM=intelmpi ESMF_COMPILER=intel ESMF_BOPT=O ESMF_OPTLEVEL=2 ESMF_ABI=64
  export ESMF_CXXCOMPILER=mpiicpc ESMF_CCOMPILER=mpiicc ESMF_F90COMPILER=mpiifort
  export ESMF_NETCDF=split ESMF_NETCDF_INCLUDE=$NETCDF/include ESMF_NETCDF_LIBPATH=$NETCDF/lib
  export ESMF_NETCDF_LIBS="-lnetcdff -lnetcdf"
  # icpx (clang, C++17 by default) rejects 'register' and makes C++11 narrowing in brace
  # initialisers a hard error; icpc 19 only warned. Pin gnu++11 and downgrade narrowing.
  export ESMF_CXXCOMPILEOPTS="-std=gnu++11 -Wno-c++11-narrowing -Wno-register"
  export ESMF_LAPACK=internal ESMF_PIO=OFF; unset ESMF_XERCES ESMF_XERCES_INCLUDE ESMF_XERCES_LIBPATH  # any value of ESMF_XERCES turns it on
  export ESMF_INSTALL_PREFIX=$pre ESMF_INSTALL_HEADERDIR=include ESMF_INSTALL_MODDIR=mod \
         ESMF_INSTALL_LIBDIR=lib ESMF_INSTALL_BINDIR=bin ESMF_INSTALL_DOCDIR=doc
  make info
  make -j"$NPROC" lib
  make install
  stamp "$pre" "esmf $esmf_ver ($tag) intelmpi/intel"
}

b_bacio()  { cmake_lib bacio  $bacio_ver  NOAA-EMC/NCEPLIBS-bacio  v$bacio_ver; }
b_sp()     { cmake_lib sp     $sp_ver     NOAA-EMC/NCEPLIBS-sp     v$sp_ver; }
b_ip()     { cmake_lib ip     $ip_ver     NOAA-EMC/NCEPLIBS-ip     v$ip_ver; }
b_w3nco()  { cmake_lib w3nco  $w3nco_ver  NOAA-EMC/NCEPLIBS-w3nco  v$w3nco_ver; }
b_sigio()  { cmake_lib sigio  $sigio_ver  NOAA-EMC/NCEPLIBS-sigio  v$sigio_ver; }
b_sfcio()  { cmake_lib sfcio  $sfcio_ver  NOAA-EMC/NCEPLIBS-sfcio  v$sfcio_ver; }
b_gfsio()  { cmake_lib gfsio  $gfsio_ver  NOAA-EMC/NCEPLIBS-gfsio  v$gfsio_ver; }
b_nemsio() { cmake_lib nemsio $nemsio_ver NOAA-EMC/NCEPLIBS-nemsio v$nemsio_ver -DCMAKE_Fortran_COMPILER=mpiifort; }
b_w3emc()  { cmake_lib w3emc  $w3emc_ver  NOAA-EMC/NCEPLIBS-w3emc  v$w3emc_ver; }
b_g2()     { cmake_lib g2     $g2_ver     NOAA-EMC/NCEPLIBS-g2     v$g2_ver; }
b_g2c()    { cmake_lib g2c    $g2c_ver    NOAA-EMC/NCEPLIBS-g2c    v$g2c_ver; }
b_g2tmpl() { cmake_lib g2tmpl $g2tmpl_ver NOAA-EMC/NCEPLIBS-g2tmpl v$g2tmpl_ver; }
b_bufr()   { cmake_lib bufr   $bufr_ver   NOAA-EMC/NCEPLIBS-bufr   bufr_v$bufr_ver; }
b_crtm()   { cmake_lib crtm   $crtm_ver   NOAA-EMC/EMC_crtm        v$crtm_ver; }
b_wrf_io() { cmake_lib wrf_io $wrf_io_ver NOAA-EMC/NCEPLIBS-wrf_io v$wrf_io_ver; }
b_landsfcutil() { cmake_lib landsfcutil $landsfcutil_ver NOAA-EMC/NCEPLIBS-landsfcutil v$landsfcutil_ver; }

ALL="zlib libpng jasper hdf5 netcdf bacio sp ip w3nco sigio sfcio gfsio nemsio w3emc g2 g2c g2tmpl bufr crtm wrf_io landsfcutil esmf"
for n in ${@:-$ALL}; do
  echo "######## $n  $(date -u +%T)"
  t0=$SECONDS
  # run in a background subshell + wait: a subshell on the left of || would silently disable set -e
  ( set -e; b_$n ) > "$NAM_WORK/logs/libs/$n.log" 2>&1 &
  wait $! || { echo "FAILED $n (see $NAM_WORK/logs/libs/$n.log)"; tail -30 "$NAM_WORK/logs/libs/$n.log"; exit 1; }
  source "$HERE/env.sh"
  echo "   ok $n in $((SECONDS - t0)) s"
done
echo "== library stack:"; cat "$LIBS_ROOT"/*/.built

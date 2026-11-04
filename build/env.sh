# Source me (bash). Intel toolchain + hpc-stack-style library variables that the upstream
# NAM makefiles/configure files expect (G2_LIB4, W3NCO_LIBd, NEMSIO_INC, ESMFMKFILE ...).
_here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$_here/versions.sh"

if [ -z "${SETVARS_COMPLETED:-}" ]; then
  _u=$-; set +eu
  source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1
  [[ $_u == *e* ]] && set -e; [[ $_u == *u* ]] && set -u
fi
export I_MPI_F90=ifort I_MPI_F77=ifort I_MPI_FC=ifort I_MPI_CC=icx I_MPI_CXX=icpx
export CC=icx CXX=icpx FC=ifort F77=ifort F90=ifort
export NPROC=${NPROC:-$(nproc)}

_p() { echo "$LIBS_ROOT/$1-$2"; }
_f() { # first match of a file under a prefix
  local hit; hit=$(find "$1" -name "$2" 2>/dev/null | sort | head -1); echo "$hit"; }
_d() { # first match of a directory under a prefix
  local hit; hit=$(find "$1" -type d -name "$2" 2>/dev/null | sort | head -1); echo "$hit"; }

export ZLIB_ROOT=$(_p zlib $zlib_ver) PNG_ROOT=$(_p libpng $libpng_ver) JASPER_ROOT=$(_p jasper $jasper_ver)
export HDF5=$(_p hdf5 $hdf5_ver) NETCDF=$(_p netcdf $netcdf_ver)
export HDF5_ROOT=$HDF5 NETCDF_ROOT=$NETCDF
export Z_INC=$ZLIB_ROOT/include Z_LIB=$ZLIB_ROOT/lib/libz.a
export PNG_INC=$PNG_ROOT/include PNG_LIB=$PNG_ROOT/lib/libpng.a
export JASPER_INC=$JASPER_ROOT/include JASPER_LIB=$(_f $JASPER_ROOT libjasper.a)
export NETCDF_INCLUDE="-I$NETCDF/include" NETCDF_INC=$NETCDF/include
export HDF5_LDFLAGS="$HDF5/lib"
export NETCDF_LDFLAGS="-L$NETCDF/lib -Wl,-rpath,$NETCDF/lib -lnetcdff -lnetcdf -L$HDF5/lib -Wl,-rpath,$HDF5/lib -lhdf5_hl -lhdf5 -L$ZLIB_ROOT/lib -lz -ldl -lm"
export NETCDF_LDFLAGS_F="$NETCDF_LDFLAGS"
export PATH=$NETCDF/bin:$HDF5/bin:$PATH

P=$(_p bacio $bacio_ver);   export BACIO_LIB4=$(_f $P libbacio_4.a) BACIO_LIB8=$(_f $P libbacio_8.a)
P=$(_p sp $sp_ver);         export SP_LIB4=$(_f $P libsp_4.a) SP_LIB8=$(_f $P libsp_8.a) SP_LIBd=$(_f $P libsp_d.a)
P=$(_p ip $ip_ver);         export IP_LIB4=$(_f $P libip_4.a) IP_LIB8=$(_f $P libip_8.a) IP_LIBd=$(_f $P libip_d.a) IP_INC4=$(_d $P include_4) IP_INCd=$(_d $P include_d)
P=$(_p w3nco $w3nco_ver);   export W3NCO_LIB4=$(_f $P libw3nco_4.a) W3NCO_LIB8=$(_f $P libw3nco_8.a) W3NCO_LIBd=$(_f $P libw3nco_d.a)
P=$(_p w3emc $w3emc_ver);   export W3EMC_LIB4=$(_f $P libw3emc_4.a) W3EMC_LIB8=$(_f $P libw3emc_8.a) W3EMC_LIBd=$(_f $P libw3emc_d.a) W3EMC_INC4=$(_d $P include_4) W3EMC_INC8=$(_d $P include_8) W3EMC_INCd=$(_d $P include_d)
P=$(_p g2 $g2_ver);         export G2_LIB4=$(_f $P libg2_4.a) G2_LIBd=$(_f $P libg2_d.a) G2_INC4=$(_d $P include_4) G2_INCd=$(_d $P include_d)
P=$(_p g2c $g2c_ver);       export G2C_LIB=$(_f $P 'libg2c*.a') G2C_INC=$P/include
P=$(_p g2tmpl $g2tmpl_ver); export G2TMPL_LIB=$(_f $P 'libg2tmpl*.a') G2TMPL_INC=$(dirname "$(_f $P 'grib2_all_tables_module.mod')")
P=$(_p sigio $sigio_ver);   export SIGIO_LIB=$(_f $P 'libsigio*.a') SIGIO_INC=$(dirname "$(_f $P 'sigio_module.mod')")
P=$(_p sfcio $sfcio_ver);   export SFCIO_LIB=$(_f $P 'libsfcio*.a') SFCIO_INC=$(dirname "$(_f $P 'sfcio_module.mod')")
P=$(_p gfsio $gfsio_ver);   export GFSIO_LIB=$(_f $P 'libgfsio*.a') GFSIO_INC=$(dirname "$(_f $P 'gfsio_module.mod')")
P=$(_p nemsio $nemsio_ver); export NEMSIO_LIB=$(_f $P 'libnemsio*.a') NEMSIO_INC=$(dirname "$(_f $P 'nemsio_module.mod')")
P=$(_p bufr $bufr_ver);     export BUFR_LIB4=$(_f $P libbufr_4.a) BUFR_LIB8=$(_f $P libbufr_8.a) BUFR_LIBd=$(_f $P libbufr_d.a)
P=$(_p crtm $crtm_ver);     export CRTM_LIB=$(_f $P 'libcrtm*.a') CRTM_INC=$(dirname "$(_f $P 'crtm_module.mod')")
P=$(_p wrf_io $wrf_io_ver); export WRF_IO_LIB=$(_f $P 'libwrf_io*.a') WRF_IO_INC=$(dirname "$(_f $P 'module_internal_header_util.mod')")
P=$(_p landsfcutil $landsfcutil_ver); export LANDSFCUTIL_LIB4=$(_f $P liblandsfcutil_4.a) LANDSFCUTIL_LIBd=$(_f $P liblandsfcutil_d.a) LANDSFCUTIL_INC4=$(_d $P include_4) LANDSFCUTIL_INCd=$(_d $P include_d)
export ESMFMKFILE=$(_p esmf $esmf_ver)/lib/esmf.mk
export SIGIO_LIB4=$SIGIO_LIB SFCIO_LIB4=$SFCIO_LIB   # names nam_post0 uses
unset P

export CMAKE_PREFIX_PATH=$(ls -d $LIBS_ROOT/*/ 2>/dev/null | sed 's:/$::' | paste -sd: -)

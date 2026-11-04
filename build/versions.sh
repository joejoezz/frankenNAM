# Pinned versions for the NAM recast build. Sourced by env.sh and every build script.
# Library pins follow upstream versions/build.ver (WCOSS2 NAM v4.2); the toolchain is the
# AWS substitute for Intel 19.1.3 + Cray MPICH 8.1.9.
export NAM_ROOT=/opt/nam
export NAM_UPSTREAM=$NAM_ROOT/upstream/MatthewPyle-NOAA-NAM
export NAM_WORK=$NAM_ROOT/work
export NAM_SRC=$NAM_WORK/src
export NAM_EXEC=$NAM_WORK/exec
export LIBS_ROOT=$NAM_ROOT/libs
export LIBSRC=$NAM_WORK/libsrc

export ONEAPI_FORTRAN_VER=2024.2   # ifort 2021.13 (classic)
export ONEAPI_CPP_VER=2024.2       # icx/icpx; icc/icpc no longer ship
export IMPI_VER=2021.13

export zlib_ver=1.2.11
export libpng_ver=1.6.37
export jasper_ver=2.0.25
export hdf5_ver=1.10.6
export netcdf_ver=4.7.4
export netcdf_fortran_ver=4.5.3
export bacio_ver=2.4.1
export sp_ver=2.3.3
export ip_ver=3.3.3
export w3nco_ver=2.4.1
export w3emc_ver=2.9.1
export g2_ver=3.4.5
export g2c_ver=1.6.4
export g2tmpl_ver=1.10.0
export sigio_ver=2.3.2
export sfcio_ver=1.4.1
export gfsio_ver=1.4.1
export nemsio_ver=2.5.2
export bufr_ver=11.5.0
export crtm_ver=2.3.0
export wrf_io_ver=1.2.0
export landsfcutil_ver=2.4.1
export esmf_ver=7.1.0r

#!/bin/bash
# Install the compiler toolchain and OS packages on a clean Ubuntu 24.04 x86_64 box (needs sudo).
# Intel oneAPI 2024.2 is the last release with classic ifort; icc/icpc are gone, so C/C++ use icx/icpx.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/versions.sh"
export DEBIAN_FRONTEND=noninteractive

sudo apt-get update -q
sudo apt-get install -y -q build-essential gfortran cmake git curl wget rsync m4 csh tcsh ksh \
  perl python3 pkg-config autoconf automake libtool libcurl4-openssl-dev libexpat1-dev gnupg file

if [ ! -f /usr/share/keyrings/oneapi-archive-keyring.gpg ]; then
  wget -qO- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB \
    | gpg --dearmor | sudo tee /usr/share/keyrings/oneapi-archive-keyring.gpg >/dev/null
  echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" \
    | sudo tee /etc/apt/sources.list.d/oneAPI.list
  sudo apt-get update -q
fi
sudo apt-get install -y -q intel-oneapi-compiler-fortran-$ONEAPI_FORTRAN_VER \
  intel-oneapi-compiler-dpcpp-cpp-$ONEAPI_CPP_VER intel-oneapi-mpi-devel-$IMPI_VER

# Make the Intel compiler runtime and Intel MPI resolvable without sourcing setvars.sh, so the
# executables (and libesmf.so / libnetcdf.so, whose own deps are libimf/libsvml/libiomp5) load
# from a plain shell or container. Equivalent Dockerfile line: the same ld.so.conf.d file.
printf '%s\n' /opt/intel/oneapi/compiler/$ONEAPI_FORTRAN_VER/lib /opt/intel/oneapi/mpi/$IMPI_VER/lib \
  /opt/intel/oneapi/mpi/$IMPI_VER/opt/mpi/libfabric/lib | sudo tee /etc/ld.so.conf.d/nam-intel-oneapi.conf >/dev/null
sudo ldconfig

sudo mkdir -p "$NAM_ROOT/work" "$NAM_ROOT/libs"; sudo chown -R "$(id -u):$(id -g)" "$NAM_ROOT/work" "$NAM_ROOT/libs"
set +eu; source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1; set -eu   # setvars.sh trips nounset
ifort --version 2>&1 | grep -v remark | head -1; icx --version | head -1

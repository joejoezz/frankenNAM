#!/bin/bash
# Install the GNU toolchain and OS packages on a clean Ubuntu 24.04 box (arm64 or x86_64; needs
# sudo): gfortran 13 + OpenMPI 4.1 from apt. The GNU counterpart of toolchain.sh (Intel oneAPI).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/versions.sh"
export DEBIAN_FRONTEND=noninteractive

sudo apt-get update -q
sudo apt-get install -y -q build-essential gfortran-$GFORTRAN_VER gfortran cmake git curl wget rsync m4 csh tcsh ksh \
  perl python3 pkg-config autoconf automake libtool libcurl4-openssl-dev libexpat1-dev gnupg file \
  openmpi-bin libopenmpi-dev time
sudo mkdir -p "$NAM_ROOT/work" "$NAM_ROOT/libs"; sudo chown -R "$(id -u):$(id -g)" "$NAM_ROOT/work" "$NAM_ROOT/libs"
gfortran --version | head -1; gcc --version | head -1; mpirun --version | head -1; mpif90 -show

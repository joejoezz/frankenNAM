#!/bin/bash
# Build-box side: pack everything a stock Ubuntu 24.04 runner needs into one tar in S3
# (replaces the AMI route, see docs/run-notes.md item 3): /opt/nam/libs (shared esmf/netcdf/hdf5
# plus the static stack), exec, fix, parm, the run scripts and the case's NPS output (IC + bocos).
# x86 bundles also carry the Intel runtime (/opt/intel/oneapi/{compiler,mpi}); arm64 bundles
# rely on apt (openmpi-bin libopenmpi3t64 libgfortran5 libgomp1, installed by deploy/04's user-data).
# usage: run/bundle.sh [cycle]   -> s3://nam-recast-617711905691/runner/bundle-<date>[-arm64].tar
#        INCLUDE_CASE=1 adds the cycle's NPS output (IC + bocos) for MODE=anl runners that skip NPS;
#        tm06 runners stage and run NPS on the node, so the default bundle carries no case data.
#        wgrib2 (the IPOLATES=1 build, products.sh) travels in exec/ and is installed by the user-data.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CYCLE=${1:-2026110100}
BUCKET=nam-recast-617711905691
ARCH=$(uname -m); SUFFIX=""; [ "$ARCH" = aarch64 ] && SUFFIX=-arm64
NAME=bundle-$(date -u +%Y%m%d)${BUNDLE_TAG:+-$BUNDLE_TAG}$SUFFIX.tar   # BUNDLE_TAG=tm06 -> bundle-YYYYMMDD-tm06-arm64.tar
mkdir -p /opt/nam/work/run; cp "$HERE"/*.sh "$HERE"/*.py /opt/nam/work/run/ 2>/dev/null || true
cp -r "$HERE"/parm /opt/nam/work/run/ 2>/dev/null || true
[ -x /opt/nam/work/exec/wgrib2 ] || cp "$(command -v wgrib2)" /opt/nam/work/exec/wgrib2
PARTS=(opt/nam/libs opt/nam/work/exec opt/nam/work/run opt/nam/work/src/parm opt/nam/fix)
[ "${INCLUDE_CASE:-0}" = 1 ] && PARTS+=(opt/nam/runs/$CYCLE/nemsinterp_ic/input_domain_01_nemsio opt/nam/runs/$CYCLE/bocos)
[ "$ARCH" = x86_64 ] && PARTS+=(opt/intel/oneapi/compiler opt/intel/oneapi/mpi)
cd /
du -shc "${PARTS[@]}" | tail -1
tar cf - "${PARTS[@]}" | aws s3 cp --only-show-errors --expected-size 20000000000 - s3://$BUCKET/runner/$NAME
aws s3 cp --only-show-errors --recursive "$HERE" s3://$BUCKET/runner/run/ --exclude "*" --include "*.sh" --include "*.py" --include "parm/*"
aws s3 ls s3://$BUCKET/runner/$NAME

#!/bin/bash
# Full build on a clean Ubuntu 24.04 box (x86_64/Intel or arm64/GNU, see versions.sh TOOLCHAIN):
# toolchain, libraries, NPS, NEMS, UPP,
# then the acceptance checks. Every stage is idempotent; rerun after a failure.
# Expects the upstream tree at /opt/nam/upstream/MatthewPyle-NOAA-NAM (see versions.sh).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/versions.sh"
mkdir -p "$NAM_WORK/logs"
stage() { local t0=$SECONDS; echo "######## $1  $(date -u +%T)"; "$HERE/$1"; echo "######## $1 done in $((SECONDS - t0)) s"; }

if [ "${SKIP_TOOLCHAIN:-0}" != 1 ]; then
  if [ "$TOOLCHAIN" = gnu ]; then stage toolchain.gnu.sh; else stage toolchain.sh; fi
fi
stage libs.sh
stage build_nps.sh
stage build_nems.sh
stage build_upp.sh
"$HERE/acceptance.sh"

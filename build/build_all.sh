#!/bin/bash
# Full Phase 0 build on a clean Ubuntu 24.04 x86_64 box: toolchain, libraries, NPS, NEMS, UPP,
# then the acceptance checks. Every stage is idempotent; rerun after a failure.
# Expects the upstream tree at /opt/nam/upstream/MatthewPyle-NOAA-NAM (see versions.sh).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/versions.sh"
mkdir -p "$NAM_WORK/logs"
stage() { local t0=$SECONDS; echo "######## $1  $(date -u +%T)"; "$HERE/$1"; echo "######## $1 done in $((SECONDS - t0)) s"; }

[ "${SKIP_TOOLCHAIN:-0}" = 1 ] || stage toolchain.sh
stage libs.sh
stage build_nps.sh
stage build_nems.sh
stage build_upp.sh
"$HERE/acceptance.sh"

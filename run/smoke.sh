#!/bin/bash
# Build-box acceptance runs after `recast.sh nps` for $CYCLE (docs/phase1-graviton-brief.md 4):
# two 3 h TDFI smoke runs (4x7 compute + 1x4 write) whose history files must be bit-identical,
# UPP on the first with a PRMSL sanity check (wgrib2 -stats), then a 1 h hourly-history run of
# the trap build NEMS_debug.x (-O0 -fcheck=all -finit-real=snan -ffpe-trap). Node memory is
# sampled every 30 s per run. Results in /opt/nam/runs/accept/summary.txt.
# usage: run/smoke.sh [cycle]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CYCLE=${1:-2026110100}; BASE=/opt/nam/runs/$CYCLE; OUT=${OUT:-/opt/nam/runs/accept}; mkdir -p $OUT
WG=${WGRIB2:-wgrib2}
SUM=$OUT/summary.txt; echo "== smoke $(date -u +%FT%TZ) $(uname -m) $(nproc) cores" >> $SUM
mk() { mkdir -p $1; ln -sfn $BASE/nemsinterp_ic $1/nemsinterp_ic; ln -sfn $BASE/bocos $1/bocos; }
memlog() { while sleep 30; do echo "$(date -u +%T) $(free -m | awk '/Mem:/{print "used_mb="$3, "avail_mb="$7}')"; done; }
run() { # run <dir> VAR=value...
  local d=$1; shift; mk $d; rm -rf $d/fcst
  memlog > $d/mem.log & local mp=$!
  local t0=$SECONDS
  ( cd $HERE && env RUNDIR=$d CYCLE=$CYCLE "$@" ./recast.sh fcst ) > $d/fcst.log 2>&1; local rc=$?
  kill $mp 2>/dev/null
  local peak; peak=$(grep -o 'used_mb=[0-9]*' $d/mem.log | cut -d= -f2 | sort -n | tail -1)
  echo "$(basename $d): rc=$rc wall=$((SECONDS - t0)) s node peak ${peak:-?} MB used; $(grep -m1 'Maximum resident' $d/fcst/nems.err 2>/dev/null | sed 's/^\s*//')" | tee -a $SUM
}
if [ "${SKIP_SMOKE:-0}" != 1 ]; then
  run $OUT/smoke_a FHMAX=3
  run $OUT/smoke_b FHMAX=3
  for f in $OUT/smoke_a/fcst/nmmb_hst_01_nio_*; do
    b=$OUT/smoke_b/fcst/$(basename $f)
    if cmp -s "$f" "$b"; then echo "IDENTICAL $(basename $f) ($(stat -c %s $f) bytes)"; else echo "DIFFER $(basename $f): $(cmp -l $f $b | wc -l) bytes differ"; fi
  done | tee -a $SUM
  ( cd $HERE && RUNDIR=$OUT/smoke_a CYCLE=$CYCLE FHMAX=3 NPOST=${NPOST:-16} ./recast.sh post ) > $OUT/smoke_a/post.log 2>&1
  echo "post rc=$? $(tr '\n' ';' < $OUT/smoke_a/post_times.txt 2>/dev/null)" | tee -a $SUM
  for fh in 00 03; do $WG $OUT/smoke_a/grib2/nam.t00z.bgdawp$fh.tm00.grib2 -match ":PRMSL:" -stats 2>&1 | tee -a $SUM; done
fi
if [ "${SKIP_DEBUG:-0}" != 1 ]; then
  run $OUT/dbg1h FHMAX=1 FILTER=0 HISTMIN=60 NEMS_EXE=/opt/nam/work/exec/NEMS_debug.x
  ls $OUT/dbg1h/fcst/nmmb_hst_01_nio_* 2>/dev/null | tee -a $SUM
  grep -n -A12 -m3 "SIGFPE\|Fortran runtime error\|signal" $OUT/dbg1h/fcst/nems.err | head -60 | tee -a $SUM
fi
echo "== done $(date -u +%FT%TZ)" >> $SUM

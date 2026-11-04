#!/bin/bash
# Runner-node driver: stage inputs, NPS, forecast, UPP + grid-218 products for $CYCLE, S3 syncs, then
# (CHAIN=1) pop the next job from the S3 queue and launch its runner. Resumes from the newest restart
# in S3 after a Spot interruption unless NO_RESTART=1. Env: CYCLE, MODE (tm06 | anl), S3SUB (tm06 |
# recast-arm64 | recast), NO_RESTART, SYNC_HISTORY, S3PROD, CHAIN, QUEUE, SKIP_NPS=1 (anl runs whose
# IC/bocos came with the bundle), POST_AFTER=1 (UPP after the forecast instead of alongside), plus any
# recast.sh override (FHMAX, FILTER, ...).
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export CYCLE=${CYCLE:-2026110100} MODE=${MODE:-tm06}
export RUNDIR=/opt/nam/runs/$CYCLE S3RUN=s3://nam-recast-617711905691/cases/$CYCLE/${S3SUB:-tm06}
export S3PROD=${S3PROD-s3://nam-recast-617711905691/products}
# NO_RESTART=1: no restart files at all (RESTMIN past the run, no f00 restart) so the run fits a
# 64 GB node (Phase 0: restarts pushed the peak from 48 to 77 GB); a Spot reclaim then means a rerun.
# RESTMIN must be a multiple of the 25 s timestep (minutes*60 mod 25 = 0, i.e. of 5 min) or NEMS
# aborts at start ("Timestep of this domain does not divide evenly into the restart interval").
if [ "${NO_RESTART:-0}" = 1 ]; then export RESTMIN=100800 RST00=false WRTLAST=false; fi   # 70 days
mkdir -p $RUNDIR/fcst $RUNDIR/grib2
cd "$HERE"
tl() { echo "$(date -u +%FT%TZ) $*" >> $RUNDIR/timeline.txt; }
# c7a has no SMT: a c7a.48xlarge is 192 physical cores. Use 168 compute + 2x8 write tasks
# and leave 8 cores for UPP running alongside; on a smaller box fall back to the 96-core layout.
NC=$(nproc)
if [ "$NC" -ge 190 ]; then
  export INPES=${INPES:-12} JNPES=${JNPES:-14} WRITE_GROUPS=${WRITE_GROUPS:-2} WRITE_TASKS=${WRITE_TASKS:-8}
  export FCST_CPUS=0-183 POST_CPUS=184-191 NPOST=8
elif [ "$NC" -ge 96 ]; then
  export INPES=${INPES:-8} JNPES=${JNPES:-11} WRITE_GROUPS=${WRITE_GROUPS:-1} WRITE_TASKS=${WRITE_TASKS:-8}
  export NPOST=${NPOST:-4}
else   # 32-core node (the account's 32-vCPU quota): all 32 cores run the model (4x7 + 1x4 write ranks);
       # UPP + products run alongside on the 4 write ranks' cores (28-31), which idle between history
       # writes once the model's MPI ranks yield when idle (FCST_YIELD, recast.sh). POST_AFTER=1 = Phase 0 behaviour.
  export INPES=${INPES:-4} JNPES=${JNPES:-7} WRITE_GROUPS=${WRITE_GROUPS:-1} WRITE_TASKS=${WRITE_TASKS:-4}
  if [ "${POST_AFTER:-0}" = 1 ]; then export NPOST=${NPOST:-16}
  else export NPOST=${NPOST:-4} POST_CPUS=${POST_CPUS:-28-31} FCST_YIELD=${FCST_YIELD:-1}; fi
fi
lscpu | grep -E "^CPU\(s\)|Thread|Model name" >> $RUNDIR/runner.log 2>/dev/null || true
echo "layout ${INPES}x${JNPES} + ${WRITE_GROUPS}x${WRITE_TASKS}, post $NPOST${POST_CPUS:+ on $POST_CPUS}" >> $RUNDIR/runner.log
ITYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null)
echo "runner start $(date -u +%FT%TZ) $ITYPE $MODE $CYCLE" | tee -a $RUNDIR/runner.log
tl "runner start $ITYPE $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null)"
( while true; do echo "$(date -u +%T) $(free -m | awk '/Mem:/{print "used_mb="$3, "avail_mb="$7}')" >> $RUNDIR/mem.log; sleep 60; done ) &
MEMPID=$!

NRC=0
if [ "${SKIP_NPS:-0}" != 1 ]; then
  NPS_CLEAN=${NPS_CLEAN:-1} ./recast.sh stage nps > $RUNDIR/nps.log 2>&1; NRC=$?
  echo "nps rc=$NRC $(date -u +%FT%TZ)" | tee -a $RUNDIR/runner.log
fi
FRC=1; PRC=1
if [ $NRC = 0 ]; then
  [ "${NO_RESTART:-0}" = 1 ] || aws s3 sync --only-show-errors $S3RUN/history/ $RUNDIR/fcst/ --exclude "*" --include "nmmb_rst_*"
  aws s3 sync --only-show-errors $S3RUN/grib2-all/ $RUNDIR/grib2/
  ./recast.sh fcst > $RUNDIR/fcst.log 2>&1 &
  FPID=$!
  ( while kill -0 $FPID 2>/dev/null; do sleep 3000; ./recast.sh sync >> $RUNDIR/sync.log 2>&1; done ) &
  # Executables fixed while a run is in progress can be dropped into runner/exec-<arch>/ in S3;
  # they are picked up before UPP runs (the forecast binary is never replaced under a running job).
  refresh_exec() { aws s3 sync --only-show-errors --exclude "NEMS*" s3://nam-recast-617711905691/runner/exec-$(uname -m)/ /opt/nam/work/exec/ 2>/dev/null || true; }
  if [ "${POST_AFTER:-0}" = 1 ]; then
    wait $FPID; FRC=$?
    refresh_exec
    ./recast.sh post > $RUNDIR/post.log 2>&1; PRC=$?
  else
    sleep 120; refresh_exec
    WAIT=1 ./recast.sh post > $RUNDIR/post.log 2>&1; PRC=$?
    wait $FPID; FRC=$?
  fi
  echo "fcst rc=$FRC post rc=$PRC $(date -u +%FT%TZ)" | tee -a $RUNDIR/runner.log
fi
kill $MEMPID 2>/dev/null
tl "runner done fcst=$FRC post=$PRC nps=$NRC"
./recast.sh sync >> $RUNDIR/sync.log 2>&1
aws s3 cp --only-show-errors $RUNDIR/runner.log $S3RUN/logs/runner.log
for f in nps.log fcst.log post.log sync.log mem.log timeline.txt products.log; do [ -s $RUNDIR/$f ] && aws s3 cp --only-show-errors $RUNDIR/$f $S3RUN/logs/$f; done
if [ $NRC = 0 ] && [ $FRC = 0 ] && [ $PRC = 0 ]; then echo done | aws s3 cp - $S3RUN/DONE; else echo "nps=$NRC fcst=$FRC post=$PRC" | aws s3 cp - $S3RUN/FAILED; fi
# self-chaining: the next queue line gets its own runner (launch.sh hands over to a relay when the
# Spot vCPU quota cannot hold two runners at once)
if [ "${CHAIN:-0}" = 1 ]; then
  QUEUE=${QUEUE:-s3://nam-recast-617711905691/queue/hindcast.txt} ./launch.sh --next > $RUNDIR/chain.log 2>&1
  echo "chain rc=$? $(cat $RUNDIR/chain.log | tail -3 | tr '\n' ' ')" | tee -a $RUNDIR/runner.log
  aws s3 cp --only-show-errors $RUNDIR/chain.log $S3RUN/logs/chain.log
  aws s3 cp --only-show-errors $RUNDIR/runner.log $S3RUN/logs/runner.log
fi

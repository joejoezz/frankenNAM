#!/bin/bash
# Runner-node driver (c7a.48xlarge from the build-box AMI): forecast + post for $CYCLE with
# hourly S3 syncs; resumes from the newest restart in S3 after a Spot interruption.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export CYCLE=${CYCLE:-2026110100}
export RUNDIR=/opt/nam/runs/$CYCLE S3RUN=s3://nam-recast-617711905691/cases/$CYCLE/recast
mkdir -p $RUNDIR/fcst $RUNDIR/grib2
cd "$HERE"
# c7a has no SMT: a c7a.48xlarge is 192 physical cores. Use 168 compute + 2x8 write tasks
# and leave 8 cores for UPP running alongside; on a smaller box fall back to the 96-core layout.
NC=$(nproc)
if [ "$NC" -ge 190 ]; then
  export INPES=${INPES:-12} JNPES=${JNPES:-14} WRITE_GROUPS=${WRITE_GROUPS:-2} WRITE_TASKS=${WRITE_TASKS:-8}
  export FCST_CPUS=0-183 POST_CPUS=184-191 NPOST=8
else
  export INPES=${INPES:-8} JNPES=${JNPES:-11} WRITE_GROUPS=${WRITE_GROUPS:-1} WRITE_TASKS=${WRITE_TASKS:-8}
  export NPOST=${NPOST:-4}
fi
lscpu | grep -E "^CPU\(s\)|Thread|Model name" >> $RUNDIR/runner.log 2>/dev/null || true
echo "layout ${INPES}x${JNPES} + ${WRITE_GROUPS}x${WRITE_TASKS}, post $NPOST" >> $RUNDIR/runner.log
echo "runner start $(date -u +%FT%TZ) $(curl -s http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null)" | tee -a $RUNDIR/runner.log
aws s3 sync --only-show-errors $S3RUN/history/ $RUNDIR/fcst/ --exclude "*" --include "nmmb_rst_*"
aws s3 sync --only-show-errors $S3RUN/grib2-all/ $RUNDIR/grib2/
./recast.sh fcst > $RUNDIR/fcst.log 2>&1 &
FPID=$!
( while kill -0 $FPID 2>/dev/null; do sleep 3000; ./recast.sh sync >> $RUNDIR/sync.log 2>&1; done ) &
sleep 120
WAIT=1 ./recast.sh post > $RUNDIR/post.log 2>&1; PRC=$?
wait $FPID; FRC=$?
echo "fcst rc=$FRC post rc=$PRC $(date -u +%FT%TZ)" | tee -a $RUNDIR/runner.log
./recast.sh sync >> $RUNDIR/sync.log 2>&1
aws s3 cp --only-show-errors $RUNDIR/runner.log $S3RUN/logs/runner.log
for f in fcst.log post.log sync.log; do aws s3 cp --only-show-errors $RUNDIR/$f $S3RUN/logs/$f; done
[ $FRC = 0 ] && [ $PRC = 0 ] && echo done | aws s3 cp - $S3RUN/DONE || echo "fcst=$FRC post=$PRC" | aws s3 cp - $S3RUN/FAILED
